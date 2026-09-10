from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid


class ThreatType(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    DATA_EXFILTRATION = "data_exfiltration"
    ROLE_HIJACKING = "role_hijacking"
    ENCODING_BYPASS = "encoding_bypass"
    MULTI_TURN = "multi_turn"
    NONE = "none"


class ActionType(str, Enum):
    ALLOW = "allow"
    FLAG = "flag"
    BLOCK = "block"
    ESCALATE = "escalate"


class AgentAutonomyLevel(int, Enum):
    OBSERVE = 1
    ADVISE = 2
    ACT_APPROVE = 3
    ACT_AUTO = 4


class AnalysisRequest(BaseModel):
    prompt: str
    response: Optional[str] = None
    agent_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class AnalysisResponse(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    threat_detected: bool
    threat_type: ThreatType
    confidence_score: float
    combined_risk: float
    action: ActionType
    violations: List[str]
    compliance_refs: List[str]
    evidence_chunks: List[str]
    reasoning: str
    requires_human_review: bool


class AuditLog(BaseModel):
    log_id: str = Field(default_factory=lambda: f"audit-{uuid.uuid4()}")
    request_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    agent_id: str
    action: str
    threat_type: ThreatType
    confidence: float
    decision: ActionType
    compliance_refs: List[str]
    reasoning: str


class AgentRegistration(BaseModel):
    agent_id: str
    name: str
    description: str
    autonomy_level: AgentAutonomyLevel
    allowed_tools: List[str]
    allowed_communications: List[str]
    owner: str
    endpoint: Optional[str] = ""
    context: Optional[str] = ""


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, str]
