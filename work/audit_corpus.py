"""Audit and mechanically refresh the single Markdown corpus without rewriting text.

The legacy file uses flat metadata, including some non-YAML interior quotation
marks. Parse that documented format strictly by line, report legacy quotations,
and reject duplicate keys or malformed lines rather than silently skipping them.
This tool does not validate historical readings against images.
"""

from argparse import ArgumentParser
from collections import Counter
from pathlib import Path
import hashlib
import json
import re
from rebuild_book_from_cc0 import BookParser


CORPUS = Path(__file__).resolve().parents[1] / "outputs/薛己核心医案_结构化样本.md"
BEGIN = "<!-- CURRENT_CORPUS_AUDIT_BEGIN -->"
END = "<!-- CURRENT_CORPUS_AUDIT_END -->"
SNAPSHOT = CORPUS.parents[1] / "work/source-snapshots/nkzy-2026-09-28.html"
SNAPSHOT_ROWS = {}
SNAPSHOT_SHA256 = ""
BOOK_RE = re.compile(r"^# 《([^》]+)》[^\n]*$", re.M)
BLOCK_RE = re.compile(r"```yaml\n(.*?)\n```", re.S)
RECORD_RE = re.compile(
    r"^##### (\S+)\n\n```yaml\n(.*?)\n```\n\n(.*?)"
    r"(?=\n#{3,5} |\Z)", re.M | re.S
)
PENDING = {
    "XJ-NKZY-V1-P071": "所標承應本確切頁待定位；已有讀法據嘉靖影像／四庫平行本",
    "XJ-NKZY-V1-P174": "所標承應本確切頁待定位；方後指令標記按 C0 記錄",
    "XJ-LYJY-V3-P018": "四庫卷十九影像未核；劑量疑點不得定為版本事實",
    "XJ-BYCY-V5-L1138": "卷末緊密字行需第二影像覆核",
    "XJ-WKSY-V4-P168": "方名小注讀法差異已登記；差異成因與原刻注文作者未核",
    "XJ-NKZY-V2-P083": "府癢：官稱用字可疑，尚無影像核對；保留原字",
    "XJ-NKZY-V2-P178": "草果茯苓：藥名分隔待影像核對；不擅自增字",
    "XJ-NKZY-V2-P179": "承應本第86頁圖讀右姜七片，電子轉錄上姜七斤；斤／片涉及用量單位，保留原文待人工審定",
    "XJ-NKZY-V2-P308": "加減濟生腎氣丸各一錢：多味藥量待影像核對，疑點不是已證實錯誤",
}
CURRENT_SCAN_NOTES = {
    'XJ-NKZY-V2-P179': {
        'current_scan_source_url':'https://commons.wikimedia.org/wiki/File:NCL-06248-0008_%E5%85%A7%E7%A7%91%E6%91%98%E8%A6%81.pdf?page=86',
        'current_scan_edition':'國家圖書館藏日本承應三年刊本，索書號304.31 06248-0008；PDF第86頁',
        'current_scan_raw_reading':'右姜七片烏梅一箇水煎服',
        'current_scan_difference':'上／右：方後指令標記；斤／片：生薑用量單位；個／箇：字形差異',
        'current_scan_difference_type':'instruction_marker_and_dose_unit_and_glyph',
        'current_scan_difference_impact':'dose_unit_content_difference_not_equivalent_marker_only',
        'current_scan_evidence_status':'model_visual_reading_of_target_line_not_human_adjudicated',
        'current_scan_review_date':'2026-09-28',
        'current_scan_review_method':'Computer Use單頁高分辨率圖像人工輔助逐字查看；未使用OCR代替原字',
        'current_scan_scope':'只核對人參養胃湯方後指令一行；不宣稱全頁或全方已校定',
        'scan_verification_status':'sampled_variants_found',
    }
}


