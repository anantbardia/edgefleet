import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';
import { DeploymentJob, Device, FirmwareRelease } from '../types';
import {
  Rocket,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
  ShieldCheck,
  RefreshCw,
  Ban,
  Layers,
  ArrowRight,
  HardDrive,
  Usb,
  Cable,
  Radio,
} from 'lucide-react';

const DEPLOYMENT_STEPS = [
  'queued',
  'preflight',
  'transferring',
  'verifying',
  'installing',
  'rebooting',
  'health_check',
  'success',
];

export const DeploymentManager: React.FC = () => {
  const [searchParams] = useSearchParams();
  const preselectDevice = searchParams.get('target');

  const [devices, setDevices] = useState<Device[]>([]);
  const [releases, setReleases] = useState<FirmwareRelease[]>([]);
  const [deployments, setDeployments] = useState<DeploymentJob[]>([]);
  const [loading, setLoading] = useState(true);

  // Wizard state
  const [selectedDevice, setSelectedDevice] = useState<string>(preselectDevice || '');
  const [selectedRelease, setSelectedRelease] = useState<string>('');
  const [preflightData, setPreflightData] = useState<any | null>(null);
  const [preflightLoading, setPreflightLoading] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const { hasRole } = useAuth();
  const { subscribe } = useWebSocket();

  const loadData = async () => {
    try {
      const [devRes, relRes, depRes] = await Promise.all([
        api.devices.list({ page_size: 50 }),
        api.firmware.list({ is_approved: true }),
        api.deployments.list({ page_size: 25 }),
      ]);
      setDevices(devRes.items);
      setReleases(relRes.items);
      setDeployments(depRes.items);

      if (preselectDevice && !selectedDevice) {
        setSelectedDevice(preselectDevice);
      }
    } catch (err) {
      console.error('Error loading deployment manager data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();

    // Listen to real-time deployment updates
    const unsub = subscribe('deployment_update', (msg) => {
      setDeployments((prev) =>
        prev.map((d) => (d.id === msg.deployment_id ? { ...d, state: msg.state, progress_details: msg.details } : d))
      );
    });

    return unsub;
  }, []);

  const targetDevObj = devices.find((d) => d.device_id === selectedDevice || d.id === selectedDevice);
  const compatibleReleases = releases.filter((r) => !targetDevObj || r.mcu_family === targetDevObj.mcu_family);

  const runPreflight = async () => {
    if (!targetDevObj || !selectedRelease) return;
    setPreflightLoading(true);
    try {
      const res = await api.deployments.preflight([targetDevObj.id], selectedRelease);
      setPreflightData(res);
    } catch (err: any) {
      alert(`Preflight check failed: ${err.message}`);
    } finally {
      setPreflightLoading(false);
    }
  };

  const handleLaunchDeployment = async () => {
    if (!targetDevObj || !selectedRelease || !preflightData?.confirmation_token) return;
    setLaunching(true);
    try {
      const res = await api.deployments.create(
        [targetDevObj.id],
        selectedRelease,
        preflightData.confirmation_token
      );
      const jobs = Array.isArray(res) ? res : ((res as any)?.jobs || []);
      if (jobs.length > 0) {
        setActiveJobId(jobs[0].id);
      }
      setPreflightData(null);
      loadData();
    } catch (err: any) {
      alert(`Failed to launch deployment: ${err.message}`);
    } finally {
      setLaunching(false);
    }
  };

  const handleCancelDeployment = async (jobId: string) => {
    try {
      await api.deployments.cancel(jobId, 'Operator initiated abort from dashboard');
      loadData();
    } catch (err: any) {
      alert(`Cancellation failed: ${err.message}`);
    }
  };

  const activeJob =
    deployments.find((d) => d.id === activeJobId) ||
    deployments.find((d) => !['success', 'failed', 'cancelled'].includes(d.state)) ||
    (deployments.length > 0 ? deployments[0] : undefined);

  const getStepStatus = (stepName: string, currentState: string) => {
    const stepIdx = DEPLOYMENT_STEPS.indexOf(stepName);
    const currIdx = DEPLOYMENT_STEPS.indexOf(currentState);

    if (currentState === 'failed' || currentState === 'cancelled') {
      const stage = activeJob?.progress_details?.stage;
      const failedIdx = stage ? DEPLOYMENT_STEPS.indexOf(stage) : 1;
      if (stepIdx === Math.max(0, failedIdx)) return 'error';
      if (stepIdx < failedIdx) return 'completed';
      return 'pending';
    }
    if (stepIdx < currIdx || currentState === 'success') return 'completed';
    if (stepIdx === currIdx) return 'active';
    return 'pending';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Rocket className="w-5 h-5 text-cyan-400" />
            <span>FOTA Deployment Engine & Rollouts</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Orchestrate OTA firmware transitions with automated preflight checks and rollback safety.
          </p>
        </div>

        <button
          onClick={loadData}
          className="p-2 bg-fleet-card hover:bg-fleet-cardHover border border-fleet-border rounded-xl text-slate-400 hover:text-white transition-colors self-start sm:self-auto"
          title="Refresh rollout queue"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Live Active Deployment Stepper Banner */}
      {activeJob && (
        <div className="glass-panel p-6 rounded-2xl border border-cyan-800/80 shadow-glow-cyan">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <div>
              <div className={`text-xs font-mono font-bold uppercase tracking-wider mb-1 flex items-center gap-2 ${
                activeJob.state === 'failed' ? 'text-rose-400' : activeJob.state === 'success' ? 'text-emerald-400' : 'text-cyan-400'
              }`}>
                <span>{activeJob.state === 'failed' ? 'Job Failed' : activeJob.state === 'success' ? 'Job Completed' : 'Active Job in Progress'}: {activeJob.id.slice(0, 8)}...</span>
                <span className={`text-[10px] px-2 py-0.5 rounded uppercase font-semibold ${
                  activeJob.state === 'failed' ? 'bg-rose-950 text-rose-300 border border-rose-800' : activeJob.state === 'success' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                }`}>
                  {activeJob.state}
                </span>
              </div>
              <div className="text-base font-extrabold text-white flex items-center gap-3">
                <span>Target: {activeJob.device_id}</span>
                <span className="font-mono text-xs px-2.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                  Target v{activeJob.target_version}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {['queued', 'preflight', 'transferring', 'verifying'].includes(activeJob.state) && (
                <button
                  onClick={() => handleCancelDeployment(activeJob.id)}
                  className="px-3.5 py-1.5 bg-rose-950/80 hover:bg-rose-900 border border-rose-800 text-rose-300 text-xs font-semibold rounded-xl flex items-center gap-1.5 transition-colors"
                >
                  <Ban className="w-3.5 h-3.5" />
                  <span>Abort Safely</span>
                </button>
              )}
            </div>
          </div>

          {/* Stepper */}
          <div className="grid grid-cols-4 sm:grid-cols-8 gap-2">
            {DEPLOYMENT_STEPS.map((step) => {
              const status = getStepStatus(step, activeJob.state);
              return (
                <div key={step} className="flex flex-col items-center text-center">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all mb-1.5 ${
                      status === 'completed'
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-600'
                        : status === 'active'
                        ? 'bg-cyan-950 text-cyan-300 border border-cyan-400 animate-pulse shadow-glow-cyan'
                        : status === 'error'
                        ? 'bg-rose-950 text-rose-400 border border-rose-600'
                        : 'bg-slate-900 text-slate-500 border border-slate-800'
                    }`}
                  >
                    {status === 'completed' ? '✓' : status === 'active' ? '●' : '○'}
                  </div>
                  <span className="text-[10px] font-mono uppercase text-slate-400">
                    {step.replace('_', ' ')}
                  </span>
                </div>
              );
            })}
          </div>

          {activeJob.failure_reason && (
            <div className="mt-4 p-3 bg-rose-950/70 border border-rose-800 rounded-xl text-rose-300 text-xs flex items-center gap-2">
              <XCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span><strong>Deployment Error:</strong> {activeJob.failure_reason}</span>
            </div>
          )}
        </div>
      )}

      {/* Deployment Creation Wizard */}
      <div className="glass-panel p-6 rounded-2xl border border-fleet-border">
        <h2 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
          <Rocket className="w-4 h-4 text-cyan-400" />
          <span>Launch New Firmware Deployment</span>
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          {/* 1. Device */}
          <div>
            <label className="block text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1.5">
              1. Target Hardware Node
            </label>
            <select
              value={selectedDevice}
              onChange={(e) => {
                setSelectedDevice(e.target.value);
                setPreflightData(null);
              }}
              className="w-full bg-[#0c1424] border border-fleet-border rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="">Select Target Device...</option>
              {devices.map((d) => (
                <option key={d.id} value={d.device_id}>
                  {d.device_id} ({d.mcu_family.toUpperCase()} - {d.name})
                </option>
              ))}
            </select>
            {targetDevObj && (
              <div className="mt-2">
                {targetDevObj.serial_port ? (
                  <div className="p-2 bg-amber-950/40 border border-amber-800/60 rounded-xl flex items-center gap-2 text-[11px] text-amber-300">
                    <Usb className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <span>
                      Wired Flash: Direct USB cable via <strong>esptool</strong> on{' '}
                      <span className="font-mono underline">{targetDevObj.serial_port}</span> (460800 baud)
                    </span>
                  </div>
                ) : (
                  <div className="p-2 bg-cyan-950/40 border border-cyan-800/60 rounded-xl flex items-center gap-2 text-[11px] text-cyan-300">
                    <Radio className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                    <span>Wireless Flash: Dual-Partition Wi-Fi OTA via MQTT & HTTP download</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 2. Firmware */}
          <div>
            <label className="block text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1.5">
              2. Approved Firmware Release
            </label>
            <select
              value={selectedRelease}
              onChange={(e) => {
                setSelectedRelease(e.target.value);
                setPreflightData(null);
              }}
              disabled={!selectedDevice}
              className="w-full bg-[#0c1424] border border-fleet-border rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 disabled:opacity-50"
            >
              <option value="">Select Release Version...</option>
              {compatibleReleases.map((r) => (
                <option key={r.id} value={r.id}>
                  v{r.version} [{r.mcu_family}] — {r.release_notes?.slice(0, 30)}
                </option>
              ))}
            </select>
          </div>

          {/* 3. Action */}
          <div className="flex flex-col justify-end">
            {!preflightData ? (
              <button
                type="button"
                onClick={runPreflight}
                disabled={!selectedDevice || !selectedRelease || preflightLoading}
                className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs rounded-xl transition-all disabled:opacity-40 flex items-center justify-center gap-2"
              >
                {preflightLoading ? 'Validating...' : 'Run Preflight Compatibility'}
              </button>
            ) : (
              <button
                type="button"
                onClick={handleLaunchDeployment}
                disabled={launching || !preflightData.all_compatible}
                className="w-full py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs rounded-xl shadow-glow-cyan transition-all flex items-center justify-center gap-2"
              >
                {launching ? 'Queuing Job...' : 'Confirm & Deploy'}
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Preflight Report Card */}
        {preflightData && (
          <div className="p-4 bg-[#070b14] border border-fleet-border rounded-xl mt-4 text-xs">
            <div className="flex items-center justify-between mb-2">
              <span className="font-semibold text-white flex items-center gap-1.5">
                {preflightData.all_compatible ? (
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                ) : (
                  <XCircle className="w-4 h-4 text-rose-400" />
                )}
                Preflight Compatibility Verification
              </span>
              <span className="text-[10px] font-mono text-slate-400">
                Token: {preflightData.confirmation_token.slice(0, 16)}...
              </span>
            </div>

            {preflightData.results.map((r: any) => (
              <div key={r.device_id} className="space-y-1">
                {r.warnings?.map((w: string, idx: number) => (
                  <div key={idx} className="text-amber-400 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                    <span>Warning: {w}</span>
                  </div>
                ))}
                {r.errors?.map((err: string, idx: number) => (
                  <div key={idx} className="text-rose-400 flex items-center gap-1.5">
                    <XCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>Error: {err}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Deployment History Table */}
      <div className="glass-panel rounded-2xl border border-fleet-border overflow-hidden">
        <div className="p-4 bg-[#0c1424] border-b border-fleet-border flex justify-between items-center">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">
            Deployment History & Audit Log
          </h3>
          <span className="text-[11px] text-slate-400 font-mono">
            {deployments.length} Jobs Total
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#0c1424]/80 text-slate-400 font-semibold uppercase tracking-wider border-b border-fleet-border">
              <tr>
                <th className="py-3 px-6">Job ID</th>
                <th className="py-3 px-6">Device</th>
                <th className="py-3 px-6">Version Target</th>
                <th className="py-3 px-6">State</th>
                <th className="py-3 px-6">Started</th>
                <th className="py-3 px-6">Duration</th>
                <th className="py-3 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-fleet-border/60">
              {deployments.map((job) => (
                <tr key={job.id} className="hover:bg-fleet-cardHover/50 transition-colors">
                  <td className="py-3.5 px-6 font-mono text-slate-400">{job.id.slice(0, 8)}...</td>
                  <td className="py-3.5 px-6 font-mono font-bold text-white">{job.device_id}</td>
                  <td className="py-3.5 px-6 font-mono text-cyan-400 font-semibold">v{job.target_version}</td>
                  <td className="py-3.5 px-6">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider ${
                        job.state === 'success'
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                          : job.state === 'failed'
                          ? 'bg-rose-950 text-rose-300 border border-rose-800'
                          : job.state === 'cancelled'
                          ? 'bg-slate-800 text-slate-400 border border-slate-700'
                          : 'bg-amber-950 text-amber-300 border border-amber-800 animate-pulse'
                      }`}
                    >
                      {job.state}
                    </span>
                  </td>
                  <td className="py-3.5 px-6 text-slate-400">{new Date(job.started_at).toLocaleString()}</td>
                  <td className="py-3.5 px-6 font-mono text-slate-400">
                    {job.completed_at
                      ? `${Math.round((new Date(job.completed_at).getTime() - new Date(job.started_at).getTime()) / 1000)}s`
                      : '—'}
                  </td>
                  <td className="py-3.5 px-6 text-right">
                    {['queued', 'preflight', 'transferring', 'verifying'].includes(job.state) && (
                      <button
                        onClick={() => handleCancelDeployment(job.id)}
                        className="px-2.5 py-1 bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 text-[11px] rounded transition-colors"
                      >
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
