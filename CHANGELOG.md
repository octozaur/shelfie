# Changelog

All notable changes to Shelfie are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [0.1.1] — 2026-11-02

### Fixed
- The CLI entry point moved from `bin/shelfie` to `scripts/shelfie`. claude.ai rejects plugins with a top-level `bin/` directory, so 0.1.0 could not be added to an organization's plugin catalog there. Hooks, the setup instructions and the project launcher now point to the new path. Nothing changes inside a project: `.shelfie/bin/shelfie` and its permission rule stay where they were, and an existing launcher is updated at the next session start.
- A layout test now fails if `bin/` comes back or a hook points at a file that does not exist.

## [0.1.0] — 2026-10-30

First public release.

### Added
- Automatic capture of artifacts Claude makes in a project: pages published to claude.ai, HTML, PDF, Markdown, Doc, Slides, Sheet and Image files, and local servers.
- Only changes made while Claude works on a reply are recorded; your own edits, `git pull` and sync are ignored.
- Claude classifies each new item (deliverable or not) and writes a title, a short description and one change line per session.
- Static, read-only dashboard at `.shelfie/shelfie.html`: activity map, timeline by day / week / month, search, type filters, change history, copy link / path / command.
- Bursts of same-type files in one folder are grouped into one entry; a file and its claude.ai page are one entry.
- `/shelfie` skill: open the dashboard, change tracked formats, see and restore ignored items.
- First-run setup with an optional, narrowly scoped permission rule for Shelfie's own `note` command.

[0.1.1]: https://github.com/octozaur/shelfie/releases/tag/v0.1.1
[0.1.0]: https://github.com/octozaur/shelfie/releases/tag/v0.1.0
