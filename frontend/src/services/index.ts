import type {
  Agent,
  SecurityAgent,
  DashboardMetrics,
  KnowledgeDocument,
  GovernanceEvent,
  Combo,
  AnalysisRequest,
  AnalysisResult,
  BackendHealthResponse,
  BackendAnalysisResponse,
  BackendAuditLog,
  BackendMetrics,
  BackendAgentDetail,
  Escalation,
  ComboViolation,
  ComboMonitorStatus,
  AgentDiscovery,
} from '@/src/types';
import * as fixtures from '@/src/fixtures';
import { apiFetch, ApiError } from '@/src/lib/api';

export const agentService = {
  async getAgents(): Promise<Agent[]> {
    const data = await apiFetch<{ agents: Array<{
      agent_id: string;
      name: string;
      description: string;
      autonomy_level: number;
      owner: string;
      allowed_tools: string[];
      proxy_url?: string;
      proxy_port?: number;
    }> }>('/api/v1/agents');
    return data.agents.map((a) => ({
      id: a.agent_id,
      name: a.name,
      description: a.description,
      autonomyLevel: a.autonomy_level as Agent['autonomyLevel'],
      status: 'active' as const,
      owner: a.owner || '',
      sentryEnabled: a.allowed_tools.includes('sentry'),
      shieldEnabled: a.allowed_tools.includes('shield'),
      intelEnabled: a.allowed_tools.includes('intel'),
      auditorEnabled: a.allowed_tools.includes('auditor'),
      routerEnabled: a.allowed_tools.includes('router'),
      proxyUrl: a.proxy_url || '',
      proxyPort: a.proxy_port || 0,
    }));
  },

  async registerAgent(agent: Omit<Agent, 'id'> & { context?: string }): Promise<Agent & { proxyUrl: string }> {
    const id = agent.name.toLowerCase().replace(/\s+/g, '-');
    const data = await apiFetch<{
      registered: boolean;
      agent_id: string;
      proxy_url: string;
      proxy_port: number;
    }>('/api/v1/agents/register', {
      method: 'POST',
      body: JSON.stringify({
        agent_id: id,
        name: agent.name,
        description: agent.description,
        autonomy_level: agent.autonomyLevel,
        allowed_tools: [
          ...(agent.sentryEnabled ? ['sentry'] : []),
          ...(agent.shieldEnabled ? ['shield'] : []),
          ...(agent.intelEnabled ? ['intel'] : []),
          ...(agent.auditorEnabled ? ['auditor'] : []),
          ...(agent.routerEnabled ? ['router'] : []),
        ],
        allowed_communications: [],
        owner: agent.owner || '',
        endpoint: agent.endpoint || '',
        context: agent.context || '',
      }),
    });
    return { ...agent, id, proxyUrl: data.proxy_url };
  },

  async getAgentById(id: string): Promise<BackendAgentDetail | null> {
    try {
      return await apiFetch<BackendAgentDetail>(`/api/v1/agents/${id}`);
    } catch {
      return null;
    }
  },

  async discoverAgents(): Promise<AgentDiscovery[]> {
    try {
      const data = await apiFetch<{ agents: AgentDiscovery[] }>('/api/v1/agents/discover');
      return data.agents;
    } catch {
      return [];
    }
  },

  async discoverAgent(id: string): Promise<AgentDiscovery | null> {
    try {
      return await apiFetch<AgentDiscovery>(`/api/v1/agents/discover/${id}`);
    } catch {
      return null;
    }
  },
};

export const securityService = {
  async getSecurityAgents(): Promise<SecurityAgent[]> {
    try {
      const data = await apiFetch<{ security_agents: SecurityAgent[] }>('/api/v1/security-agents');
      return data.security_agents;
    } catch {
      return fixtures.securityAgents;
    }
  },

  async getSecurityAgentById(id: string): Promise<SecurityAgent | null> {
    const agents = await this.getSecurityAgents();
    return agents.find((a) => a.id === id) || null;
  },
};

export const dashboardService = {
  async getMetrics(): Promise<DashboardMetrics> {
    try {
      const data = await apiFetch<BackendMetrics>('/api/v1/metrics');
      return {
        totalRequests: data.total_requests,
        threatsDetected: data.threats_detected,
        blocked: data.blocked,
        flagged: data.flagged,
        escalated: data.escalated,
        activeAgents: data.active_agents,
      };
    } catch {
      return fixtures.dashboardMetrics;
    }
  },
};

