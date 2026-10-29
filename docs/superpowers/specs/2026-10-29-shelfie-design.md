# Shelfie — design

**Date:** 2026-10-29
**Owner:** the author (personal open-source project, published under a personal GitHub account)
**One-liner:** Automatic artifact log for Claude Code — every file, page and server Claude makes in a project, with dates, descriptions and change history, browsable on one page.

## 1. Why

Claude produces a lot of deliverables: published claude.ai artifacts, HTML dashboards, PDFs, Markdown reports, decks, sheets, local prototypes. Today they get lost. The owner's real workflow is "send it to the client in chat, later scroll the chat to find it" — which he calls stone age. The built-in claude.ai gallery and `/artifacts` list exist but only cover published artifacts and lack what matters for finding things: a date and a short "what is this" description. Local files and local servers are not tracked anywhere.

The owner searches **by approximate date** first ("it was sometime around mid-September"), then recognises the item by its description.

**Success:** open one page, glance at the activity map / timeline around the remembered date, recognise the artifact by its one-line description, copy its link or open it — in seconds, without scrolling chats.

## 2. Goals

1. **Capture is automatic.** Nothing depends on the user or Claude remembering to register an artifact. Deterministic hooks detect candidates.
2. **Every entry has a date, a type and a short description.** Descriptions are written by Claude at the moment of creation, while it has context.
3. **Change history.** Each artifact keeps a list of dated, one-line "what changed" notes.
4. **One page to browse**, opened from Finder or via a command, that shows type at a glance (icon level).
5. **Per-project.** Installed into one project; all state lives inside that project.
6. **Publishable** as a Claude Code plugin from a public GitHub repo.

## 3. Non-goals

- No local web server for the dashboard (explicitly rejected by the owner). The dashboard is a static file, read-only.
- No editing or settings from the dashboard. Settings are changed via a command.
- No cross-project aggregation in v1.
- No "sent to / recipient" field — an agent cannot know it reliably.
- No backfill of past artifacts (no import of the existing claude.ai gallery or old files) in v1.
- No full diffs. Change history is human-readable one-liners, not a version store.
- Windows support is not required for v1 (macOS primary, Linux should work).

## 4. Anti-goals (would make this a failure even if it technically works)

- **Noise.** README files, specs, scratch notes, throwaway test servers cluttering the timeline.
- **Nagging.** Claude being interrupted every turn, or many times per artifact, to write descriptions.
- **Requiring discipline.** If the user or Claude has to remember a step, artifacts will be lost again.
- **Slowing Claude down** noticeably (hooks must be fast).
- **Invented content.** Descriptions or fields that are guesses dressed up as facts.

## 5. What counts as an artifact

Two independent filters, both must pass:

1. **Format** — the item's type is enabled in the project config (user controls this).
2. **Classification** — Claude judges, from conversation context, whether the item is a real deliverable ("artifact") or incidental (README, spec, notes, scaffold, test server). Non-artifacts are kept as `ignored` (hidden from the timeline but restorable), never deleted.

### Types (formats)

| Type key   | Label            | Matches                                              | Icon colour |
|------------|------------------|------------------------------------------------------|-------------|
| `artifact` | Claude artifact  | a page published to claude.ai (has a claude.ai URL)  | `#d97757`   |
| `html`     | HTML             | `.html`, `.htm`                                      | `#f76b15`   |
| `pdf`      | PDF              | `.pdf`                                               | `#e5484d`   |
| `md`       | Markdown         | `.md`, `.markdown`                                   | grey        |
| `doc`      | Doc              | `.docx`, `.doc`, `.odt`, `.rtf`                      | `#3e63dd`   |
| `slides`   | Slides           | `.pptx`, `.key`, `.odp`                              | `#e2a336`   |
| `sheet`    | Sheet            | `.xlsx`, `.xls`, `.csv`, `.tsv`, `.ods`              | `#30a46c`   |
| `server`   | Local server     | something that runs (or can be run) on localhost and is itself the deliverable — a prototype, a dashboard, an app | `#8e4ec6` |
| `image`    | Image            | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`     | `#12a594`   |

A **local server** is only an artifact when it *is* the deliverable (e.g. "the logo animation lab prototype"), as judged from context — not every dev server Claude starts. For servers Shelfie records how to bring it back: command, working directory, port. It may or may not be running at any given time.

## 6. User-facing behaviour

