"""Forwards the original demo-notes attachment as a new email carrying the
subject line a downstream pipeline's Gmail trigger search already expects —
functionally identical to a salesperson emailing that pipeline directly, so
none of the 3 downstream pipelines' code needs to change.

Also sends a plain manual-review notice (no attachment) when the classifier's
confidence is too low to route automatically.
"""

import base64
import mimetypes
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from email.utils import make_msgid
from typing import Optional

import config


def _build_attachment_part(file_bytes: bytes, filename: str, mime_type: str):
    maintype, _, subtype = mime_type.partition("/")
    if maintype == "image":
        part = MIMEImage(file_bytes, _subtype=subtype or "jpeg")
    elif mime_type == "application/pdf":
        part = MIMEApplication(file_bytes, _subtype="pdf")
    else:
        part = MIMEBase(maintype or "application", subtype or "octet-stream")
        part.set_payload(file_bytes)
        encoders.encode_base64(part)

    if not filename:
        ext = mimetypes.guess_extension(mime_type) or ""
        filename = f"demo_notes{ext}"
    part.add_header("Content-Disposition", "attachment", filename=filename)
    return part


def build_forward_message(
    to_address: str,
    subject: str,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    additional_notes: str,
    classification: dict,
) -> MIMEMultipart:
    """subject is used VERBATIM as the full Subject header — the exact
    phrase (config.ROUTING_TABLE[type]["subject"]) the target pipeline's
    Gmail search query expects, i.e. what a salesperson would have typed by
    hand."""
    message = MIMEMultipart()
    message["To"] = to_address
    message["Subject"] = subject
    message["Message-ID"] = make_msgid()

    body_lines = [
        "Auto-routed by the proposal router.",
        "",
        f"Classified as: {classification.get('proposal_type')} "
        f"(confidence: {classification.get('confidence')})",
        f"Reasoning: {classification.get('reasoning')}",
    ]
    if additional_notes:
        body_lines += ["", "Additional notes from submitter:", additional_notes]
    message.attach(MIMEText("\n".join(body_lines)))
    message.attach(_build_attachment_part(file_bytes, filename, mime_type))
    return message


def build_manual_review_message(
    to_addresses: list[str],
    response_id: str,
    filename: str,
    classification: dict,
    additional_notes: str,
) -> MIMEText:
    body_lines = [
        "A demo-notes submission could not be confidently routed automatically.",
        "",
        f"Guessed type: {classification.get('proposal_type')}",
        f"Confidence: {classification.get('confidence')}",
        f"Reasoning: {classification.get('reasoning')}",
        "",
        f"Please review Form response {response_id} ({filename or 'no filename'}) "
        "and forward it to the correct pipeline manually.",
    ]
    if additional_notes:
        body_lines += ["", "Additional notes from submitter:", additional_notes]

    message = MIMEText("\n".join(body_lines))
    message["To"] = ", ".join(to_addresses)
    message["Subject"] = "Action needed: demo notes could not be auto-routed"
    message["Message-ID"] = make_msgid()
    return message


def _send(gmail, mime_message) -> dict:
    raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")
    sent = gmail.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"message_id": sent["id"], "thread_id": sent["threadId"]}


def send_forward(gmail, mime_message) -> dict:
    return _send(gmail, mime_message)


def send_manual_review_notice(gmail, mime_message) -> dict:
    return _send(gmail, mime_message)
