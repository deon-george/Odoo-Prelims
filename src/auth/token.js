/**
 * Access token is intentionally kept in memory only (never localStorage or
 * sessionStorage). The refresh token lives in an HttpOnly cookie managed by
 * the backend.
 */
let accessToken = null

export function getAccessToken() {
  return accessToken
}

export function setAccessToken(token) {
  accessToken = token || null
}
