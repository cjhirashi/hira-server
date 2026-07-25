import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('hira-token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('hira-token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const res = await axios.post<LoginResponse>('/api/v1/auth/login', { email, password })
  return res.data
}
