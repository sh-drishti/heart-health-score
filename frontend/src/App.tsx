import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import { AppHeader } from '@/components/AppHeader'
import { AuthProvider } from '@/auth/AuthContext'
import { RequireAuth } from '@/auth/RequireAuth'
import { LandingPage } from '@/pages/LandingPage'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { IntakePage } from '@/pages/IntakePage'

// /dashboard and /entry are separate role-facing views with no nav between
// them. / is the chooser. Shared components live under src/components.
//
// The guards below mirror the roles the API enforces (see backend/main.py), so
// a user never reaches a view whose every request would come back 403.
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
      <AuthProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/dashboard"
            element={
              <RequireAuth roles={['clinician']}>
                <DashboardPage />
              </RequireAuth>
            }
          />
          <Route
            path="/entry"
            element={
              <RequireAuth roles={['clinician', 'staff']}>
                <IntakeLayout />
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
