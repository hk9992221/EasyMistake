/**
 * Session timeout configuration.
 * Keep this aligned with backend ACCESS_TOKEN_EXPIRE_MINUTES.
 */

// 3 days
export const SESSION_TIMEOUT = 3 * 24 * 60 * 60 * 1000

// Warn 5 minutes before timeout
export const WARNING_TIME = 5 * 60 * 1000

// Check once per minute
export const CHECK_INTERVAL = 60 * 1000
