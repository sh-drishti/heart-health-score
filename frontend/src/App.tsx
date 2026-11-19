import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import { AppHeader } from '@/components/AppHeader'
import { AuthProvider } from '@/auth/AuthContext'
import { RequireAuth } from '@/auth/RequireAuth'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { AdminPage } from '@/pages/AdminPage'
import { MyHealthPage } from '@/pages/MyHealthPage'
import { IntakePage } from '@/pages/IntakePage'
import { useAuth } from '@/auth/AuthContext'
import { HOME } from '@/auth/workspaces'
import { Loader2 } from 'lucide-react'
import { EcgPage } from '@/ecg/EcgPage'
// Temporary: the additional-parameter collection programme. Delete this import,
// the /collect route below, and src/collection/ to remove it.
import { CollectPage } from '@/collection/CollectPage'
import { ReviewPage } from '@/collection/ReviewPage'

// Three surfaces: /dashboard for clinicians reviewing anyone, /my-health for a
// patient reading their own record, and /entry — the same 48-field form for all
// three roles, since a patient records their own visit and staff are there to
// help someone through it.
//
// The guards mirror the roles the API enforces (see backend/main.py), so a user
// never reaches a view whose every request would come back 403.
function IntakeLayout() {
  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="max-w-[1600px] mx-auto px-6 py-5">
        <IntakePage />
      </main>
    </div>
  )
}

/**
 * `/` has no page of its own. Which workspace someone needs follows from their
 * account, so a signed-out visitor goes to sign in (which links to sign-up) and
 * a signed-in one goes straight to their role's home.
 */
function Home() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return <Navigate to={user ? HOME[user.role] : '/login'} replace />
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/collect" element={<CollectPage />} />
          <Route path="/collect/review" element={<ReviewPage />} />
          <Route
            path="/dashboard"
            element={
              <RequireAuth roles={['clinician']}>
                <DashboardPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin"
            element={
              <RequireAuth roles={['admin']}>
                <AdminPage />
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
            path="/ecg"
            element={
              <RequireAuth roles={['clinician', 'staff', 'admin']}>
                <EcgPage />
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
