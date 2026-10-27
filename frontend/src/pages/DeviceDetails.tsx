import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useWebSocket } from '../context/WebSocketContext';
import { Device, TelemetryReading, DeploymentJob, SerialPortInfo } from '../types';
import {
  Radio,
  ArrowLeft,
  Cpu,
  Rocket,
  Activity,
  HardDrive,
  Clock,
  Wifi,
  Thermometer,
  Droplets,
  Zap,
  Usb,
  Cable,
  RefreshCw,
  Check,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export const DeviceDetails: React.FC = () => {
  const { deviceId } = useParams<{ deviceId: string }>();
  const [device, setDevice] = useState<Device | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryReading[]>([]);
  const [deployments, setDeployments] = useState<DeploymentJob[]>([]);
  const [activeTab, setActiveTab] = useState<'telemetry' | 'hardware' | 'deployments'>('telemetry');
  const [loading, setLoading] = useState(true);

  // Serial Port management state
  const [editingPort, setEditingPort] = useState(false);
  const [portInput, setPortInput] = useState('');
  const [availablePorts, setAvailablePorts] = useState<SerialPortInfo[]>([]);
  const [scanningPorts, setScanningPorts] = useState(false);
  const [savingPort, setSavingPort] = useState(false);

  const { subscribe } = useWebSocket();

  const scanPorts = async () => {
    setScanningPorts(true);
    try {
      const ports = await api.devices.getSerialPorts();
      setAvailablePorts(ports);
      if (ports.length > 0 && !portInput) {
        setPortInput(ports[0].port);
      }
    } catch (err) {
      console.error('Failed scanning serial ports:', err);
    } finally {
      setScanningPorts(false);
    }
  };

  const handleSavePort = async () => {
    if (!device) return;
    setSavingPort(true);
    try {
      const updated = await api.devices.update(device.device_id, {
        serial_port: portInput.trim() || undefined,
      });
      setDevice(updated);
      setEditingPort(false);
    } catch (err: any) {
      alert(`Failed to save serial port: ${err.message}`);
    } finally {
      setSavingPort(false);
    }
  };

  const loadDeviceData = async () => {
    if (!deviceId) return;
    setLoading(true);
    try {
      const [dev, telRes, depRes] = await Promise.all([
        api.devices.get(deviceId),
        api.telemetry.getHistory(deviceId, 40),
        api.deployments.list({ page_size: 20 }),
      ]);
      setDevice(dev);
      setPortInput(dev.serial_port || '');
      setTelemetry(telRes.items.reverse());
      setDeployments(depRes.items.filter((d) => d.device_id === dev.id || d.device_id === dev.device_id));
    } catch (err) {
      console.error('Failed loading device details:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDeviceData();

    // Live telemetry websocket listener
    const unsubTel = subscribe('telemetry', (msg) => {
      if (device && (msg.device_id === device.device_id || msg.device_id === device.id)) {
        setTelemetry((prev) => {
          const next = [...prev];
          if (next.length > 50) next.shift();
          next.push({
            id: Date.now(),
            device_id: msg.device_id,
            timestamp: msg.timestamp || new Date().toISOString(),
            schema_version: '1.0',
            firmware_version: msg.firmware_version,
            readings: msg.readings,
          });
          return next;
        });
      }
    });

    // Live status websocket listener
    const unsubStatus = subscribe('device_status', (msg) => {
      if (device && (msg.device_id === device.device_id || msg.device_id === device.id)) {
        setDevice((prev) => (prev ? { ...prev, is_online: msg.is_online } : null));
      }
    });

    return () => {
      unsubTel();
      unsubStatus();
    };
  }, [deviceId, device?.id]);

  if (loading) {
    return (
      <div className="py-20 text-center text-slate-500 text-sm">
        <Activity className="w-8 h-8 mx-auto mb-3 animate-spin text-cyan-400" />
        Connecting to device diagnostics...
      </div>
    );
  }

  if (!device) {
    return (
      <div className="py-20 text-center text-slate-400">
        <div className="text-xl font-bold text-white mb-2">Device Not Found</div>
        <p className="text-xs mb-4">No node registered with identifier: {deviceId}</p>
        <Link to="/devices" className="text-xs text-cyan-400 underline">
          Back to Device Inventory
        </Link>
      </div>
    );
  }

  const latestReading = telemetry.length > 0 ? telemetry[telemetry.length - 1].readings : {};

  const formatUptime = (sec?: number) => {
    if (!sec) return '—';
    const days = Math.floor(sec / 86400);
    const hours = Math.floor((sec % 86400) / 3600);
    const mins = Math.floor((sec % 3600) / 60);
    return `${days}d ${hours}h ${mins}m`;
  };

  const chartData = telemetry.map((r) => ({
    time: new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    temperature: r.readings.temperature,
    humidity: r.readings.humidity,
    light: r.readings.light_lux,
  }));

  return (
    <div className="space-y-6">
      {/* Back button & Header */}
      <div>
        <Link
          to="/devices"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Device Inventory</span>
        </Link>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-panel p-6 rounded-2xl border border-fleet-border">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-cyan-600/30 to-blue-600/30 border border-cyan-500/40 flex items-center justify-center">
              <Cpu className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-black text-white font-mono">{device.device_id}</h1>
                {device.is_online ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-950 text-emerald-300 border border-emerald-800">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 status-pulse-live"></span>
                    Online
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-slate-800 text-slate-400 border border-slate-700">
                    Offline
                  </span>
                )}

                {device.serial_port ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-950 text-amber-300 border border-amber-800">
                    <Usb className="w-3 h-3 text-amber-400" />
                    Cable: {device.serial_port}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-cyan-950 text-cyan-300 border border-cyan-800">
                    <Wifi className="w-3 h-3 text-cyan-400" />
                    Wi-Fi OTA
                  </span>
                )}
              </div>
              <div className="text-xs text-slate-300 mt-1">{device.name}</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to={`/deployments?target=${device.device_id}`}
              className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 shadow-glow-cyan transition-all"
            >
              <Rocket className="w-3.5 h-3.5" />
              <span>Deploy Firmware</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-fleet-border gap-4 sm:gap-6 text-xs font-medium overflow-x-auto whitespace-nowrap pb-0.5">
        <button
          onClick={() => setActiveTab('telemetry')}
          className={`pb-3 flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'telemetry'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity className="w-4 h-4" />
          <span>Real-Time Sensor Telemetry</span>
        </button>

        <button
          onClick={() => setActiveTab('hardware')}
          className={`pb-3 flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'hardware'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <HardDrive className="w-4 h-4" />
          <span>Hardware & Diagnostics</span>
        </button>

        <button
          onClick={() => setActiveTab('deployments')}
          className={`pb-3 flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'deployments'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Rocket className="w-4 h-4" />
          <span>Deployment History ({deployments.length})</span>
        </button>
      </div>

      {/* TAB 1: Real-Time Telemetry */}
      {activeTab === 'telemetry' && (
        <div className="space-y-6">
          {/* Live Sensor Metrics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="glass-panel p-4 rounded-xl border border-fleet-border">
              <div className="flex justify-between items-center text-xs text-slate-400 mb-2">
                <span>Temperature</span>
                <Thermometer className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="text-2xl font-black text-white font-mono">
                {latestReading.temperature !== undefined ? `${latestReading.temperature.toFixed(1)} °C` : '—'}
              </div>
            </div>

            <div className="glass-panel p-4 rounded-xl border border-fleet-border">
              <div className="flex justify-between items-center text-xs text-slate-400 mb-2">
                <span>Humidity</span>
                <Droplets className="w-4 h-4 text-blue-400" />
              </div>
              <div className="text-2xl font-black text-white font-mono">
                {latestReading.humidity !== undefined ? `${latestReading.humidity.toFixed(1)} %` : '—'}
              </div>
            </div>

            <div className="glass-panel p-4 rounded-xl border border-fleet-border">
              <div className="flex justify-between items-center text-xs text-slate-400 mb-2">
                <span>Free Heap Memory</span>
                <Zap className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-black text-emerald-400 font-mono">
                {latestReading.heap_free ? `${Math.round(latestReading.heap_free / 1024)} KB` : '—'}
              </div>
            </div>

            <div className="glass-panel p-4 rounded-xl border border-fleet-border">
              <div className="flex justify-between items-center text-xs text-slate-400 mb-2">
                <span>Wi-Fi Signal (RSSI)</span>
                <Wifi className="w-4 h-4 text-purple-400" />
              </div>
              <div className="text-2xl font-black text-white font-mono">
                {latestReading.wifi_rssi ? `${latestReading.wifi_rssi} dBm` : '—'}
              </div>
            </div>
          </div>

          {/* Historical Area Chart */}
          <div className="glass-panel p-6 rounded-2xl border border-fleet-border">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-white">Live Time-Series Chart</h3>
              <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800">
                Streaming Stream Buffer ({telemetry.length} pts)
              </span>
            </div>

            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="tempG" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" stroke="#475569" fontSize={10} />
                  <YAxis stroke="#475569" fontSize={10} domain={['auto', 'auto']} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0c1322',
                      borderColor: '#1a2744',
                      borderRadius: '0.75rem',
                      fontSize: '11px',
                    }}
                  />
                  <Area type="monotone" dataKey="temperature" name="Temp (°C)" stroke="#06b6d4" strokeWidth={2} fill="url(#tempG)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Hardware & Diagnostics */}
      {activeTab === 'hardware' && (
        <div className="glass-panel p-6 rounded-2xl border border-fleet-border space-y-4 text-xs">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-fleet-darkest/60 border border-fleet-border rounded-xl space-y-2">
              <div className="text-slate-400 font-semibold uppercase tracking-wider text-[11px]">System Information</div>
              <div className="flex justify-between py-1 border-b border-fleet-border/50">
                <span className="text-slate-400">MCU Family:</span>
                <span className="font-mono text-white uppercase">{device.mcu_family}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-fleet-border/50">
                <span className="text-slate-400">Board Variant:</span>
                <span className="font-mono text-cyan-400">{device.board_variant}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-fleet-border/50">
                <span className="text-slate-400">Active Firmware Version:</span>
                <span className="font-mono text-emerald-400">v{device.firmware_version}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">System Uptime:</span>
                <span className="font-mono text-slate-200">{formatUptime(device.uptime_seconds)}</span>
              </div>
            </div>

            <div className="p-4 bg-fleet-darkest/60 border border-fleet-border rounded-xl space-y-2">
              <div className="text-slate-400 font-semibold uppercase tracking-wider text-[11px]">Network & Physical Ports</div>
              <div className="flex justify-between py-1 border-b border-fleet-border/50">
                <span className="text-slate-400">IP Address:</span>
                <span className="font-mono text-slate-200">{device.ip_address || '—'}</span>
              </div>
              <div className="py-2 border-b border-fleet-border/50">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <Cable className="w-3.5 h-3.5 text-amber-400" />
                    <span>Serial Port Interface:</span>
                  </span>
                  {!editingPort ? (
                    <button
                      type="button"
                      onClick={() => {
                        setEditingPort(true);
                        scanPorts();
                      }}
                      className="text-[10px] text-cyan-400 hover:text-cyan-300 font-semibold px-2 py-0.5 rounded bg-cyan-950/40 border border-cyan-800/60"
                    >
                      {device.serial_port ? 'Change Port' : '+ Assign Port'}
                    </button>
                  ) : (
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={handleSavePort}
                        disabled={savingPort}
                        className="text-[10px] bg-emerald-950 text-emerald-300 hover:bg-emerald-900 px-2 py-0.5 rounded border border-emerald-700 flex items-center gap-1 font-semibold"
                      >
                        <Check className="w-3 h-3" />
                        <span>{savingPort ? 'Saving...' : 'Save'}</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingPort(false)}
                        className="text-[10px] bg-slate-800 text-slate-400 hover:text-slate-200 px-1.5 py-0.5 rounded"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>

                {!editingPort ? (
                  <div className="font-mono text-slate-200 pl-5">
                    {device.serial_port ? (
                      <span className="text-amber-300 font-semibold bg-amber-950/40 px-2 py-0.5 rounded border border-amber-800/50">
                        {device.serial_port} (USB Cable Enabled)
                      </span>
                    ) : (
                      <span className="text-slate-500 italic">None assigned (using Wi-Fi OTA)</span>
                    )}
                  </div>
                ) : (
                  <div className="mt-2 space-y-2 p-2.5 bg-amber-950/20 border border-amber-900/40 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-amber-300 font-semibold">Select Detected Port:</span>
                      <button
                        type="button"
                        onClick={scanPorts}
                        disabled={scanningPorts}
                        className="text-[10px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
                      >
                        <RefreshCw className={`w-3 h-3 ${scanningPorts ? 'animate-spin' : ''}`} />
                        <span>Scan</span>
                      </button>
                    </div>

                    {availablePorts.length > 0 ? (
                      <select
                        value={portInput}
                        onChange={(e) => setPortInput(e.target.value)}
                        className="w-full bg-[#070b14] border border-amber-800/60 rounded px-2.5 py-1.5 text-slate-200 text-xs font-mono focus:outline-none focus:border-amber-400"
                      >
                        <option value="">None (Clear serial port)</option>
                        {availablePorts.map((p) => (
                          <option key={p.port} value={p.port}>
                            {p.port} — {p.description || p.manufacturer || 'Serial'} {p.is_esp_candidate ? '★ (ESP)' : ''}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={portInput}
                        onChange={(e) => setPortInput(e.target.value)}
                        placeholder="e.g. COM3 or /dev/ttyUSB0"
                        className="w-full bg-[#070b14] border border-amber-800/60 rounded px-2.5 py-1 text-slate-200 text-xs font-mono"
                      />
                    )}
                  </div>
                )}
              </div>
              <div className="flex justify-between py-1 border-b border-fleet-border/50">
                <span className="text-slate-400">Registered Date:</span>
                <span className="text-slate-200">{new Date(device.registered_at).toLocaleString()}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Last Seen Heartbeat:</span>
                <span className="text-slate-200">{device.last_seen ? new Date(device.last_seen).toLocaleString() : 'Never'}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: Deployment History */}
      {activeTab === 'deployments' && (
        <div className="glass-panel rounded-2xl border border-fleet-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0c1424] text-slate-400 font-semibold uppercase tracking-wider border-b border-fleet-border">
                <tr>
                  <th className="py-3 px-6">Deployment ID</th>
                  <th className="py-3 px-6">Target Version</th>
                  <th className="py-3 px-6">Outcome State</th>
                  <th className="py-3 px-6">Execution Timestamp</th>
                  <th className="py-3 px-6">Evidence Check</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-fleet-border/60">
                {deployments.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-500">
                      No past firmware deployments recorded for this node.
                    </td>
                  </tr>
                ) : (
                  deployments.map((job) => (
                    <tr key={job.id} className="hover:bg-fleet-cardHover/50 transition-colors">
                      <td className="py-3.5 px-6 font-mono font-medium text-slate-300">{job.id.slice(0, 8)}...</td>
                      <td className="py-3.5 px-6 font-mono text-cyan-400 font-bold">v{job.target_version}</td>
                      <td className="py-3.5 px-6">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider ${
                            job.state === 'success'
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                              : job.state === 'failed'
                              ? 'bg-rose-950 text-rose-300 border border-rose-800'
                              : 'bg-amber-950 text-amber-300 border border-amber-800'
                          }`}
                        >
                          {job.state}
                        </span>
                      </td>
                      <td className="py-3.5 px-6 text-slate-400">{new Date(job.started_at).toLocaleString()}</td>
                      <td className="py-3.5 px-6 font-mono text-slate-400 text-[11px]">
                        {job.verification_evidence ? 'Verified SHA256' : '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
