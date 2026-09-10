import time
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager


@dataclass
class TraceStep:
    step_id: str
    agent: str
    action: str
    tool_calls: List[str]
    confidence: Optional[float]
    latency_ms: float
    input_text: str
    output_text: str
    timestamp: str
    metadata: Dict[str, Any]


class AegisTracer:
    """
    Observability tracer — captures every step, tool call, and decision.
    Produces structured traces for post-incident analysis.
    """

    def __init__(self):
        self.traces: List[Dict[str, Any]] = []
        self.current_trace: Optional[Dict[str, Any]] = None
        self.step_counter = 0
        self.trace_dir = "logs/traces"
        os.makedirs(self.trace_dir, exist_ok=True)

    def start_trace(self, request_id: str, prompt: str) -> str:
        """Start a new trace for a request."""
        self.step_counter = 0
        self.current_trace = {
            "run_id": f"aegis-{request_id}",
            "timestamp": datetime.utcnow().isoformat(),
            "input_prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "steps": [],
            "final_action": None,
            "total_latency_ms": 0,
            "start_time": time.time()
        }
        return self.current_trace["run_id"]

    def add_step(
        self,
        agent: str,
        action: str,
        tool_calls: List[str] = None,
        confidence: float = None,
        input_text: str = "",
        output_text: str = "",
        metadata: Dict[str, Any] = None
    ) -> TraceStep:
        """Add a step to the current trace."""
        if not self.current_trace:
            return None

        self.step_counter += 1
        step_id = f"step-{self.step_counter}"

        step = TraceStep(
            step_id=step_id,
            agent=agent,
            action=action,
            tool_calls=tool_calls or [],
            confidence=confidence,
            latency_ms=0,
            input_text=input_text[:200],
            output_text=output_text[:200],
            timestamp=datetime.utcnow().isoformat(),
            metadata=metadata or {}
        )

        self.current_trace["steps"].append(asdict(step))
        return step

    def end_trace(self, final_action: str) -> Dict[str, Any]:
        """End the current trace and save it."""
        if not self.current_trace:
            return None

        total_latency = (time.time() - self.current_trace["start_time"]) * 1000
        self.current_trace["final_action"] = final_action
        self.current_trace["total_latency_ms"] = round(total_latency, 2)

        # Save trace
        trace_id = self.current_trace["run_id"]
        trace_file = os.path.join(self.trace_dir, f"{trace_id}.json")
        with open(trace_file, "w") as f:
            json.dump(self.current_trace, f, indent=2)

        self.traces.append(self.current_trace)
        trace = self.current_trace
        self.current_trace = None

        return trace

    def get_traces(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent traces."""
        return self.traces[-limit:]

    def get_trace_summary(self) -> Dict[str, Any]:
        """Get summary of all traces."""
        if not self.traces:
            return {"total": 0, "avg_latency_ms": 0}

        total = len(self.traces)
        avg_latency = sum(t.get("total_latency_ms", 0) for t in self.traces) / total

        actions = {}
        for t in self.traces:
            action = t.get("final_action", "unknown")
            actions[action] = actions.get(action, 0) + 1

        return {
            "total": total,
            "avg_latency_ms": round(avg_latency, 2),
            "action_distribution": actions
        }


tracer = AegisTracer()


@asynccontextmanager
async def trace_step(agent: str, action: str, **kwargs):
    """Context manager for tracing a step."""
    start = time.time()
    step = tracer.add_step(agent=agent, action=action, **kwargs)
    try:
        yield step
    finally:
        if step:
            step.latency_ms = round((time.time() - start) * 1000, 2)
