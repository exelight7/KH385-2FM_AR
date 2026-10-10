# Build inputs

Desktop packaging uses the verified compact patch and does not require game extracts.

Rebuilding version 1.0.1 requires an owned matching Steam copy, Python 3.12 (Pillow, numpy, arabic-reshaper, python-bidi), Node.js, OpenKH and LittleBitUA's tool. Expected original hashes are in installer/patch/manifest.json. Extracted game files stay local and read-only.

1. Clone LittleBitUA/KINGDOM-HEARTS-LOCALIZATION-TOOL to technical/tools/kh-localization-tool and checkout 7cba46cb308d4a9498618cb6d3c1c2d093fdc710.
2. Extract Mare into technical/extracted_mare and companion archives into technical/extracted, retaining original/uk paths. The parser verifies all 92 CTDs byte-for-byte. The supplied IBM Plex Sans Arabic Medium font and OFL license are in font-rtl/fonts.
3. Run python technical/quality_review_v100.py to check the frozen1.0.0 review provenance, then python technical/build_v030.py --version 1.0.1. The historical builder name is shared by versions. The quality audit verifies the fresh review hash chain and recorded correction history. The builder requires both complete review reports per file, validates the second review output hash, verifies source English/IDs against original CTDs, preserves text commands and produces out/v1.0.1/payload. --draft-check bypasses the review gate for local investigation only; never release that output.
4. Set OPENKH_IDXIMG to OpenKh.Command.IdxImg.exe and DAYS_BUILD_DIR to the absolute out/v1.0.1 directory. The packager finds and verifies original archives, preferring the original backup when a patch is installed.
5. Use OpenKH hed patch on the verified original Mare.pkg, with out/v1.0.1/payload and output out/v1.0.1/patched. Never install this intermediate HED; OpenKH drops 57 unknown records.
6. Run python technical/package_first_dialogue.py. Despite its historical name it reads DAYS_BUILD_DIR, transplants all 136 verified replacements, preserves all 2024 records, and verifies the unchanged original PKG prefix and decrypted replacement hashes.
7. Run python technical/export_installer_patch.py with the same DAYS_BUILD_DIR. It checks installer/build version agreement, exports the XOR delta and permits direct upgrades from the saved 0.1.0, 0.2.0, 0.3.0, 0.4.0, 0.4.1 and 1.0.0 hashes.
8. Run npm test in installer, then node technical/test_app_full_archive.cjs. The latter uses disposable full-size copies to verify install/restore and checks that live files remain unchanged.
9. Build Windows EXE and Linux AppImage through installer/package.json or GitHub Actions. Capture the UI with installer/preview.cjs; it never installs the patch or launches the game.

The user authorized installing the tested patch into the live game. Each installed version has a separate hash receipt. In-game rendering remains human verification; automated archive checks and offline font previews do not prove it. Do not launch the game automatically. Never publish original backups, whole archives, extracts or third-party tool clones.

1.0.0 freshly reviews all nine CTDs twice and retains 25 translated labels in two native L2D UI containers. build_days_ui_art.py typesets the supplied Plex font inside original SP2 UV rectangles; file lengths, geometry, other textures and pixels outside labels are asserted unchanged. inspect_days_art.py only exports local previews. No original artwork is published. The CTD metric excludes 95 preserved movie resource keys from the legacy2556 inventory; it is2461/2461, separate from incomplete artwork localization and in-game verification.


1.0.1 keeps all nine translation files byte-identical to1.0.0 and inherits its two linguistic reviews. It does not claim fresh review passes. Font joins now occupy x0 and COD.width-1, inside sampled quads; glyph body bounds are included in the advance. The preview crops glyphs to COD.width, correcting the older full32-pixel preview. verify_font_rendering.py compares frozen1.0.0 and1.0.1 payloads (both required locally), scans1334 distinct adjacent Arabic pairs per font, and writes offline evidence. It assumes zero extra engine spacing; current in-game validation remains pending. The original Days20-byte CTD layouts stay byte-identical.

Main-menu image labels use40px Plex, secondary options28px, and headers26px, with native anchors/common baselines. Stable alpha>80 ink height is asserted at most four pixels above the original for every label. SP2 records, geometry and original alpha maxima remain unchanged. Omitting sprite79 restores original DEVELOPED BY/SQUARE ENIX pixels. There are24 translated image labels in1.0.1. User screenshots confirm1.0.0 Arabic rendering but expose the defects addressed here; no automated game launch occurs.
