from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from contextlib import asynccontextmanager
from models.schemas import (
    AnalysisRequest, AnalysisResponse, AuditLog,
    AgentRegistration, AgentRegistrationResponse, HealthResponse,
    ComboMonitorRequest, MonitoringMode,
)
from langgraph_pipeline import AegisPipeline
from agents.auditor import AuditorAgent
from agents.shield import ShieldAgent
from agents.combo_monitor import ComboMonitorAgent
from services import agent_store, audit_store, combo_store
from services import proxy_manager
from datetime import datetime
import httpx
import os
import json
import time

combo_monitor = ComboMonitorAgent()


@asynccontextmanager
async def lifespan(app: FastAPI):
    proxy_manager.start_all_existing_proxies()
    yield


app = FastAPI(
    title="Aegis - Enterprise AI Agent Governance Proxy",
    description="Transparent security proxy for LLM applications",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = AegisPipeline()
auditor = AuditorAgent()
shield = ShieldAgent()

UPSTREAM_LLM_BASE_URL = os.getenv("UPSTREAM_LLM_BASE_URL", "https://api.openai.com")
UPSTREAM_LLM_API_KEY = os.getenv("UPSTREAM_LLM_API_KEY", "")


# ============================================================
# PROXY MODE — Main proxy on port 8000
# ============================================================

@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_to_upstream(request: Request, path: str):
    start_time = time.time()
    agent_id = request.headers.get("x-aegis-agent-id", "unknown")

    body = await request.body()
    request_json = {}
    if body:
        try:
            request_json = json.loads(body)
        except json.JSONDecodeError:
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

    sentry_result = await pipeline.sentry.analyze_input(prompt)

    if sentry_result.get("threat_detected") and sentry_result.get("confidence_score", 0) > 0.7:
        elapsed = time.time() - start_time
        detection_path = sentry_result.get("path", "unknown")

        await auditor.log_and_map(
            request_id=f"proxy-block-{int(time.time()*1000)}",
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
                "detection_path": detection_path,
                "aegis_latency_ms": round(elapsed * 1000, 1),
                "message": "Request blocked by Aegis security proxy. Contact your security team.",
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
        return JSONResponse(
            status_code=502,
            content={"error": "upstream_unavailable", "detail": str(e)},
        )

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
            request_id=f"proxy-output-block-{int(time.time()*1000)}",
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
                "message": "LLM response blocked by Aegis. Output contained policy violations.",
            },
        )

    elapsed = time.time() - start_time

    await auditor.log_and_map(
        request_id=f"proxy-allow-{int(time.time()*1000)}",
        sentry_result=sentry_result,
        shield_result=shield_result,
        router_result={"action": "allow", "combined_risk": 0},
        agent_id=agent_id,
    )

    detection_path = sentry_result.get("path", "unknown")
    response_headers = dict(upstream_response.headers)
    response_headers["x-aegis-action"] = "allow"
    response_headers["x-aegis-threat-detected"] = str(sentry_result.get("threat_detected", False)).lower()
    response_headers["x-aegis-detection-path"] = detection_path
    response_headers["x-aegis-latency-ms"] = str(round(elapsed * 1000, 1))

    return StreamingResponse(
        iter([upstream_response.content]),
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type", "application/json"),
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    running_proxies = proxy_manager.get_running_proxies()
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        services={
            "api": "up",
            "qdrant": "up",
            "pipeline": "up",
            "upstream_llm": "configured" if UPSTREAM_LLM_API_KEY else "not_configured",
            "agent_proxies": f"{len(running_proxies)} running",
        },
    )


# ============================================================
# DIRECT ANALYSIS MODE
# ============================================================

