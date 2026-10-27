import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';
import { Alert, AuditLog } from '../types';
import {
  Bell,
  CheckCircle,
  AlertTriangle,
  Info,
  ShieldAlert,
  Search,
  Filter,
  RefreshCw,
  FileText,
} from 'lucide-react';

export const AlertsLogs: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'alerts' | 'audit'>('alerts');
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterAcknowledged, setFilterAcknowledged] = useState<'all' | 'unacked' | 'acked'>('unacked');

  const { hasRole } = useAuth();
  const { subscribe } = useWebSocket();

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const ackParam =
        filterAcknowledged === 'all' ? undefined : filterAcknowledged === 'acked';
      const [alertRes, auditRes] = await Promise.all([
        api.alerts.list({ acknowledged: ackParam, page_size: 50 }),
        api.alerts.listAuditLogs(1, 50).catch(() => ({ items: [], total: 0 })),
      ]);
      setAlerts(alertRes.items);
      setAuditLogs(auditRes.items);
    } catch (err) {
      console.error('Failed loading alerts and logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();

    // Subscribe to new real-time alerts
    const unsub = subscribe('alert', (msg) => {
      setAlerts((prev) => [msg.alert, ...prev]);
    });

    return unsub;
  }, [filterAcknowledged]);

  const handleAcknowledge = async (alertId: string) => {
    try {
      await api.alerts.acknowledge(alertId);
      loadAlerts();
    } catch (err: any) {
      alert(`Failed to acknowledge alert: ${err.message}`);
    }
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case 'critical':
      case 'error':
        return 'bg-rose-950 text-rose-300 border-rose-800';
      case 'warning':
        return 'bg-amber-950 text-amber-300 border-amber-800';
      default:
        return 'bg-blue-950 text-blue-300 border-blue-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Bell className="w-5 h-5 text-cyan-400" />
            <span>Alerts & Operations Audit Log</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Fleet exceptions, heartbeat dropouts, and immutable security audit records.
          </p>
        </div>

        <button
          onClick={loadAlerts}
          className="p-2 bg-fleet-card hover:bg-fleet-cardHover border border-fleet-border rounded-xl text-slate-400 hover:text-white transition-colors self-start sm:self-auto"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-fleet-border gap-4 sm:gap-6 text-xs font-medium overflow-x-auto whitespace-nowrap pb-0.5">
        <button
          onClick={() => setActiveTab('alerts')}
          className={`pb-3 flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'alerts'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          <span>Operational Alerts ({alerts.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('audit')}
          className={`pb-3 flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'audit'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Security Audit Trail ({auditLogs.length})</span>
        </button>
      </div>

      {/* TAB 1: Alerts */}
      {activeTab === 'alerts' && (
        <div className="space-y-4">
          {/* Filter */}
          <div className="flex items-center gap-3">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={filterAcknowledged}
              onChange={(e) => setFilterAcknowledged(e.target.value as any)}
              className="bg-[#0c1424] border border-fleet-border rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="unacked">Unacknowledged Only</option>
              <option value="acked">Acknowledged Alerts</option>
              <option value="all">All Alerts</option>
            </select>
          </div>

          <div className="glass-panel rounded-2xl border border-fleet-border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
              <thead className="bg-[#0c1424] text-slate-400 font-semibold uppercase tracking-wider border-b border-fleet-border">
                <tr>
                  <th className="py-3 px-6">Severity</th>
                  <th className="py-3 px-6">Device Node</th>
                  <th className="py-3 px-6">Type & Message</th>
                  <th className="py-3 px-6">Detected At</th>
                  <th className="py-3 px-6 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-fleet-border/60">
                {loading ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-500">
                      Loading alerts...
                    </td>
                  </tr>
                ) : alerts.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-500">
                      No matching alerts found in this view.
                    </td>
                  </tr>
                ) : (
                  alerts.map((alert) => (
                    <tr key={alert.id} className="hover:bg-fleet-cardHover/50 transition-colors">
                      <td className="py-4 px-6">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider border ${getSeverityBadge(
                            alert.severity
                          )}`}
                        >
                          {alert.severity}
                        </span>
                      </td>

                      <td className="py-4 px-6 font-mono font-semibold text-cyan-400">
                        {alert.device_id || 'SYSTEM'}
                      </td>

                      <td className="py-4 px-6">
                        <div className="font-semibold text-white">{alert.alert_type}</div>
                        <div className="text-slate-400 text-[11px] mt-0.5">{alert.message}</div>
                      </td>

                      <td className="py-4 px-6 text-slate-400">
                        {new Date(alert.created_at).toLocaleString()}
                      </td>

                      <td className="py-4 px-6 text-right">
                        {!alert.acknowledged ? (
                          hasRole('operator') && (
                            <button
                              onClick={() => handleAcknowledge(alert.id)}
                              className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition-colors border border-slate-700"
                            >
                              Acknowledge
                            </button>
                          )
                        ) : (
                          <span className="text-emerald-400 text-xs flex items-center justify-end gap-1">
                            <CheckCircle className="w-3.5 h-3.5" />
                            <span>Acknowledged</span>
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Audit Logs */}
      {activeTab === 'audit' && (
        <div className="glass-panel rounded-2xl border border-fleet-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
            <thead className="bg-[#0c1424] text-slate-400 font-semibold uppercase tracking-wider border-b border-fleet-border">
              <tr>
                <th className="py-3 px-6">Timestamp</th>
                <th className="py-3 px-6">Action</th>
                <th className="py-3 px-6">Resource</th>
                <th className="py-3 px-6">IP Address</th>
                <th className="py-3 px-6">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-fleet-border/60">
              {auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-slate-500">
                    No security audit logs recorded yet.
                  </td>
                </tr>
              ) : (
                auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-fleet-cardHover/50 transition-colors">
                    <td className="py-3.5 px-6 font-mono text-slate-400">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-6 font-semibold text-white">{log.action}</td>
                    <td className="py-3.5 px-6 font-mono text-cyan-400">
                      {log.resource_type}: {log.resource_id?.slice(0, 8) || '—'}
                    </td>
                    <td className="py-3.5 px-6 font-mono text-slate-400">{log.ip_address || 'local'}</td>
                    <td className="py-3.5 px-6 font-mono text-[11px] text-slate-400 max-w-xs truncate">
                      {JSON.stringify(log.details || {})}
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
