import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './hooks/AuthContext'
import PublicLayout from './layouts/PublicLayout'
import DashboardLayout from './layouts/DashboardLayout'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import DashboardPage from './pages/DashboardPage'
import UsersPage from './pages/UsersPage'
import ProfilePage from './pages/ProfilePage'
import ProductsPage from './pages/ProductsPage'
import PlansPage from './pages/PlansPage'
import MyQuotationsPage from './pages/MyQuotationsPage'
import QuotationDetailPage from './pages/QuotationDetailPage'

function getDefaultHome(role) {
  return role === 'CUSTOMER' ? '/my-quotations' : '/dashboard'
}

function ProtectedRoute({ roles }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <div className="page-loading">Restoring your workspace…</div>
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (roles && !roles.includes(user.role)) return <Navigate to={getDefaultHome(user.role)} replace />
  return <Outlet />
}

function PublicOnly() {
  const { user, loading } = useAuth()
  if (loading) return <div className="page-loading">Loading Brightloop…</div>
  if (user) return <Navigate to={getDefaultHome(user.role)} replace />
  return <Outlet />
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route element={<PublicOnly />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
        </Route>
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/plans" element={<PlansPage />} />
          <Route element={<ProtectedRoute roles={['CUSTOMER']} />}>
            <Route path="/my-quotations" element={<MyQuotationsPage />} />
            <Route path="/quotations/:id" element={<QuotationDetailPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={['ADMIN', 'STAFF']} />}>
            <Route path="/products" element={<ProductsPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={['ADMIN']} />}>
            <Route path="/admin/users" element={<UsersPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
