# Days Arabic · 2.0.0

Date: 2026-10-31 / FINAL-200

- Built locally; not published. The release workflow publishes a regular release (not a prerelease) when version 2.0.0 reaches main. No git, gh or GitHub login was available here, so the push was not made.
- The 2.0.0 patch is byte-identical to the fourth test build installed in the live game on 2026-10-31 (receipt: technical/verification/v1.0.3-install.json), which the user tested. 1.0.3 was never published.
- Font: Noto Sans Arabic SemiBold 21px with a 0.75px rim for dialogue (20px for menus, no rim); IBM Plex SemiBold for ( ) / and the registered sign. Glyphs moved to free atlas cells with edge repeats, so they should look the same whether the engine crops quads to COD.width or draws whole cells.
- Offline bilinear check at 1x, 1.5x, 2x and 2.25x: 0 weak seams of 4002 per scale in each font, assuming cropped quads. User screenshots of earlier builds show no seams or stray marks in the shots supplied.
- 1.0.2's day-96 tiles (40 rows, 367 extra 28px cells) are not carried over, and no new day-96 screenshot has been supplied.
- Text: one full read and an automatic lint of 2461 rows found no misspelled word. Two agreement corrections are logged in translation/v2.0.0/corrections.json. Inherits the 1.0.0 reviews; no fresh bilingual review is claimed.
- The ctmn000 34000001 word order is fixed. Diary lines are rebalanced at build time. The GAME SETTINGS label is translated in days_theatre and recoded_theatre (25 image labels, 3 containers). 0 width warnings.
- Disposable full-size copies: install, upgrade from published 1.0.2 and uninstall all match expected hashes; live game hashes unchanged. 28 installer tests pass. Linux AppImage is built only by GitHub Actions.
- Decorative scene artwork is still English. Re:coded story/KH1/KH2 excluded.

Preserve the original Image/.days-arabic-backup and prior frozen proofs. Sources of truth: PROJECT_PROGRESS.json, installer/patch/manifest.json and versioned verification files.