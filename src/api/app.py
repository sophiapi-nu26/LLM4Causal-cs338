from flask import Flask
from .config import DevConfig
from .routes import api_bp
from .job_manager import JobManager
from .worker import JobWorker

def create_app():
    app = Flask(__name__)

    app.config.from_object(DevConfig)

    app.job_manager = JobManager()
    app.worker = JobWorker(app.job_manager)
    
    # get routes
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    from flask_cors import CORS
    CORS(app)

    # start worker
    app.worker.start()
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5001)
