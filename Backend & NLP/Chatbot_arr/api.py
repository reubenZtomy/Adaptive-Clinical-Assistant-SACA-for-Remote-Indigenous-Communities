
import os
import uvicorn
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

# Import your existing chatbot module (loads model & intents on import)
# chat.py must be in the same directory when you run this API.
import chat  # noqa: F401

# We will use selected objects/functions from chat.py
from chat import (
    route_message,
    reset_state,
    predict_tag,
    bot_name,
    dialog_state,
    # below are globals we may expose for debug
    tags,
)

app = FastAPI(
    title="SwinSACA Arrernte Chatbot API",
    description="FastAPI wrapper for the Arrernte-language SwinSACA chatbot.",
    version="1.0.0",
)

# Enable CORS (adjust origins for your deployment as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional API prefix to avoid route clashes with the English chatbot API
API_PREFIX = os.getenv("ARR_API_PREFIX", "/arr")
router = APIRouter(prefix=API_PREFIX)

# ---------- Schemas ----------

class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to the chatbot")
    reset: Optional[bool] = Field(
        False, description="If true, clears dialog state before processing"
    )


class ChatResponse(BaseModel):
    response: str
    bot: str = Field(default=bot_name)
    state: Dict[str, Any]


class PredictRequest(BaseModel):
    message: str = Field(..., description="User message to classify")


class PredictResponse(BaseModel):
    tag: str
    confidence: float


# ---------- Endpoints ----------

@router.get("/health")
def health():
    return {"status": "ok", "service": "SwinSACA Chatbot API"}


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    try:
        if req.reset:
            reset_state()
        reply = route_message(req.message)
        # Shallow copy state for response (avoid exposing internal references)
        state_copy = {
            "active_domain": dialog_state.get("active_domain"),
            "stage": dialog_state.get("stage"),
            "slots": dict(dialog_state.get("slots", {})),
        }
        return ChatResponse(response=reply, bot=bot_name, state=state_copy)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict", response_model=PredictResponse)
def predict_endpoint(req: PredictRequest):
app.include_router(router)

    try:
        tag, conf = predict_tag(req.message)
        return PredictResponse(tag=tag, confidence=conf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Allow overriding host/port via env for container platforms
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api:app", host=host, port=port, reload=True)
