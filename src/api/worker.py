import threading
import queue
import time
import logging
import os
import json
from datetime import datetime, UTC
from .job_manager import JobType

logger = logging.getLogger(__name__)

# Performance monitoring toggle
ENABLE_TIMERS = os.getenv("ENABLE_PERFORMANCE_LOGGING", "false").lower() == "true"

class JobWorker:
    def __init__(self, job_manager):
        self.job_manager = job_manager
        self.queue = queue.Queue()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()

    def submit_job(self, job_id, params):
        """Add to queue""" 
        self.queue.put((job_id, params))

    def _worker_loop(self):
        """Process one job at a time"""
        while True:
            job_id, params = self.queue.get()

            # Start timing total job duration
            job_start_time = time.time()

            try:
                # Update status to running (persists to GCS)
                self.job_manager.update_status(job_id, "running")

                # Get job to check its type
                job = self.job_manager.get_job(job_id)

                # Route to correct handler based on job type
                if job.job_type == JobType.RETRIEVAL:
                    results = self._run_retrieval(job_id, params)
                elif job.job_type == JobType.EXTRACTION:
                    results = self._run_extraction(job_id, params)
                else:
                    raise ValueError(f"Unknown job type: {job.job_type}")

                # Log performance summary (if timing enabled)
                if ENABLE_TIMERS:
                    total_time = time.time() - job_start_time
                    logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    logger.info(f"SUMMARY: Job {job_id} completed in {total_time:.2f}s")
                    if results and 'summary' in results:
                        summary = results['summary']
                        logger.info(f"   Papers: {summary.get('total', 0)} total, "
                                  f"{summary.get('downloaded', 0)} downloaded, "
                                  f"{summary.get('parsed', 0)} parsed")
                    logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

                # Update with results (persists to GCS)
                self.job_manager.update_status(job_id, "completed", results=results)

            except Exception as e:
                if ENABLE_TIMERS:
                    total_time = time.time() - job_start_time
                    logger.error(f"❌ Job {job_id} failed after {total_time:.2f}s: {e}")
                else:
                    logger.error(f"❌ Job {job_id} failed: {e}")

                # Update with error (persists to GCS)
                self.job_manager.update_status(job_id, "failed", error=str(e))

            finally:
                self.queue.task_done()

    def _run_retrieval(self, job_id, params):
        """Wrap article_retriever.py logic here"""
        from document_preparation.article_retriever import run_retrieval

        # add progress
        def progress_callback(current, total, paper_title):
            self.job_manager.update_progress(job_id, {
                "total_papers": total,
                "processed": current,
                "current_paper": paper_title,
            })

        results = run_retrieval(
            query=params["query"],
            max_results=params.get("max_results", 20),
            year_min=params.get("year_min"),
            parse_pdfs=params.get("parse_pdfs", True),
            progress_callback=progress_callback,
            run_id=job_id  # Use job_id as run_id for consistent naming
        )
        return results

    def _run_extraction(self, job_id, params):
        """Run Monte Carlo extraction on a parsed paper."""
        from matsci_llm_causality.models.llm.monte_carlo_extractor import run_extraction

        logger.info(f"Starting extraction for paper {params['paper_id']}")

        # Progress callback to update job status
        def progress_callback(stage, status):
            self.job_manager.update_progress(job_id, {
                "stage": stage,
                "status": status
            })

        # Call the extraction module (handles everything internally)
        results = run_extraction(
            run_id=params['run_id'],
            paper_id=params['paper_id'],
            job_id=job_id,
            n_runs=params.get('n_runs', 5),
            progress_callback=progress_callback
        )

        return results

