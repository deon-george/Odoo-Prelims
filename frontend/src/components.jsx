import {
  AlertTriangle,
  ArrowLeft,
  Bell,
  CheckCircle2,
  Download,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  MoreVertical,
  Package,
  Pencil,
  Plus,
  ReceiptText,
  Search,
  Send,
  Tags,
  Users,
  X,
} from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuth } from './auth/AuthContext'
import { roleLabel } from './auth/roles'

const ADMIN_LINKS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/products', label: 'Products', icon: Package },
  { to: '/plans', label: 'Plans', icon: Tags },
  { to: '/quotations/new', label: 'Quotations', icon: FileText },
  { to: '/subscriptions', label: 'Subscriptions', icon: ReceiptText },
  { to: '/invoices', label: 'Invoices', icon: FileText },
  { to: '/staff', label: 'Staff Dashboard', icon: Users },
]

const STAFF_LINKS = [
  { to: '/staff', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/products', label: 'Products', icon: Package },
  { to: '/plans', label: 'Plans', icon: Tags },
  { to: '/quotations/new', label: 'Quotations', icon: FileText },
  { to: '/subscriptions', label: 'Subscriptions', icon: ReceiptText },
  { to: '/invoices', label: 'Invoices', icon: FileText },
]

const CUSTOMER_LINKS = [
  { to: '/portal', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/portal/catalog', label: 'Product Catalog', icon: Package },
  { to: '/portal/invoices', label: 'Invoices', icon: FileText },
]

const STATUS_STYLES = {
  Active: 'bg-emerald-100 text-emerald-700',
  Available: 'bg-emerald-100 text-emerald-700',
  Paid: 'bg-emerald-100 text-emerald-700',
  Overdue: 'bg-rose-100 text-rose-700',
  'Partially Paid': 'bg-amber-100 text-amber-700',
  Paused: 'bg-amber-100 text-amber-700',
  Inactive: 'bg-slate-200 text-slate-600',
  Closed: 'bg-slate-200 text-slate-600',
  Unavailable: 'bg-slate-200 text-slate-600',
}

export function Status({ children }) {
  const colors = STATUS_STYLES[children] || 'bg-slate-100 text-slate-600'
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-md px-2.5 py-1 text-xs font-semibold ${colors}`}
    >
      {children}
    </span>
  )
}

/** Shows effective plan availability separately from the stored plan status. */
export function PlanAvailability({ plan }) {
  const productInactive = plan?.product?.status === 'inactive'

  if (productInactive) {
    return (
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border border-amber-200 bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-800">
        <AlertTriangle size={13} />
        Unavailable – Product Inactive
      </span>
    )
  }

  if (plan?.status === 'active') {
    return (
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-md bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700">
        <CheckCircle2 size={13} />
        Available
      </span>
    )
  }

  return <Status>Unavailable</Status>
}

export function Shell({ children, customer = false }) {
  const [open, setOpen] = useState(false)
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  // Derive navigation from the authenticated role, not from the page that
  // happens to render Shell. This keeps the sidebar stable on fallback routes.
  const isCustomer = customer || user?.role === 'customer'
  const nav = isCustomer
    ? CUSTOMER_LINKS
    : user?.role === 'staff'
      ? STAFF_LINKS
      : ADMIN_LINKS

  useEffect(() => {
    if (!open) return undefined

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [open])

  useEffect(() => {
    const desktopQuery = window.matchMedia('(min-width: 1024px)')
    const closeOnDesktop = () => {
      if (desktopQuery.matches) setOpen(false)
    }

    closeOnDesktop()
    desktopQuery.addEventListener('change', closeOnDesktop)
    return () => desktopQuery.removeEventListener('change', closeOnDesktop)
  }, [])

  function closeSidebar() {
    setOpen(false)
  }

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-[#f7f8fc] text-ink">
      <aside
        className={`sidebar ${open ? 'sidebar-open' : ''}`}
        aria-label="Main navigation"
      >
        <div className="sidebar-brand">
          <div className="grid h-8 w-8 place-items-center rounded-md bg-[#694ee9] text-sm font-black">
            S
          </div>
          <span className="text-base font-bold">SMS</span>
          <button
            type="button"
            onClick={closeSidebar}
            className="ml-auto rounded p-1 text-slate-300 hover:bg-white/10 hover:text-white lg:hidden"
            aria-label="Close navigation"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="sidebar-nav">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              end={to === '/' || to === '/portal'}
              key={to}
              to={to}
              onClick={closeSidebar}
              className={({ isActive }) =>
                `nav-item ${isActive ? 'nav-active' : ''}`
              }
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button
            type="button"
            onClick={handleLogout}
            className="nav-item w-full"
          >
            <LogOut size={17} />
            Logout
          </button>
        </div>
      </aside>

      {open && (
        <button
          type="button"
          className="sidebar-backdrop lg:hidden"
          onClick={closeSidebar}
          aria-label="Close navigation"
        />
      )}

      <main className="app-main">
        <header className="app-header">
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="rounded-md p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
            aria-label="Open navigation"
          >
            <Menu size={22} />
          </button>

          <div className="ml-auto flex items-center gap-3 sm:gap-5">
            <button
              type="button"
              className="rounded-md p-2 text-slate-500 hover:bg-slate-100"
              aria-label="Notifications"
              title="Notifications"
            >
              <Bell size={19} />
            </button>
            <div className="h-8 w-px bg-slate-200" />
            <div className="flex items-center gap-2.5">
              <div className="grid h-9 w-9 place-items-center rounded-full bg-brand text-sm font-semibold text-white">
                {(user?.full_name || 'A').charAt(0).toUpperCase()}
              </div>
              <div className="hidden text-xs leading-tight sm:block">
                <b className="block text-sm text-ink">
                  {user?.full_name || (isCustomer ? 'ABC Traders' : 'Admin')}
                </b>
                <span className="text-slate-500">
                  {user?.role ? roleLabel(user.role) : 'Administrator'}
                </span>
              </div>
            </div>
          </div>
        </header>

        <div className="page-container">{children}</div>
      </main>
    </div>
  )
}

export function PageHeader({ title, action, back = false }) {
  const navigate = useNavigate()
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div className="flex items-center gap-2">
        {back && (
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="rounded-md p-1.5 text-slate-600 hover:bg-slate-200"
            aria-label="Go back"
          >
            <ArrowLeft size={20} />
          </button>
        )}
        <h1 className="text-2xl font-bold tracking-tight text-ink md:text-[26px]">
          {title}
        </h1>
      </div>
      {action}
    </div>
  )
}

export function Button({
  children,
  onClick,
  className = '',
  type = 'button',
  disabled = false,
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-md bg-brand px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#4d36c4] ${disabled ? 'cursor-not-allowed opacity-60' : ''} ${className}`}
    >
      {children}
    </button>
  )
}

