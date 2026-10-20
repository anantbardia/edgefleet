import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Layers,
  HardDriveDownload,
  Rocket,
  Bell,
  Settings,
  Radio,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { label: 'Overview', to: '/', icon: LayoutDashboard },
    { label: 'Device Inventory', to: '/devices', icon: Layers },
    { label: 'Firmware Releases', to: '/firmware', icon: HardDriveDownload },
    { label: 'Deployment Manager', to: '/deployments', icon: Rocket },
    { label: 'Alerts & Audit Logs', to: '/alerts', icon: Bell },
    { label: 'Settings & Cloud', to: '/settings', icon: Settings },
  ];

  return (
    <aside className="w-64 border-r border-fleet-border bg-[#090e1a] flex flex-col justify-between shrink-0 h-screen sticky top-0">
      <div>
        {/* Brand header */}
        <div className="h-16 flex items-center px-6 border-b border-fleet-border gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center shadow-glow-cyan">
            <Radio className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-extrabold tracking-wide text-lg bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
              EdgeFleet
            </div>
            <div className="text-[10px] text-slate-500 font-mono tracking-widest uppercase">
              IoT FOTA Gateway
            </div>
          </div>
        </div>

        {/* Navigation items */}
        <nav className="p-4 space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-cyan-950/80 to-blue-950/50 text-cyan-400 border border-cyan-800/60 shadow-glow-cyan'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer with Gateway specs */}
      <div className="p-4 border-t border-fleet-border bg-fleet-darkest/50">
        <div className="text-[11px] text-slate-400 space-y-1">
          <div className="flex justify-between">
            <span>Gateway Host:</span>
            <span className="font-mono text-slate-200">rpi4-lan0</span>
          </div>
          <div className="flex justify-between">
            <span>Broker:</span>
            <span className="font-mono text-emerald-400">1883 [LAN]</span>
          </div>
          <div className="flex justify-between">
            <span>Version:</span>
            <span className="font-mono text-slate-400">v0.1.0-prod</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