### Install & first run
- Install into a project: `claude plugin marketplace add <owner>/shelfie`, then `claude plugin install shelfie@shelfie --scope project` (or the `/plugin` equivalents).
- First session in a project without `.shelfie/config.json`: Claude asks the user which formats to track (default: all nine), then writes the config. Tracking starts after that.

### Commands (one skill, `/shelfie`)
- `/shelfie` — regenerate and open the dashboard (`open` on macOS, `xdg-open` on Linux); print its path.
- `/shelfie formats` — show enabled/disabled formats and change them conversationally.
- `/shelfie ignored` — list ignored items; restore one (`/shelfie restore <id>`) or ignore one.
- `/shelfie setup` — re-run the first-run question.

### Dashboard
Static file at `<project>/.shelfie/shelfie.html`, opened from Finder or via `/shelfie`. Read-only. Data is embedded in the file (no fetch), so it works from `file://`. Visual reference: `docs/design/dashboard-mockup.html` (approved by the owner; layout "A" + activity map). All UI text in English. Light and dark themes follow the OS.

Top to bottom:
1. **Header:** eyebrow `<project-name> · artifact log`, title "Artifacts", stats: total / this month / today.
2. **Activity map:** last 26 weeks, GitHub-style grid, 5 intensity levels, month labels. Clicking a day filters the timeline to that day; clicking again clears.
3. **Sticky bar:** search over titles + descriptions + change notes (`/` focuses it); type filter chips with icon + count (single row, horizontal scroll on narrow screens).
4. **Timeline**, newest first, ordered by *last activity* (creation or last change). Groups: Today, Yesterday, This week, then by month (`October`, `September`…), with year once it's not the current year.
5. **Row:** type icon tile (coloured rounded square, glyph, small badge under it: `ARTIFACT`, `HTML`, `PDF`, `MD`, `DOCX`, `PPTX`, `XLSX`, `SERVER`, `IMG`), title, description (1–2 sentences), location line in mono (claude.ai URL / project-relative path / `localhost:PORT · command · dir`), time of last activity, `N changes` chip. Missing files (deleted since) show greyed with a "missing" marker.
6. **Expanded row** (click): vertical change history (date · time — note), ending with "Created"; actions: **Copy link** (artifact), **Open** (file:// link or claude.ai URL), **Copy path** (files), **Copy command** (servers). ("Reveal in Finder" is not possible from a static page — dropped.)
7. **Ignored (n)** collapsed section at the bottom, read-only, so the user can see what Claude filtered out.

## 7. How it works

### Components (decided)
- Claude Code **plugin**; the repo is also its own **marketplace** (`.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`).
- **Hooks** in `hooks/hooks.json`, implemented as **Python 3, standard library only** (no pip installs), one CLI script with subcommands.
- **Skill** `skills/shelfie/SKILL.md` for `/shelfie` and its arguments.
- **Per-project state** in `<project>/.shelfie/`:
  - `config.json` — enabled formats, exclude globs.
  - `registry.json` — entries (source of truth).
  - `shelfie.html` — generated dashboard (derived; safe to delete).
- Project root = `CLAUDE_PROJECT_DIR`.

### Capture (deterministic, no Claude involvement)
Hooks only record **candidates**; they never decide whether something is an artifact.

| Signal | Hook | What is recorded |
|---|---|---|
| Page published to claude.ai | `PostToolUse` on the artifact-publishing tool (`Artifact` in the Claude desktop app / environments that have it) | URL (from tool response), source file path, title/description passed in the call. Republish to the same URL = a change, not a new entry. |
| Local server started | `PostToolUse` on `Bash` when the command looks like a dev server (e.g. `npm/pnpm/yarn run dev|start|preview`, `vite`, `next dev`, `python -m http.server`, `flutter run -d web-server`, … or a backgrounded long-running command with a port), on writes to `.claude/launch.json`, and on the desktop app's preview-start tool | command, cwd, port (parsed if possible) |
| File created/changed | `UserPromptSubmit` marks the turn start; `Stop` scans the project for files of enabled file formats modified **during the turn** | path, type, mtime |

Files are detected by **scan at Stop**, not only by `Write`/`Edit` hooks, because many deliverables (PDFs, docx, pptx) are produced by scripts run via `Bash`. The scan skips `.git`, `.shelfie`, `.claude`, `node_modules`, virtualenvs and user-configured exclude globs; inside a git repo it should respect `.gitignore`. Only files inside the project are tracked.

**Capture window (owner's decision):** only changes that appear while Claude is working on a reply count — from the user's message (`UserPromptSubmit`) to the end of Claude's reply (`Stop`). The user's own edits between turns, `git pull`/checkout, and cloud-sync changes outside that window are never recorded.

Dedup keys: claude.ai URL for published artifacts; project-relative path for files; `cwd + command` for servers.

**Linked entries (builder's call, agreed in principle):** when a published artifact's source file is a file already tracked (or detected in the same turn), they are **one entry**: type becomes `artifact`, the row shows the claude.ai URL as primary location and the file path as secondary, actions include both Copy link and Copy path. Claude is asked about it once, not twice. If `html` is disabled but `artifact` is enabled, the merged entry is still shown (it is an artifact).

**Bulk output (builder's call):** if one turn produces many new files of the same type in one directory (threshold ~5, e.g. a script generating 74 level files or a folder of PNGs), they become **one group entry** — "`<dir>/` · N files" — with one description and one change line per session. The dashboard row shows the file count; expanded view lists the files (collapsed after ~10).

### Classification, descriptions, change notes (Claude, once per item per session)
At `Stop`, if there are pending candidates (new, or changed in this session and not yet noted in this session), the hook **blocks once** (`{"decision":"block","reason": …}`) with a short instruction listing the candidates and the exact command to record them, e.g.:

```
python3 "<plugin-root>/scripts/shelfie.py" note <id> --artifact yes \
  --title "Northwind — onboarding agent brief" \
  --desc "Offer → Dropbox agent design for the client, with open questions Q1–Q14." \
  --change "Added the Fargate scheduled-task section"
```

- New item: Claude sets `--artifact yes|no`, title, description. (`no` → `ignored`.)
- Changed item: Claude writes one `--change` line (and may update the description).
- Several items can be noted in one command or a few commands.
- **Once per item per session:** after an item has a note for the current session, further edits in that session do not ask again. Result: one history line per session, not one per save.
- Loop safety: never block when `stop_hook_active` is true. If Claude doesn't comply, candidates stay pending and are asked about at the next natural stop.
- Ignored items are not asked about again when they change.

### First-run & config
- `SessionStart` hook: if `.shelfie/config.json` is missing, inject `additionalContext` telling Claude to ask the user which formats to track (default all) and run `shelfie.py setup --formats …`. Until configured, nothing is captured.
- **Permission for the `note` command (owner's decision):** during setup Claude also asks the user for consent to add an allow rule for Shelfie's own command to the project's `.claude/settings.local.json` (personal, not committed). With consent, `setup` adds exactly that one rule (merging into existing JSON, never removing anything). Without consent, Shelfie still works but each note triggers the normal permission prompt; README explains this. This is the only file outside `.shelfie/` Shelfie ever modifies.
- Changing formats later: `/shelfie formats` → `shelfie.py formats --enable … --disable …`. Disabling a format stops capture for it; existing entries of that format stay in the registry but are hidden from the dashboard.

### Dashboard generation
Regenerated by `shelfie.py render` after every registry write, and by `/shelfie`. Single self-contained HTML (inline CSS/JS/SVG icons, registry embedded as JSON). No external network requests.

### Time
All timestamps stored as ISO-8601 with local UTC offset; displayed in local time.

## 8. Constraints

- Hooks must be fast: `PostToolUse` handlers should finish in well under 200 ms; the `Stop` scan should stay fast on typical projects (cap/skip huge directories).
- Python 3 stdlib only; must run on stock macOS `python3`.
- Must work in both the Claude Code CLI and the desktop app's Code tab. Tool names differ between environments (desktop-only tools like the artifact publisher and preview server); matchers must cover both and degrade silently where a tool doesn't exist.
- Never write into the plugin directory; all state in `<project>/.shelfie/` (sole exception: the consented allow rule in `.claude/settings.local.json`).
- Registry writes must be safe against concurrent sessions in the same project (atomic write via temp file + rename, simple lock).

## 9. Repo & publishing

- Local path: `~/Documents/shelfie`. Public repo under the owner's personal GitHub account.
- README in English: what it is, the screenshot, install commands, formats, commands, how classification works, privacy note (everything stays local in `.shelfie/`).

## 10. Left to the builder

- Exact registry/config JSON schema, entry id format.
- The precise dev-server detection heuristics and port parsing.
- Exact wording of the Stop-hook instruction (must be short).
- Test approach (expected: unit tests for registry/scan/hook payload handling using fixture payloads; a manual end-to-end check in a scratch project).
- Licence (suggest MIT).
- Whether `.shelfie/` should be suggested for `.gitignore` (mention in README, don't modify user files automatically).
- Handling of renames (v1 may treat as missing + new).
