export type UserRole = 'admin' | 'operator' | 'viewer';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

export interface Device {
  id: string;
  device_id: string;
  name: string;
  mcu_family: 'esp32' | 'arduino_uno' | string;
  board_variant: string;
  sensor_types?: Record<string, string> | string[];
  firmware_version: string;
  is_online: boolean;
  last_seen?: string;
  uptime_seconds?: number;
  ip_address?: string;
  serial_port?: string;
  registered_at: string;
  description?: string;
  metadata_extra?: Record<string, any>;
  is_mock?: boolean;
}

export interface TelemetryReading {
  id: number;
  device_id: string;
  timestamp: string;
  schema_version: string;
  firmware_version?: string;
  readings: {
    temperature?: number;
    humidity?: number;
    heap_free?: number;
    wifi_rssi?: number;
    light_lux?: number;
    vcc_mv?: number;
    [key: string]: any;
  };
}

export interface FirmwareRelease {
  id: string;
  version: string;
  mcu_family: string;
  target_boards: string[];
  file_path: string;
  file_size: number;
  sha256: string;
  build_id?: string;
  release_notes?: string;
  is_approved: boolean;
  created_at: string;
  created_by?: string;
  original_filename?: string;
}

export type DeploymentState =
  | 'queued'
  | 'preflight'
  | 'transferring'
  | 'verifying'
  | 'installing'
  | 'rebooting'
  | 'health_check'
  | 'success'
  | 'failed'
  | 'cancelled'
  | 'recovery_required';

export interface DeploymentJob {
  id: string;
  device_id: string;
  release_id: string;
  rollout_id?: string;
  state: DeploymentState;
  source_version?: string;
  target_version: string;
  requested_by?: string;
  started_at: string;
  completed_at?: string;
  failure_reason?: string;
  verification_evidence?: Record<string, any>;
  progress_details?: Record<string, any>;
}

export interface DeploymentAudit {
  id: number;
  deployment_id: string;
  timestamp: string;
  event_type: string;
  old_state?: string;
  new_state?: string;
  details?: Record<string, any>;
}

export interface Alert {
  id: string;
  device_id?: string;
  alert_type: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  acknowledged: boolean;
  created_at: string;
  acknowledged_at?: string;
  acknowledged_by?: string;
}

export interface AuditLog {
  id: number;
  user_id?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  details?: Record<string, any>;
  ip_address?: string;
  timestamp: string;
}

export interface CloudStatus {
  enabled: boolean;
  api_url: string;
  connected: boolean;
  last_sync_at?: string;
  queue_size: number;
  pending_events: number;
  failed_events: number;
  sent_events: number;
  recent_errors: string[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SerialPortInfo {
  port: string;
  description: string;
  manufacturer?: string;
  hwid?: string;
  vid?: string;
  pid?: string;
  is_esp_candidate?: boolean;
  is_arduino_candidate?: boolean;
}
