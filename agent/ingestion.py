"""
Ingestion Module
Clones GitHub repositories and collects Python source files for analysis.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
import git
from git import Repo, InvalidGitRepositoryError


class RepoIngestion:
    """Handles cloning and file collection from GitHub repositories."""

    SUPPORTED_EXTENSIONS = {".py"}
    MAX_FILE_SIZE_KB = 500  # Skip files larger than this
    IGNORE_DIRS = {
        ".git", "__pycache__", ".venv", "venv", "env",
        "node_modules", ".tox", "dist", "build", "*.egg-info"
    }

    def __init__(self, clone_root: Optional[str] = None):
        self.clone_root = clone_root or tempfile.mkdtemp(prefix="code_reviewer_")
        self.repo_path: Optional[str] = None
        self.repo: Optional[Repo] = None

    def clone(self, github_url: str) -> str:
        """
        Clone the given GitHub URL into a temp directory.
        Returns the local path to the cloned repo.
        """
        # Sanitize URL
        github_url = github_url.strip().rstrip("/")
        if not github_url.endswith(".git"):
            github_url += ".git"

        repo_name = github_url.split("/")[-1].replace(".git", "")
        target_path = os.path.join(self.clone_root, repo_name)

        # Remove if already exists (re-run scenario)
        if os.path.exists(target_path):
            shutil.rmtree(target_path)

        try:
            self.repo = Repo.clone_from(github_url, target_path, depth=1)
            self.repo_path = target_path
            return target_path
        except git.exc.GitCommandError as e:
            raise ValueError(f"Failed to clone repository: {e}")

    def collect_files(self, repo_path: Optional[str] = None) -> list[dict]:
        """
        Walk the repo and collect all Python source files.
        Returns a list of dicts: {path, relative_path, content, size_kb}
        """
        root = Path(repo_path or self.repo_path)
        if not root.exists():
            raise FileNotFoundError(f"Repo path not found: {root}")

        collected = []
        for file_path in root.rglob("*"):
            # Skip ignored directories
            if any(part in self.IGNORE_DIRS for part in file_path.parts):
                continue
            if file_path.suffix not in self.SUPPORTED_EXTENSIONS:
                continue
            if not file_path.is_file():
                continue

            size_kb = file_path.stat().st_size / 1024
            if size_kb > self.MAX_FILE_SIZE_KB:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                if not content.strip():
                    continue
                collected.append({
                    "path": str(file_path),
                    "relative_path": str(file_path.relative_to(root)),
                    "content": content,
                    "size_kb": round(size_kb, 2),
                })
            except Exception:
                continue

        return collected

    def get_repo_metadata(self) -> dict:
        """Return basic metadata about the cloned repo."""
        if not self.repo:
            return {}
        try:
            commit = self.repo.head.commit
            return {
                "commit_sha": commit.hexsha[:8],
                "commit_message": commit.message.strip(),
                "author": str(commit.author),
                "committed_date": commit.committed_datetime.isoformat(),
                "branch": self.repo.active_branch.name,
            }
        except Exception:
            return {}

    def cleanup(self):
        """Remove the cloned repo from disk."""
        if self.repo_path and os.path.exists(self.repo_path):
            shutil.rmtree(self.repo_path, ignore_errors=True)
