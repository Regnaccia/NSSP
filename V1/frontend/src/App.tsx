import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'

import { useAuthStore } from '@/store/authStore'
import { OfficeLayout } from '@/layouts/OfficeLayout'
import { KioskLayout } from '@/layouts/KioskLayout'

// Pages — Office
import Login from '@/pages/Login'
import AdminUtenti from '@/pages/Admin/Utenti'
import AdminSync from '@/pages/Admin/Sync'
import AdminCategorie from '@/pages/Admin/Categorie'
import F1a from '@/pages/Produzione/F1a'
import F1b from '@/pages/Produzione/F1b'
import F2 from '@/pages/Produzione/F2'
import ProdF4 from '@/pages/Produzione/F4'
import Articoli from '@/pages/Produzione/Articoli'
import MateriePrime from '@/pages/Produzione/MateriePrime'
import F3a from '@/pages/Logistica/F3a'
import F3b from '@/pages/Logistica/F3b'
import F3c from '@/pages/Logistica/F3c'
import LogF4 from '@/pages/Logistica/F4'
import Clienti from '@/pages/Logistica/Clienti'

// Pages — Kiosk
import MacchinaSelect from '@/pages/Reparto/MacchinaSelect'
import KioskReparto from '@/pages/Reparto/KioskReparto'
import KioskMagazzino from '@/pages/Magazzino/KioskMagazzino'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function RequireRole({ children, ruoli }: { children: React.ReactNode; ruoli: string[] }) {
  const ruolo = useAuthStore(s => s.ruolo)
  if (!ruolo || (!ruoli.includes(ruolo) && ruolo !== 'admin')) {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}

function HomeRedirect() {
  const ruolo = useAuthStore(s => s.ruolo)
  if (ruolo === 'logistica') return <Navigate to="/logistica/f3a" replace />
  if (ruolo === 'admin') return <Navigate to="/admin/utenti" replace />
  return <Navigate to="/produzione/f1a" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" richColors />
      <Routes>
        {/* Pubbliche */}
        <Route path="/login" element={<Login />} />

        {/* Kiosk — nessuna auth */}
        <Route element={<KioskLayout />}>
          <Route path="/reparto" element={<MacchinaSelect />} />
          <Route path="/reparto/:macchinaId" element={<KioskReparto />} />
          <Route path="/magazzino" element={<KioskMagazzino />} />
        </Route>

        {/* Office — richiede auth */}
        <Route
          element={
            <RequireAuth>
              <OfficeLayout />
            </RequireAuth>
          }
        >
          <Route path="/" element={<HomeRedirect />} />

          {/* Admin */}
          <Route path="/admin/utenti" element={
            <RequireRole ruoli={['admin']}>
              <AdminUtenti />
            </RequireRole>
          } />
          <Route path="/admin/sync" element={
            <RequireRole ruoli={['admin']}>
              <AdminSync />
            </RequireRole>
          } />
          <Route path="/admin/categorie" element={
            <RequireRole ruoli={['admin']}>
              <AdminCategorie />
            </RequireRole>
          } />

          {/* Produzione */}
          <Route path="/produzione/f1a" element={
            <RequireRole ruoli={['produzione']}>
              <F1a />
            </RequireRole>
          } />
          <Route path="/produzione/f1b" element={
            <RequireRole ruoli={['produzione']}>
              <F1b />
            </RequireRole>
          } />
          <Route path="/produzione/f2" element={
            <RequireRole ruoli={['produzione']}>
              <F2 />
            </RequireRole>
          } />
          <Route path="/produzione/f4" element={
            <RequireRole ruoli={['produzione']}>
              <ProdF4 />
            </RequireRole>
          } />
          <Route path="/produzione/articoli" element={
            <RequireRole ruoli={['produzione']}>
              <Articoli />
            </RequireRole>
          } />
          <Route path="/produzione/materie-prime" element={
            <RequireRole ruoli={['produzione']}>
              <MateriePrime />
            </RequireRole>
          } />

          {/* Logistica */}
          <Route path="/logistica/f3a" element={
            <RequireRole ruoli={['logistica']}>
              <F3a />
            </RequireRole>
          } />
          <Route path="/logistica/f3b" element={
            <RequireRole ruoli={['logistica']}>
              <F3b />
            </RequireRole>
          } />
          <Route path="/logistica/f3c" element={
            <RequireRole ruoli={['logistica']}>
              <F3c />
            </RequireRole>
          } />
          <Route path="/logistica/f4" element={
            <RequireRole ruoli={['logistica']}>
              <LogF4 />
            </RequireRole>
          } />
          <Route path="/logistica/clienti" element={
            <RequireRole ruoli={['logistica']}>
              <Clienti />
            </RequireRole>
          } />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
