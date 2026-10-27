import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { useWebSocket } from '../../context/WebSocketContext';
import { LogOut, Wifi, WifiOff, ShieldCheck, Cpu, Menu } from 'lucide-react';

interface NavbarProps {
  onOpenSidebar?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenSidebar }) => {
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
    <header className="h-16 border-b border-fleet-border bg-fleet-darkest/80 backdrop-blur-md px-3 sm:px-6 flex items-center justify-between z-20 sticky top-0">
      <div className="flex items-center space-x-2 sm:space-x-4">
        {/* Mobile Hamburger Drawer Trigger */}
        <button
          onClick={onOpenSidebar}
          className="p-2 -ml-1 text-slate-300 hover:text-white hover:bg-slate-800/80 rounded-xl md:hidden transition-colors"
          aria-label="Open Navigation Menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-2 text-fleet-cyan font-bold tracking-wider text-xs sm:text-sm bg-fleet-card px-2.5 sm:px-3 py-1.5 rounded-lg border border-fleet-border">
          <Cpu className="w-4 h-4 text-fleet-cyan animate-pulse shrink-0" />
          <span className="hidden sm:inline">GATEWAY: </span>
          <span>RPI4-B01</span>
          <span className="w-2 h-2 rounded-full bg-emerald-500 status-pulse-live ml-0.5 sm:ml-1 shrink-0"></span>
        </div>

        <div className="hidden lg:flex items-center space-x-2 text-xs text-slate-400">
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

      <div className="flex items-center space-x-2 sm:space-x-4">
        {user && (
          <div className="flex items-center space-x-2 sm:space-x-3">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-semibold text-slate-200">{user.full_name || user.email}</div>
              <div className="text-[10px] text-slate-400 font-mono">{user.email}</div>
            </div>

            <span className={`text-[10px] sm:text-[11px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${getRoleBadge(user.role)} flex items-center gap-1`}>
              <ShieldCheck className="w-3 h-3 shrink-0" />
              <span>{user.role}</span>
            </span>

            <button
              onClick={logout}
              title="Sign Out"
              className="p-1.5 sm:p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 rounded-lg transition-colors border border-transparent hover:border-rose-900/50"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};

