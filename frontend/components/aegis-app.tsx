'use client'

import { useState, useCallback } from 'react'
import type { Agent, GovernanceEvent } from '@/src/types'
import type { View } from '@/src/aegis/view-types'
import { AuditView } from './aegis/audit'
import { AgentsView } from './aegis/agents'
import { CombosView } from './aegis/combos'
import { ComboMonitorView } from './aegis/combo-monitor'
import { Overview } from './aegis/overview'
import { RegisterView } from './aegis/register'
import { EscalationsView } from './aegis/escalations'
import { Header, Sidebar } from './aegis/navigation'
import { ActionBadge } from './aegis/shared'

export default function AegisApp() {
  const [view, setView] = useState<View>('overview')
  const [mobileNav, setMobileNav] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState<GovernanceEvent | null>(null)
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
  const [agentRefreshKey, setAgentRefreshKey] = useState(0)

  const navigate = useCallback((next: View) => {
    setView(next)
    setMobileNav(false)
    if (next === 'agents') setAgentRefreshKey((k) => k + 1)
  }, [])

  return (
    <div className="app-shell">
      <div className="app-layout">
        <Sidebar view={view} onNavigate={navigate} />
        {mobileNav && (
          <div className="mobile-overlay" onClick={() => setMobileNav(false)}>
            <div onClick={(event) => event.stopPropagation()}>
              <Sidebar view={view} onNavigate={navigate} />
            </div>
          </div>
        )}
        <div className="app-content">
          <Header view={view} onMenu={() => setMobileNav(true)} />
          <main className="content-wrap">
            {view === 'overview' && <Overview onNavigate={navigate} />}
            {view === 'agents' && <AgentsView key={agentRefreshKey} onNavigate={navigate} onSelect={setSelectedAgent} />}
            {view === 'register' && <RegisterView onNavigate={navigate} />}
            {view === 'combos' && <CombosView />}
            {view === 'combo-monitor' && <ComboMonitorView />}
            {view === 'audit' && <AuditView onSelect={setSelectedEvent} />}
            {view === 'escalations' && <EscalationsView />}
          </main>
        </div>
      </div>

      {selectedEvent && (
        <div className="drawer-backdrop" onClick={() => setSelectedEvent(null)}>
          <aside className="drawer" onClick={(event) => event.stopPropagation()}>
            <button className="drawer-close" onClick={() => setSelectedEvent(null)}>×</button>
            <span className="section-kicker">Governance event</span>
            <h2>{selectedEvent.requestId}</h2>
            <div className="drawer-decision">
              <ActionBadge action={selectedEvent.decision.action} />
              <strong>{Math.round(selectedEvent.threat.combinedRisk * 100)}% risk</strong>
            </div>
            <p>{selectedEvent.decision.reasoning}</p>
            {selectedEvent.decision.violations.length > 0 && (
              <div className="mt-4">
                <span className="section-kicker">Violations</span>
                <div className="module-tags mt-2">
                  {selectedEvent.decision.violations.map((v) => (
                    <span key={v} className="enabled">{v}</span>
                  ))}
                </div>
              </div>
            )}
            {selectedEvent.decision.complianceReferences.length > 0 && (
              <div className="mt-4">
                <span className="section-kicker">Compliance</span>
                <div className="module-tags mt-2">
                  {selectedEvent.decision.complianceReferences.map((c) => (
                    <span key={c} className="enabled">{c}</span>
                  ))}
                </div>
              </div>
            )}
          </aside>
        </div>
      )}

      {selectedAgent && (
        <div className="drawer-backdrop" onClick={() => setSelectedAgent(null)}>
          <aside className="drawer" onClick={(event) => event.stopPropagation()}>
            <button className="drawer-close" onClick={() => setSelectedAgent(null)}>×</button>
            <span className="section-kicker">Agent detail</span>
            <h2>{selectedAgent.name}</h2>
            <p className="mt-2 text-sm text-[var(--muted)]">{selectedAgent.description}</p>
            <div className="mt-4">
              <span className="section-kicker">Owner</span>
              <p className="mt-1 text-sm">{selectedAgent.owner || 'Not specified'}</p>
            </div>
            <div className="mt-4">
              <span className="section-kicker">Autonomy level</span>
              <p className="mt-1 text-sm">Level {selectedAgent.autonomyLevel}</p>
            </div>
            {selectedAgent.proxyUrl && (
              <div className="mt-4">
                <span className="section-kicker">Proxy URL</span>
                <div className="proxy-url-display drawer-proxy">
                  <code>{selectedAgent.proxyUrl}</code>
                </div>
                {selectedAgent.proxyPort && (
                  <p className="mt-1 text-xs text-[var(--muted)]">Port: {selectedAgent.proxyPort}</p>
                )}
              </div>
            )}
            <div className="mt-4">
              <span className="section-kicker">Governance modules</span>
              <div className="module-tags mt-2">
                {(['Sentry', 'Shield', 'Intel', 'Auditor', 'Router'] as const).map((label) => {
                  const key = `${label.toLowerCase()}Enabled` as keyof Agent
                  const enabled = selectedAgent[key]
                  return (
                    <span key={label} className={enabled ? 'enabled' : ''}>
                      {enabled ? '●' : '○'} {label}
                    </span>
                  )
                })}
              </div>
            </div>
          </aside>
        </div>
      )}
    </div>
  )
}
