import React, { useState } from 'react';
import { Tree } from '../../types';
import { TreeStatusBadge } from '../common/Badge';
import { Trees, Search, Eye, Edit2, MapPin, Trash2 } from 'lucide-react';

interface TreeTableProps {
  trees: Tree[];
  onSelectTree: (tree: Tree) => void;
  onEditTree?: (tree: Tree) => void;
  onViewOnMap?: (tree: Tree) => void;
  onDeleteTree?: (tree: Tree) => void;
}

export const TreeTable: React.FC<TreeTableProps> = ({
  trees,
  onSelectTree,
  onEditTree,
  onViewOnMap,
  onDeleteTree,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const filteredTrees = trees.filter((tree) => {
    const matchesSearch =
      tree.tree_uid.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tree.species.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (tree.notes && tree.notes.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesStatus = statusFilter === 'ALL' || tree.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="glass-panel rounded-2xl overflow-hidden">
      {/* Table Header Controls */}
      <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Search Bar */}
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search Tree ID, species, notes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-950/80 border border-slate-700/80 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
          />
        </div>

        {/* Filter Badges */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
          {(['ALL', 'HEALTHY', 'AT_RISK', 'DISEASED', 'HARVESTED'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
                statusFilter === status
                  ? 'bg-emerald-500 text-slate-950 font-bold'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {status === 'ALL' ? 'All Trees' : status.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Table Body */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950/60 text-[11px] uppercase tracking-wider text-slate-400 font-mono border-b border-slate-800">
            <tr>
              <th className="py-3.5 px-4 font-semibold">Tree UID</th>
              <th className="py-3.5 px-4 font-semibold">Species</th>
              <th className="py-3.5 px-4 font-semibold">GPS Coordinates</th>
              <th className="py-3.5 px-4 font-semibold">Age / Girth / Ht</th>
              <th className="py-3.5 px-4 font-semibold">Health Status</th>
              <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {filteredTrees.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500 font-sans">
                  No sandalwood trees found matching criteria.
                </td>
              </tr>
            ) : (
              filteredTrees.map((tree) => (
                <tr
                  key={tree.id}
                  className="hover:bg-slate-800/40 transition-colors group cursor-pointer"
                  onClick={() => onSelectTree(tree)}
                >
                  <td className="py-3.5 px-4 font-bold text-emerald-400 flex items-center gap-2">
                    <Trees className="w-4 h-4 text-emerald-500/70" />
                    <span>{tree.tree_uid}</span>
                  </td>
                  <td className="py-3.5 px-4 italic text-slate-300 font-sans">{tree.species}</td>
                  <td className="py-3.5 px-4 text-slate-400">
                    {tree.latitude.toFixed(4)}° N, {tree.longitude.toFixed(4)}° E
                  </td>
                  <td className="py-3.5 px-4 text-slate-300">
                    {tree.age_label || (tree.estimated_age_years ? `~${tree.estimated_age_years}y` : '-')}{' '}
                    &bull; {tree.girth_cm ? `${tree.girth_cm}cm` : '-'}{' '}
                    &bull; {tree.height_m ? `${tree.height_m}m` : '-'}
                  </td>
                  <td className="py-3.5 px-4">
                    <TreeStatusBadge status={tree.status} />
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => onSelectTree(tree)}
                        className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-emerald-400 transition-colors"
                        title="View Tree Detail & Telemetry"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      {onViewOnMap && (
                        <button
                          onClick={() => onViewOnMap(tree)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-cyan-400 transition-colors"
                          title="Locate on Internet Sandalwood"
                        >
                          <MapPin className="w-3.5 h-3.5" />
                        </button>
                      )}
                      {onEditTree && (
                        <button
                          onClick={() => onEditTree(tree)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-amber-400 transition-colors"
                          title="Update Measurements"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                      {onDeleteTree && (
                        <button
                          onClick={() => onDeleteTree(tree)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-rose-950 text-slate-300 hover:text-rose-400 transition-colors"
                          title="Delete Tree"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
