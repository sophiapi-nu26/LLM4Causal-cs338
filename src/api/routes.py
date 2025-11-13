from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, UTC
from .schemas import RetrieveRequest
# from .app import job_manager, worker


api_bp = Blueprint("api", __name__)

@api_bp.route('/retrieve', methods=['POST'])
def submit_retrieval():
    """Submit new retrieval job"""
    
    # get from current_app instead of import (circular)
    job_manager = current_app.job_manager
    worker = current_app.worker

    # validate request
    try:
        data = RetrieveRequest(**request.json)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    # generate job_id from timestamp
    job_id = datetime.now(UTC).strftime("run_%Y-%m-%d_%H%M%S")

    job_manager.create_job(job_id, data.query)
    worker.submit_job(job_id, data.model_dump())

    # return immediately
    return jsonify({
        "job_id": job_id,
        "status": "queued",
        "status_url": f"/api/v1/jobs/{job_id}"
    }), 202


@api_bp.route('/jobs/<job_id>', methods=['GET'])
def job_status(job_id):
    """Get job status and results"""
    job_manager = current_app.job_manager
    job = job_manager.get_job(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "results": job.results,
        "error": job.error,
        "created_at": job.created_at.isoformat()
    }), 200



