"""Classifies a demo-call notes photo/PDF as one of the 3 known proposal
types via Claude vision, by reading which format option is circled, checked,
or otherwise marked as selected on the sheet.

Only invoked as a fallback: pipeline.py skips this entirely when the
salesperson already picked a "Proposal Type" on the router Form.

UNVALIDATED: this has not yet been run against a real sample of the demo-notes
sheet's format-checkbox section for any of the 3 types. Test it against real
samples per type before trusting its output in production — misrouting sends
the wrong deck design to a real client. See config.ROUTING_TABLE for the
canonical type keys this must return.
"""

import base64

import anthropic

import config

MODEL = "claude-opus-5"

CLASSIFICATION_TOOL = {
    "name": "classify_proposal_type",
    "description": (
        "Identify which of the three demo-notes sheet format options is "
        "circled, checked, or otherwise marked as selected on this page."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "proposal_type": {
                "type": "string",
                "enum": ["uncharted_ice", "keynote", "interactive_keynote"],
                "description": "Which format option is marked as selected on the sheet",
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": (
                    "How clearly the marked option could be determined. Use "
                    "'low' rather than guessing when the mark is ambiguous, "
                    "multiple options appear marked, none appear marked, or "
                    "the page doesn't match the expected sheet format."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": "1-2 sentences citing the visual evidence (which option was marked, or why it's ambiguous/illegible)",
            },
        },
        "required": ["proposal_type", "confidence", "reasoning"],
    },
}


def classify(image_bytes: bytes, mime_type: str, additional_notes: str = "") -> dict:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    encoded = base64.standard_b64encode(image_bytes).decode("utf-8")
    block_type = "document" if mime_type == "application/pdf" else "image"

    notes_context = (
        f'\n\nThe salesperson also left this free-text note: "{additional_notes}" '
        "— use it as extra context if it clarifies which format was chosen."
        if additional_notes
        else ""
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[CLASSIFICATION_TOOL],
        tool_choice={"type": "tool", "name": "classify_proposal_type"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": block_type,
                        "source": {"type": "base64", "media_type": mime_type, "data": encoded},
                    },
                    {
                        "type": "text",
                        "text": (
                            "This is a sales demo-call notes sheet. Somewhere on the page "
                            "is a format section listing three proposal format options — "
                            "'Uncharted Ice', 'Keynote', and 'Interactive Keynote' (labels/"
                            "wording on the physical sheet may vary slightly) — with one "
                            "circled, ticked, or otherwise marked as the format chosen for "
                            "this client. Identify which one and return it via "
                            "classify_proposal_type." + notes_context
                        ),
                    },
                ],
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "classify_proposal_type":
            result = dict(block.input)
            if result.get("proposal_type") not in config.ROUTING_TABLE:
                raise RuntimeError(
                    f"classify_proposal_type returned an unknown proposal_type: {result.get('proposal_type')!r}"
                )
            return result
    raise RuntimeError("Claude did not return the expected classify_proposal_type tool call")
