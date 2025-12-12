import React from 'react';
import { CheckCircle, AlertCircle, Unlock } from 'lucide-react';

export default function PaperCard({
  paper,
  isSelected,
  onToggleSelect,
  onClick,
  isActive
}) {
  const canSelect = paper.canExtract; // parse_status === 'success'

  return (
    <div
      className={`relative p-3 rounded-lg border transition-all ${
        isActive
          ? 'bg-blue-500/20 border-blue-500'
          : 'bg-slate-700/50 border-slate-600 hover:border-slate-500'
      } ${!canSelect ? 'opacity-50' : ''}`}
    >
      {/* Checkbox (top-left) */}
      <div className="absolute top-2 left-2 z-10">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => {
            e.stopPropagation();
            if (canSelect) {
              onToggleSelect(paper.id);
            }
          }}
          disabled={!canSelect}
          className="w-4 h-4 rounded border-slate-500 bg-slate-700 text-blue-600 focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed"
        />
      </div>

      {/* Paper content (clickable area) */}
      <div
        onClick={() => canSelect && onClick(paper)}
        className={`pl-6 ${canSelect ? 'cursor-pointer' : 'cursor-default'}`}
      >
        {/* Title */}
        <h3 className="font-medium text-white text-sm mb-1 line-clamp-2">
          {paper.title}
        </h3>

        {/* Authors & Year */}
        <p className="text-xs text-slate-400 mb-2">
          {paper.authors} • {paper.year}
        </p>

        {/* Badges */}
        <div className="flex flex-wrap gap-1">
          {/* Parse Status */}
          {paper.status === 'completed' ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-green-500/20 text-green-400">
              <CheckCircle className="w-3 h-3" />
              Parsed
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-red-500/20 text-red-400">
              <AlertCircle className="w-3 h-3" />
              Failed
            </span>
          )}

          {/* Open Access */}
          {paper.isOpenAccess && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-blue-500/20 text-blue-400">
              <Unlock className="w-3 h-3" />
              Open Access
            </span>
          )}

          {/* Citation Count */}
          {paper.citationCount > 0 && (
            <span className="px-2 py-0.5 rounded text-xs bg-slate-600 text-slate-300">
              {paper.citationCount} citations
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
