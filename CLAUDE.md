# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Blender addon (targets Blender 5.x, min 4.5) for BeamNG.drive's model formats (`.cdae`, Collada `.dae`) and `*.materials.json` materials. The repo folder is the installed addon itself (`scripts/addons/grille_beamng_cdae`).

## Commands

Everything imports `bpy`, so tests run inside Blender. `blender` is not on PATH; it lives at `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`.

```powershell
# all tests (~2s)
& $blender -b --factory-startup --python tests/run_tests.py

# all tests + real-file tests: reads/rewrites every .cdae and *.materials.json under the dir (~45s)
& $blender -b --factory-startup --python tests/run_tests.py -- "$env:LOCALAPPDATA\BeamNG\BeamNG.drive\current"

# single test
& $blender -b --factory-startup --python-expr "import sys, unittest; sys.path[:0] = ['tests', 'src', 'modules']; unittest.main(module=None, argv=['x', 'test_material.MaterialDictTest.test_legacy_key_aliases'], exit=False)"
```

- The BeamNG dir argument sets `BEAMNG_SAMPLES_DIR`; tests depending on it skip otherwise. Use those files to settle format questions empirically.
- Test modules that create custom nodes call `addon.register()` in `setUpModule`.
- `python setup.py` installs `msgpack` into `modules/` and `fake-bpy-module` stubs into `bpy/` (for pyright only). `python build.py` zips the addon.
- Pyright runs in strict mode (`.vscode/settings.json`); the stubs type Blender enum properties as `Literal`s.

## Architecture

The root `__init__.py` puts `src/` and `modules/` on `sys.path` and imports `grille_cdae.addon` (register/unregister). Code is split into:

- `grille_cdae/common` — shared base layer, star-imported everywhere (`from grille_cdae.common import *`). Includes `PropertyInfoFactory`/`PropertyInfoGroup`: Blender properties are declared once, registered with the `grille_beamng_cdae_` prefix, read via `Pinfo.prop[obj]` and drawn via `UILayoutCtx.prop(pinfo.prop)`.
- `grille_cdae/beamng/cdae` — model formats. `CdaeV31` is the in-memory file; `io/` has readers/writers (cdae = msgpack + packed binary vectors, dae, dts). `builder.py` goes Blender → CDAE, `parser.py` CDAE → Blender.
- `grille_cdae/beamng/material` — material JSON model and its conversion to/from node trees.
- `grille_cdae/blender` — operators, panels, properties and the custom shader nodes.

### Materials

- **Model** (`material.py`): thin wrappers over the raw JSON dict with `DictProperty` descriptors. A key is omitted when its value equals the default, and defaults are BeamNG's *file* defaults (value when the key is absent), not the BeamNG material editor's defaults. Texture sockets share uniform keys (`map`, `value`, `uv`, `instance`, `vertex`) mapped to real JSON keys by `material_socket_info.py`. A JSON key may be a tuple `(primary, *legacy aliases)`: reads take the first present, writes set the primary and drop the aliases.
- Material 1.0 and 1.5 reuse some JSON keys for different concepts; duplicate mappings in the model are intentional.
- **Field tables** (`node_fields.py`) map node sockets ↔ model paths (never JSON keys) and drive both directions: `material_builder.py` (node tree → JSON) and `material_parser.py` (JSON → node tree, plus converting Principled/Diffuse BSDF trees to BeamNG nodes).
- Export always builds a fresh, clean dict; import → export is deliberately lossy (only what the node tree represents survives). Don't merge into existing JSON entries or store extra data on node trees.
- `NodeWalker` (`blender/node_walker.py`) follows links through groups and reroutes and ignores muted links.

### Custom shader nodes

- `blender/shader_nodes.py`: every node is a `ShaderNodeCustomGroup` whose group is built by `create_node_group` with the `shader_node_builder.py` DSL (`a * b >> out`, `NodeSignature` for bundles/closures). Groups are shared by name `.{bl_idname}_v{ng_version_mayor}`, so **bump `ng_version_mayor` whenever a node's interface changes** (sockets renamed, added, removed or retyped; node trees need fixing after the update). Outdated nodes show an Update button that carries links and values over by socket name; declare renamed sockets in `get_socket_renames`. Bump `ng_version_minor` for internal changes (group internals, socket shapes, defaults), which let nodes update without problems; `update_node_groups` applies those on file load.
- Nodes parametrised by `Operation` (e.g. `BeamRGBAMath`) are internal building blocks, in the add menu only for debugging. `Operation` is deliberately loose; an unsupported operation throwing is a programmer error, not something to validate.

## Conventions

- Commit each finished step on `main` without asking (tests passing). Don't push unless asked.
- Don't delete unused helpers or commented-out code; most of it is kept on purpose. Fix it instead if it's broken.
- Prefer enums/constants (`enums.py`, per-node `Sockets` enums) over string literals for socket names and identifiers.
