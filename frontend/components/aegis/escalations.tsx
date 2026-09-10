'use client'

import { useEffect, useState } from 'react'
import { Clock3 } from 'lucide-react'
import { escalationService } from '@/src/services'
import type { Escalation } from '@/src/types'
import { EmptyState } from './shared'

const threatLabels: Record<string, string> = {
  prompt_injection: 'Prompt injection',
  jailbreak: 'Jailbreak',
  data_exfiltration: 'Data exfiltration',
  role_hijacking: 'Role hijacking',
  encoding_bypass: 'Encoding bypass',
  multi_turn: 'Multi-turn',
  none: 'No threat',
}

export function EscalationsView() {
  const [escalations, setEscalations] = useState<Escalation[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    escalationService.getEscalations()
      .then(setEscalations)
      .catch(() => setEscalations([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-7">
      <div className="page-intro">
        <div>
          <span className="section-kicker">Human review</span>
          <h2>Escalations</h2>
          <p>Requests flagged for human analyst review.</p>
        </div>
      </div>
      {loading ? (
        <div className="empty-state"><p className="text-[var(--muted)]">Loading escalations...</p></div>
      ) : escalations.length === 0 ? (
        <EmptyState title="No escalations" text="Escalated requests will appear here when the governance pipeline flags them for human review." />
      ) : (
        <div className="audit-table">
          <div className="audit-head">
            <span>Time</span>
            <span>Request</span>
            <span>Threat</span>
            <span>Confidence</span>
            <span>Status</span>
          </div>
          {escalations.map((esc) => (
            <div key={esc.escalation_id} className="audit-row">
              <span>
                <Clock3 size={13} />
                {new Date(esc.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
              <span>
                <b>{esc.request_id}</b>
                <small className="block max-w-[260px] truncate">{esc.prompt}</small>
              </span>
              <span>{threatLabels[esc.threat_type] || esc.threat_type}</span>
              <span>{esc.confidence ? `${Math.round(esc.confidence * 100)}%` : '—'}</span>
              <span>
                <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[10px] font-bold tracking-[.12em] ${
                  esc.status === 'resolved'
                    ? 'text-emerald-300 bg-emerald-400/10 border-emerald-400/20'
                    : 'text-orange-300 bg-orange-400/10 border-orange-400/20'
                }`}>
                  <span className="h-1.5 w-1.5 rounded-full bg-current" />
                  {esc.status === 'resolved' ? 'RESOLVED' : 'PENDING'}
                </span>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
