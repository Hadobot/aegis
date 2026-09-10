// Agent types
export type AutonomyLevel = 1 | 2 | 3 | 4 | 5;

export interface Agent {
  id: string;
  name: string;
  description: string;
  endpoint?: string;
  autonomyLevel: AutonomyLevel;
  status: 'active' | 'inactive' | 'error';
  owner?: string;
  sentryEnabled: boolean;
  shieldEnabled: boolean;
  intelEnabled: boolean;
  auditorEnabled: boolean;
  routerEnabled: boolean;
}

// Security pipeline types
export type ThreatType =
  | 'prompt_injection'
  | 'jailbreak'
  | 'data_exfiltration'
  | 'role_hijacking'
  | 'encoding_bypass'
  | 'multi_turn_attack'
  | 'none';

export type Action = 'allow' | 'flag' | 'block' | 'escalate';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface ThreatDetection {
  detected: boolean;
  type: ThreatType;
  confidence: number;
  combinedRisk: number;
}

export interface GovernanceDecision {
  action: Action;
  reasoning: string;
  violations: string[];
  complianceReferences: string[];
  evidenceChunks: string[];
}

export interface GovernanceEvent {
  id: string;
  requestId: string;
  agentId: string;
  timestamp: Date;
  threat: ThreatDetection;
  decision: GovernanceDecision;
  component: 'sentry' | 'shield' | 'intel' | 'router' | 'auditor';
}

// Security agent types
export interface SecurityAgent {
  id: string;
  name: string;
  role: string;
  description: string;
  status: 'active' | 'inactive';
  eventCount: number;
  latestEvent?: GovernanceEvent;
  riskLevel: RiskLevel;
}

// Dashboard metrics
export interface DashboardMetrics {
  totalRequests: number;
  threatsDetected: number;
  blocked: number;
  flagged: number;
  escalated: number;
  activeAgents: number;
}

// Knowledge document types
export interface KnowledgeDocument {
  id: string;
  name: string;
  category: string;
  lastUpdated: Date;
  status: 'active' | 'deprecated';
  chunks: number;
}

// Combo (multi-agent governance)
export type CommunicationType = 'allowed' | 'conditional' | 'blocked';
export type DataFlowType = 'public' | 'internal' | 'sensitive' | 'pii' | 'restricted';

export interface AgentConnection {
  from: string;
  to: string;
  communication: CommunicationType;
  dataFlow: DataFlowType;
  actions: string[];
  approvalRequired: boolean;
}

export interface Combo {
  id: string;
  name: string;
  description: string;
  agents: string[];
  connections: AgentConnection[];
  status: 'active' | 'inactive';
  createdAt: Date;
}

// Analysis request/response
export interface AnalysisRequest {
  prompt: string;
  response?: string;
}

export interface AnalysisResult {
  requestId: string;
  threat: ThreatDetection;
  decision: GovernanceDecision;
  component: string;
}
