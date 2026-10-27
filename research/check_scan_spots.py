#!/usr/bin/env python3
"""Check recorded spot provenance and working-text links, not visual interpretation.
Optional --pdf verifies the downloaded artifact; it does not re-read print glyphs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import reproduce_sample as base

PATH=base.ROOT/'research/scan_reviews/KCLY_target_spots_2026-10-27.json'

def validate(record,index,pdf=None):
    if record['source_git_blob']!=base.BLOB_SHA_AT_FREEZE:
        raise ValueError('Scan record source blob drift')
    if record['human_adjudication']!='pending' or record['full_case_print_collations']!=0:
        raise ValueError('Unsupported scan adjudication claim')
    seen=set()
    for spot in record['spots']:
        if spot['spot_id'] in seen:raise ValueError('Duplicate scan spot')
        seen.add(spot['spot_id'])
        ev=spot['working_evidence'];text=index[spot['source_ref']]
        a,b=ev['source_start_char'],ev['source_end_char_exclusive']
        if not 0<=a<b<=len(text) or text[a:b]!=ev['raw_quote']:
            raise ValueError('Scan evidence literal mismatch')
        if not 1<=spot['pdf_page']<=record['pdf_pages']:
            raise ValueError('Scan PDF page out of range')
        if spot['human_adjudication']!='pending' or spot['scope']!='specified_glyph_and_context_only_not_entire_case_or_edition':
            raise ValueError('Unsupported spot verification scope')
        if spot['disputed_working_glyph'] not in ev['raw_quote'] or spot['disputed_working_glyph'] not in spot['image_target_reading_without_added_punctuation']:
            raise ValueError('Target glyph is not linked to the working reading')
    if pdf is not None:
        raw=Path(pdf).read_bytes()
        if len(raw)!=record['pdf_bytes'] or hashlib.sha256(raw).hexdigest()!=record['pdf_sha256']:
            raise ValueError('Downloaded PDF differs from recorded scan')
    return record

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pdf');a=p.parse_args()
    index,_=base.load();record=validate(json.loads(PATH.read_text()),index,a.pdf)
    print(json.dumps({'recorded_model_visual_spots':len(record['spots']),
        'recorded_pdf_pages_viewed':len({s['pdf_page'] for s in record['spots']}),
        'pdf_artifact_hash_checked_this_command':a.pdf is not None,
        'full_case_print_collations':0,'human_adjudication':'pending'},ensure_ascii=False))
    print('PASS: recorded provenance and source links valid; visual glyph judgments are not automatically verified')

if __name__=='__main__':main()
