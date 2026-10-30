#!/usr/bin/env python3
"""Reproduce selected person-role and modality evidence; no clinical truth claim."""
import argparse
import hashlib
import json
import build_close_read_160 as review

ROOT=review.ROOT
CONTRACT={
 'MOTHER':(['mother'],'narrator_assessment'),
 'BOTH':(['child','mother'],'narrated_shared_treatment_and_outcome'),
 'PRIOR':(['child'],'prior_intervention_and_interpretation_actor_uncertain'),
 'PLAN':(['child'],'proposed_intervention_no_performance_claim'),
 'SIGN':(['child'],'unresolved_observation_not_standard_wrist_pulse'),
 'TREAT':(['child'],'narrator_assessment_and_narrated_treatment'),
 'COUNTER':(['child'],'conditional_warning_not_observed_death'),
}

def build():
    _,sample,index=review.build()
    r=json.loads((ROOT/'research/review_inputs/BYCY_role_pilot.json').read_text())
    c=next(c for c in sample if c['case_id']==r['case_id'])
    r.update(work_ref=c['work_ref'],source_git_blob=review.base.BLOB_SHA_AT_FREEZE,
             case_text_sha256=hashlib.sha256(c['body'].encode()).hexdigest(),
             initial_query_eligible=False)
    for f in r['findings']:
        f['evidence']=review.evidence_for(c,f.pop('quote'),index)
    return r,c,index

def validate(r,c,index):
    if (r['case_id']!=c['case_id'] or r['work_ref']!=c['work_ref']
        or r['source_git_blob']!=review.base.BLOB_SHA_AT_FREEZE
        or r['case_text_sha256']!=hashlib.sha256(c['body'].encode()).hexdigest()):
        raise ValueError('Role pilot provenance drift')
    if r['human_adjudication']!='pending' or r['initial_query_eligible'] is not False:
        raise ValueError('Unreviewed role pilot cannot enable query or human verification')
    ids=[f['id'] for f in r['findings']]
    if len(ids)!=len(set(ids)) or set(ids)!=set(CONTRACT):
        raise ValueError('Role pilot finding roster drift')
    reviewed=json.loads((ROOT/'research/review_inputs/BYCY_role_pilot.json').read_text())
    quotes={f['id']:f['quote'] for f in reviewed['findings']}
    for f in r['findings']:
        if (f['subjects'],f['assertion_type'])!=CONTRACT[f['id']]:
            raise ValueError('Reviewed person/modality contract drift')
        quote=''.join(e['raw_quote'] for e in f['evidence'])
        if quote!=quotes[f['id']] or f['evidence']!=review.evidence_for(c,quote,index):
            raise ValueError('Role evidence mapping drift')

def render(r):
    out=['# 保婴母子人物归属及条件语气试点\n\n',
         '完整案文窗口经模型阅读，以下只选关键片段，尚非整案事件轴或专家裁决。\n\n']
    for f in r['findings']:
        quote=' ／ '.join(e['raw_quote'] for e in f['evidence'])
        out.append(f"- {f['id']}：{quote}；对象 {','.join(f['subjects'])}；{f['assertion_type']}。{f['note']}\n")
    out.append('\n乙未、丙申、丁酉保留干支，不换算公历；先前寅卯关脉候选继续未决。子母共同服药不反推双方同病；末段条件死亡警告不作为本案死亡。逐字区间及案文摘要见同名JSON。未新增影像核对。\n')
    return ''.join(out)

def main():
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');a=p.parse_args()
    r,c,index=build();validate(r,c,index)
    for path,text in {
        ROOT/'research/samples/role_pilot_bycy_v1.json':json.dumps(r,ensure_ascii=False,indent=2)+'\n',
        ROOT/'research/samples/ROLE_PILOT_BYCY_V1.md':render(r),
    }.items():
        if a.write:path.write_text(text)
        if path.read_text()!=text:raise ValueError('Stored role artifact drift')
    validate(json.loads((ROOT/'research/samples/role_pilot_bycy_v1.json').read_text()),c,index)
    print('PASS: 1 case, 7 selected role/modality findings; expert pending; query disabled')

if __name__=='__main__':main()
