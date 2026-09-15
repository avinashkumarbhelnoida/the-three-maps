# Deploying THE THREE MAPS to Render

This deploys the frontend and backend together as **one** Render web service
(FastAPI already serves the static frontend itself), using the included
`render.yaml` blueprint. Render does not support dropping a zip file for web
services — it deploys from a Git repository, so step 1 is getting this code
into one.

## 1. Push this project to GitHub

```bash
cd the_three_maps
git init
git add .
git commit -m "THE THREE MAPS: merged frontend + backend"
```
Create an empty repo on GitHub (or GitLab), then:
```bash
git remote add origin <your-repo-url>
git branch -M main
git push -u origin main
```

## 2. Create the Blueprint on Render

1. Go to the Render dashboard → **New** → **Blueprint**.
2. Connect the repo you just pushed. Render will detect `render.yaml`
   automatically and show you the one service it defines
   (`the-three-maps`, free plan).
3. Click **Apply**. Render will run `pip install -e .` (this also installs
   `pyswisseph`, which compiles a small C extension — Render's Python build
   image includes the compiler this needs, so no extra setup) and then start
   `uvicorn three_maps.api.app:app --host 0.0.0.0 --port $PORT`.
4. When the build finishes you'll get a URL like
   `https://the-three-maps.onrender.com`. Open it — that's the real app.

## What the blueprint already handles for you

- **Port binding.** Render assigns its own `$PORT`; the start command binds
  to it and to `0.0.0.0` (required — `run_local.py`'s hardcoded
  `127.0.0.1:8000` is for local use only and isn't used here).
- **The auth token.** `render.yaml` sets `THE_THREE_MAPS_WEB_TOKEN` with
  `generateValue: true`, so Render generates a random secret at deploy time
  instead of you picking one. `api/app.py` reads it server-side and injects
  it into the page it serves (`window.__THREE_MAPS_TOKEN__`), so the real
  token lives only in Render's environment variables — never in the
  committed `app.js`. The well-known `local-dev-token` default is
  automatically disabled the moment this variable is set (see
  `api/security.py`), regardless of `THE_THREE_MAPS_ENV`.
- **Dependencies.** `pyswisseph` (needed for Astrology) was missing from
  `pyproject.toml` before this pass — it's now declared, so Astrology will
  actually work on this deployment, unlike in the browser-only preview I
  showed earlier.

## What's still true after deploying

- **No persistent disk on the free plan.** Every reading lives in an
  in-memory SQLite database for the life of the running process. A restart,
  redeploy, or the free tier's spin-down after 15 minutes of inactivity
  clears it. If you want readings to survive that, you'd need a paid disk
  (or Render's free Postgres, which itself expires after 30 days) and a
  small change to point `THE_THREE_MAPS_DB_PATH` at it.
- **Cold starts.** The first request after 15 minutes of inactivity will
  hang for several seconds while the free instance spins back up.
- **Fusion/Relationship/Explanation are still unavailable.** That's a gap in
  the mapping-registry content, not something deployment changes — see
  `MERGE_NOTES.md`.
- **The bearer token is still a shared secret, not real user accounts.**
  Anyone with your URL and access to browser dev tools can read the token
  out of the page source and call the API as `web-user`. That's fine for
  sharing with people you trust to try it out; it is not access control for
  a public product. Real multi-user auth is out of scope for this pass (the
  original handoff spec explicitly defers a production identity provider).

## Rotating or replacing the token

Render → your service → **Environment** → edit `THE_THREE_MAPS_WEB_TOKEN` →
save. Render redeploys automatically with the new value; the frontend picks
it up on next page load since it's injected server-side per request.