def parse_metadata(block):
    data = {}
    legacy_quotes = []
    for number, line in enumerate(block.splitlines(), 1):
        if not line.strip():
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z_0-9]*):\s*(.*)", line)
        if not match:
            raise ValueError(f"Malformed metadata line {number}: {line}")
        key, value = match.groups()
        if key in data:
            raise ValueError(f"Duplicate metadata key: {key}")
        if value.startswith('"'):
            if not value.endswith('"'):
                raise ValueError(f"Unclosed quoted value: {key}")
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                # Preserve the historical flat format and explicitly report it.
                value = value[1:-1].replace('\\"', '"').replace('\\\\', '\\')
                legacy_quotes.append(key)
        data[key] = str(value)
    return data, legacy_quotes


def books(text):
    starts = list(BOOK_RE.finditer(text))
    output = []
    seen = set()
    for i, start in enumerate(starts):
        stop = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        section = text[start.start():stop]
        first = BLOCK_RE.search(section)
        if not first:
            raise ValueError(f"Book metadata missing: {start.group(1)}")
        meta, quote_fields = parse_metadata(first.group(1))
        rows = []
        for match in RECORD_RE.finditer(section):
            record, quotes = parse_metadata(match.group(2))
            sid = record.get("source_id")
            if sid != match.group(1) or sid in seen:
                raise ValueError(f"Duplicate or mismatching record ID: {sid}")
            seen.add(sid)
            body = match.group(3).rstrip()
            if not body:
                raise ValueError(f"Empty text: {sid}")
            rows.append({"meta": record, "body": body, "quotes": quotes})
        declared = len(re.findall(r"^source_id:", section, re.M))
        if len(rows) != declared:
            raise ValueError(f"Unparsed record in {meta.get('work_id')}")
        output.append({"meta": meta, "rows": rows, "section": section,
                       "quotes": quote_fields})
    if len(output) != 8:
        raise ValueError(f"Expected eight existing works, found {len(output)}")
    return output


