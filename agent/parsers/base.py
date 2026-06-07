"""
Base Parser Interface
Every language parser must inherit from BaseParser and implement parse_and_chunk().
Adding a new language = create a new file inheriting this class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedFile:
    """Unified representation of any parsed source file."""
    relative_path: str
    language: str
    imports: list[str]
    total_lines: int
    items: list[dict] = field(default_factory=list)   # functions, classes, structs etc
    top_level_code: str = ""
    parse_error: Optional[str] = None


class BaseParser(ABC):
    """
    Abstract base class for all language parsers.
    Each language parser must implement parse_and_chunk().
    """

    MAX_CHUNK_LINES = 80
    LANGUAGE = "unknown"
    EXTENSIONS: list[str] = []

    @abstractmethod
    def parse_and_chunk(self, file_info: dict, max_lines: int = None) -> tuple[ParsedFile, list[dict]]:
        """
        Parse a file and return (ParsedFile, list of review chunks).
        Each chunk dict must contain:
            chunk_type, name, source, lineno, relative_path,
            complexity_hints, is_method, decorators, args, docstring, language
        """
        ...

    def _make_chunk(self, **kwargs) -> dict:
        """Helper to build a well-formed chunk dict with defaults."""
        defaults = {
            "chunk_type": "unknown",
            "name": "unknown",
            "source": "",
            "lineno": 1,
            "relative_path": "",
            "complexity_hints": [],
            "is_method": False,
            "decorators": [],
            "args": [],
            "docstring": None,
            "language": self.LANGUAGE,
        }
        return {**defaults, **kwargs}