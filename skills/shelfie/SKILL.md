---
name: shelfie
description: Open or manage this project's Shelfie artifact log. Use for "/shelfie", "show my artifacts", "open the artifact log", "where is the thing you made last week", "which formats does shelfie track", "stop tracking PDFs", or restoring something Shelfie ignored.
argument-hint: "[formats | ignored | restore <id> | ignore <id> | setup]"
---

# Shelfie

Shelfie logs the artifacts Claude makes in this project into `.shelfie/` and renders a read-only dashboard at `.shelfie/shelfie.html`. All commands go through the project launcher `.shelfie/bin/shelfie`, run from the project root.

If `.shelfie/bin/shelfie` does not exist, Shelfie is not set up yet: do the **setup** flow below first.

Arguments: `$ARGUMENTS`

## No arguments — open the dashboard

Run `.shelfie/bin/shelfie open`. Tell the user the printed path in one line (they can also open it from Finder).

## `formats` — change what is tracked

1. Run `.shelfie/bin/shelfie formats` and show the list (✓ = tracked).
2. Ask what to change, unless the user already said.
3. Run `.shelfie/bin/shelfie formats --enable <keys> --disable <keys>` (comma-separated keys: artifact, html, pdf, md, doc, slides, sheet, server, image). Disabling a format stops tracking it and hides its entries; nothing is deleted.

## `ignored` — see what Shelfie filtered out

Run `.shelfie/bin/shelfie list --ignored` and show the items briefly.

## `restore <id>` / `ignore <id>`

Run `.shelfie/bin/shelfie restore <id>` or `.shelfie/bin/shelfie ignore <id>`. A restored item without a description will be asked about at the end of your next reply.

## `setup`

Ask the user:
1. Which formats to track — Claude artifact, HTML, PDF, Markdown, Doc, Slides, Sheet, Local server, Image. Default: all.
2. Whether Shelfie may record its notes without permission prompts — this adds one allow rule for `.shelfie/bin/shelfie` to `.claude/settings.local.json` (personal, not committed).

Then run `"${CLAUDE_PLUGIN_ROOT}/bin/shelfie" setup --formats all|<keys> --allow-permission yes|no` (if `CLAUDE_PLUGIN_ROOT` is not set in your shell, use the path from the Shelfie setup note in your context, or the existing `.shelfie/bin/shelfie setup …`).
