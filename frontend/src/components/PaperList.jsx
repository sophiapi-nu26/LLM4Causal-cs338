import React from 'react';
import { List } from 'lucide-react';
import PaperCard from './PaperCard';

export default function PaperList({
  papers,
  selectedPaperIds,
  onToggleSelect,
  activePaperId,
  onPaperClick
}) {
  // Separate successful vs failed papers
  const successfulPapers = papers.filter(p => p.canExtract);
  const failedPapers = papers.filter(p => !p.canExtract);

  if (papers.length === 0) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center text-slate-400">
          <List className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-sm">Retrieved papers will appear here</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Successful Papers Section */}
      {successfulPapers.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-slate-300 mb-2 px-1">
            Available Papers ({successfulPapers.length})
          </h3>
          <div className="space-y-2">
            {successfulPapers.map((paper) => (
              <PaperCard
                key={paper.id}
                paper={paper}
                isSelected={selectedPaperIds.includes(paper.id)}
                onToggleSelect={onToggleSelect}
                onClick={onPaperClick}
                isActive={paper.id === activePaperId}
              />
            ))}
          </div>
        </div>
      )}

      {/* Failed Papers Section (collapsed by default) */}
      {failedPapers.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-slate-500 mb-2 px-1">
            Parse Failed ({failedPapers.length})
          </h3>
          <p className="text-xs text-slate-500 mb-2 px-1">
            These papers could not be processed and cannot be extracted.
          </p>
          <div className="space-y-2">
            {failedPapers.map((paper) => (
              <PaperCard
                key={paper.id}
                paper={paper}
                isSelected={false}
                onToggleSelect={() => {}}
                onClick={() => {}}
                isActive={false}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
