"""AI Skills analyzer — detects installed Codex/Claude skills and recommends bundles."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from anchormd.models import AnalysisResult, ForgeConfig, ProjectStructure

logger = logging.getLogger(__name__)

# Supported local skill directories (newest first).
PROJECT_SKILL_ROOTS = (".codex", ".claude")


def _default_skills_dirs() -> list[Path]:
    """Build default skill directory candidates in priority order."""
    candidates: list[Path] = []

    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        candidates.append(Path(codex_home).expanduser() / "skills")

    home = Path.home()
    candidates.extend(
        [
            home / ".codex" / "skills",
            home / ".claude" / "skills",
        ]
    )

    # Deduplicate while preserving order.
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


# Map framework indicators to recommended skill bundles.
FRAMEWORK_BUNDLE_MAP: dict[str, list[str]] = {
    "fastapi": ["full-stack-dev", "api-integration"],
    "django": ["full-stack-dev", "api-integration"],
    "flask": ["full-stack-dev", "api-integration"],
    "express": ["full-stack-dev", "api-integration"],
    "nestjs": ["full-stack-dev", "api-integration"],
    "react": ["website-builder", "full-stack-dev"],
    "nextjs": ["website-builder", "full-stack-dev"],
    "vue": ["website-builder"],
    "svelte": ["website-builder"],
    "rust": ["full-stack-dev"],
    "bevy": ["full-stack-dev"],
    "go": ["full-stack-dev"],
}

# Skills relevant to specific project patterns.
PATTERN_SKILL_MAP: dict[str, list[str]] = {
    "has_ci": ["cicd-pipeline"],
    "has_docker": ["web-deployer"],
    "has_tests": ["testing-specialist", "code-reviewer"],
    "has_scoring": ["composite-scorer"],
    "has_content": ["content-scrubber", "web-content-writer"],
    "has_agents": ["handoff", "multi-agent-supervisor"],
}


class SkillsAnalyzer:
    """Detects installed AI skills and recommends relevant ones for the project."""

    def __init__(self, skills_dir: Path | None = None) -> None:
        self._skills_dirs = [skills_dir.expanduser()] if skills_dir else _default_skills_dirs()

    def analyze(self, structure: ProjectStructure, config: ForgeConfig) -> AnalysisResult:
        """Detect installed skills and recommend bundles based on project."""
        findings: dict[str, object] = {}

        installed, installed_dirs = self._detect_installed_skills()
        findings["installed_skills"] = installed
        findings["installed_count"] = len(installed)
        findings["installed_skill_dirs"] = [str(path) for path in installed_dirs]

        frameworks = self._detect_frameworks(structure)
        findings["detected_frameworks"] = frameworks

        recommended = self._recommend_skills(structure, frameworks, installed)
        findings["recommended_skills"] = recommended
        findings["recommended_bundles"] = self._recommend_bundles(frameworks)

        project_skills = self._detect_project_skills(structure)
        findings["project_skills"] = project_skills

        sources = sum(1 for v in [installed, recommended, project_skills] if v)
        confidence = min(1.0, sources / 2.0) if sources else 0.1

        section = self._render_section(findings)

        return AnalysisResult(
            category="skills",
            findings=findings,
            confidence=confidence,
            section_content=section,
        )

    def _detect_installed_skills(self) -> tuple[list[str], list[Path]]:
        """Find skills installed in supported local skill directories."""
        skills: set[str] = set()
        installed_dirs: list[Path] = []

        for skills_dir in self._skills_dirs:
            if not skills_dir.is_dir():
                continue

            installed_dirs.append(skills_dir)
            for entry in sorted(skills_dir.iterdir()):
                if entry.is_dir() and (entry / "SKILL.md").is_file():
                    skills.add(entry.name)

        return sorted(skills), installed_dirs

    def _detect_frameworks(self, structure: ProjectStructure) -> list[str]:
        """Detect frameworks from project structure."""
        frameworks: list[str] = []
        file_names = {Path(f.path).name for f in structure.files}

        from anchormd.config import FRAMEWORK_INDICATORS

        for framework, indicators in FRAMEWORK_INDICATORS.items():
            for indicator in indicators:
                if ":" in indicator:
                    filename, search_term = indicator.split(":", 1)
                    matching = [f for f in structure.files if Path(f.path).name == filename]
                    if matching:
                        try:
                            content = (structure.root / matching[0].path).read_text(
                                errors="replace"
                            )
                            if search_term in content:
                                frameworks.append(framework)
                                break
                        except OSError:
                            continue
                elif indicator in file_names:
                    frameworks.append(framework)
                    break

        return frameworks

    def _detect_project_skills(self, structure: ProjectStructure) -> list[str]:
        """Detect skills defined within project-local instruction directories."""
        skills: set[str] = set()

        for root_name in PROJECT_SKILL_ROOTS:
            for subdir in ("commands", "agents", "skills"):
                skill_dir = structure.root / root_name / subdir
                if not skill_dir.is_dir():
                    continue

                for entry in sorted(skill_dir.iterdir()):
                    if entry.suffix == ".md":
                        skills.add(f"{subdir}/{entry.stem}")
                    elif entry.is_dir() and (entry / "SKILL.md").is_file():
                        skills.add(f"{subdir}/{entry.name}")

        return sorted(skills)

    def _recommend_skills(
        self,
        structure: ProjectStructure,
        frameworks: list[str],
        installed: list[str],
    ) -> list[str]:
        """Recommend skills based on project patterns."""
        recommended: set[str] = set()

        # Framework-based recommendations.
        for fw in frameworks:
            for bundle in FRAMEWORK_BUNDLE_MAP.get(fw, []):
                recommended.add(bundle)

        # Pattern-based recommendations.
        file_names = {Path(f.path).name for f in structure.files}

        if any(name in file_names for name in ("ci.yml", "test.yml", ".github")) or any(
            str(f.path).startswith(".github/workflows") for f in structure.files
        ):
            for skill in PATTERN_SKILL_MAP.get("has_ci", []):
                recommended.add(skill)

        if "Dockerfile" in file_names or "docker-compose.yml" in file_names:
            for skill in PATTERN_SKILL_MAP.get("has_docker", []):
                recommended.add(skill)

        if any("test" in Path(f.path).name for f in structure.files):
            for skill in PATTERN_SKILL_MAP.get("has_tests", []):
                recommended.add(skill)

        # Don't recommend what's already installed.
        recommended -= set(installed)

        return sorted(recommended)

    def _recommend_bundles(self, frameworks: list[str]) -> list[str]:
        """Recommend skill bundles based on detected frameworks."""
        bundles: set[str] = set()
        for fw in frameworks:
            bundles.update(FRAMEWORK_BUNDLE_MAP.get(fw, []))
        return sorted(bundles)

    def _render_section(self, findings: dict[str, Any]) -> str:
        """Render skills section as markdown."""

        def _to_str_list(value: object) -> list[str]:
            if isinstance(value, list):
                return [str(item) for item in value]
            return []

        installed = _to_str_list(findings.get("installed_skills", []))
        installed_dirs = _to_str_list(findings.get("installed_skill_dirs", []))
        project_skills = _to_str_list(findings.get("project_skills", []))
        recommended = _to_str_list(findings.get("recommended_skills", []))
        recommended_bundles = _to_str_list(findings.get("recommended_bundles", []))

        if not installed and not project_skills and not recommended:
            return ""

        lines: list[str] = ["## AI Skills", ""]

        if installed:
            if installed_dirs:
                dirs_text = ", ".join(
                    f"`{self._format_display_path(Path(path))}`" for path in installed_dirs
                )
                lines.append(f"**Installed**: {len(installed)} skills across {dirs_text}")
            else:
                lines.append(f"**Installed**: {len(installed)} skills")
            # Show first 15, summarize rest.
            shown = installed[:15]
            lines.append(f"- {', '.join(f'`{s}`' for s in shown)}")
            if len(installed) > 15:
                lines.append(f"- ... and {len(installed) - 15} more")
            lines.append("")

        if project_skills:
            lines.append("**Project-local skills**:")
            for skill in project_skills:
                lines.append(f"- `{skill}`")
            lines.append("")

        if recommended_bundles:
            lines.append(
                "**Recommended bundles**: " + ", ".join(f"`{b}`" for b in recommended_bundles)
            )
            lines.append("")

        if recommended:
            lines.append("**Recommended skills** (not yet installed):")
            for skill in recommended[:10]:
                lines.append(f"- `{skill}`")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_display_path(path: Path) -> str:
        """Render absolute paths relative to home when possible."""
        expanded = path.expanduser()
        try:
            relative = expanded.relative_to(Path.home())
        except ValueError:
            return str(expanded)
        return f"~/{relative.as_posix()}"
