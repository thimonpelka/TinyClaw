from features.commands.registry import CommandContext
import ollama


async def handle_compact(ctx: CommandContext, args: str) -> None:
    """Summarize recent chat history and replace those entries with a single summary.

    Usage: /compact [N|all]
      - N: number of most recent history entries to summarize (default: all)
      - all: summarize the entire history

    The handler expects `ctx.extras["app"]` to be a reference to the active ChatApp instance.
    """

    app = None
    try:
        app = ctx.extras.get("app")
    except Exception:
        app = None

    if app is None:
        ctx.write_error("Compact command not available: app reference missing in CommandContext.extras.")
        return

    arg = (args or "").strip().lower()
    if arg == "all" or not arg:
        # Default: summarize the entire history when no argument is provided
        n = len(app.history)
    else:
        try:
            n = int(arg)
        except Exception:
            ctx.write_error("Invalid argument. Usage: /compact [N|all]")
            return

    if n <= 0:
        ctx.write_error("N must be a positive integer")
        return

    if not app.history:
        ctx.write_system("No chat history to compact.")
        return

    n = min(n, len(app.history))
    convo = app.history[-n:]

    # Build a human-readable transcript for the summarizer
    parts = []
    for item in convo:
        role = item.get("role", "unknown")
        content = item.get("content", "")
        parts.append(f"{role.upper()}:\n{content}\n")
    convo_text = "\n---\n\n".join(parts)

    # Instruction for the summarizer: produce a short factual summary only
    system_instruction = (
        "You are a concise summarizer. Produce a short (one-paragraph) summary that captures key facts, decisions, action-items, and relevant details from the conversation. "
        "Return the summary only. Do not add commentary, meta-text, or explanations."
    )

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": convo_text},
    ]

    try:
        response = await ollama.AsyncClient().chat(model=app.model, messages=messages)
        # response.message.content is expected to be the assistant text
        summary = response.message.content if getattr(response, "message", None) else str(response)
    except Exception as e:
        ctx.write_error(f"Summarization failed: {e}")
        return

    # Create a single summary entry and replace the tail of history
    summary_entry = {"role": "assistant", "content": f"[compact summary]\n\n{summary}"}
    app.history = app.history[:-n] + [summary_entry]

    ctx.write_system(f"Compacted last {n} message(s) into a single summary to reduce tokens.")
    # Show the produced summary in the log for visibility
    ctx.log.write(summary)