export const governanceService = {
  async getGovernanceEvents(): Promise<GovernanceEvent[]> {
    const data = await apiFetch<{ logs: BackendAuditLog[]; total: number }>(
      '/api/v1/audit/logs?limit=100'
    );
    return data.logs.map(mapAuditLogToEvent);
  },

  async getRecentEvents(limit: number = 10): Promise<GovernanceEvent[]> {
    const events = await this.getGovernanceEvents();
    return events.slice(0, limit);
  },

  async getEventsByAgent(agentId: string): Promise<GovernanceEvent[]> {
    const events = await this.getGovernanceEvents();
    return events.filter((e) => e.agentId === agentId);
  },

  async analyzePrompt(request: AnalysisRequest): Promise<AnalysisResult> {
    const data = await apiFetch<BackendAnalysisResponse>('/api/v1/analyze', {
      method: 'POST',
      body: JSON.stringify({
        prompt: request.prompt,
        response: request.response,
      }),
    });
    return {
      requestId: data.request_id,
      threat: {
        detected: data.threat_detected,
        type: data.threat_type,
        confidence: data.confidence_score,
        combinedRisk: data.combined_risk,
      },
      decision: {
        action: data.action,
        reasoning: data.reasoning,
        violations: data.violations,
        complianceReferences: data.compliance_refs,
        evidenceChunks: data.evidence_chunks,
      },
      component: 'sentry',
    };
  },
};

export const escalationService = {
  async getEscalations(): Promise<Escalation[]> {
    const data = await apiFetch<{ escalations: Escalation[]; total: number }>(
      '/api/v1/escalations?limit=100'
    );
    return data.escalations;
  },
};

export const knowledgeService = {
  async getKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
    return fixtures.knowledgeDocuments;
  },

  async getDocumentById(id: string): Promise<KnowledgeDocument | null> {
    return fixtures.knowledgeDocuments.find((d) => d.id === id) || null;
  },
};

