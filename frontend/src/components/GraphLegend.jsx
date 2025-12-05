import React from 'react';
import { NODE_COLORS, EDGE_COLORS } from '../utils/cytoscapeConfig';

/**
 * GraphLegend Component
 * ---------------------
 * Visual legend showing node types and edge relationship types with colors.
 */
export default function GraphLegend() {
  const nodeTypes = [
    { type: 'material', color: NODE_COLORS.material, label: 'Material' },
    { type: 'process', color: NODE_COLORS.process, label: 'Process' },
    { type: 'structure', color: NODE_COLORS.structure, label: 'Structure' },
    { type: 'property', color: NODE_COLORS.property, label: 'Property' }
  ];

  const edgeTypes = [
    { type: 'increases', color: EDGE_COLORS.increases, label: 'Increases' },
    { type: 'decreases', color: EDGE_COLORS.decreases, label: 'Decreases' },
    { type: 'causes', color: EDGE_COLORS.causes, label: 'Causes' },
    {
      type: 'correlates_pos',
      color: EDGE_COLORS['positively correlates with'],
      label: 'Correlates +'
    },
    {
      type: 'correlates_neg',
      color: EDGE_COLORS['negatively correlates with'],
      label: 'Correlates -' 
    }
  ];

  return (
    <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
      <h3 className="text-sm font-semibold text-white mb-3">Legend</h3>

      {/* Node Types */}
      <div className="mb-4">
        <div className="text-xs text-slate-400 uppercase tracking-wide mb-2">
          Node Types
        </div>
        <div className="space-y-1.5">
          {nodeTypes.map((node) => (
            <div key={node.type} className="flex items-center gap-2">
              <div
                className="w-4 h-4 rounded-full flex-shrink-0"
                style={{ backgroundColor: node.color }}
              />
              <span className="text-xs text-slate-300">{node.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Edge Types */}
      <div>
        <div className="text-xs text-slate-400 uppercase tracking-wide mb-2">
          Relationship Types
        </div>
        <div className="space-y-1.5">
          {edgeTypes.map((edge) => (
            <div key={edge.type} className="flex items-center gap-2">
              <div className="flex items-center flex-shrink-0" style={{ width: '20px' }}>
                <div
                  className="h-0.5 w-3"
                  style={{ backgroundColor: edge.color }}
                />
                <div
                  className="w-0 h-0 border-l-4 border-y-2 border-y-transparent"
                  style={{ borderLeftColor: edge.color }}
                />
              </div>
              <span className="text-xs text-slate-300">{edge.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
