# Report 0033: Key File — `RCM_MC/deploy/Dockerfile`

## Scope

Reads `RCM_MC/deploy/Dockerfile` line-by-line on `origin/main` at commit `f3f7e7f`. 35 lines, 1,186 B. Owed since Reports 0023, 0026, 0028, 0032.

Prior reports reviewed: 0029-0032.

## Findings

### Full file (35 lines)

```dockerfile
FROM python:3.14-slim                                                # 1

LABEL maintainer="RCM-MC Team"                                       # 3
LABEL description="RCM-MC analytics platform"                        # 4

WORKDIR /app                                                         # 6

RUN apt-get update && \                                              # 9-11
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./                                               # 13
COPY rcm_mc/ rcm_mc/                                                 # 14

RUN pip install --no-cache-dir .                                     # 16

RUN mkdir -p /data                                                   # 19
ENV RCM_MC_DB=/data/rcm_mc.db                                        # 20

EXPOSE 8080                                                          # 22

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \                # 24-25
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

ENTRYPOINT ["python", "-m", "rcm_mc", "serve"]                       # 27
CMD ["--db", "/data/rcm_mc.db", "--port", "8080", "--host", "0.0.0.0"]  # 35
```

### Per-line analysis

| Line | Item | Notes |
|---|---|---|
| 1 | `FROM python:3.14-slim` | Pins Python 3.14 (the latest declared per pyproject classifier). `slim` variant — minimal Debian + Python. |
| 3-4 | LABELs | Cosmetic OCI metadata. |
| 6 | `WORKDIR /app` | Container root. Source tree lands at `/app/rcm_mc/`. |
| 9-11 | apt install gcc g++ | **Build-time only — never cleaned out.** Final image carries gcc+g++ unnecessarily (cross-link Report 0032 MR290 multi-stage build). |
| 13 | `COPY pyproject.toml ./` | One-line; **needed for `pip install .` to find the project metadata.** |
| 14 | `COPY rcm_mc/ rcm_mc/` | Copies the entire package source. **Cache-invalidates on any source change** — every code edit re-runs Step 16. (Report 0032 MR289.) |
| 16 | `pip install --no-cache-dir .` | **Critical:** installs **only core deps** (numpy, pandas, pyyaml, matplotlib, openpyxl). **NO `[diligence]`, `[exports]`, `[api]`, `[all]`.** Pyarrow + python-pptx + python-docx + fastapi + uvicorn + scipy all absent. |
| 19 | `mkdir -p /data` | Creates the SQLite mount point. |
| 20 | `ENV RCM_MC_DB=/data/rcm_mc.db` | Container default for the DB path. **Redundant with `docker-compose.yml:38`** but consistent. |
| 22 | `EXPOSE 8080` | Documentation only — actual port mapping happens in compose. |
| 24-25 | HEALTHCHECK | Calls `http://localhost:8080/health` every 30s. Comment in Dockerfile (lines 32-34): "in-container HEALTHCHECK silently passes either way" — flagged in Report 0032 MR291. |
| 27 | ENTRYPOINT | `python -m rcm_mc serve` — invokes the `__main__.py` entry. **Note:** uses `-m` (module form) rather than the `rcm-mc` console script entry. Cross-link Report 0003 MR14 (broken `rcm-intake` entry-point); using `-m` sidesteps the console-script path entirely. |
| 35 | CMD | Default args: `--db /data/rcm_mc.db --port 8080 --host 0.0.0.0`. **`--host 0.0.0.0` is the production-vs-default override** explained in the comment at lines 28-34. |

### What's NOT in the Dockerfile

