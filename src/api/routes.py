from flask import request, current_app
from flask_restx import Namespace, Resource, fields
from datetime import datetime, UTC
from .schemas import RetrieveRequest
from .job_manager import JobType


api = Namespace('retrieval', description='Article retrieval & parsing')

retrieve_request_schema = api.model('RetrieveRequest', {
    'query': fields.String(required=True, description='Search query'),
    'max_results': fields.Integer(default=20, min=1, max=100, description='Maximum papers'),
    'year_min': fields.Integer(default=2020, description='Minimum publication year'),
    'parse_pdfs': fields.Boolean(default=True, description='Parse PDFs')
})

extract_single_schema = api.model('ExtractSingle', {
    'run_id': fields.String(required=True, description='Unique run identifier containing desired paper'),
    'paper_id': fields.String(required=True, description='Specific paper found under given job run'),
    'n_runs': fields.Integer(default=5, min=1, max=10, description='Number of Monte Carlo extraction runs')
})

extract_multi_schema = api.model('ExtractMulti', {
    'run_id': fields.String(required=True, description='Run ID containing papers'),
    'paper_ids': fields.List(fields.String, required=True, description='List of paper IDs'),
    'n_runs': fields.Integer(default=5, min=1, max=10, description='Monte Carlo runs per paper')
})

job_response = api.model('JobResponse', {
    'job_id': fields.String(description='Unique job identifier'),
    'status': fields.String(description='Job status'),
    'status_url': fields.String(description='URL to check job status'),
})

@api.route('/retrieve')
class SubmitRetrieval(Resource):
    @api.expect(retrieve_request_schema)
    @api.response(202, 'Job submitted', job_response)
    @api.response(400, 'Validation error')
    def post(self):
        """Submit new retrieval job"""

        # get from current_app instead of import (circular)
        job_manager = current_app.job_manager
        worker = current_app.worker

        # validate request with Pydantic
        try:
            data = RetrieveRequest(**request.json)
        except Exception as e:
            api.abort(400, str(e))

        # generate job_id from timestamp
        job_id = datetime.now(UTC).strftime("retrieve_%Y-%m-%d_%H%M%S")

        job_manager.create_job(job_id, data.query, JobType.RETRIEVAL)
        worker.submit_job(job_id, data.model_dump())

        # return immediately (no jsonify needed with Resource)
        return {
            "job_id": job_id,
            "status": "queued",
            "status_url": f"/api/v1/jobs/{job_id}"
        }, 202


@api.route('/jobs/<string:job_id>')
@api.param('job_id', 'Auto assigned job identifier')
class JobStatus(Resource):
    @api.response(200, 'Success')
    @api.response(404, 'Job not found')

    def get(self, job_id):
        """Get job status and results"""
        job_manager = current_app.job_manager
        job = job_manager.get_job(job_id)

        if not job:
            api.abort(404, "Job not found")

        return {
            "job_id": job.job_id,
            "status": job.status,
            "progress": job.progress,
            "results": job.results,
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat()
        }, 200

@api.route('/extract-graph/single')
class ExtractSingle(Resource):
    @api.expect(extract_single_schema)
    @api.response(202, 'Extraction job submitted', job_response)
    @api.response(400, 'Validation error')

    def post(self):
        """Submit single-paper Monte Carlo extraction job"""

        # Get job manager and worker from current app
        job_manager = current_app.job_manager
        worker = current_app.worker

        # Validate request data
        data = request.json
        if not data:
            api.abort(400, "Request body is required")

        # Validate required fields
        run_id = data.get('run_id')
        paper_id = data.get('paper_id')

        if not run_id:
            api.abort(400, "run_id is required")
        if not paper_id:
            api.abort(400, "paper_id is required")

        # Optional: number of Monte Carlo runs (default 5)
        n_runs = data.get('n_runs', 5)

        # Validate n_runs range
        if not isinstance(n_runs, int) or n_runs < 1 or n_runs > 10:
            api.abort(400, "n_runs must be an integer between 1 and 10")

        # Generate unique job_id for extraction
        # Use "extract_" prefix to distinguish from retrieval jobs
        job_id = datetime.now(UTC).strftime("extract_%Y-%m-%d_%H%M%S")

        # Create extraction job with paper_id as the "query" field
        # (The query field is repurposed to store what we're processing)
        job_manager.create_job(job_id, paper_id, JobType.EXTRACTION)

        # Submit job to worker with extraction parameters
        worker.submit_job(job_id, {
            'run_id': run_id,
            'paper_id': paper_id,
            'n_runs': n_runs
        })

        # Return immediately with job info
        return {
            "job_id": job_id,
            "status": "queued",
            "status_url": f"/api/v1/jobs/{job_id}",
            "extraction_params": {
                "run_id": run_id,
                "paper_id": paper_id,
                "n_runs": n_runs
            }
        }, 202

@api.route('/extract-graph/multi')
class ExtractMulti(Resource):
    @api.expect(extract_multi_schema)
    @api.response(202, 'Multi-extraction job submitted', job_response)
    @api.response(400, 'Validation error')

    def post(self):
        """Submit multi-paper Monte Carlo extraction job"""
        job_manager = current_app.job_manager
        worker = current_app.worker
        data = request.json

        # Validation
        if not data:
            api.abort(400, "Request body is required")

        run_id = data.get('run_id')
        paper_ids = data.get('paper_ids')

        if not run_id:
            api.abort(400, "run_id is required")
        if not paper_ids or not isinstance(paper_ids, list) or len(paper_ids) == 0:
            api.abort(400, "paper_ids must be a non-empty list")
        if len(paper_ids) > 20:
            api.abort(400, "paper_ids cannot exceed 20 papers")

        n_runs = data.get('n_runs', 5)
        if not isinstance(n_runs, int) or n_runs < 1 or n_runs > 10:
            api.abort(400, "n_runs must be an integer between 1 and 10")

        # Create job
        job_id = datetime.now(UTC).strftime("extract_multi_%Y-%m-%d_%H%M%S")
        job_manager.create_job(job_id, f"{len(paper_ids)} papers", JobType.MULTI_EXTRACTION)

        # Submit to worker
        worker.submit_job(job_id, {
            'run_id': run_id,
            'paper_ids': paper_ids,
            'n_runs': n_runs
        })

        return {
            "job_id": job_id,
            "status": "queued",
            "status_url": f"/api/v1/jobs/{job_id}",
            "extraction_params": {
                "run_id": run_id,
                "paper_count": len(paper_ids),
                "paper_ids": paper_ids,
                "n_runs": n_runs
            }
        }, 202
