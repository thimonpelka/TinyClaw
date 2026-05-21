from pathlib import Path

from rich.text import Text

from features.skills.colors import skill_color
from features.skills.loader import load_skills
from features.skills.prompt import build_system_prompt
from features.skills.types import Skill


class SkillsManager:
    def __init__(self, skills_dir: Path) -> None:
        self._skills_dir = skills_dir
        self._skills: list[Skill] = []
        self._active: list[str] = []

    def load(self) -> None:
        self._skills = load_skills(self._skills_dir)

    @property
    def skills(self) -> list[Skill]:
        return self._skills

    @property
    def active_skill_names(self) -> list[str]:
        return list(self._active)

    def find(self, name: str) -> Skill | None:
        return next((s for s in self._skills if s["name"] == name), None)

    def activate(self, name: str) -> bool:
        """Returns False if already active, raises ValueError if skill not found."""
        if name in self._active:
            return False
        if self.find(name) is None:
            raise ValueError(f"Skill '{name}' not found")
        self._active.append(name)
        return True

    def deactivate(self, name: str) -> bool:
        """Returns False if not active."""
        if name not in self._active:
            return False
        self._active.remove(name)
        return True

    def deactivate_all(self) -> None:
        self._active.clear()

    def build_prefix(self, extra_names: list[str] | None = None) -> str:
        names = list(self._active) + (extra_names or [])
        parts = []
        for name in names:
            skill = self.find(name)
            if skill:
                parts.append(f"# [Skill: {name}]\n{skill['content']}")
        return "\n\n---\n\n".join(parts)

    def badge_markup(self, name: str) -> str:
        return f"[bold {skill_color(name)}] {name} [/]"

    def indicator_text(self) -> Text:
        if not self._active:
            return Text(
                "No active skills  ·  press s to browse  ·  /skill-name to activate",
                style="dim",
            )
        text = Text()
        for i, name in enumerate(self._active):
            if i > 0:
                text.append("  ")
            text.append(f" {name} ", style=f"bold {skill_color(name)}")
        return text

    def list_renderables(self) -> list[tuple[str, str, str]]:
        result = []
        for s in self._skills:
            active_marker = " ●" if s["name"] in self._active else ""
            badge = f"[bold {skill_color(s['name'])}][ {s['name']}{active_marker} ][/]"
            result.append((badge, s["description"], s["when_to_use"]))
        return result

    def system_prompt(self) -> str:
        return build_system_prompt(self._skills)
