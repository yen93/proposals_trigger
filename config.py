"""Loads environment variables and project_vars.txt constants for the router.

Every secret below must arrive via a pre-existing .env / environment —
never via prompt text. Anything (a routine, a script) that invokes main.py
must ensure .env already exists in the working directory beforehand; it
must never reconstruct .env from literal values embedded in its own
instructions, since that means those live secrets sit in plaintext
wherever that prompt is stored. See apps_script/README.md's "If you're
configuring the proposal-router-hourly routine itself" section.
"""

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

# Deliberately NOT read from "ANTHROPIC_API_KEY": on claude.ai cloud
# environments that exact name is reserved for the Claude Code session's own
# account-based authentication and is silently never injected into the
# process environment for user code to read (confirmed empirically —
# os.environ.get("ANTHROPIC_API_KEY") returns "" even after it's saved in
# the environment's variable UI). classifier_service.py's own direct
# Anthropic SDK calls need their own separately-named key instead.
ANTHROPIC_API_KEY = os.environ.get("CLASSIFIER_ANTHROPIC_API_KEY", "")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

SUPABASE_LOG_TABLE = "proposal_router_logs"

# Must match the exact scope set actually granted to GOOGLE_REFRESH_TOKEN at
# consent time — Google's refresh grant rejects a requested scope list that
# doesn't match what was originally consented (invalid_scope), even if this
# repo only ever calls a subset of these APIs. Only send/read scopes are
# actually used (gmail.send, drive, forms.responses.readonly);
# gmail.modify/presentations are unused here but must stay listed for the
# refresh to succeed against whichever token is configured.
#
# IMPORTANT, verified 2026-08-25: this is NOT interchangeable with the
# refresh token baked into the other 3 sibling routines' deployed job_configs
# (sales-proposals-automation-hourly, crossing-the-ice-keynote-automation-hourly,
# interactive-keynote-proposals-automation-hourly) — that token lacks
# forms.responses.readonly (confirmed by calling Google's oauth2/token
# endpoint directly and comparing the returned `scope` field for each token;
# do not assume otherwise from older comments/commit messages in this repo's
# history, which incorrectly assumed a single fully-shared token before this
# was checked). This repo's .env must use a token that was actually consented
# with forms.responses.readonly (e.g. the one already present in
# sales_proposals_automation's local .env on disk, or a fresh one minted via
# oauth_setup.py) — using the older shared token here will fail with
# invalid_scope at the credential-refresh step.
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/presentations",
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
        "fire_token_env": "FIRE_TOKEN_UNCHARTED_ICE",
    },
    "keynote": {
        "subject": "Crossing the Ice Keynote demo notes",
        "trigger_id": "trig_01SJiDxNiKbNHHtBiUT2je93",
        "fire_token_env": "FIRE_TOKEN_KEYNOTE",
    },
    "interactive_keynote": {
        "subject": "interactive keynote",
        "trigger_id": "trig_01KSh5tdtUWA1BXND9eNgR4R",
        "fire_token_env": "FIRE_TOKEN_INTERACTIVE_KEYNOTE",
    },
}

# Maps the router Form's "Proposal Type" radio option labels (verbatim, as
# they appear on the Form) to ROUTING_TABLE's canonical type keys. Lets a
# salesperson's manual Form selection override AI classification.
PROPOSAL_TYPE_FORM_LABELS = {
    "Uncharted Ice": "uncharted_ice",
    "Keynote": "keynote",
    "Interactive Keynote": "interactive_keynote",
}


def fire_token_for(proposal_type: str) -> str:
    """Bearer token for directly firing ROUTING_TABLE[proposal_type]'s routine
    via its bound-session HTTP fire endpoint (src/trigger_fire_service.py) --
    NOT one of the Anthropic/Google/Supabase keys above. Each downstream
    routine's fire endpoint requires its own token, minted via the claude.ai
    UI -- a routine-run agent can only call the RemoteTrigger tool against
    triggers it created itself, not these pre-existing http_api-created ones,
    so this direct-HTTP path is the only way to fire them with no lag and no
    human/agent babysitting (see src/trigger_fire_service.py's docstring).
    Returns "" if unset; callers must treat that as "skip the direct fire,
    rely on the downstream routine's own hourly cron instead" rather than
    raising."""
    env_name = ROUTING_TABLE[proposal_type]["fire_token_env"]
    return os.environ.get(env_name, "")


def require(*names: str) -> None:
    """Raise a clear error if any of the named config values are unset."""
    missing = [n for n in names if not globals().get(n)]
    if missing:
        raise RuntimeError(
            f"Missing required configuration: {', '.join(missing)}. "
            f"Set them in {BASE_DIR / '.env'} (see .env.example)."
        )
