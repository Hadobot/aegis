'use client'

import { useState } from 'react'
import type { Agent, GovernanceEvent } from '@/src/types'
import type { View } from '@/src/aegis/view-types'
import { AuditView } from './aegis/audit'
import { AgentsView } from './aegis/agents'
import { CombosView } from './aegis/combos'
import { Overview } from './aegis/overview'
import { RegisterView } from './aegis/register'
import { Header, Sidebar } from './aegis/navigation'
import { ActionBadge } from './aegis/shared'

export default function AegisApp() { const [view, setView] = useState<View>('overview'); const [mobileNav, setMobileNav] = useState(false); const [selectedEvent, setSelectedEvent] = useState<GovernanceEvent | null>(null); const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null); const navigate = (next: View) => { setView(next); setMobileNav(false) }; return <div className="app-shell"><div className="app-layout"><Sidebar view={view} onNavigate={navigate} />{mobileNav && <div className="mobile-overlay" onClick={() => setMobileNav(false)}><div onClick={(event) => event.stopPropagation()}><Sidebar view={view} onNavigate={navigate} /></div></div>}<div className="app-content"><Header view={view} onMenu={() => setMobileNav(true)} /><main className="content-wrap">{view === 'overview' && <Overview onNavigate={navigate} />}{view === 'agents' && <AgentsView onNavigate={navigate} onSelect={setSelectedAgent} />}{view === 'register' && <RegisterView onNavigate={navigate} />}{view === 'combos' && <CombosView />}{view === 'audit' && <AuditView onSelect={setSelectedEvent} />}</main></div></div>{selectedEvent && <div className="drawer-backdrop" onClick={() => setSelectedEvent(null)}><aside className="drawer" onClick={(event) => event.stopPropagation()}><button className="drawer-close" onClick={() => setSelectedEvent(null)}>×</button><span className="section-kicker">Governance event</span><h2>{selectedEvent.requestId}</h2><div className="drawer-decision"><ActionBadge action={selectedEvent.decision.action} /><strong>{Math.round(selectedEvent.threat.combinedRisk * 100)}% risk</strong></div><p>{selectedEvent.decision.reasoning}</p></aside></div>}{selectedAgent && <div className="drawer-backdrop" onClick={() => setSelectedAgent(null)}><aside className="drawer" onClick={(event) => event.stopPropagation()}><button className="drawer-close" onClick={() => setSelectedAgent(null)}>×</button><span className="section-kicker">Agent detail</span><h2>{selectedAgent.name}</h2><p>{selectedAgent.description}</p><div className="drawer-list"><span>Owner <b>{selectedAgent.owner}</b></span><span>Autonomy <b>Level {selectedAgent.autonomyLevel}</b></span><span>Context <b>Agent-specific</b></span></div></aside></div>}</div> }
