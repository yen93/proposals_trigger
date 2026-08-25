# Apps Script: fire proposal-router-hourly on Form submission

Wires the "Proposal Automation Trigger Form" so that submitting it fires the
`proposal-router-hourly` routine (`trig_01VUXJpHGMMEAABsEAVdWjJG`) within
seconds — no polling, no hourly-cron lag.

This can't be deployed from this repo/git: Apps Script projects live inside
Google's own UI, bound to the Form. `on_form_submit.gs` in this folder is
kept here for reference/version history only — you still have to paste it
into the Form's own Apps Script project by hand, once.

## One-time setup

1. Open the Form in Google Forms -> the three-dot menu -> **Script editor**
   (or: **Extensions -> Apps Script**).
2. Delete any placeholder code in the default script file and paste in the
   contents of `on_form_submit.gs`.
3. **Set the bearer token as a Script Property — never paste it into the
   script's source:**
   - Click the gear icon (**Project Settings**) in the left sidebar.
   - Scroll to **Script Properties** -> **Add script property**.
   - Property: `ROUTINE_FIRE_TOKEN`
   - Value: the bearer token for this routine's fire endpoint (get it from
     wherever it's currently stored — do not commit it anywhere, do not
     paste it into any file, only into this Properties field).
   - Save.
4. Add the installable trigger:
   - Click the clock icon (**Triggers**) in the left sidebar.
   - **Add Trigger**.
   - Function: `onFormSubmit`
   - Event source: **From form**
   - Event type: **On form submit**
   - Save, and grant the permissions Google asks for (this script needs to
     make an external HTTP request via `UrlFetchApp`).

## Verifying it works

1. Submit a real test response to the Form.
2. In the Apps Script editor, open **Executions** (the list icon) and
   confirm the latest `onFormSubmit` run logged
   `proposal-router-hourly fired successfully (HTTP 2xx)`.
3. Confirm a new run session actually started for the routine
   (`RemoteTrigger action=list_runs`, `trigger_id: trig_01VUXJpHGMMEAABsEAVdWjJG`)
   within seconds of the submission — not on the next hourly boundary.

## If the token needs rotating

The token is scoped to this one routine's fire endpoint. If it's ever
rotated, only step 3 above needs repeating (update the `ROUTINE_FIRE_TOKEN`
script property) — the committed `.gs` file doesn't change.

## If you're configuring the proposal-router-hourly routine itself

Never paste literal secret values (Google OAuth client secret/refresh
token, `ANTHROPIC_API_KEY`, `SUPABASE_SERVICE_KEY`, any `FIRE_TOKEN_*`) into
the routine's stored prompt/instructions on claude.ai. The routine's
execution environment should already have `.env` populated (or equivalent
secret injection) before the agent starts — the prompt should only need to
say "run `python main.py`," never "here are the values, write them to .env
first." Embedding real credentials in a stored prompt means every future
run re-exposes them in plaintext to whatever reads that prompt. (This
matters because two separate scheduled runs of this routine correctly
refused to execute after finding live secrets embedded in their own
prompt — see this repo's chat history around 2026-08-25.)
