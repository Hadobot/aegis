from rag.vector_store import ThreatVectorStore
from datetime import datetime
from typing import Dict, Any, List
import json
import os


class AuditorAgent:
    """
    AUDITOR - Logs everything and maps to compliance frameworks.
    Full traceability for audit purposes.
    """

    def __init__(self):
        self.vector_store = ThreatVectorStore()
        self.agent_id = "auditor"
        self.audit_logs: List[Dict] = []

    async def log_and_map(
        self,
        request_id: str,
        sentry_result: Dict,
        shield_result: Dict,
        router_result: Dict,
        agent_id: str = "auditor"
    ) -> Dict[str, Any]:
        # 1. Map to compliance frameworks
        compliance_refs = await self._map_compliance(
            threat_type=sentry_result.get("threat_type", "none"),
            violations=shield_result.get("violations", [])
        )

        # 2. Create audit log entry
        audit_entry = {
            "log_id": f"audit-{request_id}",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": agent_id,
            "sentry_result": sentry_result,
            "shield_result": shield_result,
            "router_result": router_result,
            "compliance_refs": compliance_refs,
            "action_taken": router_result.get("action", "unknown")
        }

        # 3. Store audit log
        self.audit_logs.append(audit_entry)

        # 4. Write to file
        os.makedirs("logs", exist_ok=True)
        with open("logs/audit.jsonl", "a") as f:
            f.write(json.dumps(audit_entry) + "\n")

        return {
            "audit_id": audit_entry["log_id"],
            "compliance_refs": compliance_refs,
            "logged": True,
            "timestamp": audit_entry["timestamp"]
        }

    async def _map_compliance(self, threat_type: str, violations: List[str]) -> List[str]:
        query = f"Threat: {threat_type}, Violations: {violations}"
        results = await self.vector_store.query(
            query,
            collection="compliance_frameworks",
            top_k=3
        )

        return [chunk["metadata"].get("control_id", "unknown")
                for chunk in results.get("chunks", [])]

    def get_logs(self, limit: int = 100) -> List[Dict]:
        return self.audit_logs[-limit:]

    def get_logs_by_request(self, request_id: str) -> List[Dict]:
        return [log for log in self.audit_logs if log["request_id"] == request_id]
