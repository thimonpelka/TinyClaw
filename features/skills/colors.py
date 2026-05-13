import hashlib

SKILL_BADGE_COLORS = [
    "#7aa2f7",  # blue
    "#9ece6a",  # green
    "#e0af68",  # yellow
    "#bb9af7",  # purple
    "#f7768e",  # red
    "#2ac3de",  # cyan
    "#ff9e64",  # orange
]


def skill_color(name: str) -> str:
    idx = int(hashlib.md5(name.encode()).hexdigest(), 16) % len(SKILL_BADGE_COLORS)
    return SKILL_BADGE_COLORS[idx]
