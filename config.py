"""Application settings: environment loading, SSL setup and tunable constants.

Import this module before anything that makes network calls so the
environment and certificate settings are in place.
"""

import os

import certifi
from dotenv import load_dotenv

load_dotenv()
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing. Please add it to your .env file.")

# Override with GROQ_MODEL in .env if Groq retires or renames this model.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
LLM_MAX_TOKENS = 3500
LLM_MAX_RETRIES = 3

# Maximum number of "request revision" rounds before the plan is finalized.
MAX_REVISIONS = 3

# Groq free tier allows 8000 tokens/minute per request (prompt + max_tokens).
# Roughly 4 characters per token, so these caps keep prompts well under that.
CLIP_LIMITS = {
    "flight": 2000,
    "hotel": 2000,
    "weather": 1200,
    "budget": 1500,
    "itinerary": 5000,
    "previous_draft": 4000,
}

# Specialist agents in execution order. itinerary_agent always runs last.
AGENT_ORDER = [
    "flight_agent",
    "hotel_agent",
    "weather_agent",
    "budget_agent",
    "itinerary_agent",
]
KNOWN_AGENTS = set(AGENT_ORDER)


def get_database_url() -> str:
    """Return the Postgres URL from .env, forcing sslmode=require."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL is missing. "
            "Please add your Render PostgreSQL External Database URL to .env"
        )

    if "sslmode=" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"

    return database_url
