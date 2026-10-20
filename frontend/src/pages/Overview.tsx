import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useWebSocket } from '../context/WebSocketContext';
import { Device, Alert, DeploymentJob } from '../types';
import {
  Layers,
  Radio,
  WifiOff,
  Rocket,
  Bell,
  ArrowUpRight,
  TrendingUp,
  Cpu,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export const Overview: React.FC = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [activeDeployments, setActiveDeployments] = useState<DeploymentJob[]>([]);
  const [telemetryHistory, setTelemetryHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const { subscribe } = useWebSocket();

  const loadData = async () => {
    try {
      const [devRes, alertRes, depRes] = await Promise.all([
        api.devices.list({ page_size: 50 }),
        api.alerts.list({ page_size: 10, acknowledged: false }),
        api.deployments.list({ page_size: 5 }),
      ]);

      setDevices(devRes.items);
      setAlerts(alertRes.items);
      setActiveDeployments(depRes.items.filter((d) => !['success', 'failed', 'cancelled'].includes(d.state)));

      // Load sample historical readings for the primary device for charting
      if (devRes.items.length > 0) {
        const primId = devRes.items[0].device_id;
        const hist = await api.telemetry.getHistory(primId, 25);
        const chartData = hist.items.reverse().map((r) => ({
          time: new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          temperature: r.readings.temperature ?? 24,
          humidity: r.readings.humidity ?? 50,
          heap: (r.readings.heap_free ?? 150000) / 1024,
        }));
        setTelemetryHistory(chartData);
      }
    } catch (err) {
      console.error('Failed loading dashboard overview:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();

    // Subscribe to live websocket telemetry updates
    const unsubTelemetry = subscribe('telemetry', (msg) => {
      setTelemetryHistory((prev) => {
        const next = [...prev];
        if (next.length > 30) next.shift();
        next.push({
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          temperature: msg.readings.temperature ?? 24,
          humidity: msg.readings.humidity ?? 50,
          heap: (msg.readings.heap_free ?? 150000) / 1024,
        });
        return next;
      });
    });

    // Subscribe to device status updates
    const unsubStatus = subscribe('device_status', (msg) => {
      setDevices((prev) =>
        prev.map((d) => (d.device_id === msg.device_id ? { ...d, is_online: msg.is_online } : d))
      );
    });

    // Subscribe to alerts
    const unsubAlert = subscribe('alert', (msg) => {
      setAlerts((prev) => [msg.alert, ...prev]);
    });

    return () => {
      unsubTelemetry();
      unsubStatus();
      unsubAlert();
    };
  }, []);

  const totalDevices = devices.length;
  const onlineDevices = devices.filter((d) => d.is_online).length;
  const offlineDevices = totalDevices - onlineDevices;

  return (
    <div className="space-y-6">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-fleet-card to-fleet-cardHover p-6 rounded-2xl border border-fleet-border">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <span>Fleet Operations Matrix</span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono uppercase bg-cyan-950 text-cyan-300 border border-cyan-800">
              Live Gateway Active
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time telemetry streaming, firmware distribution, and node state diagnostics.
          </p>
        </div>
        <div className="flex gap-2.5">
          <Link
            to="/deployments"
            className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 shadow-glow-cyan transition-all"
          >
            <Rocket className="w-3.5 h-3.5" />
            <span>Launch Deployment</span>
          </Link>
          <Link
            to="/firmware"
            className="px-4 py-2 bg-fleet-card hover:bg-slate-800 text-slate-200 border border-fleet-border text-xs font-semibold rounded-xl flex items-center gap-1.5 transition-all"
          >
            <span>Upload Release</span>
          </Link>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Devices */}
        <div className="glass-panel p-5 rounded-2xl border border-fleet-border">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Fleet Nodes</span>
            <div className="p-2 rounded-xl bg-blue-950/60 text-blue-400 border border-blue-900/50">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-white">{totalDevices}</div>
          <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
            <Cpu className="w-3 h-3 text-cyan-400" />
            <span>ESP32 & Arduino Uno hardware</span>
          </div>
        </div>

        {/* Online Devices */}
        <div className="glass-panel p-5 rounded-2xl border border-fleet-border">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Nodes Online</span>
            <div className="p-2 rounded-xl bg-emerald-950/60 text-emerald-400 border border-emerald-900/50">
              <Radio className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-emerald-400 flex items-center gap-2">
            <span>{onlineDevices}</span>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 status-pulse-live"></span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            <span>{totalDevices > 0 ? Math.round((onlineDevices / totalDevices) * 100) : 0}% fleet connectivity</span>
          </div>
        </div>

        {/* Offline Devices */}
        <div className="glass-panel p-5 rounded-2xl border border-fleet-border">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Offline Nodes</span>
            <div className="p-2 rounded-xl bg-rose-950/60 text-rose-400 border border-rose-900/50">
              <WifiOff className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-rose-400">{offlineDevices}</div>
          <div className="text-[11px] text-slate-400 mt-1">
            <span>{offlineDevices === 0 ? 'All nodes reporting' : 'Heartbeat timeout exceeded'}</span>
          </div>
        </div>

        {/* Active Alerts */}
        <div className="glass-panel p-5 rounded-2xl border border-fleet-border">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Alerts</span>
            <div className="p-2 rounded-xl bg-amber-950/60 text-amber-400 border border-amber-900/50">
              <Bell className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-amber-400">{alerts.length}</div>
          <div className="text-[11px] text-slate-400 mt-1">
            <span>{alerts.length === 0 ? 'Zero unhandled warnings' : 'Action required'}</span>
          </div>
        </div>
      </div>

      {/* Real-Time Telemetry & Active Rollouts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Telemetry Chart */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-fleet-border flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-cyan-400" />
                <span>Live Environmental Telemetry (ESP32-001)</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Real-time streaming via MQTT broker & WebSocket bridge
              </p>
            </div>
            <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/80 px-2 py-0.5 rounded-lg">
              5000ms POLL
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={telemetryHistory}>
                <defs>
                  <linearGradient id="tempGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="humGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="#475569" fontSize={10} tickLine={false} />
                <YAxis stroke="#475569" fontSize={10} tickLine={false} domain={['dataMin - 2', 'dataMax + 2']} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0c1322',
                    borderColor: '#1a2744',
                    borderRadius: '0.75rem',
                    fontSize: '11px',
                  }}
                />
                <Area type="monotone" dataKey="temperature" name="Temp (°C)" stroke="#06b6d4" strokeWidth={2} fillOpacity={1} fill="url(#tempGradient)" />
                <Area type="monotone" dataKey="humidity" name="Humidity (%)" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#humGradient)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Active Deployment Widget */}
        <div className="glass-panel p-6 rounded-2xl border border-fleet-border flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Rocket className="w-4 h-4 text-cyan-400" />
                <span>Active Deployments</span>
              </h2>
              <Link to="/deployments" className="text-xs text-cyan-400 hover:underline flex items-center gap-1">
                View All <ArrowUpRight className="w-3 h-3" />
              </Link>
            </div>

            {activeDeployments.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-xs">
                <Rocket className="w-8 h-8 mx-auto mb-2 opacity-30" />
                No firmware deployments currently in-flight.
              </div>
            ) : (
              <div className="space-y-3">
                {activeDeployments.map((job) => (
                  <div key={job.id} className="p-3.5 bg-fleet-darkest/60 border border-fleet-border rounded-xl">
                    <div className="flex justify-between items-center mb-1.5">
                      <span className="font-mono text-xs text-cyan-400 font-semibold">{job.device_id}</span>
                      <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800">
                        {job.state}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400">
                      Target Firmware: <span className="text-slate-200 font-mono">v{job.target_version}</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
                      <div className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full w-2/3 animate-pulse"></div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="pt-4 border-t border-fleet-border">
            <Link
              to="/deployments"
              className="w-full py-2 bg-slate-900 hover:bg-slate-800 border border-fleet-border text-slate-200 text-xs font-semibold rounded-xl flex items-center justify-center gap-1.5 transition-colors"
            >
              <span>Manage Rollout Jobs</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* Fleet Device Quick Grid */}
      <div className="glass-panel p-6 rounded-2xl border border-fleet-border">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span>Monitored Edge Nodes</span>
          </h2>
          <Link to="/devices" className="text-xs text-cyan-400 hover:underline flex items-center gap-1">
            All Devices ({devices.length}) <ArrowUpRight className="w-3 h-3" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {devices.map((dev) => (
            <Link
              key={dev.id}
              to={`/devices/${dev.device_id}`}
              className="p-4 bg-fleet-darkest/50 hover:bg-fleet-cardHover border border-fleet-border rounded-xl transition-all group"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-xs font-bold text-white group-hover:text-cyan-400 transition-colors">
                  {dev.device_id}
                </span>
                <span className={`w-2 h-2 rounded-full ${dev.is_online ? 'bg-emerald-500 status-pulse-live' : 'bg-slate-600'}`}></span>
              </div>
              <div className="text-xs text-slate-300 font-medium truncate mb-2">{dev.name}</div>
              <div className="text-[11px] text-slate-400 flex justify-between">
                <span>MCU: <span className="font-mono text-slate-300 uppercase">{dev.mcu_family}</span></span>
                <span>FW: <span className="font-mono text-cyan-400">v{dev.firmware_version}</span></span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};
