"""Loads environment variables and project_vars.txt constants for the router."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN_STORE_PATH = BASE_DIR / ".google_token.json"


def _load_project_vars() -> dict:
    with open(BASE_DIR / "project_vars.txt", encoding="utf-8") as f:
        data = json.load(f)
    return data[0]


_PROJECT_VARS = _load_project_vars()

NOTIFICATION_RECIPIENTS = _PROJECT_VARS["notification_recipients"]
# The shared mailbox identity behind GOOGLE_REFRESH_TOKEN — every downstream
# pipeline's Gmail trigger search runs against this same inbox, so a
# self-addressed forward lands exactly where a salesperson's manual email
# would have.
FORWARD_TO_ADDRESS = _PROJECT_VARS["mailbox_address"]

# Optional: the whole Form-reading path (src/router_form_service.py) is
# skipped entirely (run_once() treats it as not configured) until this is
# filled in after the "Demo Notes Router Intake" form is created.
ROUTER_FORM_ID = _PROJECT_VARS.get("router_form_id") or ""

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN", "")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

SUPABASE_LOG_TABLE = "proposal_router_logs"

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/forms.responses.readonly",
]

# Fixed live-infra routing table — reproduced verbatim from the 3 downstream
# routines' existing job configs (subject line + trigger_id each one's Gmail
# search / RemoteTrigger already expects). Not deploy-time config, so it
# lives here as a plain constant rather than in project_vars.txt/.env.
ROUTING_TABLE = {
    "uncharted_ice": {
        "subject": "attached image",
        "trigger_id": "trig_01KNnjdscJ1KpMTEKqneqs1S",
    },
    "keynote": {
        "subject": "Crossing the Ice Keynote demo notes",
        "trigger_id": "trig_01SJiDxNiKbNHHtBiUT2je93",
    },
    "interactive_keynote": {
        "subject": "interactive keynote",
        "trigger_id": "trig_01KSh5tdtUWA1BXND9eNgR4R",
    },
}


def require(*names: str) -> None:
    """Raise a clear error if any of the named config values are unset."""
    missing = [n for n in names if not globals().get(n)]
    if missing:
        raise RuntimeError(
            f"Missing required configuration: {', '.join(missing)}. "
            f"Set them in {BASE_DIR / '.env'} (see .env.example)."
        )
