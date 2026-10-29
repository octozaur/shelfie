# Changelog

All notable changes to Shelfie are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

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

[0.1.0]: https://github.com/octozaur/shelfie/releases/tag/v0.1.0
