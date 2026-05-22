"""
Pipeline Orchestrator
Coordinates: clone → parse → chunk → review → aggregate results.
Provides progress callbacks for Streamlit real-time updates.
"""

import os
from dataclasses import dataclass, field
from typing import Callable, Optional
from agent.ingestion import RepoIngestion
from agent.parser import ASTParser
from agent.reviewer import LLMReviewer, ReviewComment, ReviewResult


@dataclass
class PipelineResult:
    repo_url: str
    repo_metadata: dict
    file_results: list[ReviewResult]
    all_comments: list[ReviewComment]
    total_files_analyzed: int
    total_tokens_used: int
    errors: list[str] = field(default_factory=list)

    # Derived stats (populated post-run)
    by_severity: dict = field(default_factory=dict)
    by_category: dict = field(default_factory=dict)
    by_file: dict = field(default_factory=dict)
    high_confidence: list[ReviewComment] = field(default_factory=list)
    low_confidence: list[ReviewComment] = field(default_factory=list)

    def compute_stats(self):
        self.by_severity = {}
        self.by_category = {}
        self.by_file = {}
        self.high_confidence = []
        self.low_confidence = []

        for c in self.all_comments:
            self.by_severity[c.severity] = self.by_severity.get(c.severity, 0) + 1
            self.by_category[c.category] = self.by_category.get(c.category, 0) + 1
            self.by_file[c.file] = self.by_file.get(c.file, 0) + 1
            if c.low_confidence:
                self.low_confidence.append(c)
            else:
                self.high_confidence.append(c)


ProgressCallback = Callable[[str, int, int], None]  # (message, current, total)


class Pipeline:
    """
    Main pipeline: clone → parse → chunk → LLM review → aggregate.
    """

    MAX_FILES = 30        # Don't review more than this many files per run
    MAX_CHUNKS_PER_FILE = 20

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        progress_callback: Optional[ProgressCallback] = None,
    ):
        self.ingestion = RepoIngestion()
        self.parser = ASTParser()
        self.reviewer = LLMReviewer(api_key=api_key, model=model)
        self.progress = progress_callback or (lambda msg, cur, tot: None)

    def run(self, github_url: str) -> PipelineResult:
        """
        Full pipeline run. Returns a PipelineResult with all review data.
        """
        errors = []

        # 1. Clone
        self.progress("Cloning repository…", 0, 4)
        try:
            repo_path = self.ingestion.clone(github_url)
        except ValueError as e:
            raise RuntimeError(f"Clone failed: {e}")

        repo_metadata = self.ingestion.get_repo_metadata()

        # 2. Collect files
        self.progress("Collecting Python files…", 1, 4)
        files = self.ingestion.collect_files(repo_path)
        if not files:
            raise RuntimeError("No Python files found in this repository.")

        # Limit file count
        files = files[: self.MAX_FILES]

        # 3. Parse all files
        self.progress(f"Parsing {len(files)} files with AST…", 2, 4)
        all_chunks = []
        for f in files:
            parsed = self.parser.parse_file(f)
            chunks = self.parser.chunk_for_review(parsed)
            all_chunks.extend(chunks[: self.MAX_CHUNKS_PER_FILE])

        if not all_chunks:
            raise RuntimeError("No reviewable code chunks found.")

        # 4. LLM Review (per chunk, with progress)
        self.progress(f"Reviewing {len(all_chunks)} code chunks with AI…", 3, 4)
        file_results: dict[str, ReviewResult] = {}
        total_tokens = 0

        for i, chunk in enumerate(all_chunks):
            rel_path = chunk["relative_path"]
            self.progress(
                f"Reviewing {rel_path} — {chunk['name']} ({i+1}/{len(all_chunks)})",
                3,
                4,
            )
            if rel_path not in file_results:
                file_results[rel_path] = ReviewResult(relative_path=rel_path)

            try:
                comments, tokens = self.reviewer.review_chunk(chunk)
                file_results[rel_path].comments.extend(comments)
                file_results[rel_path].tokens_used += tokens
                total_tokens += tokens
            except Exception as e:
                err = f"Error reviewing {rel_path}/{chunk['name']}: {e}"
                errors.append(err)
                file_results[rel_path].error = err

        # 5. Aggregate
        self.progress("Aggregating results…", 4, 4)
        all_comments = []
        for fr in file_results.values():
            all_comments.extend(fr.comments)

        result = PipelineResult(
            repo_url=github_url,
            repo_metadata=repo_metadata,
            file_results=list(file_results.values()),
            all_comments=all_comments,
            total_files_analyzed=len(file_results),
            total_tokens_used=total_tokens,
            errors=errors,
        )
        result.compute_stats()

        # Cleanup cloned repo
        self.ingestion.cleanup()

        return result
