"""
Step 85: Minimal FastAPI endpoint for programmatic simulation.

Usage:
    pip install fastapi uvicorn
    uvicorn rcm_mc.api:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    app = FastAPI(title="RCM Monte Carlo API", version="0.5.0")

    class SimulateRequest(BaseModel):
        actual_config: Dict[str, Any]
        benchmark_config: Dict[str, Any]
        n_sims: int = 1000
        seed: int = 42
        align_profile: bool = True

    class SimulateResponse(BaseModel):
        ebitda_drag_mean: float
        ebitda_drag_p10: float
        ebitda_drag_p90: float
        economic_drag_mean: float
        n_sims: int

    @app.post("/simulate", response_model=SimulateResponse)
    def simulate_endpoint(req: SimulateRequest) -> SimulateResponse:
        from .infra.config import validate_config
        from .core.simulator import simulate_compare

        try:
            actual = validate_config(req.actual_config)
            benchmark = validate_config(req.benchmark_config)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Config validation failed: {e}")

        df = simulate_compare(
            actual, benchmark,
            n_sims=req.n_sims,
            seed=req.seed,
            align_profile=req.align_profile,
        )

        return SimulateResponse(
            ebitda_drag_mean=float(df["ebitda_drag"].mean()),
            ebitda_drag_p10=float(df["ebitda_drag"].quantile(0.10)),
            ebitda_drag_p90=float(df["ebitda_drag"].quantile(0.90)),
            economic_drag_mean=float(df["economic_drag"].mean()),
            n_sims=len(df),
        )

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok"}

except ImportError:
    app = None
