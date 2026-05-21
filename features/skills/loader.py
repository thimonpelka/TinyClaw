from pathlib import Path

from features.skills.types import Skill


def load_skills(skills_dir: Path) -> list[Skill]:
    skills: list[Skill] = []
    if not skills_dir.exists():
        return skills
    for path in sorted(skills_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) == 3:
                fm, body = parts[1], parts[2]
                meta: dict[str, str] = {}
                for line in fm.strip().splitlines():
                    if ": " in line:
                        k, v = line.split(": ", 1)
                        meta[k.strip()] = v.strip()
                skills.append(
                    Skill(
                        name=meta.get("name", path.stem),
                        description=meta.get("description", ""),
                        when_to_use=meta.get("when_to_use", ""),
                        content=body.strip(),
                    )
                )
    return skills
