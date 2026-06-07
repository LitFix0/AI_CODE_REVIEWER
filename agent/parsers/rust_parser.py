"""
Rust Parser
Regex-based structural extraction for Rust source files.
Extracts fn, struct, enum, impl, trait, mod blocks.
"""

import re
from agent.parsers.base import BaseParser, ParsedFile


class RustParser(BaseParser):

    LANGUAGE   = "rust"
    EXTENSIONS = [".rs"]

    ITEM_PATTERNS = [
        (re.compile(r'^(pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+(\w+)'),  "fn"),
        (re.compile(r'^(pub(?:\([^)]*\))?\s+)?struct\s+(\w+)'),            "struct"),
        (re.compile(r'^(pub(?:\([^)]*\))?\s+)?enum\s+(\w+)'),              "enum"),
        (re.compile(r'^(pub(?:\([^)]*\))?\s+)?impl(?:<[^>]*)?\s+(\w+)'),   "impl"),
        (re.compile(r'^(pub(?:\([^)]*\))?\s+)?trait\s+(\w+)'),             "trait"),
        (re.compile(r'^(pub(?:\([^)]*\))?\s+)?mod\s+(\w+)'),               "mod"),
    ]

    USE_PATTERN  = re.compile(r'^use\s+([\w::{}, *]+);')
    ATTR_PATTERN = re.compile(r'^#\[([^\]]+)\]')

    COMPLEXITY_PATTERNS = {
        "loop":           re.compile(r'\b(?:for|while|loop)\b'),
        "unsafe":         re.compile(r'\bunsafe\b'),
        "unwrap":         re.compile(r'\.unwrap\(\)'),
        "panic":          re.compile(r'\bpanic!\b'),
        "clone":          re.compile(r'\.clone\(\)'),
        "match":          re.compile(r'\bmatch\b'),
        "error_handling": re.compile(r'\?|\.expect\('),
    }

    def parse_and_chunk(self, file_info: dict, max_lines: int = None) -> tuple[ParsedFile, list[dict]]:
        max_lines = max_lines or self.MAX_CHUNK_LINES
        path    = file_info["relative_path"]
        content = file_info["content"]
        lines   = content.splitlines()

        uses  = self._extract_uses(lines)
        items = self._extract_items(lines)

        parsed = ParsedFile(
            relative_path=path, language=self.LANGUAGE,
            imports=uses, total_lines=len(lines),
        )

        chunks = self._build_chunks(items, path, max_lines)
        return parsed, chunks

    # ── Extraction ────────────────────────────────────────────────────────────

    def _extract_uses(self, lines: list[str]) -> list[str]:
        uses = []
        for line in lines:
            m = self.USE_PATTERN.match(line.strip())
            if m:
                uses.append(m.group(1))
        return uses

    def _extract_items(self, lines: list[str]) -> list[dict]:
        items = []
        i = 0
        pending_attrs = []

        while i < len(lines):
            stripped = lines[i].strip()

            attr_m = self.ATTR_PATTERN.match(stripped)
            if attr_m:
                pending_attrs.append(attr_m.group(1))
                i += 1
                continue

            matched_kind = None
            matched_name = None
            matched_vis  = ""

            for pattern, kind in self.ITEM_PATTERNS:
                m = pattern.match(stripped)
                if m:
                    matched_kind = kind
                    matched_vis  = (m.group(1) or "").strip()
                    matched_name = m.group(2)
                    break

            if matched_kind and matched_name:
                end    = self._find_block_end(lines, i)
                source = "\n".join(lines[i: end + 1])
                items.append({
                    "name":       matched_name,
                    "kind":       matched_kind,
                    "lineno":     i + 1,
                    "end_lineno": end + 1,
                    "source":     source,
                    "visibility": matched_vis or "private",
                    "attributes": list(pending_attrs),
                    "complexity_hints": self._get_complexity_hints(source),
                })
                pending_attrs = []
                i = end + 1
            else:
                pending_attrs = []
                i += 1

        return items

    def _find_block_end(self, lines: list[str], start: int) -> int:
        depth = 0
        for i in range(start, len(lines)):
            depth += lines[i].count("{") - lines[i].count("}")
            if depth <= 0 and i > start:
                return i
        return min(start + 5, len(lines) - 1)

    def _get_complexity_hints(self, source: str) -> list[str]:
        return [hint for hint, pat in self.COMPLEXITY_PATTERNS.items() if pat.search(source)]

    # ── Chunking ──────────────────────────────────────────────────────────────

    def _build_chunks(self, items: list[dict], path: str, max_lines: int) -> list[dict]:
        chunks = []
        for item in items:
            src_lines = item["source"].splitlines()
            base = {
                "relative_path":   path,
                "complexity_hints": item["complexity_hints"],
                "decorators":      item["attributes"],
                "is_method":       item["kind"] == "fn" and item["visibility"] == "private",
            }
            if len(src_lines) <= max_lines:
                chunks.append(self._make_chunk(
                    **base, chunk_type=item["kind"],
                    name=item["name"], source=item["source"], lineno=item["lineno"],
                ))
            else:
                for j in range(0, len(src_lines), max_lines):
                    chunks.append(self._make_chunk(
                        **base, chunk_type=f"{item['kind']}_chunk",
                        name=f"{item['name']} (lines {item['lineno']+j}–{item['lineno']+j+max_lines})",
                        source="\n".join(src_lines[j: j + max_lines]),
                        lineno=item["lineno"] + j,
                    ))
        return chunks