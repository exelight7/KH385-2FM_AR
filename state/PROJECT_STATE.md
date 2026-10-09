# PROJECT_STATE (days)

date: 2026-10-09
last round: DAYS-DAY7-V020
executor: Codex; user owns game client

## Current result
- User selected complete Day 7 and version 0.2.0. Public publishing to exelight7/KH385-2FM_AR remains authorized.
- User reports 0.1.0 installer success but English dialogue. Read-only SHA256 checks prove live Mare matches released 0.1.0 exactly; backup matches the original pair.
- Independent chapter trace: CHP record2 offset200 day7 references THD sequences2,3,188: hd002 (silent), hd803 (4 welcome messages), hd003 (4 narration messages). Menu selector is Number XIV.
- All 8/8 Day7 dialogue messages translated. Four welcome rows in cthd800 were missing in0.1.0. Their omission may explain the report; runtime root cause is not yet confirmed.
- Cumulative28/2556 visible rows (1.095%); 673 untouched rows in the two modified CTDs. Chapter labels and image title cards remain English.
- CTD and embedded English EXIA2 Text fields both updated for28 rows across4 schedules. XML timing, IDs, other languages and nonText content unchanged. Runtime use of inline Text remains unconfirmed.
- Segoe UI Bold24px,81 forms,233 joins,min125/128;92 original CTD byteexact roundtrips.
- Archive transplant preserves2024 records including57 unknown;8 modified records; rebuilt block extraction hashes match. Public XORdelta78778 bytes.
- App0.2 supports direct0.1→0.2 upgrade, keeps original backup, restores originals on uninstall.10 fixture tests pass including upgrade rollback and crash recovery.
- Full size0.1 to0.2 upgrade and restore PASS; all expected archive hashes match; live0.1 files unchanged. GitHubActions run37934072172: Windows, Linux, release allSUCCESS. v0.2.0 public prerelease published; downloaded all assets and verified SHA256 and EXE/AppImage headers.

## Installed and verified
- Live game remains0.1.0 as installed by user; Codex has not installed0.2 or launched game.
- Ingame verified rows:0. Screenshot needed on Number XIV first line: أبشروا يا أصدقائي.
- Backup: Image/.days-arabic-backup. Use0.2 installer/uninstaller after upgrade.

## Frozen choices
- Font Segoe UI Bold; glossary shared with KH names; Xion=شيون.
- Builds derive only from verified originals (backup preferred); never from patched live archive.
- Never install direct OpenKH patched output; it loses57 records.
- User runs the game. Build/release tests use disposable copies.

## Evidence
- technical/verification/day7-scope.json
- technical/verify_day7.py
- technical/verification/v0.1.0-manifest.json
- out/first-dialogue/manifest.json and package-manifest.json
- installer/patch/manifest.json

- Release: https://github.com/exelight7/KH385-2FM_AR/releases/tag/v0.2.0
- Release source commit:5ca9bf55ba91ce61b04734c95c29fd4112002d26.
