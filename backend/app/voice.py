"""ElevenLabs voice-agent seam.

The browser never sees the API key. It asks this backend for a short-lived
WebRTC conversation token, then starts the session with the ElevenLabs SDK.
Docs: https://elevenlabs.io/docs/api-reference/conversations/get-webrtc-token
"""

import httpx
from fastapi import APIRouter, Request

from .errors import ApiError

router = APIRouter(prefix="/api/voice")

ELEVENLABS_TOKEN_URL = "https://api.elevenlabs.io/v1/convai/conversation/token"


@router.get("/status")
def voice_status(request: Request):
    return {"configured": request.app.state.settings.voice_configured}


@router.get("/conversation-token")
def conversation_token(request: Request):
    settings = request.app.state.settings
    if not settings.voice_configured:
        raise ApiError(503, "voice_not_configured",
                       "Set ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID in .env to enable voice.")
    try:
        resp = httpx.get(
            ELEVENLABS_TOKEN_URL,
            params={"agent_id": settings.elevenlabs_agent_id},
            headers={"xi-api-key": settings.elevenlabs_api_key},
            timeout=10,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        raise ApiError(502, "voice_upstream_error", "Could not get a conversation token from ElevenLabs.",
                       {"upstream_status": status})
    return {"token": resp.json()["token"]}
