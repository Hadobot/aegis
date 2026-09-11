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


class AgentRegistrationResponse(BaseModel):
    registered: bool
    agent_id: str
    proxy_url: str
    proxy_port: int


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, str]


class CommunicationType(str, Enum):
    ALLOWED = "allowed"
    CONDITIONAL = "conditional"
    BLOCKED = "blocked"


class DataFlowType(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    PII = "pii"
    RESTRICTED = "restricted"


class MonitoringMode(str, Enum):
    ENFORCE = "enforce"
    MONITOR = "monitor"


class AgentConnectionDefinition(BaseModel):
    from_agent: str
    to_agent: str
    communication: CommunicationType = CommunicationType.ALLOWED
    data_flow: DataFlowType = DataFlowType.PUBLIC
    actions: List[str] = []
    approval_required: bool = False


class ComboMonitorRequest(BaseModel):
    from_agent_id: str
    to_agent_id: str
    combo_id: str
    data_flow: Optional[DataFlowType] = DataFlowType.PUBLIC
    action: Optional[str] = ""


class ComboViolation(BaseModel):
    violation_id: str = Field(default_factory=lambda: f"violation-{uuid.uuid4()}")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    from_agent: str
    to_agent: str
    combo_id: str
    reason: str
    blocked: bool
    connection_ref: Optional[Dict[str, Any]] = None
    data_flow: Optional[str] = None
    action: Optional[str] = None


class ComboWithMonitoring(BaseModel):
    id: str
    name: str
    description: str
    agents: List[str]
    connections: List[AgentConnectionDefinition]
    monitoring_mode: MonitoringMode = MonitoringMode.ENFORCE
    status: str = "active"
    created_at: Optional[str] = None
