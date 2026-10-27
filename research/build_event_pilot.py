#!/usr/bin/env python3
"""Reproduce a model-selected full narrative segmentation for one pilot case.
Narrative sequence is not a causal estimate or an exhaustive clinical event list.
"""
import argparse
import hashlib
import json
import build_close_read_160 as review

ROOT=review.ROOT
INPUT=ROOT/'research/review_inputs/ZTLY_event_pilot.json'
OUT=ROOT/'research/samples/event_pilot_ztly_v1.json'
READABLE=ROOT/'research/samples/EVENT_PILOT_ZTLY_V1.md'


def build():
    _,sample,index=review.build()
    record=json.loads(INPUT.read_text())
    case=next(c for c in sample if c['case_id']==record['case_id'])
    record['source_git_blob']=review.base.BLOB_SHA_AT_FREEZE
    record['case_text_sha256']=hashlib.sha256(case['body'].encode()).hexdigest()
    for i,event in enumerate(record['events'],1):
        event['narrative_order']=i
        event['evidence']=review.evidence_for(case,event.pop('quote'),index)
        event['initial_query_eligible']=False
    record['relations']=[{'from':a['event_id'],'to':b['event_id'],
                         'relation':'next_in_source_narrative_not_proven_causality'}
                        for a,b in zip(record['events'],record['events'][1:])]
    return record,case,index


def validate(record,case,index):
    if record['source_git_blob']!=review.base.BLOB_SHA_AT_FREEZE or record['case_text_sha256']!=hashlib.sha256(case['body'].encode()).hexdigest():
        raise ValueError('Event pilot provenance drift')
    if record['human_adjudication']!='pending' or record['initial_query_export']!='disabled_pending_expert_temporal_role_review':
        raise ValueError('Unchecked event verification or query claim')
    events=record['events'];ids=[e['event_id'] for e in events]
    if len(ids)!=len(set(ids)) or record['first_recorded_care_decision_event'] not in ids:
        raise ValueError('Event IDs or care anchor invalid')
    anchor=ids.index(record['first_recorded_care_decision_event'])
    if events[anchor]['event_type']!='care_recommendation':raise ValueError('Care anchor must remain a recommendation')
    joined=''
    for i,e in enumerate(events,1):
        reading=''.join(x['raw_quote'] for x in e['evidence'])
        if e['evidence']!=review.evidence_for(case,reading,index):raise ValueError('Event evidence mapping drift')
        joined+=reading
        if e['narrative_order']!=i or e['initial_query_eligible'] is not False:
            raise ValueError('Event order or query export invalid')
        expected='initial_narrator_window' if i-1<=anchor else 'later_narrator_window'
        if e['time_phase']!=expected:raise ValueError('Event phase crosses care-advice anchor')
        if e['calendar_date'] is not None:raise ValueError('Unsupported event calendar date')
        if e['event_type']=='care_recommendation' and e['intervention_status']!='recommendation_only_no_performance_claim':
            raise ValueError('Recommendation cannot be promoted to performed treatment')
        if e['time_expression_raw'] and e['time_expression_raw'] not in reading:
            raise ValueError('Time expression must be literal evidence')
    if joined!=''.join(case['parts']):raise ValueError('Event segmentation must cover entire case window in source order')
    expected_relations=[{'from':a,'to':b,'relation':'next_in_source_narrative_not_proven_causality'} for a,b in zip(ids,ids[1:])]
    if record['relations']!=expected_relations:raise ValueError('Event relation must not invent causality')


def render(r):
    out=['# 正体事件轴试点：完整案文叙事分段（1案）\n\n',
         '模型按来源顺序逐段选择，非专家裁定，也不代表160案完整事件轴已完成。首次医者建议与实际治疗严格分开；次日、数日后不换算日历日期。相邻关系只指叙事顺序，不证明因果。全部查询导出禁用。\n\n',
         f"案例：`{r['case_id']}`。首次明确医者建议：`{r['first_recorded_care_decision_event']}`，未据此认定建议已实施。\n\n"]
    for e in r['events']:
        quote=' ／ '.join(x['raw_quote'] for x in e['evidence'])
        refs='; '.join(f"{x['source_ref']}[{x['source_start_char']}:{x['source_end_char_exclusive']})" for x in e['evidence'])
        out.append(f"- **{e['event_id']}** {quote} `{refs}`；{e['event_type']}；{e['actor_role']}；{e['intervention_status']}；{e['time_phase']}\n")
    return ''.join(out)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    record,case,index=build();validate(record,case,index)
    results={OUT:json.dumps(record,ensure_ascii=False,indent=2)+'\n',READABLE:render(record)}
    for path,text in results.items():
        if a.write:path.write_text(text)
        if path.read_text()!=text:raise ValueError('Event pilot artifact drift')
    validate(json.loads(OUT.read_text()),case,index)
    print(json.dumps({'cases':1,'narrative_segments':len(record['events']),'complete_case_window_coverage':True,'human_adjudication':'pending','initial_query_exported':0}))
    print('PASS: exact full-window segmentation; care recommendation not counted as performed treatment')

if __name__=='__main__':main()
