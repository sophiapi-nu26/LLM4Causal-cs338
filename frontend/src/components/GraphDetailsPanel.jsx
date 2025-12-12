import React from 'react';
import { formatFrequency } from '../utils/transformGraphData';

/**
 * GraphDetailsPanel Component
 * ----------------------------
 * Displays detailed information about the selected graph element (node or edge).
 */
export default function GraphDetailsPanel({ selectedElement, onClose }) {
  if (!selectedElement) {
    return (
      <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700">
        <p className="text-slate-400 text-center text-sm">
          Click on a node or edge to view details
        </p>
      </div>
    );
  }

  const { type, data } = selectedElement;

  if (type === 'node') {
    return (
      <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
        <div className="flex items-start justify-between mb-3">
          <h3 className="text-lg font-semibold text-white">Entity Details</h3>
          {onClose && (
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white transition-colors"
              aria-label="Close details"
            >
              
            </button>
          )}
        </div>

        <div className="space-y-3">
          {/* Entity Name */}
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-wide mb-1">
              Name
            </div>
            <div className="text-white font-medium">{data.label}</div>
          </div>

          {/* Entity Type */}
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-wide mb-1">
              Type
            </div>
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: data.color }}
              />
              <span className="text-white capitalize">{data.entityType}</span>
            </div>
          </div>

          {/* Frequency */}
          {data.frequency !== undefined && (
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wide mb-1">
                Frequency
              </div>
              <div className="text-white">
                Found in {data.frequency} run{data.frequency !== 1 ? 's' : ''}
              </div>
            </div>
          )}

          {/* Variations */}
          {data.variations && data.variations.length > 0 && (
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wide mb-1">
                Name Variations
              </div>
              <div className="flex flex-wrap gap-1">
                {data.variations.map((variation, idx) => (
                  <span
                    key={idx}
                    className="text-xs px-2 py-1 bg-slate-700 text-slate-300 rounded"
                  >
                    {variation}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (type === 'edge') {
    return (
      <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
        <div className="flex items-start justify-between mb-3">
          <h3 className="text-lg font-semibold text-white">Relationship Details</h3>
          {onClose && (
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white transition-colors"
              aria-label="Close details"
            >
              
            </button>
          )}
        </div>

        <div className="space-y-3">
          {/* Relationship */}
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-wide mb-1">
              Relationship
            </div>
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: data.color }}
              />
              <span className="text-white font-medium">{data.source}</span>
              <span className="text-slate-400">�</span>
              <span className="text-white font-medium">{data.target}</span>
            </div>
          </div>

          {/* Relation Type */}
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-wide mb-1">
              Type
            </div>
            <div
              className="inline-block px-3 py-1 rounded text-sm font-medium"
              style={{ backgroundColor: data.color + '20', color: data.color }}
            >
              {data.relation}
            </div>
          </div>

          {/* Frequency */}
          {data.frequency !== undefined && (
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wide mb-1">
                Frequency
              </div>
              <div className="text-white">
                Found in {data.frequency} run{data.frequency !== 1 ? 's' : ''}
              </div>
            </div>
          )}

          {/* Evidence */}
          {data.evidence && data.evidence.length > 0 && (
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wide mb-1">
                Evidence Samples
              </div>
              <div className="space-y-1">
                {data.evidence.slice(0, 3).map((evidence, idx) => (
                  <div
                    key={idx}
                    className="text-xs text-slate-300 bg-slate-700/50 p-2 rounded"
                  >
                    {evidence}
                  </div>
                ))}
                {data.evidence.length > 3 && (
                  <div className="text-xs text-slate-400 italic">
                    +{data.evidence.length - 3} more...
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return null;
}
