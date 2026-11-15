"""Build the same installable addon layout used by CurseForge's packager."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import argparse
import re

ROOT = Path(__file__).resolve().parents[1]


def package(tag=None):
    toc = (ROOT / "PriestShieldTracker.toc").read_text(encoding="utf-8")
    version = re.search(r"^## Version: (\S+)$", toc, re.M).group(1)
    if tag:
        if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-(?:alpha|beta)\.\d+)?", tag):
            raise ValueError("Use vX.Y.Z, vX.Y.Z-alpha.N, or vX.Y.Z-beta.N")
        if tag != f"v{version}":
            raise ValueError(f"Tag {tag} does not match TOC version {version}")
    assert "## Interface: 16001" in toc
    files = {"PriestShieldTracker.toc", "LICENSE", "CHANGELOG.md"}
    for line in toc.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            files.add(line.replace("\\", "/"))
    for folder in ("Media", "licenses"):
        if (ROOT / folder).exists():
            files.update(p.relative_to(ROOT).as_posix() for p in (ROOT / folder).rglob("*") if p.is_file())
    for name in files:
        path = (ROOT / name).resolve()
        assert path.is_relative_to(ROOT) and path.is_file(), name
    members = {f"PriestShieldTracker/{name}": ROOT / name for name in files}
    # Keep only the saved-variable loader at the old folder path, matching .pkgmeta.
    importer = ROOT / "Compatibility/SoulShield"
    for path in importer.rglob("*"):
        if path.is_file():
            members[f"SoulShield/{path.relative_to(importer).as_posix()}"] = path
    output = ROOT / "dist" / f"PriestShieldTracker-{version}.zip"
    output.parent.mkdir(exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, path in sorted(members.items()):
            archive.write(path, name)
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(members)
        for name, path in members.items():
            assert archive.read(name) == path.read_bytes()
    return version, output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag")
    args = parser.parse_args()
    version, output = package(args.tag)
    print(output)
