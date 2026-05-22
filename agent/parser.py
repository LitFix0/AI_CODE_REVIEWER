"""
AST Parser Module
Parses Python source files to extract structural information:
functions, classes, imports, and code chunks for LLM review.
"""

import ast
import textwrap
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FunctionInfo:
    name: str
    lineno: int
    end_lineno: int
    args: list[str]
    decorators: list[str]
    docstring: Optional[str]
    source: str
    is_method: bool = False
    complexity_hints: list[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    name: str
    lineno: int
    end_lineno: int
    bases: list[str]
    methods: list[str]
    docstring: Optional[str]
    source: str


@dataclass
class ParsedFile:
    relative_path: str
    imports: list[str]
    functions: list[FunctionInfo]
    classes: list[ClassInfo]
    top_level_code: str
    total_lines: int
    parse_error: Optional[str] = None


class ASTParser:
    """Parses Python files and extracts structural elements."""

    MAX_CHUNK_LINES = 80  # Max lines per LLM chunk

    def parse_file(self, file_info: dict) -> ParsedFile:
        """
        Parse a single file dict (from RepoIngestion.collect_files).
        Returns a ParsedFile with extracted structure.
        """
        path = file_info["relative_path"]
        content = file_info["content"]
        lines = content.splitlines()

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return ParsedFile(
                relative_path=path,
                imports=[],
                functions=[],
                classes=[],
                top_level_code=content[:500],
                total_lines=len(lines),
                parse_error=str(e),
            )

        imports = self._extract_imports(tree)
        functions = self._extract_functions(tree, lines)
        classes = self._extract_classes(tree, lines)
        top_level = self._extract_top_level(tree, lines)

        return ParsedFile(
            relative_path=path,
            imports=imports,
            functions=functions,
            classes=classes,
            top_level_code=top_level,
            total_lines=len(lines),
        )

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

    def _extract_functions(self, tree: ast.AST, lines: list[str]) -> list[FunctionInfo]:
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
                    decorators.append(f"{d.value.id}.{d.attr}" if isinstance(d.value, ast.Name) else d.attr)

            docstring = ast.get_docstring(node)
            end = getattr(node, "end_lineno", node.lineno + 10)
            source = "\n".join(lines[node.lineno - 1: end])
            source = textwrap.dedent(source)

            complexity_hints = self._get_complexity_hints(node)
            is_method = "self" in args or "cls" in args

            functions.append(FunctionInfo(
                name=node.name,
                lineno=node.lineno,
                end_lineno=end,
                args=args,
                decorators=decorators,
                docstring=docstring,
                source=source,
                is_method=is_method,
                complexity_hints=complexity_hints,
            ))
        return functions

    def _extract_classes(self, tree: ast.AST, lines: list[str]) -> list[ClassInfo]:
        classes = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = []
            for b in node.bases:
                if isinstance(b, ast.Name):
                    bases.append(b.id)
                elif isinstance(b, ast.Attribute):
                    bases.append(f"{b.attr}")

            methods = [
                n.name for n in ast.walk(node)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            docstring = ast.get_docstring(node)
            end = getattr(node, "end_lineno", node.lineno + 20)
            source = "\n".join(lines[node.lineno - 1: end])

            classes.append(ClassInfo(
                name=node.name,
                lineno=node.lineno,
                end_lineno=end,
                bases=bases,
                methods=methods,
                docstring=docstring,
                source=source,
            ))
        return classes

    def _extract_top_level(self, tree: ast.AST, lines: list[str]) -> str:
        """Extract top-level non-function, non-class code (module-level logic)."""
        top_lines = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            end = getattr(node, "end_lineno", node.lineno)
            top_lines.extend(lines[node.lineno - 1: end])
        return "\n".join(top_lines[:50])  # Cap at 50 lines

    def _get_complexity_hints(self, node: ast.AST) -> list[str]:
        hints = []
        for child in ast.walk(node):
            if isinstance(child, (ast.For, ast.While)):
                hints.append("loop")
            elif isinstance(child, ast.ExceptHandler):
                hints.append("exception_handling")
            elif isinstance(child, ast.comprehension):
                hints.append("comprehension")
            elif isinstance(child, ast.Lambda):
                hints.append("lambda")
            elif isinstance(child, ast.Global):
                hints.append("global_var")
        return list(set(hints))

    def chunk_for_review(self, parsed: ParsedFile, max_lines: int = None) -> list[dict]:
        """
        Break a ParsedFile into reviewable chunks.
        Each chunk is a dict: {type, name, source, lineno, relative_path}
        """
        max_lines = max_lines or self.MAX_CHUNK_LINES
        chunks = []

        # Individual functions
        for fn in parsed.functions:
            fn_lines = fn.source.splitlines()
            if len(fn_lines) <= max_lines:
                chunks.append({
                    "chunk_type": "function",
                    "name": fn.name,
                    "source": fn.source,
                    "lineno": fn.lineno,
                    "relative_path": parsed.relative_path,
                    "complexity_hints": fn.complexity_hints,
                    "is_method": fn.is_method,
                    "decorators": fn.decorators,
                    "args": fn.args,
                    "docstring": fn.docstring,
                })
            else:
                # Split oversized functions into sub-chunks
                for i in range(0, len(fn_lines), max_lines):
                    chunk_src = "\n".join(fn_lines[i: i + max_lines])
                    chunks.append({
                        "chunk_type": "function_chunk",
                        "name": f"{fn.name} (lines {fn.lineno + i}–{fn.lineno + i + max_lines})",
                        "source": chunk_src,
                        "lineno": fn.lineno + i,
                        "relative_path": parsed.relative_path,
                        "complexity_hints": fn.complexity_hints,
                        "is_method": fn.is_method,
                        "decorators": fn.decorators,
                        "args": fn.args,
                        "docstring": fn.docstring,
                    })

        # Class-level overview (without method bodies to avoid duplication)
        for cls in parsed.classes:
            cls_src = cls.source.splitlines()[:15]  # just the class header
            chunks.append({
                "chunk_type": "class",
                "name": cls.name,
                "source": "\n".join(cls_src),
                "lineno": cls.lineno,
                "relative_path": parsed.relative_path,
                "complexity_hints": [],
                "is_method": False,
                "decorators": [],
                "args": [],
                "docstring": cls.docstring,
            })

        # Top-level module code
        if parsed.top_level_code.strip():
            chunks.append({
                "chunk_type": "module",
                "name": f"module:{parsed.relative_path}",
                "source": parsed.top_level_code,
                "lineno": 1,
                "relative_path": parsed.relative_path,
                "complexity_hints": [],
                "is_method": False,
                "decorators": [],
                "args": [],
                "docstring": None,
            })

        return chunks