---

name: research-log

description: Workspace research logging convention with a master research_log.md and detailed session logs in /logs

---

# research-log

Workspace research logging convention. This skill teaches agents how to use the structured research log in this workspace.

## When to use

Use this convention whenever completing a work session, starting a new session, or when any agent needs to understand the project history. This applies to all recurring tasks and manual sessions in this workspace.

## Convention

This workspace uses a two-tier research logging system:

### 1. `/workspace/research_log.md` — The master log

This file is the single source of truth for the workspace's research history. Its structure:

- **Opening paragraph**: A small, tight paragraph describing the research project, the experiment being run, and the scientific question being investigated. Written once, rarely changed.
- `## Sessions`** section**: A bullet list where each bullet is **one sentence** summarizing a single session/run. Bullets optionally include a markdown link to a detailed log file (e.g., `Full log`).

The research log must stay scannable — anyone should be able to read the full project history in 30 seconds.

### 2. `/workspace/logs/` — Detailed session logs

Each session gets its own file: `sessionNYYYY-MM-DD.md`. These contain full details: what was accomplished, key findings, surprises, limitations, and next steps. The research log bullets link here when more detail is available.

If an agent or future agent ever needs to understand what happened in a specific session, they read the detailed log. They should NOT need to read every detailed log — the research log gives the overview.

### 3. `/workspace/index.html` — Visual dashboard

This is your place to showcase your work visually. Update it at the end of every session so anyone opening the workspace can immediately see the current state of the research — progress, results, trends, and what's next.

## Instructions

When completing a work session:

1. **Write the detailed log first** — Create `/workspace/logs/sessionNYYYY-MM-DD.md` with full details of what you did.
2. **Then append ONE bullet to the research log** — Open `/workspace/research_log.md` and add exactly one bullet to the `## Sessions` section:

```

- **Session N (YYYY-MM-DD):** One sentence summary of what was done and the key finding. Full log

```

1. **Keep bullets to one sentence** — If you can't summarize in one sentence, pick the most important thing.
2. **Never rewrite the opening paragraph** unless explicitly asked.
3. **Never rewrite past bullets** — only append new ones.
4. **Update the dashboard** — As a final step, update `/workspace/index.html` to visually reflect the latest results. If a `generate_dashboard.py` script exists, run it. Otherwise, update the HTML directly. The dashboard should always reflect the current state of the research.
5. **Commit and push changes** — After updating the dashboard, commit all session artifacts and push to remote:
   - Stage the new session log, updated `research_log.md`, and updated `index.html`
   - Commit with a message summarizing the experiment: `experiment N: <short description>` and include the key result (val_bpb and ✓/✗) in the commit body
   - Push to remote: `git push`
   - This ensures every experiment is version-controlled and the remote stays up to date

When starting a work session:

1. **Read **`/workspace/research_log.md`** first** — this orients you on the project and its history.
2. **Only read detailed logs if needed** — don't read every log file on every run. The bullets tell you what happened; drill into `/workspace/logs/` only when you need specifics about a past session.