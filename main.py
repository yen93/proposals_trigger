"""Entrypoint — runs the router once. Intended to be invoked on a schedule
(e.g. hourly via the routine's cron) so repeated runs are safe: the Supabase
dedup check skips any Form response already processed.

Deliberately does not call RemoteTrigger itself — see pipeline.py's module
docstring. After this exits, the routine's own job_config prompt reads the
`trigger_ids_to_fire: ...` stdout line (if printed) and fires each one.
"""

from pipeline import run_once

if __name__ == "__main__":
    run_once()
