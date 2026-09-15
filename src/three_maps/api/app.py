from __future__ import annotations

import os
import pathlib
from datetime import date, datetime, timezone
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from three_maps.domain.types import AnalysisStatus, Target, VersionBundle, InputSnapshot
from three_maps.engines.numerology import (
    life_path, birthday_number, attitude_number, expression_number,
    soul_urge, personality_number, maturity_number,
)
from three_maps.engines.astrology import calculate_astrology
from three_maps.persistence import SQLiteRepository
from three_maps.engines.lineage import make_lineage, canonical_hash
from three_maps.api.security import SecurityPolicy, validate_requested_maps, validate_name, validate_analysis_id, authenticate_request
from three_maps.config.production import load_settings
from three_maps.api.hardening import FixedWindowRateLimiter, request_id


API_VERSION = "AV-0.2.0"
METHODOLOGY_VERSION = "MV-0.1.0"
ONTOLOGY_VERSION = "OV-0.1.0"
CALCULATION_VERSION = "CV-0.1.0"
EXPLANATION_VERSION = "EV-0.1.0"
PRESENTATION_VERSION = "PV-0.1.0"

VERSIONS = VersionBundle(
    methodology_version=METHODOLOGY_VERSION,
    ontology_version=ONTOLOGY_VERSION,
    calculation_version=CALCULATION_VERSION,
    explanation_version=EXPLANATION_VERSION,
    presentation_version=PRESENTATION_VERSION,
)


class AnalysisCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, max_length=200)
    birth_date: date | None = None
    birth_datetime: datetime | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    target: Target
    requested_maps: list[str] = Field(default_factory=lambda: ["NUMEROLOGY", "ASTROLOGY"], max_length=3)
    question: str | None = Field(default=None, max_length=1000)


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysis_id: str
    status: AnalysisStatus
    input_snapshot_id: str
    version_bundle: VersionBundle
    requested_maps: list[str]
    available_maps: list[str]
    result_hash: str


class _Store:
    def __init__(self) -> None:
        self.analyses: dict[str, dict[str, Any]] = {}
        self.lineage: dict[str, list[Any]] = {}

    def put(self, analysis_id: str, record: dict[str, Any]) -> None:
        self.analyses[analysis_id] = record


store = _Store()
settings = load_settings()
repository = SQLiteRepository()
app = FastAPI(title="THE THREE MAPS API", version=API_VERSION)
if settings.allowed_origins:
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.allowed_origins), allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"])
rate_limiter = FixedWindowRateLimiter(settings.rate_limit_per_minute)
app.mount("/frontend", StaticFiles(directory="src/three_maps/frontend"), name="frontend")

@app.middleware("http")
async def security_headers(request: Request, call_next):
    policy = SecurityPolicy(max_body_bytes=settings.max_body_bytes)
    rid = request.headers.get("X-Request-ID") or request_id()
    if not rate_limiter.allow(request.client.host if request.client else "unknown"):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded", "request_id": rid}, headers={"Retry-After": "60", "X-Request-ID": rid})
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > policy.max_body_bytes:
        return __import__("fastapi.responses", fromlist=["JSONResponse"]).JSONResponse(status_code=413, content={"detail": "Request body too large"})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Request-ID"] = rid
    return response


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _require_analysis(analysis_id: str, owner_id: str) -> dict[str, Any]:
    validate_analysis_id(analysis_id)
    record = store.analyses.get(analysis_id)
    if record is None or record.get("owner_id") != owner_id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return record


def _calculate_numerology(name: str | None, birth_date: date | None) -> dict[str, Any]:
    if birth_date is None and name is None:
        return {}
    result: dict[str, Any] = {}
    if birth_date is not None:
        result.update({
            "life_path": life_path(birth_date),
            "birthday": birthday_number(birth_date),
            "attitude": attitude_number(birth_date),
        })
    if name:
        result.update({
            "expression": expression_number(name),
            "soul_urge": soul_urge(name),
            "personality": personality_number(name),
        })
    if birth_date is not None and name:
        result["maturity"] = maturity_number(birth_date, name)
    return {k: v.__dict__ for k, v in result.items()}


def _calculate_maps(req: AnalysisCreateRequest) -> tuple[dict[str, Any], list[str], list[Any]]:
    maps: dict[str, Any] = {}
    available: list[str] = []
    lineage = []
    requested = {m.upper() for m in req.requested_maps}

    if "NUMEROLOGY" in requested and (req.name or req.birth_date):
        maps["numerology"] = _calculate_numerology(req.name, req.birth_date)
        available.append("NUMEROLOGY")
        lineage.append(make_lineage("NUMEROLOGY", "calculation", "NUM-RESULT", METHODOLOGY_VERSION,
                                    ONTOLOGY_VERSION, CALCULATION_VERSION))

    if "ASTROLOGY" in requested and req.birth_datetime is not None and req.latitude is not None and req.longitude is not None:
        maps["astrology"] = calculate_astrology(req.birth_datetime, req.longitude, req.latitude,
                                                  methodology_version=METHODOLOGY_VERSION,
                                                  calculation_version=CALCULATION_VERSION)
        maps["astrology"] = maps["astrology"].__dict__
        available.append("ASTROLOGY")
        lineage.append(make_lineage("ASTROLOGY", "calculation", "AST-RESULT", METHODOLOGY_VERSION,
                                    ONTOLOGY_VERSION, CALCULATION_VERSION))

    return maps, available, lineage


@app.get("/v1/me")
def get_current_user(owner_id: str = Depends(authenticate_request)) -> dict[str, str]:
    """Return the current principal for local/product smoke testing."""
    return {"user_id": owner_id, "environment": settings.environment}


