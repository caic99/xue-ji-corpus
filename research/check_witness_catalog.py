#!/usr/bin/env python3
"""Validate recorded catalog attribution without upgrading it to a read colophon."""
import argparse
import copy
import json
from pathlib import Path
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'research/witness_reviews/KCLY_catalog_2026-10-29.json'
OUT=ROOT/'research/samples/witness_kcly_catalog.json'

def build(record=None):
    r=copy.deepcopy(record) if record is not None else json.loads(INPUT.read_text())
    pdf=json.loads((ROOT/r['target_pdf_record']).read_text())
    if r['target_pdf_sha256']!=pdf['pdf_sha256']:raise ValueError('Catalog/PDF identity drift')
    f=r['catalog_fields']
    if f['book_number']!='06248-0014' or ('NCL-'+f['book_number']) not in unquote(pdf['download_url']):
        raise ValueError('Catalog book number does not identify this PDF')
    if f['title']!='口齒類要' or f['edition_label']!='日本承應3年(1654)刊本':
        raise ValueError('Recorded catalog fields drift')
    if (r['edition_catalog_verification']!='institutional_catalog_record_supported_not_colophon_verified'
        or r['colophon_verified'] is not False or r['human_adjudication']!='pending'
        or r['new_independent_print_witnesses']!=0):
        raise ValueError('Catalog metadata cannot be promoted to colophon or independent edition proof')
    if r['citation_template_date_label']!='年代不詳':
        raise ValueError('Separate citation date must remain recorded')
    return r

def main():
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');a=p.parse_args()
    r=build();text=json.dumps(r,ensure_ascii=False,indent=2)+'\n'
    if a.write:OUT.write_text(text)
    if OUT.read_text()!=text:raise ValueError('Catalog evidence artifact drift')
    print('PASS: matching institutional catalog edition field supports 1654; image colophon and expert review unverified')

if __name__=='__main__':main()
