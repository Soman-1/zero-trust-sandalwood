import React, { useState, useEffect, FormEvent } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { treesApi } from '../api/trees';
import { Tree, TreeStatus } from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useToast } from '../context/ToastContext';

export const TreeStatusUpdatePage: React.FC = () => {
  const { treeUid } = useParams<{ treeUid: string }>();
  const navigate = useNavigate();
  const [tree, setTree] = useState<Tree | null>(null);
  const [status, setStatus] = useState<TreeStatus>('HEALTHY');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(true);
  const { success, error: toastError } = useToast();

  useEffect(() => {
    const load = async () => {
      if (!treeUid) return;
      try {
        const data = await treesApi.getTree(treeUid);
        setTree(data);
        setStatus(data.status);
      } catch (e) {
        console.error(e);
        toastError('Failed to load tree');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [treeUid]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!treeUid) return;
    try {
      await treesApi.updateTreeStatus(treeUid, { status, reason: reason || undefined });
      success('Tree status updated');
      navigate('/trees');
    } catch (err) {
      console.error(err);
      toastError('Failed to update status');
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading tree..." size="lg" />;
  }

  if (!tree) {
    return <div className="p-4 text-slate-400">Tree not found.</div>;
  }

  return (
    <div className="max-w-2xl mx-auto p-6 glass-panel rounded-2xl">
      <h2 className="text-xl font-bold text-slate-100 mb-4">Update Status for <span className="text-emerald-400">{tree.tree_uid}</span></h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">Status</label>
          <select
            value={status}
            onChange={e => setStatus(e.target.value as TreeStatus)}
            className="w-full rounded-md bg-slate-800 text-slate-100 border border-slate-700 p-2"
          >
            <option value="HEALTHY">HEALTHY</option>
            <option value="AT_RISK">AT_RISK</option>
            <option value="DISEASED">DISEASED</option>
            <option value="HARVESTED">HARVESTED</option>
            <option value="REMOVED">REMOVED</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">Reason (optional)</label>
          <textarea
            value={reason}
            onChange={e => setReason(e.target.value)}
            rows={3}
            className="w-full rounded-md bg-slate-800 text-slate-100 border border-slate-700 p-2"
            placeholder="Enter reason for status change..."
          />
        </div>
        <div className="flex items-center gap-4 pt-2">
          <button
            type="submit"
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-slate-100 rounded-lg transition"
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => navigate('/trees')}
            className="px-4 py-2 bg-slate-600 hover:bg-slate-500 text-slate-100 rounded-lg transition"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};
