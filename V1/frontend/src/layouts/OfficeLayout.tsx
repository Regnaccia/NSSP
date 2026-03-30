import { Outlet, NavLink } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { SyncIndicator } from '@/components/SyncIndicator'
import { LogOut, BarChart3, Users, RefreshCw } from 'lucide-react'

const NAV_PRODUZIONE = [
  { to: '/produzione/f1a', label: 'Lancio ordini' },
  { to: '/produzione/f1b', label: 'Lancio scorte' },
  { to: '/produzione/f2',  label: 'Schedulazione' },
  { to: '/produzione/f4',  label: 'Urgenze' },
]

const NAV_LOGISTICA = [
  { to: '/logistica/f3a',     label: 'Da spedire' },
  { to: '/logistica/f3b',     label: 'Spedizioni' },
  { to: '/logistica/f3c',     label: 'Calendario' },
  { to: '/logistica/f4',      label: 'Urgenze' },
  { to: '/logistica/clienti', label: 'Clienti' },
]

const NAV_ADMIN = [
  { to: '/admin/utenti',  label: 'Utenti', icon: Users },
  { to: '/admin/sync',    label: 'Sync',   icon: RefreshCw },
]

function NavSection({ title, items }: { title: string; items: { to: string; label: string }[] }) {
  return (
    <div>
      <div className="px-3 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        {title}
      </div>
      {items.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `flex items-center px-3 py-2 rounded-md text-sm transition-colors ${
              isActive
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-muted text-foreground'
            }`
          }
        >
          {label}
        </NavLink>
      ))}
    </div>
  )
}

export function OfficeLayout() {
  const { username, ruolo, logout } = useAuthStore()

  const isAdmin = ruolo === 'admin'
  const showProduzione = ruolo === 'produzione' || isAdmin
  const showLogistica = ruolo === 'logistica' || isAdmin

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-56 border-r flex flex-col gap-1 p-3 shrink-0">
        <div className="flex items-center gap-2 px-3 py-2 mb-2">
          <BarChart3 className="h-5 w-5 text-primary" />
          <span className="text-sm font-bold tracking-tight">MRS</span>
        </div>

        <div className="flex flex-col gap-3 flex-1 overflow-y-auto">
          {showProduzione && <NavSection title="Produzione" items={NAV_PRODUZIONE} />}
          {showLogistica && <NavSection title="Logistica" items={NAV_LOGISTICA} />}
          {isAdmin && (
            <NavSection
              title="Admin"
              items={NAV_ADMIN.map(({ to, label }) => ({ to, label }))}
            />
          )}
        </div>

        <div className="border-t pt-3 space-y-1">
          <SyncIndicator tabella="ordini" />
          <div className="px-3 text-xs text-muted-foreground">
            {username} · {ruolo}
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground rounded-md hover:bg-muted w-full transition-colors"
          >
            <LogOut className="h-3.5 w-3.5" />
            Logout
          </button>
        </div>
      </aside>

      {/* Contenuto pagina */}
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
