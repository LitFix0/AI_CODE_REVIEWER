"""
Python Parser
Uses Python's built-in ast module for accurate structural extraction.
Extracts functions, classes, imports, and top-level code.
"""

import ast
import textwrap
from agent.parsers.base import BaseParser, ParsedFile


class PythonParser(BaseParser):

    LANGUAGE   = "python"
    EXTENSIONS = [".py"]

    def parse_and_chunk(self, file_info: dict, max_lines: int = None) -> tuple[ParsedFile, list[dict]]:
        max_lines = max_lines or self.MAX_CHUNK_LINES
        path    = file_info["relative_path"]
        content = file_info["content"]
        lines   = content.splitlines()

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            parsed = ParsedFile(
                relative_path=path, language=self.LANGUAGE,
                imports=[], total_lines=len(lines),
                top_level_code=content[:500], parse_error=str(e),
            )
            return parsed, []

        imports   = self._extract_imports(tree)
        functions = self._extract_functions(tree, lines)
        classes   = self._extract_classes(tree, lines)
        top_level = self._extract_top_level(tree, lines)

        parsed = ParsedFile(
            relative_path=path, language=self.LANGUAGE,
            imports=imports, total_lines=len(lines),
            top_level_code=top_level,
        )

        chunks = self._build_chunks(functions, classes, top_level, path, max_lines)
        return parsed, chunks

    # ── Extraction ────────────────────────────────────────────────────────────

    def _extract_imports(self, tree: ast.AST) -> list[str]:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        return imports

    def _extract_functions(self, tree: ast.AST, lines: list[str]) -> list[dict]:
        functions = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            args = [a.arg for a in node.args.args]
            decorators = []
            for d in node.decorator_list:
                if isinstance(d, ast.Name):
                    decorators.append(d.id)
                elif isinstance(d, ast.Attribute):
                    decorators.append(
                        f"{d.value.id}.{d.attr}" if isinstance(d.value, ast.Name) else d.attr
                    )
            end    = getattr(node, "end_lineno", node.lineno + 10)
            source = textwrap.dedent("\n".join(lines[node.lineno - 1: end]))
            functions.append({
                "name": node.name,
                "lineno": node.lineno,
                "end_lineno": end,
                "args": args,
                "decorators": decorators,
                "docstring": ast.get_docstring(node),
                "source": source,
                "is_method": "self" in args or "cls" in args,
                "complexity_hints": self._get_complexity_hints(node),
            })
        return functions

    def _extract_classes(self, tree: ast.AST, lines: list[str]) -> list[dict]:
        classes = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = []
            for b in node.bases:
                if isinstance(b, ast.Name): bases.append(b.id)
                elif isinstance(b, ast.Attribute): bases.append(b.attr)
            methods = [
                n.name for n in ast.walk(node)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            end = getattr(node, "end_lineno", node.lineno + 20)
            classes.append({
                "name": node.name,
                "lineno": node.lineno,
                "end_lineno": end,
                "bases": bases,
                "methods": methods,
                "docstring": ast.get_docstring(node),
                "source": "\n".join(lines[node.lineno - 1: end]),
            })
        return classes

    def _extract_top_level(self, tree: ast.AST, lines: list[str]) -> str:
        top_lines = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            end = getattr(node, "end_lineno", node.lineno)
            top_lines.extend(lines[node.lineno - 1: end])
        return "\n".join(top_lines[:50])

    def _get_complexity_hints(self, node: ast.AST) -> list[str]:
        hints = []
        for child in ast.walk(node):
            if isinstance(child, (ast.For, ast.While)):    hints.append("loop")
            elif isinstance(child, ast.ExceptHandler):     hints.append("exception_handling")
            elif isinstance(child, ast.comprehension):     hints.append("comprehension")
            elif isinstance(child, ast.Lambda):            hints.append("lambda")
            elif isinstance(child, ast.Global):            hints.append("global_var")
        return list(set(hints))

    # ── Chunking ──────────────────────────────────────────────────────────────

    def _build_chunks(self, functions, classes, top_level, path, max_lines) -> list[dict]:
        chunks = []

        for fn in functions:
            fn_lines = fn["source"].splitlines()
            base = {
                "relative_path": path,
                "complexity_hints": fn["complexity_hints"],
                "is_method": fn["is_method"],
                "decorators": fn["decorators"],
                "args": fn["args"],
                "docstring": fn["docstring"],
            }
            if len(fn_lines) <= max_lines:
                chunks.append(self._make_chunk(
                    **base, chunk_type="function",
                    name=fn["name"], source=fn["source"], lineno=fn["lineno"],
                ))
            else:
                for i in range(0, len(fn_lines), max_lines):
                    chunks.append(self._make_chunk(
                        **base, chunk_type="function_chunk",
                        name=f"{fn['name']} (lines {fn['lineno']+i}–{fn['lineno']+i+max_lines})",
                        source="\n".join(fn_lines[i: i + max_lines]),
                        lineno=fn["lineno"] + i,
                    ))

        for cls in classes:
            chunks.append(self._make_chunk(
                chunk_type="class", name=cls["name"],
                source="\n".join(cls["source"].splitlines()[:15]),
                lineno=cls["lineno"], relative_path=path,
                docstring=cls["docstring"],
            ))

        if top_level.strip():
            chunks.append(self._make_chunk(
                chunk_type="module", name=f"module:{path}",
                source=top_level, lineno=1, relative_path=path,
            ))

        return chunks