# Vercel entrypoint — re-exports the FastAPI app for @vercel/python
# The file must live in api/ for Vercel to discover it automatically.
from app.main import app  # noqa: F401

__all__ = ['app']

