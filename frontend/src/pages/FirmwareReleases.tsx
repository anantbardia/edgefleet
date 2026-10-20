import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { FirmwareRelease } from '../types';
import {
  HardDriveDownload,
  Upload,
  CheckCircle,
  XCircle,
  Copy,
  Check,
  Cpu,
  FileCode,
  ShieldCheck,
  AlertCircle,
} from 'lucide-react';

export const FirmwareReleases: React.FC = () => {
  const [releases, setReleases] = useState<FirmwareRelease[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Upload Form State
  const [file, setFile] = useState<File | null>(null);
  const [version, setVersion] = useState('');
  const [mcuFamily, setMcuFamily] = useState('esp32');
  const [targetBoards, setTargetBoards] = useState('esp32-wroom-32, esp32-s3-wroom-1');
  const [releaseNotes, setReleaseNotes] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { hasRole } = useAuth();

  const loadReleases = async () => {
    setLoading(true);
    try {
      const res = await api.firmware.list();
      setReleases(res.items);
    } catch (err) {
      console.error('Failed loading releases:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReleases();
  }, []);

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleToggleApproval = async (releaseId: string, currentStatus: boolean) => {
    if (!hasRole('admin')) return;
    try {
      await api.firmware.approve(releaseId, !currentStatus);
      loadReleases();
    } catch (err: any) {
      alert(`Failed updating approval: ${err.message}`);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setUploadError('Please select a firmware binary file (.bin or .hex)');
      return;
    }

    setUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('version', version);
    formData.append('mcu_family', mcuFamily);
    const boardsArray = targetBoards.split(',').map((b) => b.trim()).filter(Boolean);
    formData.append('target_boards', JSON.stringify(boardsArray));
    formData.append('release_notes', releaseNotes);

    try {
      await api.firmware.upload(formData);
      setShowUploadModal(false);
      setFile(null);
      setVersion('');
      setReleaseNotes('');
      loadReleases();
    } catch (err: any) {
      setUploadError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <HardDriveDownload className="w-5 h-5 text-cyan-400" />
            <span>Firmware Releases & Binary Registry</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Immutable firmware artifacts with cryptographically verified SHA-256 signatures.
          </p>
        </div>

        {hasRole('operator') && (
          <button
            onClick={() => setShowUploadModal(true)}
            className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 shadow-glow-cyan transition-all"
          >
            <Upload className="w-4 h-4" />
            <span>Upload New Firmware</span>
          </button>
        )}
      </div>

      {/* Releases Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-full py-16 text-center text-slate-500 text-xs">
            Loading verified release registry...
          </div>
        ) : releases.length === 0 ? (
          <div className="col-span-full py-16 text-center text-slate-500 text-xs">
            No firmware releases uploaded yet.
          </div>
        ) : (
          releases.map((rel) => (
            <div
              key={rel.id}
              className="glass-panel p-5 rounded-2xl border border-fleet-border flex flex-col justify-between hover:border-slate-700 transition-all"
            >
              <div>
                {/* Release top badge */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-base font-extrabold text-white">v{rel.version}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700">
                      {rel.mcu_family}
                    </span>
                  </div>

                  {rel.is_approved ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-950 text-emerald-300 border border-emerald-800">
                      <CheckCircle className="w-3 h-3 text-emerald-400" />
                      Approved
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-950 text-amber-300 border border-amber-800">
                      <AlertCircle className="w-3 h-3 text-amber-400" />
                      Pending Approval
                    </span>
                  )}
                </div>

                {/* Release notes */}
                <p className="text-xs text-slate-300 mb-4 line-clamp-2">
                  {rel.release_notes || 'No release notes provided.'}
                </p>

                {/* Target boards */}
                <div className="mb-4">
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold mb-1.5">
                    Target Board Architectures
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {rel.target_boards?.map((b) => (
                      <span key={b} className="px-2 py-0.5 bg-[#070b14] border border-fleet-border rounded text-[10px] font-mono text-cyan-400">
                        {b}
                      </span>
                    ))}
                  </div>
                </div>

                {/* SHA-256 Hash box */}
                <div className="p-2.5 bg-[#070b14] border border-fleet-border rounded-xl mb-4">
                  <div className="flex justify-between items-center text-[10px] text-slate-400 mb-1">
                    <span>SHA-256 Checksum</span>
                    <button
                      onClick={() => handleCopyHash(rel.sha256)}
                      className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
                    >
                      {copiedHash === rel.sha256 ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedHash === rel.sha256 ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                  <div className="font-mono text-[10px] text-slate-300 truncate select-all">
                    {rel.sha256}
                  </div>
                </div>
              </div>

              {/* Card Footer: Metadata and Approval action */}
              <div className="pt-3 border-t border-fleet-border/70 flex items-center justify-between text-[11px] text-slate-400">
                <span>{(rel.file_size / 1024).toFixed(1)} KB</span>

                {hasRole('admin') && (
                  <button
                    onClick={() => handleToggleApproval(rel.id, rel.is_approved)}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                      rel.is_approved
                        ? 'bg-rose-950/60 hover:bg-rose-900/60 text-rose-300 border border-rose-800'
                        : 'bg-emerald-950/60 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-800'
                    }`}
                  >
                    {rel.is_approved ? 'Revoke Approval' : 'Approve for FOTA'}
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Upload Firmware Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0c1424] border border-fleet-border rounded-2xl max-w-lg w-full p-6 shadow-2xl relative">
            <h2 className="text-lg font-bold text-white mb-1 flex items-center gap-2">
              <Upload className="w-5 h-5 text-cyan-400" />
              <span>Upload Firmware Release</span>
            </h2>
            <p className="text-xs text-slate-400 mb-6">
              The gateway will stream-calculate the SHA-256 hash and verify target header format.
            </p>

            {uploadError && (
              <div className="mb-4 p-3 bg-rose-950/50 border border-rose-800 rounded-xl text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{uploadError}</span>
              </div>
            )}

            <form onSubmit={handleUploadSubmit} className="space-y-4 text-xs">
              {/* File input */}
              <div>
                <label className="block text-slate-300 font-semibold uppercase tracking-wider mb-1">
                  Binary Image File (.bin for ESP32 / .hex for Arduino)
                </label>
                <input
                  type="file"
                  required
                  accept=".bin,.hex"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="w-full bg-[#070b14] border border-fleet-border rounded-xl p-2.5 text-slate-300 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:bg-cyan-900/60 file:text-cyan-300 file:text-xs file:font-semibold hover:file:bg-cyan-800/80"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold uppercase tracking-wider mb-1">
                    Release Version
                  </label>
                  <input
                    type="text"
                    required
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                    placeholder="e.g. 1.2.0"
                    className="w-full bg-[#070b14] border border-fleet-border rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold uppercase tracking-wider mb-1">
                    Target MCU Architecture
                  </label>
                  <select
                    value={mcuFamily}
                    onChange={(e) => {
                      setMcuFamily(e.target.value);
                      if (e.target.value === 'arduino_uno') setTargetBoards('atmega328p, uno');
                      else setTargetBoards('esp32-wroom-32, esp32-s3-wroom-1');
                    }}
                    className="w-full bg-[#070b14] border border-fleet-border rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="esp32">ESP32 (Wi-Fi OTA)</option>
                    <option value="arduino_uno">Arduino Uno (USB)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold uppercase tracking-wider mb-1">
                  Target Board Variants (comma-separated)
                </label>
                <input
                  type="text"
                  required
                  value={targetBoards}
                  onChange={(e) => setTargetBoards(e.target.value)}
                  className="w-full bg-[#070b14] border border-fleet-border rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold uppercase tracking-wider mb-1">
                  Changelog & Release Notes
                </label>
                <textarea
                  rows={3}
                  value={releaseNotes}
                  onChange={(e) => setReleaseNotes(e.target.value)}
                  placeholder="Summary of bug fixes, security patches, or feature updates..."
                  className="w-full bg-[#070b14] border border-fleet-border rounded-xl p-3 text-slate-200 focus:outline-none focus:border-cyan-500 resize-none"
                ></textarea>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-fleet-border">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="px-5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold rounded-xl shadow-glow-cyan transition-all disabled:opacity-50"
                >
                  {uploading ? 'Hashing & Uploading...' : 'Upload Release'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
