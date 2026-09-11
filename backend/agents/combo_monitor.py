import json
import os
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime

VIOLATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
VIOLATIONS_FILE = os.path.join(VIOLATIONS_DIR, "combo_violations.jsonl")

_lock = threading.Lock()


def _ensure_dir():
    os.makedirs(VIOLATIONS_DIR, exist_ok=True)


class ComboMonitorAgent:
    """
    Monitors agent-to-agent communication and enforces guardrails.

    Validates cross-agent calls against combo connection definitions:
    - from/to agent pairs
    - communication type (allowed/conditional/blocked)
    - data flow level (public/internal/sensitive/pii/restricted)
    - required actions and approval flags
    """

    def __init__(self):
        self.violations: List[Dict[str, Any]] = []
        self._load_violations()

    def _load_violations(self):
        _ensure_dir()
        if not os.path.exists(VIOLATIONS_FILE):
            return
        try:
            with open(VIOLATIONS_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.violations.append(json.loads(line))
        except Exception:
            pass

    def _save_violation(self, violation: Dict[str, Any]):
        _ensure_dir()
        with open(VIOLATIONS_FILE, "a") as f:
            f.write(json.dumps(violation) + "\n")
        self.violations.append(violation)

    def validate_communication(
        self,
        from_agent: str,
        to_agent: str,
        combo_id: str,
        data_flow: str = "public",
        action: str = "",
        combos: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Validate whether from_agent is allowed to communicate with to_agent
        within the context of a specific combo.

        Returns:
            {
                "allowed": bool,
                "reason": str,
                "monitoring_mode": "enforce" | "monitor",
                "connection": dict | None,
                "violated_rules": list[str],
            }
        """
        if not combos:
            from services import combo_store
            combos = combo_store.get_all()

        combo = None
        for c in combos:
            if c.get("id") == combo_id:
                combo = c
                break

        if not combo:
            return self._deny(
                from_agent, to_agent, combo_id,
                f"Combo '{combo_id}' not found",
                data_flow, action,
            )

        if combo.get("status") != "active":
            return self._deny(
                from_agent, to_agent, combo_id,
                f"Combo '{combo_id}' is not active",
                data_flow, action,
            )

        agents_in_combo = combo.get("agents", [])
        if from_agent not in agents_in_combo:
            return self._deny(
                from_agent, to_agent, combo_id,
                f"Agent '{from_agent}' is not a member of combo '{combo_id}'",
                data_flow, action,
            )
        if to_agent not in agents_in_combo:
            return self._deny(
                from_agent, to_agent, combo_id,
                f"Agent '{to_agent}' is not a member of combo '{combo_id}'",
                data_flow, action,
            )

        connections = combo.get("connections", [])
        matching_connection = None
        for conn in connections:
            conn_from = conn.get("from_agent", conn.get("from", ""))
            conn_to = conn.get("to_agent", conn.get("to", ""))
            if conn_from == from_agent and conn_to == to_agent:
                matching_connection = conn
                break

        if not matching_connection:
            return self._deny(
                from_agent, to_agent, combo_id,
                f"No connection defined from '{from_agent}' to '{to_agent}' in combo '{combo_id}'",
                data_flow, action,
            )

        violated_rules = []
        communication_type = matching_connection.get("communication", "allowed")
        connection_data_flow = matching_connection.get("data_flow", matching_connection.get("dataFlow", "public"))
        connection_actions = matching_connection.get("actions", [])
        approval_required = matching_connection.get("approval_required", matching_connection.get("approvalRequired", False))

        if communication_type == "blocked":
            violated_rules.append(f"Connection from '{from_agent}' to '{to_agent}' is explicitly blocked")

        if communication_type == "conditional" and approval_required:
            violated_rules.append(f"Communication from '{from_agent}' to '{to_agent}' requires approval")

        data_flow_hierarchy = {"public": 0, "internal": 1, "sensitive": 2, "pii": 3, "restricted": 4}
        requested_level = data_flow_hierarchy.get(data_flow, 0)
        allowed_level = data_flow_hierarchy.get(connection_data_flow, 0)
        if requested_level > allowed_level:
            violated_rules.append(
                f"Data flow level '{data_flow}' exceeds allowed level '{connection_data_flow}'"
            )

        if connection_actions and action and action not in connection_actions:
            violated_rules.append(
                f"Action '{action}' is not in allowed actions: {connection_actions}"
            )

        monitoring_mode = combo.get("monitoring_mode", "enforce")

        if violated_rules:
            reason = "; ".join(violated_rules)
            self._log_violation(
                from_agent=from_agent,
                to_agent=to_agent,
                combo_id=combo_id,
                reason=reason,
                blocked=(monitoring_mode == "enforce"),
                connection_ref=matching_connection,
                data_flow=data_flow,
                action=action,
            )
            return {
                "allowed": monitoring_mode == "monitor",
                "reason": reason,
                "monitoring_mode": monitoring_mode,
                "connection": matching_connection,
                "violated_rules": violated_rules,
            }

        return {
            "allowed": True,
            "reason": "Communication is permitted by combo connection rules",
            "monitoring_mode": monitoring_mode,
            "connection": matching_connection,
            "violated_rules": [],
        }

    def _deny(
        self,
        from_agent: str,
        to_agent: str,
        combo_id: str,
        reason: str,
        data_flow: str,
        action: str,
    ) -> Dict[str, Any]:
        self._log_violation(
            from_agent=from_agent,
            to_agent=to_agent,
            combo_id=combo_id,
            reason=reason,
            blocked=True,
            connection_ref=None,
            data_flow=data_flow,
            action=action,
        )
        return {
            "allowed": False,
            "reason": reason,
            "monitoring_mode": "enforce",
            "connection": None,
            "violated_rules": [reason],
        }

    def _log_violation(
        self,
        from_agent: str,
        to_agent: str,
        combo_id: str,
        reason: str,
        blocked: bool,
        connection_ref: Optional[Dict[str, Any]],
        data_flow: str,
        action: str,
    ):
        violation = {
            "violation_id": f"violation-{int(datetime.utcnow().timestamp()*1000)}",
            "timestamp": datetime.utcnow().isoformat(),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "combo_id": combo_id,
            "reason": reason,
            "blocked": blocked,
            "connection_ref": connection_ref,
            "data_flow": data_flow,
            "action": action,
        }
        with _lock:
            self._save_violation(violation)

    def get_violations(self, combo_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with _lock:
            if combo_id:
                filtered = [v for v in self.violations if v.get("combo_id") == combo_id]
            else:
                filtered = list(self.violations)
            filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return filtered[:limit]

    def get_violation_count(self, combo_id: Optional[str] = None) -> int:
        with _lock:
            if combo_id:
                return sum(1 for v in self.violations if v.get("combo_id") == combo_id)
            return len(self.violations)

    def get_active_monitored_combos(self, combos: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        if combos is None:
            from services import combo_store
            combos = combo_store.get_all()

        monitored = []
        for combo in combos:
            if combo.get("status") == "active" and combo.get("connections"):
                monitored.append({
                    "combo_id": combo.get("id"),
                    "name": combo.get("name"),
                    "monitoring_mode": combo.get("monitoring_mode", "enforce"),
                    "agent_count": len(combo.get("agents", [])),
                    "connection_count": len(combo.get("connections", [])),
                    "violation_count": self.get_violation_count(combo.get("id")),
                })
        return monitored

    def get_monitoring_summary(self, combos: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        active_combos = self.get_active_monitored_combos(combos)
        total_violations = self.get_violation_count()
        blocked_count = sum(1 for v in self.violations if v.get("blocked"))

        return {
            "total_active_combos": len(active_combos),
            "total_violations": total_violations,
            "total_blocked": blocked_count,
            "total_allowed_with_violation": total_violations - blocked_count,
            "combos": active_combos,
        }