@app.post("/api/v1/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest):
    try:
        result = await pipeline.analyze(
            prompt=request.prompt,
            response=request.response,
        )

        return AnalysisResponse(
            request_id=result["request_id"],
            timestamp=datetime.utcnow().isoformat(),
            threat_detected=result["threat_detected"],
            threat_type=result["threat_type"],
            confidence_score=result["confidence_score"],
            combined_risk=result["combined_risk"],
            action=result["action"],
            violations=result["violations"],
            compliance_refs=result["compliance_refs"],
            evidence_chunks=result["evidence_chunks"],
            reasoning=result["reasoning"],
            requires_human_review=result["requires_human_review"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/analyze/prompt")
async def analyze_prompt(request: AnalysisRequest):
    try:
        result = await pipeline.analyze(prompt=request.prompt)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# AUDIT
# ============================================================

@app.get("/api/v1/audit/logs")
async def get_audit_logs(limit: int = 100, offset: int = 0):
    file_logs = audit_store.get_audit_logs(limit=limit, offset=offset)
    memory_logs = auditor.get_logs(limit=limit)
    seen_ids = {log.get("log_id") for log in file_logs}
    merged = file_logs + [log for log in memory_logs if log.get("log_id") not in seen_ids]
    merged.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    merged = merged[:limit]
    return {"logs": merged, "total": audit_store.get_audit_logs_count() + len(auditor.audit_logs)}


@app.get("/api/v1/audit/agent/{agent_id}")
async def get_agent_logs(agent_id: str):
    file_logs = audit_store.get_audit_logs_by_agent(agent_id)
    memory_logs = [log for log in auditor.audit_logs if log.get("agent_id") == agent_id]
    seen_ids = {log.get("log_id") for log in file_logs}
    merged = file_logs + [log for log in memory_logs if log.get("log_id") not in seen_ids]
    merged.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return {"agent_id": agent_id, "logs": merged}


# ============================================================
# AGENTS — Registration + Per-Agent Proxy
# ============================================================

@app.post("/api/v1/agents/register")
async def register_agent(agent: AgentRegistration):
    agent_data = agent.model_dump()
    agent_data["autonomy_level"] = int(agent.autonomy_level)

    proxy_info = proxy_manager.start_agent_proxy(agent.agent_id)
    agent_data["proxy_url"] = proxy_info["proxy_url"]
    agent_data["proxy_port"] = proxy_info["port"]

    agent_store.upsert(agent.agent_id, agent_data)

    return {
        "registered": True,
        "agent_id": agent.agent_id,
        "proxy_url": proxy_info["proxy_url"],
        "proxy_port": proxy_info["port"],
    }


@app.get("/api/v1/agents")
async def list_agents():
    agents = agent_store.get_all()
    for agent in agents:
        aid = agent.get("agent_id", "")
        if not agent.get("proxy_url"):
            agent["proxy_url"] = proxy_manager.get_agent_proxy_url(aid)
            agent["proxy_port"] = proxy_manager.get_agent_port(aid) or 0
    return {"agents": agents}


@app.get("/api/v1/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = agent_store.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    agent["proxy_url"] = proxy_manager.get_agent_proxy_url(agent_id)
    agent["proxy_port"] = proxy_manager.get_agent_port(agent_id) or 0
    agent_logs = audit_store.get_audit_logs_by_agent(agent_id, limit=50)
    return {"agent": agent, "logs": agent_logs}


@app.get("/api/v1/agents/discover")
async def discover_agents():
    agents = agent_store.get_all()
    discovery = []
    for agent in agents:
        aid = agent.get("agent_id", "")
        discovery.append({
            "agent_id": aid,
            "name": agent.get("name", ""),
            "description": agent.get("description", ""),
            "proxy_url": proxy_manager.get_agent_proxy_url(aid),
            "proxy_port": proxy_manager.get_agent_port(aid) or 0,
            "status": "active",
            "owner": agent.get("owner", ""),
        })
    return {"agents": discovery}


@app.get("/api/v1/agents/discover/{agent_id}")
async def discover_agent(agent_id: str):
    agent = agent_store.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return {
        "agent_id": agent_id,
        "name": agent.get("name", ""),
        "description": agent.get("description", ""),
        "proxy_url": proxy_manager.get_agent_proxy_url(agent_id),
        "proxy_port": proxy_manager.get_agent_port(agent_id) or 0,
        "status": "active",
        "owner": agent.get("owner", ""),
    }


@app.get("/api/v1/proxies")
async def list_proxies():
    return {"proxies": proxy_manager.get_all_proxies()}


@app.get("/api/v1/proxies/running")
async def list_running_proxies():
    return {"proxies": proxy_manager.get_running_proxies()}


@app.post("/api/v1/proxies/{agent_id}/restart")
async def restart_proxy(agent_id: str):
    agent = agent_store.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    proxy_manager.stop_agent_proxy(agent_id)
    time.sleep(0.5)
    result = proxy_manager.start_agent_proxy(agent_id)
    return result


# ============================================================
# METRICS
# ============================================================

@app.get("/api/v1/metrics")
async def get_metrics():
    metrics = audit_store.compute_metrics()
    metrics["active_agents"] = len(agent_store.get_all())
    metrics["escalations"] = audit_store.get_escalations_count()
    return metrics


# ============================================================
# COMBOS — Multi-agent governance graphs
# ============================================================

@app.get("/api/v1/combos")
async def list_combos():
    return {"combos": combo_store.get_all()}


@app.get("/api/v1/combos/{combo_id}")
async def get_combo(combo_id: str):
    combo = combo_store.get(combo_id)
    if not combo:
        raise HTTPException(status_code=404, detail=f"Combo '{combo_id}' not found")
    return combo


@app.post("/api/v1/combos")
async def create_combo(request: Request):
    body = await request.json()
    combo_id = f"combo-{int(time.time()*1000)}"

    connections = body.get("connections", [])
    normalized_connections = []
    for conn in connections:
        normalized_connections.append({
            "from_agent": conn.get("from_agent", conn.get("from", "")),
            "to_agent": conn.get("to_agent", conn.get("to", "")),
            "communication": conn.get("communication", "allowed"),
            "data_flow": conn.get("data_flow", conn.get("dataFlow", "public")),
            "actions": conn.get("actions", []),
            "approval_required": conn.get("approval_required", conn.get("approvalRequired", False)),
        })

    combo = {
        "id": combo_id,
        "name": body.get("name", ""),
        "description": body.get("description", ""),
        "agents": body.get("agents", []),
        "connections": normalized_connections,
        "monitoring_mode": body.get("monitoring_mode", "enforce"),
        "status": "active",
        "createdAt": datetime.utcnow().isoformat(),
    }
    combo_store.upsert(combo_id, combo)
    return combo


@app.put("/api/v1/combos/{combo_id}")
async def update_combo(combo_id: str, request: Request):
    existing = combo_store.get(combo_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Combo '{combo_id}' not found")

    body = await request.json()
    connections = body.get("connections", existing.get("connections", []))
    normalized_connections = []
    for conn in connections:
        normalized_connections.append({
            "from_agent": conn.get("from_agent", conn.get("from", "")),
            "to_agent": conn.get("to_agent", conn.get("to", "")),
            "communication": conn.get("communication", "allowed"),
            "data_flow": conn.get("data_flow", conn.get("dataFlow", "public")),
            "actions": conn.get("actions", []),
            "approval_required": conn.get("approval_required", conn.get("approvalRequired", False)),
        })

    existing.update({
        "name": body.get("name", existing.get("name", "")),
        "description": body.get("description", existing.get("description", "")),
        "agents": body.get("agents", existing.get("agents", [])),
        "connections": normalized_connections,
        "monitoring_mode": body.get("monitoring_mode", existing.get("monitoring_mode", "enforce")),
    })
    combo_store.upsert(combo_id, existing)
    return existing


@app.delete("/api/v1/combos/{combo_id}")
async def delete_combo(combo_id: str):
    deleted = combo_store.delete(combo_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Combo '{combo_id}' not found")
    return {"deleted": True}


# ============================================================
# COMBO MONITOR — Agent-to-agent communication guardrails
# ============================================================

@app.post("/api/v1/combo-monitor/validate")
async def validate_agent_communication(request: ComboMonitorRequest):
    combos = combo_store.get_all()
    result = combo_monitor.validate_communication(
        from_agent=request.from_agent_id,
        to_agent=request.to_agent_id,
        combo_id=request.combo_id,
        data_flow=request.data_flow.value if request.data_flow else "public",
        action=request.action or "",
        combos=combos,
    )
    status_code = 200 if result["allowed"] else 403
    return JSONResponse(status_code=status_code, content=result)


@app.get("/api/v1/combo-monitor/violations")
async def get_combo_violations(combo_id: str = None, limit: int = 100):
    violations = combo_monitor.get_violations(combo_id=combo_id, limit=limit)
    return {"violations": violations, "total": combo_monitor.get_violation_count(combo_id)}


@app.get("/api/v1/combo-monitor/status")
async def get_combo_monitor_status():
    combos = combo_store.get_all()
    return combo_monitor.get_monitoring_summary(combos)


@app.get("/api/v1/combo-monitor/active")
async def get_active_monitored_combos():
    combos = combo_store.get_all()
    return {"combos": combo_monitor.get_active_monitored_combos(combos)}


# ============================================================
# SECURITY AGENTS — Internal pipeline components
# ============================================================

@app.get("/api/v1/security-agents")
async def get_security_agents():
    logs = audit_store.get_audit_logs(limit=1000)
    sentry_events = sum(1 for l in logs if l.get("sentry_result", {}).get("threat_detected"))
    shield_events = sum(1 for l in logs if l.get("shield_result", {}).get("violations"))
    total = len(logs)
    return {"security_agents": [
        {
            "id": "sentry",
            "name": "Sentry",
            "role": "Input Guard",
            "description": "Detect prompt injection, jailbreaks, role hijacking and other malicious input.",
            "status": "active",
            "eventCount": total,
            "riskLevel": "medium" if sentry_events < total * 0.1 else "high",
        },
        {
            "id": "shield",
            "name": "Shield",
            "role": "Output Guard",
            "description": "Validate generated responses for harmful content, PII leakage and policy violations.",
            "status": "active",
            "eventCount": total,
            "riskLevel": "high" if shield_events > 0 else "low",
        },
        {
            "id": "intel",
            "name": "Intel",
            "role": "Threat Intelligence",
            "description": "Enrich suspicious interactions with threat intelligence from NVD, OWASP, and MITRE.",
            "status": "active",
            "eventCount": sentry_events,
            "riskLevel": "medium",
        },
        {
            "id": "router",
            "name": "Router",
            "role": "Decision Engine",
            "description": "Combine governance signals and determine the final allow/flag/block/escalate action.",
            "status": "active",
            "eventCount": total,
            "riskLevel": "low",
        },
        {
            "id": "auditor",
            "name": "Auditor",
            "role": "Compliance & Audit",
            "description": "Record governance decisions and map them to compliance frameworks.",
            "status": "active",
            "eventCount": total,
            "riskLevel": "low",
        },
        {
            "id": "combo-monitor",
            "name": "Combo Monitor",
            "role": "Agent Communication Guard",
            "description": "Monitor and enforce guardrails on agent-to-agent communication within combos.",
            "status": "active",
            "eventCount": combo_monitor.get_violation_count(),
            "riskLevel": "medium",
        },
    ]}


# ============================================================
# ESCALATIONS
# ============================================================

@app.post("/api/v1/escalate")
async def escalate_to_human(request: Request):
    body = await request.json()

    escalation = {
        "escalation_id": f"esc-{int(time.time()*1000)}",
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": body.get("request_id"),
        "prompt": body.get("prompt", "")[:200],
        "threat_type": body.get("threat_type"),
        "confidence": body.get("confidence"),
        "reasoning": body.get("reasoning"),
        "compliance_refs": body.get("compliance_refs", []),
        "status": "pending_review",
        "assigned_to": None,
    }

    os.makedirs("logs", exist_ok=True)
    with open("logs/escalations.jsonl", "a") as f:
        f.write(json.dumps(escalation) + "\n")

    return {
        "escalated": True,
        "escalation_id": escalation["escalation_id"],
        "message": "Request escalated to human analyst",
        "status": "pending_review",
    }


@app.get("/api/v1/escalations")
async def get_escalations(limit: int = 50):
    escalations = audit_store.get_escalations(limit=limit)
    return {"escalations": escalations, "total": audit_store.get_escalations_count()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
