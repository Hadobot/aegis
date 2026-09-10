from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List, Dict, Any
from agents.sentry import SentryAgent
from agents.shield import ShieldAgent
from agents.intel import IntelAgent
from agents.auditor import AuditorAgent
from agents.router import Router
import uuid


class AegisState(TypedDict):
    request_id: str
    prompt: str
    response: str
    agent_id: str
    sentry_result: Dict[str, Any]
    intel_result: Dict[str, Any]
    shield_result: Dict[str, Any]
    router_result: Dict[str, Any]
    auditor_result: Dict[str, Any]
    final_action: str
    combined_risk: float


class AegisPipeline:
    def __init__(self):
        self.sentry = SentryAgent()
        self.shield = ShieldAgent()
        self.intel = IntelAgent()
        self.auditor = AuditorAgent()
        self.router = Router()

        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AegisState)

        # Add nodes
        workflow.add_node("sentry", self._sentry_node)
        workflow.add_node("intel", self._intel_node)
        workflow.add_node("shield", self._shield_node)
        workflow.add_node("router", self._router_node)
        workflow.add_node("auditor", self._auditor_node)

        # Set entry point
        workflow.set_entry_point("sentry")

        # Add edges
        workflow.add_conditional_edges(
            "sentry",
            self._should_enrich,
            {
                "enrich": "intel",
                "skip": "shield"
            }
        )

        workflow.add_edge("intel", "shield")
        workflow.add_edge("shield", "router")
        workflow.add_edge("router", "auditor")
        workflow.add_edge("auditor", END)

        return workflow.compile()

    async def _sentry_node(self, state: AegisState) -> AegisState:
        result = await self.sentry.analyze_input(state["prompt"])
        return {"sentry_result": result}

    async def _intel_node(self, state: AegisState) -> AegisState:
        sentry_result = state.get("sentry_result", {})
        result = await self.intel.enrich_threat(
            threat_type=sentry_result.get("threat_type", "none"),
            pattern=state["prompt"]
        )
        return {"intel_result": result}

    async def _shield_node(self, state: AegisState) -> AegisState:
        response = state.get("response", "")
        if not response:
            response = "No response provided for analysis"

        result = await self.shield.validate_output(
            prompt=state["prompt"],
            response=response
        )
        return {"shield_result": result}

    async def _router_node(self, state: AegisState) -> AegisState:
        sentry_result = state.get("sentry_result", {})
        shield_result = state.get("shield_result", {})

        result = self.router.decide(sentry_result, shield_result)
        return {
            "router_result": result,
            "final_action": result.get("action", "unknown"),
            "combined_risk": result.get("combined_risk", 0)
        }

    async def _auditor_node(self, state: AegisState) -> AegisState:
        result = await self.auditor.log_and_map(
            request_id=state.get("request_id", str(uuid.uuid4())),
            sentry_result=state.get("sentry_result", {}),
            shield_result=state.get("shield_result", {}),
            router_result=state.get("router_result", {})
        )
        return {"auditor_result": result}

    def _should_enrich(self, state: AegisState) -> str:
        sentry_result = state.get("sentry_result", {})
        if sentry_result.get("threat_detected", False):
            return "enrich"
        return "skip"

    async def analyze(self, prompt: str, response: str = None) -> Dict[str, Any]:
        request_id = str(uuid.uuid4())

        initial_state = {
            "request_id": request_id,
            "prompt": prompt,
            "response": response or "",
            "agent_id": "unknown",
            "sentry_result": {},
            "intel_result": {},
            "shield_result": {},
            "router_result": {},
            "auditor_result": {},
            "final_action": "",
            "combined_risk": 0
        }

        result = await self.graph.ainvoke(initial_state)

        return {
            "request_id": request_id,
            "threat_detected": result["sentry_result"].get("threat_detected", False),
            "threat_type": result["sentry_result"].get("threat_type", "none"),
            "confidence_score": result["sentry_result"].get("confidence_score", 0),
            "combined_risk": result["combined_risk"],
            "action": result["final_action"],
            "violations": result["shield_result"].get("violations", []),
            "compliance_refs": result["auditor_result"].get("compliance_refs", []),
            "evidence_chunks": result["sentry_result"].get("evidence_chunks", []),
            "reasoning": result["router_result"].get("reasoning", ""),
            "requires_human_review": result["final_action"] == "escalate"
        }
