import threading
import queue
from datetime import datetime, UTC

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

            try:
                # update status
                job = self.job_manager.get_job(job_id)
                job.status = "running"

                # run retrieval
                results = self._run_retrieval(job_id, params)

                # update with results
                job.status = "completed"
                job.results = results 

            except Exception as e:
                job.status = "failed"
                job.error = str(e)

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
                "current": paper_title,
            })

        results = run_retrieval(
            query=params["query"],
            max_results=params["max_results"],
            progress_callback=progress_callback
        )
        return results
        



