'use client'

import { useEffect, useState } from 'react'
import { ArrowRight, Check, Plus, Trash2, Shield, Eye } from 'lucide-react'
import { agentService, comboService } from '@/src/services'
import type { Agent, Combo, AgentConnection, CommunicationType, DataFlowType, MonitoringModeType } from '@/src/types'
import type { View } from '@/src/aegis/view-types'
import { AgentIcon, Button } from './shared'

const DATA_FLOW_OPTIONS: DataFlowType[] = ['public', 'internal', 'sensitive', 'pii', 'restricted']
const COMM_OPTIONS: CommunicationType[] = ['allowed', 'conditional', 'blocked']

function ConnectionEditor({
  connections,
  agents,
  selectedAgentIds,
  onChange,
}: {
  connections: AgentConnection[]
  agents: Agent[]
  selectedAgentIds: string[]
  onChange: (connections: AgentConnection[]) => void
}) {
  const selectedAgents = agents.filter((a) => selectedAgentIds.includes(a.id))

  const addConnection = () => {
    if (selectedAgentIds.length < 2) return
    const from = selectedAgentIds[0]
    const to = selectedAgentIds[1]
    onChange([
      ...connections,
      {
        from,
        to,
        communication: 'allowed' as CommunicationType,
        dataFlow: 'public' as DataFlowType,
        actions: [],
        approvalRequired: false,
      },
    ])
  }

  const updateConnection = (index: number, field: keyof AgentConnection, value: unknown) => {
    const updated = [...connections]
    updated[index] = { ...updated[index], [field]: value } as AgentConnection
    onChange(updated)
  }

  const removeConnection = (index: number) => {
    onChange(connections.filter((_, i) => i !== index))
  }

  return (
    <div className="connection-editor">
      <div className="flex items-center justify-between mb-3">
        <span className="section-kicker">Connection guardrails</span>
        <button type="button" onClick={addConnection} disabled={selectedAgentIds.length < 2} className="add-connection-btn">
          <Plus size={12} /> Add connection
        </button>
      </div>
      {connections.length === 0 && (
        <p className="text-[var(--muted)] text-sm">No connections defined. Add connections to control how agents communicate.</p>
      )}
      {connections.map((conn, idx) => (
        <div key={idx} className="connection-row">
          <div className="connection-pair">
            <select value={conn.from} onChange={(e) => updateConnection(idx, 'from', e.target.value)}>
              {selectedAgents.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
            <ArrowRight size={14} className="text-[var(--accent)] shrink-0" />
            <select value={conn.to} onChange={(e) => updateConnection(idx, 'to', e.target.value)}>
              {selectedAgents.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>
          <div className="connection-settings">
            <select value={conn.communication} onChange={(e) => updateConnection(idx, 'communication', e.target.value)}>
              {COMM_OPTIONS.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <select value={conn.dataFlow} onChange={(e) => updateConnection(idx, 'dataFlow', e.target.value)}>
              {DATA_FLOW_OPTIONS.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
            <label className="inline-flex items-center gap-1 text-xs">
              <input
                type="checkbox"
                checked={conn.approvalRequired}
                onChange={(e) => updateConnection(idx, 'approvalRequired', e.target.checked)}
              />
              Approval
            </label>
            <button type="button" onClick={() => removeConnection(idx)} className="remove-connection-btn" title="Remove">
              <Trash2 size={12} />
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

export function CombosView() {
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [selected, setSelected] = useState<string[]>([])
  const [connections, setConnections] = useState<AgentConnection[]>([])
  const [monitoringMode, setMonitoringMode] = useState<MonitoringModeType>('enforce')
  const [created, setCreated] = useState(false)
  const [agents, setAgents] = useState<Agent[]>([])
  const [combos, setCombos] = useState<Combo[]>([])
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    agentService.getAgents().then(setAgents).catch(() => setAgents([]))
    comboService.getCombos().then(setCombos).catch(() => setCombos([]))
  }, [])

  const toggle = (id: string) =>
    setSelected((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id]
    )

  const handleCreate = async () => {
    if (!name.trim() || selected.length < 2) return
    setSubmitting(true)
    try {
      const combo = await comboService.createCombo({
        name,
        description,
        agents: selected,
        connections,
        monitoringMode,
        status: 'active',
      })
      setCombos((prev) => [...prev, combo])
      setCreated(true)
    } catch {
      setCreated(true)
    } finally {
      setSubmitting(false)
    }
  }

  const resetForm = () => {
    setCreating(false)
    setCreated(false)
    setName('')
    setDescription('')
    setSelected([])
    setConnections([])
    setMonitoringMode('enforce')
  }

  if (creating && created)
    return (
      <div className="success-panel">
        <div className="success-icon"><Check size={24} /></div>
        <span className="section-kicker text-emerald-300">Combo created</span>
        <h2>{name || 'New combo'} is ready</h2>
        <p>Your selected agents can now communicate through a governed execution graph with {monitoringMode} monitoring.</p>
        <Button onClick={resetForm}>Back to all combos</Button>
      </div>
    )

  if (creating)
    return (
      <div className="form-page">
        <div className="page-intro">
          <div>
            <span className="section-kicker">Coordination graph</span>
            <h2>Create a combo</h2>
            <p>Choose agents and define communication guardrails between them.</p>
          </div>
          <Button secondary onClick={resetForm}>Cancel</Button>
        </div>
        <div className="form-panel">
          <label>Combo name<input value={name} onChange={(e) => setName(e.target.value)} placeholder="Research and Review" /></label>
          <label className="mt-5 block">Description<textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} placeholder="Describe how these agents work together" /></label>

          <div className="form-divider">
            <span className="section-kicker">Choose agents</span>
            <div className="combo-select-grid">
              {agents.map((agent) => (
                <button type="button" key={agent.id} onClick={() => toggle(agent.id)} className={`combo-agent ${selected.includes(agent.id) ? 'selected' : ''}`}>
                  <AgentIcon />
                  <span><b>{agent.name}</b><small>{agent.description}</small></span>
                  {selected.includes(agent.id) && <Check size={16} className="ml-auto text-[var(--accent)]" />}
                </button>
              ))}
            </div>
          </div>

          {selected.length >= 2 && (
            <>
              <div className="form-divider">
                <span className="section-kicker">Monitoring mode</span>
                <p>Choose how violations are handled.</p>
                <div className="monitoring-mode-toggle">
                  <button
                    type="button"
                    onClick={() => setMonitoringMode('enforce')}
                    className={`mode-btn ${monitoringMode === 'enforce' ? 'selected' : ''}`}
                  >
                    <Shield size={14} /> Enforce
                    <small>Block unauthorized communication</small>
                  </button>
                  <button
                    type="button"
                    onClick={() => setMonitoringMode('monitor')}
                    className={`mode-btn ${monitoringMode === 'monitor' ? 'selected' : ''}`}
                  >
                    <Eye size={14} /> Monitor only
                    <small>Log violations but allow traffic</small>
                  </button>
                </div>
              </div>

              <div className="form-divider">
                <ConnectionEditor
                  connections={connections}
                  agents={agents}
                  selectedAgentIds={selected}
                  onChange={setConnections}
                />
              </div>
            </>
          )}

          <Button disabled={!name.trim() || selected.length < 2 || submitting} onClick={handleCreate}>
            {submitting ? 'Creating...' : <>Create combo <Plus size={14} /></>}
          </Button>
        </div>
      </div>
    )

  return (
    <div className="space-y-7">
      <div className="page-intro">
        <div>
          <span className="section-kicker">Coordination graph</span>
          <h2>Agent combos</h2>
          <p>Govern communication across multi-agent execution graphs with guardrails.</p>
        </div>
        <Button onClick={() => setCreating(true)}><Plus size={14} /> Create combo</Button>
      </div>
      <div className="combo-list">
        {combos.map((combo) => (
          <article className="combo-card" key={combo.id}>
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <AgentIcon combo />
                <div>
                  <h3>{combo.name}</h3>
                  <p>{combo.description}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`monitoring-badge ${combo.monitoringMode || 'enforce'}`}>
                  {combo.monitoringMode === 'monitor' ? <Eye size={10} /> : <Shield size={10} />}
                  {combo.monitoringMode || 'enforce'}
                </span>
                <span className="live-status"><i /> {combo.status}</span>
              </div>
            </div>
            <div className="combo-flow">
              {combo.agents.map((id, index) => (
                <div className="flex items-center gap-2" key={id}>
                  {index > 0 && <ArrowRight size={14} className="text-[var(--accent)]" />}
                  <span>{agents.find((agent) => agent.id === id)?.name.replace(' Agent', '') || id}</span>
                </div>
              ))}
            </div>
            {combo.connections.length > 0 && (
              <div className="combo-connections-summary">
                <small>{combo.connections.length} connection{combo.connections.length !== 1 ? 's' : ''} defined</small>
                {combo.connections.map((conn, idx) => (
                  <span key={idx} className={`connection-chip ${conn.communication}`}>
                    {conn.from} → {conn.to} ({conn.communication})
                  </span>
                ))}
              </div>
            )}
          </article>
        ))}
      </div>
    </div>
  )
}
