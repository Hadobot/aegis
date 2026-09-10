export type View = 'overview' | 'agents' | 'register' | 'audit' | 'combos'

export type GovernanceConfig = {
  sentry: boolean
  shield: boolean
  intel: boolean
  auditor: boolean
  router: boolean
}

export const emptyGovernance: GovernanceConfig = {
  sentry: false,
  shield: false,
  intel: false,
  auditor: false,
  router: false,
}

export const viewTitles: Record<View, string> = {
  overview: 'Overview',
  agents: 'Registered Agents',
  register: 'Register Agent',
  audit: 'Audit Logs',
  combos: 'Agent Combos',
}

export const governanceModules = [
  ['sentry', 'Sentry', 'Threat detection and prompt inspection'],
  ['shield', 'Shield', 'Policy enforcement and boundary protection'],
  ['intel', 'Intel', 'Contextual risk and threat intelligence'],
  ['auditor', 'Auditor', 'Decision evidence and compliance trail'],
  ['router', 'Router', 'Action routing and escalation control'],
] as const
