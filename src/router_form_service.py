"""Reads submissions from the "Demo Notes Router Intake" Google Form via the
Forms API — a 3-item form: file upload, optional free-text notes, and an
optional "Proposal Type" radio field. When the salesperson picks a Proposal
Type on the Form, pipeline.py uses it as-is and skips AI classification
entirely; left blank, the type is inferred by src/classifier_service.py as
before.

The Form must have items with these EXACT titles (case-sensitive) for the
field mapping below to find them.
"""

import config

FILE_UPLOAD_ITEM_TITLE = "Demo call notes"
NOTES_ITEM_TITLE = "Additional notes"
PROPOSAL_TYPE_ITEM_TITLE = "Proposal Type"


def _build_question_id_map(forms_client) -> dict:
    """Maps each expected item title -> its questionId, by inspecting the
    form's structure once. Titles not found on the form are silently
    omitted (that field just won't be read)."""
    form = forms_client.forms().get(formId=config.ROUTER_FORM_ID).execute()
    title_to_question_id = {}
    for item in form.get("items", []):
        title = item.get("title", "")
        question_item = item.get("questionItem", {})
        question_id = question_item.get("question", {}).get("questionId")
        if question_id:
            title_to_question_id[title] = question_id
    return title_to_question_id


def list_new_responses(forms_client) -> list[dict]:
    """Returns [{response_id, file_id, filename, mime_type, additional_notes,
    manual_proposal_type}, ...] for every response that has a file-upload
    answer. manual_proposal_type is "" when the salesperson left the
    "Proposal Type" field blank (or picked something not in
    config.PROPOSAL_TYPE_FORM_LABELS), signaling pipeline.py to fall back to
    AI classification. Callers are responsible
    for the Supabase dedup check — this always lists ALL responses on the
    form (fine at this form's expected volume; Forms API supports a
    timestamp filter if that stops being true).

    Returns [] immediately if config.ROUTER_FORM_ID is unset (the router's
    Form-reading path is disabled until the real form exists).
    """
    if not config.ROUTER_FORM_ID:
        return []

    title_to_question_id = _build_question_id_map(forms_client)
    file_question_id = title_to_question_id.get(FILE_UPLOAD_ITEM_TITLE)
    if not file_question_id:
        raise RuntimeError(
            f'Router form has no item titled "{FILE_UPLOAD_ITEM_TITLE}" — '
            "check the form matches src/router_form_service.py's expected titles."
        )
    notes_question_id = title_to_question_id.get(NOTES_ITEM_TITLE)
    proposal_type_question_id = title_to_question_id.get(PROPOSAL_TYPE_ITEM_TITLE)

    results = []
    page_token = None
    while True:
        resp = (
            forms_client.forms()
            .responses()
            .list(formId=config.ROUTER_FORM_ID, pageToken=page_token)
            .execute()
        )
        for response in resp.get("responses", []):
            answers = response.get("answers", {})
            file_answer = answers.get(file_question_id, {}).get("fileUploadAnswers", {})
            files = file_answer.get("answers", [])
            if not files:
                continue  # required question, but be defensive about drafts/partial responses

            first_file = files[0]
            additional_notes = ""
            if notes_question_id:
                text_answers = answers.get(notes_question_id, {}).get("textAnswers", {}).get("answers", [])
                additional_notes = text_answers[0]["value"] if text_answers else ""

            manual_proposal_type = ""
            if proposal_type_question_id:
                text_answers = answers.get(proposal_type_question_id, {}).get("textAnswers", {}).get("answers", [])
                if text_answers:
                    manual_proposal_type = config.PROPOSAL_TYPE_FORM_LABELS.get(text_answers[0]["value"], "")

            results.append(
                {
                    "response_id": response["responseId"],
                    "file_id": first_file["fileId"],
                    "filename": first_file.get("fileName", ""),
                    "mime_type": first_file.get("mimeType", "application/octet-stream"),
                    "additional_notes": additional_notes,
                    "manual_proposal_type": manual_proposal_type,
                }
            )

        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return results


def download_response_file(drive, file_id: str) -> bytes:
    return drive.files().get_media(fileId=file_id).execute()
