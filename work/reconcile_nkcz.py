"""Read-only reconciliation of XJ-NKCZ (女科撮要) working transcription against a
freshly fetched jicheng.tw snapshot. Does not modify the main corpus file.

Mirrors the paragraph-alignment method audit_corpus.load_nkzy_snapshot uses for
XJ-NKZY, generalized to any single-work snapshot with the same <main data-render="book">
structure (h1=volume, h2=section, div[data-sec=p]=paragraph).
"""

from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rebuild_book_from_cc0 import BookParser
from audit_corpus import CORPUS, books

SNAPSHOT = Path(__file__).resolve().parent / "source-snapshots/nkcz-index-2026-09-29.html"
WORK_ID = "XJ-NKCZ"


def load_snapshot():
    raw = SNAPSHOT.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    parser = BookParser()
    parser.feed(raw.decode("utf-8"))
    source = []
    volume, section = "", ""
    for tag, value in parser.items:
        if tag == "h1":
            volume, section = value, ""
        elif tag == "h2":
            section = value
        else:
            source.append((volume, section, value))
    return sha256, source


def main():
    text = CORPUS.read_text()
    items = books(text)
    book = next(b for b in items if b["meta"]["work_id"] == WORK_ID)
    sha256, source = load_snapshot()

    report = {
        "work_id": WORK_ID,
        "snapshot_path": str(SNAPSHOT.relative_to(CORPUS.parents[1])),
        "snapshot_sha256": sha256,
        "existing_record_count": len(book["rows"]),
        "snapshot_paragraph_count": len(source),
        "count_matches": len(book["rows"]) == len(source),
    }

    diffs = []
    chapter_mismatches = []
    n = min(len(book["rows"]), len(source))
    for ordinal in range(n):
        row = book["rows"][ordinal]
        volume, section, value = source[ordinal]
        m = row["meta"]
        sid = m["source_id"]
        if (m.get("volume"), m.get("section") or "") != (volume, section):
            chapter_mismatches.append({
                "ordinal": ordinal + 1,
                "source_id": sid,
                "existing": [m.get("volume"), m.get("section")],
                "snapshot": [volume, section],
            })
        body = row["body"].removesuffix("\n\n---").strip()
        if body != value:
            diffs.append({
                "ordinal": ordinal + 1,
                "source_id": sid,
                "has_legacy_difference_grade": bool(m.get("difference_grade")),
                "existing_text": body,
                "snapshot_text": value,
            })

    report["chapter_boundary_mismatches"] = len(chapter_mismatches)
    report["text_diffs"] = len(diffs)
    report["chapter_mismatch_detail"] = chapter_mismatches
    report["diff_detail"] = diffs

    if len(book["rows"]) != len(source):
        report["length_note"] = (
            f"existing={len(book['rows'])} snapshot={len(source)}; "
            f"compared only first {n} in alignment order"
        )
        if len(book["rows"]) > n:
            report["extra_existing_tail"] = [
                r["meta"]["source_id"] for r in book["rows"][n:]
            ]
        if len(source) > n:
            report["extra_snapshot_tail"] = [
                {"volume": v, "section": s, "text": t[:60]} for v, s, t in source[n:]
            ]

    out_path = Path(__file__).resolve().parent / "reconcile_nkcz_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items()
                       if k not in ("chapter_mismatch_detail", "diff_detail")},
                      ensure_ascii=False, indent=2))
    print(f"\nfull report written to {out_path}")


if __name__ == "__main__":
    main()
