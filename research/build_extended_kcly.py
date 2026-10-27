#!/usr/bin/env python3
"""Reproduce manually selected independent dimensions for 20 KCLY or ZTLY cases.
No inference from prescriptions, disease names, or empty fields.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
import build_close_read_160 as review

ROOT=review.ROOT
FIELDS=('pulse','tongue_features','habitus','habits')
INPUT=ROOT/'research/review_inputs/KCLY_extended.tsv'
OUT=ROOT/'research/samples/extended_kcly_20_v1.jsonl'
SUMMARY=ROOT/'research/samples/extended_kcly_20_summary.json'
READABLE=ROOT/'research/samples/EXTENDED_KCLY_20_V1.md'


def build(work="KCLY"):
    if work not in {"KCLY", "ZTLY"}:raise ValueError("Unsupported extended work")
    _,sample,index=review.build()
    cases={c['case_id']:c for c in sample if c['work_ref']=='XJ-'+work}
    choices={}
    with (ROOT/f'research/review_inputs/{work}_extended.tsv').open(newline='') as f:
        for row in csv.reader(f,delimiter='\t'):
            if len(row)!=5:raise ValueError('Extended input requires five columns')
            cid='XJ-'+work+'-C-'+row[0]
            if cid in choices:raise ValueError('Duplicate extended case')
            choices[cid]=dict(zip(FIELDS,row[1:]))
    if set(choices)!=set(cases):raise ValueError('Extended roster must match exactly 20 cases of the selected work')
    records=[]
    for cid,choice in choices.items():
        c=cases[cid];fields={}
        for field,tokens in choice.items():
            observations=[]
            for token in tokens.split('¦') if tokens else []:
                obs=review.make_observation(c,'symptoms',token,index,{})
                reading=obs['reading_joined_source_segments']
                if field=='pulse':kind='narrated_pulse_description_not_modern_measurement'
                elif field=='tongue_features':kind='reported_tongue_swelling_not_formal_tongue_exam'
                elif field=='habitus' and reading=='稟實年壯':kind='narrator_constitution_and_age_assessment_not_objective_measurement'
                elif field=='habitus':kind='contemporaneous_body_description_not_premorbid_constitution'
                elif '怒' in reading:kind='habitual_affect_description_not_episode_trigger'
                elif '膏粱' in reading:kind='narrator_dietary_social_descriptor_not_measured_intake'
                else:kind='reported_drinking_habit_no_quantity_or_dependency_inferred'
                obs['interpretation_type']=kind
                observations.append(obs)
            fields[field]={'status':'model_selected_evidence' if observations else 'not_identified_in_model_case_read',
                           'missingness':None if observations else 'unrecorded_or_unresolved_not_explicit_absence',
                           'observations':observations}
        records.append({'case_id':cid,'work_ref':'XJ-'+work,'review_date':'2026-10-27',
            'source_git_blob':review.base.BLOB_SHA_AT_FREEZE,
            'case_text_sha256':hashlib.sha256(c['body'].encode()).hexdigest(),
            'review_method':'model_selected_independent_dimensions_not_exhaustive',
            'human_adjudication':'pending','initial_query_export':'disabled_pending_expert_temporal_role_review',
            'fields':fields})
    return records,cases,index


def validate(records,cases,index):
    if len(records)!=20 or {r['case_id'] for r in records}!=set(cases):raise ValueError('Extended roster drift')
    for row in records:
        c=cases[row['case_id']]
        if row['source_git_blob']!=review.base.BLOB_SHA_AT_FREEZE or row['case_text_sha256']!=hashlib.sha256(c['body'].encode()).hexdigest():
            raise ValueError('Extended source provenance drift')
        if row['human_adjudication']!='pending' or row['initial_query_export']!='disabled_pending_expert_temporal_role_review':
            raise ValueError('Unchecked extended verification or query claim')
        if set(row['fields'])!=set(FIELDS):raise ValueError('Four independent dimensions required')
        for field,data in row['fields'].items():
            obs=data['observations']
            if not obs and (data['status']!='not_identified_in_model_case_read' or data['missingness']!='unrecorded_or_unresolved_not_explicit_absence'):
                raise ValueError('Missing extended evidence is unresolved, not absent')
            if obs and (data['status']!='model_selected_evidence' or data['missingness'] is not None):
                raise ValueError('Extended presence metadata inconsistent')
            seen=set()
            for o in obs:
                q=o['reading_joined_source_segments']
                if q in seen:raise ValueError('Duplicate extended observation')
                seen.add(q)
                if o['evidence']!=review.evidence_for(c,q,index):raise ValueError('Extended literal evidence mapping drift')
                if o['initial_query_eligible'] is not False or o['time_phase'] not in review.PHASES:
                    raise ValueError('Unchecked extended query or phase')
                if field=='tongue_features' and o['interpretation_type']!='reported_tongue_swelling_not_formal_tongue_exam':
                    raise ValueError('Unsupported formal tongue-exam inference')


def summary(rows):
    all_obs=[o for r in rows for d in r['fields'].values() for o in d['observations']]
    return {'date':'2026-10-27','cases':len(rows),'dimension_slots':len(rows)*len(FIELDS),
            'cases_with_selected_evidence':{f:sum(bool(r['fields'][f]['observations']) for r in rows) for f in FIELDS},
            'observations':len(all_obs),'literal_spans':sum(len(o['evidence']) for o in all_obs),
            'phases':dict(Counter(o['time_phase'] for o in all_obs)),
            'human_adjudicated':0,'initial_query_exported':0,
            'scope':'independent_dimensions_separate_from_five_domain_totals'}


def render(rows):
    title='口齿' if rows[0]['work_ref']=='XJ-KCLY' else '正体'
    out=[f'# {title}20案：独立脉象、舌部观察、体形与习惯维度\n\n',
         '2026-10-27模型精选证据，非专家审校或穷尽标注。空字段保留未载/不明，不解释为患者没有。全部初诊查询导出禁用。\n\n',
         '舌肿是明载局部形态变化，不等同舌苔、舌色等正式舌诊；口舌生疮、舌痛不自动生成舌诊字段。骨立/瘦倦记录当时状态，不推断发病前体质。膏粱仅保留叙述者类别词，未量化饮食。善怒另标平素性情，不直接变成诱因。\n\n']
    for r in rows:
        out.append('## '+r['case_id']+'\n\n')
        for field,d in r['fields'].items():
            if not d['observations']:out.append(f'- {field}：本轮未选定证据，未载/不明。\n')
            for o in d['observations']:
                refs='; '.join(f"{e['source_ref']}[{e['source_start_char']}:{e['source_end_char_exclusive']})" for e in o['evidence'])
                out.append(f"- {field}：{o['reading_joined_source_segments']}；{o['time_phase']}；{o['interpretation_type']}；`{refs}`\n")
        out.append('\n')
    if rows[0]['work_ref']=='XJ-ZTLY':
        out[2]='本批未选到独立舌部观察或习惯证据，不等于患者没有。稟實年壯是叙述者的体质及年龄概括，不生成精确年龄、现代体格数值或客观体质诊断。脉象保留前药及后续阶段。\n\n'
    return ''.join(out).rstrip()+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--work',choices=['KCLY','ZTLY'],default='KCLY');a=p.parse_args()
    rows,cases,index=build(a.work);validate(rows,cases,index)
    stem=a.work.lower()
    out=ROOT/f'research/samples/extended_{stem}_20_v1.jsonl'
    summary_path=ROOT/f'research/samples/extended_{stem}_20_summary.json'
    readable=ROOT/f'research/samples/EXTENDED_{a.work}_20_V1.md'
    results={out:''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),
             summary_path:json.dumps(summary(rows),ensure_ascii=False,indent=2)+'\n',readable:render(rows)}
    for path,text in results.items():
        if a.write:path.write_text(text)
        if path.read_text()!=text:raise ValueError('Extended artifact drift: '+str(path.relative_to(ROOT)))
    validate([json.loads(l) for l in out.read_text().splitlines()],cases,index)
    print(json.dumps(summary(rows),ensure_ascii=False,indent=2))
    print('PASS: independent-dimension choices reproduce exact evidence; no absence or clinical validity inferred')

if __name__=='__main__':main()
