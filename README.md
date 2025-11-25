## Blender BeamNG CDAE Addon

Addon for [Blender 4.5/5.0](https://www.blender.org/) adding support for [BeamNG](https://www.beamng.com/game/)’s model and material formats.\
This addon mainly targets Blender 5.0.

[Wiki (WIP)](https://github.com/Grille/Blender_BeamNG_CDAE/wiki)

### Features

- #### **DAE (Collada)**
  Export only, produces a .dae optimized for BeamNG.

  |  | Export | Import |
  | --- | --- | --- |
  | Mesh | ✅ Functional | ➖ |
  | Animations | ✅ Functional | ➖ |

---
- #### **CDAE**
  WIP
  
  |  | Export | Import |
  | --- | --- | --- |
  | Mesh | ❌ Partial | ✅ Functional |
  | Animations | ❌ Planned | ➖ |

---
- #### **Materials**
  Full support for the export of V1.5 (PBR) Materials.
  V1 is only usable for very basic materials.\
  While the exporter can parse Blender's built-in nodes to some extent, you should use the [Nodes](https://github.com/Grille/Blender_BeamNG_CDAE/wiki/Material-Tree) provided by this addon for best effect.
---

### Supported/Tested Blender Versions
- 5.0
- 4.5
- 4.4

### Collada Subset
While this addon contains Collada, it’s only the subset used by BeamNG, for other use cases this addon is probably of limited use.
- **Nodes**
  - Translation & Rotation: Matrix4x4
- **Mesh**
  - Positions
  - Normals
  - 2 UV Maps (Optional)
  - Int/RGBA Colors maped to Vec4 (Optional)
- **Materials**
  - Names Only
- **Animations**
  - Keyframes: Matrix4x4

### Resources
- [BeamNG.CDAE Specifications](https://documentation.beamng.com/modding/file_formats/cdae/)
- [Torque3D.DTS Specifications](https://torquegameengines.github.io/T3D-Documentation/content/documentation/Artist%20Guide/Formats/dts_format.html)
