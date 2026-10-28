#!/usr/bin/env python3
"""Reproduce manually selected independent dimensions for 20 cases in KCLY, ZTLY, NKCZ, NKZY or WKSY.
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


def interpretation_kind(field,reading):
    """Type already selected evidence; never turn unknown background into drinking."""
    if field=='pulse' and reading=='脈洪大，脈欲絕也':return 'narrated_pulse_with_narrator_prognostic_interpretation'
    if field=='pulse':return 'narrated_pulse_description_not_modern_measurement'
    if field=='tongue_features':return 'reported_tongue_swelling_not_formal_tongue_exam'
    if field=='habitus' and reading=='稟實年壯':return 'narrator_constitution_and_age_assessment_not_objective_measurement'
    if field=='habitus':return 'contemporaneous_body_description_not_premorbid_constitution'
    if reading=='日飲冰水數碗':return 'episode_drinking_behavior_not_premorbid_habit'
    if '怒' in reading:return 'habitual_affect_description_not_episode_trigger'
    if any(x in reading for x in ('郁','鬱')):return 'persistent_affective_description_not_proven_episode_cause_or_modern_psychiatric_diagnosis'
    if '膏粱' in reading:return 'narrator_dietary_social_descriptor_not_measured_intake'
    if reading in {'善飲','素善飲'}:return 'reported_drinking_habit_no_quantity_or_dependency_inferred'
    raise ValueError('Unclassified background/behavior descriptor; explicit type required')


def build(work="KCLY"):
    if work not in {"KCLY", "ZTLY", "NKCZ", "NKZY", "WKSY"}:raise ValueError("Unsupported extended work")
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
                kind=interpretation_kind(field,reading)
                obs['interpretation_type']=kind
                observations.append(obs)
            fields[field]={'status':'model_selected_evidence' if observations else 'not_identified_in_model_case_read',
                           'missingness':None if observations else 'unrecorded_or_unresolved_not_explicit_absence',
                           'observations':observations}
        records.append({'case_id':cid,'work_ref':'XJ-'+work,'review_date':'2026-10-28' if work=='WKSY' else '2026-10-27',
            'source_git_blob':review.base.BLOB_SHA_AT_FREEZE,
            'case_text_sha256':hashlib.sha256(c['body'].encode()).hexdigest(),
            'retrieval_status':c['md'].get('retrieval_status','unknown'),
            'default_retrieval_excluded':c['md'].get('retrieval_status')=='needs_review',
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
        if row['retrieval_status']!=c['md'].get('retrieval_status','unknown') or row['default_retrieval_excluded']!=(c['md'].get('retrieval_status')=='needs_review'):
            raise ValueError('Extended pending-source exclusion lost')
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
    return {'date':max(r['review_date'] for r in rows),'cases':len(rows),'dimension_slots':len(rows)*len(FIELDS),
            'cases_with_selected_evidence':{f:sum(bool(r['fields'][f]['observations']) for r in rows) for f in FIELDS},
            'observations':len(all_obs),'literal_spans':sum(len(o['evidence']) for o in all_obs),
            'phases':dict(Counter(o['time_phase'] for o in all_obs)),
            'human_adjudicated':0,'initial_query_exported':0,
            'default_retrieval_excluded':sum(r['default_retrieval_excluded'] for r in rows),
            'scope':'independent_dimensions_separate_from_five_domain_totals'}


def render(rows):
    title={'XJ-KCLY':'口齿','XJ-ZTLY':'正体','XJ-NKCZ':'女科','XJ-NKZY':'内科','XJ-WKSY':'外科枢要'}[rows[0]['work_ref']]
    out=[f'# {title}20案：独立脉象、舌部观察、体形与习惯维度\n\n',
         f"{max(r['review_date'] for r in rows)}模型精选证据，"
         '非专家审校或穷尽标注。空字段保留未载/不明，不解释为患者没有。全部初诊查询导出禁用。\n\n',
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
    if rows[0]['work_ref']=='XJ-NKCZ':
        out[2]='脉象保留原字；倦瘦为当时状态，不反推发病前体质。善怒、多怒、久郁等属于性情或持续情志描述，不自动成为当次诱因，也不转换现代精神疾病诊断。未选定舌部观察不等于明确没有。\n\n'
    if rows[0]['work_ref']=='XJ-NKZY':
        out[2]='病中日饮冰水不等于病前习惯；形体状态保留阶段，不反推发病前体质。脉欲绝是叙述者的预后解释，不作为独立客观检查结果。舌本强硬不生成舌苔舌色。三条待核来源案例的排除标记继承至本独立维度文件。\n\n'
    if rows[0]['work_ref']=='XJ-WKSY':
        out[2]='脉象区分首次及后段；善怒不自动生成诱因，膏粱只是叙述者类别描述。未选到舌部形态、体形证据保留未载/不明，舌痛不生成舌苔舌色。素清苦含义未定，未硬归为饮食或心理测量。\n\n'
    return ''.join(out).rstrip()+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--work',choices=['KCLY','ZTLY','NKCZ','NKZY','WKSY'],default='KCLY');a=p.parse_args()
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
