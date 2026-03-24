from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from mcp import types
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
from starlette.middleware.cors import CORSMiddleware

# ── Widget ─────────────────────────────────────────────────────────────────────

WIDGET_URI        = "ui://widget/financial-review.html"
RESOURCE_MIME_TYPE = "text/html;profile=mcp-app"
WIDGET_HTML        = (Path(__file__).parent / "web" / "widget.html").read_text(encoding="utf-8")

# ── MCP Server ─────────────────────────────────────────────────────────────────

mcp = FastMCP("financial-review")


@mcp.resource(WIDGET_URI, mime_type=RESOURCE_MIME_TYPE)
async def financial_review_widget() -> str:
    """UI widget for Human-in-the-Loop review of financial statements."""
    return WIDGET_HTML


# ── Tool: propose_financial_review ─────────────────────────────────────────────

@mcp.tool(
    description=(
        "Present one or more financial statements to the user for Human-in-the-Loop review. "
        "The widget renders an editable, tabbed view of the statements inside M365 Copilot chat. "
        "The user inspects and optionally corrects values, then clicks Approve or Reject. "
        "IMPORTANT: After calling this tool, stop and do NOT proceed — wait for "
        "'submit_reviewed_statement' to be called by the user via the review widget."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def propose_financial_review(
    statements: list[dict],
    review_title: str = "Financial Statement Review",
    instructions: str = "",
) -> types.CallToolResult:
    """
    Args:
        statements:    List of financial statement objects following the canonical JSON schema
                       (statement_type, metadata, columns, rows, validation_warnings).
        review_title:  Heading displayed at the top of the review widget.
        instructions:  Optional reviewer guidance shown below the title.
    """
    structured_content = {
        "review_title": review_title,
        "instructions": instructions,
        "statements": statements,
        "status": "pending_review",
    }

    type_labels = {
        "balance_sheet":      "Balance Sheet",
        "income_statement":   "Income Statement",
        "cash_flow":          "Cash Flow",
    }
    names = [
        ((s.get("metadata") or {}).get("statement_title"))
        or type_labels.get(s.get("statement_type", ""), s.get("statement_type", "statement"))
        for s in statements
    ]

    total_warnings = sum(len(s.get("validation_warnings") or []) for s in statements)
    warning_note = (
        f" — {total_warnings} validation warning(s) flagged for attention" if total_warnings else ""
    )

    summary = (
        f"Presenting {len(statements)} financial statement(s) for review: "
        f"{', '.join(names)}.{warning_note} "
        f"Awaiting user approval before proceeding."
    )

    return types.CallToolResult(
        content=[TextContent(type="text", text=summary)],
        structuredContent=structured_content,
    )


# ── Tool: submit_reviewed_statement ────────────────────────────────────────────

@mcp.tool(
    description=(
        "Receives the outcome of a Human-in-the-Loop financial statement review. "
        "Called automatically by the review widget when the user clicks Approve or Reject. "
        "Contains the approval decision, field-level edits made by the reviewer, and a timestamp. "
        "Use this result to decide the next action: proceed on approval, or re-draft on rejection."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def submit_reviewed_statement(
    approved: bool,
    review_title: str,
    edits: list[dict],
    rejection_reason: str = "",
    reviewed_at: str = "",
) -> types.CallToolResult:
    """
    Args:
        approved:         True if the user approved, False if rejected.
        review_title:     Title of the review session that was completed.
        edits:            Field-level edits: [{statement_type, canonical_key, label,
                          col_label, row_index, col_index, original, edited}]
        rejection_reason: Reason for rejection (only populated when approved=False).
        reviewed_at:      ISO 8601 timestamp of review completion.
    """
    structured_content = {
        "approved":         approved,
        "review_title":     review_title,
        "edits":            edits,
        "edit_count":       len(edits),
        "rejection_reason": rejection_reason,
        "reviewed_at":      reviewed_at or datetime.now(timezone.utc).isoformat(),
    }

    if approved:
        if edits:
            top     = edits[:3]
            changes = "; ".join(
                f"{e['label']} [{e.get('col_label', '')}]: {e['original']} → {e['edited']}"
                for e in top
            )
            if len(edits) > 3:
                changes += f" … and {len(edits) - 3} more"
            summary = f"Review APPROVED with {len(edits)} edit(s). Changes: {changes}."
        else:
            summary = "Review APPROVED — no changes made."
    else:
        summary = f"Review REJECTED. Reason: {rejection_reason or 'No reason provided.'}"

    return types.CallToolResult(
        content=[TextContent(type="text", text=summary)],
        structuredContent=structured_content,
    )


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    app = mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    uvicorn.run(app, host="0.0.0.0", port=3001)


if __name__ == "__main__":
    main()
