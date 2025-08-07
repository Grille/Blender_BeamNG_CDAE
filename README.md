## Blender BeamNG CDAE Addon

A (WIP) [BeamNG](https://www.beamng.com/game/) specific Blender addon to export to cdae/dae file formats.

Since [BeamNG's](https://www.beamng.com/game/) CDAE now has format [specifications](https://documentation.beamng.com/modding/file_formats/cdae/), as well as blender announcing to drop collada support with 5.0, I thought a dedicated addon might become useful.

[Wiki (WIP)](https://github.com/Grille/Blender_BeamNG_CDAE/wiki)

### Features
| Data | Import | Export |
| --- | --- | --- |
| CDAE.Mesh | ✅ Functional | ❌ Partial |
| CDAE.Animations | ➖ | ❌ Planned |
| CDA.Mesh | ➖ | ✅ Functional |
| CDA.Animations | ➖ | ❌ Planned |
| Main.Materials.JSON | ➖ | ✅ Functional (PBR) |

### Models
DAE Export is mostly working as expected, CDAE is still WIP and won’t be loaded by BeamNG.\
Support for some special features like Animations or Skin-Meshes is still missing.

### Materials
With the help of specialized nodes, it is possible to build full v1.5 materials in blender.\
V1 can also be exported but support is still very lackluster.


### Supported/Tested Blender Versions
- 5.0 (Alpha)
- 4.5
- 4.4

### Resources
- [CDAE Specifications](https://documentation.beamng.com/modding/file_formats/cdae/)