from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import HealthResponse
from app.api import upload, training, inference, anomalies, equipment

app = FastAPI(
    title="AEGIS API",
    description="Intelligent Energy & Equipment Monitoring - contextual anomaly detection for chillers.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(training.router)
app.include_router(inference.router)
app.include_router(anomalies.router)
app.include_router(equipment.router)


@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", version=app.version)


@app.get("/")
async def root():
    return {"message": "AEGIS API is running. See /docs for the interactive API reference."}
