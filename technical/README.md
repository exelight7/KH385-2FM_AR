# Build inputs

The repository includes the compact, verified patch so desktop packaging does not need extracted game assets.

Rebuilding the translation itself requires an owned, matching Steam installation, Python 3.12 with Pillow/numpy/arabic-reshaper/python-bidi, Node.js, OpenKH and LittleBitUA's tool. Source game SHA256 values are recorded in `installer/patch/manifest.json`.

1. Clone `https://github.com/LittleBitUA/KINGDOM-HEARTS-LOCALIZATION-TOOL.git` to `technical/tools/kh-localization-tool`, then checkout `7cba46cb308d4a9498618cb6d3c1c2d093fdc710`.
2. Extract Mare into `technical/extracted_mare` and the companion archives used by the 92-file parser check into `technical/extracted`, preserving `original/uk/...` paths. These directories must stay local and ignored.
3. Set `OPENKH_IDXIMG` to the absolute path of `OpenKh.Command.IdxImg.exe`. The Windows Segoe UI Bold font must exist at `C:/Windows/Fonts/segoeuib.ttf`.
4. Run `python technical/build_first_dialogue.py`.
5. Use OpenKH `hed patch` on the installed Mare.pkg, with `out/first-dialogue/payload` as input and `out/first-dialogue/patched` as output. This is an intermediate encoding step only: its HED drops unknown entries, so never install it.
6. Run `python technical/package_first_dialogue.py` to transplant the three verified encoded blocks into copies of the original archives while preserving every original record and the original PKG prefix.
7. Run `python technical/export_installer_patch.py` to export XOR differences against owned original archive blocks and the HED changes to `installer/patch`.
8. Run `node technical/test_app_full_archive.cjs` to test the actual patch on a disposable copy. This checks full-size install/restore hashes and that the live game's hashes remain unchanged. It does not launch or modify the installed game.

Game rendering remains a separate human verification gate. Font preview evidence is offline only. Keep all original backups, full archives, extracts and third-party tool clones out of GitHub.
