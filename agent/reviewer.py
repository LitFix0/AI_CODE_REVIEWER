"""
LLM Reviewer Module
Sends code chunks to an LLM and parses back structured review comments
with severity, category, and confidence scores.
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional, Literal
from groq import Groq

# --- Data models ---

Category = Literal[
    "bug", "security", "performance", "style",
    "maintainability", "documentation", "logic", "other"
]
Severity = Literal["critical", "high", "medium", "low", "info"]


@dataclass
class ReviewComment:
    file: str
    line: int
    chunk_name: str
    chunk_type: str
    category: Category
    severity: Severity
    title: str
    description: str
    suggestion: str
    confidence: int          # 0–100
    low_confidence: bool = False  # True if confidence < 60

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "chunk_name": self.chunk_name,
            "chunk_type": self.chunk_type,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "low_confidence": self.low_confidence,
        }


@dataclass
class ReviewResult:
    relative_path: str
    comments: list[ReviewComment] = field(default_factory=list)
    error: Optional[str] = None
    tokens_used: int = 0


# --- Prompt templates ---

SYSTEM_PROMPT = """You are a senior software engineer performing a thorough code review.
Your job is to identify real, actionable issues in the code — not superficial style nits.

You MUST respond with ONLY valid JSON. No markdown, no explanation, no preamble.

For each issue found, output this JSON schema:
{
  "comments": [
    {
      "category": "<bug|security|performance|style|maintainability|documentation|logic|other>",
      "severity": "<critical|high|medium|low|info>",
      "title": "<short issue title, max 80 chars>",
      "description": "<clear explanation of the problem, 1-3 sentences>",
      "suggestion": "<concrete fix or improvement, 1-3 sentences>",
      "confidence": <integer 0-100>
    }
  ]
}

Confidence scoring rules:
- 90-100: You are certain this is an issue. Evidence is clear in the code.
- 70-89: Likely an issue but depends on context you may not have.
- 50-69: Possible issue; uncertain without seeing the full codebase.
- Below 50: Speculative — flag it but mark it low confidence.

If the code is clean and you find no issues, return: {"comments": []}

Focus on:
1. Actual bugs (null refs, off-by-one, unhandled exceptions, race conditions)
2. Security vulnerabilities (injection, hardcoded secrets, unsafe deserialization)
3. Performance issues (N+1 queries, unnecessary copies, blocking I/O)
4. Logic errors (wrong conditions, missing edge cases)
5. Maintainability (deeply nested code, god functions, unclear naming)
Do NOT flag minor style issues unless they significantly hurt readability.
"""


def build_user_prompt(chunk: dict) -> str:
    meta = []
    if chunk.get("decorators"):
        meta.append(f"Decorators: {', '.join(chunk['decorators'])}")
    if chunk.get("args"):
        meta.append(f"Arguments: {', '.join(chunk['args'])}")
    if chunk.get("complexity_hints"):
        meta.append(f"Contains: {', '.join(chunk['complexity_hints'])}")
    if chunk.get("docstring"):
        meta.append(f"Docstring: {chunk['docstring'][:120]}")

    meta_str = "\n".join(meta)
    return f"""File: {chunk['relative_path']}
{chunk['chunk_type'].upper()}: {chunk['name']} (line {chunk['lineno']})
{meta_str}

```python
{chunk['source']}
```

Review this code and return ONLY the JSON response."""


# --- Reviewer class ---

class LLMReviewer:
    """Sends code chunks to Groq and parses structured review comments."""

    LOW_CONFIDENCE_THRESHOLD = 60
    MAX_RETRIES = 2
    RETRY_DELAY = 2

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))
        self.model = model

    def review_chunk(self, chunk: dict) -> tuple[list[ReviewComment], int]:
        """
        Review a single code chunk.
        Returns (list of ReviewComment, tokens_used).
        """
        prompt = build_user_prompt(chunk)

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=1500,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content.strip()
                tokens = response.usage.prompt_tokens + response.usage.completion_tokens
                comments = self._parse_response(raw, chunk)
                return comments, tokens

            except json.JSONDecodeError:
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY)
                    continue
                return [], 0
            except Exception as e:
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY)
                    continue
                raise e

        return [], 0

    def review_file(self, chunks: list[dict], relative_path: str) -> ReviewResult:
        """Review all chunks from one file."""
        result = ReviewResult(relative_path=relative_path)
        for chunk in chunks:
            if chunk["relative_path"] != relative_path:
                continue
            try:
                comments, tokens = self.review_chunk(chunk)
                result.comments.extend(comments)
                result.tokens_used += tokens
            except Exception as e:
                result.error = str(e)
        return result

    def _parse_response(self, raw: str, chunk: dict) -> list[ReviewComment]:
        """Parse the JSON response from the LLM into ReviewComment objects."""
        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = "\n".join(raw.splitlines()[1:])
        if raw.endswith("```"):
            raw = "\n".join(raw.splitlines()[:-1])
        raw = raw.strip()

        data = json.loads(raw)
        comments_data = data.get("comments", [])

        comments = []
        for c in comments_data:
            confidence = int(c.get("confidence", 50))
            confidence = max(0, min(100, confidence))
            comments.append(ReviewComment(
                file=chunk["relative_path"],
                line=chunk["lineno"],
                chunk_name=chunk["name"],
                chunk_type=chunk["chunk_type"],
                category=c.get("category", "other"),
                severity=c.get("severity", "info"),
                title=c.get("title", "")[:80],
                description=c.get("description", ""),
                suggestion=c.get("suggestion", ""),
                confidence=confidence,
                low_confidence=confidence < self.LOW_CONFIDENCE_THRESHOLD,
            ))
        return comments