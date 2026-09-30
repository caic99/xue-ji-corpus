"""Read-only reconciliation of a single work's working transcription against a
freshly fetched jicheng.tw snapshot. Does not modify the main corpus file.
Generalizes work/reconcile_nkcz.py to any work_id/snapshot pair.
"""

from argparse import ArgumentParser
from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rebuild_book_from_cc0 import BookParser
from audit_corpus import CORPUS, books


def load_snapshot(path):
    raw = path.read_bytes()
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
    p = ArgumentParser()
    p.add_argument("--work-id", required=True)
    p.add_argument("--snapshot", required=True)
    p.add_argument("--report", required=True)
    a = p.parse_args()

    text = CORPUS.read_text()
    items = books(text)
    book = next(b for b in items if b["meta"]["work_id"] == a.work_id)
    snapshot_path = Path(a.snapshot)
    sha256, source = load_snapshot(snapshot_path)

    report = {
        "work_id": a.work_id,
        "snapshot_path": str(snapshot_path.relative_to(CORPUS.parents[1])),
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
            report["extra_existing_tail"] = [r["meta"]["source_id"] for r in book["rows"][n:]]
        if len(source) > n:
            report["extra_snapshot_tail"] = [
                {"volume": v, "section": s, "text": t[:60]} for v, s, t in source[n:]
            ]

    out_path = Path(a.report)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items()
                       if k not in ("chapter_mismatch_detail", "diff_detail")},
                      ensure_ascii=False, indent=2))
    print(f"\nfull report written to {out_path}")


if __name__ == "__main__":
    main()