export const comboService = {
  async getCombos(): Promise<Combo[]> {
    try {
      const data = await apiFetch<{ combos: Array<{
        id: string;
        name: string;
        description: string;
        agents: string[];
        connections: unknown[];
        monitoring_mode?: string;
        status: string;
        createdAt: string;
      }> }>('/api/v1/combos');
      return data.combos.map((c) => ({
        id: c.id,
        name: c.name,
        description: c.description,
        agents: c.agents,
        connections: c.connections as Combo['connections'],
        monitoringMode: (c.monitoring_mode || 'enforce') as Combo['monitoringMode'],
        status: c.status as Combo['status'],
        createdAt: new Date(c.createdAt),
      }));
    } catch {
      return [];
    }
  },

  async getComboById(id: string): Promise<Combo | null> {
    try {
      const c = await apiFetch<{
        id: string;
        name: string;
        description: string;
        agents: string[];
        connections: unknown[];
        monitoring_mode?: string;
        status: string;
        createdAt: string;
      }>(`/api/v1/combos/${id}`);
      return {
        id: c.id,
        name: c.name,
        description: c.description,
        agents: c.agents,
        connections: c.connections as Combo['connections'],
        monitoringMode: (c.monitoring_mode || 'enforce') as Combo['monitoringMode'],
        status: c.status as Combo['status'],
        createdAt: new Date(c.createdAt),
      };
    } catch {
      return null;
    }
  },

  async createCombo(
    combo: Omit<Combo, 'id' | 'createdAt'>
  ): Promise<Combo> {
    const data = await apiFetch<{
      id: string;
      name: string;
      description: string;
      agents: string[];
      connections: unknown[];
      monitoring_mode?: string;
      status: string;
      createdAt: string;
    }>('/api/v1/combos', {
      method: 'POST',
      body: JSON.stringify({
        name: combo.name,
        description: combo.description,
        agents: combo.agents,
        connections: combo.connections,
        monitoring_mode: combo.monitoringMode || 'enforce',
      }),
    });
    return {
      id: data.id,
      name: data.name,
      description: data.description,
      agents: data.agents,
      connections: data.connections as Combo['connections'],
      monitoringMode: (data.monitoring_mode || 'enforce') as Combo['monitoringMode'],
      status: data.status as Combo['status'],
      createdAt: new Date(data.createdAt),
    };
  },

  async updateCombo(id: string, combo: Partial<Combo>): Promise<Combo | null> {
    try {
      const data = await apiFetch<{
        id: string;
        name: string;
        description: string;
        agents: string[];
        connections: unknown[];
        monitoring_mode?: string;
        status: string;
        createdAt: string;
      }>(`/api/v1/combos/${id}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: combo.name,
          description: combo.description,
          agents: combo.agents,
          connections: combo.connections,
          monitoring_mode: combo.monitoringMode,
        }),
      });
      return {
        id: data.id,
        name: data.name,
        description: data.description,
        agents: data.agents,
        connections: data.connections as Combo['connections'],
        monitoringMode: (data.monitoring_mode || 'enforce') as Combo['monitoringMode'],
        status: data.status as Combo['status'],
        createdAt: new Date(data.createdAt),
      };
    } catch {
      return null;
    }
  },

  async deleteCombo(id: string): Promise<boolean> {
    try {
      await apiFetch(`/api/v1/combos/${id}`, { method: 'DELETE' });
      return true;
    } catch {
      return false;
    }
  },
};

export const comboMonitorService = {
  async getViolations(comboId?: string): Promise<ComboViolation[]> {
    try {
      const query = comboId ? `?combo_id=${comboId}` : '';
      const data = await apiFetch<{ violations: ComboViolation[]; total: number }>(
        `/api/v1/combo-monitor/violations${query}`
      );
      return data.violations;
    } catch {
      return [];
    }
  },

  async getMonitorStatus(): Promise<ComboMonitorStatus | null> {
    try {
      return await apiFetch<ComboMonitorStatus>('/api/v1/combo-monitor/status');
    } catch {
      return null;
    }
  },

  async getActiveCombos(): Promise<ComboMonitorStatus['combos']> {
    try {
      const data = await apiFetch<{ combos: ComboMonitorStatus['combos'] }>('/api/v1/combo-monitor/active');
      return data.combos;
    } catch {
      return [];
    }
  },

  async validateCommunication(payload: {
    from_agent_id: string;
    to_agent_id: string;
    combo_id: string;
    data_flow?: string;
    action?: string;
  }): Promise<{
    allowed: boolean;
    reason: string;
    monitoring_mode: string;
    violated_rules: string[];
  }> {
    try {
      return await apiFetch('/api/v1/combo-monitor/validate', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch {
      return { allowed: false, reason: 'Monitor service unavailable', monitoring_mode: 'enforce', violated_rules: [] };
    }
  },
};

export const proxyService = {
  async getProxies(): Promise<Record<string, { agent_id: string; port: number; proxy_url: string; status: string }>> {
    try {
      const data = await apiFetch<{ proxies: Record<string, { agent_id: string; port: number; proxy_url: string; status: string }> }>('/api/v1/proxies');
      return data.proxies;
    } catch {
      return {};
    }
  },

  async restartProxy(agentId: string): Promise<{ agent_id: string; port: number; proxy_url: string; status: string } | null> {
    try {
      return await apiFetch(`/api/v1/proxies/${agentId}/restart`, { method: 'POST' });
    } catch {
      return null;
    }
  },
};

export const healthService = {
  async getHealth(): Promise<BackendHealthResponse> {
    return apiFetch<BackendHealthResponse>('/api/v1/health');
  },
};

function mapAuditLogToEvent(log: BackendAuditLog): GovernanceEvent {
  const sentry = log.sentry_result || {};
  const router = log.router_result || {};
  const threatType = (sentry.threat_type as GovernanceEvent['threat']['type']) || 'none';

  return {
    id: log.log_id,
    requestId: log.request_id,
    agentId: log.agent_id,
    timestamp: new Date(log.timestamp),
    threat: {
      detected: Boolean(sentry.threat_detected),
      type: threatType,
      confidence: Number(sentry.confidence_score) || 0,
      combinedRisk: Number(router.combined_risk) || 0,
    },
    decision: {
      action: (log.action_taken as GovernanceEvent['decision']['action']) || 'allow',
      reasoning: (router.reasoning as string) || '',
      violations: (log.shield_result?.violations as string[]) || [],
      complianceReferences: log.compliance_refs || [],
      evidenceChunks: [],
    },
    component: 'sentry',
  };
}
