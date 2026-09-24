import axios from 'axios'
import './tokens'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8010/api/v1'

let csrfToken = null
const api = axios.create({ baseURL, withCredentials: true })

export async function bootstrapCsrf() {
  const { data } = await api.get('/auth/csrf/')
  csrfToken = data.csrfToken
  return csrfToken
}

export function clearCsrf() {
  csrfToken = null
}

api.interceptors.request.use(async (config) => {
  const method = (config.method || 'get').toLowerCase()
  if (!['get', 'head', 'options'].includes(method)) {
    if (!csrfToken) await bootstrapCsrf()
    config.headers['X-CSRFToken'] = csrfToken
  }
  return config
})

api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    // Mutações nunca são repetidas automaticamente.
    if (error.response?.status === 403) clearCsrf()
    return Promise.reject(error)
  },
)

export default api
