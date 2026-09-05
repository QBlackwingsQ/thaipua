# AGENTS.md

Thai PUA font mapping and glyph composition tool. PySide6 GUI over a
GUI-free core that handles font I/O, encoding pipelines, and persistence.

## Quick reference

| Task | Command |
|---|---|
| Create venv | `uv venv --python 3.14` |
| Install deps | `uv sync` |
| Run GUI | `uv run python -m thaipua` |
| Format | `uv run ruff format .` |
| Lint | `uv run ruff check .` |
| Type-check | `uv run mypy .` |
| Test | `uv run pytest` |
| Bundle | `uv run pyside6-deploy -c pysidedeploy.spec` |

Python 3.14. Stack: `fontTools`, `pydantic`, `PySide6` (GUI only), `uv`.

## Project structure

```
src/thaipua/
  app.py + __main__.py  # Entry: uv run python -m thaipua → app.main
  core/                 # Backend. Depends only on stdlib + fontTools + pydantic.
    domain/             # Pure models (no Qt/fontTools/IO): thai, cluster
                        # (try_key), settings, layout, resolution, grid,
                        # pua_map, slots, errors
    font/               # fontTools adapters: workspace, composer, specs,
                        # ownership, map_validation, occupancy, cff_convert,
                        # alternates, bounding_box
    text/               # encoding (normalize_sara_am + encode/decode),
                        # file_codec, string_table, text_encoding
    fonttools/          # Settings file IO only (load/save_placement_settings)
    store/              # JsonStore ports + disk/memory backends
    layout.py           # Deterministic PUA layout engine
    session.py          # ProjectSession undo/redo
    commands.py         # DocumentCommand / DocumentSnapshot + coalescing
    pua_map.py          # PUA-map load/save + free-slot search
    constants.py        # PUA range, SARA_AM_REPLACEMENTS
    paths.py            # APP_DATA_DIR / ASSETS_DIR roots
    bootstrap.py        # ensure_app_data_dirs (mkdir-only)
  gui/
    main_window.py      # Top-level window, sole AppState mutator
    state.py            # GUI state container (PySide6-free)
    font_service.py     # ONLY owner of workspace/renderer/session (PySide6-free)
    rendering.py        # FontRenderer (preview + install)
    glyph_pen.py        # Glyph outline pen (PySide6-free)
    theme.py / icons.py # PySide6 allowed
    widgets/            # controls/glyph-grid/preview panes, toolbar, footer,
                        # occupancy + pua-mapping dialogs, tooltips
assets/fonts/           # Test fixtures (Sarabun-Regular.ttf)
data/                   # Runtime state. Never written to by tests.
tests/                  # unit/ (pure logic + fakes) + integration/ (font asset, FontService, Qt)
```

## Boundaries

### Always
- Route document/workspace mutations through `FontService.execute*` →
  `session.execute(label, mutate, coalesce_key)`. Panes emit signals;
  `MainWindow` alone mutates `AppState`.
- Keep these PySide6-free so they import without a `QApplication`:
  `core/`, `gui/state.py`, `gui/font_service.py`, `gui/glyph_pen.py`.
- Normalize `SARA AM U+0E33` to `NIKHAHIT U+0E4D` + `SARA AA U+0E32`
  before it reaches a mapping key.
- Run `ruff format --check .`, `ruff check .`, `mypy .`, and `pytest`
  before proposing a change complete.

### Ask first
- Changing the `layout.json` or settings schema version.
- Changing the composite glyph naming scheme (`thaipua_XXXX`).
- Adding a dependency, or adding PySide6 to a currently-free module.

### Never
- Mutate the user's source font file on disk.
- Introduce a modal dialog for codepoint conflicts.
- Commit generated `data/` state or bundled font binaries.

## Domain invariants

### Layout & PUA mapping
- `codepoint = base + ordinal`, where `base` is configurable and
  `ordinal = consonant_index * 60` (60-combo stride). Layout is deterministic —
  the same inputs must always produce the same codepoints.
- `layout.json` is authoritative. `pua_mapping.json` is a derived cache and
  may be regenerated from `layout.json` at any time.
- Conflicts surface as a footer warning, then resolve through
  `occupancy_dialog.py` via Override / Relocate / Remap.

### Fonts & rendering
- CFF (`.otf`) sources convert to TrueType **in memory** at load time.
- Composites use stable `thaipua_XXXX` names so reinstall replaces in place
  without breaking cmap or glyph order.
- Preview resolves through read-only `ComponentPlacement`.
- Grid refresh is debounced 300ms — required for slider performance.

### Settings & profiles
- Settings JSON keys: `version`, `metadata`, `marks` (offsets per role) and
  `consonants` (offsets, snap configs, substitutions).
- `layout.json` accepts versions 1–2; settings accept version 1. Any other
  version raises — do not silently upgrade or coerce.
- Profiles auto-match on `family_name` + `units_per_em`.

### Undo
- `ProjectSession` (in `core/`) owns the undo/redo stacks via
  `DocumentCommand` / `DocumentSnapshot`.
- Undo scope is the document only: layout + settings. Font binaries are
  transient artifacts and are rebuilt, not undone.
- Consecutive edits sharing a coalesce key (e.g. slider ticks) merge into one
  history step.

## Landmines

- Thai sets live only in `core/domain/thai.py` — never re-list codepoints.
  Cluster parsing lives only in `domain/cluster.try_key`. Only `ฬ` is
  `CONSONANT_PROTRUSION="ascender"`.
- Relocate targets the first free tail-zone slot past the canonical block.
  `validate_pua_map` blocks Save until conflicts are resolved.
- `U+0E4C` counts as a tone mark. Key order is below→above→tone; normalize
  mark order at every boundary. Tone variants of SARA AM fold via
  `SARA_AM_REPLACEMENTS`.
- The 11 hole combos longest-partial-match yet round-trip — not a bug.
- Save-Font defaults to `<stem>_pua.ttf`; installs always target `glyf`.
  Gate slot decisions on `classify_pua_slot` + `InstallResult.status`,
  never log text.
- Offset stack is global `marks` + `base_offsets` + `mark/combo_offsets`;
  `state.py` is pure `current_*`/`apply_*` transforms.
- Open/reload/approval-GC clear undo history. Layout files write eagerly;
  the font binary stays in memory until Save Font.

## Code style

- 4-space indent, 120-char lines, double quotes, `snake_case` functions and
  modules, `PascalCase` classes.
- Ruff ignores for Qt/fontTools camelCase are already configured in
  `pyproject.toml` — do not add per-file `noqa` for these.
- Module docstrings: one line. Method docstrings: imperative mood, describe
  the contract and any side effects. Skip docstrings on trivial members.

```python
def normalize_sara_am(content: str) -> str:
    """Rewrite SARA AM combinations into NIKHAHIT + SARA AA sequences."""
```

## Testing

- Integration tests use `SAMPLE_FONT_PATH` from `tests/conftest.py`.
- GUI tests stub dialog components — an unstubbed modal will hang the suite.
- Tests must not touch repo-root `data/`; use `tmp_path`.
- Run a single file: `uv run pytest tests/unit/test_layout.py -q`

## Commits & PRs

- Conventional Commits, imperative subject, ≤72 chars: `feat: add remap action`
- PR body states: scope, linked issue, schema/API impact, and
  screenshots or logs for any UI change.
- All checks in Quick reference must pass locally before opening the PR.
