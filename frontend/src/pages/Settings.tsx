import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';
import { CloudStatus } from '../types';
import {
  Settings as SettingsIcon,
  Cloud,
  CheckCircle,
  XCircle,
  RefreshCw,
  Cpu,
  User as UserIcon,
  Database,
  Radio,
  Shield,
  ArrowRight,
} from 'lucide-react';

export const Settings: React.FC = () => {
  const { user } = useAuth();
  const { isConnected } = useWebSocket();
  const [cloudStatus, setCloudStatus] = useState<CloudStatus | null>(null);
  const [gatewayHealth, setGatewayHealth] = useState<any | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadSettingsData = async () => {
    setLoading(true);
    try {
      const [cloud, health] = await Promise.all([
        api.cloud.getStatus().catch(() => null),
        api.health.check().catch(() => null),
      ]);
      setCloudStatus(cloud);
      setGatewayHealth(health);
    } catch (err) {
      console.error('Failed loading settings info:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettingsData();
  }, []);

  const handleSyncNow = async () => {
    setSyncing(true);
    try {
      const res = await api.cloud.syncNow();
      alert(`Sync triggered: ${res.message}. Processed ${res.events_processed} events.`);
      loadSettingsData();
    } catch (err: any) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-cyan-400" />
          <span>Gateway Settings & Cloud Control Plane</span>
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Local Raspberry Pi diagnostics, outbound HTTPS cloud synchronization, and operator profile.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gateway Infrastructure Health */}
        <div className="glass-panel p-6 rounded-2xl border border-fleet-border space-y-4">
          <h2 className="text-sm font-bold text-white flex items-center gap-2 border-b border-fleet-border pb-3">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <span>Local Gateway Stack Diagnostics</span>
          </h2>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center py-2 border-b border-fleet-border/40">
              <span className="text-slate-400">Gateway Version:</span>
              <span className="font-mono text-cyan-400 font-bold">
                v{gatewayHealth?.version || '0.1.0'}
              </span>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-fleet-border/40">
              <span className="text-slate-400">REST API Status:</span>
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-emerald-950 text-emerald-300 border border-emerald-800">
                <CheckCircle className="w-3 h-3 text-emerald-400" />
                {gatewayHealth?.status || 'HEALTHY'}
              </span>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-fleet-border/40">
              <span className="text-slate-400">WebSocket Event Stream:</span>
              <span
                className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                  isConnected
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    : 'bg-amber-950 text-amber-300 border border-amber-800'
                }`}
              >
                {isConnected ? 'Connected (Live)' : 'Reconnecting...'}
              </span>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-fleet-border/40">
              <span className="text-slate-400">Local Storage Engine:</span>
              <span className="font-mono text-slate-300 flex items-center gap-1">
                <Database className="w-3.5 h-3.5 text-blue-400" />
                SQLite 3 (WAL mode enabled)
              </span>
            </div>

            <div className="flex justify-between items-center py-2">
              <span className="text-slate-400">Mosquitto MQTT Broker:</span>
              <span className="font-mono text-emerald-400 flex items-center gap-1">
                <Radio className="w-3.5 h-3.5" />
                tcp://localhost:1883
              </span>
            </div>
          </div>
        </div>

        {/* User Profile */}
        <div className="glass-panel p-6 rounded-2xl border border-fleet-border space-y-4">
          <h2 className="text-sm font-bold text-white flex items-center gap-2 border-b border-fleet-border pb-3">
            <UserIcon className="w-4 h-4 text-cyan-400" />
            <span>Active Operator Profile</span>
          </h2>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center py-2 border-b border-fleet-border/40">
              <span className="text-slate-400">Full Name:</span>
              <span className="text-slate-200 font-semibold">{user?.full_name || '—'}</span>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-fleet-border/40">
              <span className="text-slate-400">Email Address:</span>
              <span className="font-mono text-slate-300">{user?.email || '—'}</span>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-fleet-border/40">
              <span className="text-slate-400">Assigned RBAC Role:</span>
              <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-bold uppercase bg-purple-950 text-purple-300 border border-purple-800">
                {user?.role || 'viewer'}
              </span>
            </div>

            <div className="flex justify-between items-center py-2">
              <span className="text-slate-400">Account ID:</span>
              <span className="font-mono text-slate-400 text-[11px]">{user?.id || '—'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Cloud Synchronization Section */}
      <div className="glass-panel p-6 rounded-2xl border border-fleet-border space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Cloud className="w-5 h-5 text-cyan-400" />
              <span>Outbound HTTPS Cloud Synchronization</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Durable local SQLite queue transmitting status changes and aggregates to central cloud VPS.
            </p>
          </div>

          <button
            onClick={handleSyncNow}
            disabled={syncing}
            className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 shadow-glow-cyan transition-all disabled:opacity-50 self-start sm:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
            <span>{syncing ? 'Syncing Now...' : 'Force Batch Sync'}</span>
          </button>
        </div>

        {/* Cloud Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 bg-[#070b14] border border-fleet-border rounded-xl">
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Cloud Link</div>
            <div className="text-sm font-bold mt-1">
              {cloudStatus?.connected ? (
                <span className="text-emerald-400 flex items-center gap-1">
                  <CheckCircle className="w-3.5 h-3.5" /> Online
                </span>
              ) : (
                <span className="text-slate-500 flex items-center gap-1">
                  <XCircle className="w-3.5 h-3.5" /> Idle / Standalone
                </span>
              )}
            </div>
          </div>

          <div className="p-4 bg-[#070b14] border border-fleet-border rounded-xl">
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Pending Queue</div>
            <div className="text-lg font-black text-white font-mono mt-1">
              {cloudStatus?.pending_events ?? 0}
            </div>
          </div>

          <div className="p-4 bg-[#070b14] border border-fleet-border rounded-xl">
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Synced Events</div>
            <div className="text-lg font-black text-cyan-400 font-mono mt-1">
              {cloudStatus?.sent_events ?? 0}
            </div>
          </div>

          <div className="p-4 bg-[#070b14] border border-fleet-border rounded-xl">
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Failed Events</div>
            <div className="text-lg font-black text-rose-400 font-mono mt-1">
              {cloudStatus?.failed_events ?? 0}
            </div>
          </div>
        </div>

        {cloudStatus?.recent_errors && cloudStatus.recent_errors.length > 0 && (
          <div className="p-4 bg-rose-950/30 border border-rose-900/60 rounded-xl text-xs space-y-1">
            <div className="text-rose-400 font-semibold mb-1">Recent Cloud Sync Alerts:</div>
            {cloudStatus.recent_errors.map((err, idx) => (
              <div key={idx} className="font-mono text-[11px] text-rose-300 truncate">
                {err}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
