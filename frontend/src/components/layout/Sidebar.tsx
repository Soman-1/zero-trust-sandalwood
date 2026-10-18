import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  MapPin,
  Trees,
  Cpu,
  Activity,
  BrainCircuit,
  AlertTriangle,
  Link2,
  Settings,
  TreePine,
  X,
  Globe,
  MapPinned,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { user } = useAuth();

  const navSections = [
    {
      title: 'Navigation',
      items: [
        { to: '/', label: 'Dashboard', icon: LayoutDashboard },
        { to: '/map', label: 'GIS Radar Map', icon: MapPin },
        { to: '/trees', label: 'Tree Registry', icon: Trees },
        { to: '/devices', label: 'IoT Gateways', icon: Cpu },
        { to: '/regions', label: 'Forest Reserves', icon: MapPinned },
        { to: '/telemetry', label: 'Telemetry', icon: Activity },
      ],
    },
    {
      title: 'Global Intelligence',
      items: [
        { to: '/global-trees', label: 'Internet Sandalwood', icon: Globe },
      ],
    },
    {
      title: 'Management',
      items: [
        { to: '/alerts', label: 'Security Alerts', icon: AlertTriangle },
        { to: '/anomaly', label: 'Anomaly Detection', icon: BrainCircuit },
        { to: '/audit', label: 'Audit Ledger', icon: Link2 },
        { to: '/system', label: 'System Health', icon: Settings },
      ],
    },
  ];


  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-slate-950/80 z-40 lg:hidden backdrop-blur-md transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar Panel */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 w-64 bg-[#090d16] border-r border-slate-800/80 flex flex-col transition-all duration-300 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center justify-between px-5 border-b border-slate-800/80 bg-slate-950/40">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 shadow-glow-emerald">
              <TreePine className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-bold text-sm text-slate-100 tracking-tight">Sandalwood AI</h1>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="lg:hidden text-slate-400 hover:text-slate-100 p-1.5 rounded-xl hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Menu */}
        <div className="flex-1 overflow-y-auto px-3.5 py-4 space-y-6 scrollbar-thin">
          {navSections.map((section) => (
            <div key={section.title} className="space-y-1.5">
              <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-500 font-mono">
                {section.title}
              </p>
              {section.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => onClose()}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all group ${
                        isActive
                          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-glow-emerald font-bold'
                          : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/80 hover:border hover:border-slate-800'
                      }`
                    }
                  >
                    <Icon className="w-4 h-4 flex-shrink-0 transition-transform duration-200 group-hover:scale-110" />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
          ))}
        </div>

        {/* Bottom User Profile Card */}
        {user && (
          <div className="p-3.5 border-t border-slate-800/80 bg-slate-950/60">
            <div className="flex items-center justify-between px-3 py-2 rounded-xl bg-slate-900/90 border border-slate-800 text-xs">
              <div className="flex items-center gap-2.5 truncate">
                <div className="w-7 h-7 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center font-mono font-bold text-xs">
                  {user.username.charAt(0).toUpperCase()}
                </div>
                <div className="truncate">
                  <p className="text-slate-200 font-semibold truncate leading-none">{user.username}</p>
                  <span className="text-[9px] text-slate-400 font-mono">Authenticated</span>
                </div>
              </div>
              <span className="text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded-md bg-slate-800 text-emerald-400 border border-emerald-500/20">
                {user.role}
              </span>
            </div>
          </div>
        )}
      </aside>
    </>
  );
};
