"""Document composer that assembles sections into a complete CLAUDE.md."""

from __future__ import annotations

import re

from anchormd.config import SECTION_ORDER
from anchormd.models import (
    AnalysisResult,
    ForgeConfig,
    FrameworkPreset,
    PresetPack,
    ProjectStructure,
)
from anchormd.templates.frameworks import FRAMEWORK_PRESETS, PREMIUM_PRESETS
from anchormd.templates.presets import PRESET_PACKS

from .sections import SectionGenerator

_FRAMEWORK_PRESET_BY_SIGNAL: dict[str, str] = {
    "fastapi": "python-fastapi",
    "django": "django",
    "react": "react-typescript",
    "nextjs": "nextjs",
    "rust": "rust",
    "go": "go",
    "express": "node-express",
}


class DocumentComposer:
    """Assembles sections into a complete CLAUDE.md document."""

    def __init__(self, config: ForgeConfig) -> None:
        self.config = config
        self._gen = SectionGenerator()

    def compose(
        self,
        structure: ProjectStructure,
        analyses: list[AnalysisResult],
        project_name: str | None = None,
    ) -> str:
        """Compose all sections into final CLAUDE.md content."""
        name = project_name or structure.root.name

        # Build a lookup by category.
        by_category: dict[str, AnalysisResult] = {}
        for a in analyses:
            by_category[a.category] = a

        # Generate each section.
        section_map: dict[str, str] = {}

        section_map["header"] = self._gen.generate_header(name)
        section_map["project_overview"] = self._gen.generate_project_overview(
            name, structure_description=structure.description or ""
        )
        section_map["current_state"] = self._gen.generate_current_state(structure)
        section_map["architecture"] = self._gen.generate_architecture(structure)

        if "language" in by_category:
            section_map["tech_stack"] = self._gen.generate_tech_stack(by_category["language"])
        if "patterns" in by_category:
            section_map["coding_standards"] = self._gen.generate_coding_standards(
                by_category["patterns"]
            )
        if "commands" in by_category:
            section_map["common_commands"] = self._gen.generate_commands(by_category["commands"])
        if "domain" in by_category:
            section_map["domain_context"] = self._gen.generate_domain_context(by_category["domain"])
        if "skills" in by_category and by_category["skills"].section_content:
            section_map["skills"] = by_category["skills"].section_content

        section_map["anti_patterns"] = self._gen.generate_anti_patterns(structure, analyses)
        section_map["dependencies"] = self._gen.generate_dependencies(analyses, structure)
        section_map["git_conventions"] = self._gen.generate_git_conventions(structure)

        pack = self._resolve_pack()
        framework_preset = self._resolve_framework_preset(by_category)
        if framework_preset:
            self._apply_framework_preset(section_map, framework_preset)

        result = self._assemble_sections(section_map, pack)
        return self._clean_output(result)

    def _resolve_pack(self) -> PresetPack | None:
        """Resolve a named preset pack (default/minimal/full/etc.)."""
        return PRESET_PACKS.get(self.config.preset)

    def _resolve_framework_preset(
        self, by_category: dict[str, AnalysisResult]
    ) -> FrameworkPreset | None:
        """Resolve explicit or auto-detected framework preset guidance."""
        preset_name = self.config.preset
        if preset_name in FRAMEWORK_PRESETS:
            return FRAMEWORK_PRESETS[preset_name]
        if preset_name in PREMIUM_PRESETS:
            return PREMIUM_PRESETS[preset_name]

        pack = PRESET_PACKS.get(preset_name)
        if not pack or not pack.auto_detect:
            return None

        language_analysis = by_category.get("language")
        if not language_analysis:
            return None
        frameworks = language_analysis.findings.get("frameworks", [])
        if not isinstance(frameworks, list):
            return None

        for framework in frameworks:
            mapped_name = _FRAMEWORK_PRESET_BY_SIGNAL.get(str(framework).lower())
            if not mapped_name:
                continue
            if mapped_name in FRAMEWORK_PRESETS:
                return FRAMEWORK_PRESETS[mapped_name]
            if mapped_name in PREMIUM_PRESETS:
                return PREMIUM_PRESETS[mapped_name]

        return None

    def _apply_framework_preset(
        self, section_map: dict[str, str], framework_preset: FrameworkPreset
    ) -> None:
        """Overlay coding standards/commands/anti-patterns from framework preset."""
        section_map["coding_standards"] = self._render_list_section(
            "Coding Standards",
            framework_preset.coding_standards,
        )
        section_map["anti_patterns"] = self._render_list_section(
            "Anti-Patterns (Do NOT Do)",
            framework_preset.anti_patterns,
        )
        section_map["common_commands"] = self._render_commands_section(
            framework_preset.common_commands
        )

        tech_stack = section_map.get("tech_stack", "")
        if tech_stack and "- **Preset**:" not in tech_stack:
            section_map["tech_stack"] = (
                f"{tech_stack.rstrip()}\n- **Preset**: {framework_preset.name}\n"
            )

    def _render_list_section(self, title: str, items: list[str]) -> str:
        lines = [f"## {title}", ""]
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
        return "\n".join(lines)

    def _render_commands_section(self, commands: dict[str, str]) -> str:
        lines = ["## Common Commands", "", "```bash"]
        for name, command in commands.items():
            lines.append(f"# {name}")
            lines.append(command)
            lines.append("")
        if lines[-1] == "":
            lines.pop()
        lines.extend(["```", ""])
        return "\n".join(lines)

    def _assemble_sections(self, section_map: dict[str, str], pack: PresetPack | None) -> str:
        """Assemble final document honoring pack section selection and extras."""
        allowed_sections = set(pack.sections) if pack and pack.sections else set(SECTION_ORDER)

        parts: list[str] = []
        for section_name in SECTION_ORDER:
            if section_name not in allowed_sections:
                continue
            content = section_map.get(section_name, "")
            if content and content.strip():
                parts.append(content)

        if pack and pack.extra_sections:
            for section_title in pack.extra_sections:
                parts.append(self._render_pack_extra_section(section_title, pack.name))

        return "\n".join(parts)

    def _render_pack_extra_section(self, section_title: str, pack_name: str) -> str:
        return (
            f"## {section_title}\n\n"
            f"This section is included by the `{pack_name}` preset. "
            "Add project-specific guidance here.\n"
        )

    def _clean_output(self, content: str) -> str:
        """Remove excessive blank lines, normalize heading levels, ensure trailing newline."""
        # Collapse 3+ consecutive blank lines to 2.
        content = re.sub(r"\n{3,}", "\n\n", content)
        # Ensure single trailing newline.
        content = content.rstrip() + "\n"
        return content

    def estimate_quality_score(self, content: str) -> int:
        """Score 0-100 based on section coverage and content depth."""
        score = 0

        # Section coverage (max 60 points).
        expected_headings = [
            "Project Overview",
            "Current State",
            "Architecture",
            "Tech Stack",
            "Coding Standards",
            "Common Commands",
            "Anti-Patterns",
            "Dependencies",
            "Git Conventions",
        ]
        present = sum(1 for h in expected_headings if f"## {h}" in content)
        score += int((present / len(expected_headings)) * 60)

        # Content depth (max 20 points).
        lines = content.splitlines()
        if len(lines) > 50:
            score += 10
        if len(lines) > 100:
            score += 5
        if len(lines) > 150:
            score += 5

        # Code blocks present (max 10 points).
        code_blocks = content.count("```")
        if code_blocks >= 2:
            score += 10
        elif code_blocks >= 1:
            score += 5

        # Specificity — bullet points with bold labels (max 10 points).
        bold_bullets = len(re.findall(r"- \*\*\w+", content))
        if bold_bullets > 5:
            score += 10
        elif bold_bullets > 2:
            score += 5

        return min(100, score)
