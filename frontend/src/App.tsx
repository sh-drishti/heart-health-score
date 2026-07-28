import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import { AppHeader } from '@/components/AppHeader'
import { LandingPage } from '@/pages/LandingPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { IntakePage } from '@/pages/IntakePage'

// /dashboard and /entry are separate role-facing views with no nav between
// them. / is the chooser. Shared components live under src/components.
function IntakeLayout() {
  return (
    <div className="min-h-screen bg-background">
      <AppHeader subtitle="Encounter Entry" />
      <main className="max-w-[1600px] mx-auto px-6 py-5">
        <IntakePage />
      </main>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/entry" element={<IntakeLayout />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
