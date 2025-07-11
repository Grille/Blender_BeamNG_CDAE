## Blender BeamNG CDAE Addon

Since [BeamNG's](https://www.beamng.com/game/) CDAE is now a proper file format with [specifications](https://documentation.beamng.com/modding/file_formats/cdae/), I thought it might be useful to be able Import/Export it directly from blender.\
Especially since Collada is deprecated and might get removed in the future.\
It’s still very WIP, Import is very rudimentary and will give you barely anything useful. And Export only works for the scene tree.

### Features
| Data | Import | Export |
| --- | --- | --- |
| CDAE.Mesh | ⚠️ | ⚠️ |
| CDA.Mesh | ❌ | ⚠️ |
| CDAE.Animations | ❌ | ❌ |
| CDA.Animations | ❌ | ❌ |
| Main.Materials.JSON | ❌ | ⚠️ |

### Planned Advanced Features
- Support for main.materials.json files at export location, merge materials with existing file if it exists.
- Scene tree based on Custom Properties
- Export of cdae animation data