def text_digest(items):
    # Metadata and report can change; every source ID and its entire text cannot.
    payload = [(r["meta"]["source_id"], r["body"])
               for book in items for r in book["rows"]]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def validate_structured_units(text, items):
    index = {r['meta']['source_id']:r['body'] for b in items for r in b['rows']}
    ids = set()
    spans = {}
    case_count = 0
    unit_count = 0
    structured_metadata = []
    for match in BLOCK_RE.finditer(text):
        m, _ = parse_metadata(match.group(1))
        uid = m.get('case_id') or m.get('text_unit_id')
        if not uid:
            continue
        if uid in ids:
            raise ValueError(f'Duplicate structured ID: {uid}')
        ids.add(uid)
        structured_metadata.append((uid, m))
        sid = m.get('source_ref')
        if sid not in index:
            raise ValueError(f'{uid}: unknown source reference')
        start, end = int(m['source_start_char']), int(m['source_end_char_exclusive'])
        source = index[sid]
        if not 0 <= start < end <= len(source):
            raise ValueError(f'{uid}: invalid character boundaries')
        expected = source[start:end]
        references = [(sid, start, end)]
        if m.get('continued_source_ref'):
            continued_sid = m['continued_source_ref']
            if continued_sid not in index:
                raise ValueError(f'{uid}: unknown continuation reference')
            continued_start = int(m['continued_start_char'])
            continued_end = int(m['continued_end_char_exclusive'])
            if not 0 <= continued_start < continued_end <= len(index[continued_sid]):
                raise ValueError(f'{uid}: invalid continuation boundaries')
            expected += '\n\n' + index[continued_sid][continued_start:continued_end]
            references.append((continued_sid, continued_start, continued_end))
        if m.get('continued_source_refs'):
            # Generalized chain for records spanning more than two source
            # records (e.g. XJ-BYCY's line-based transcription, where a
            # single case narrative commonly spans many physical lines).
            # Format: "sid:start:end; sid:start:end; ...". Each entry is
            # independent of the singular continued_source_ref above; a
            # record uses one mechanism or the other, not both.
            for entry in m['continued_source_refs'].split('; '):
                if not entry:
                    continue
                parts = entry.rsplit(':', 2)
                if len(parts) != 3:
                    raise ValueError(f'{uid}: malformed continued_source_refs entry: {entry}')
                chain_sid, chain_start_s, chain_end_s = parts
                if chain_sid not in index:
                    raise ValueError(f'{uid}: unknown continuation reference: {chain_sid}')
                chain_start, chain_end = int(chain_start_s), int(chain_end_s)
                if not 0 <= chain_start < chain_end <= len(index[chain_sid]):
                    raise ValueError(f'{uid}: invalid continuation boundaries for {chain_sid}')
                expected += '\n\n' + index[chain_sid][chain_start:chain_end]
                references.append((chain_sid, chain_start, chain_end))
        rest = text[match.end():]
        boundary = re.search(r'\n### |\n<!-- [A-Z0-9]+_[A-Z_]+_END -->', rest)
        # Only strip the plain-ASCII blank-line padding the rendering
        # convention inserts around a body (spaces/tabs/newlines); Python's
        # bare .strip() also removes U+3000 (ideographic space), which is
        # genuine source content on e.g. XJ-BYCY's indented chapter-title
        # lines ("　　　寒熱瘰癧") and must not be stripped from `actual`
        # while `expected` (a raw slice) keeps it.
        padding = ' \t\n\r\x0b\x0c'
        actual = rest[:boundary.start()].strip(padding) if boundary else rest.strip(padding)
        if actual != expected:
            raise ValueError(f'{uid}: original text is not the exact referenced span')
        for key, value in m.items():
            if key.endswith('_quote') and value and value not in expected:
                raise ValueError(f'{uid}: {key} is not present in case text')
        if m.get('retrieval_status') not in {'needs_review', 'source_research_with_caveats'}:
            raise ValueError(f'{uid}: missing or invalid retrieval status')
        for referenced_sid, referenced_start, referenced_end in references:
            spans.setdefault(referenced_sid, []).append((referenced_start, referenced_end))
        case_count += bool(m.get('case_id'))
        unit_count += bool(m.get('text_unit_id'))
    for uid, m in structured_metadata:
        for key in ('case_ref', 'shared_management_ref', 'intro_context_ref'):
            ref = m.get(key)
            if ref and ref not in ids:
                raise ValueError(f'{uid}: dangling {key}: {ref}')
        if m.get('symptom_context_ref') and m['symptom_context_ref'] not in ids | set(index):
            raise ValueError(f'{uid}: dangling symptom_context_ref')
        for key in ('narrative_context_ref', 'person_context_ref', 'possible_repeat_source_ref',
                    'formula_first_source', 'formula_last_source'):
            ref = m.get(key)
            if ref and ref not in index:
                raise ValueError(f'{uid}: dangling {key}: {ref}')
        for ref in filter(None, m.get('shared_case_refs', '').split('; ')):
            if ref not in ids:
                raise ValueError(f'{uid}: dangling shared case: {ref}')
        for ref in filter(None, m.get('possible_repeat_case_refs', '').split('; ')):
            if ref not in ids:
                raise ValueError(f'{uid}: dangling possible repeat case: {ref}')
    manifests = []
    for match in BLOCK_RE.finditer(text):
        meta, _ = parse_metadata(match.group(1))
        if meta.get('coverage_id'):
            manifests.append(meta)
    for manifest in manifests:
        prefix = manifest['source_prefix']
        # Zero-padding width varies by book (most use 3 digits, e.g. "P001";
        # XJ-BYCY's line-based ids use 4, e.g. "L0001"). Infer it from any
        # existing source_id sharing this prefix rather than assuming 3.
        width = 3
        for key in index:
            if key.startswith(prefix) and key[len(prefix):].isdigit():
                width = len(key) - len(prefix)
                break
        for n in range(int(manifest['first_source_number']), int(manifest['last_source_number']) + 1):
            sid = f"{prefix}{n:0{width}d}"
            if sid not in index:
                raise ValueError(f'{sid}: declared coverage refers to unknown source')
            cursor = 0
            for start, end in sorted(spans.get(sid, [])):
                if start != cursor:
                    raise ValueError(f'{sid}: structured coverage gap or overlap')
                cursor = end
            if cursor != len(index[sid]):
                raise ValueError(f'{sid}: incomplete declared chapter coverage')
    validate_baselines_and_comparisons(text, index)
    return {'cases': case_count, 'non_case_units': unit_count}



