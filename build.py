from pathlib import Path
import zipfile


root = Path(__file__).parent
output = root / "grille_beamng_cdae.zip"

include = [
    root / "__init__.py",
    root / "blender_manifest.toml",
    root / "LICENSE",
    root / "README.md",
    root / "modules",
    root / "src",
]


def should_include(path: Path) -> bool:
    return "__pycache__" not in path.parts and path.suffix != ".pyc"
    

with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
    for path in include:
        if path.is_file():
            zipf.write(path, path.relative_to(root))
        elif path.is_dir():
            for file in path.rglob("*"):
                if file.is_file() and should_include(file):
                    zipf.write(file, file.relative_to(root))


print(f"Created {output}")