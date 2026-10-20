import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { WebSocketProvider } from './context/WebSocketContext';
import { Layout } from './components/layout/Layout';
import { Login } from './pages/Login';
import { Overview } from './pages/Overview';
import { DeviceInventory } from './pages/DeviceInventory';
import { DeviceDetails } from './pages/DeviceDetails';
import { FirmwareReleases } from './pages/FirmwareReleases';
import { DeploymentManager } from './pages/DeploymentManager';
import { AlertsLogs } from './pages/AlertsLogs';
import { Settings } from './pages/Settings';
import { Activity } from 'lucide-react';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#070b14] flex flex-col items-center justify-center text-slate-400 gap-3">
        <Activity className="w-8 h-8 text-cyan-400 animate-spin" />
        <span className="text-xs font-mono uppercase tracking-widest text-slate-400">
          Connecting to EdgeFleet Gateway...
        </span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <WebSocketProvider>
          <Routes>
            <Route path="/login" element={<Login />} />

            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Overview />} />
              <Route path="devices" element={<DeviceInventory />} />
              <Route path="devices/:deviceId" element={<DeviceDetails />} />
              <Route path="firmware" element={<FirmwareReleases />} />
              <Route path="deployments" element={<DeploymentManager />} />
              <Route path="alerts" element={<AlertsLogs />} />
              <Route path="settings" element={<Settings />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </WebSocketProvider>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
