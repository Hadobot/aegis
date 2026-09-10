'use client'

import { useEffect, useMemo, useState } from 'react'
import { Clock3, Filter } from 'lucide-react'
import { governanceService } from '@/src/services'
import type { GovernanceEvent } from '@/src/types'
import { ActionBadge, EmptyState } from './shared'

const labels: Record<string, string> = { prompt_injection: 'Prompt injection', jailbreak: 'Jailbreak', data_exfiltration: 'Data exfiltration', role_hijacking: 'Role hijacking', encoding_bypass: 'Encoding bypass', multi_turn: 'Multi-turn attack', none: 'No threat' }

export function AuditView({ onSelect }: { onSelect: (event: GovernanceEvent) => void }) {
  const [filter, setFilter] = useState('all')
  const [events, setEvents] = useState<GovernanceEvent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    governanceService.getGovernanceEvents()
      .then(setEvents)
      .catch(() => setEvents([]))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(
    () => filter === 'all' ? events : events.filter((event) => event.decision.action === filter),
    [filter, events]
  )

  return (
    <div className="space-y-7">
      <div className="page-intro">
        <div>
          <span className="section-kicker">Decision evidence</span>
          <h2>Audit logs</h2>
          <p>Complete decision history across your governed agents.</p>
        </div>
        <div className="filter-control">
          <Filter size={14} />
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">All actions</option>
            <option value="allow">Allow</option>
            <option value="flag">Flag</option>
            <option value="block">Block</option>
            <option value="escalate">Escalate</option>
          </select>
        </div>
      </div>
      {loading ? (
        <div className="empty-state"><p className="text-[var(--muted)]">Loading audit logs...</p></div>
      ) : filtered.length === 0 ? (
        <EmptyState title="No audit events" text="Events will appear here as requests are processed through the governance pipeline." />
      ) : (
        <div className="audit-table">
          <div className="audit-head">
            <span>Timestamp</span>
            <span>Event</span>
            <span>Risk</span>
            <span>Decision</span>
          </div>
          {filtered.map((event) => (
            <button key={event.id} onClick={() => onSelect(event)} className="audit-row">
              <span>
                <Clock3 size={13} />
                {event.timestamp instanceof Date
                  ? event.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                  : new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
              <span>
                <b>{labels[event.threat.type] || event.threat.type}</b>
                <small>{event.requestId}</small>
              </span>
              <span>{Math.round(event.threat.combinedRisk * 100)}%</span>
              <span><ActionBadge action={event.decision.action} /></span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
