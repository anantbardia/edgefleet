"""Initial schema migration for EdgeFleet.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-19 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), default='', nullable=False),
        sa.Column('role', sa.String(20), default='viewer', nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
    )

    # Devices table
    op.create_table(
        'devices',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_id', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('mcu_family', sa.String(32), nullable=False, index=True),
        sa.Column('board_variant', sa.String(64), nullable=True),
        sa.Column('sensor_types', sa.JSON(), nullable=True),
        sa.Column('firmware_version', sa.String(32), default='0.0.0', nullable=False),
        sa.Column('is_online', sa.Boolean(), default=False, nullable=False, index=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('uptime_seconds', sa.Integer(), default=0, nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('registered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_metadata', sa.JSON(), nullable=True),
    )

    # Telemetry readings table
    op.create_table(
        'telemetry_readings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('device_id', sa.String(64), nullable=False, index=True),
        sa.Column('schema_version', sa.String(10), default='1.0', nullable=False),
        sa.Column('readings', sa.JSON(), nullable=False),
        sa.Column('firmware_version', sa.String(32), default='', nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
    )

    # Firmware releases table
    op.create_table(
        'firmware_releases',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('version', sa.String(32), nullable=False, index=True),
        sa.Column('mcu_family', sa.String(32), nullable=False, index=True),
        sa.Column('target_boards', sa.JSON(), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('build_id', sa.String(64), nullable=True),
        sa.Column('release_notes', sa.Text(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), default=False, nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('signature_metadata', sa.JSON(), nullable=True),
    )

    # Deployment jobs table
    op.create_table(
        'deployment_jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_id', sa.String(64), nullable=False, index=True),
        sa.Column('release_id', sa.String(36), nullable=False, index=True),
        sa.Column('rollout_id', sa.String(36), nullable=True, index=True),
        sa.Column('state', sa.String(20), default='QUEUED', nullable=False, index=True),
        sa.Column('source_version', sa.String(32), default='', nullable=False),
        sa.Column('target_version', sa.String(32), nullable=False),
        sa.Column('requested_by', sa.String(36), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('verification_evidence', sa.JSON(), nullable=True),
        sa.Column('progress_details', sa.JSON(), nullable=True),
    )

    # Deployment audits table
    op.create_table(
        'deployment_audits',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('deployment_id', sa.String(36), nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('old_state', sa.String(20), nullable=False),
        sa.Column('new_state', sa.String(20), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
    )

    # Alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('device_id', sa.String(64), nullable=True, index=True),
        sa.Column('alert_type', sa.String(50), nullable=False, index=True),
        sa.Column('severity', sa.String(20), default='info', nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('acknowledged', sa.Boolean(), default=False, nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', sa.String(36), nullable=True),
    )

    # Audit logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(36), nullable=True),
        sa.Column('action', sa.String(100), nullable=False, index=True),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(36), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
    )

    # Cloud sync queue table
    op.create_table(
        'cloud_sync_queue',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.String(36), unique=True, nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False, index=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer(), default=0, nullable=False),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(20), default='pending', nullable=False, index=True),
        sa.Column('error', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('cloud_sync_queue')
    op.drop_table('audit_logs')
    op.drop_table('alerts')
    op.drop_table('deployment_audits')
    op.drop_table('deployment_jobs')
    op.drop_table('firmware_releases')
    op.drop_table('telemetry_readings')
    op.drop_table('devices')
    op.drop_table('users')