export function Card({ children, className = '' }) {
  return (
    <div
      className={`rounded-lg border border-[#e6e8f1] bg-white p-5 shadow-card md:p-6 ${className}`}
    >
      {children}
    </div>
  )
}

export function SearchBar({
  placeholder = 'Search...',
  value,
  onChange,
}) {
  return (
    <div className="relative">
      <Search
        className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
        size={17}
      />
      <input
        className="field pl-10"
        placeholder={placeholder}
        value={value}
        onChange={onChange}
      />
    </div>
  )
}

export function ActionButtons({ invoiceId }) {
  const nav = useNavigate()
  return (
    <div className="flex justify-end gap-2">
      <button
        type="button"
        onClick={() => invoiceId && nav(`/invoices/${invoiceId}`)}
        className="icon-button"
        aria-label="Edit"
      >
        <Pencil size={16} />
      </button>
      <button type="button" className="icon-button" aria-label="More actions">
        <MoreVertical size={16} />
      </button>
    </div>
  )
}

export function Field({ label, error, hint, children }) {
  return (
    <label className="block text-sm font-semibold text-slate-700">
      {label}
      {children}
      {hint && !error && (
        <span className="mt-1.5 block text-xs font-normal text-slate-400">
          {hint}
        </span>
      )}
      {error && (
        <span className="mt-1.5 block text-xs font-normal text-rose-500">
          {error}
        </span>
      )}
    </label>
  )
}

export function Modal({ open, title, onClose, children }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg border border-[#e6e8f1] bg-white shadow-card"
      >
        <div className="flex items-center justify-between border-b border-[#edf0f5] px-5 py-4">
          <h2 className="text-lg font-bold text-ink">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="icon-button"
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>
        <div className="p-5 md:p-6">{children}</div>
      </div>
    </div>
  )
}
