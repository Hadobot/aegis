'use client'

import { useEffect, useState } from 'react'
import { Plus, Copy, Check } from 'lucide-react'
import { agentService } from '@/src/services'
import type { Agent } from '@/src/types'
import type { View } from '@/src/aegis/view-types'
import { AgentIcon, Button, EmptyState } from './shared'

export function AgentsView({ onNavigate, onSelect }: { onNavigate: (view: View) => void; onSelect: (agent: Agent) => void }) {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  useEffect(() => {
    agentService.getAgents()
      .then(setAgents)
      .catch(() => setAgents([]))
      .finally(() => setLoading(false))
  }, [])

  const copyProxyUrl = (url: string, agentId: string) => {
    navigator.clipboard.writeText(url)
    setCopiedId(agentId)
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <div className="space-y-7">
      <div className="page-intro">
        <div>
          <span className="section-kicker">Runtime registry</span>
          <h2>Your governed agents</h2>
          <p>Each agent has an independent context, unique proxy, and opt-in governance configuration.</p>
        </div>
        <Button onClick={() => onNavigate('register')}><Plus size={14} /> Register agent</Button>
      </div>
      {loading ? (
        <div className="empty-state"><p className="text-[var(--muted)]">Loading agents...</p></div>
      ) : agents.length === 0 ? (
        <EmptyState title="No agents registered" text="Register your first agent to start governing its interactions with the Aegis pipeline." />
      ) : (
        <div className="agent-grid">
          {agents.map((agent) => (
            <button key={agent.id} onClick={() => onSelect(agent)} className="agent-card">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <AgentIcon />
                  <div>
                    <h3>{agent.name}</h3>
                    <p>{agent.owner || 'No owner'}</p>
                  </div>
                </div>
                <span className="live-status"><i /> {agent.status}</span>
              </div>
              <p className="agent-description">{agent.description}</p>
              {agent.proxyUrl && (
                <div className="proxy-url-row" onClick={(e) => { e.stopPropagation(); copyProxyUrl(agent.proxyUrl!, agent.id) }}>
                  <small>Proxy</small>
                  <code>{agent.proxyUrl}</code>
                  {copiedId === agent.id ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} className="text-[var(--muted)]" />}
                </div>
              )}
              <div className="agent-meta">
                <span><small>Autonomy</small><b>L{agent.autonomyLevel}</b></span>
                {agent.proxyPort ? <span><small>Port</small><b>{agent.proxyPort}</b></span> : null}
              </div>
              <div className="module-tags">
                {(['Sentry', 'Shield', 'Intel', 'Auditor', 'Router'] as const).map((label) => {
                  const key = `${label.toLowerCase()}Enabled` as keyof Agent
                  const enabled = agent[key]
                  return (
                    <span key={label} className={enabled ? 'enabled' : ''}>
                      {enabled ? '●' : '○'} {label}
                    </span>
                  )
                })}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
