"""Patch the eight-book metadata blocks with 2026-09-29 electronic-source
reconciliation results for the five books freshly re-fetched from jicheng.tw
(WKSY, LZWKFH, KCLY, ZTLY, LYJY). Read-only except for the single corpus file;
only touches each book's own ```yaml metadata block, never source_paragraph text.
"""
import json
import re
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[1] / "outputs/薛己核心医案_结构化样本.md"

BOOKS = {
    "XJ-WKSY": dict(
        snapshot="work/source-snapshots/wksy-index-2026-09-29.html",
        report="work/reconcile_wksy_report.json",
        chapters=62,
        extra_note=(
            "reconciliation_result: \"851/851 aligned snapshot paragraphs exact-match except 98 "
            "already-documented legacy corrections; 0 chapter-boundary mismatches; working transcription "
            "retains 2 additional records (XJ-WKSY-V4-P416/P417, 右肩尖肘尖二穴圖說明) recovered from image "
            "verification that the current jicheng.tw page still omits, per existing handoff record\""
        ),
    ),
    "XJ-LZWKFH": dict(
        snapshot="work/source-snapshots/lzwkfh-index-2026-09-29.html",
        report="work/reconcile_lzwkfh_report.json",
        chapters=33,
        extra_note=(
            "reconciliation_result: \"1170/1170 paragraphs exact-match current snapshot except 4 "
            "already-documented legacy corrections; 0 chapter-boundary mismatches; no new unexplained "
            "differences found\""
        ),
    ),
    "XJ-KCLY": dict(
        snapshot="work/source-snapshots/kcly-index-2026-09-29.html",
        report="work/reconcile_kcly_report.json",
        chapters=13,
        extra_note=(
            "reconciliation_result: \"322/322 paragraphs exact-match current snapshot except 7 "
            "already-documented legacy corrections; 0 chapter-boundary mismatches; no new unexplained "
            "differences found\""
        ),
    ),
    "XJ-ZTLY": dict(
        snapshot="work/source-snapshots/ztly-index-2026-09-29.html",
        report="work/reconcile_ztly_report.json",
        chapters=6,
        extra_note=(
            "reconciliation_result: \"329/329 paragraphs exact-match current snapshot except 5 "
            "already-documented legacy corrections; 0 chapter-boundary mismatches; no new unexplained "
            "differences found\""
        ),
    ),
    "XJ-LYJY": dict(
        snapshot="work/source-snapshots/lyjy-index-2026-09-29.html",
        report="work/reconcile_lyjy_report.json",
        chapters=10,
        extra_note=(
            "reconciliation_result: \"407/407 working-transcription paragraphs exact-match current "
            "snapshot's first 407 except 7 already-documented legacy corrections; 0 chapter-boundary "
            "mismatches; current snapshot has 2 additional trailing paragraphs (當歸川芎散) that the "
            "existing handoff record already identifies as misattributed to this book (actually 四庫《薛氏"
            "醫案》卷四十八) and intentionally excluded, per prior image verification\""
        ),
    ),
}

text = CORPUS.read_text(encoding="utf-8")

for wid, cfg in BOOKS.items():
    report = json.loads(Path(cfg["report"]).read_text(encoding="utf-8"))
    sha256 = report["snapshot_sha256"]
    pattern = re.compile(
        r'(```yaml\nwork_id: "' + re.escape(wid) + r'"\nwork_title:.*?\n)'
        r'(source_snapshot_status: "not_found_in_current_task_files"\n)'
        r'(source_acquisition_date: "unknown"\n)'
        r'(metadata_audit_date: "2026-09-28"\n)'
        r'(electronic_source_alignment: "pending_independent_snapshot_comparison"\n)',
        re.S,
    )
    m = pattern.search(text)
    if not m:
        raise SystemExit(f"metadata block pattern not found for {wid}")

    replacement = (
        m.group(1)
        + f'source_snapshot_status: "current_snapshot_preserved_historical_snapshot_unknown"\n'
        + f'current_snapshot_path: "{cfg["snapshot"]}"\n'
        + f'current_snapshot_date: "2026-09-29"\n'
        + f'current_snapshot_sha256: "{sha256}"\n'
        + m.group(3)
        + 'metadata_audit_date: "2026-09-29"\n'
        + f'electronic_source_alignment: "all_{report["existing_record_count"]}_paragraphs_and_{cfg["chapters"]}_chapters_aligned_with_documented_edits"\n'
        + 'reconciliation_method: "work/reconcile_book.py paragraph-order alignment against current_snapshot_path; report at ' + cfg["report"] + '"\n'
        + cfg["extra_note"] + "\n"
    )
    new_text = text[:m.start()] + replacement + text[m.end():]
    if new_text == text:
        raise SystemExit(f"no change applied for {wid}")
    text = new_text
    print(f"patched {wid}")

CORPUS.write_text(text, encoding="utf-8")
print("done")