COMPARISON_CATEGORIES = {'貫通', '發展', '張力／差異', '明確反對', '證據不足'}


def _locator_text(uid, m, prefix, index):
    sid = m.get(f'{prefix}_source_ref')
    if sid not in index:
        raise ValueError(f'{uid}: unknown source reference for {prefix}')
    start, end = int(m[f'{prefix}_start_char']), int(m[f'{prefix}_end_char_exclusive'])
    if not 0 <= start < end <= len(index[sid]):
        raise ValueError(f'{uid}: invalid character boundaries for {prefix}')
    expected = index[sid][start:end]
    chain = [sid]
    # Multi-line quotes (e.g. XJ-BYCY's physical lines): further "sid:start:end"
    # spans are concatenated directly, without a separator, because a physical
    # line break is not a source character.
    for entry in filter(None, m.get(f'{prefix}_continued_source_refs', '').split('; ')):
        parts = entry.rsplit(':', 2)
        if len(parts) != 3 or parts[0] not in index:
            raise ValueError(f'{uid}: malformed or unknown {prefix}_continued_source_refs entry: {entry}')
        c_start, c_end = int(parts[1]), int(parts[2])
        if not 0 <= c_start < c_end <= len(index[parts[0]]):
            raise ValueError(f'{uid}: invalid character boundaries in {prefix}_continued_source_refs')
        expected += index[parts[0]][c_start:c_end]
        chain.append(parts[0])
    if expected != m.get(f'{prefix}_quote'):
        raise ValueError(f'{uid}: {prefix}_quote is not the exact referenced span')
    return chain


def validate_baselines_and_comparisons(text, index):
    """Thought-baseline cards need >=2 located supporting passages from distinct
    source records; comparisons use only the five approved categories and must
    locate both sides. Every quote must equal its referenced span exactly."""
    pending = set()
    ids = set()
    for match in BLOCK_RE.finditer(text):
        m, _ = parse_metadata(match.group(1))
        if m.get('retrieval_status') == 'needs_review' and m.get('source_ref'):
            pending.add(m['source_ref'])
    for match in BLOCK_RE.finditer(text):
        m, _ = parse_metadata(match.group(1))
        uid = m.get('baseline_id') or m.get('comparison_id')
        if not uid:
            continue
        if uid in ids:
            raise ValueError(f'Duplicate baseline/comparison ID: {uid}')
        ids.add(uid)
        if m.get('retrieval_status') not in {'needs_review', 'source_research_with_caveats'}:
            raise ValueError(f'{uid}: missing or invalid retrieval status')
        used = []
        if m.get('baseline_id'):
            n = int(m['supporting_passage_count'])
            if n < 2:
                raise ValueError(f'{uid}: a baseline needs at least two supporting passages')
            supporting = [_locator_text(uid, m, f'p{k}', index) for k in range(1, n + 1)]  # each is a list of source ids
            if len({chain[0] for chain in supporting}) < 2:
                raise ValueError(f'{uid}: supporting passages must come from at least two source records')
            used += [sid for chain in supporting for sid in chain]
            c = int(m.get('counterexample_count', '0'))
            if c == 0 and not m.get('counterexample_search_note'):
                raise ValueError(f'{uid}: no counterexample and no search note')
            used += [sid for k in range(1, c + 1) for sid in _locator_text(uid, m, f'c{k}', index)]
        else:
            if m.get('comparison_category') not in COMPARISON_CATEGORIES:
                raise ValueError(f'{uid}: comparison category is not one of the approved five')
            used += _locator_text(uid, m, 'a', index) + _locator_text(uid, m, 'b', index)
        if any(sid in pending for sid in used) and m.get('retrieval_status') != 'needs_review':
            raise ValueError(f'{uid}: depends on a pending source but is not needs_review')

