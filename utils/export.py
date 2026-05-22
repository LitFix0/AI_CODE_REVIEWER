"""
Export Utilities
Generate Markdown reports and CSV exports from pipeline results.
"""

import csv
import io
from datetime import datetime
from agent.pipeline import PipelineResult
from agent.reviewer import ReviewComment


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "info": "⚪",
}


def to_markdown(result: PipelineResult) -> str:
    """Generate a full Markdown report from a PipelineResult."""
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    meta = result.repo_metadata

    lines += [
        f"# AI Code Review Report",
        f"",
        f"**Repository:** `{result.repo_url}`  ",
        f"**Generated:** {ts}  ",
        f"**Files analyzed:** {result.total_files_analyzed}  ",
        f"**Total comments:** {len(result.all_comments)}  ",
        f"**Tokens used:** {result.total_tokens_used:,}  ",
        f"",
    ]

    if meta:
        lines += [
            f"## Repository Info",
            f"",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| Commit | `{meta.get('commit_sha', 'N/A')}` |",
            f"| Author | {meta.get('author', 'N/A')} |",
            f"| Branch | `{meta.get('branch', 'N/A')}` |",
            f"| Message | {meta.get('commit_message', 'N/A')[:80]} |",
            f"",
        ]

    # Summary table
    lines += ["## Summary", ""]
    lines += ["### By Severity", ""]
    lines += ["| Severity | Count |", "|----------|-------|"]
    for sev in ["critical", "high", "medium", "low", "info"]:
        count = result.by_severity.get(sev, 0)
        if count:
            lines.append(f"| {SEVERITY_EMOJI[sev]} {sev.title()} | {count} |")
    lines.append("")

    lines += ["### By Category", ""]
    lines += ["| Category | Count |", "|----------|-------|"]
    for cat, count in sorted(result.by_category.items(), key=lambda x: -x[1]):
        lines.append(f"| {cat.title()} | {count} |")
    lines.append("")

    # High confidence issues
    high_conf = sorted(
        result.high_confidence,
        key=lambda c: SEVERITY_ORDER.get(c.severity, 99)
    )
    if high_conf:
        lines += ["## High-Confidence Issues", ""]
        for c in high_conf:
            lines += _comment_section(c)

    # Low confidence issues
    if result.low_confidence:
        lines += [
            "---",
            "",
            "## ⚠️ Low-Confidence Issues — Verify These",
            "",
            "> These comments are speculative. Review manually before acting on them.",
            "",
        ]
        for c in result.low_confidence:
            lines += _comment_section(c, low_conf=True)

    # Errors
    if result.errors:
        lines += ["---", "", "## Pipeline Errors", ""]
        for err in result.errors:
            lines.append(f"- `{err}`")
        lines.append("")

    return "\n".join(lines)


def _comment_section(c: ReviewComment, low_conf: bool = False) -> list[str]:
    badge = "⚠️ VERIFY" if low_conf else ""
    emoji = SEVERITY_EMOJI.get(c.severity, "")
    lines = [
        f"### {emoji} [{c.severity.upper()}] {c.title} {badge}",
        f"",
        f"**File:** `{c.file}` · **Line:** {c.line} · **Category:** {c.category.title()}  ",
        f"**Confidence:** {c.confidence}%",
        f"",
        f"**Issue:** {c.description}",
        f"",
        f"**Suggestion:** {c.suggestion}",
        f"",
        f"---",
        f"",
    ]
    return lines


def to_csv(result: PipelineResult) -> str:
    """Generate a CSV export of all review comments."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "file", "line", "chunk_name", "chunk_type",
        "category", "severity", "title",
        "description", "suggestion", "confidence", "low_confidence"
    ])
    writer.writeheader()
    for c in result.all_comments:
        writer.writerow(c.to_dict())
    return output.getvalue()
