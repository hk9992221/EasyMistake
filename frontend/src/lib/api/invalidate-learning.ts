import type { QueryClient } from '@tanstack/react-query'

const learningKeys = new Set([
  'questions', 'question-progress', 'attempts', 'reviews-today-page',
  'dashboard-reviews-today', 'dashboard-question-total', 'dashboard-analytics-overview',
  'dashboard-error-tags', 'paper-set-review-attempts', 'paper-set-review-progress',
  'paper-set-review-data',
])

export const invalidateLearning = (client: QueryClient) =>
  client.invalidateQueries({ predicate: (query) => learningKeys.has(String(query.queryKey[0])) })
