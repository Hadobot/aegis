'use client'

import { useEffect, useState } from 'react'
import { Shield, Eye, AlertTriangle, CheckCircle, XCircle, RefreshCw } from 'lucide-react'
import { comboMonitorService } from '@/src/services'
import type { ComboViolation, ComboMonitorStatus } from '@/src/types'
import { Button } from './shared'

export function ComboMonitorView() {
  const [status, setStatus] = useState<ComboMonitorStatus | null>(null)
  const [violations, setViolations] = useState<ComboViolation[]>([])
  const [loading, setLoading] = useState(true)
  const [filterCombo, setFilterCombo] = useState<string>('')

  const fetchData = async () => {
    setLoading(true)
    try {
      const [s, v] = await Promise.all([
        comboMonitorService.getMonitorStatus(),
        comboMonitorService.getViolations(filterCombo || undefined),
      ])
      setStatus(s)
      setViolations(v)
    } catch {
      // keep state
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [filterCombo])

  return (
    <div className="space-y-7">
      <div className="page-intro">
        <div>
          <span className="section-kicker">Communication guardrails</span>
          <h2>Combo Monitor</h2>
          <p>Real-time monitoring of agent-to-agent communication across all governed combos.</p>
        </div>
        <Button secondary onClick={fetchData} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
        </Button>
      </div>

      {status && (
        <div className="monitor-stats">
          <div className="stat-card">
            <span className="stat-label">Active Combos</span>
            <span className="stat-value">{status.total_active_combos}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Total Violations</span>
            <span className="stat-value warning">{status.total_violations}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Blocked</span>
            <span className="stat-value danger">{status.total_blocked}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Logged (Allowed)</span>
            <span className="stat-value muted">{status.total_allowed_with_violation}</span>
          </div>
        </div>
      )}

      {status && status.combos.length > 0 && (
        <div className="monitor-combo-list">
          <span className="section-kicker">Monitored combos</span>
          <div className="combo-monitor-grid">
            {status.combos.map((combo) => (
              <button
                key={combo.combo_id}
                onClick={() => setFilterCombo(filterCombo === combo.combo_id ? '' : combo.combo_id)}
                className={`combo-monitor-card ${filterCombo === combo.combo_id ? 'selected' : ''}`}
              >
                <div className="flex items-center gap-2">
                  {combo.monitoring_mode === 'enforce' ? <Shield size={14} /> : <Eye size={14} />}
                  <b>{combo.name}</b>
                </div>
                <div className="combo-monitor-meta">
                  <span>{combo.agent_count} agents</span>
                  <span>{combo.connection_count} connections</span>
                  <span className={combo.violation_count > 0 ? 'text-amber-400' : ''}>{combo.violation_count} violations</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="violations-section">
        <span className="section-kicker">
          Violations {filterCombo && <span className="text-[var(--accent)]">(filtered)</span>}
        </span>
        {violations.length === 0 ? (
          <div className="empty-state">
            <CheckCircle size={24} className="text-emerald-400 mb-2" />
            <p className="text-[var(--muted)]">
              {filterCombo ? 'No violations for this combo.' : 'No violations recorded yet.'}
            </p>
          </div>
        ) : (
          <div className="violations-table">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>From</th>
                  <th>To</th>
                  <th>Combo</th>
                  <th>Data Flow</th>
                  <th>Reason</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {violations.map((v) => (
                  <tr key={v.violation_id}>
                    <td className="text-xs text-[var(--muted)]">{new Date(v.timestamp).toLocaleTimeString()}</td>
                    <td><code>{v.from_agent}</code></td>
                    <td><code>{v.to_agent}</code></td>
                    <td className="text-xs">{v.combo_id}</td>
                    <td><span className="data-flow-badge">{v.data_flow}</span></td>
                    <td className="text-xs max-w-[300px] truncate">{v.reason}</td>
                    <td>
                      {v.blocked ? (
                        <span className="violation-status blocked"><XCircle size={12} /> Blocked</span>
                      ) : (
                        <span className="violation-status logged"><AlertTriangle size={12} /> Logged</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
