from flask import request, current_app
from flask_restx import Namespace, Resource, fields
from datetime import datetime, UTC
from .schemas import RetrieveRequest


api = Namespace('retrieval', description='Article retrieval & parsing')

retrieve_request_schema = api.model('RetrieveRequest', {
    'query': fields.String(required=True, description='Search query'),
    'max_results': fields.Integer(default=20, min=1, max=100, description='Maximum papers'),
    'year_min': fields.Integer(description='Minimum publication year'),
    'parse_pdfs': fields.Boolean(default=True, description='Parse PDFs')
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
        job_id = datetime.now(UTC).strftime("run_%Y-%m-%d_%H%M%S")

        job_manager.create_job(job_id, data.query)
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



