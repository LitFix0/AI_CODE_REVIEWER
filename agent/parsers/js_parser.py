"""
JS/TS Parser
Regex-based structural extraction for JavaScript and TypeScript source files.
Extracts function, class, arrow function, method, interface, type alias, and
enum blocks — mirroring the structure of RustParser.
"""

import re
from agent.parsers.base import BaseParser, ParsedFile


class JSParser(BaseParser):

    LANGUAGE   = "javascript"
    EXTENSIONS = [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]

    # ── Item patterns ─────────────────────────────────────────────────────────
    # Each tuple: (compiled regex, kind string)
    # Group 1 → optional export/async/visibility prefix
    # Group 2 → item name
    ITEM_PATTERNS = [
        # export async function foo / export function foo / function foo
        (re.compile(r'^(export\s+(?:default\s+)?(?:async\s+)?)?function\s+(\w+)'),          "function"),
        # export default class Foo / export class Foo / class Foo
        (re.compile(r'^(export\s+(?:default\s+)?)?class\s+(\w+)'),                          "class"),
        # export const foo = async (...) => / export const foo = (...) =>
        (re.compile(r'^(export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\('),      "arrow_fn"),
        # TypeScript interface
        (re.compile(r'^(export\s+)?interface\s+(\w+)'),                                      "interface"),
        # TypeScript type alias  (type Foo = ...)
        (re.compile(r'^(export\s+)?type\s+(\w+)\s*(?:<[^>]*)?\s*='),                        "type_alias"),
        # TypeScript / JS enum
        (re.compile(r'^(export\s+)?(?:const\s+)?enum\s+(\w+)'),                             "enum"),
    ]

    # ES module import  (import ... from '...')
    IMPORT_PATTERN  = re.compile(r"^import\s+(.+?)\s+from\s+['\"]([^'\"]+)['\"]")
    # require()  (const x = require('...'))
    REQUIRE_PATTERN = re.compile(r"^(?:const|let|var)\s+\S+\s*=\s*require\(['\"]([^'\"]+)['\"]\)")
    # Decorator  (@decorator or @decorator(...))
    DECORATOR_PATTERN = re.compile(r'^@([\w.]+)(?:\([^)]*\))?')

    COMPLEXITY_PATTERNS = {
        "loop":          re.compile(r'\b(?:for|while|do)\b'),
        "async_await":   re.compile(r'\b(?:async|await)\b'),
        "promise":       re.compile(r'\bPromise\b|\.then\(|\.catch\('),
        "callback":      re.compile(r'\bcallback\b|\.forEach\(|\.map\(|\.filter\(|\.reduce\('),
        "try_catch":     re.compile(r'\btry\s*\{'),
        "type_cast":     re.compile(r'\bas\s+\w+|<\w+>'),          # TS casts
        "null_coalesce": re.compile(r'\?\?|\?\.'),
        "regex":         re.compile(r'/[^/\n]{2,}/[gimsuy]*'),
    }

    def parse_and_chunk(self, file_info: dict, max_lines: int = None) -> tuple[ParsedFile, list[dict]]:
        max_lines = max_lines or self.MAX_CHUNK_LINES
        path      = file_info["relative_path"]
        content   = file_info["content"]
        lines     = content.splitlines()

        # Detect TypeScript by extension
        language  = (
            "typescript"
            if path.endswith((".ts", ".tsx"))
            else self.LANGUAGE
        )

        imports = self._extract_imports(lines)
        items   = self._extract_items(lines)

        parsed = ParsedFile(
            relative_path=path, language=language,
            imports=imports, total_lines=len(lines),
        )

        chunks = self._build_chunks(items, path, max_lines)
        return parsed, chunks

    # ── Extraction ────────────────────────────────────────────────────────────

    def _extract_imports(self, lines: list[str]) -> list[str]:
        imports = []
        for line in lines:
            stripped = line.strip()
            m = self.IMPORT_PATTERN.match(stripped)
            if m:
                imports.append(m.group(2))   # module specifier
                continue
            m = self.REQUIRE_PATTERN.match(stripped)
            if m:
                imports.append(m.group(1))
        return imports

    def _extract_items(self, lines: list[str]) -> list[dict]:
        items            = []
        i                = 0
        pending_decorators = []

        while i < len(lines):
            stripped = lines[i].strip()

            # Collect decorators
            dec_m = self.DECORATOR_PATTERN.match(stripped)
            if dec_m:
                pending_decorators.append(dec_m.group(1))
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
                    "name":             matched_name,
                    "kind":             matched_kind,
                    "lineno":           i + 1,
                    "end_lineno":       end + 1,
                    "source":           source,
                    "visibility":       "export" if "export" in matched_vis else "private",
                    "decorators":       list(pending_decorators),
                    "complexity_hints": self._get_complexity_hints(source),
                })
                pending_decorators = []
                i = end + 1
            else:
                pending_decorators = []
                i += 1

        return items

    def _find_block_end(self, lines: list[str], start: int) -> int:
        """
        Brace-counting block-end finder.
        For arrow functions that end with a semicolon on the same line
        (e.g. `const foo = () => expr;`) we fall back to that line.
        """
        depth = 0
        found_open = False
        for i in range(start, len(lines)):
            line = lines[i]
            depth += line.count("{") - line.count("}")
            if line.count("{") > 0:
                found_open = True
            if found_open and depth <= 0 and i > start:
                return i
            # Single-line arrow without braces: `const foo = () => value;`
            if not found_open and "=>" in line and line.rstrip().endswith(";") and i >= start:
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
                "relative_path":    path,
                "complexity_hints": item["complexity_hints"],
                "decorators":       item["decorators"],
                "is_method":        item["kind"] == "arrow_fn" and item["visibility"] == "private",
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