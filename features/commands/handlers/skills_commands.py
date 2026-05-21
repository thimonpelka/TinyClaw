from features.commands.registry import CommandContext


async def handle_list_skills(ctx: CommandContext, args: str) -> None:
    if not ctx.skills.skills:
        ctx.write_system("No skills loaded (add .md files to skill-definitions/)")
        return
    ctx.write_system("Available skills (● = active):")
    for badge, desc, when in ctx.skills.list_renderables():
        ctx.log.write(f"  {badge} — {desc}  [dim](use when: {when})[/dim]")


async def handle_disable_skills(ctx: CommandContext, args: str) -> None:
    if not args:
        ctx.skills.deactivate_all()
        ctx.write_system("All skills deactivated.")
    else:
        name = args.strip()
        if ctx.skills.deactivate(name):
            ctx.write_system(f"Skill [cyan]{name}[/cyan] deactivated.")
        else:
            ctx.write_error(f"Skill '{name}' is not currently active.")
    ctx.update_indicator()


async def handle_skill_by_name(ctx: CommandContext, raw: str) -> None:
    """Fallback handler: /<skill-name> [inline message]"""
    parts = raw.split(" ", 1)
    skill_name = parts[0]
    inline_message = parts[1].strip() if len(parts) > 1 else None

    if ctx.skills.find(skill_name) is None:
        ctx.write_error(f"Unknown command: /{raw}")
        return

    if inline_message:
        prefix = ctx.skills.build_prefix(extra_names=[skill_name])
        full_text = f"{prefix}\n\n---\n\n{inline_message}"
        display_text = f"{ctx.skills.badge_markup(skill_name)} {inline_message}"
        ctx.send_message(display_text, full_text)
    else:
        activated = ctx.skills.activate(skill_name)
        if not activated:
            ctx.write_error(f"Skill '{skill_name}' is already active.")
            return
        ctx.write_system(
            f"Skill [cyan]{skill_name}[/cyan] activated — prepended to all future messages."
        )
        ctx.update_indicator()
