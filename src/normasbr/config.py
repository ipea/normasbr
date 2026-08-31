import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    LLM_API_BASE = os.getenv("LLM_API_BASE", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "")
    LLM_API_KEY = os.getenv("LLM_API_KEY", None)
