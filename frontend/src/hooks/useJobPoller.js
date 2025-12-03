import { useEffect, useState, useRef } from 'react';
import { api } from '../services/api';

/**
 * Custom hook for polling job status with exponential backoff
 *
 * @param {string|null} jobId - Job ID to poll (null to disable polling)
 * @param {function} onComplete - Callback when job completes successfully
 * @param {function} onError - Callback when job fails
 * @param {object} options - Configuration options
 * @returns {{status: string, progress: object, isPolling: boolean}}
 */
export function useJobPoller(jobId, onComplete, onError, options = {}) {
  const [status, setStatus] = useState('queued');
  const [progress, setProgress] = useState({});
  const [isPolling, setIsPolling] = useState(false);

  const intervalRef = useRef(null);
  const pollIntervalRef = useRef(options.initialInterval || 2000); // Start at 2 seconds
  const lastProgressRef = useRef({}); // Store last known progress
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  // Keep refs up to date
  useEffect(() => {
    onCompleteRef.current = onComplete;
    onErrorRef.current = onError;
  }, [onComplete, onError]);

  useEffect(() => {
    if (!jobId) {
      setIsPolling(false);
      setStatus('queued');
      setProgress({});
      return;
    }

    setIsPolling(true);
    let isMounted = true;

    const poll = async () => {
      try {
        const job = await api.getJobStatus(jobId);

        if (!isMounted) return;

        setStatus(job.status);

        // Only update progress if it's actually progressing forward
        const newProgress = job.progress || {};
        const lastProgress = lastProgressRef.current;

        // For retrieval jobs, check if processed count increased
        if (newProgress.processed !== undefined && lastProgress.processed !== undefined) {
          // Only update if processed count increased or stayed the same (don't regress)
          if (newProgress.processed >= lastProgress.processed) {
            setProgress(newProgress);
            lastProgressRef.current = newProgress;
          }
          // Otherwise keep the last known good progress
        } else if (Object.keys(newProgress).length > 0) {
          // If we have any progress data and no previous data, use it
          setProgress(newProgress);
          lastProgressRef.current = newProgress;
        }
        // If newProgress is empty, keep the last known progress (don't reset)

        if (job.status === 'completed') {
          clearInterval(intervalRef.current);
          setIsPolling(false);
          onCompleteRef.current?.(job.results);
        } else if (job.status === 'failed') {
          clearInterval(intervalRef.current);
          setIsPolling(false);
          onErrorRef.current?.(job.error || 'Job failed');
        } else {
          // Exponential backoff: 5s -> 5.5s -> 6.05s ... -> 15s max
          pollIntervalRef.current = Math.min(
            pollIntervalRef.current * 1.1,
            options.maxInterval || 15000
          );
        }
      } catch (error) {
        console.error('Polling error:', error);
        if (isMounted) {
          onErrorRef.current?.(error.message);
          clearInterval(intervalRef.current);
          setIsPolling(false);
        }
      }
    };

    // Initial poll
    poll();

    // Set up interval with current interval time
    intervalRef.current = setInterval(() => {
      poll();
    }, pollIntervalRef.current);

    // Cleanup
    return () => {
      isMounted = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      setIsPolling(false);
      // Reset for next use
      pollIntervalRef.current = options.initialInterval || 5000;
      lastProgressRef.current = {};
    };
  }, [jobId, options.initialInterval, options.maxInterval]);

  return { status, progress, isPolling };
}
