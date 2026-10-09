# PROJECT_MASTER (days)

date: 2026-10-09
round: DAYS-OPENING-24-DESKTOP-APP

Source of current state: PROJECT_STATE.md. Live game unchanged; nothing installed.

Translation: 24/2,556 visible entries, 76 Arabic forms. Segoe UI Bold 24px. Seven app fixture tests pass; real in-game display unverified. Owner explicitly selected public publication at exelight7/KH385-2FM_AR. Linux AppImage workflow prepared but not executed. Desktop Windows artifacts go under out/apps.

Safe distribution includes a compact XOR delta against owned original blocks and HED record changes. Originals are checked by SHA256, backed up, then used to generate and verify the patched archive before switching files. Uninstall restores the verified backup. No hardcoded credentials.

Never install the intermediate out/first-dialogue/patched archive: it lacks 57 unknown entries. Verified standalone archives are under out/first-dialogue/archives, but should not be published because they contain the original game data.

User owns runtime verification. Obtain evidence of the first translated conversation before increasing injection batches.
