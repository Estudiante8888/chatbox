import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

models = genai.list_models()  # List available mod
for m in models:
    print(f"{m.name} - {m.supported_generation_methods}")