"""
Parsers package.
To add a new language:
  1. Create agent/parsers/your_language_parser.py inheriting BaseParser
  2. Add its extension mapping to PARSER_REGISTRY below — nothing else changes.
"""

from agent.parsers.base import BaseParser, ParsedFile
from agent.parsers.python_parser import PythonParser
from agent.parsers.rust_parser import RustParser

# ── Registry — add new languages here only ────────────────────────────────────
PARSER_REGISTRY: dict[str, BaseParser] = {}

for _parser in [PythonParser(), RustParser()]:
    for _ext in _parser.EXTENSIONS:
        PARSER_REGISTRY[_ext] = _parser

__all__ = ["BaseParser", "ParsedFile", "PARSER_REGISTRY"]