import React from 'react';
import { X, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { formatProgress } from '../utils/transformers';

export default function JobStatusModal({ isOpen, onClose, jobType, progress, status, error }) {
  if (!isOpen) return null;

  const { message, percentage, details } = formatProgress(progress, jobType);
  const isRunning = status === 'running' || status === 'queued';

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-xl border border-slate-700 max-w-md w-full p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-xl font-bold text-white mb-1">
              {jobType === 'retrieval' ? 'Retrieving Papers' : 'Extracting Graphs'}
            </h3>
            <p className="text-sm text-slate-400">
              {isRunning ? 'Processing...' : status === 'completed' ? 'Complete!' : 'Failed'}
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={isRunning}
            className="text-slate-400 hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Status Icon */}
        <div className="flex justify-center mb-4">
          {isRunning && <Loader2 className="w-12 h-12 text-blue-400 animate-spin" />}
          {status === 'completed' && <CheckCircle className="w-12 h-12 text-green-500" />}
          {status === 'failed' && <AlertCircle className="w-12 h-12 text-red-500" />}
        </div>

        {/* Progress Bar */}
        {isRunning && (
          <div className="mb-4">
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all duration-500"
                style={{ width: `${percentage}%` }}
              />
            </div>
            <p className="text-sm text-slate-300 mt-2 text-center">{message}</p>

            {/* Multi-extraction details */}
            {details && jobType === 'extraction' && (
              <div className="mt-3 flex justify-center gap-4 text-xs">
                <span className="text-green-400">
                  ✓ {details.completed} completed
                </span>
                {details.failed > 0 && (
                  <span className="text-red-400">
                    ✗ {details.failed} failed
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {/* Success Message */}
        {status === 'completed' && (
          <div className="text-center">
            <p className="text-green-400 mb-2">
              {jobType === 'retrieval'
                ? 'Papers retrieved successfully!'
                : 'Extraction complete!'}
            </p>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              View Results
            </button>
          </div>
        )}

        {/* Error Message */}
        {status === 'failed' && error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4">
            <p className="text-sm text-red-400">{error}</p>
            <button
              onClick={onClose}
              className="mt-3 w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
