from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from models.schemas import (
    AnalysisRequest, AnalysisResponse, AuditLog,
    AgentRegistration, HealthResponse
)
from langgraph_pipeline import AegisPipeline
from agents.auditor import AuditorAgent
from agents.shield import ShieldAgent
from services import agent_store, audit_store, combo_store
from datetime import datetime
import httpx
import os
import json
import time

app = FastAPI(
    title="Aegis - Enterprise AI Agent Governance Proxy",
    description="Transparent security proxy for LLM applications",
    version="1.0.0"
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
# PROXY MODE — The real deal
# ============================================================

@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_to_upstream(request: Request, path: str):
    """
    Transparent proxy: intercepts all /v1/* calls, runs security,
    then forwards to real LLM if safe.

    Enterprise just points their base_url to http://localhost:8000/v1
    """
    start_time = time.time()

    # 0. Extract agent identity from custom header
    agent_id = request.headers.get("x-aegis-agent-id", "unknown")

    # 1. Read the request body
    body = await request.body()
    request_json = {}
    if body:
        try:
            request_json = json.loads(body)
        except json.JSONDecodeError:
            request_json = {}

    # 2. Extract the user prompt from the request
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

    # 3. Run Sentry (input threat detection)
    sentry_result = await pipeline.sentry.analyze_input(prompt)

    # 4. If threat detected -> block immediately, never hit real LLM
    if sentry_result.get("threat_detected") and sentry_result.get("confidence_score", 0) > 0.7:
        elapsed = time.time() - start_time
        detection_path = sentry_result.get("path", "unknown")

        await auditor.log_and_map(
            request_id=f"proxy-block-{int(time.time()*1000)}",
            sentry_result=sentry_result,
            shield_result={"violations": [], "confidence_score": 0},
            router_result={"action": "block", "combined_risk": sentry_result["confidence_score"]},
            agent_id=agent_id
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
                "message": "Request blocked by Aegis security proxy. Contact your security team."
            }
        )

    # 5. Forward to real LLM
    # Handle base URLs that already include /v1 (e.g., OpenRouter)
    if UPSTREAM_LLM_BASE_URL.rstrip("/").endswith("/v1"):
        upstream_url = f"{UPSTREAM_LLM_BASE_URL.rstrip('/')}/{path}"
    else:
        upstream_url = f"{UPSTREAM_LLM_BASE_URL.rstrip('/')}/v1/{path}"
    headers = dict(request.headers)
    headers["host"] = upstream_url.split("//")[1].split("/")[0]
    if UPSTREAM_LLM_API_KEY:
        headers["authorization"] = f"Bearer {UPSTREAM_LLM_API_KEY}"
    headers.pop("host", None)  # Remove original host, let httpx set it

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            upstream_response = await client.request(
                method=request.method,
                url=upstream_url,
                headers=headers,
                content=body,
                params=dict(request.query_params)
            )
    except httpx.RequestError as e:
        return JSONResponse(
            status_code=502,
            content={"error": "upstream_unavailable", "detail": str(e)}
        )

    # 6. Get the LLM response
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

    # 7. Run Shield (output validation)
    shield_result = await shield.validate_output(prompt=prompt, response=llm_response_text)

    # 8. If output has violations -> block the response
    if shield_result.get("violations") and not shield_result.get("safe", True):
        elapsed = time.time() - start_time

        await auditor.log_and_map(
            request_id=f"proxy-output-block-{int(time.time()*1000)}",
            sentry_result=sentry_result,
            shield_result=shield_result,
            router_result={"action": "block", "combined_risk": shield_result.get("confidence_score", 0)},
            agent_id=agent_id
        )

        return JSONResponse(
            status_code=403,
            content={
                "error": "blocked_by_aegis",
                "reason": "LLM response failed output validation",
                "violations": shield_result.get("violations", []),
                "confidence": shield_result.get("confidence_score"),
                "aegis_latency_ms": round(elapsed * 1000, 1),
                "message": "LLM response blocked by Aegis. Output contained policy violations."
            }
        )

    # 9. Everything safe -> return the real LLM response with Aegis headers
    elapsed = time.time() - start_time

    await auditor.log_and_map(
        request_id=f"proxy-allow-{int(time.time()*1000)}",
        sentry_result=sentry_result,
        shield_result=shield_result,
        router_result={"action": "allow", "combined_risk": 0},
        agent_id=agent_id
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
        media_type=upstream_response.headers.get("content-type", "application/json")
    )


# ============================================================
# DIRECT ANALYSIS MODE — For demo and testing
# ============================================================

@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        services={
            "api": "up",
            "qdrant": "up",
            "pipeline": "up",
            "upstream_llm": "configured" if UPSTREAM_LLM_API_KEY else "not_configured"
        }
    )


@app.post("/api/v1/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest):
    try:
        result = await pipeline.analyze(
            prompt=request.prompt,
            response=request.response
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
            requires_human_review=result["requires_human_review"]
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


@app.post("/api/v1/agents/register")
async def register_agent(agent: AgentRegistration):
    agent_data = agent.model_dump()
    agent_data["autonomy_level"] = int(agent.autonomy_level)
    agent_store.upsert(agent.agent_id, agent_data)
    return {"registered": True, "agent_id": agent.agent_id}


@app.get("/api/v1/agents")
async def list_agents():
    return {"agents": agent_store.get_all()}


@app.get("/api/v1/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = agent_store.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    agent_logs = audit_store.get_audit_logs_by_agent(agent_id, limit=50)
    return {"agent": agent, "logs": agent_logs}


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
    combo = {
        "id": combo_id,
        "name": body.get("name", ""),
        "description": body.get("description", ""),
        "agents": body.get("agents", []),
        "connections": body.get("connections", []),
        "status": "active",
        "createdAt": datetime.utcnow().isoformat(),
    }
    combo_store.upsert(combo_id, combo)
    return combo


@app.delete("/api/v1/combos/{combo_id}")
async def delete_combo(combo_id: str):
    deleted = combo_store.delete(combo_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Combo '{combo_id}' not found")
    return {"deleted": True}


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
    ]}


@app.post("/api/v1/escalate")
async def escalate_to_human(request: Request):
    """
    Escalate a flagged request to human review.
    In production, this would send to a webhook/SIEM/dashboard.
    """
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
        "assigned_to": None
    }

    os.makedirs("logs", exist_ok=True)
    with open("logs/escalations.jsonl", "a") as f:
        f.write(json.dumps(escalation) + "\n")

    return {
        "escalated": True,
        "escalation_id": escalation["escalation_id"],
        "message": "Request escalated to human analyst",
        "status": "pending_review"
    }


@app.get("/api/v1/escalations")
async def get_escalations(limit: int = 50):
    """Get pending escalations for human review."""
    escalations = audit_store.get_escalations(limit=limit)
    return {"escalations": escalations, "total": audit_store.get_escalations_count()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
