export const HOME_BY_ROLE = {
  admin: '/',
  staff: '/staff',
  customer: '/portal',
}

export function homeForRole(role) {
  return HOME_BY_ROLE[role] || '/login'
}

export function roleLabel(role) {
  if (role === 'admin') return 'Administrator'
  if (role === 'staff') return 'Staff'
  if (role === 'customer') return 'Customer'
  return ''
}