@app.post("/v1/readings", response_model=AnalysisResponse, status_code=201)
def create_reading(req: AnalysisCreateRequest, owner_id: str = Depends(authenticate_request), request: Request = None) -> AnalysisResponse:
    """Product-facing alias for an analysis session.

    The V1 intelligence core remains authoritative; this endpoint currently
    creates the same immutable analysis record while preserving the user's
    question for the future reading/explanation layer.
    """
    return create_analysis(req, owner_id=owner_id, request=request)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "api_version": API_VERSION, "environment": settings.environment}

@app.get("/ready")
def ready() -> dict[str, str]:
    try:
        repository.conn.execute("SELECT 1").fetchone()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Persistence unavailable") from exc
    return {"status": "ready", "api_version": API_VERSION}


@app.post("/v1/analyses", response_model=AnalysisResponse, status_code=201)
def create_analysis(req: AnalysisCreateRequest, owner_id: str = Depends(authenticate_request), request: Request = None) -> AnalysisResponse:
    req.name = validate_name(req.name)
    req.requested_maps = validate_requested_maps(req.requested_maps)
    idem = request.headers.get("Idempotency-Key", "") if request else ""
    if idem:
        if len(idem) > 128:
            raise HTTPException(status_code=422, detail="Idempotency-Key too long")
        existing = repository.get_idempotency(owner_id, idem)
        if existing:
            record = store.analyses.get(existing)
            if record:
                return AnalysisResponse(analysis_id=existing, status=record["status"], input_snapshot_id=record["input_snapshot"]["id"], version_bundle=VERSIONS, requested_maps=record["requested_maps"], available_maps=record["available_maps"], result_hash=record["result_hash"])
    analysis_id = "ANL-" + uuid4().hex[:12]
    snapshot_id = "INP-" + uuid4().hex[:12]
    now = _utc_now()
    snapshot = InputSnapshot(
        id=snapshot_id,
        analysis_id=analysis_id,
        data=req.model_dump(mode="json"),
        created_at=now,
        immutable=True,
        version_bundle=VERSIONS,
    )

    try:
        maps, available, lineage = _calculate_maps(req)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    status = AnalysisStatus.COMPLETED if available else AnalysisStatus.PARTIAL
    record = {
        "analysis_id": analysis_id,
        "owner_id": owner_id,
        "status": status,
        "input_snapshot": snapshot.model_dump(mode="json"),
        "version_bundle": VERSIONS.model_dump(mode="json"),
        "requested_maps": req.requested_maps,
        "available_maps": available,
        "target": req.target.model_dump(mode="json"),
        "question": req.question,
        "maps": maps,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    record["result_hash"] = canonical_hash(record)
    store.put(analysis_id, record)
    store.lineage[analysis_id] = lineage
    analysis_obj = __import__("three_maps.domain.types", fromlist=["Analysis"]).Analysis(id=analysis_id, owner_id=owner_id, status=status, input_snapshot_id=snapshot_id, version_bundle=VERSIONS, requested_maps=req.requested_maps, target=req.target, created_at=now, updated_at=now)
    repository.save_analysis(analysis_obj, snapshot)
    for lin in lineage:
        repository.save_lineage(analysis_id, lin)
    if idem:
        repository.save_idempotency(owner_id, idem, analysis_id)

    return AnalysisResponse(
        analysis_id=analysis_id,
        status=status,
        input_snapshot_id=snapshot_id,
        version_bundle=VERSIONS,
        requested_maps=req.requested_maps,
        available_maps=available,
        result_hash=record["result_hash"],
    )


@app.get("/v1/analyses/{analysis_id}")
def get_analysis(analysis_id: str, owner_id: str = Depends(authenticate_request)) -> dict[str, Any]:
    return _require_analysis(analysis_id, owner_id)


@app.get("/v1/analyses/{analysis_id}/maps/{map_name}")
def get_map(analysis_id: str, map_name: str, owner_id: str = Depends(authenticate_request)) -> dict[str, Any]:
    record = _require_analysis(analysis_id, owner_id)
    key = map_name.lower()
    if key not in record["maps"]:
        raise HTTPException(status_code=404, detail="Requested map result is unavailable")
    return {"analysis_id": analysis_id, "map": key, "result": record["maps"][key]}


@app.get("/v1/analyses/{analysis_id}/lineage")
def get_lineage(analysis_id: str, owner_id: str = Depends(authenticate_request)) -> list[dict[str, Any]]:
    _require_analysis(analysis_id, owner_id)
    return [x.model_dump(mode="json") for x in store.lineage.get(analysis_id, [])]


def _web_token() -> str:
    """The bearer token the served frontend should use.

    In local development (no token registry configured) this is the
    documented `local-dev-token`, matching what security.py accepts. Once
    THE_THREE_MAPS_WEB_TOKEN or THE_THREE_MAPS_AUTH_TOKENS is configured
    (e.g. on a public deployment), the real token is injected here instead
    -- it lives in the server's environment, not in the public app.js file.
    """
    configured = os.getenv("THE_THREE_MAPS_WEB_TOKEN", "").strip()
    if configured:
        return configured
    return "local-dev-token"


@app.get("/", include_in_schema=False)
def frontend_root():
    from fastapi.responses import HTMLResponse
    import json as _json
    html = pathlib.Path("src/three_maps/frontend/index.html").read_text(encoding="utf-8")
    injected = f'<script>window.__THREE_MAPS_TOKEN__={_json.dumps(_web_token())};</script>\n</head>'
    html = html.replace("</head>", injected, 1)
    return HTMLResponse(html)
