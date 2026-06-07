"""
Parser Dispatcher
Routes each file to the correct language parser via PARSER_REGISTRY.

To add a new language:
  1. Create agent/parsers/<lang>_parser.py  (inherit BaseParser)
  2. Register its extension in agent/parsers/__init__.py
  
That's it — nothing in this file ever needs to change.
"""

from pathlib import Path
from agent.parsers import PARSER_REGISTRY, ParsedFile


class ASTParser:
    """
    Thin dispatcher — looks up the right parser by file extension
    and delegates all work to it.
    """

    def parse_and_chunk(self, file_info: dict, max_lines: int = None) -> tuple[ParsedFile, list[dict]]:
        ext    = Path(file_info["relative_path"]).suffix.lower()
        parser = PARSER_REGISTRY.get(ext)

        if parser is None:
            # Unsupported extension — return empty result gracefully
            return ParsedFile(
                relative_path=file_info["relative_path"],
                language="unknown",
                imports=[],
                total_lines=len(file_info["content"].splitlines()),
                parse_error=f"No parser registered for extension '{ext}'",
            ), []

        return parser.parse_and_chunk(file_info, max_lines)

    @staticmethod
    def supported_extensions() -> list[str]:
        return list(PARSER_REGISTRY.keys())