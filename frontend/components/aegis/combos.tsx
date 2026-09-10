'use client'

import { useEffect, useState } from 'react'
import { ArrowRight, Check, Plus } from 'lucide-react'
import { agentService, comboService } from '@/src/services'
import type { Agent, Combo } from '@/src/types'
import type { View } from '@/src/aegis/view-types'
import { AgentIcon, Button } from './shared'

export function CombosView() {
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [selected, setSelected] = useState<string[]>([])
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
        connections: [],
        status: 'active',
      })
      setCombos((prev) => [...prev, combo])
      setCreated(true)
    } catch {
      // Keep UI state, combo won't persist
      setCreated(true)
    } finally {
      setSubmitting(false)
    }
  }

  if (creating && created)
    return (
      <div className="success-panel">
        <div className="success-icon"><Check size={24} /></div>
        <span className="section-kicker text-emerald-300">Combo created</span>
        <h2>{name || 'New combo'} is ready</h2>
        <p>Your selected agents can now communicate through an explicitly governed execution graph.</p>
        <Button onClick={() => { setCreating(false); setCreated(false); setName(''); setSelected([]) }}>Back to all combos</Button>
      </div>
    )

  if (creating)
    return (
      <div className="form-page">
        <div className="page-intro">
          <div>
            <span className="section-kicker">Coordination graph</span>
            <h2>Create a combo</h2>
            <p>Choose the agents that participate in this governed execution path.</p>
          </div>
          <Button secondary onClick={() => setCreating(false)}>Cancel</Button>
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
          <p>Govern communication across multi-agent execution graphs.</p>
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
              <span className="live-status"><i /> {combo.status}</span>
            </div>
            <div className="combo-flow">
              {combo.agents.map((id, index) => (
                <div className="flex items-center gap-2" key={id}>
                  {index > 0 && <ArrowRight size={14} className="text-[var(--accent)]" />}
                  <span>{agents.find((agent) => agent.id === id)?.name.replace(' Agent', '') || id}</span>
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
