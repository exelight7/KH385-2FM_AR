# PROJECT_STATE (days)

date: 2026-10-10
round: DAYS-STORY-V030
executor: Codex; user owns and runs the game client

## Current result
- User explicitly requested at least 60% translation and installation, and publishing version 0.3.0 in the public repository exelight7/KH385-2FM_AR.
- 1616/2556 enumerated text records translated and installed (63.224%). Five story/narration CTDs: cthd000, cthd050, cthd100, cthd300, cthd800. The denominator remains unchanged from previous releases; image text and video duration are not counted.
- All 1616 records received two independent complete source-English reviews, with corrections/reasons and hashes in translation/v0.3.0/reviews. Final review hashes use UTF-8 with LF normalization to work on both Windows and Linux. No unresolved linguistic items recorded.
- New font: exact IBM Plex Sans Arabic Medium file used by current KH2FM project, SHA256 b60e43e9a2f454f3ef705bb29bb751a9eb915de14898dc0513a2d80d0d3e54f0. SIL OFL included in source and application. 125 Arabic/Unicode forms plus 4 ASCII punctuation/blank cells, 129 total donor cells in each native font. Half-pixel outline for eventfont; original RGBA menu format preserved. English cells unchanged. 212 joins across both fonts pass; no relative width warnings.
- CTD source English, IDs, layouts, untranslated entries, newline counts, blank-line positions and commands verified. All 92 originals roundtrip byte-exact. 1568 inline EN IDs updated across121 EXIA2 files with schedule timing/attributes/other languages retained. 44 original inline EN fields differ from canonical CTD (many empty or spelling variants); canonical original CTD is the translation reference.
- Archive preserves all2024 records including57 unknown records;130 changed assets re-extracted and SHA256 matched. Original entire PKG prefix unchanged. XORdelta1111942 compressed bytes; raw35583696 bytes.
- Eleven fixture tests pass locally including previous and legacy upgrade, rollback, crash recovery, corrupt backup, corrupt patch and concurrent external changes. The final full-size0.2→0.3 install/restore test passes with exact target/original hashes and no live changes during the test.

## Installed and visual verification
- Codex installed0.3.0 after the user's explicit installation request, after the final disposable-copy test, with running-game checks. Receipt technical/verification/v0.3.0-install.json proves final target hashes and unchanged original backups. No game launched.
- User's supplied screenshot proves Arabic appeared in0.2.0. New0.3.0 font/layout has0 visually verified rows. Offline preview is not an in-game screenshot.
- Menus, diaries and image title cards remain English. Unreviewed full-project drafts remain local and are excluded from0.3.0.
- Read-only video audit found no movie reencoding or movie writes in the patch pipeline. User has not compared the same scene after uninstall; visual quality cause remains unconfirmed.
- CI/release publication pending. PROJECT_PROGRESS.json will record actual published status and download hashes when complete.

## Rules
- Never launch the game automatically. Human screenshot verification remains separate from archive installation checks.
- Derive builds only from SHA256-verified original backups/extracts. Never install direct OpenKH intermediate output: it drops57 entries.
- Preserve Image/.days-arabic-backup. Use0.3 installer/uninstaller to restore original Mare.hed/pkg.
- Source of truth: PROJECT_PROGRESS.json, installer/patch/manifest.json and technical/verification/v0.3.0-*.json.
