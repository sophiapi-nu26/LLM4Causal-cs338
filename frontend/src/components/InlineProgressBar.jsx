import React from 'react';
import { Loader2 } from 'lucide-react';
import { formatProgress } from '../utils/transformers';

export default function InlineProgressBar({ jobType, progress, status }) {
  const { message, percentage } = formatProgress(progress, jobType);

  return (
    <div className="max-w-2xl mx-auto p-8">
      <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700">
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
          <div>
            <h3 className="text-lg font-semibold text-white">
              {jobType === 'retrieval' ? 'Retrieving Papers' : 'Extracting Graphs'}
            </h3>
            <p className="text-sm text-slate-400">
              {status === 'queued' ? 'Starting...' : 'Processing...'}
            </p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-3">
          <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-500 ease-out"
              style={{ width: `${percentage}%` }}
            />
          </div>
        </div>

        {/* Status Message */}
        <p className="text-sm text-slate-300 text-center">
          {message}
        </p>

        {/* Progress Percentage */}
        <p className="text-xs text-slate-400 text-center mt-2">
          {percentage}% complete
        </p>
      </div>
    </div>
  );
}
