import type { Action } from '@/src/types'
import { ArrowRight, Bot, Check, Network, ShieldCheck } from 'lucide-react'

export const actionMeta: Record<Action, { label: string; tone: string }> = {
  allow: { label: 'ALLOW', tone: 'text-emerald-300 bg-emerald-400/10 border-emerald-400/20' },
  flag: { label: 'FLAG', tone: 'text-amber-300 bg-amber-400/10 border-amber-400/20' },
  block: { label: 'BLOCK', tone: 'text-rose-300 bg-rose-400/10 border-rose-400/20' },
  escalate: { label: 'ESCALATE', tone: 'text-orange-300 bg-orange-400/10 border-orange-400/20' },
}

export function ActionBadge({ action }: { action: Action }) {
  const meta = actionMeta[action]
  return <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[10px] font-bold tracking-[.12em] ${meta.tone}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{meta.label}</span>
}

export function Button({ children, onClick, secondary = false, disabled = false }: { children: React.ReactNode; onClick?: () => void; secondary?: boolean; disabled?: boolean }) {
  return <button disabled={disabled} onClick={onClick} className={secondary ? 'button-secondary' : 'button-primary'}>{children}</button>
}

export function EmptyState({ title, text }: { title: string; text: string }) {
  return <div className="empty-state"><div className="mx-auto grid h-11 w-11 place-items-center rounded-xl border border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--accent)]"><ShieldCheck size={19} /></div><h3 className="mt-4 text-sm font-semibold text-[var(--text)]">{title}</h3><p className="mt-2 max-w-sm text-xs leading-5 text-[var(--muted)]">{text}</p></div>
}

export function AgentIcon({ combo = false }: { combo?: boolean }) { return <div className="icon-tile">{combo ? <Network size={17} /> : <Bot size={17} />}</div> }
export { ArrowRight, Check }
