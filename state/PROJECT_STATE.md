# PROJECT_STATE (days)

date: 2026-10-09
last round: DAYS-PUBLIC-GITHUB-PUBLISH
executor: Codex; user owns the game client

## Current result
- User originally asked to start translation and create a dedicated GitHub project with easy Windows EXE installers/uninstaller and a Linux AppImage.
- Built 24/2,556 visible Days entries (0.939%); cthd000 contains 332 untouched entries. Not a full translation.
- Segoe UI Bold 24px; 76 contextual Arabic forms; 178 joining checks pass, minimum ink 125/128.
- 92 original CTD round-trips pass. IDs, layouts, line counts and all untouched messages preserved.
- Safe archive transplant preserves all 2,024 records, including 57 unknown entries lost by direct OpenKH hed patch. Only three replacement records change, original PKG prefix remains byte-identical. Encoded replacement blocks re-extracted and SHA256 verified.
- Public desktop payload: format 2 XOR differences against the owned original encoded blocks, compressed to 49,335 bytes. Reconstructed tail hashes match the same verified archive. Neither full archives nor raw replacement blocks are distributed.
- Electron desktop app prepared: Arabic navy/gold UI, Steam library detection, local patch, immutable original backups, SHA256 gates, install/uninstall, transaction rollback and interrupted-operation recovery. Seven fixture tests pass.
- Windows EXEs and Linux x64 AppImage built successfully in GitHub Actions run 37930980259; all seven installer fixture tests pass on both operating systems.
- User supplied exelight7/KH385-2FM_AR and explicitly chose PUBLIC publication after visibility was checked. Initial remote main contains GPL-3.0 LICENSE only. Public code/delta uploaded at commit 2969c118f2d627a75fa6ee11b97d78da0a48697e. Public prerelease v0.1.0 published with Setup/Uninstall EXEs, AppImage and SHA256SUMS; no browser sign-in needed for connector upload.

## Installed and verified
- Original live game archives unchanged; no live installation performed.
- In-game Arabic display, timing, position and Linux/Proton compatibility remain unverified.
- Backup for installed app lives under Image/.days-arabic-backup; retains original files on uninstall.

## Frozen choices and gates
- Segoe UI Bold remains the chosen font.
- Keep this project independent from KH1/KH2/Re:coded projects.
- Build the requested packages; do not infer approval to overwrite the live game archives from the packaging request.
- User runs the first 24 entries and provides in-game evidence before broadening asset injection.
- Never install out/first-dialogue/patched: that intermediate OpenKH output drops 57 entries.

## Artifacts
- translation/first_dialogue.json; translation/days-glossary.md
- out/first-dialogue/manifest.json and package-manifest.json
- out/first-dialogue/preview.png: current 24-entry offline atlas preview
- installer/: application, compact patch, test fixtures and package-lock
- .github/workflows/build.yml: Windows + Linux packages, automatic prerelease on first successful main build for each version
- out/apps/installer-preview.png
- technical/test_app_full_archive.cjs: disposable full-archive install/uninstall check

## History
- 2026-10-03: initial read-only recon.
- 2026-10-09: discovered LittleBitUA CTD/font support; first 3 narration entries built.
- 2026-10-09: user rejected disconnected preview; clipped overlapping interior outlines at shared joining boundaries. Old minimum join ink 51/128 improved to 125/128. Earlier 3-entry preview retained under before-join-fix.
- 2026-10-09: expanded first dialogue to 24 entries, added desktop packaging and private GitHub publishing preparation.

- 2026-10-09: owner explicitly chose PUBLIC repository exelight7/KH385-2FM_AR. Converted raw tail to an XOR delta against owned files before upload; updated installer release links.

- Public format 2 full-size disposable archive install/uninstall passed. All source/target archive hashes matched; live game files unchanged.

- Published release: https://github.com/exelight7/KH385-2FM_AR/releases/tag/v0.1.0
- Workflow run 37930980259: Windows, Linux and release jobs all SUCCESS. Linux runtime/gameplay still unverified.
