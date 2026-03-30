import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

// Client con JWT — usato solo per /api/produzione, /api/logistica, /api/articoli,
// /api/auth, /api/sync, /api/eventi
export const officeClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '',
  headers: { 'Content-Type': 'application/json' },
})

// Aggiunge automaticamente il token JWT ad ogni richiesta
officeClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Intercetta 401 → logout + redirect login
officeClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)
