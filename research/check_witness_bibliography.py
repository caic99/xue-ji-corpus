#!/usr/bin/env python3
"""Validate recorded bibliographic claim boundaries, not historical truth or visual reading."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'research/witness_reviews/KCLY_bibliography_2026-10-29.json'
OUT=ROOT/'research/samples/witness_kcly_bibliography.json'

def build(record=None):
    r=copy.deepcopy(record) if record is not None else json.loads(INPUT.read_text())
    source=json.loads((ROOT/r['source_metadata_record']).read_text())
    if any(r[k]!=source[k] for k in ('pdf_sha256','pdf_bytes','pdf_pages')):
        raise ValueError('Witness PDF identity drift')
    if r['human_adjudication']!='pending':raise ValueError('Unsupported expert cataloguing claim')
    ids=[x['pdf_page'] for x in r['reviewed_pages']]
    if len(ids)!=len(set(ids)) or any(not 1<=p<=r['pdf_pages'] for p in ids):
        raise ValueError('Invalid reviewed page roster')
    for key in ('title_claim','authorship_claim','date_claim'):
        if not set(r[key]['supporting_pdf_pages'])<=set(ids):
            raise ValueError('Bibliographic claim cites an unviewed page')
    date=r['date_claim']
    if (date['status']!='inherited_metadata_not_reverified_from_images' or
        date['year_observed_in_reviewed_pages'] is not False or date['supporting_pdf_pages']):
        raise ValueError('Inherited date cannot be promoted to image-verified publication year')
    return r

def main():
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');p.add_argument('--pdf',type=Path);a=p.parse_args()
    r=build()
    if a.pdf and (a.pdf.stat().st_size!=r['pdf_bytes'] or hashlib.sha256(a.pdf.read_bytes()).hexdigest()!=r['pdf_sha256']):
        raise ValueError('Witness PDF artifact mismatch')
    text=json.dumps(r,ensure_ascii=False,indent=2)+'\n'
    if a.write:OUT.write_text(text)
    if OUT.read_text()!=text:raise ValueError('Bibliographic artifact drift')
    print('PASS: 5 recorded pages; title/printed attribution model-read; inherited date unverified; expert pending')

if __name__=='__main__':main()
