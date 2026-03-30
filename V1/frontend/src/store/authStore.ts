import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Ruolo, TokenPayload } from '@/types/api'

interface AuthState {
  token: string | null
  username: string | null
  ruolo: Ruolo | null
  isAuthenticated: boolean
  login: (token: string, username: string, ruolo: Ruolo) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      username: null,
      ruolo: null,
      isAuthenticated: false,
      login: (token, username, ruolo) =>
        set({ token, username, ruolo, isAuthenticated: true }),
      logout: () =>
        set({ token: null, username: null, ruolo: null, isAuthenticated: false }),
    }),
    { name: 'mrs-auth' }
  )
)

// Decodifica payload JWT lato client (senza verifica firma).
// Usato solo per leggere username/ruolo — il controllo accesso vero è backend.
export function parseTokenPayload(token: string): TokenPayload {
  const base64 = token.split('.')[1]
  return JSON.parse(atob(base64)) as TokenPayload
}
