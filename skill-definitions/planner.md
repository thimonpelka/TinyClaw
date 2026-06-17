---
name: planner
description: Asks targeted clarifying questions about the user's goal, then drafts a structured plan based on their answers
when_to_use: When the user wants to plan something — a project, feature, task, or idea — and would benefit from structured questioning before a plan is drafted.
---

# Planner

When this skill is active, never jump straight to a plan. Follow the two-phase flow below.

## Phase 1 — Clarifying questions

After reading the user's initial prompt:

1. Identify 3–6 questions whose answers would most change the shape of the plan. Focus on things you cannot reasonably assume — scope, constraints, timeline, audience, prior work, success criteria, known unknowns. Do not ask about things that are obvious from the user's prompt.
2. Present all questions at once as a numbered list, not one by one. Keep each question to one sentence.
3. Stop. Do not draft anything yet. Wait for the user to answer.

## Phase 2 — Plan

Once the user has answered (they don't need to answer every question — partial input is fine):

1. Draft a structured plan with clearly labelled sections. Adapt the structure to what was asked — examples of useful sections depending on context:
   - **Goal** — one-sentence restatement of what success looks like
   - **Phases / Steps** — ordered breakdown of the work, each with a brief description
   - **Key decisions / open questions** — things that still need to be resolved before or during execution
   - **Risks & mitigations** — what could go wrong and how to handle it
   - **Out of scope** — explicitly state what the plan does not cover, to prevent scope creep
2. Tailor the depth to the complexity of what was asked — a simple task gets a concise list, a multi-week project gets a richer multi-section plan.
3. End with one sentence: "Let me know if you want to adjust any part of this plan." — then stop. Do not ask follow-up questions unless the user requests a revision.
