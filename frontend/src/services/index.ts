import type {
  Agent,
  SecurityAgent,
  DashboardMetrics,
  KnowledgeDocument,
  GovernanceEvent,
  Combo,
  AnalysisRequest,
  AnalysisResult,
} from '@/src/types';
import * as fixtures from '@/src/fixtures';

// Service layer - initially backed by fixtures, easily replaced with API calls

export const agentService = {
  async getAgents(): Promise<Agent[]> {
    return fixtures.agents;
  },

  async registerAgent(agent: Omit<Agent, 'id'>): Promise<Agent> {
    const id = agent.name.toLowerCase().replace(/\s+/g, '-');
    return { ...agent, id };
  },

  async getAgentById(id: string): Promise<Agent | null> {
    return fixtures.agents.find((a) => a.id === id) || null;
  },
};

export const securityService = {
  async getSecurityAgents(): Promise<SecurityAgent[]> {
    return fixtures.securityAgents;
  },

  async getSecurityAgentById(id: string): Promise<SecurityAgent | null> {
    return fixtures.securityAgents.find((a) => a.id === id) || null;
  },
};

export const dashboardService = {
  async getMetrics(): Promise<DashboardMetrics> {
    return fixtures.dashboardMetrics;
  },
};

export const governanceService = {
  async getGovernanceEvents(): Promise<GovernanceEvent[]> {
    return fixtures.governanceEvents;
  },

  async getRecentEvents(limit: number = 10): Promise<GovernanceEvent[]> {
    return fixtures.governanceEvents.slice(0, limit);
  },

  async getEventsByAgent(agentId: string): Promise<GovernanceEvent[]> {
    return fixtures.governanceEvents.filter((e) => e.agentId === agentId);
  },

  async analyzePrompt(request: AnalysisRequest): Promise<AnalysisResult> {
    // Mock analysis - replace with actual API call to POST /api/v1/analyze
    const isMalicious = request.prompt.toLowerCase().includes('inject');
    return {
      requestId: `req-${Date.now()}`,
      threat: {
        detected: isMalicious,
        type: isMalicious ? 'prompt_injection' : 'none',
        confidence: isMalicious ? 0.85 : 0.05,
        combinedRisk: isMalicious ? 0.82 : 0.1,
      },
      decision: {
        action: isMalicious ? 'block' : 'allow',
        reasoning: isMalicious ? 'Potential injection pattern detected' : 'Request is safe',
        violations: isMalicious ? ['LLM01'] : [],
        complianceReferences: isMalicious ? ['OWASP-LLM01'] : [],
        evidenceChunks: isMalicious ? ['chunk-12'] : [],
      },
      component: 'sentry',
    };
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
    return fixtures.combos;
  },

  async getComboById(id: string): Promise<Combo | null> {
    return fixtures.combos.find((c) => c.id === id) || null;
  },

  async createCombo(combo: Omit<Combo, 'id' | 'createdAt'>): Promise<Combo> {
    const id = `combo-${fixtures.combos.length + 1}`;
    return {
      ...combo,
      id,
      createdAt: new Date(),
    };
  },

  async updateCombo(id: string, combo: Partial<Combo>): Promise<Combo | null> {
    const existing = fixtures.combos.find((c) => c.id === id);
    if (!existing) return null;
    return { ...existing, ...combo };
  },
};

export const healthService = {
  async getHealth() {
    // Will call GET /api/v1/health later
    return { status: 'healthy', agents: fixtures.securityAgents.length };
  },
};
