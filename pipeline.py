"""Orchestrates the proposal router: for every new Form response, classify
which of the 3 existing proposal pipelines it belongs to, then hand it off
by forwarding the original attachment as an email carrying that pipeline's
expected subject line — the only way to feed it an attachment without
touching that pipeline's code, since all 3 only trigger from a Gmail search.

After forwarding, this also fires the downstream routine directly via
src/trigger_fire_service.py (a plain authenticated HTTP call, not the
RemoteTrigger Claude Code tool — a routine-run agent can only RemoteTrigger
triggers it created itself, not these pre-existing ones, so main.py does the
firing itself). That direct fire is a best-effort zero-lag optimization: if
it fails or a fire token isn't configured, the forwarded email still
guarantees the downstream routine's own hourly cron will pick it up.
"""

import logging

import config
from src import classifier_service, gmail_forwarder, router_form_service, supabase_service, trigger_fire_service
from src.google_clients import GoogleClients

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pipeline")


def _process_response(clients: GoogleClients, supabase, response: dict) -> None:
    response_id = response["response_id"]
    filename = response["filename"]
    additional_notes = response["additional_notes"]

    try:
        file_bytes = router_form_service.download_response_file(clients.drive, response["file_id"])
        classification = classifier_service.classify(file_bytes, response["mime_type"], additional_notes)
        confidence = classification["confidence"]
        proposal_type = classification["proposal_type"]

        if confidence == "low":
            notice = gmail_forwarder.build_manual_review_message(
                config.NOTIFICATION_RECIPIENTS, response_id, filename, classification, additional_notes
            )
            gmail_forwarder.send_manual_review_notice(clients.gmail, notice)
            supabase_service.mark_processed(
                supabase, response_id, status="needs_review",
                classified_type=proposal_type, confidence=confidence,
                reasoning=classification.get("reasoning"),
                filename=filename, additional_notes=additional_notes,
                error_message="Low-confidence classification — routed for manual review instead of auto-forwarding.",
            )
            log.info("Response %s: low confidence, sent for manual review", response_id)
            return

        routing = config.ROUTING_TABLE[proposal_type]
        forward = gmail_forwarder.build_forward_message(
            config.FORWARD_TO_ADDRESS, routing["subject"], file_bytes, filename,
            response["mime_type"], additional_notes, classification,
        )
        sent = gmail_forwarder.send_forward(clients.gmail, forward)

        supabase_service.mark_processed(
            supabase, response_id, status="success",
            classified_type=proposal_type, confidence=confidence,
            reasoning=classification.get("reasoning"),
            target_subject=routing["subject"], target_trigger_id=routing["trigger_id"],
            forwarded_message_id=sent["message_id"],
            filename=filename, additional_notes=additional_notes,
        )
        fired = trigger_fire_service.fire(
            routing["trigger_id"], config.fire_token_for(proposal_type),
            text=f"Fired by proposal-router-hourly after classifying a new submission as {proposal_type}.",
        )
        log.info(
            "Response %s: routed to %s (trigger %s)%s",
            response_id, proposal_type, routing["trigger_id"],
            " — fired immediately" if fired else " — not fired directly, relying on its own hourly cron",
        )

    except Exception as exc:
        log.exception("Failed to process response %s", response_id)
        supabase_service.mark_processed(supabase, response_id, status="error", error_message=str(exc))


def run_once() -> None:
    if not config.ROUTER_FORM_ID:
        log.info("ROUTER_FORM_ID not set — router form path disabled")
        return

    clients = GoogleClients()
    supabase = supabase_service.get_client()

    responses = router_form_service.list_new_responses(clients.forms)
    log.info("Found %d form response(s)", len(responses))

    for response in responses:
        if supabase_service.is_processed(supabase, response["response_id"]):
            continue
        _process_response(clients, supabase, response)
