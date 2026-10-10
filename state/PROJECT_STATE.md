# PROJECT_STATE (days)

date: 2026-10-10
round: DAYS-QUALITY-V040

- 0.4.0 reviews all 1616 translated story, intro and narration records twice independently against canonical original English. 64 distinct records corrected for fidelity, grammar, spelling, pronouns, tense and consistent phrasing. Every change has before/after/source/reasons in translation/v0.4.0/quality-report.json. Frozen 0.3.0 text retained.
- Coverage remains 1616/2556 (63.224%). Menus, diaries and image title cards remain English; unreviewed drafts excluded. No unresolved linguistic items in the two reviews.
- Source English, IDs, layouts, commands, newline/blank positions preserved. 92 original CTDs roundtrip byte-exact. 1568 inline IDs updated across 121 XML schedules without timing or other-language changes. 44 inline original English fields differ from canonical CTD; canonical CTD remains the translation reference.
- All 2024 Mare entries preserved, including 57 unknown entries. All 130 replacements re-extracted and SHA256 matched; original PKG prefix unchanged. No movie reencoding.
- Four font assets are byte-identical to 0.3.0: IBM Plex Sans Arabic Medium from KH2FM, Plex spacing/punctuation. 212 join checks pass; 0 relative-width warnings. This is offline verification, not in-game proof.
- 12 installer fixture tests pass. Full-size 0.3.0 to 0.4.0 upgrade and uninstall restore exact target/original hashes on disposable copies; live files unchanged during this test.
- 0.4.0 installed in the live game after copy tests and running-game checks. technical/verification/v0.4.0-install.json verifies target and unchanged original backups. Game not launched. Direct upgrade recognizes 0.1.0/0.2.0/0.3.0.
- User screenshot verifies Arabic in 0.2.0 only. Current font/layout has 0 visually verified rows. User has not compared the same scene after uninstall; reported video-quality cause unconfirmed.
- Public v0.4.0 prerelease published. All three CI jobs succeeded, with 12 tests per OS. Public EXE/AppImage downloads and platform headers verified against SHA256SUMS and GitHub digests. https://github.com/exelight7/KH385-2FM_AR/actions/runs/38025887258

Never launch the game automatically. Preserve Image/.days-arabic-backup. Build only from verified originals, never install intermediate OpenKH output (it omits 57 entries). Source of truth: PROJECT_PROGRESS.json, installer/patch/manifest.json and versioned technical/verification proofs.
