"""Fires a downstream pipeline's routine directly via its bound-session HTTP
"fire" endpoint, bypassing the RemoteTrigger Claude Code tool entirely.

Why this exists: a routine-run agent's RemoteTrigger tool can only call
action="run" against triggers that agent itself created -- not these 4
routines, all of which were created via the http_api (confirmed by their
"created_via" field). That means the original design -- main.py prints
`trigger_ids_to_fire`, the routine's own job_config agent reads it and calls
RemoteTrigger -- cannot work for these specific downstream targets. This
module's plain authenticated HTTP call has no such restriction, since it
isn't going through the RemoteTrigger tool at all; it's the same mechanism
already used by apps_script/on_form_submit.gs to fire this repo's own
routine from a Google Form submission.

Each downstream routine's fire endpoint requires its OWN bearer token
(config.fire_token_for), minted via the claude.ai UI -- not interchangeable
between routines. Never log or persist these tokens.
"""

import logging

import requests

log = logging.getLogger("trigger_fire_service")

FIRE_URL_TEMPLATE = "https://api.anthropic.com/v1/claude_code/routines/{trigger_id}/fire"


def fire(trigger_id: str, token: str, text: str = "") -> bool:
    """Best-effort: returns True on a 2xx response, False on any failure
    (missing token, HTTP error, network error) -- never raises. Firing is an
    optimization for zero-lag handoff, not the actual handoff itself (the
    forwarded email already guarantees the downstream routine's own hourly
    cron will pick it up eventually), so a failure here must never break the
    caller's own success path."""
    if not token:
        log.warning("No fire token configured for trigger %s -- skipping direct fire; "
                    "the downstream routine's own hourly cron will still pick this up.", trigger_id)
        return False

    try:
        response = requests.post(
            FIRE_URL_TEMPLATE.format(trigger_id=trigger_id),
            headers={
                "Authorization": f"Bearer {token}",
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "experimental-cc-routine-2026-04-01",
                "Content-Type": "application/json",
            },
            json={"text": text} if text else {},
            timeout=30,
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        log.exception("Failed to fire trigger %s", trigger_id)
        return False
