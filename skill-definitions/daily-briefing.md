---
name: daily-briefing
description: Produces one consolidated summary of today's calendar events, unread email, and open tasks
when_to_use: When the user asks for a daily briefing, morning summary, "what's on my plate today", or similar overview of their day. Also suitable for a recurring morning heartbeat task.
---

# Daily Briefing

When this skill is active, build a single consolidated briefing instead of answering with separate tool dumps.

1. Gather the day's raw material with these tool calls **in parallel** (call them together, not one after another):
   - `calendar_list_events` for today's date range, to get the schedule.
   - `gmail_list_emails` with `query="is:unread"` to get unread mail.
   - `list_tasks` to see open/recurring tasks.
2. Once all three results are back, synthesize them into one short briefing with three sections, in this order:
   - **Schedule** — today's events with times, earliest first. Say "No events today" if empty.
   - **Inbox** — unread emails, each as one line: sender + subject. Flag anything that looks time-sensitive (e.g. mentions a deadline, meeting today, or "urgent"/"asap"). Say "Inbox is clear" if empty.
   - **Tasks** — open tasks and when they're next due. Say "No open tasks" if empty.
3. Keep it skimmable: short lines, no filler sentences, no restating the user's request. This briefing should be readable in under 15 seconds.
4. Do not take any action on the user's behalf (no replying to emails, no creating/deleting events or tasks) unless they explicitly ask after seeing the briefing — this skill is read-only/summarizing by default.
5. If a data source errors out (e.g. Calendar or Gmail not authenticated), still produce the briefing from whatever sources succeeded, and note which section is missing and why.
