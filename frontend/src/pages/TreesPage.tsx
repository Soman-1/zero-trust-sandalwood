import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { treesApi } from '../api/trees';
import { clearApiClientCache } from '../api/client';
import { getApiErrorMessage } from '../utils/apiError';
import { Tree } from '../types';
import { TreeTable } from '../components/trees/TreeTable';
import { TreeRegisterModal } from '../components/trees/TreeRegisterModal';
import { TreeDetailDrawer } from '../components/trees/TreeDetailDrawer';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { Trees, Plus, RefreshCw, Trash2, X } from 'lucide-react';

export const TreesPage: React.FC = () => {
  const navigate = useNavigate();
  const { canManage } = useAuth();
  const { success, error: toastError } = useToast();
  const [trees, setTrees] = useState<Tree[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [selectedTree, setSelectedTree] = useState<Tree | null>(null);
  const [treeToDelete, setTreeToDelete] = useState<Tree | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchTrees = async () => {
    try {
      const treesList = await treesApi.listTrees({ limit: 200 });
      setTrees(treesList);
    } catch (e) {
      console.error('Error loading trees:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrees();
  }, []);

  const handleConfirmDelete = async () => {
    if (!treeToDelete) return;
    setDeleting(true);
    try {
      await treesApi.deleteTree(treeToDelete.tree_uid);
      clearApiClientCache('/dashboard/map-layer');
      success('Tree Deleted', `${treeToDelete.tree_uid} was removed from the registry.`);
      if (selectedTree?.tree_uid === treeToDelete.tree_uid) {
        setSelectedTree(null);
      }
      setTreeToDelete(null);
      await fetchTrees();
    } catch (err: unknown) {
      toastError('Delete Failed', getApiErrorMessage(err, 'Could not delete this tree.'));
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading Tree Registry..." size="lg" />;
  }

  return (
    <div className="space-y-6 font-sans">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-3xl">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
            <Trees className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">Sandalwood Tree Registry</h2>
            <p className="text-xs text-slate-400 mt-0.5 max-w-2xl">
              Registered <em>Santalum album</em> specimens, spatial bounds, biometrics, and health history.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={fetchTrees}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Refresh Trees"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          {canManage && (
            <button
              type="button"
              onClick={() => setIsRegisterOpen(true)}
              className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-emerald-500 hover:bg-emerald-600 text-slate-950 transition-all shadow-glow-emerald flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" />
              <span>Register Tree</span>
            </button>
          )}
        </div>
      </div>

      {/* Tree Data Table */}
      <TreeTable
        trees={trees}
        onSelectTree={(tree) => setSelectedTree(tree)}
        onViewOnMap={(tree) =>
          navigate(
            `/global-trees?lat=${encodeURIComponent(String(tree.latitude))}&lon=${encodeURIComponent(String(tree.longitude))}&tree_uid=${encodeURIComponent(tree.tree_uid)}`
          )
        }
        onEditTree={(tree) => setSelectedTree(tree)}
        onDeleteTree={canManage ? (tree) => setTreeToDelete(tree) : undefined}
      />

      {/* Tree Registration Modal */}
      <TreeRegisterModal
        isOpen={isRegisterOpen}
        onClose={() => setIsRegisterOpen(false)}
        onTreeRegistered={fetchTrees}
      />

      {/* Tree Detail Drawer */}
      <TreeDetailDrawer
        tree={selectedTree}
        onClose={() => setSelectedTree(null)}
        onTreeUpdated={fetchTrees}
        onDeleteTree={canManage ? (tree) => setTreeToDelete(tree) : undefined}
      />

      {treeToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#111723] border border-slate-700/80 rounded-2xl p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-100 font-semibold text-sm">
                <Trash2 className="w-4 h-4 text-rose-400" />
                <span>Delete registered tree</span>
              </div>
              <button
                type="button"
                onClick={() => !deleting && setTreeToDelete(null)}
                className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-sm text-slate-300">
              Permanently delete <span className="font-mono text-emerald-300">{treeToDelete.tree_uid}</span> from the
              Sandalwood Tree Registry? This cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                disabled={deleting}
                onClick={() => setTreeToDelete(null)}
                className="px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-slate-200 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleting}
                onClick={handleConfirmDelete}
                className="px-3 py-2 rounded-xl text-xs font-semibold bg-rose-600 text-white hover:bg-rose-500 disabled:opacity-60"
              >
                {deleting ? 'Deleting...' : 'Delete Tree'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
