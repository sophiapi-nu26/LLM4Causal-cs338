import React from 'react';
import { Search, Loader2, Calendar, FileStack } from 'lucide-react';

export default function SearchBar({
  query,
  onQueryChange,
  onSearch,
  isSearching,
  yearMin,
  onYearMinChange,
  maxResults,
  onMaxResultsChange
}) {
  const currentYear = new Date().getFullYear();

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !isSearching && query.trim()) {
      onSearch();
    }
  };

  const handleYearChange = (e) => {
    // Allow any input while typing (including empty string)
    onYearMinChange(e.target.value);
  };

  const handleYearBlur = (e) => {
    // Validate and clamp only when user finishes editing
    const value = parseInt(e.target.value);
    if (isNaN(value) || e.target.value === '') {
      onYearMinChange(2020); // Reset to default if invalid
    } else {
      // Clamp between 1900 and current year
      const clamped = Math.max(1900, Math.min(currentYear, value));
      onYearMinChange(clamped);
    }
  };

  const handleMaxResultsChange = (e) => {
    // Allow any input while typing
    onMaxResultsChange(e.target.value);
  };

  const handleMaxResultsBlur = (e) => {
    // Validate and clamp only when user finishes editing
    const value = parseInt(e.target.value);
    if (isNaN(value) || e.target.value === '') {
      onMaxResultsChange(50); // Reset to default if invalid
    } else {
      // Clamp between 1 and 100
      const clamped = Math.max(1, Math.min(100, value));
      onMaxResultsChange(clamped);
    }
  };

  return (
    <div className="bg-slate-800/30 border-b border-slate-700 px-6 py-4">
      <div className="max-w-4xl mx-auto space-y-3">
        {/* Main search input */}
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isSearching}
            placeholder="e.g., mechanical properties of stainless steel"
            className="w-full px-6 py-3 pr-14 rounded-lg bg-slate-800/80 border border-slate-600 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            onClick={onSearch}
            disabled={isSearching || !query.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-md transition-colors"
          >
            {isSearching ? (
              <Loader2 className="w-5 h-5 text-white animate-spin" />
            ) : (
              <Search className="w-5 h-5 text-white" />
            )}
          </button>
        </div>

        {/* Filters row */}
        <div className="flex items-center gap-4">
          {/* Year filter */}
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-slate-400" />
            <label className="text-sm text-slate-400">Minimum year:</label>
            <input
              type="number"
              value={yearMin}
              onChange={handleYearChange}
              onBlur={handleYearBlur}
              disabled={isSearching}
              placeholder="2020"
              className="w-20 px-3 py-1.5 rounded bg-slate-800/80 border border-slate-600 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            />
          </div>

          {/* Max results filter */}
          <div className="flex items-center gap-2">
            <FileStack className="w-4 h-4 text-slate-400" />
            <label className="text-sm text-slate-400">Max papers:</label>
            <input
              type="number"
              value={maxResults}
              onChange={handleMaxResultsChange}
              onBlur={handleMaxResultsBlur}
              disabled={isSearching}
              placeholder="20"
              className="w-16 px-3 py-1.5 rounded bg-slate-800/80 border border-slate-600 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            />
            <span className="text-xs text-slate-500">(1-100)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
