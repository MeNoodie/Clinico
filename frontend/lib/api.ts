const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

/** Extract a human-readable error message from a FastAPI error body. */
function extractErrorMessage(body: unknown): string {
  if (!body || typeof body !== 'object') return 'Request failed'
  const b = body as Record<string, unknown>

  // FastAPI validation error: detail is an array of {loc, msg, type}
  if (Array.isArray(b.detail)) {
    return b.detail
      .map((e: unknown) => (e && typeof e === 'object' ? (e as Record<string, unknown>).msg ?? String(e) : String(e)))
      .join('; ')
  }

  // Standard FastAPI HTTP exception: detail is a string
  if (typeof b.detail === 'string') return b.detail

  // Fallback: message field
  if (typeof b.message === 'string') return b.message

  return 'Request failed'
}

export async function api<T>(path: string, token?: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(extractErrorMessage(body))
  return body as T
}

