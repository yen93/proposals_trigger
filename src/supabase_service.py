"""Dedup/audit tracking against the proposal_router_logs Supabase table.

Actual columns (proposal_router_logs):
    id                     uuid primary key
    created_at             timestamptz
    response_id            text  -- Google Forms response id, unique
    is_processed           boolean
    status                 text        -- 'success' | 'error' | 'needs_review'
    classified_type        text, nullable  -- 'uncharted_ice' | 'keynote' | 'interactive_keynote'
    confidence             text, nullable  -- 'high' | 'medium' | 'low'
    reasoning              text, nullable
    target_subject         text, nullable
    target_trigger_id      text, nullable
    forwarded_message_id   text, nullable
    filename               text, nullable
    additional_notes       text, nullable
    error_message          text, nullable
    processed_at           timestamptz, nullable
"""

from datetime import datetime, timezone
from typing import Optional

from supabase import Client, create_client

import config


def get_client() -> Client:
    config.require("SUPABASE_URL", "SUPABASE_SERVICE_KEY")
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


def is_processed(client: Client, response_id: str) -> bool:
    resp = (
        client.table(config.SUPABASE_LOG_TABLE)
        .select("response_id")
        .eq("response_id", response_id)
        .eq("is_processed", True)
        .limit(1)
        .execute()
    )
    return bool(resp.data)


def mark_processed(
    client: Client,
    response_id: str,
    status: str,
    classified_type: Optional[str] = None,
    confidence: Optional[str] = None,
    reasoning: Optional[str] = None,
    target_subject: Optional[str] = None,
    target_trigger_id: Optional[str] = None,
    forwarded_message_id: Optional[str] = None,
    filename: Optional[str] = None,
    additional_notes: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    """Marks the Form response as processed regardless of success/error
    outcome so a bad response is never retried forever. `status`
    distinguishes the outcome."""
    client.table(config.SUPABASE_LOG_TABLE).upsert(
        {
            "response_id": response_id,
            "is_processed": True,
            "status": status,
            "classified_type": classified_type,
            "confidence": confidence,
            "reasoning": reasoning,
            "target_subject": target_subject,
            "target_trigger_id": target_trigger_id,
            "forwarded_message_id": forwarded_message_id,
            "filename": filename,
            "additional_notes": additional_notes,
            "error_message": error_message,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="response_id",
    ).execute()