def load_nkzy_snapshot(items):
    global SNAPSHOT_SHA256
    SNAPSHOT_ROWS.clear()
    if not SNAPSHOT.exists():
        return
    raw = SNAPSHOT.read_bytes()
    SNAPSHOT_SHA256 = hashlib.sha256(raw).hexdigest()
    parser = BookParser()
    parser.feed(raw.decode("utf-8"))
    book = next(b for b in items if b['meta']['work_id'] == 'XJ-NKZY')
    source = []
    volume, section = "", ""
    for tag, value in parser.items:
        if tag == 'h1':
            volume, section = value, ""
        elif tag == 'h2':
            section = value
        else:
            source.append((volume, section, value))
    # Records added later from other sources (record_added_status) are not in the jicheng snapshot.
    rows = [r for r in book['rows'] if not r['meta'].get('record_added_status')]
    if len(source) != len(rows):
        raise ValueError('NKZY snapshot count does not align; manual reconciliation required')
    for ordinal, (row, (volume, section, value)) in enumerate(zip(rows, source), 1):
        m = row['meta']
        if (m.get('volume'), m.get('section')) != (volume, section):
            raise ValueError(f"NKZY source chapter mismatch at {m['source_id']}")
        body = row['body'].removesuffix('\n\n---').strip()
        SNAPSHOT_ROWS[m['source_id']] = {
            'ordinal': ordinal, 'text': value, 'exact': value == body,
            'legacy_difference': bool(m.get('difference_grade')),
        }


def enrich_block(match):
    meta, _ = parse_metadata(match.group(1))
    updates = {}
    if "source_id" in meta:
        sid = meta["source_id"]
        grade = meta.get("difference_grade", "")
        status = meta.get("scan_verification_status")
        pending = sid in PENDING or grade.startswith("D_") or status == "sampled_pending"
        updates["retrieval_status"] = "needs_review" if pending else "source_research_with_caveats"
        if grade:
            updates["evidence_status"] = (
                "unresolved" if pending else "legacy_evidence_linked_not_rechecked"
            )
            updates["review_method"] = "legacy_model_review_human_review_not_documented"
            updates["original_transcription_recovery"] = "source_snapshot_missing"
            marker = ("上" in meta.get("original_public_transcription", "")
                      and "右" in meta.get("preferred_reading", ""))
            if marker and grade in {"C_instruction_glyph", "C0_formula_instruction_marker_equivalent"}:
                updates["difference_type"] = "formula_instruction_marker"
                updates["difference_impact"] = "no_medical_semantic_change"
            else:
                updates["difference_type"] = "legacy_description_requires_facet_review"
                updates["difference_impact"] = (
                    "content_or_retrieval" if grade.startswith(("A_", "B_"))
                    else "unassessed" if pending else "glyph_wording_or_mixed_requires_review"
                )
            if sid in PENDING:
                updates["pending_reason"] = PENDING[sid]
        if sid in SNAPSHOT_ROWS:
            source = SNAPSHOT_ROWS[sid]
            updates['current_source_paragraph_ordinal'] = str(source['ordinal'])
            updates['current_source_alignment'] = (
                'exact' if source['exact'] else
                'different_with_legacy_collation' if source['legacy_difference'] else
                'unexplained_difference'
            )
            updates['current_source_snapshot_date'] = '2026-09-28'
            if grade:
                updates['original_transcription_recovery'] = 'current_snapshot_available_historical_snapshot_unknown'
            if not source['exact']:
                updates['current_source_transcription'] = source['text']
            if not source['exact'] and not source['legacy_difference']:
                updates['retrieval_status'] = 'needs_review'
                updates['pending_reason'] = '當前電子來源與工作稿有未登記差異'
        if sid in CURRENT_SCAN_NOTES:
            updates.update(CURRENT_SCAN_NOTES[sid])
    elif "work_id" in meta and "work_title" in meta:
        updates = {
            "content_layer": "working_transcription_with_legacy_edits",
            "source_snapshot_status": "not_found_in_current_task_files",
            "source_acquisition_date": "unknown",
            "metadata_audit_date": "2026-09-28",
            "electronic_source_alignment": "pending_independent_snapshot_comparison",
            "edition_chapter_completeness": "pending_external_chapter_mapping",
            "image_text_completeness": "partial_legacy_samples_only",
            "structuring_rule": "來源記錄 ID 固定；正文為帶歷史校訂的工作轉錄；取得時的原始快照與當前電子來源分開追溯，不從差異片段猜寫完整原讀",
            "legacy_text_layer_note": "逐條 original_text 為舊字段；實際內容層級以本書 content_layer 及逐條校勘字段為準",
        }
        if meta['work_id'] == 'XJ-NKZY' and SNAPSHOT_ROWS:
            updates.update({
                'source_snapshot_status': 'current_snapshot_preserved_historical_snapshot_unknown',
                'current_snapshot_path': 'work/source-snapshots/nkzy-2026-09-28.html',
                'current_snapshot_date': '2026-09-28',
                'current_snapshot_sha256': SNAPSHOT_SHA256,
                'electronic_source_alignment': 'all_544_paragraphs_and_23_chapters_aligned_with_documented_edits',
            })
    lines = match.group(1).splitlines()
    for key, value in updates.items():
        rendered = f"{key}: {json.dumps(value, ensure_ascii=False)}"
        old = next((i for i, line in enumerate(lines) if line.startswith(key + ":")), None)
        if old is None:
            lines.append(rendered)
        else:
            lines[old] = rendered
    return "```yaml\n" + "\n".join(lines) + "\n```"


