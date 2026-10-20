import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { useWebSocket } from '../../context/WebSocketContext';
import { LogOut, Wifi, WifiOff, ShieldCheck, Cpu } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const { isConnected } = useWebSocket();

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-purple-950 text-purple-300 border-purple-800';
      case 'operator':
        return 'bg-cyan-950 text-cyan-300 border-cyan-800';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <header className="h-16 border-b border-fleet-border bg-fleet-darkest/80 backdrop-blur-md px-6 flex items-center justify-between z-20 sticky top-0">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2 text-fleet-cyan font-bold tracking-wider text-sm bg-fleet-card px-3 py-1.5 rounded-lg border border-fleet-border">
          <Cpu className="w-4 h-4 text-fleet-cyan animate-pulse" />
          <span>GATEWAY: RPI4-B01</span>
          <span className="w-2 h-2 rounded-full bg-emerald-500 status-pulse-live ml-1"></span>
        </div>

        <div className="hidden md:flex items-center space-x-2 text-xs text-slate-400">
          {isConnected ? (
            <span className="flex items-center text-emerald-400">
              <Wifi className="w-3.5 h-3.5 mr-1" />
              Live Telemetry Stream
            </span>
          ) : (
            <span className="flex items-center text-amber-400">
              <WifiOff className="w-3.5 h-3.5 mr-1" />
              Reconnecting WebSocket...
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {user && (
          <div className="flex items-center space-x-3">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-semibold text-slate-200">{user.full_name || user.email}</div>
              <div className="text-[10px] text-slate-400 font-mono">{user.email}</div>
            </div>

            <span className={`text-[11px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${getRoleBadge(user.role)} flex items-center gap-1`}>
              <ShieldCheck className="w-3 h-3" />
              {user.role}
            </span>

            <button
              onClick={logout}
              title="Sign Out"
              className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 rounded-lg transition-colors border border-transparent hover:border-rose-900/50"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
