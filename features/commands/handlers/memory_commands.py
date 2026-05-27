from features.commands.registry import CommandContext


async def handle_create_memory(ctx: CommandContext, args: str) -> None:
    """Handle /create-memory <description> — instruct the agent to save a memory."""
    if not args.strip():
        ctx.write_error("Usage: /create-memory <description of what to remember>")
        return
    instruction = (
        f"Please save a memory about the following:\n\n{args.strip()}\n\n"
        "Choose an appropriate kebab-case filename ending in .md and call the "
        "`save_memory` tool (or `update_memory` if a relevant file already exists). "
        "Confirm what you saved when done."
    )
    ctx.send_message(f"/create-memory {args.strip()}", instruction)
