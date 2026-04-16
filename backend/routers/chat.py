"""In-browser chat endpoint that reuses the WhatsApp patient pipeline.

The calculator page embeds a chat widget. Each browser session gets a
synthetic phone number `web-<session_id>`; the backend then runs the same
intent parser + command executor that the WhatsApp webhook uses and returns
any buffered replies.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from database import get_database
from routers.auth import get_current_user
from services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    context: Optional[Dict[str, Any]] = Field(default=None)


class ChatResponse(BaseModel):
    session_id: str
    replies: List[str]


def _session_to_phone(session_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9-]", "", session_id)[:40] or uuid.uuid4().hex
    return f"web-{safe}"


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, current=Depends(get_current_user)) -> ChatResponse:
    from routers.webhook import process_incoming_message  # local import avoids cycle

    # Bind the chat session to the authenticated user so reloads resume cleanly.
    session_id = body.session_id or f"u-{current['id']}"
    phone = _session_to_phone(session_id)
    message_text = (body.message or "").strip()
    if not message_text:
        return ChatResponse(session_id=session_id, replies=[])

    # Seed a web-patient record on first contact so consent/name flow behaves.
    db = get_database()
    existing = await db.patients.find_one({"phone": phone})
    if not existing:
        from datetime import datetime, timezone

        await db.patients.insert_one(
            {
                "id": str(uuid.uuid4()),
                "phone": phone,
                "user_id": current.get("id"),
                "name": current.get("name"),
                "preferred_language": "en",
                # Authenticated web users: consent is implicit via T&C.
                "consent_status": "given",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    # Prepend calculator context (selected procedures, estimate) on first message.
    if body.context and not existing:
        ctx_line = _format_context(body.context)
        if ctx_line:
            message_text = f"{ctx_line}\n{message_text}"

    # Drain any stale messages then dispatch.
    WhatsAppService.collect_web_messages(phone)
    fake_message = {
        "from": phone,
        "id": str(uuid.uuid4()),
        "text": {"body": message_text},
    }
    await process_incoming_message(fake_message, {})
    replies = WhatsAppService.collect_web_messages(phone)
    return ChatResponse(session_id=session_id, replies=replies)


def _format_context(ctx: Dict[str, Any]) -> str:
    procs = ctx.get("procedures") or []
    state = ctx.get("state") or ""
    total = ctx.get("total")
    parts = []
    if procs:
        parts.append("Procedures I'm interested in: " + ", ".join(str(p) for p in procs))
    if state:
        parts.append(f"State: {state}")
    if total is not None:
        parts.append(f"Estimated out-of-pocket: ${total}")
    return " | ".join(parts)
