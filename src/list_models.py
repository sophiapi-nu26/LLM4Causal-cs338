# Quick script to list available Gemini models
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("GEMINI_API_KEY not found!")
    exit(1)

try:
    client = genai.Client()
    models = client.models.list()
    
    print("Available Gemini models:")
    for model in models:
        print(f"- {model.name}")
        
except Exception as e:
    print(f"Error listing models: {e}")
