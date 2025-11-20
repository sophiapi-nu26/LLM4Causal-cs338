import threading
import logging
import json
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from typing import Optional

logger = logging.getLogger(__name__)

# Performance monitoring toggle
ENABLE_TIMERS = os.getenv("ENABLE_PERFORMANCE_LOGGING", "false").lower() == "true"


class Timer:
    """Context manager for timing GCS operations.

    Controlled by ENABLE_PERFORMANCE_LOGGING environment variable.
    Set to "true" to enable timing logs, "false" to disable.
    """

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.elapsed = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Skip timing if disabled
        if not ENABLE_TIMERS:
            return

        self.elapsed = time.time() - self.start_time
        logger.info(f"  TIMER: {self.operation_name}: {self.elapsed:.3f}s")

@dataclass
class Job:
    job_id: str
    status: str
    query: str
    progress: dict
    results: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self):
        """Convert job to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict):
        """Create Job from dictionary loaded from JSON"""
        # Convert ISO format strings back to datetime objects
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)

class JobManager:
    """
    Manages job state with GCS persistence.

    Uses write-through caching:
    - All writes go to both memory cache AND GCS
    - Reads check memory first, then GCS
    - Survives Cloud Run container restarts
    """

    def __init__(self, gcs_connector=None):
        self._jobs = {}  # In-memory cache
        self._lock = threading.Lock()
        self.gcs_connector = gcs_connector

        # Log whether GCS persistence is enabled
        if self.gcs_connector:
            logger.info("JobManager initialized with GCS persistence enabled")
        else:
            logger.warning("JobManager initialized WITHOUT GCS persistence (memory-only mode)")

    def create_job(self, job_id: str, query: str):
        """Create a new job and persist to GCS"""
        with self._lock:
            now = datetime.now(UTC)
            job = Job(
                job_id=job_id,
                status="queued",
                query=query,
                progress={},
                results=None,
                error=None,
                created_at=now,
                updated_at=now,
            )

            # Save to memory cache
            self._jobs[job_id] = job

            # Persist to GCS
            self._save_job_to_gcs(job)

            return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID. Checks memory cache first, then GCS.

        This allows jobs to survive container restarts.
        """
        with self._lock:
            # Check memory cache first (fast path)
            if job_id in self._jobs:
                return self._jobs[job_id]

            # Not in memory - try loading from GCS (slow path)
            job = self._load_job_from_gcs(job_id)
            if job:
                # Cache it for future requests
                self._jobs[job_id] = job
                logger.debug(f"Loaded job {job_id} from GCS into memory cache")

            return job

    def update_progress(self, job_id: str, progress: dict):
        """Update job progress and persist to GCS"""
        with self._lock:
            # Load from GCS if not in memory (handles multi-container scenario)
            if job_id not in self._jobs:
                job = self._load_job_from_gcs(job_id)
                if job:
                    self._jobs[job_id] = job
                    logger.debug(f"Loaded job {job_id} from GCS for progress update")
                else:
                    logger.warning(f"Cannot update progress - job {job_id} not found")
                    return

            # Update progress
            self._jobs[job_id].progress = progress
            self._jobs[job_id].updated_at = datetime.now(UTC)

            # Persist progress updates to GCS
            self._save_job_to_gcs(self._jobs[job_id])

    def update_status(self, job_id: str, status: str, results: dict = None, error: str = None):
        """
        Update job status and optionally results/error. Persists to GCS.

        This method is called by worker when job completes or fails.
        """
        with self._lock:
            # Load from GCS if not in memory (handles multi-container scenario)
            if job_id not in self._jobs:
                job = self._load_job_from_gcs(job_id)
                if job:
                    self._jobs[job_id] = job
                    logger.debug(f"Loaded job {job_id} from GCS for status update")
                else:
                    logger.warning(f"Cannot update status - job {job_id} not found")
                    return

            # Update status
            self._jobs[job_id].status = status
            self._jobs[job_id].updated_at = datetime.now(UTC)

            if results is not None:
                self._jobs[job_id].results = results

            if error is not None:
                self._jobs[job_id].error = error

            # Persist to GCS
            self._save_job_to_gcs(self._jobs[job_id])
            logger.info(f"Job {job_id} status updated to: {status}")

    def _save_job_to_gcs(self, job: Job):
        """
        Persist job metadata to GCS.

        Storage path: gs://bucket/jobs/{job_id}/job_metadata.json

        Fails gracefully - if GCS write fails, job still exists in memory.
        """
        if not self.gcs_connector:
            return  # GCS persistence disabled

        try:
            with Timer(f"GCS write (job metadata for {job.job_id})"):
                blob_name = f"jobs/{job.job_id}/job_metadata.json"
                blob = self.gcs_connector.bucket.blob(blob_name)

                # Serialize job to JSON
                json_string = json.dumps(job.to_dict(), indent=2, ensure_ascii=False)

                # Upload to GCS
                blob.upload_from_string(
                    json_string,
                    content_type="application/json",
                    timeout=10
                )

            logger.debug(f"Saved job {job.job_id} metadata to GCS: {blob_name}")

        except Exception as e:
            # Log error but don't fail - job still works in memory
            logger.error(f"Failed to save job {job.job_id} to GCS: {e}")

    def _load_job_from_gcs(self, job_id: str) -> Optional[Job]:
        """
        Load job metadata from GCS.

        Returns None if job doesn't exist or GCS read fails.
        """
        if not self.gcs_connector:
            return None  # GCS persistence disabled

        try:
            with Timer(f"GCS read (job metadata for {job_id})"):
                blob_name = f"jobs/{job_id}/job_metadata.json"
                blob = self.gcs_connector.bucket.blob(blob_name)

                if not blob.exists():
                    return None

                # Download and parse JSON
                json_string = blob.download_as_text()
                job_dict = json.loads(json_string)

            # Reconstruct Job object
            job = Job.from_dict(job_dict)

            logger.debug(f"Loaded job {job_id} from GCS: {blob_name}")
            return job

        except Exception as e:
            logger.error(f"Failed to load job {job_id} from GCS: {e}")
            return None
