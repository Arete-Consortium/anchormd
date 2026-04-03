"""OPSEC analyzer — detects operational security leaks in public repos."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field

from anchormd.config import LANGUAGE_EXTENSIONS
from anchormd.models import AnalysisResult, ForgeConfig, ProjectStructure

logger = logging.getLogger(__name__)

_MAX_SAMPLE_FILES = 150

# --- Severity weights (same scale as tech_debt) ---
_SEVERITY_WEIGHTS = {
    "critical": 10,
    "high": 5,
    "medium": 2,
    "low": 1,
}

# --- File extensions to scan (superset of code — includes docs, config) ---
_SCANNABLE_EXTENSIONS = {
    *LANGUAGE_EXTENSIONS.keys(),
    ".md",
    ".txt",
    ".rst",
    ".toml",
    ".yml",
    ".yaml",
    ".json",
    ".cfg",
    ".ini",
    ".sh",
    ".bash",
    ".zsh",
    ".env",
    ".example",
    ".sample",
    ".dockerfile",
    ".pem",
    ".key",
    ".crt",
    ".cer",
}


@dataclass
class OpsecFinding:
    """A single OPSEC issue."""

    category: str  # local_paths, secrets, strategy_docs, infra_exposure, credentials
    severity: str  # critical, high, medium, low
    file: str
    line: int | None
    message: str


@dataclass
class OpsecSummary:
    """Aggregated OPSEC findings."""

    findings: list[OpsecFinding] = field(default_factory=list)
    category_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    score: int = 100

    def add(self, finding: OpsecFinding) -> None:
        self.findings.append(finding)
        self.category_counts[finding.category] += 1


# --- Detection patterns ---

# Local filesystem paths (home directories)
_HOME_PATH_PATTERN = re.compile(r"/home/\w+/|/Users/\w+/|C:\\Users\\\w+\\")

# API key / secret patterns (real values, not placeholders)
_SECRET_PATTERNS = [
    (re.compile(r"sk-ant-[a-zA-Z0-9\-]{20,}"), "Anthropic API key"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "OpenAI API key"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub personal access token"),
    (re.compile(r"gho_[a-zA-Z0-9]{36}"), "GitHub OAuth token"),
    (re.compile(r"AKIA[A-Z0-9]{16}"), "AWS access key"),
    (re.compile(r"xai-[a-zA-Z0-9]{20,}"), "xAI API key"),
    (re.compile(r"xoxb-[0-9]{10,}-[a-zA-Z0-9]+"), "Slack bot token"),
    (re.compile(r"xoxp-[0-9]{10,}-[a-zA-Z0-9]+"), "Slack user token"),
]

# Hardcoded passwords (not in comments, not placeholders)
_PASSWORD_PATTERN = re.compile(
    r"""(?:password|passwd|pwd|secret)\s*[=:]\s*['"][^'"]{4,}['"]""",
    re.IGNORECASE,
)

# Placeholder indicators (skip these lines)
_PLACEHOLDER_INDICATORS = re.compile(
    r"your[-_]|example|placeholder|changeme|xxx|REPLACE|<.*>|\.\.\.|\*{3,}",
    re.IGNORECASE,
)

# Strategy / outreach documents
_STRATEGY_FILENAMES = {
    "outreach.md",
    "outreach.txt",
    "sales.md",
    "sales-strategy.md",
    "pitch.md",
    "pitch-deck.md",
    "cold-email.md",
    "cold_email.md",
    "pricing-strategy.md",
    "competitor-analysis.md",
    "go-to-market.md",
    "gtm.md",
}

# Interview artifacts
_INTERVIEW_INDICATORS = re.compile(
    r"interview|take[-_]home|technical[-_]exercise|coding[-_]challenge|assessment",
    re.IGNORECASE,
)

# Infrastructure exposure in fly.toml
_FLY_SENSITIVE_KEYS = {"app", "primary_region", "kill_signal", "kill_timeout"}

# Private key markers
_PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----")

# .env files that shouldn't be tracked (not .env.example)
_REAL_ENV_PATTERN = re.compile(r"(^|/)\.env$")

# Database connection strings with credentials
_DB_CONN_PATTERN = re.compile(
    r"(?:postgres|mysql|mongodb|redis)://\w+:[^@\s]+@",
    re.IGNORECASE,
)


class OpsecAnalyzer:
    """Scans codebase for operational security leaks."""

    def analyze(self, structure: ProjectStructure, config: ForgeConfig) -> AnalysisResult:
        """Scan files for OPSEC risks."""
        summary = OpsecSummary()

        # Project-level checks
        self._check_strategy_docs(structure, summary)
        self._check_tracked_env_files(structure, summary)
        self._check_interview_artifacts(structure, summary)

        # File-level checks on scannable files
        scannable = [
            f
            for f in structure.files
            if f.extension in _SCANNABLE_EXTENSIONS or f.path.name.startswith(".env")
        ]
        sample = scannable[:_MAX_SAMPLE_FILES]

        for fi in sample:
            full_path = structure.root / fi.path
            try:
                text = full_path.read_text(errors="replace")
            except OSError:
                continue

            filepath = str(fi.path)
            is_scan_script = self._is_scan_script(filepath, text)

            self._check_local_paths(text, filepath, summary)

            if not is_scan_script:
                self._check_secrets(text, filepath, summary)

            self._check_private_keys(text, filepath, summary)
            self._check_hardcoded_passwords(text, filepath, summary)
            self._check_db_credentials(text, filepath, summary)

        # Calculate score
        summary.score = self._calculate_score(summary)

        findings = {
            "score": summary.score,
            "total_findings": len(summary.findings),
            "categories": dict(summary.category_counts),
            "critical_count": sum(1 for f in summary.findings if f.severity == "critical"),
            "high_count": sum(1 for f in summary.findings if f.severity == "high"),
            "medium_count": sum(1 for f in summary.findings if f.severity == "medium"),
            "low_count": sum(1 for f in summary.findings if f.severity == "low"),
            "findings": [
                {
                    "category": f.category,
                    "severity": f.severity,
                    "file": f.file,
                    "line": f.line,
                    "message": f.message,
                }
                for f in summary.findings
            ],
        }

        confidence = min(1.0, len(sample) / _MAX_SAMPLE_FILES)
        section = self._render_section(summary)

        return AnalysisResult(
            category="opsec",
            findings=findings,
            confidence=confidence,
            section_content=section,
        )

    # --- Check methods ---

    def _is_scan_script(self, filepath: str, text: str) -> bool:
        """Detect scripts that scan FOR secrets (avoid false positives)."""
        scan_indicators = ("grep", "gitleaks", "opsec", "secret.scan", "bandit")
        return any(ind in text[:500].lower() for ind in scan_indicators)

    def _check_local_paths(self, text: str, filepath: str, summary: OpsecSummary) -> None:
        """Detect hardcoded local filesystem paths."""
        for i, line in enumerate(text.splitlines(), 1):
            if _HOME_PATH_PATTERN.search(line):
                summary.add(
                    OpsecFinding(
                        category="local_paths",
                        severity="high",
                        file=filepath,
                        line=i,
                        message=f"Local filesystem path exposed: {line.strip()[:80]}",
                    )
                )

    def _check_secrets(self, text: str, filepath: str, summary: OpsecSummary) -> None:
        """Detect hardcoded API keys and tokens."""
        # Skip .env.example and .env.sample files
        if ".example" in filepath or ".sample" in filepath:
            return

        for i, line in enumerate(text.splitlines(), 1):
            # Skip comment lines and grep patterns
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue
            if "grep" in stripped.lower() or "rg " in stripped:
                continue
            # Skip placeholder values
            if _PLACEHOLDER_INDICATORS.search(line):
                continue

            for pattern, label in _SECRET_PATTERNS:
                if pattern.search(line):
                    summary.add(
                        OpsecFinding(
                            category="secrets",
                            severity="critical",
                            file=filepath,
                            line=i,
                            message=f"Possible {label} detected",
                        )
                    )
                    break  # one finding per line

    def _check_private_keys(self, text: str, filepath: str, summary: OpsecSummary) -> None:
        """Detect private key material."""
        if _PRIVATE_KEY_PATTERN.search(text):
            summary.add(
                OpsecFinding(
                    category="secrets",
                    severity="critical",
                    file=filepath,
                    line=None,
                    message="Private key material found in tracked file",
                )
            )

    def _check_hardcoded_passwords(self, text: str, filepath: str, summary: OpsecSummary) -> None:
        """Detect hardcoded passwords in non-example files."""
        if ".example" in filepath or ".sample" in filepath:
            return

        for i, line in enumerate(text.splitlines(), 1):
            if _PASSWORD_PATTERN.search(line) and not _PLACEHOLDER_INDICATORS.search(line):
                summary.add(
                    OpsecFinding(
                        category="credentials",
                        severity="high",
                        file=filepath,
                        line=i,
                        message="Hardcoded password or secret value",
                    )
                )

    def _check_db_credentials(self, text: str, filepath: str, summary: OpsecSummary) -> None:
        """Detect database connection strings with embedded credentials."""
        if ".example" in filepath or ".sample" in filepath:
            return

        for i, line in enumerate(text.splitlines(), 1):
            if _DB_CONN_PATTERN.search(line) and not _PLACEHOLDER_INDICATORS.search(line):
                summary.add(
                    OpsecFinding(
                        category="credentials",
                        severity="critical",
                        file=filepath,
                        line=i,
                        message="Database connection string with embedded credentials",
                    )
                )

    def _check_strategy_docs(self, structure: ProjectStructure, summary: OpsecSummary) -> None:
        """Detect tracked strategy/outreach documents."""
        for fi in structure.files:
            name = fi.path.name.lower()
            if name in _STRATEGY_FILENAMES:
                summary.add(
                    OpsecFinding(
                        category="strategy_docs",
                        severity="high",
                        file=str(fi.path),
                        line=None,
                        message=f"Strategy/outreach document tracked: {fi.path.name}",
                    )
                )

    def _check_tracked_env_files(self, structure: ProjectStructure, summary: OpsecSummary) -> None:
        """Detect real .env files (not .env.example) in tracked files."""
        for fi in structure.files:
            if _REAL_ENV_PATTERN.search(str(fi.path)):
                summary.add(
                    OpsecFinding(
                        category="credentials",
                        severity="critical",
                        file=str(fi.path),
                        line=None,
                        message="Real .env file tracked (should be in .gitignore)",
                    )
                )

    def _check_interview_artifacts(
        self, structure: ProjectStructure, summary: OpsecSummary
    ) -> None:
        """Detect interview/assessment artifacts in repo."""
        for fi in structure.files:
            path_str = str(fi.path).lower()
            if _INTERVIEW_INDICATORS.search(path_str):
                summary.add(
                    OpsecFinding(
                        category="strategy_docs",
                        severity="low",
                        file=str(fi.path),
                        line=None,
                        message="Possible interview artifact (consider if repo should be private)",
                    )
                )
                break  # one finding is enough

    # --- Scoring ---

    def _calculate_score(self, summary: OpsecSummary) -> int:
        """100 = clean, 0 = critical exposure."""
        score = 100
        for finding in summary.findings:
            score -= _SEVERITY_WEIGHTS.get(finding.severity, 1)
        return max(0, min(100, score))

    # --- Rendering ---

    def _render_section(self, summary: OpsecSummary) -> str:
        """Render markdown section for CLAUDE.md."""
        if not summary.findings:
            return ""

        lines = ["## Security"]
        lines.append("")

        critical = [f for f in summary.findings if f.severity == "critical"]
        high = [f for f in summary.findings if f.severity == "high"]

        if critical:
            lines.append("### Critical Issues")
            lines.append("")
            for f in critical:
                loc = f"{f.file}:{f.line}" if f.line else f.file
                lines.append(f"- **{f.message}** (`{loc}`)")
            lines.append("")

        if high:
            lines.append("### High Priority")
            lines.append("")
            for f in high:
                loc = f"{f.file}:{f.line}" if f.line else f.file
                lines.append(f"- {f.message} (`{loc}`)")
            lines.append("")

        return "\n".join(lines)
