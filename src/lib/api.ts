const DEFAULT_API_BASE_URL = 'http://localhost:8080'

export const AUTH_TOKEN_STORAGE_KEY = 'dp_med_auth_token_v1'

type ApiEnvelope<T> = {
  success: boolean
  message: string
  data: T
  timestamp: string
}

type ApiRequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown
}

export class ApiError extends Error {
  status: number
  payload?: unknown

  constructor(message: string, status: number, payload?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

function getApiBaseUrl() {
  const raw = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL
  return raw.endsWith('/') ? raw.slice(0, -1) : raw
}

function buildUrl(path: string) {
  if (/^https?:\/\//i.test(path)) {
    return path
  }
  return `${getApiBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`
}

async function parseResponseBody(response: Response) {
  const text = await response.text()
  if (!text) {
    return null
  }

  try {
    return JSON.parse(text) as unknown
  } catch {
    return text
  }
}

function extractMessage(payload: unknown, fallback: string) {
  if (!payload) {
    return fallback
  }

  if (typeof payload === 'string') {
    return payload
  }

  if (typeof payload === 'object') {
    const message = Reflect.get(payload, 'message')
    if (typeof message === 'string' && message.trim()) {
      return message
    }
  }

  return fallback
}

export function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)
}

export function setAuthToken(token: string) {
  localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token)
}

export function clearAuthToken() {
  localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY)
}

export function getErrorMessage(error: unknown, fallback = '请求失败，请稍后重试') {
  if (error instanceof ApiError) {
    return error.message
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message
  }
  return fallback
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}) {
  const headers = new Headers(options.headers)

  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json')
  }

  const token = getAuthToken()
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  let body: BodyInit | undefined
  if (options.body !== undefined) {
    if (
      options.body instanceof FormData ||
      typeof options.body === 'string' ||
      options.body instanceof Blob ||
      options.body instanceof URLSearchParams
    ) {
      body = options.body
    } else {
      headers.set('Content-Type', 'application/json')
      body = JSON.stringify(options.body)
    }
  }

  let response: Response
  try {
    response = await fetch(buildUrl(path), {
      ...options,
      headers,
      body,
    })
  } catch (error) {
    throw new ApiError(getErrorMessage(error, '无法连接后端服务，请确认接口已启动'), 0)
  }

  const payload = await parseResponseBody(response)

  if (!response.ok) {
    throw new ApiError(
      extractMessage(payload, response.statusText || '请求失败'),
      response.status,
      payload
    )
  }

  if (
    payload &&
    typeof payload === 'object' &&
    'success' in payload &&
    'data' in payload
  ) {
    const envelope = payload as ApiEnvelope<T>
    if (!envelope.success) {
      throw new ApiError(extractMessage(payload, '请求失败'), response.status, payload)
    }
    return envelope.data
  }

  return payload as T
}

export const api = {
  get<T>(path: string, options?: Omit<ApiRequestOptions, 'method' | 'body'>) {
    return apiRequest<T>(path, { ...options, method: 'GET' })
  },
  post<T>(path: string, body?: unknown, options?: Omit<ApiRequestOptions, 'method' | 'body'>) {
    return apiRequest<T>(path, { ...options, method: 'POST', body })
  },
  put<T>(path: string, body?: unknown, options?: Omit<ApiRequestOptions, 'method' | 'body'>) {
    return apiRequest<T>(path, { ...options, method: 'PUT', body })
  },
  patch<T>(path: string, body?: unknown, options?: Omit<ApiRequestOptions, 'method' | 'body'>) {
    return apiRequest<T>(path, { ...options, method: 'PATCH', body })
  },
  delete<T>(path: string, options?: Omit<ApiRequestOptions, 'method' | 'body'>) {
    return apiRequest<T>(path, { ...options, method: 'DELETE' })
  },
}
