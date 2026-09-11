import json
import os
import threading
import time
import asyncio
from typing import Dict, Optional
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import httpx

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PROXY_PORTS_FILE = os.path.join(DATA_DIR, "proxy_ports.json")

PROXY_BASE_PORT = int(os.getenv("PROXY_BASE_PORT", "8001"))
UPSTREAM_LLM_BASE_URL = os.getenv("UPSTREAM_LLM_BASE_URL", "https://api.openai.com")
UPSTREAM_LLM_API_KEY = os.getenv("UPSTREAM_LLM_API_KEY", "")

_lock = threading.Lock()
_port_allocator: Dict[str, int] = {}
_running_servers: Dict[str, uvicorn.Server] = {}
_server_threads: Dict[str, threading.Thread] = {}


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_ports() -> Dict[str, int]:
    _ensure_dir()
    if not os.path.exists(PROXY_PORTS_FILE):
        return {}
    with open(PROXY_PORTS_FILE, "r") as f:
        return json.load(f)


def _save_ports(ports: Dict[str, int]):
    _ensure_dir()
    with open(PROXY_PORTS_FILE, "w") as f:
        json.dump(ports, f, indent=2)


def _get_next_available_port() -> int:
    used_ports = set(_port_allocator.values())
    port = PROXY_BASE_PORT
    while port in used_ports:
        port += 1
    return port


def assign_port(agent_id: str) -> int:
    with _lock:
        ports = _load_ports()
        if agent_id in ports:
            return ports[agent_id]
        port = _get_next_available_port()
        ports[agent_id] = port
        _port_allocator[agent_id] = port
        _save_ports(ports)
        return port


def release_port(agent_id: str):
    with _lock:
        ports = _load_ports()
        if agent_id in ports:
            del ports[agent_id]
            _port_allocator.pop(agent_id, None)
            _save_ports(ports)


def get_agent_port(agent_id: str) -> Optional[int]:
    with _lock:
        ports = _load_ports()
        return ports.get(agent_id)


def get_agent_proxy_url(agent_id: str) -> str:
    port = get_agent_port(agent_id)
    if port:
        return f"http://localhost:{port}/v1"
    return ""


def get_all_proxies() -> Dict[str, dict]:
    with _lock:
        ports = _load_ports()
        return {
            aid: {
                "agent_id": aid,
                "port": port,
                "proxy_url": f"http://localhost:{port}/v1",
                "status": "running" if aid in _running_servers else "stopped",
            }
            for aid, port in ports.items()
        }


