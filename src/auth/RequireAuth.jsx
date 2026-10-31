import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import { homeForRole } from './roles'

function AuthLoading() {
  return (
    <div className="grid min-h-screen place-items-center bg-[#f4f5fb]">
      <div className="text-xs font-semibold text-slate-500">Loading…</div>
    </div>
  )
}

/** Blocks unauthenticated users and enforces the allowed roles. */
export function RequireAuth({ roles, children }) {
  const { user, initializing } = useAuth()
  const location = useLocation()

  if (initializing) return <AuthLoading />
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  if (roles && !roles.includes(user.role)) {
    return <Navigate to={homeForRole(user.role)} replace />
  }
  return children
}

/** Keeps signed-in users away from the login/register/forgot pages. */
export function PublicOnly({ children }) {
  const { user, initializing } = useAuth()

  if (initializing) return <AuthLoading />
  if (user) {
    return <Navigate to={homeForRole(user.role)} replace />
  }
  return children
}
