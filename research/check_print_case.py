#!/usr/bin/env python3
"""Compare a recorded full-case model image reading to frozen text, not validate vision."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import build_close_read_160 as core

ROOT=core.ROOT
INPUT=ROOT/'research/print_case_reviews/KCLY_H3_P005_2026-10-28.json'
OUT=ROOT/'research/samples/print_case_kcly_h3_p005.json'
PUNCTUATION=set('，。；：！？、')

def build(record=None, path=INPUT):
    _,sample,index=core.build()
    r=copy.deepcopy(record) if record is not None else json.loads(path.read_text())
    case=next(c for c in sample if c['case_id']==r['case_id'])
    if r['human_adjudication']!='pending' or r['initial_query_eligible'] is not False:
        raise ValueError('Unsupported print verification or query claim')
    if r['full_case_model_image_comparisons']!=1 or r['expert_collated_cases']!=0:
        raise ValueError('Model image comparison is not expert collation')
    witness=json.loads((ROOT/r['pdf_record']).read_text())
    if not 1<=r['pdf_page']<=witness['pdf_pages']:raise ValueError('Page outside PDF')
    reading=''.join(r['scan_columns'])
    chars=[]
    for segment in case['segments']:
        text=index[segment['source_ref']]
        for pos in range(segment['start'],segment['end']):
            if text[pos] not in PUNCTUATION:
                chars.append((segment['source_ref'],pos,text[pos]))
    if len(chars)!=len(reading):raise ValueError('Full-case alignment requires equal character count; review insertions or omissions explicitly')
    alignment=[{'ordinal':i+1,'source_ref':sid,'source_start_char':pos,
                'source_end_char_exclusive':pos+1,'working':w,'scan':s,
                'status':'same_model_reading' if w==s else 'different_model_reading'}
               for i,((sid,pos,w),s) in enumerate(zip(chars,reading))]
    differences=[x for x in alignment if x['working']!=x['scan']]
    if [{'working':x['working'],'scan':x['scan']} for x in differences]!=r['expected_substitutions']:
        raise ValueError('Recorded print differences drift')
    return {**r,'source_git_blob':core.base.BLOB_SHA_AT_FREEZE,
            'case_text_sha256':hashlib.sha256(case['body'].encode()).hexdigest(),
            'pdf_sha256':witness['pdf_sha256'],'pdf_bytes':witness['pdf_bytes'],
            'working_case_evidence':core.evidence_for(case,''.join(case['parts']),index),
            'scan_reading':reading,'compared_body_characters_excluding_modern_punctuation':len(chars),
            'differences':differences,'alignment':alignment,
            'limitations':['Program validates recorded alignment and provenance, not the model visual reading.',
                           'One printed witness cannot adjudicate other editions or correct the frozen corpus.',
                           'Punctuation, kundoku marks and paleographic glyph variants are not fully collated.']}

def summarize(records):
    ids=[r['case_id'] for r in records]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate full-case comparison case')
    return {'scope':'full_case_model_image_comparisons_not_expert_collation',
            'cases':len(records),'case_ids':ids,
            'compared_body_characters':sum(r['compared_body_characters_excluding_modern_punctuation'] for r in records),
            'different_character_positions':sum(len(r['differences']) for r in records),
            'unique_pdf_pages':len({(r['pdf_sha256'],r['pdf_page']) for r in records}),
            'expert_collated_cases':0,'initial_query_exported':0}

def main():
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');p.add_argument('--pdf',type=Path);p.add_argument('--all',action='store_true');a=p.parse_args()
    paths=sorted((ROOT/'research/print_case_reviews').glob('*.json')) if a.all else [INPUT]
    records=[]
    for path in paths:
        r=build(path=path);records.append(r)
        if a.pdf and (a.pdf.stat().st_size!=r['pdf_bytes'] or hashlib.sha256(a.pdf.read_bytes()).hexdigest()!=r['pdf_sha256']):
            raise ValueError('PDF identity mismatch')
        # Preserve the first published artifact name for backwards compatibility.
        out=OUT if path==INPUT else ROOT/'research/samples'/('print_case_'+path.stem.lower()+'.json')
        text=json.dumps(r,ensure_ascii=False,indent=2)+'\n'
        if a.write:out.write_text(text)
        if out.read_text()!=text:raise ValueError('Full-case image comparison artifact drift')
    result=summarize(records)
    if a.all:
        out=ROOT/'research/samples/print_case_summary.json';text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
        if a.write:out.write_text(text)
        if out.read_text()!=text:raise ValueError('Full-case summary drift')
    print(json.dumps(result,ensure_ascii=False))
    print('PASS: recorded full-case model reading reproduces; visual accuracy and expert review not established')

if __name__=='__main__':main()
