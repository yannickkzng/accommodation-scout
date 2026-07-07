from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import SearchRequest, SearchResponse
from app.services.search import search_accommodations
from app.providers.base import ProviderNotConfigured
from app.providers.hotelbeds import HotelbedsProvider

app = FastAPI(
    title="Accommodation Scout API",
    version="1.0.0",
    description="Searches, filters, deduplicates and ranks available accommodations for a Custom GPT Action.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_auth(authorization: str | None = Header(default=None)):
    expected = settings.accommodation_scout_api_token
    if not expected:
        return True
    if authorization != f"Bearer {expected}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Authorization header.",
        )
    return True


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.environment, "mock_provider": settings.use_mock_provider}


@app.post("/search-accommodations", response_model=SearchResponse)
async def search(request: SearchRequest, _: bool = Depends(verify_auth)):
    return await search_accommodations(request)


@app.get("/debug/hotelbeds-status")
async def hotelbeds_status(_: bool = Depends(verify_auth)):
    try:
        return await HotelbedsProvider().status()
    except ProviderNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Hotelbeds status check failed: {exc}") from exc
