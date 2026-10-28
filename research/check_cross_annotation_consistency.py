#!/usr/bin/env python3
"""Check stored five-domain, independent-dimension and event-pilot joins.
No automatic assessment of clinical truth, translation or missing evidence.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
import build_close_read_160 as core
import build_extended_kcly as extended
import build_event_pilot as event

ROOT=core.ROOT
OUT=ROOT/'research/samples/cross_annotation_consistency_160.json'


def overlap(left,right):
    return any(a['source_ref']==b['source_ref'] and
               max(a['source_start_char'],b['source_start_char']) <
               min(a['source_end_char_exclusive'],b['source_end_char_exclusive'])
               for a in left for b in right)


def phase_candidates(core_rows,extended_rows,event_rows):
    """Flag conflicting labels on overlapping source intervals, not all observations."""
    by_id={r['case_id']:r for r in core_rows};flags=[];dimension_pairs=0;event_obs=0
    for row in extended_rows:
        c=by_id[row['case_id']]
        for field,data in row['fields'].items():
            for o in data['observations']:
                for cf,cd in c['fields'].items():
                    for co in cd['observations']:
                        if not overlap(o['evidence'],co['evidence']):continue
                        dimension_pairs+=1
                        if o['time_phase']!=co['time_phase']:
                            flags.append({'kind':'overlapping_dimension_phase_difference','case_id':row['case_id'],
                                'independent_field':field,'core_field':cf,'independent_reading':o['reading_joined_source_segments'],
                                'core_reading':co['reading_joined_source_segments'],'phases':[o['time_phase'],co['time_phase']]})
    for row in event_rows:
        c=by_id[row['case_id']]
        for field,data in c['fields'].items():
            for o in data['observations']:
                phases={e['time_phase'] for e in row['events'] if overlap(e['evidence'],o['evidence'])}
                if not phases:continue
                event_obs+=1
                if phases!={o['time_phase']}:
                    flags.append({'kind':'observation_event_phase_difference','case_id':row['case_id'],
                        'core_field':field,'reading':o['reading_joined_source_segments'],
                        'core_phase':o['time_phase'],'event_phases':sorted(phases)})
    return flags,dimension_pairs,event_obs



def negation_candidates(rows):
    """A bounded lexical screen, not a universal clinical negation parser."""
    pattern=re.compile('無汗|無痛|無痰|無膿|無熱|不痛|不腫|不熱|不癢|不渴|不紅|不赤|不作膿|不生膿|未作膿')
    return [{'case_id':r['case_id'],'reading':o['reading_joined_source_segments'],
             'matched_cue':m.group(0),'decision':'requires_context_review_not_automatic_negative'}
            for r in rows for o in r['fields']['symptoms']['observations']
            if o['polarity']=='present' and (m:=pattern.search(o['reading_joined_source_segments']))]


def validate_held_out(record,cases,index,extended_rows):
    if record['human_adjudication']!='pending' or record['source_git_blob']!=core.base.BLOB_SHA_AT_FREEZE:
        raise ValueError('Unsupported held-out adjudication or provenance')
    expected={cid for cid,c in cases.items() if c['work_ref']=='XJ-BYCY'}
    ids=[c['case_id'] for c in record['cases']]
    if len(ids)!=20 or set(ids)!=expected:raise ValueError('Held-out review roster drift')
    for row in [*record['cases'],*record['held_out_candidates']]:
        c=cases[row['case_id']]
        if row['case_text_sha256']!=hashlib.sha256(c['body'].encode()).hexdigest():raise ValueError('Held-out case digest drift')
    ext={r['case_id']:r for r in extended_rows}
    for row in record['held_out_candidates']:
        c=cases[row['case_id']]
        if row['evidence']!=core.evidence_for(c,row['reading'],index):raise ValueError('Held-out literal mapping drift')
        if row['human_adjudication']!='pending' or row['initial_query_eligible'] is not False:
            raise ValueError('Unchecked held-out export or verification')
        if row['source_git_blob']!=core.base.BLOB_SHA_AT_FREEZE:raise ValueError('Held-out source blob drift')
        if row['decision'] not in {'other_person_not_patient_feature','observation_not_assigned_to_standard_pulse','unresolved_literal_reading_not_normalized_to_pulse'}:
            raise ValueError('Unknown held-out decision')
        if any(overlap(row['evidence'],o['evidence']) for d in ext[row['case_id']]['fields'].values() for o in d['observations']):
            raise ValueError('Held-out evidence was promoted into patient independent features')


def build():
    core.freeze_check();_,sample,index=core.build();cases={c['case_id']:c for c in sample}
    rows=[json.loads(l) for l in core.JSONL.read_text().splitlines()]
    core.validate_records(rows,sample,index)
    independent=[];profiles=[]
    works=sorted({c['work_ref'].removeprefix('XJ-') for c in sample})
    for work in works:
        path=ROOT/f'research/samples/extended_{work.lower()}_20_v1.jsonl'
        data=[json.loads(l) for l in path.read_text().splitlines()]
        wc={cid:c for cid,c in cases.items() if c['work_ref']=='XJ-'+work}
        extended.validate(data,wc,index);independent.extend(data)
        profiles.append({'work_ref':'XJ-'+work,**extended.summary(data)})
    if len(independent)!=160 or len({r['case_id'] for r in independent})!=160:
        raise ValueError('Independent join must be exactly one row per sampled case')
    pilots=[]
    for inp in sorted((ROOT/'research/review_inputs').glob('*_event_pilot.json')):
        work=inp.name.removesuffix('_event_pilot.json')
        row=json.loads((ROOT/f'research/samples/event_pilot_{work.lower()}_v1.json').read_text())
        event.validate(row,cases[row['case_id']],index);pilots.append(row)
    ids=[r['case_id'] for r in pilots]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate event-pilot case')
    held=json.loads((ROOT/'research/review_inputs/BYCY_extended_review.json').read_text())
    validate_held_out(held,cases,index,independent)
    flags,pairs,events=phase_candidates(rows,independent,pilots)
    by_id={r['case_id']:r for r in rows}
    for r in independent:
        c=by_id[r['case_id']]
        if any(r[k]!=c[k] for k in ('case_text_sha256','source_git_blob','default_retrieval_excluded')):
            raise ValueError('Core/independent joined provenance or exclusion mismatch')
    def flat(data):return [o for r in data for d in r['fields'].values() for o in d['observations']]
    co=flat(rows);ex=flat(independent)
    return {'review_date':'2026-10-28','method':'automated_stored_artifact_consistency_not_semantic_adjudication',
        'source_git_blob':core.base.BLOB_SHA_AT_FREEZE,'grain':'one_case_row_per_sample_in_each_of_two_tables; observations_nested_by_field; event_rows_only_pilot_subset',
        'core_case_rows':len(rows),'independent_case_rows':len(independent),'matched_case_ids':len(set(by_id)&{r['case_id'] for r in independent}),
        'core_field_slots':len(rows)*len(core.FIELDS),'independent_field_slots':len(independent)*len(extended.FIELDS),
        'core_empty_unresolved_slots':sum(not d['observations'] for r in rows for d in r['fields'].values()),
        'independent_empty_unresolved_slots':sum(not d['observations'] for r in independent for d in r['fields'].values()),
        'core_observations':len(co),'independent_observations':len(ex),
        'core_literal_spans':sum(len(o['evidence']) for o in co),'independent_literal_spans':sum(len(o['evidence']) for o in ex),
        'core_phases':dict(Counter(o['time_phase'] for o in co)),'independent_phases':dict(Counter(o['time_phase'] for o in ex)),
        'core_explicit_negative_observations':sum(o['polarity']=='explicitly_absent' for o in co),
        'independent_explicit_negative_observations':sum(o['polarity']=='explicitly_absent' for o in ex),
        'default_excluded_cases':sum(r['default_retrieval_excluded'] for r in rows),
        'event_pilot_cases':len(pilots),'event_segments':sum(len(r['events']) for r in pilots),
        'overlapping_cross_dimension_observation_pairs_checked':pairs,'core_observations_overlapping_pilot_events_checked':events,
        'phase_difference_candidates':flags,'bounded_negation_screen_candidates':negation_candidates(rows),'held_out_candidates':len(held['held_out_candidates']),
        'human_adjudicated_cases':0,'initial_query_exported':0,'independent_profiles':profiles,
        'limitations':['No automatic interpretation of drug causality, patient identity, negation meaning or missing clinical facts.',
                       'Zero interval-label candidates is not zero semantic errors; only selected overlapping evidence is compared.',
                       'The negation screen uses a bounded cue list; zero candidates does not establish exhaustive negation coverage.',
                       'No third full-case clinical review or new print collation is established by this command.']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    result=build();text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if a.write:OUT.write_text(text)
    if OUT.read_text()!=text:raise ValueError('Cross-annotation report drift')
    print(json.dumps({k:result[k] for k in ('core_case_rows','independent_case_rows','independent_observations','overlapping_cross_dimension_observation_pairs_checked','core_observations_overlapping_pilot_events_checked','phase_difference_candidates','held_out_candidates')},ensure_ascii=False))
    print('PASS: stored joins, literal provenance and label-consistency profile reproduced; semantic accuracy not established')

if __name__=='__main__':main()
