from agent.parsers.base import BaseParser, ParsedFile
from agent.parsers.python_parser import PythonParser
from agent.parsers.rust_parser import RustParser
from agent.parsers.js_parser import JSParser          # ← add this

# ── Registry — add new languages here only ────────────────────────────────────
PARSER_REGISTRY: dict[str, BaseParser] = {}

for _parser in [PythonParser(), RustParser(), JSParser()]:   # ← add JSParser()
    for _ext in _parser.EXTENSIONS:
        PARSER_REGISTRY[_ext] = _parser

__all__ = ["BaseParser", "ParsedFile", "PARSER_REGISTRY"]