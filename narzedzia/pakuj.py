"""Build the Teams submission from an explicit allowlist, then verify it."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ["README.md", "sprawozdanie.pdf", "prezentacja.pdf", "pyproject.toml",
         "requirements.txt", "dokumentacja/sprawozdanie.md", "dokumentacja/prezentacja.md"]
DIRS = ["kod", "dane", "modele", "wyniki", "uruchomienie", "narzedzia"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    team = json.loads((ROOT / "dane/zespol.json").read_text(encoding="utf-8"))
    name = f"projekt_{team['zespol']}_{team['dzien']}_{team['godzina']}"
    if not re.fullmatch(r"projekt_\d+_(pon|czw)_(8|10\.30)", name):
        raise SystemExit("Niepoprawne dane nazwy archiwum w dane/zespol.json")
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    if status.strip() and not args.allow_dirty:
        raise SystemExit("Zapisz zmiany w Git przed pakowaniem, aby wersja była jednoznaczna.")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    version = {"version": "1.0.0", "commit": commit, "dirty": bool(status.strip()),
               "repository": "Lokalne repozytorium Git. Kompletny kod jest w kod/."}
    candidates = [ROOT / f for f in FILES]
    for directory in DIRS:
        candidates.extend(p for p in (ROOT / directory).rglob("*") if p.is_file())
    files = sorted({p for p in candidates if not any(part in {"__pycache__"}
                                                  for part in p.relative_to(ROOT).parts)
                    and p.suffix not in {".pyc", ".pyo"}})
    for p in files:
        if not p.is_file() or p.is_symlink():
            raise SystemExit(f"Brak pliku lub niedozwolony symlink: {p}")
    payload = {str(p.relative_to(ROOT)).replace("\\", "/"): p.read_bytes() for p in files}
    payload["wersja.json"] = (json.dumps(version, ensure_ascii=False, indent=2) + "\n").encode()
    sums = "".join(f"{hashlib.sha256(data).hexdigest()}  {path}\n" for path, data in sorted(payload.items()))
    payload["SUMY_SHA256.txt"] = sums.encode()
    args.output.mkdir(parents=True, exist_ok=True)
    output = args.output / f"{name}.zip"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, data in sorted(payload.items()):
            info = zipfile.ZipInfo(f"{name}/{path}", date_time=(2026, 11, 15, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert {p.split("/")[0] for p in archive.namelist()} == {name}
        for path, data in payload.items():
            assert archive.read(f"{name}/{path}") == data
    print(output)
    print(f"{len(payload)} plików, {output.stat().st_size:,} bajtów, commit {commit}")


if __name__ == "__main__":
    main()
