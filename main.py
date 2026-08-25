"""Entrypoint — runs the router once. Intended to be invoked on demand (via
its webhook, see apps_script/) or on a schedule, so repeated runs are safe:
the Supabase dedup check skips any Form response already processed.

Fires each downstream pipeline itself, directly, via src/trigger_fire_service
— see pipeline.py's module docstring for why that's a plain HTTP call rather
than the RemoteTrigger Claude Code tool.
"""

from pipeline import run_once

if __name__ == "__main__":
    run_once()
