import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';
import { Device, SerialPortInfo } from '../types';
import {
  Search,
  Filter,
  Plus,
  Radio,
  Cpu,
  ArrowRight,
  RefreshCw,
  HardDrive,
  Usb,
  Cable,
} from 'lucide-react';

export const DeviceInventory: React.FC = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [search, setSearch] = useState('');
  const [mcuFilter, setMcuFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [showRegisterModal, setShowRegisterModal] = useState(false);

  // New Device Form State
  const [newDeviceId, setNewDeviceId] = useState('');
  const [newName, setNewName] = useState('');
  const [newMcu, setNewMcu] = useState('esp32');
  const [newBoard, setNewBoard] = useState('esp32-wroom-32');
  const [connectionMode, setConnectionMode] = useState<'wifi' | 'cable'>('cable');
  const [newSerialPort, setNewSerialPort] = useState('');
  const [availablePorts, setAvailablePorts] = useState<SerialPortInfo[]>([]);
  const [scanningPorts, setScanningPorts] = useState(false);

  const { hasRole } = useAuth();
  const { subscribe } = useWebSocket();

  const loadDevices = async () => {
    setLoading(true);
    try {
      const res = await api.devices.list({
        search: search || undefined,
        mcu_family: mcuFilter !== 'all' ? mcuFilter : undefined,
        is_online: statusFilter !== 'all' ? statusFilter === 'online' : undefined,
      });
      setDevices(res.items);
    } catch (err) {
      console.error('Failed fetching devices:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDevices();

    // Subscribe to status updates in real-time
    const unsub = subscribe('device_status', (msg) => {
      setDevices((prev) =>
        prev.map((d) => (d.device_id === msg.device_id ? { ...d, is_online: msg.is_online } : d))
      );
    });

    return unsub;
  }, [search, mcuFilter, statusFilter]);

  const scanSerialPorts = async () => {
    setScanningPorts(true);
    try {
      const ports = await api.devices.getSerialPorts();
      setAvailablePorts(ports);
      if (ports.length > 0 && !newSerialPort) {
        setNewSerialPort(ports[0].port);
      }
    } catch (err) {
      console.error('Failed to scan serial ports:', err);
    } finally {
      setScanningPorts(false);
    }
  };

  const handleRegisterDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const isCable = connectionMode === 'cable' || newMcu === 'arduino_uno';
      await api.devices.register({
        device_id: newDeviceId,
        name: newName,
        mcu_family: newMcu,
        board_variant: newBoard,
        serial_port: isCable ? (newSerialPort || undefined) : undefined,
      });
      setShowRegisterModal(false);
      setNewDeviceId('');
      setNewName('');
      setNewSerialPort('');
      loadDevices();
    } catch (err: any) {
      alert(`Registration failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Radio className="w-5 h-5 text-cyan-400" />
            <span>Device Inventory & Fleets</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Registered edge controllers, status heartbeats, and hardware variants.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadDevices}
            className="p-2 bg-fleet-card hover:bg-fleet-cardHover border border-fleet-border rounded-xl text-slate-400 hover:text-white transition-colors"
            title="Refresh list"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          {hasRole('admin') && (
            <button
              onClick={() => {
                setShowRegisterModal(true);
                scanSerialPorts();
              }}
              className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 shadow-glow-cyan transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Register Device</span>
            </button>
          )}
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-panel p-4 rounded-2xl border border-fleet-border flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by device ID, node name, or IP address..."
            className="w-full bg-[#0c1424] border border-fleet-border rounded-xl pl-10 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <select
            value={mcuFilter}
            onChange={(e) => setMcuFilter(e.target.value)}
            className="bg-[#0c1424] border border-fleet-border rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All MCU Architectures</option>
            <option value="esp32">ESP32 (Wi-Fi OTA)</option>
            <option value="arduino_uno">Arduino Uno (USB Serial)</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#0c1424] border border-fleet-border rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All Statuses</option>
            <option value="online">Online Nodes</option>
            <option value="offline">Offline Nodes</option>
          </select>
        </div>
      </div>

      {/* Devices Data Table */}
      <div className="glass-panel rounded-2xl border border-fleet-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#0c1424] text-slate-400 font-semibold uppercase tracking-wider border-b border-fleet-border">
              <tr>
                <th className="py-3.5 px-6">Device Node</th>
                <th className="py-3.5 px-6">Hardware Arch</th>
                <th className="py-3.5 px-6">Connectivity</th>
                <th className="py-3.5 px-6">Active Firmware</th>
                <th className="py-3.5 px-6">Interface</th>
                <th className="py-3.5 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-fleet-border/60">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    Loading registered devices...
                  </td>
                </tr>
              ) : devices.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    No devices matched the selected filter criteria.
                  </td>
                </tr>
              ) : (
                devices.map((device) => (
                  <tr key={device.id} className="hover:bg-fleet-cardHover/50 transition-colors">
                    <td className="py-4 px-6">
                      <div className="font-mono font-bold text-white text-sm">
                        {device.device_id}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5 truncate max-w-xs">
                        {device.name}
                      </div>
                    </td>

                    <td className="py-4 px-6">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-mono font-medium uppercase bg-slate-900 border border-slate-700 text-slate-300">
                        <Cpu className="w-3 h-3 text-cyan-400" />
                        {device.mcu_family}
                      </span>
                      <div className="text-[10px] text-slate-500 font-mono mt-1">
                        {device.board_variant}
                      </div>
                    </td>

                    <td className="py-4 px-6">
                      {device.is_online ? (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-950 text-emerald-300 border border-emerald-800">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 status-pulse-live"></span>
                          Online
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-slate-800 text-slate-400 border border-slate-700">
                          <span className="w-1.5 h-1.5 rounded-full bg-slate-500"></span>
                          Offline
                        </span>
                      )}
                      <div className="text-[10px] text-slate-500 mt-1">
                        {device.last_seen
                          ? `Last seen ${new Date(device.last_seen).toLocaleTimeString()}`
                          : 'Never seen'}
                      </div>
                    </td>

                    <td className="py-4 px-6">
                      <span className="font-mono text-cyan-400 font-semibold bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-900/60">
                        v{device.firmware_version}
                      </span>
                    </td>

                    <td className="py-4 px-6">
                      {device.serial_port ? (
                        <div
                          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-amber-950/40 text-amber-300 border border-amber-800/60"
                          title={`Direct USB Cable (${device.serial_port})`}
                        >
                          <Usb className="w-3 h-3 text-amber-400" />
                          <span>{device.serial_port}</span>
                        </div>
                      ) : device.ip_address ? (
                        <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono text-cyan-300 bg-cyan-950/40 border border-cyan-800/60">
                          <Radio className="w-3 h-3 text-cyan-400" />
                          <span>{device.ip_address}</span>
                        </div>
                      ) : (
                        <span className="text-slate-500 font-mono">—</span>
                      )}
                    </td>

                    <td className="py-4 px-6 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          to={`/devices/${device.device_id}`}
                          className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg flex items-center gap-1 transition-colors"
                        >
                          <span>Diagnostics</span>
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Register Device Modal */}
      {showRegisterModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0c1424] border border-fleet-border rounded-2xl max-w-md w-full p-6 shadow-2xl relative">
            <h2 className="text-lg font-bold text-white mb-1 flex items-center gap-2">
              <Plus className="w-5 h-5 text-cyan-400" />
              <span>Register Hardware Node</span>
            </h2>
            <p className="text-xs text-slate-400 mb-6">
              Manually add a node to the gateway's authorized device registry.
            </p>

            <form onSubmit={handleRegisterDevice} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold uppercase tracking-wider mb-1">
                  Device Identifier (Slug)
                </label>
                <input
                  type="text"
                  required
                  value={newDeviceId}
                  onChange={(e) => setNewDeviceId(e.target.value)}
                  placeholder="e.g. esp32-004 or uno-002"
                  className="w-full bg-[#070b14] border border-fleet-border rounded-xl px-3.5 py-2.5 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold uppercase tracking-wider mb-1">
                  Friendly Node Name
                </label>
                <input
                  type="text"
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Cleanroom Chamber Sensor"
                  className="w-full bg-[#070b14] border border-fleet-border rounded-xl px-3.5 py-2.5 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold uppercase tracking-wider mb-1">
                    MCU Family
                  </label>
                  <select
                    value={newMcu}
                    onChange={(e) => {
                      const mcu = e.target.value;
                      setNewMcu(mcu);
                      if (mcu === 'arduino_uno') {
                        setNewBoard('atmega328p');
                        setConnectionMode('cable');
                      } else {
                        setNewBoard('esp32-wroom-32');
                      }
                    }}
                    className="w-full bg-[#070b14] border border-fleet-border rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="esp32">ESP32</option>
                    <option value="arduino_uno">Arduino Uno</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold uppercase tracking-wider mb-1">
                    Board Variant
                  </label>
                  <input
                    type="text"
                    required
                    value={newBoard}
                    onChange={(e) => setNewBoard(e.target.value)}
                    className="w-full bg-[#070b14] border border-fleet-border rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                  />
                </div>
              </div>

              {/* Connection Interface Selector */}
              <div>
                <label className="block text-slate-300 font-semibold uppercase tracking-wider mb-1">
                  Connection Interface
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setConnectionMode('cable')}
                    className={`py-2 px-3 rounded-xl border text-left flex items-center gap-2 transition-all ${
                      connectionMode === 'cable' || newMcu === 'arduino_uno'
                        ? 'bg-amber-950/40 border-amber-500/70 text-amber-300 font-semibold'
                        : 'bg-[#070b14] border-fleet-border text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Usb className="w-4 h-4 text-amber-400" />
                    <div>
                      <div className="text-xs">USB Cable</div>
                      <div className="text-[10px] text-slate-400">Direct esptool flashing</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    disabled={newMcu === 'arduino_uno'}
                    onClick={() => setConnectionMode('wifi')}
                    className={`py-2 px-3 rounded-xl border text-left flex items-center gap-2 transition-all ${
                      connectionMode === 'wifi' && newMcu !== 'arduino_uno'
                        ? 'bg-cyan-950/40 border-cyan-500/70 text-cyan-300 font-semibold'
                        : 'bg-[#070b14] border-fleet-border text-slate-400 hover:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed'
                    }`}
                  >
                    <Radio className="w-4 h-4 text-cyan-400" />
                    <div>
                      <div className="text-xs">Wi-Fi Network</div>
                      <div className="text-[10px] text-slate-400">MQTT & HTTP OTA</div>
                    </div>
                  </button>
                </div>
              </div>

              {(connectionMode === 'cable' || newMcu === 'arduino_uno') && (
                <div className="p-3 bg-amber-950/20 border border-amber-900/40 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-amber-300 font-semibold uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                      <Cable className="w-3.5 h-3.5 text-amber-400" />
                      <span>Serial Port Interface</span>
                    </label>
                    <button
                      type="button"
                      onClick={scanSerialPorts}
                      disabled={scanningPorts}
                      className="text-[10px] text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1"
                    >
                      <RefreshCw className={`w-3 h-3 ${scanningPorts ? 'animate-spin' : ''}`} />
                      <span>{scanningPorts ? 'Scanning...' : 'Scan Ports'}</span>
                    </button>
                  </div>

                  {availablePorts.length > 0 ? (
                    <select
                      value={newSerialPort}
                      onChange={(e) => setNewSerialPort(e.target.value)}
                      className="w-full bg-[#070b14] border border-amber-800/60 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-400 font-mono text-xs"
                    >
                      <option value="">Select connected port...</option>
                      {availablePorts.map((p) => (
                        <option key={p.port} value={p.port}>
                          {p.port} — {p.description || p.manufacturer || 'Serial Port'} {p.is_esp_candidate ? '★ (ESP)' : ''}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      value={newSerialPort}
                      onChange={(e) => setNewSerialPort(e.target.value)}
                      placeholder="e.g. COM3 or /dev/ttyUSB0"
                      className="w-full bg-[#070b14] border border-amber-800/60 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-400 font-mono text-xs"
                    />
                  )}
                  <p className="text-[10px] text-slate-400 leading-relaxed">
                    Connecting via USB cable enables direct cable flashing using <code>esptool</code> at 460800 baud and serial telemetry ingestion.
                  </p>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4 border-t border-fleet-border">
                <button
                  type="button"
                  onClick={() => setShowRegisterModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold rounded-xl shadow-glow-cyan transition-all"
                >
                  Save Device
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
