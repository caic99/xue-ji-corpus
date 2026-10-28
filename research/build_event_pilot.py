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


def build(work="ZTLY"):
    if work not in {"ZTLY","NKCZ","NKZY","WKSY","LZWKFH"}:raise ValueError("Unsupported event pilot work")
    _,sample,index=review.build()
    record=json.loads((ROOT/f'research/review_inputs/{work}_event_pilot.json').read_text())
    case=next(c for c in sample if c['case_id']==record['case_id'])
    if case['work_ref']!='XJ-'+work:raise ValueError('Event pilot work mismatch')
    record['work_ref']=case['work_ref']
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
    if record['case_id']!=case['case_id'] or record['work_ref']!=case['work_ref']:
        raise ValueError('Event pilot case/work identity drift')
    if record['source_git_blob']!=review.base.BLOB_SHA_AT_FREEZE or record['case_text_sha256']!=hashlib.sha256(case['body'].encode()).hexdigest():
        raise ValueError('Event pilot provenance drift')
    if record['human_adjudication']!='pending' or record['initial_query_export']!='disabled_pending_expert_temporal_role_review':
        raise ValueError('Unchecked event verification or query claim')
    events=record['events'];ids=[e['event_id'] for e in events]
    if len(ids)!=len(set(ids)) or record['first_recorded_care_decision_event'] not in ids:
        raise ValueError('Event IDs or care anchor invalid')
    if not set(record.get('claim_only_event_ids',[]))<=set(ids):raise ValueError('Unknown claim-only event')
    if not set(record.get('forecast_only_event_ids',[]))<=set(ids):raise ValueError('Unknown forecast-only event')
    if not set(record.get('intent_only_event_ids',[]))<=set(ids):raise ValueError('Unknown intent-only event')
    anchor=ids.index(record['first_recorded_care_decision_event'])
    expected_anchor_types={
        'first_recorded_narrator_assessment_in_window_not_first_performed_treatment':'narrator_interpretation',
        'first_recorded_narrator_recommendation_in_window_not_first_performed_treatment':'care_recommendation',
        'first_explicit_narrator_advice_in_this_window_not_first_performed_treatment':'care_recommendation',
        'first_recorded_narrator_care_intent_in_this_window_not_first_performed_treatment':'care_intent',
    }
    expected_anchor=expected_anchor_types.get(record['anchor_scope'])
    if expected_anchor is None or events[anchor]['event_type']!=expected_anchor:
        raise ValueError('Care anchor type differs from documented intent/advice scope')
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
        if e['event_type']=='care_intent' and e['intervention_status']!='intended_only_no_performance_claim':
            raise ValueError('Intention cannot be promoted to performed treatment or issued recommendation')
        if e['event_id'] in record.get('intent_only_event_ids',[]) and (e['event_type']!='care_intent' or e['intervention_status']!='intended_only_no_performance_claim'):
            raise ValueError('Protected intent cannot become performed treatment or recommendation')
        if e['event_id'] in record.get('claim_only_event_ids',[]) and (e['event_type']!='reported_intervention_claim_with_narrator_deception_attribution' or e['intervention_status']!='claimed_only_not_performance_evidence'):
            raise ValueError('Reported intervention claim cannot become performed treatment')
        if e['event_id'] in record.get('forecast_only_event_ids',[]) and (e['event_type']!='reported_healing_expectation' or e['intervention_status']!='forecast_only_not_observed_outcome'):
            raise ValueError('Healing expectation cannot become observed outcome')
        if e['time_expression_raw'] and e['time_expression_raw'] not in reading:
            raise ValueError('Time expression must be literal evidence')
    if joined!=''.join(case['parts']):raise ValueError('Event segmentation must cover entire case window in source order')
    expected_relations=[{'from':a,'to':b,'relation':'next_in_source_narrative_not_proven_causality'} for a,b in zip(ids,ids[1:])]
    if record['relations']!=expected_relations:raise ValueError('Event relation must not invent causality')


def render(r):
    title={'XJ-ZTLY':'正体','XJ-NKCZ':'女科','XJ-NKZY':'内科','XJ-WKSY':'外科枢要','XJ-LZWKFH':'立斋外科发挥'}[r['work_ref']]
    out=[f'# {title}事件轴试点：完整案文叙事分段（1案）\n\n',
         '模型按来源顺序逐段选择，非专家裁定，也不代表160案完整事件轴已完成。医者建议、处置意向与实际治疗严格分开；次日、数日后不换算日历日期。相邻关系只指叙事顺序，不证明因果。全部查询导出禁用。\n\n',
         f"案例：`{r['case_id']}`。首次记录医者决策：`{r['first_recorded_care_decision_event']}`，未据此认定建议或意向已实施。\n\n"]
    for e in r['events']:
        quote=' ／ '.join(x['raw_quote'] for x in e['evidence'])
        refs='; '.join(f"{x['source_ref']}[{x['source_start_char']}:{x['source_end_char_exclusive']})" for x in e['evidence'])
        out.append(f"- **{e['event_id']}** {quote} `{refs}`；{e['event_type']}；{e['actor_role']}；{e['intervention_status']}；{e['time_phase']}\n")
    if r.get('claim_conflict_note'):
        out.append('\n本案末段黄连是被转述的用药声称，叙述者另记阴仍用参附汤并称诈；这不是独立核实了欺骗事实。辛丑年不换算公历；相邻叙事不证明声称和实际处置严格先后。\n')
    if r.get('forecast_only_event_ids'):
        out.append('\n旬日收敛是被转述且至今未应的预期，不当作十日已愈或精确已观察时长。不数日亦保留原词，不强定天数；云字说话者未明。\n')
    if r.get('intent_only_event_ids'):
        out.append('\n余欲及待发后用针为分期处置计划，并非已经施行；复求治后仍投前药及托出针之才是后段叙述治疗。彼欲内消是患者意愿，不是已证实的实际治疗。相邻先后不能证明攻伐药的真实因果效应。\n')
    return ''.join(out)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--work',choices=['ZTLY','NKCZ','NKZY','WKSY','LZWKFH'],default='ZTLY');a=p.parse_args()
    record,case,index=build(a.work);validate(record,case,index)
    out=ROOT/f'research/samples/event_pilot_{a.work.lower()}_v1.json'
    readable=ROOT/f'research/samples/EVENT_PILOT_{a.work}_V1.md'
    results={out:json.dumps(record,ensure_ascii=False,indent=2)+'\n',readable:render(record)}
    for path,text in results.items():
        if a.write:path.write_text(text)
        if path.read_text()!=text:raise ValueError('Event pilot artifact drift')
    validate(json.loads(out.read_text()),case,index)
    print(json.dumps({'cases':1,'narrative_segments':len(record['events']),'complete_case_window_coverage':True,'human_adjudication':'pending','initial_query_exported':0}))
    print('PASS: exact full-window segmentation; care recommendation not counted as performed treatment')

if __name__=='__main__':main()
