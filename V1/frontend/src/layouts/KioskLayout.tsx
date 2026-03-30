import { Outlet } from 'react-router-dom'

// Layout per terminali kiosk (Reparto, Magazzino).
// Full-screen, font più grande, niente sidebar — il terminale è always-on.
export function KioskLayout() {
  return (
    <div className="min-h-screen bg-background text-lg">
      <Outlet />
    </div>
  )
}
