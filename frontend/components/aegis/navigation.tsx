'use client'

import { useEffect, useState } from 'react'
import { Bell, Bot, ClipboardCheck, LayoutDashboard, Menu, Network, Plus, Settings2, ShieldCheck, AlertTriangle } from 'lucide-react'
import { viewTitles, type View } from '@/src/aegis/view-types'
import { healthService } from '@/src/services'

export function Sidebar({ view, onNavigate }: { view: View; onNavigate: (view: View) => void }) {
  const item = (label: string, icon: React.ReactNode, target: View) => <button onClick={() => onNavigate(target)} className={`nav-item ${view === target ? 'nav-item-active' : ''}`}>{icon}<span>{label}</span>{view === target && <span className="nav-dot" />}</button>
  return <aside className="sidebar"><div className="brand"><div className="brand-mark"><ShieldCheck size={19} /></div><div><b>AEGIS</b><span>Runtime governance</span></div></div><div className="nav-groups"><div><p className="nav-label">Workspace</p>{item('Overview', <LayoutDashboard size={16} />, 'overview')}</div><div><p className="nav-label">Agents</p>{item('Registered agents', <Bot size={16} />, 'agents')}{item('Register agent', <Plus size={16} />, 'register')}</div><div><p className="nav-label">Coordination</p>{item('Agent combos', <Network size={16} />, 'combos')}</div><div><p className="nav-label">Security</p>{item('Audit logs', <ClipboardCheck size={16} />, 'audit')}{item('Escalations', <AlertTriangle size={16} />, 'escalations')}</div></div><div className="operator"><div className="avatar">OP</div><div><p>Operations</p><span>Control plane</span></div><Settings2 size={15} /></div></aside>
}

export function Header({ view, onMenu }: { view: View; onMenu: () => void }) {
  const [status, setStatus] = useState<'healthy' | 'degraded' | 'down'>('healthy')

  useEffect(() => {
    const check = () => {
      healthService.getHealth()
        .then((h) => setStatus(h.status === 'healthy' ? 'healthy' : 'degraded'))
        .catch(() => setStatus('down'))
    }
    check()
    const interval = setInterval(check, 30000)
    return () => clearInterval(interval)
  }, [])

  const statusLabel = status === 'healthy' ? 'All systems operational' : status === 'degraded' ? 'Degraded' : 'API unreachable'
  const statusColor = status === 'healthy' ? 'bg-emerald-400' : status === 'degraded' ? 'bg-amber-400' : 'bg-rose-400'

  return <header className="topbar"><div className="flex items-center gap-3"><button onClick={onMenu} className="mobile-menu"><Menu size={19} /></button><div><div className="crumb">AEGIS <span>/</span> Control plane</div><h1>{viewTitles[view]}</h1></div></div><div className="flex items-center gap-3"><div className="status-pill"><i className={statusColor} /> {statusLabel}</div><button className="icon-button"><Bell size={17} /></button></div></header>
}
