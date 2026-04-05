"""
To use CrewAI with LLM:
1. Get an OpenAI API key from https://platform.openai.com/
2. Set it as environment variable:
   - Windows: set OPENAI_API_KEY=your_key_here
   - Or add to .env file

Then run the application - CrewAI will use LLM for agent reasoning!
"""

import os

try:
    # Optional: load from .env if python-dotenv installed
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

if OPENAI_API_KEY:
    print("[System] OPENAI_API_KEY detected. CrewAI with LLM can be enabled.")
else:
    print("[System] No OPENAI_API_KEY found. Using non-LLM pipeline.")
