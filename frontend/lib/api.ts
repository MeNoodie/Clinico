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
  const headers = new Headers(options.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData
  if (!isFormData && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')

  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers,
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(extractErrorMessage(body))
  return body as T
}

export async function downloadFile(path: string, token: string, filename: string): Promise<void> {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(extractErrorMessage(body))
  }

  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export async function viewFile(path: string, token: string): Promise<void> {
  const preview = window.open('about:blank', '_blank')
  if (!preview) throw new Error('Allow pop-ups to view this document.')

  try {
    const response = await fetch(`${baseUrl}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      throw new Error(extractErrorMessage(body))
    }

    const url = URL.createObjectURL(await response.blob())
    preview.opener = null
    preview.location.href = url
    window.setTimeout(() => URL.revokeObjectURL(url), 5 * 60_000)
  } catch (error) {
    preview.close()
    throw error
  }
}
