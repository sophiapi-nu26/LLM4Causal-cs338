/**
 * Transform backend paper object to frontend format
 *
 * Backend format (from retrieval job results.papers):
 * {
 *   paper_id: "s2_12345",
 *   title: "...",
 *   authors: "Smith et al.",
 *   year: 2023,
 *   abstract: "...",
 *   cited_by_count: 150,
 *   relevance_score: 0.85,
 *   venue: "Nature Materials",
 *   parse_status: "success" | "failed",
 *   open_access_status: "gold" | "hybrid" | "closed",
 *   pdf_source: "semantic_scholar" | "openalex" | "unpaywall"
 * }
 */
export function transformPaper(apiPaper) {
  return {
    id: apiPaper.paper_id,
    paperId: apiPaper.paper_id, // Keep for extraction API
    title: apiPaper.title,
    authors: apiPaper.authors,
    year: apiPaper.year,
    abstract: apiPaper.abstract || 'No abstract available',
    citationCount: apiPaper.cited_by_count || 0,
    relevanceScore: apiPaper.relevance_score ? (apiPaper.relevance_score * 100).toFixed(0) : null,
    venue: apiPaper.venue || 'Unknown',
    status: apiPaper.parse_status === 'success' ? 'completed' : 'failed',
    parseStatus: apiPaper.parse_status,
    openAccess: apiPaper.open_access_status,
    pdfSource: apiPaper.pdf_source,
    // UI helpers
    isOpenAccess: apiPaper.open_access_status === 'gold' || apiPaper.open_access_status === 'hybrid',
    canExtract: apiPaper.parse_status === 'success'
  };
}

/**
 * Transform array of backend papers to frontend format
 */
export function transformPapers(apiPapers) {
  if (!Array.isArray(apiPapers)) {
    console.error('Invalid papers array:', apiPapers);
    return [];
  }
  return apiPapers.map(transformPaper);
}

/**
 * Format progress object for UI display
 *
 * Backend progress format (from job.progress):
 * Retrieval: {
 *   total_papers: 20,
 *   processed: 5,
 *   current_paper: "Title of current paper"
 * }
 */
export function formatProgress(progress, jobType = 'retrieval') {
  if (jobType === 'extraction') {
    return formatExtractionProgress(progress);
  }

  const { total_papers, processed, current_paper } = progress || {};

  // If we have valid progress data, show it
  if (total_papers && processed !== undefined) {
    const percentage = Math.round((processed / total_papers) * 100);
    const paperTitle = current_paper ? `: ${current_paper.substring(0, 50)}${current_paper.length > 50 ? '...' : ''}` : '';
    return {
      message: `Processing paper ${processed}/${total_papers}${paperTitle}`,
      percentage
    };
  }

  // Default state when no progress data yet
  return {
    message: 'Initializing retrieval...',
    percentage: 0
  };
}

/**
 * Format extraction progress for UI display
 *
 * Single-paper extraction progress:
 * {
 *   stage: "Entity Extraction",
 *   status: "Running Monte Carlo run 3/5"
 * }
 *
 * Multi-paper extraction progress:
 * {
 *   total_papers: 3,
 *   current_paper_index: 2,
 *   current_paper_id: "s2_12345",
 *   completed_papers: 1,
 *   failed_papers: 0,
 *   stage: "Entity Extraction",
 *   status: "Running Monte Carlo run 2/5"
 * }
 */
export function formatExtractionProgress(progress) {
  if (!progress || Object.keys(progress).length === 0) {
    return {
      message: 'Starting extraction...',
      percentage: 0
    };
  }

  // Multi-paper extraction
  if (progress.total_papers && progress.current_paper_index) {
    const percentage = Math.round(
      ((progress.completed_papers + progress.failed_papers) / progress.total_papers) * 100
    );

    const currentStage = progress.status || 'Processing...';

    return {
      message: `Paper ${progress.current_paper_index}/${progress.total_papers} - ${currentStage}`,
      percentage,
      details: {
        completed: progress.completed_papers,
        failed: progress.failed_papers
      }
    };
  }

  // Single-paper extraction
  if (progress.stage || progress.status) {
    return {
      message: progress.status || 'Processing...',
      percentage: 50 // Indeterminate
    };
  }

  return {
    message: 'Extracting relationships...',
    percentage: 0
  };
}
