#!/usr/bin/env python3
"""Reproduce the stratified 160-case roster and verify evidence candidates.

Read-only by default. Uses the existing corpus parser; does not edit source text.
    python3 research/reproduce_sample.py
    python3 research/reproduce_sample.py --write
The sampled text is historical material for corpus research, not clinical advice.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "work"))
from audit_corpus import BLOCK_RE, CORPUS, books, parse_metadata  # noqa: E402

SEED = "xueji-retrieval-v1-20261026"
MANIFEST = ROOT / "research/samples/manifest_160_v1.csv"
ANNOTATIONS = ROOT / "research/samples/annotation_candidates_160_v1.jsonl"
PILOT = ROOT / "research/samples/close_read_pilot_16_v1.jsonl"
BLOB_SHA_AT_FREEZE = "e8459e27e93711c44357fafcf7d106f97ecaca26"
WORK_NAMES = {
    "XJ-NKZY", "XJ-NKCZ", "XJ-WKSY", "XJ-LZWKFH",
    "XJ-KCLY", "XJ-ZTLY", "XJ-LYJY", "XJ-BYCY",
}
ANCHORS = {
    "XJ-NKZY": ["XJ-NKZY-C-V1-P002-1", "XJ-NKZY-C-V1-P098-1"],
    "XJ-NKCZ": ["XJ-NKCZ-C-V1-P026-1", "XJ-NKCZ-C-V1-P106-1"],
    "XJ-WKSY": ["XJ-WKSY-C-V1-P095-1", "XJ-WKSY-C-V2-P122-1"],
    "XJ-LZWKFH": ["XJ-LZWKFH-C-V2-P015-1", "XJ-LZWKFH-C-V4-P086-1"],
    "XJ-KCLY": ["XJ-KCLY-C-H3-P014-1", "XJ-KCLY-C-H1-P012-1"],
    "XJ-ZTLY": ["XJ-ZTLY-C-V1-P057-1"],
    "XJ-LYJY": ["XJ-LYJY-C-V1-P075", "XJ-LYJY-C-V2-P002"],
    "XJ-BYCY": ["XJ-BYCY-C-V5-L0234", "XJ-BYCY-C-V5-L0046"],
}
FIELD_NAMES = ("symptoms", "trigger", "course", "prior_treatment", "mechanism")
PATTERNS = {
    "trigger": re.compile(
        r"(?:因勞[^，。；]{0,12}|勞則[^，。；]{0,12}|每勞[^，。；]{0,12}|"
        r"勞心[^，。；]{0,12}|善怒[^，。；]{0,12}|因怒[^，。；]{0,12}|"
        r"素因[^，。；]{0,18}|素善飲[^，。；]{0,10}|過飲[^，。；]{0,12}|"
        r"飲食失節[^，。；]{0,12}|因憂[^，。；]{0,12}|墜梯[^，。；]{0,12}|"
        r"墜馬[^，。；]{0,12}|撲傷[^，。；]{0,12}|妊娠[^，。；]{0,12}|"
        r"產後[^，。；]{0,12}|停食[^，。；]{0,12})"
    ),
    "course": re.compile(
        r"(?:年餘[^，。；]{0,10}|數月[^，。；]{0,10}|數年[^，。；]{0,10}|"
        r"數日[^，。；]{0,10}|經年[^，。；]{0,10}|兩年[^，。；]{0,10}|"
        r"二年[^，。；]{0,10}|日晡[^，。；]{0,10}|仲夏[^，。；]{0,10}|"
        r"孟秋[^，。；]{0,10}|每勞[^，。；]{0,10}|時或[^，。；]{0,10}|"
        r"或時[^，。；]{0,10}|復發[^，。；]{0,10}|再發[^，。；]{0,10}|"
        r"久不[^，。；]{0,10})"
    ),
    "prior_treatment": re.compile(
        r"(?:誤用[^，。；]{0,26}|誤服[^，。；]{0,26}|先服[^，。；]{0,26}|"
        r"曾服[^，。；]{0,26}|前醫[^，。；]{0,26}|他醫[^，。；]{0,26}|"
        r"服[^，。；]{1,16}藥[^，。；]{0,15}|服[^，。；]{1,16}丸[^，。；]{0,15}|"
        r"服[^，。；]{1,18}湯[^，。；]{0,15}|用發表之劑[^，。；]{0,15})"
    ),
    "mechanism": re.compile(
        r"(?:余曰[:：][^。；]{4,40}|余謂[^。；，]{4,40}|"
        r"余以為[^。；]{4,40}|余作[^。；]{4,40}|"
        r"此[^，。；]{1,16}(?:虛|火|氣|血|痰|邪|脾|肝|腎|濕|熱|寒)[^，。；]{0,18}|"
        r"乃[^，。；]{1,12}(?:虛|火|氣|血|痰|邪|脾|肝|腎)[^，。；]{0,18})"
    ),
}
THERAPY_STRATUM = re.compile(r"服|用|投|施|針|刺|灸|誤|误|治|先|後")
PULSE_STRATUM = re.compile(r"脈|脉")


def fnv1a32(value: str) -> str:
    h = 2166136261
    for byte in value.encode("utf-8"):
        h = ((h ^ byte) * 16777619) & 0xFFFFFFFF
    return f"{h:08x}"


def load() -> tuple[dict[str, str], list[dict]]:
    txt = CORPUS.read_text(encoding="utf-8")
    items = books(txt)
    index = {row["meta"]["source_id"]: row["body"] for b in items for row in b["rows"]}
    all_cases = []
    for match in BLOCK_RE.finditer(txt):
        meta, _ = parse_metadata(match.group(1))
        case_id = meta.get("case_id")
        if not case_id:
            continue
        raw_spans = [
            (meta["source_ref"], int(meta["source_start_char"]),
             int(meta["source_end_char_exclusive"]))
        ]
        if meta.get("continued_source_ref"):
            raw_spans.append((meta["continued_source_ref"], int(meta["continued_start_char"]),
                              int(meta["continued_end_char_exclusive"])))
        if meta.get("continued_source_refs"):
            for token in meta["continued_source_refs"].split(";"):
                sid, start, end = token.strip().rsplit(":", 2)
                raw_spans.append((sid, int(start), int(end)))
        spans = []
        parts = []
        for sid, start, end in raw_spans:
            if sid not in index or not 0 <= start < end <= len(index[sid]):
                raise ValueError(f"{case_id}: invalid source span {sid}:{start}:{end}")
            spans.append({"source_ref": sid, "start": start, "end": end})
            parts.append(index[sid][start:end])
        work = meta.get("work_ref") or case_id.split("-C-")[0]
        all_cases.append({"case_id": case_id, "work_ref": work,
                          "source_ref": meta["source_ref"], "segments": spans,
                          "parts": parts, "body": "\n\n".join(parts), "md": meta})
    if len(index) != 5361 or len(all_cases) != 1532:
        raise AssertionError(f"Unexpected source/case counts: {len(index)}/{len(all_cases)}")
    return index, all_cases


def choose_cases(all_cases: list[dict]) -> list[dict]:
    by_work = defaultdict(list)
    for c in all_cases:
        by_work[c["work_ref"]].append(c)
    if set(by_work) != WORK_NAMES:
        raise AssertionError(f"Unexpected works: {sorted(by_work)}")
    sample = []
    for work in sorted(by_work):
        cases = sorted(by_work[work], key=lambda x: x["case_id"])
        seen = set()
        selected = []

        def add(c, label):
            if c is not None and c["case_id"] not in seen:
                seen.add(c["case_id"])
                selected.append((c, label))

        for anchor in ANCHORS[work]:
            match = next((c for c in cases if c["case_id"] == anchor), None)
            if match is None:
                raise AssertionError(f"Missing anchor: {anchor}")
            add(match, "anchor_quantile")
        if work == "XJ-NKZY":
            pending = next((c for c in cases if c["md"].get("retrieval_status") == "needs_review"
                            and c["case_id"] not in seen), None)
            if pending is None:
                raise AssertionError("No review-pending case found in XJ-NKZY")
            add(pending, "anchor_quantile")
        for i in range(15):
            if len(selected) >= 5:
                break
            add(cases[min(len(cases) - 1, int((i + 0.5) * len(cases) / 15))],
                "anchor_quantile")
        if len(selected) != 5:
            raise AssertionError(f"{work}: quantile sample underfilled")

        def ranked(predicate):
            return sorted((c for c in cases if c["case_id"] not in seen and predicate(c)),
                          key=lambda c: (fnv1a32(SEED + "|" + c["case_id"]), c["case_id"]))

        for c in ranked(lambda c: bool(PULSE_STRATUM.search(c["body"])))[:5]:
            add(c, "pulse_literal")
        if len(selected) != 10:
            raise AssertionError(f"{work}: pulse stratum underfilled")
        for c in ranked(lambda c: bool(THERAPY_STRATUM.search(c["body"])))[:5]:
            add(c, "treatment_sequence_candidate")
        if len(selected) != 15:
            raise AssertionError(f"{work}: therapy stratum underfilled")
        for c in ranked(lambda c: True)[:5]:
            add(c, "hash_remainder")
        if len(selected) != 20:
            raise AssertionError(f"{work}: remainder underfilled")
        sample.extend((dict(c, stratum=label) for c, label in selected))
    if len(sample) != 160 or len({c["case_id"] for c in sample}) != 160:
        raise AssertionError("Roster must contain 160 unique cases")
    return sample


def make_manifest(sample: list[dict]) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["case_id", "work_ref", "sample_stratum", "source_ref",
                     "retrieval_status", "source_span_count", "case_text_fnv1a32", "seed"])
    for c in sample:
        writer.writerow([c["case_id"], c["work_ref"], c["stratum"], c["source_ref"],
                         c["md"].get("retrieval_status") or "unknown", len(c["segments"]),
                         fnv1a32(c["body"]), SEED])
    return stream.getvalue()


def find_evidence(c: dict, quote: str, index: dict[str, str]):
    if not quote:
        return None
    for part, span in zip(c["parts"], c["segments"]):
        i = part.find(quote)
        if i < 0:
            continue
        start = span["start"] + i
        end = start + len(quote)
        if index[span["source_ref"]][start:end] != quote:
            raise AssertionError("Source evidence not exact")
        return {"source_ref": span["source_ref"],
                "source_start_char": start, "source_end_char_exclusive": end,
                "raw_quote": quote}
    return None


def regex_evidence(c: dict, field: str, index: dict[str, str]):
    for part in c["parts"]:
        match = PATTERNS[field].search(part)
        if match and match.group(0).strip():
            result = find_evidence(c, match.group(0), index)
            if result:
                return result
    return None


def annotate(c: dict, index: dict[str, str]) -> dict:
    record = {"case_id": c["case_id"], "work_ref": c["work_ref"],
              "source_ref": c["source_ref"],
              "case_source_spans": [
                  {"source_ref": sp["source_ref"], "source_start_char": sp["start"],
                   "source_end_char_exclusive": sp["end"]} for sp in c["segments"]],
              "sample_stratum": c["stratum"],
              "source_record_retrieval_status": c["md"].get("retrieval_status") or "unknown",
              "annotation_status": "auto_literal_candidates_not_human_reviewed",
              "fields": {}}

    def put(key, evidence, rule):
        if evidence:
            record["fields"][key] = {
                "status": "candidate_requires_human_review",
                "polarity": "unknown_until_review",
                "time_phase": "unknown_until_review",
                "assertion_type": "not_adjudicated",
                "extraction_rule": rule,
                "evidence": evidence,
            }
        else:
            record["fields"][key] = {
                "status": "not_identified_by_rule",
                "polarity": "unknown_not_equivalent_to_absent",
                "time_phase": "unknown",
                "assertion_type": "not_adjudicated",
                "extraction_rule": rule,
                "evidence": None,
            }

    symptoms_quote = c["md"].get("symptoms_quote") or ""
    symptom_evidence = find_evidence(c, symptoms_quote[:56], index) if symptoms_quote else None
    if symptom_evidence:
        origin = "legacy_symptoms_quote_first_56_codepoints"
    else:
        origin = "source_opening_preview_not_symptom_classified"
        first = next((p for p in c["parts"] if p.strip()), "")
        symptom_evidence = find_evidence(c, first.lstrip()[:52], index)
    put("symptoms", symptom_evidence, origin)
    for key, label in [
        ("trigger", "literal_trigger_regex_v0_1"),
        ("course", "literal_temporal_regex_v0_1"),
        ("prior_treatment", "literal_therapy_regex_v0_1_role_unresolved"),
    ]:
        put(key, regex_evidence(c, key, index), label)
    mechanism_quote = c["md"].get("mechanism_quote") or ""
    mechanism_evidence = (find_evidence(c, mechanism_quote[:65], index)
                          if mechanism_quote else None)
    mechanism_rule = "legacy_mechanism_quote_first_65_codepoints"
    if not mechanism_evidence:
        mechanism_evidence = regex_evidence(c, "mechanism", index)
        mechanism_rule = "literal_reasoning_regex_v0_1_role_unresolved"
    put("mechanism", mechanism_evidence, mechanism_rule)
    return record


def verify_annotations(data: str, sample: list[dict], index: dict[str, str]) -> Counter:
    entries = [json.loads(line) for line in data.splitlines() if line]
    if len(entries) != 160:
        raise AssertionError(f"Expected 160 annotations, got {len(entries)}")
    actual = Counter()
    for obj, c in zip(entries, sample):
        if obj["case_id"] != c["case_id"] or obj["sample_stratum"] != c["stratum"]:
            raise AssertionError(f"Different case or stratum: {obj['case_id']} vs {c['case_id']}")
        expected = annotate(c, index)
        if obj != expected:
            raise AssertionError(f"Annotation drift: {c['case_id']}")
        if set(obj["fields"]) != set(FIELD_NAMES):
            raise AssertionError(f"Incomplete feature dimensions: {c['case_id']}")
        for key, field in obj["fields"].items():
            ev = field["evidence"]
            if not ev:
                if field["polarity"] == "explicitly_absent":
                    raise AssertionError("Missing evidence treated as negative")
                continue
            if field["time_phase"] != "unknown_until_review":
                raise AssertionError("Unreviewed evidence asserted temporal phase")
            if not any(sp["source_ref"] == ev["source_ref"] and
                       sp["source_start_char"] <= ev["source_start_char"] <
                       ev["source_end_char_exclusive"] <= sp["source_end_char_exclusive"]
                       for sp in obj["case_source_spans"]):
                raise AssertionError(f"Evidence leaves cited case: {c['case_id']}, {key}")
            if index[ev["source_ref"]][ev["source_start_char"]:
                                     ev["source_end_char_exclusive"]] != ev["raw_quote"]:
                raise AssertionError(f"Evidence mismatch: {c['case_id']}, {key}")
            actual[key] += 1
    return actual


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="Rebuild outputs from fixed rules")
    ap.add_argument("--allow-source-update", action="store_true",
                    help="Intentionally regenerate after changing the corpus; requires review")
    args = ap.parse_args()
    index, cases = load()
    raw = CORPUS.read_bytes()
    current_blob_sha = hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + bytes([0]) + raw
    ).hexdigest()
    if not args.allow_source_update and current_blob_sha != BLOB_SHA_AT_FREEZE:
        raise AssertionError(
            f"Corpus Git blob SHA drift: {current_blob_sha}; "
            f"expected frozen {BLOB_SHA_AT_FREEZE}"
        )
    if args.allow_source_update:
        print("WARNING: source-update override; comparison to historical baseline is not implied")
    roster = choose_cases(cases)
    manifest = make_manifest(roster)
    if args.write:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(manifest, encoding="utf-8")
        with ANNOTATIONS.open("w", encoding="utf-8") as out:
            for c in roster:
                out.write(json.dumps(annotate(c, index), ensure_ascii=False,
                                     separators=(",", ":")) + "\n")
    stored_manifest = MANIFEST.read_text(encoding="utf-8")
    if stored_manifest != manifest:
        raise AssertionError("Manifest is not reproducible from this corpus and seed")
    actual = verify_annotations(ANNOTATIONS.read_text(encoding="utf-8"), roster, index)
    selected_ids = {c["case_id"] for c in roster}
    reviewed = [json.loads(line) for line in PILOT.read_text(encoding="utf-8").splitlines()
                if line]
    if len(reviewed) != 16 or len({r["case_id"] for r in reviewed}) != 16:
        raise AssertionError("Pilot must contain 16 unique rows")
    pilot_span_count = 0
    for pilot in reviewed:
        if pilot["case_id"] not in selected_ids or set(pilot["fields"]) != set(FIELD_NAMES):
            raise AssertionError(f"Pilot ID or fields invalid: {pilot['case_id']}")
        case = next(c for c in roster if c["case_id"] == pilot["case_id"])
        for name, field in pilot["fields"].items():
            ev = field["evidence"]
            if ev is None:
                if field["polarity"] == "explicitly_absent":
                    raise AssertionError("Pilot missing evidence cannot assert absence")
                continue
            if not any(sp["source_ref"] == ev["source_ref"] and
                       sp["start"] <= ev["source_start_char"] <
                       ev["source_end_char_exclusive"] <= sp["end"]
                       for sp in case["segments"]):
                raise AssertionError(f"Pilot evidence outside case: {pilot['case_id']} {name}")
            if index[ev["source_ref"]][ev["source_start_char"]:
                                     ev["source_end_char_exclusive"]] != ev["raw_quote"]:
                raise AssertionError(f"Pilot evidence mismatch: {pilot['case_id']} {name}")
            pilot_span_count += 1
    per_book = Counter(c["work_ref"] for c in roster)
    per_stratum = Counter(c["stratum"] for c in roster)
    assert len(per_book) == 8 and set(per_book.values()) == {20}
    assert all(per_stratum[k] == 40 for k in (
        "anchor_quantile", "pulse_literal", "treatment_sequence_candidate", "hash_remainder"))
    print(f"PASS: 5361 sources, 1532 cases, 160 unique sample rows, 8 works x 20")
    print(f"PASS: manifest reproducible; {sum(actual.values())} evidence spans exact")
    print(f"Candidate spans by field: {dict(sorted(actual.items()))}")
    print(f"PASS: 16 model close-read pilot records, {pilot_span_count} exact evidence spans")
    print(f"PASS: frozen source Git blob: {current_blob_sha}")
    print("No clinical feature polarity, time point or medical interpretation has been adjudicated.")


if __name__ == "__main__":
    main()
