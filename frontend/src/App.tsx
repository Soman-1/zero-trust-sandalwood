import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ToastProvider } from './context/ToastContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Layout } from './components/layout/Layout';
import { LoadingSpinner } from './components/common/LoadingSpinner';

// Eager Login Page for instant initial rendering
import { LoginPage } from './pages/LoginPage';

// Lazy Loaded Operational Pages (Code-Split on Demand)
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const MapPage = lazy(() => import('./pages/MapPage').then(m => ({ default: m.MapPage })));
const TreesPage = lazy(() => import('./pages/TreesPage').then(m => ({ default: m.TreesPage })));
const TreeStatusUpdatePage = lazy(() => import('./pages/TreeStatusUpdatePage').then(m => ({ default: m.TreeStatusUpdatePage })));
const DevicesPage = lazy(() => import('./pages/DevicesPage').then(m => ({ default: m.DevicesPage })));
const RegionsPage = lazy(() => import('./pages/RegionsPage').then(m => ({ default: m.RegionsPage })));
const TelemetryPage = lazy(() => import('./pages/TelemetryPage').then(m => ({ default: m.TelemetryPage })));
const AnomalyPage = lazy(() => import('./pages/AnomalyPage').then(m => ({ default: m.AnomalyPage })));
const AlertsPage = lazy(() => import('./pages/AlertsPage').then(m => ({ default: m.AlertsPage })));
const AuditPage = lazy(() => import('./pages/AuditPage').then(m => ({ default: m.AuditPage })));
const SystemPage = lazy(() => import('./pages/SystemPage').then(m => ({ default: m.SystemPage })));
const GlobalTreesPage = lazy(() => import('./pages/GlobalTreesPage').then(m => ({ default: m.GlobalTreesPage })));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage').then(m => ({ default: m.NotFoundPage })));

const PageFallback: React.FC = () => (
  <div className="h-[calc(100vh-8rem)] flex items-center justify-center">
    <LoadingSpinner message="Loading module..." size="lg" />
  </div>
);

// Protected Route Guard
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#090d16] flex items-center justify-center">
        <LoadingSpinner message="Authenticating Zero Trust Session..." size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <ToastProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Login Route */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected Application Routes */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Suspense fallback={<PageFallback />}><DashboardPage /></Suspense>} />
              <Route path="map" element={<Suspense fallback={<PageFallback />}><MapPage /></Suspense>} />
              <Route path="trees" element={<Suspense fallback={<PageFallback />}><TreesPage /></Suspense>} />
              <Route path="trees/:treeUid/status" element={<Suspense fallback={<PageFallback />}><TreeStatusUpdatePage /></Suspense>} />
              <Route path="devices" element={<Suspense fallback={<PageFallback />}><DevicesPage /></Suspense>} />
              <Route path="regions" element={<Suspense fallback={<PageFallback />}><RegionsPage /></Suspense>} />
              <Route path="telemetry" element={<Suspense fallback={<PageFallback />}><TelemetryPage /></Suspense>} />
              <Route path="anomaly" element={<Suspense fallback={<PageFallback />}><AnomalyPage /></Suspense>} />
              <Route path="alerts" element={<Suspense fallback={<PageFallback />}><AlertsPage /></Suspense>} />
              <Route path="audit" element={<Suspense fallback={<PageFallback />}><AuditPage /></Suspense>} />
              <Route path="system" element={<Suspense fallback={<PageFallback />}><SystemPage /></Suspense>} />
              <Route path="global-trees" element={<Suspense fallback={<PageFallback />}><GlobalTreesPage /></Suspense>} />
              <Route path="*" element={<Suspense fallback={<PageFallback />}><NotFoundPage /></Suspense>} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ToastProvider>
  );
};

export default App;
