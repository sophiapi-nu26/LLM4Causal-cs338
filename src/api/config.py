import os
from dotenv import load_dotenv

load_dotenv()

class Config(object):
    DEBUG = False

class DevConfig(Config):
    DEBUG = True
    SEMANTIC_SCHOLAR_KEY=os.getenv("SEMANTIC_SCHOLAR_KEY")
    GOOGLE_APPLICATION_CREDENTIALS=os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    GCP_BUCKET_NAME=os.getenv("GCP_BUCKET_NAME")

