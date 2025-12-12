const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://llm4causal-api-470387906928.us-central1.run.app';

/**
 * Handle API response and error parsing
 */
async function handleResponse(response) {
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API Error (${response.status}): ${errorBody || response.statusText}`);
  }
  return await response.json();
}

/**
 * Submit a new retrieval job to search for and download papers
 *
 * @param {string} query - Search query
 * @param {number} maxResults - Maximum papers to retrieve (default: 20)
 * @param {number|null} yearMin - Minimum publication year (optional)
 * @returns {Promise<{job_id: string, status: string, status_url: string}>}
 */
export async function submitRetrieval(query, maxResults = 20, yearMin = 2020) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/retrieve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        max_results: maxResults,
        year_min: yearMin,
        parse_pdfs: true
      }),
      signal: AbortSignal.timeout(30000) // 30s timeout
    });
    return await handleResponse(response);
  } catch (error) {
    if (error.name === 'AbortError' || error.name === 'TimeoutError') {
      throw new Error('Request timed out - please try again');
    }
    if (error.message.includes('Failed to fetch')) {
      throw new Error('Network error - check your connection');
    }
    throw error;
  }
}

/**
 * Get the status and results of a submitted job
 *
 * @param {string} jobId - Job ID to check
 * @returns {Promise<{job_id: string, status: string, progress: object, results: object|null, error: string|null}>}
 */
export async function getJobStatus(jobId) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`, {
      signal: AbortSignal.timeout(10000) // 10s timeout for polling
    });
    return await handleResponse(response);
  } catch (error) {
    if (error.name === 'AbortError' || error.name === 'TimeoutError') {
      throw new Error('Status check timed out');
    }
    if (error.message.includes('Failed to fetch')) {
      throw new Error('Network error - check your connection');
    }
    throw error;
  }
}

/**
 * Extract causal graph from a single paper using Monte Carlo method
 *
 * @param {string} runId - Run ID from retrieval job
 * @param {string} paperId - Specific paper ID
 * @param {number} nRuns - Number of Monte Carlo extraction runs (default: 5)
 * @returns {Promise<{job_id: string, status: string, status_url: string, extraction_params: object}>}
 */
export async function extractSingle(runId, paperId, nRuns = 5) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/extract-graph/single`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        run_id: runId,
        paper_id: paperId,
        n_runs: nRuns
      }),
      signal: AbortSignal.timeout(30000) // 30s timeout
    });
    return await handleResponse(response);
  } catch (error) {
    if (error.name === 'AbortError' || error.name === 'TimeoutError') {
      throw new Error('Request timed out - please try again');
    }
    if (error.message.includes('Failed to fetch')) {
      throw new Error('Network error - check your connection');
    }
    throw error;
  }
}

/**
 * Extract causal graphs from multiple papers using Monte Carlo method
 *
 * @param {string} runId - Run ID from retrieval job
 * @param {string[]} paperIds - Array of paper IDs
 * @param {number} nRuns - Number of Monte Carlo runs per paper (default: 5)
 * @returns {Promise<{job_id: string, status: string, status_url: string, extraction_params: object}>}
 */
export async function extractMulti(runId, paperIds, nRuns = 5) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/extract-graph/multi`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        run_id: runId,
        paper_ids: paperIds,
        n_runs: nRuns
      }),
      signal: AbortSignal.timeout(30000) // 30s timeout
    });
    return await handleResponse(response);
  } catch (error) {
    if (error.name === 'AbortError' || error.name === 'TimeoutError') {
      throw new Error('Request timed out - please try again');
    }
    if (error.message.includes('Failed to fetch')) {
      throw new Error('Network error - check your connection');
    }
    throw error;
  }
}

export const api = {
  submitRetrieval,
  getJobStatus,
  extractSingle,
  extractMulti
};