| Missing | Impact |
|---|---|
| **Multi-stage build** | gcc/g++ stay in final image (~50-80 MB bloat). |
| **Specific Python patch version** | `python:3.14-slim` floats; rebuilds get whatever's current. |
| **`pip install .[diligence]` or any extras** | Production cannot run any path through `rcm_mc/diligence/ingest/` (Report 0023 MR183, Report 0032 MR283). |
| **`USER nonroot`** or non-root user | Runs as root inside container — typical security hardening would `USER 1000` or similar. |
| **`COPY .dockerignore` excludes** | Note: `.dockerignore` exists at repo root + at `RCM_MC/.dockerignore` (Report 0002). |
| **Source code lock — no requirements-lock.txt** | Pip resolves on every build. (Report 0023 MR189.) |
| **Production logging config** | No env-var overrides for log level (Report 0024 MR199). |

### Dependencies

- **Incoming:** `RCM_MC/deploy/docker-compose.yml:13-14` (`build: context: .., dockerfile: deploy/Dockerfile`); GitHub Actions `deploy.yml`; the systemd unit's `docker compose up -d --build`.
- **Outgoing:** `python:3.14-slim` (Docker Hub), Debian apt packages (gcc, g++), `pyproject.toml` (for the `pip install .` resolution), `rcm_mc/` source tree.

### Cross-link to prior reports

- Report 0023 MR183 — pyarrow isolation violated; this Dockerfile is the **production install** that doesn't include `[diligence]` extras → confirms the bug is reachable in production.
- Report 0026 MR229 — CI installs only `[dev]`; this Dockerfile installs only core. **Neither path tests `[exports]` / `[diligence]` / `[api]`.**
- Report 0019 MR142 — `feature/workbench-corpus-polish` removes `RCM_MC_DB` env var support. This Dockerfile sets `RCM_MC_DB` at line 20 — that branch's removal would break the implicit contract.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR294** | **Production install missing `[diligence]` extras** (cross-link MR183, MR283) | Critical — flagged again because this is the canonical install. | **Critical** (cumulative) |
| **MR295** | **`python:3.14-slim` floats — no patch pin** | Each build pulls latest 3.14.x. Reproducibility weak. Recommend pinning to digest. | Medium |
| **MR296** | **Container runs as root** | `python -m rcm_mc serve` runs as the default container user (root in slim). Defense-in-depth gap. | Medium |
| **MR297** | **`COPY rcm_mc/ rcm_mc/` invalidates pip-install cache on every source change** | Layer order suboptimal. Should `COPY pyproject.toml + RUN pip install` first, then `COPY rcm_mc/`. | Low |
| **MR298** | **`gcc g++` stay in final image** | No multi-stage build; final image carries dev tools. | Medium |
| **MR299** | **HEALTHCHECK can silently pass with wrong bind** | (Documented in Dockerfile comment.) Acceptable but flagged. | Low |
| **MR300** | **`-m rcm_mc serve` sidesteps the console-script entry** | This works around the broken `rcm-intake` entry point (Report 0003 MR14). Pre-merge: any branch that removes `rcm_mc/__main__.py` breaks the container. | Medium |

## Open questions / Unknowns

- **Q1.** Does the Docker build include `RCM_MC/configs/`? `COPY rcm_mc/ rcm_mc/` only copies the package. The simulator needs configs at runtime — operator must supply paths.
- **Q2.** Why `pip install --no-cache-dir .` (no `-e`)? Editable mode is for dev only; non-editable is correct for prod. ✓ already-resolved.
- **Q3.** Does `python -m rcm_mc` resolve to `rcm_mc/__main__.py`? If so, what does it do?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0034** | **Read `rcm_mc/__main__.py`** | Resolves Q3 — what `-m rcm_mc serve` actually invokes. |
| **0035** | **Read `docker-compose.yml`** end-to-end (86 lines) | Pairs with this report. |
| **0036** | **Read `vm_setup.sh`** end-to-end (109 lines) | Closes the deploy stack. |

---

Report/Report-0033.md written. Next iteration should: read `rcm_mc/__main__.py` and confirm what `python -m rcm_mc serve` invokes — closes Q3 here and pins the production entry-point path that bypasses the broken `rcm-intake` console script.

