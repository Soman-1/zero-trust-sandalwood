"""Interactive Real-World GIS Map & Sandalwood Tree Radar Command Center."""

from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, status
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["GIS Map UI"])

_TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent / "templates" / "map.html"


@lru_cache(maxsize=1)
def _load_map_template() -> str:
    """Load and cache the GIS map template from disk."""
    if _TEMPLATE_PATH.is_file():
        return _TEMPLATE_PATH.read_text(encoding="utf-8")
    return "<html><body><h1>GIS Map Template Not Found</h1></body></html>"


@router.get(
    "/map",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    summary="Interactive Real-World GIS Map & Sandalwood Radar Command Center",
    description="Serves high-resolution GIS map dashboard with satellite imagery, multi-spectral AI canopy analyzer, proximity radar, and drone inspection.",
)
def get_gis_map_view():
    return HTMLResponse(content=_load_map_template(), status_code=200)
