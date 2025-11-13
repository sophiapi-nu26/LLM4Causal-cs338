import threading
from dataclasses import dataclass
from datetime import datetime, UTC

@dataclass
class Job:
    job_id: str
    status: str
    query: str
    progress: dict
    results: dict | None
    error: str | None
    created_at: datetime

class JobManager:
    def __init__(self):
        self._jobs = {}
        self._lock = threading.Lock()

    def create_job(self, job_id: str, query: str):
        with self._lock:
            job = Job(
                job_id=job_id,
                status="queued",
                query=query,
                progress={},
                results=None,
                error=None,
                created_at=datetime.now(UTC),
            )
            self._jobs[job_id] = job
            return job

    def get_job(self, job_id: str):
        with self._lock:
            return self._jobs.get(job_id)

    def update_progress(self, job_id, progress):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].progress = progress
