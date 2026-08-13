import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import { AppHeader } from '@/components/AppHeader'
import { AuthProvider } from '@/auth/AuthContext'
import { RequireAuth } from '@/auth/RequireAuth'
import { LandingPage } from '@/pages/LandingPage'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { MyHealthPage } from '@/pages/MyHealthPage'
import { IntakePage } from '@/pages/IntakePage'
import { useAuth } from '@/auth/AuthContext'

// Three surfaces: /dashboard for clinicians reviewing anyone, /my-health for a
// patient reading their own record, and /entry — the same 48-field form for all
// three roles, since a patient records their own visit and staff are there to
// help someone through it.
//
// The guards mirror the roles the API enforces (see backend/main.py), so a user
// never reaches a view whose every request would come back 403.
function IntakeLayout() {
  const { user } = useAuth()

  return (
    <div className="min-h-screen bg-background">
      <AppHeader
        subtitle={user?.role === 'patient' ? 'Record a Visit' : 'Encounter Entry'}
      />
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
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/dashboard"
            element={
              <RequireAuth roles={['clinician']}>
                <DashboardPage />
              </RequireAuth>
            }
          />
          <Route
            path="/my-health"
            element={
              <RequireAuth roles={['patient']}>
                <MyHealthPage />
              </RequireAuth>
            }
          />
          <Route
            path="/entry"
            element={
              <RequireAuth roles={['clinician', 'staff', 'patient']}>
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
