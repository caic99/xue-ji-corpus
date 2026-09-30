"""Read-only reconciliation of XJ-BYCY against a freshly fetched Kanripo raw
text file, replicating archive/tools/append_kanripo_volume.py's exact parsing
(pilcrow ¶ stripped, <pb:...> folio markers tracked, blank/header lines before
the first folio marker skipped). Does not modify the main corpus file.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_corpus import CORPUS, books

SNAPSHOT = Path(__file__).resolve().parent / "source-snapshots/bycy-kr3e0070_005-2026-09-29.txt"
WORK_ID = "XJ-BYCY"
PAGE_RE = re.compile(r"^<pb:([^>]+)>¶?$")


def parse_kanripo(raw_text):
    physical_lines = raw_text.splitlines()
    folio = ""
    folios = []
    records = []
    metadata_done = False
    for raw_line in physical_lines:
        line = raw_line.rstrip("\r")
        page_match = PAGE_RE.match(line)
        if page_match:
            folio = page_match.group(1)
            folios.append(folio)
            metadata_done = True
            continue
        if not metadata_done and (line.startswith("#") or not line.strip()):
            continue
        text = line[:-1] if line.endswith("¶") else line
        if not text.strip():
            continue
        records.append((folio, text))
    return physical_lines, folios, records


def main():
    raw_bytes = SNAPSHOT.read_bytes()
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    physical_lines, folios, records = parse_kanripo(raw_bytes.decode("utf-8"))

    text = CORPUS.read_text()
    items = books(text)
    book = next(b for b in items if b["meta"]["work_id"] == WORK_ID)

    report = {
        "work_id": WORK_ID,
        "snapshot_path": str(SNAPSHOT.relative_to(CORPUS.parents[1])),
        "snapshot_sha256": sha256,
        "snapshot_physical_line_count": len(physical_lines),
        "snapshot_folio_marker_count": len(folios),
        "snapshot_source_line_count": len(records),
        "existing_record_count": len(book["rows"]),
        "count_matches": len(book["rows"]) == len(records),
    }

    diffs = []
    folio_mismatches = []
    n = min(len(book["rows"]), len(records))
    for ordinal in range(n):
        row = book["rows"][ordinal]
        folio, value = records[ordinal]
        m = row["meta"]
        sid = m["source_id"]
        if m.get("folio") != folio:
            folio_mismatches.append({
                "ordinal": ordinal + 1, "source_id": sid,
                "existing_folio": m.get("folio"), "snapshot_folio": folio,
            })
        body = row["body"]
        if body != value:
            diffs.append({
                "ordinal": ordinal + 1, "source_id": sid,
                "has_legacy_difference_grade": bool(m.get("difference_grade")),
                "existing_text": body, "snapshot_text": value,
            })

    report["folio_mismatches"] = len(folio_mismatches)
    report["text_diffs"] = len(diffs)
    report["folio_mismatch_detail"] = folio_mismatches
    report["diff_detail"] = diffs
    if len(book["rows"]) != len(records):
        report["length_note"] = f"existing={len(book['rows'])} snapshot={len(records)}"

    out_path = Path(__file__).resolve().parent / "reconcile_bycy_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items()
                       if k not in ("folio_mismatch_detail", "diff_detail")},
                      ensure_ascii=False, indent=2))
    print(f"\nfull report written to {out_path}")


if __name__ == "__main__":
    main()