def _create_agent_proxy_app(agent_id: str) -> FastAPI:
    proxy_app = FastAPI(title=f"Aegis Agent Proxy - {agent_id}")

    @proxy_app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def agent_proxy(request: Request, path: str):
        start_time = time.time()

        body = await request.body()
        request_json = {}
        if body:
            try:
                request_json = json.loads(body)
            except Exception:
                request_json = {}

        prompt = ""
        if "messages" in request_json:
            for msg in reversed(request_json["messages"]):
                if msg.get("role") == "user":
                    prompt = msg.get("content", "")
                    break
        elif "prompt" in request_json:
            prompt = request_json["prompt"]
        elif "contents" in request_json:
            for part in request_json["contents"]:
                if isinstance(part, dict) and "parts" in part:
                    for p in part["parts"]:
                        if isinstance(p, dict) and "text" in p:
                            prompt = p["text"]
                            break

        from langgraph_pipeline import AegisPipeline
        from agents.auditor import AuditorAgent
        from agents.shield import ShieldAgent

        pipeline = AegisPipeline()
        auditor = AuditorAgent()
        shield = ShieldAgent()

        sentry_result = await pipeline.sentry.analyze_input(prompt)

        if sentry_result.get("threat_detected") and sentry_result.get("confidence_score", 0) > 0.7:
            elapsed = time.time() - start_time
            await auditor.log_and_map(
                request_id=f"proxy-agent-block-{int(time.time()*1000)}",
                sentry_result=sentry_result,
                shield_result={"violations": [], "confidence_score": 0},
                router_result={"action": "block", "combined_risk": sentry_result["confidence_score"]},
                agent_id=agent_id,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "blocked_by_aegis",
                    "reason": sentry_result.get("reasoning", "Threat detected"),
                    "threat_type": sentry_result.get("threat_type"),
                    "confidence": sentry_result.get("confidence_score"),
                    "detection_path": sentry_result.get("path", "unknown"),
                    "aegis_latency_ms": round(elapsed * 1000, 1),
                    "proxy_agent_id": agent_id,
                },
            )

        if UPSTREAM_LLM_BASE_URL.rstrip("/").endswith("/v1"):
            upstream_url = f"{UPSTREAM_LLM_BASE_URL.rstrip('/')}/{path}"
        else:
            upstream_url = f"{UPSTREAM_LLM_BASE_URL.rstrip('/')}/v1/{path}"

        headers = dict(request.headers)
        headers["host"] = upstream_url.split("//")[1].split("/")[0]
        if UPSTREAM_LLM_API_KEY:
            headers["authorization"] = f"Bearer {UPSTREAM_LLM_API_KEY}"
        headers.pop("host", None)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                upstream_response = await client.request(
                    method=request.method,
                    url=upstream_url,
                    headers=headers,
                    content=body,
                    params=dict(request.query_params),
                )
        except httpx.RequestError as e:
            return JSONResponse(status_code=502, content={"error": "upstream_unavailable", "detail": str(e)})

        llm_response_text = ""
        if upstream_response.status_code == 200:
            try:
                llm_json = upstream_response.json()
                if "choices" in llm_json and llm_json["choices"]:
                    llm_response_text = llm_json["choices"][0].get("message", {}).get("content", "")
                elif "candidates" in llm_json:
                    candidates = llm_json.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        llm_response_text = "".join(p.get("text", "") for p in parts)
            except Exception:
                pass

        shield_result = await shield.validate_output(prompt=prompt, response=llm_response_text)

        if shield_result.get("violations") and not shield_result.get("safe", True):
            elapsed = time.time() - start_time
            await auditor.log_and_map(
                request_id=f"proxy-agent-output-block-{int(time.time()*1000)}",
                sentry_result=sentry_result,
                shield_result=shield_result,
                router_result={"action": "block", "combined_risk": shield_result.get("confidence_score", 0)},
                agent_id=agent_id,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "blocked_by_aegis",
                    "reason": "LLM response failed output validation",
                    "violations": shield_result.get("violations", []),
                    "confidence": shield_result.get("confidence_score"),
                    "aegis_latency_ms": round(elapsed * 1000, 1),
                    "proxy_agent_id": agent_id,
                },
            )

        elapsed = time.time() - start_time
        await auditor.log_and_map(
            request_id=f"proxy-agent-allow-{int(time.time()*1000)}",
            sentry_result=sentry_result,
            shield_result=shield_result,
            router_result={"action": "allow", "combined_risk": 0},
            agent_id=agent_id,
        )

        response_headers = dict(upstream_response.headers)
        response_headers["x-aegis-action"] = "allow"
        response_headers["x-aegis-agent-id"] = agent_id
        response_headers["x-aegis-threat-detected"] = str(sentry_result.get("threat_detected", False)).lower()
        response_headers["x-aegis-detection-path"] = sentry_result.get("path", "unknown")
        response_headers["x-aegis-latency-ms"] = str(round(elapsed * 1000, 1))
        response_headers["x-aegis-proxy-port"] = str(get_agent_port(agent_id) or "")

        return StreamingResponse(
            iter([upstream_response.content]),
            status_code=upstream_response.status_code,
            headers=response_headers,
            media_type=upstream_response.headers.get("content-type", "application/json"),
        )

    return proxy_app


def _run_server(agent_id: str, port: int):
    app = _create_agent_proxy_app(agent_id)
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    _running_servers[agent_id] = server
    try:
        server.run()
    except Exception:
        pass
    finally:
        _running_servers.pop(agent_id, None)


def start_agent_proxy(agent_id: str, port: Optional[int] = None) -> dict:
    if agent_id in _running_servers:
        return {
            "agent_id": agent_id,
            "port": get_agent_port(agent_id),
            "proxy_url": get_agent_proxy_url(agent_id),
            "status": "already_running",
        }

    if port is None:
        port = assign_port(agent_id)

    thread = threading.Thread(target=_run_server, args=(agent_id, port), daemon=True)
    thread.start()
    _server_threads[agent_id] = thread

    time.sleep(0.3)

    return {
        "agent_id": agent_id,
        "port": port,
        "proxy_url": f"http://localhost:{port}/v1",
        "status": "started",
    }


def stop_agent_proxy(agent_id: str) -> bool:
    server = _running_servers.get(agent_id)
    if server:
        server.should_exit = True
        _server_threads.pop(agent_id, None)
        return True
    return False


def start_all_existing_proxies():
    ports = _load_ports()
    for agent_id, port in ports.items():
        if agent_id not in _running_servers:
            start_agent_proxy(agent_id, port)


def get_running_proxies() -> Dict[str, dict]:
    result = {}
    for agent_id, server in _running_servers.items():
        port = get_agent_port(agent_id)
        result[agent_id] = {
            "agent_id": agent_id,
            "port": port,
            "proxy_url": f"http://localhost:{port}/v1" if port else "",
            "status": "running",
        }
    return result
