## Blender BeamNG CDAE Addon

A (WIP) [BeamNG](https://www.beamng.com/game/) specific Blender addon to export to cdae/dae file formats.

Since [BeamNG's](https://www.beamng.com/game/) CDAE now has format [specifications](https://documentation.beamng.com/modding/file_formats/cdae/), as well as blender announcing to drop collada support with 5.0, I thought a dedicated addon might become useful.

### Features
| Data | Import | Export |
| --- | --- | --- |
| CDAE.Mesh | ✔️ Functional | ⚠️ Partial |
| CDAE.Animations | ➖ | ❌ Planned |
| CDA.Mesh | ➖ | ⚠️ Partial |
| CDA.Animations | ➖ | ❌ Planned |
| Main.Materials.JSON | ➖ | ⚠️ Partial |

### Materials
Material placeholders can be generated at the export location, existing `main.materials.json` files can be handled/merged based on user preference.\
I would like to export the material node graph as BeamNG materials in the future.

### Supported/Tested Blender Versions
- 4.4
- 4.5

### Resources
- [CDAE Specifications](https://documentation.beamng.com/modding/file_formats/cdae/)