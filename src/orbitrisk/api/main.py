from fastapi import FastAPI

from orbitrisk.api.routes import router

app = FastAPI(
    title="OrbitRisk API",
    version="0.1.0",
    description="Risk-as-a-Service API for parametric crop insurance.",
)

app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
