"""Internal enrollment service: uvicorn server:app --port 8001  (called only by the backend)."""
import hmac

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

import config
from registration import process_samples

app = FastAPI(title="Face Engine Service")


class EmbedIn(BaseModel):
    images: list[str] = Field(min_length=1, max_length=20)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/embed")
def embed(data: EmbedIn, x_service_token: str = Header(default="")):
    if not config.SERVICE_TOKEN or not hmac.compare_digest(x_service_token, config.SERVICE_TOKEN):
        raise HTTPException(401, "Invalid service token")
    return {"results": process_samples(data.images)}
