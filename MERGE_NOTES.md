# Merge Notes — 201.82 Frontend + 201.83 Backend → ONE app

## What this merge actually did

Diffing the two archives showed they share one codebase: `201.83` is `201.82`
plus the backend wiring, so no reconciliation of divergent engines/domain
code was needed. This package is `201.83`'s tree (the superset) used as-is,
with one change.

Files that differed, and what was kept:

| File | Kept | Why |
|---|---|---|
| `api/app.py` | 201.83 version | Adds `GET /v1/me`, `POST /v1/readings`, question capture. 201.82's version is a strict subset. |
| `api/security.py` | 201.83 version | Adds the documented `local-dev-token` fallback for local testing, disabled the moment a real token registry is configured. |
| `frontend/app.js` | 201.83 version, **modified** | 201.83 already sends `Authorization: Bearer local-dev-token` and the user's `question` — required for the frontend to actually reach the backend. See below for the one behavioral change. |

`index.html` and `styles.css` were byte-identical between the two archives.

## The one functional change: no more fake results

Both archives' `app.js` had a `renderDemo()` fallback: if the `/v1/analyses`
call failed for any reason, it fabricated a Life Path number, an ascendant
sign, a fusion score, and an "interpretation" string, then rendered them as
if they were a result (labeled `status: 'DEMO'` internally, but visually
indistinguishable from a real reading).

That's exactly the thing both the backend handoff spec and your merge
instruction rule out: *"do not replace the calculation engines with
frontend logic or mock data"* / *"No fake three-map result should ever be
produced merely for visual completeness."* A fabricated Life Path number is
synthetic evidence no matter which layer invents it.

`renderDemo()` is now `renderError()`: on any failure it shows an honest
"we couldn't complete this reading" state — every map marked `Unavailable`,
fusion `NOT CALCULATED`, confidence `—` — and surfaces the real error
message. No Python/engine files were touched to make this change; it's
frontend-only.

## Why Fusion, Relationship, Contradiction, Timing, and Explanation aren't wired into the API yet

This isn't an oversight in the merge — it's a real gap in the codebase that
the merge should not paper over. Those engines exist and are fully tested
in isolation (`fusion.py`, `relationship.py`, `contradiction.py`,
`timing.py`, `explanation.py`, `integration.py`, `cross_map.py`), but they
all consume `Signal` objects that come from an ontology-mapped
`SignalMappingRegistry`. The shipped registry is empty:

```python
# config/mapping_registry.py
DEFAULT_MAPPING_REGISTRY = SignalMappingRegistry()   # no records
```

There is currently no versioned, reviewed mapping from real Numerology/
Astrology output variables (e.g. `life_path`, `ascendant.sign`) to
Theme/Axis/Pole IDs. Populating that registry is a methodology decision,
not orchestration — it's the kind of thing the handoff doc explicitly
reserves ("Do not add new methodology... Do not change the frozen
calculation rules"). Inventing plausible-looking mappings myself to light up
Fusion would be the exact same failure mode as `renderDemo()`, just moved
into the backend.

So today's honest, wired pipeline is:

```
INPUT → VALIDATE → NUMEROLOGY (real) ┐
                  → ASTROLOGY (real) ┴→ PERSIST → LINEAGE → RETURN
```

Palmistry, Convergence/Relationship, Fusion, Timing, and Explanation report
`UNAVAILABLE` (never `0`, never invented) until the mapping registry is
populated and `three_maps/services/reading_orchestrator.py` is built to
call `integrate_cross_engine()` with real `MapEvaluation`s. That's the
documented next milestone in `201.83_LOCAL_BACKEND_SMOKE_TEST.md`
("Deliberately not included yet: full reading orchestration/fusion
endpoint from raw user data").

## Running it

```bash
cd the_three_maps
pip install -e .
python run_local.py
```

Open `http://127.0.0.1:8000/`. Enter a name/DOB for a live Numerology
result; add birth time + coordinates for a live Astrology result. Palmistry
shows "Awaiting image" (no fabricated palm data — image upload isn't built
yet). The lineage/audit trail on each reading is real, not decorative.

## Not verified in this environment

This sandbox has no network access and `fastapi`/`uvicorn`/`pytest` are not
installed, so the existing test suite (`tests/`) could not be executed here
to confirm the merge is still green. No Python source files were modified
by this merge (only `frontend/app.js`), so the existing behavior/tests for
`app.py`, `security.py`, and all engines should be unaffected — but please
run `pytest` on your machine before treating this as final:

```bash
pip install -e .
pytest
```
