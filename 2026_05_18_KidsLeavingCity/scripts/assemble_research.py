"""Assemble RESEARCH.md from phase scratch files."""
import re
from pathlib import Path
from datetime import date

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
SECTIONS = [
    ("_scratch_phase7.md", "1. Research Synthesis"),
    ("_scratch_phase5.md", "2. Key Statistics"),
    ("_scratch_phase2.md", "3. Media Coverage"),
    ("_scratch_phase3.md", "4. Commentary & Academic"),
    ("_scratch_phase4.md", "5. Policy / Official Statistics"),
]


def demote(text):
    return re.sub(r"^# (?!#)", "## ", text, flags=re.MULTILINE)


def main():
    out = []
    out.append("# Research Dossier — Why are Families Leaving New York City?\n")
    intro = (
        "*Compiled " + date.today().isoformat() + ". "
        "Single-file consolidation of all research for this project. "
        "Add inline annotations with [[AZIZ: your note]] and I will respond with "
        "<mark>**Claude (date):** ...</mark>.*\n"
    )
    out.append(intro)
    out.append("## Contents\n")
    for _, title in SECTIONS:
        out.append("- " + title)
    out.append("\n---\n")

    for filename, title in SECTIONS:
        path = PROJECT / "data" / filename
        if not path.exists():
            print("  missing:", filename)
            continue
        body = path.read_text()
        out.append("# " + title + "\n")
        out.append(demote(body).rstrip())
        out.append("\n---\n")

    (PROJECT / "RESEARCH.md").write_text("\n".join(out))

    # Clean scratch files
    for filename, _ in SECTIONS:
        p = PROJECT / "data" / filename
        if p.exists():
            p.unlink()
    p1 = PROJECT / "data" / "_scratch_phase1_scope.md"
    if p1.exists():
        p1.unlink()

    size = (PROJECT / "RESEARCH.md").stat().st_size
    print("Wrote RESEARCH.md -", str(size // 1024), "KB")


if __name__ == "__main__":
    main()
