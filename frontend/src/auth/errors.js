/** Convert FastAPI/Pydantic error responses into a single readable message. */
export function apiErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const detail = error?.response?.data?.detail

  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item
        return String(item?.msg || '').replace(/^Value error,\s*/i, '')
      })
      .filter(Boolean)
    if (messages.length) return messages.join(' ')
  }

  if (!error?.response) {
    return 'Unable to reach the server. Please check that the backend is running.'
  }

  return fallback
}
