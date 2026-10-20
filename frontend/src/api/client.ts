import {
  Alert,
  AuditLog,
  CloudStatus,
  DeploymentAudit,
  DeploymentJob,
  Device,
  FirmwareRelease,
  PaginatedResponse,
  TelemetryReading,
  User,
  SerialPortInfo,
} from '../types';

const BASE_URL = '/api';

class ApiClient {
  private getAccessToken(): string | null {
    return localStorage.getItem('edgefleet_access_token');
  }

  private setTokens(access: string, refresh?: string) {
    localStorage.setItem('edgefleet_access_token', access);
    if (refresh) localStorage.setItem('edgefleet_refresh_token', refresh);
  }

  public clearTokens() {
    localStorage.removeItem('edgefleet_access_token');
    localStorage.removeItem('edgefleet_refresh_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getAccessToken();
    const headers = new Headers(options.headers || {});

    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    let response = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    // Handle token expiration & automatic refresh
    if (response.status === 401) {
      const refreshToken = localStorage.getItem('edgefleet_refresh_token');
      if (refreshToken && endpoint !== '/auth/login' && endpoint !== '/auth/refresh') {
        try {
          const refreshRes = await fetch(`${BASE_URL}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });

          if (refreshRes.ok) {
            const data = await refreshRes.json();
            this.setTokens(data.access_token, data.refresh_token);
            headers.set('Authorization', `Bearer ${data.access_token}`);
            response = await fetch(`${BASE_URL}${endpoint}`, {
              ...options,
              headers,
            });
          } else {
            this.clearTokens();
            window.location.href = '/login';
          }
        } catch {
          this.clearTokens();
          window.location.href = '/login';
        }
      }
    }

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      let msg = 'An unexpected API error occurred';
      if (typeof err.detail === 'string') {
        msg = err.detail;
      } else if (Array.isArray(err.detail)) {
        msg = err.detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ');
      } else if (err.detail && typeof err.detail === 'object') {
        msg = err.detail.msg || JSON.stringify(err.detail);
      }
      throw new Error(msg);
    }

    return response.json();
  }

  // ── Authentication ────────────────────────────────────────────────────────
  auth = {
    login: async (email: string, password: string) => {
      const data = await this.request<{ access_token: string; refresh_token: string }>(
        '/auth/login',
        {
          method: 'POST',
          body: JSON.stringify({ email, password }),
        }
      );
      this.setTokens(data.access_token, data.refresh_token);
      return data;
    },
    getMe: () => this.request<User>('/auth/me'),
    logout: () => this.clearTokens(),
  };

  // ── Devices ───────────────────────────────────────────────────────────────
  devices = {
    list: (params: { page?: number; page_size?: number; mcu_family?: string; is_online?: boolean; search?: string } = {}) => {
      const q = new URLSearchParams();
      if (params.page) q.set('page', params.page.toString());
      if (params.page_size) q.set('page_size', params.page_size.toString());
      if (params.mcu_family) q.set('mcu_family', params.mcu_family);
      if (params.is_online !== undefined) q.set('is_online', String(params.is_online));
      if (params.search) q.set('search', params.search);
      return this.request<PaginatedResponse<Device>>(`/devices?${q.toString()}`);
    },
    get: (deviceId: string) => this.request<Device>(`/devices/${deviceId}`),
    register: (device: Partial<Device>) =>
      this.request<Device>('/devices', {
        method: 'POST',
        body: JSON.stringify(device),
      }),
    update: (deviceId: string, updates: Partial<Device>) =>
      this.request<Device>(`/devices/${deviceId}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
      }),
    delete: (deviceId: string) =>
      this.request<{ message: string }>(`/devices/${deviceId}`, {
        method: 'DELETE',
      }),
    getSerialPorts: () => this.request<SerialPortInfo[]>('/devices/ports/serial'),
  };

  // ── Telemetry ─────────────────────────────────────────────────────────────
  telemetry = {
    getHistory: (deviceId: string, limit = 50) =>
      this.request<PaginatedResponse<TelemetryReading>>(`/devices/${deviceId}/telemetry?page_size=${limit}`),
    getLatest: (deviceId: string) =>
      this.request<TelemetryReading>(`/devices/${deviceId}/telemetry/latest`),
  };

  // ── Firmware ──────────────────────────────────────────────────────────────
  firmware = {
    list: (params: { mcu_family?: string; is_approved?: boolean } = {}) => {
      const q = new URLSearchParams();
      if (params.mcu_family) q.set('mcu_family', params.mcu_family);
      if (params.is_approved !== undefined) q.set('is_approved', String(params.is_approved));
      return this.request<PaginatedResponse<FirmwareRelease>>(`/firmware?${q.toString()}`);
    },
    get: (releaseId: string) => this.request<FirmwareRelease>(`/firmware/${releaseId}`),
    upload: (formData: FormData) =>
      this.request<FirmwareRelease>('/firmware/upload', {
        method: 'POST',
        body: formData,
      }),
    approve: (releaseId: string, is_approved = true) =>
      this.request<FirmwareRelease>(`/firmware/${releaseId}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_approved }),
      }),
  };

  // ── Deployments ───────────────────────────────────────────────────────────
  deployments = {
    preflight: (deviceIds: string[], releaseId: string) =>
      this.request<{
        results: Array<{ device_id: string; compatible: boolean; warnings: string[]; errors: string[] }>;
        all_compatible: boolean;
        confirmation_token: string;
      }>('/deployments/preflight', {

        method: 'POST',
        body: JSON.stringify({ device_ids: deviceIds, release_id: releaseId }),
      }),
    create: (deviceIds: string[], releaseId: string, confirmationToken: string) =>
      this.request<{ jobs: DeploymentJob[]; rollout_id?: string }>('/deployments', {
        method: 'POST',
        body: JSON.stringify({
          device_ids: deviceIds,
          release_id: releaseId,
          confirmation_token: confirmationToken,
        }),
      }),
    list: (params: { page?: number; page_size?: number; state?: string } = {}) => {
      const q = new URLSearchParams();
      if (params.page) q.set('page', params.page.toString());
      if (params.page_size) q.set('page_size', params.page_size.toString());
      if (params.state) q.set('state', params.state);
      return this.request<PaginatedResponse<DeploymentJob>>(`/deployments?${q.toString()}`);
    },
    get: (id: string) => this.request<DeploymentJob>(`/deployments/${id}`),
    cancel: (id: string, reason = 'Operator cancelled') =>
      this.request<{ message: string; deployment_id: string }>(`/deployments/${id}/cancel`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      }),
    getLogs: (id: string) => this.request<DeploymentAudit[]>(`/deployments/${id}/logs`),
  };

  // ── Alerts & Audits ───────────────────────────────────────────────────────
  alerts = {
    list: (params: { page?: number; page_size?: number; acknowledged?: boolean } = {}) => {
      const q = new URLSearchParams();
      if (params.page) q.set('page', params.page.toString());
      if (params.page_size) q.set('page_size', params.page_size.toString());
      if (params.acknowledged !== undefined) q.set('acknowledged', String(params.acknowledged));
      return this.request<PaginatedResponse<Alert>>(`/alerts?${q.toString()}`);
    },
    acknowledge: (alertId: string) =>
      this.request<Alert>(`/alerts/${alertId}/acknowledge`, {
        method: 'POST',
      }),
    listAuditLogs: (page = 1, page_size = 30) =>
      this.request<PaginatedResponse<AuditLog>>(`/audit?page=${page}&page_size=${page_size}`),
  };

  // ── Cloud Sync ────────────────────────────────────────────────────────────
  cloud = {
    getStatus: () => this.request<CloudStatus>('/cloud/status'),
    syncNow: () =>
      this.request<{ message: string; events_processed: number; success: boolean }>('/cloud/sync-now', {
        method: 'POST',
      }),
  };

  // ── System Health ─────────────────────────────────────────────────────────
  health = {
    check: () => this.request<{ status: string; version: string; uptime: number }>('/health'),
  };
}

export const api = new ApiClient();
