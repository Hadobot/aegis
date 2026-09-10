'use client'

import { useState } from 'react'
import { Check, Plus } from 'lucide-react'
import type { View, GovernanceConfig } from '@/src/aegis/view-types'
import type { Agent } from '@/src/types'
import { emptyGovernance, governanceModules } from '@/src/aegis/view-types'
import { agentService } from '@/src/services'
import { Button } from './shared'

export function RegisterView({ onNavigate }: { onNavigate: (view: View) => void }) {
  const [name, setName] = useState('')
  const [endpoint, setEndpoint] = useState('')
  const [description, setDescription] = useState('')
  const [owner, setOwner] = useState('')
  const [context, setContext] = useState('')
  const [autonomyLevel, setAutonomyLevel] = useState<Agent['autonomyLevel']>(2)
  const [governance, setGovernance] = useState<GovernanceConfig>(emptyGovernance)
  const [registered, setRegistered] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const toggle = (key: keyof GovernanceConfig) =>
    setGovernance((current) => ({ ...current, [key]: !current[key] }))

  const handleRegister = async () => {
    if (!name.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      await agentService.registerAgent({
        name,
        endpoint,
        description,
        owner,
        autonomyLevel,
        status: 'active',
        sentryEnabled: governance.sentry,
        shieldEnabled: governance.shield,
        intelEnabled: governance.intel,
        auditorEnabled: governance.auditor,
        routerEnabled: governance.router,
        context,
      } as Omit<Agent, 'id'> & { context: string })
      setRegistered(true)
    } catch (e) {
      setError('Registration failed. Make sure the backend is running.')
    } finally {
      setSubmitting(false)
    }
  }

  if (registered) {
    return (
      <div className="success-panel">
        <div className="success-icon"><Check size={24} /></div>
        <span className="section-kicker text-emerald-300">Registration complete</span>
        <h2>{name} is now registered</h2>
        <p>Its context and selected governance modules are ready for runtime use.</p>
        <Button onClick={() => onNavigate('agents')}>View registered agents</Button>
      </div>
    )
  }

  return (
    <div className="form-page">
      <div className="page-intro">
        <div>
          <span className="section-kicker">New runtime connection</span>
          <h2>Register an agent</h2>
          <p>Define this agent&apos;s identity, context, and governance modules.</p>
        </div>
      </div>
      <div className="form-panel">
        <div className="form-grid">
          <label>
            Agent name
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Customer Research Agent" />
          </label>
          <label>
            Agent endpoint
            <input value={endpoint} onChange={(e) => setEndpoint(e.target.value)} placeholder="https://agent.example.com" />
          </label>
          <label className="wide">
            Description
            <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What does this agent do?" />
          </label>
          <label>
            Owner / team
            <input value={owner} onChange={(e) => setOwner(e.target.value)} placeholder="Operations team" />
          </label>
          <label>
            Autonomy level
            <select value={autonomyLevel} onChange={(e) => setAutonomyLevel(Number(e.target.value) as Agent['autonomyLevel'])}>
              <option value={1}>Level 1 · Observe</option>
              <option value={2}>Level 2 · Assisted</option>
              <option value={3}>Level 3 · Conditional</option>
              <option value={4}>Level 4 · Autonomous</option>
            </select>
          </label>
          <label className="wide">
            Agent-specific context
            <textarea value={context} onChange={(e) => setContext(e.target.value)} rows={4} placeholder="Describe this agent's purpose, data boundaries, approved behaviors, and special instructions." />
            <small>This context belongs only to this agent and is used as governance evidence.</small>
          </label>
        </div>
        <div className="form-divider">
          <span className="section-kicker">Choose governance modules</span>
          <p>Nothing is enabled by default. Select only the controls this agent needs.</p>
          <div className="governance-grid">
            {governanceModules.map(([key, label, text]) => (
              <button type="button" key={key} onClick={() => toggle(key)} className={`governance-option ${governance[key] ? 'selected' : ''}`}>
                <span className="check-box">{governance[key] && <Check size={13} />}</span>
                <span><b>{label}</b><small>{text}</small></span>
              </button>
            ))}
          </div>
        </div>
        {error && <p className="text-rose-300 text-sm mt-3">{error}</p>}
        <Button disabled={!name.trim() || submitting} onClick={handleRegister}>
          <Plus size={14} /> {submitting ? 'Registering...' : 'Register agent'}
        </Button>
      </div>
    </div>
  )
}
