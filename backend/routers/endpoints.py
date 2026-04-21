"""
CRUD for target model endpoints persisted to config/endpoints.json.
"""
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.settings import settings

router = APIRouter(prefix="/api/endpoints", tags=["endpoints"])


class EndpointIn(BaseModel):
    name: str
    base_url: str
    model_id: str


class Endpoint(EndpointIn):
    id: str


def _read() -> list[Endpoint]:
    f = settings.endpoints_file
    if not f.exists():
        return []
    return [Endpoint(**e) for e in json.loads(f.read_text())]


def _write(endpoints: list[Endpoint]) -> None:
    settings.endpoints_file.parent.mkdir(parents=True, exist_ok=True)
    settings.endpoints_file.write_text(
        json.dumps([e.model_dump() for e in endpoints], indent=2)
    )


@router.get("", response_model=list[Endpoint])
def list_endpoints():
    return _read()


@router.post("", response_model=Endpoint, status_code=201)
def create_endpoint(body: EndpointIn):
    endpoints = _read()
    ep = Endpoint(id=str(uuid.uuid4()), **body.model_dump())
    endpoints.append(ep)
    _write(endpoints)
    return ep


@router.put("/{ep_id}", response_model=Endpoint)
def update_endpoint(ep_id: str, body: EndpointIn):
    endpoints = _read()
    for i, ep in enumerate(endpoints):
        if ep.id == ep_id:
            updated = Endpoint(id=ep_id, **body.model_dump())
            endpoints[i] = updated
            _write(endpoints)
            return updated
    raise HTTPException(status_code=404, detail="Endpoint not found")


@router.delete("/{ep_id}", status_code=204)
def delete_endpoint(ep_id: str):
    endpoints = _read()
    filtered = [ep for ep in endpoints if ep.id != ep_id]
    if len(filtered) == len(endpoints):
        raise HTTPException(status_code=404, detail="Endpoint not found")
    _write(filtered)
