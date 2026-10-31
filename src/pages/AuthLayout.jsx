/**
 * Shared split-screen shell for all auth screens. It keeps the visual
 * language of the existing login page (same gradient panel, spacing, fields).
 */
export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="grid min-h-screen place-items-center bg-[#f4f5fb] p-5">
      <div className="grid w-full max-w-4xl overflow-hidden rounded-xl bg-white shadow-xl md:grid-cols-2">
        <div className="hidden min-h-[480px] bg-gradient-to-br from-[#10173a] to-[#2b2370] p-12 text-white md:block">
          <div className="mb-28 flex items-center gap-2 font-bold">
            <div className="grid h-7 w-7 place-items-center rounded bg-brand">S</div>
            SMS
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold">
              Subscription
              <br />
              Management System
            </div>
            <p className="mt-5 text-sm leading-6 text-indigo-100">
              Manage subscriptions, billing,
              <br />
              payments and revenue in one place.
            </p>
            <div className="mt-16 text-7xl">◈</div>
          </div>
        </div>
        <div className="p-10 md:p-14">
          <h1 className="text-2xl font-bold">{title}</h1>
          <p className="mb-8 text-xs text-slate-500">{subtitle}</p>
          {children}
          {footer}
        </div>
      </div>
    </div>
  )
}

export function AuthField({ label, error, children }) {
  return (
    <label className="block text-[10px] font-semibold">
      {label}
      {children}
      {error && (
        <span className="mt-1 block text-rose-500">{error.message || error}</span>
      )}
    </label>
  )
}

export function AuthAlert({ type = 'error', children }) {
  const styles =
    type === 'success'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : 'border-rose-200 bg-rose-50 text-rose-700'
  return (
    <div
      role="status"
      className={`mb-4 rounded-md border px-3 py-2 text-[10px] font-semibold ${styles}`}
    >
      {children}
    </div>
  )
}
