# Days Arabic · 0.4.1

Date: 2026-10-10 / DAYS-TEXT-V041

- 2461/2461 translatable CTD rows completed. Legacy inventory2556 included95 movie resource keys; all95 stay verbatim. The corrected denominator is explicit, not an assertion of complete visual localization.
- Adds845 translated menu, diary/report and character rows. Two independent review passes completed; 55 distinct draft rows corrected. The1616 frozen story rows reuse their verified0.4.0 reviews with hash provenance; no new reread is claimed.
- Nine CTDs, four font assets,121 inline XML schedules and two UI containers:136 changed assets. Source IDs, layouts, commands, timing, blank-line positions and other-language schedules preserved.92 original CTDs roundtrip;1568 inline IDs updated.44 inline source-field discrepancies use canonical CTD English.
-25 native UI labels translated with IBM Plex Sans Arabic Medium. Original UVs, geometry, texture dimensions, alpha maximum and all pixels outside label rectangles preserved.136 font glyphs;216 connectivity checks;0 relative-width warnings.
-2024 archive records and57 unknown records preserved. Every replacement re-extracted and SHA256 matched; original PKG prefix unchanged. No movie reencoding. Reported video-quality cause remains unconfirmed.
-13 installer tests pass. Full-size upgrade/uninstall verification: True. Direct upgrade supports0.1.0/0.2.0/0.3.0/0.4.0.
-Live installed:True; current live version:0.4.1. No game launch. Current in-game font/menu/diary verification remains0 rows.
-Decorative English in artwork, including WINNER and OPERATIONS CLOSED FOR VACATION, remains. Publisher logos/credits retained; full artwork inventory still needed. Shared Re:coded menu labels/profiles included; Re:coded story and KH1 story excluded.
-Public release verified:False. Packaging pending.

Never launch the game automatically. Preserve Image/.days-arabic-backup and frozen earlier translations/proofs. Never install intermediate OpenKH output; it drops57 records. Sources of truth: PROJECT_PROGRESS.json, installer/patch/manifest.json, versioned verification files.
