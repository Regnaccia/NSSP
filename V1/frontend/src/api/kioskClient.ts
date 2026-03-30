import axios from 'axios'

// Client pulito, senza interceptor auth — usato solo per /api/reparto e /api/magazzino
export const kioskClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '',
  headers: { 'Content-Type': 'application/json' },
})
