#!/usr/bin/env python3
"""Build/verify model-selected observations. No automatic clinical extraction.

Default is read-only; --write renders reviewed choices in review_inputs/*.tsv.
Offsets are Python Unicode code points in parser source bodies, end exclusive.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import reproduce_sample as base

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / 'research/review_inputs'
JSONL = ROOT / 'research/samples/close_read_160_v1.jsonl'
READABLE = ROOT / 'research/samples/CLOSE_READ_160_V1.md'
SUMMARY = ROOT / 'research/samples/close_read_160_summary.json'
FIELDS = base.FIELD_NAMES
PHASES = {'initial_narrator_window', 'later_narrator_window', 'unknown'}
PREFIXES = {'@post:', '@prior_response:', '@theory:', '@absent:', '@unknown:', '@post_absent:'}
DATE = '2026-10-26'


def freeze_check():
    raw = base.CORPUS.read_bytes()
    sha = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if sha != base.BLOB_SHA_AT_FREEZE:
        raise ValueError(f'Frozen corpus changed: {sha}')


def evidence_for(case, reading, index):
    """Map exact concatenation to original source slices, never invent a raw quote.

    Only parser-inserted separators between case source segments are omitted.
    Existing characters (including U+3000, spaces, punctuation) remain intact.
    A joined reading is displayed separately from each literal raw_quote.
    """
    joined = ''.join(case['parts'])
    start = joined.find(reading)
    if not reading or start < 0:
        raise ValueError(f"{case['case_id']}: quote not found: {reading!r}")
    if joined.find(reading, start + 1) >= 0:
        raise ValueError(f"{case['case_id']}: ambiguous quote; select a longer span: {reading!r}")
    stop = start + len(reading)
    evidence = []
    cursor = 0
    for part, span in zip(case['parts'], case['segments']):
        a, b = max(start, cursor), min(stop, cursor + len(part))
        if a < b:
            absolute_a = span['start'] + a - cursor
            absolute_b = span['start'] + b - cursor
            raw = index[span['source_ref']][absolute_a:absolute_b]
            evidence.append({'source_ref': span['source_ref'],
                             'source_start_char': absolute_a,
                             'source_end_char_exclusive': absolute_b,
                             'raw_quote': raw})
        cursor += len(part)
    if ''.join(e['raw_quote'] for e in evidence) != reading:
        raise ValueError('Joined reading differs from literal source slices')
    return evidence


def make_observation(case, field, token, index, overrides, role_overrides=None):
    phase = 'initial_narrator_window'
    role = 'case_narrator'
    assertion = 'narrated_observation'
    narrative = 'before_first_explicit_narrator_assessment_or_intervention'
    polarity = 'present'
    reading = token
    if token.startswith('@'):
        prefix = next((p for p in PREFIXES if token.startswith(p)), None)
        if prefix is None:
            raise ValueError(f'Unknown prefix {token}')
        reading = token[len(prefix):]
        if prefix == '@post:':
            phase = 'later_narrator_window'
            narrative = 'later_episode_or_after_first_narrator_assessment'
        elif prefix == '@post_absent:':
            phase, polarity = 'later_narrator_window', 'explicitly_absent'
            narrative = 'explicit_negative_after_first_narrator_assessment_or_care'
        elif prefix == '@prior_response:':
            narrative = 'after_earlier_treatment_before_narrator_assessment'
        elif prefix == '@theory:':
            phase, role, assertion = 'unknown', 'quoted_author', 'quoted_theory'
            narrative = 'theory_quoted_in_case_not_individual_observation'
        elif prefix == '@unknown:':
            phase, narrative = 'unknown', 'retrospective_state_no_narrator_encounter_recorded'
        elif prefix == '@absent:':
            polarity = 'explicitly_absent'
    if field == 'mechanism' and assertion != 'quoted_theory':
        assertion = 'physician_interpretation'
        narrative = ('later_episode_interpretation' if phase == 'later_narrator_window'
                     else 'first_recorded_case_explanation_not_objective_patient_fact')
    if field == 'prior_treatment':
        assertion, role = 'treatment_given', 'uncertain'
        narrative = ('later_intervening_treatment_before_later_episode_or_outcome'
                     if phase == 'later_narrator_window'
                     else 'earlier_intervention_before_narrator_assessment_actor_not_assumed')
    obj = {'reading_joined_source_segments': reading,
           'evidence': evidence_for(case, reading, index),
           'polarity': polarity, 'time_phase': phase,
           'relative_to': 'first_recorded_narrator_assessment_or_care_decision_including_advice',
           'speaker_role': role, 'assertion_type': assertion,
           'narrative_role': narrative,
           'certainty': 'model_interpretation_requires_expert_review',
           'initial_query_eligible': False}
    if field == 'trigger':
        obj['relation_type'] = 'narrated_trigger_relief_or_association_not_proven_causality'
    obj.update(overrides.get(case['case_id'], {}).get(field, {}) if not token.startswith('@') else {})
    selected = (role_overrides or {}).get(case['case_id'], {}).get(field, {}).get(reading, {})
    if not set(selected) <= {'speaker_role', 'assertion_type', 'narrative_role'}:
        raise ValueError('Role override may not alter evidence, phase or query status')
    obj.update(selected)
    return obj


def load_choices():
    choices = {}
    for work in sorted(base.WORK_NAMES):
        path = INPUTS / (work.removeprefix('XJ-') + '.tsv')
        with path.open(encoding='utf-8', newline='') as f:
            rows = list(csv.reader(f, delimiter='\t'))
        if len(rows) != 20:
            raise ValueError(f'{path}: expected 20 rows')
        for row in rows:
            if len(row) != 7:
                raise ValueError(f'{path}: expected 7 columns')
            cid = work + '-C-' + row[0]
            if cid in choices:
                raise ValueError(f'Duplicate review {cid}')
            choices[cid] = (dict(zip(FIELDS, row[1:6])), row[6])
    return choices


def scan_spots():
    from check_scan_spots import load_records
    index, _ = base.load()
    return [dict(spot, scan_record_ref=str(path.relative_to(ROOT)), scan_pdf_sha256=record['pdf_sha256'])
            for path, record in load_records(index) for spot in record['spots']]



def case_scan_refs(case, spots):
    return [spot['spot_id'] for spot in spots if any(
        span['source_ref'] == spot['source_ref'] and
        span['start'] <= spot['working_evidence']['source_start_char'] <
        spot['working_evidence']['source_end_char_exclusive'] <= span['end']
        for span in case['segments'])]



def build():
    freeze_check()
    index, all_cases = base.load()
    sample = base.choose_cases(all_cases)
    choices = load_choices()
    if set(choices) != {c['case_id'] for c in sample}:
        raise ValueError('Review choices do not exactly cover the frozen roster')
    overrides = json.loads((INPUTS / 'phase_overrides.json').read_text())
    if not set(overrides) <= set(choices):
        raise ValueError('Unknown case in phase overrides')
    role_overrides = json.loads((INPUTS / 'observation_role_overrides.json').read_text())
    for cid, fields in role_overrides.items():
        if cid not in choices:
            raise ValueError('Unknown case in role overrides')
        for field, readings in fields.items():
            if field not in FIELDS:
                raise ValueError('Unknown field in role overrides')
            selected = choices[cid][0][field].split('¦')
            selected = [t.split(':', 1)[1] if t.startswith('@') else t for t in selected]
            if not set(readings) <= set(selected):
                raise ValueError('Unused reading in role overrides')
    source_meta = {row['meta']['source_id']: row['meta']
                   for book in base.books(base.CORPUS.read_text(encoding='utf-8'))
                   for row in book['rows']}
    followup_by_id = {}
    for path in sorted(INPUTS.glob('*_second_pass.json')):
        followup = json.loads(path.read_text())
        work = followup['work_ref']
        expected = {c['case_id'] for c in sample if c['work_ref'] == work}
        found = {x['case_id'] for x in followup['cases']}
        if len(followup['cases']) != 20 or len(expected) != 20 or found != expected:
            raise ValueError('Second pass must cover exactly 20 cases of one known work')
        if followup['human_adjudication'] != 'pending':
            raise ValueError('Second-pass model record cannot claim human adjudication')
        for entry in followup['cases']:
            if entry['case_id'] in followup_by_id:
                raise ValueError('Duplicate second-pass case')
            followup_by_id[entry['case_id']] = dict(entry, date=followup['date'],
                ref=str(path.relative_to(ROOT)))
    spots = scan_spots()
    records = []
    for c in sample:
        selected, note = choices[c['case_id']]
        fields = {}
        for name, text in selected.items():
            tokens = text.split('¦') if text else []
            observations = [make_observation(c, name, token, index, overrides, role_overrides) for token in tokens]
            fields[name] = {
                'status': ('model_selected_evidence' if observations else
                           'not_identified_in_model_case_read'),
                'missingness': None if observations else 'unrecorded_or_unresolved_in_this_case_window',
                'observations': observations,
            }
        provenance = []
        for sid in dict.fromkeys(sp['source_ref'] for sp in c['segments']):
            md = source_meta[sid]
            keep = {k: md[k] for k in ('source_id', 'work_id', 'volume', 'section', 'folio',
                    'source_location', 'source_url', 'scan_source_url', 'rights_status',
                    'retrieval_status') if k in md}
            keep['source_metadata_is_legacy_not_new_scan_verification'] = True
            provenance.append(keep)
        scan_refs = case_scan_refs(c, spots)
        audit = followup_by_id.get(c['case_id'])
        if audit and audit['case_text_sha256'] != hashlib.sha256(c['body'].encode()).hexdigest():
            raise ValueError('Second-pass case digest drift')
        records.append({
            'case_id': c['case_id'], 'work_ref': c['work_ref'],
            'sample_stratum': c['stratum'], 'review_date': DATE,
            'review_method': 'model_full_case_read_selected_observations_not_exhaustive',
            'model_review_passes': 2 if audit else 1,
            'followup_review_ref': audit['ref'] if audit else None,
            'latest_model_review_date': audit['date'] if audit else DATE,
            'human_adjudication': 'pending',
            'original_print_image_verification_this_pass': ('targeted_spots_only_not_full_case' if scan_refs else 'not_performed'),
            'targeted_print_spot_refs': scan_refs,
            'source_git_blob': base.BLOB_SHA_AT_FREEZE,
            'case_text_sha256': hashlib.sha256(c['body'].encode()).hexdigest(),
            'case_source_spans': c['segments'],
            'source_provenance': provenance,
            'retrieval_status': c['md'].get('retrieval_status', 'unknown'),
            'default_retrieval_excluded': c['md'].get('retrieval_status') == 'needs_review',
            'initial_query_export': 'disabled_pending_expert_temporal_role_review',
            'fields': fields, 'interpretation_note': note,
        })
    return records, sample, index


def validate_records(records, sample, index):
    by_id = {c['case_id']: c for c in sample}
    if len(records) != 160 or len({r['case_id'] for r in records}) != 160:
        raise ValueError('Must contain 160 unique reviewed cases')
    spots = scan_spots()
    for row in records:
        c = by_id[row['case_id']]
        expected_scan_refs = case_scan_refs(c, spots)
        expected_scan_status = 'targeted_spots_only_not_full_case' if expected_scan_refs else 'not_performed'
        if set(row['fields']) != set(FIELDS):
            raise ValueError('Five domains required')
        if row['human_adjudication'] != 'pending' or row['original_print_image_verification_this_pass'] != expected_scan_status or row['targeted_print_spot_refs'] != expected_scan_refs:
            raise ValueError('Unsupported verification claim')
        if row['default_retrieval_excluded'] != (c['md'].get('retrieval_status') == 'needs_review'):
            raise ValueError('Pending source exclusion lost')
        if row['source_git_blob'] != base.BLOB_SHA_AT_FREEZE:
            raise ValueError('Source blob provenance drift')
        if row['case_text_sha256'] != hashlib.sha256(c['body'].encode()).hexdigest():
            raise ValueError('Case digest drift')
        for name, field in row['fields'].items():
            if not field['observations']:
                if field['status'] != 'not_identified_in_model_case_read' or not field['missingness']:
                    raise ValueError('Missing evidence must remain explicitly unresolved')
            observed = set()
            for obs in field['observations']:
                reading = obs['reading_joined_source_segments']
                if reading in observed:
                    raise ValueError('Duplicate observation in domain')
                observed.add(reading)
                if obs['time_phase'] not in PHASES or obs['initial_query_eligible'] is not False:
                    raise ValueError('Unsupported phase or unchecked query export')
                if obs['polarity'] not in {'present', 'explicitly_absent', 'uncertain'}:
                    raise ValueError('Unknown polarity')
                if not obs['evidence']:
                    raise ValueError('Observation has no evidence')
                for ev in obs['evidence']:
                    a, b = ev['source_start_char'], ev['source_end_char_exclusive']
                    if not any(sp['source_ref'] == ev['source_ref'] and
                               sp['start'] <= a < b <= sp['end'] for sp in c['segments']):
                        raise ValueError('Evidence outside case')
                    if index[ev['source_ref']][a:b] != ev['raw_quote']:
                        raise ValueError('Literal evidence mismatch')
                if ''.join(ev['raw_quote'] for ev in obs['evidence']) != obs['reading_joined_source_segments']:
                    raise ValueError('Joined reading mismatch')
                if obs['evidence'] != evidence_for(c, reading, index):
                    raise ValueError('Evidence is not the canonical case-local source mapping')
                if name == 'mechanism' and obs['assertion_type'] not in {
                        'physician_interpretation', 'patient_interpretation', 'quoted_theory',
                        'reported_prior_interpretation_actor_uncertain'}:
                    raise ValueError('Mechanism confused with objective observation')


def render(records, sample):
    title = '# 160案逐案模型复读：五领域精选证据（V1）\n\n'
    warning = (f"{DATE}初读；{sum(r['model_review_passes']==2 for r in records)}案已完成第二遍模型复审，逐案日期见相应复审记录。"
               '每案完整窗口已由模型阅读，以下为精选证据，**不是穷尽临床标注、专家审核或原刻影像校定**。另有多书指定字句影像点核，见对应案例及独立影像记录；不升级为整案校定。'
               '未选到证据保留不确定，不解释为患者没有。\n\n'
               'initial/later window 相对于首次明确叙述者评议或处置；later 包括评议后拒治、自服及后来复发，不等于已接受首次治疗。'
               '病机、理论和后续表现不能直接导出初诊查询。全部初诊查询导出暂禁用。\n\n'
               '原文保留各来源片段；“／”仅为显示片段分隔符，不是底本字。Unicode码点区间均为左闭右开。'
               '来源及许可见仓库 NOTICE.md。Kanripo 保婴文本归属 Kanseki Repository (KR3e0070)；标注CC BY-SA 4.0，代码MIT。\n\n')
    out = [title, warning]
    for i, (r, c) in enumerate(zip(records, sample), 1):
        out.append(f"## {i:03d} · {r['case_id']}\n\n")
        scan_label = '仅指定字句影像点核，非全案校定' if r['targeted_print_spot_refs'] else '本轮未核'
        out.append(f"来源状态：`{r['retrieval_status']}`；原刻：{scan_label}；人工审校待办。\n\n")
        out.append('案文窗口：\n\n')
        for part, sp in zip(c['parts'], c['segments']):
            out.append(f"`{sp['source_ref']}[{sp['start']}:{sp['end']})`\n\n> {part.replace(chr(10), chr(10)+'> ')}\n\n")
        labels = dict(zip(FIELDS, ['症状','诱发/缓解关联','病程','干预前史/后续插入干预','病机解释']))
        for name, f in r['fields'].items():
            if not f['observations']:
                out.append(f"- **{labels[name]}**：本次复读未选定证据；未载/归属不明待专家确认。\n")
            for obs in f['observations']:
                refs = '; '.join(f"{e['source_ref']}[{e['source_start_char']}:{e['source_end_char_exclusive']})" for e in obs['evidence'])
                raw = ' ／ '.join(e['raw_quote'] for e in obs['evidence'])
                out.append(f"- **{labels[name]}**：{raw}（{obs['time_phase']}；{obs['speaker_role']}；{obs['assertion_type']}；{obs['polarity']}） `{refs}`\n")
        out.append('\n复读意见：'+r['interpretation_note']+'\n\n')
    return ''.join(out)


def summary(records):
    observations = [o for r in records for f in r['fields'].values() for o in f['observations']]
    return {
        'date': max(r['latest_model_review_date'] for r in records),
        'initial_review_date': DATE, 'cases': len(records), 'domains': len(records)*5,
        'cases_per_work': dict(sorted(Counter(r['work_ref'] for r in records).items())),
        'domains_with_evidence': dict((k,sum(bool(r['fields'][k]['observations']) for r in records)) for k in FIELDS),
        'observations': len(observations),
        'literal_source_spans': sum(len(o['evidence']) for o in observations),
        'multi_segment_observations': sum(len(o['evidence'])>1 for o in observations),
        'phases': dict(Counter(o['time_phase'] for o in observations)),
        'default_retrieval_excluded': sum(r['default_retrieval_excluded'] for r in records),
        'human_adjudicated_cases': 0, 'print_images_checked_this_pass': len({(s['scan_pdf_sha256'],s['pdf_page']) for s in scan_spots()}),
        'full_case_print_collations_this_pass': 0,
        'targeted_print_spot_review_refs': sorted({s['scan_record_ref'] for s in scan_spots()}),
        'targeted_print_spots_recorded': len(scan_spots()),
        'initial_query_exported': 0,
        'cases_with_second_model_pass': sum(r['model_review_passes'] == 2 for r in records),
        'interpretation_scope': 'initial_model_read_all_cases_followup_scope_in_per_case_records_not_exhaustive',
        'source_git_blob': base.BLOB_SHA_AT_FREEZE,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    records,sample,index=build()
    validate_records(records,sample,index)
    results={JSONL: ''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in records),
             READABLE: render(records,sample),
             SUMMARY: json.dumps(summary(records),ensure_ascii=False,indent=2)+'\n'}
    for path,text in results.items():
        if args.write:
            path.write_text(text,encoding='utf-8')
        if path.read_text(encoding='utf-8') != text:
            raise ValueError(f'Review output drift: {path.relative_to(ROOT)}')
    # Independently validate the serialized artifact, not just in-memory objects.
    validate_records([json.loads(line) for line in JSONL.read_text().splitlines()],sample,index)
    print(json.dumps(summary(records),ensure_ascii=False,indent=2))
    print('PASS: reviewed choices reproduce all outputs; every quoted segment is exact and inside its case')


if __name__=='__main__':
    main()
