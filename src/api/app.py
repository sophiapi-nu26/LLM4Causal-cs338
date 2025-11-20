from flask import Flask
from flask_restx import Api
import logging
import sys
from .config import DevConfig
from .routes import api as retrieval_namespace
from .job_manager import JobManager
from .worker import JobWorker

def create_app():
    # set up logging for application
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stdout
    )

    app = Flask(__name__)

    app.config.from_object(DevConfig)

    api = Api(
        app,
        version='1.0',
        title='MCG Retrieval API',
        description='Retrieve and parse material science documents'
    )

    # Initialize GCS connector for job persistence
    try:
        from document_preparation.gcp_connector import GCPBucketConnector
        gcs_connector = GCPBucketConnector()
        logging.info("GCS connector initialized for job persistence")
    except Exception as e:
        logging.warning(f"Failed to initialize GCS connector: {e}. Jobs will be memory-only.")
        gcs_connector = None

    # Initialize JobManager with GCS persistence
    app.job_manager = JobManager(gcs_connector=gcs_connector)
    app.worker = JobWorker(app.job_manager)

    # get routes
    api.add_namespace(retrieval_namespace, path='/api/v1')

    from flask_cors import CORS
    CORS(app)

    # start worker
    app.worker.start()

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5001) # for macOS local