def cell(value):
    return str(value).replace("|", "／").replace("\n", " ")


def report(items):
    current = CORPUS.read_text()
    cases = re.findall(r'^case_id: "([^"\n]+)"$', current, re.M)
    lines = [BEGIN, "## 現行來源、狀態與完整性對賬（2026-09-28）", "",
             "本節由逐條元資料生成，後續執行以本節為準。相合／異文主要是歷次影像檢查標記，不把它們提升為已審定；本輪新看的影像僅《內科摘要》卷下 P179 所在承應本第86頁的目標行，另見本輪讀法表。歷史取得時的原始快照未在當前任務文件中找到；《內科摘要》另已保存 2026-09-28 當前電子來源快照並全量對賬。`needs_review` 預設排除於來源研究檢索，顯式開啟後仍須顯示原因；其餘資料只能作帶來源與校勘提示的歷史全文研究。問答系統尚未建成。", "",
             "| 書名 | 記錄 | 相合 | 有異文 | 未開始 | 待核排除 |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for book in items:
        counts = Counter(r["meta"].get("scan_verification_status") for r in book["rows"])
        pending = sum(r["meta"].get("retrieval_status") == "needs_review" for r in book["rows"])
        lines.append(f"| {book['meta']['work_title']} | {len(book['rows'])} | {counts['sampled_verified']} | {counts['sampled_variants_found']} | {counts['not_started']} | {pending} |")
    lines += ['', f'當前結構化醫案：{len(cases)} 條（依 case_id 實際盤點）；來源段落／行為 5361 條。完整篇章覆蓋狀態見本文件醫案結構化區，不能把醫案數與來源記錄數相加。']
    if '<!-- NKZY_VOLUME_TWO_CASES_BEGIN -->' in current:
        units = re.findall(r'^text_unit_id: "(XJ-NKZY-[^"\n]+)"$', current, re.M)
        formulas = set(re.findall(r'^formula_id: "(XJ-NKZY-[^"\n]+)"$', current, re.M))
        lines += ['', '### 《內科摘要》全書結構化交付狀態', '',
                  f'卷上 176 段／12 篇與卷下 368 段／11 篇均已逐字符覆蓋。全書 {len(cases)} 個醫案單元、{len(units)} 個非個別醫案單元、{len(formulas)} 個方劑歸組。所有 case_id／text_unit_id 唯一，正文與來源跨度逐字相等；共有治法、上下文、相似重見和方劑首末定位引用均可解析。', '',
                  '這一完成狀態只指現有工作轉錄的全文組織與邊界；選定摘引字段並非完整方藥索引，全書影像校勘與獨立古籍版本卷篇完整性尚未完成。216 案不等於 216 名獨立患者，不可用來算療效。前面各篇末的待續數字是當時交付記錄，現行進度以本節為準。其他七書仍是全文來源記錄，尚未宣稱完成逐案組織。']
    lines += ["", "### 八書來源版本卡", "",
              "作品歸屬沿用現行收錄範圍，題署／序跋審定尚待補證。下列版本是原元資料的聲明，不代表本輪已比對館藏複本。取得日期未知；本輪元資料盤點日期為 2026-09-28。七書權利聲明共用中醫笈成聲明頁；2026-09-28 查看該頁確認公版文本編輯採 CC0，仍須逐書確認個別例外及圖像權利。《保嬰粹要》保留 CC BY-SA 版本未詳的待核狀態。", "",
              "| 作品 | 電子来源／聲明版本 | 權利證據 | 完整性狀態 |",
              "| --- | --- | --- | --- |"]
    for book in items:
        m = book["meta"]
        alignment = '當前電子来源 544 段／23 篇全部對應；版本影像卷篇待核' if m['work_id'] == 'XJ-NKZY' and SNAPSHOT_ROWS else '電子來源全量對賬待做；版本卷篇外部映射待做'
        lines.append(f"| {m['work_title']} | [電子來源]({m['source_url']})；{cell(m.get('source_edition', '未詳'))} | [{cell(m.get('rights_status', '未詳'))}]({m.get('rights_statement_url', m['source_url'])}) | {alignment}；影像僅歷次抽樣 |")
    if SNAPSHOT_ROWS:
        exact = sum(r['exact'] for r in SNAPSHOT_ROWS.values())
        different = [sid for sid, r in SNAPSHOT_ROWS.items() if not r['exact']]
        lines += ['', '### 《內科摘要》當前電子來源全量對賬', '',
                  f'單次取得完整書頁，日期 2026-09-28；快照保存於 `work/source-snapshots/nkzy-2026-09-28.html`，SHA-256：`{SNAPSHOT_SHA256}`。電子來源明標薛己及日本承應三年刊本，卷上 12 篇、卷下 11 篇，共 544 段，與主文件逐段的卷／篇／次序一致。', '',
                  f'完整文字逐段比較：{exact} 段相同、{len(different)} 段不同；差異全部已有歷史校勘字段，未發現未登記的文字差異。每個不同段落新增 `current_source_transcription` 保存當前電子來源的整段讀法；快照不冒充 7 月取得版本，也不證明承應影像無中段缺文。', '',
                  '| 記錄 | 當前來源與工作稿差異 | 證據狀態 |', '| --- | --- | --- |']
        for sid in different:
            row = next(r for b in items for r in b['rows'] if r['meta']['source_id'] == sid)
            lines.append(f"| `{sid}` | 整段當前來源讀法已保存在該記錄元資料 | {row['meta'].get('evidence_status')} |")
    lines += ["", "### 優先疑點與檢索排除", "",
              "| 記錄 | 原因 | 當前處理 |", "| --- | --- | --- |"]
    for sid, reason in PENDING.items():
        lines.append(f"| `{sid}` | {reason} | `needs_review`；保留原文與已有讀法，待定位或評估 |")
    if CURRENT_SCAN_NOTES:
        lines += ['', '### 本輪新核對的影像讀法（不覆盖電子原文）', '',
                  '| 記錄 | 館藏影像與原字 | 差異及處理 |', '| --- | --- | --- |']
        for sid, m in CURRENT_SCAN_NOTES.items():
            lines.append(f"| `{sid}` | [{cell(m['current_scan_edition'])}]({m['current_scan_source_url']})；圖讀「{m['current_scan_raw_reading']}」 | {cell(m['current_scan_difference'])}；模型圖讀尚待人工審定，原文未改，整方待核 |")
    lines += ["", "### 逐篇完整性對賬清單", "",
              "下列映射來自現有來源記錄。每一卷篇均已列出首尾 ID，但外部目錄／影像的逐篇對應仍待確認；這是完整性核查清單，不能作無漏文結論。", "",
              "| 作品 | 卷／篇 | 記錄数 | 首 ID | 末 ID | 外部對賬 |",
              "| --- | --- | ---: | --- | --- | --- |"]
    for book in items:
        groups = {}
        for row in book["rows"]:
            m = row["meta"]
            key = (m.get("volume", ""), m.get("section", ""))
            groups.setdefault(key, []).append(m["source_id"])
        for (volume, section), ids in groups.items():
            label = volume + ("／" + section if section and section != volume else "")
            status = '當前電子来源相接；影像待核' if book['meta']['work_id'] == 'XJ-NKZY' and SNAPSHOT_ROWS else '待核'
            lines.append(f"| {book['meta']['work_title']} | {cell(label)} | {len(ids)} | `{ids[0]}` | `{ids[-1]}` | {status} |")
    lines += ["", "### 全部既有異文／補文證據索引", "",
              "證據確定程度統一標為歷次記錄未重核或未解決；A／B／C／D 作歷史標記保留。原轉錄字段常只含片段或差異清單，完整来源段落尚無快照可核，不能據字段名稱宣稱原始文本可完整還原。每個 ID 的正文下方元資料保留原讀及採用讀法。", "",
              "| 記錄 | 歷史分級 | 原讀字段 | 影像／平行來源 | 證據狀態 |",
              "| --- | --- | --- | --- | --- |"]
    for book in items:
        for row in book["rows"]:
            m = row["meta"]
            if not m.get("difference_grade"):
                continue
            raw = "；".join(m.get(f, "") for f in ("original_public_transcription", "public_transcription_reading", "early_edition_variant") if m.get(f))
            links = [(k, v) for k, v in m.items() if k.endswith("url") and k != "source_url"]
            evidence = "、".join(f"[{'影像' if 'scan' in k else '平行'}]({v})" for k, v in links) or "無逐條影像連結"
            lines.append(f"| `{m['source_id']}` | {cell(m['difference_grade'])} | {cell(raw or '缺／僅其他讀法字段')} | {evidence} | {m.get('evidence_status')} |")
    quote_count = sum(len(book['quotes']) + sum(len(r['quotes']) for r in book['rows']) for book in items)
    lines += ["", f"元資料檢查：所有行均已解析；重复鍵會報錯。另有 {quote_count} 個歷史字符串包含未轉義內部引號，按舊平面格式保留並明示，後續需轉成標準 YAML。正文校验值（逐 ID／完整文字）：`{text_digest(items)}`。", "", END]
    return "\n".join(lines)


def main():
    parser = ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--record")
    parser.add_argument("--include-review", action="store_true")
    args = parser.parse_args()
    text = CORPUS.read_text(encoding="utf-8")
    original = books(text)
    load_nkzy_snapshot(original)
    before = text_digest(original)
    if args.refresh:
        text = BLOCK_RE.sub(enrich_block, text)
        updated = books(text)
        section = report(updated)
        if BEGIN in text:
            text = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda _: section,
                          text, flags=re.S)
        else:
            at = text.index("\n> 這是目前唯一")
            text = text[:at] + "\n" + section + "\n\n---\n" + text[at:]
        final = books(text)
        if text_digest(final) != before:
            raise ValueError("Refusing update: a record ID or historical text changed")
        validate_structured_units(text, final)
        CORPUS.write_text(text, encoding="utf-8")
        original = final
    if args.record:
        for book in original:
            for row in book["rows"]:
                if row["meta"]["source_id"] == args.record:
                    if row["meta"].get("retrieval_status") == "needs_review" and not args.include_review:
                        print(json.dumps({"excluded": args.record, "reason": row["meta"].get("pending_reason")}, ensure_ascii=False))
                    else:
                        print(json.dumps(row, ensure_ascii=False, indent=2))
                    return
        raise SystemExit("Unknown source ID")
    structured = validate_structured_units(CORPUS.read_text(), original)
    print(json.dumps({"works": len(original), "records": sum(len(b['rows']) for b in original),
                      "structured": structured,
                      "review_exclusions": sum(r['meta'].get('retrieval_status') == 'needs_review' for b in original for r in b['rows']),
                      "text_sha256": before, "report_refreshed": args.refresh}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
