#!/usr/bin/env python3
"""Read-only reconciliation of selected evidence to dated electronic snapshots.
Does not claim current live text or original-print image verification.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
import build_close_read_160 as review
sys.path.insert(0,str(review.ROOT/'work'))
from reconcile_book import load_snapshot
from reconcile_bycy import parse_kanripo

OUT=review.ROOT/'research/samples/snapshot_evidence_check_160.json'
SNAPS={
 'XJ-NKZY':'nkzy-2026-09-28.html', 'XJ-NKCZ':'nkcz-index-2026-09-29.html',
 'XJ-KCLY':'kcly-index-2026-09-29.html', 'XJ-LZWKFH':'lzwkfh-index-2026-09-29.html',
 'XJ-WKSY':'wksy-index-2026-09-29.html', 'XJ-ZTLY':'ztly-index-2026-09-29.html',
 'XJ-LYJY':'lyjy-index-2026-09-29.html', 'XJ-BYCY':'bycy-kr3e0070_005-2026-09-29.txt',
}


def run():
 records,sample,index=review.build()
 books=review.base.books(review.base.CORPUS.read_text())
 source_meta={row['meta']['source_id']:row['meta'] for b in books for row in b['rows']}
 lookup={}; manifests=[]
 for work,filename in SNAPS.items():
  path=review.ROOT/'work/source-snapshots'/filename
  raw=path.read_bytes()
  manifests.append({'work_ref':work,'path':str(path.relative_to(review.ROOT)),
                    'sha256':hashlib.sha256(raw).hexdigest(),
                    'scope':'dated_cached_electronic_transcription_not_print_scan'})
  if work=='XJ-BYCY':
   _,_,lines=parse_kanripo(raw.decode())
   for i,(folio,text) in enumerate(lines,1):
    lookup[f'{work}-V5-L{i:04d}']=(text,{'snapshot_line_ordinal':i,'folio':folio})
  else:
   _,rows=load_snapshot(path)
   count=Counter()
   for ordinal,(volume,section,text) in enumerate(rows,1):
    count[volume]+=1
    # Match the original volume-local paragraph numbering; validate section below.
    matching=[sid for sid,md in source_meta.items() if md['work_id']==work
              and md.get('volume')==volume and sid.endswith(f'-P{count[volume]:03d}')]
    if len(matching)==1:
     lookup[matching[0]]=(text,{'snapshot_paragraph_ordinal':ordinal,
                              'volume':volume,'section':section})
 details=[]
 for record in records:
  for field,data in record['fields'].items():
   for oi,obs in enumerate(data['observations']):
    for ei,ev in enumerate(obs['evidence']):
     sid=ev['source_ref']; md=source_meta[sid]
     found=lookup.get(sid)
     result={'case_id':record['case_id'],'field':field,'observation_index':oi,
             'segment_index':ei,'source_ref':sid,'raw_quote':ev['raw_quote'],
             'snapshot_path':'work/source-snapshots/'+SNAPS[record['work_ref']]}
     if found is None:
      result['status']='source_mapping_unresolved'
     else:
      text,loc=found
      result['snapshot_location']=loc
      if record['work_ref']=='XJ-BYCY':
       aligned=md.get('folio')==loc['folio']
      else:
       aligned=md.get('volume')==loc['volume'] and md.get('section','')==loc['section']
      if not aligned:
       result['status']='source_mapping_unresolved'
      else:
       at=text.find(ev['raw_quote'])
       result['source_paragraph_identical']=index[sid]==text
       if at>=0:
        result.update(status='exact_quote_present_in_mapped_snapshot_record',
                      snapshot_start_char=at,
                      snapshot_end_char_exclusive=at+len(ev['raw_quote']))
       else:
        result.update(status='quote_differs_from_cached_transcription',
                      working_record=index[sid],snapshot_record=text,
                      existing_correction_metadata={k:v for k,v in md.items()
                        if k in ['text_correction_applied','collation_status','original_public_transcription',
                                 'preferred_reading','edition_image_check_status']},
                      interpretation='difference_only_not_newly_adjudicated_transcription_error_or_edition_variant')
     details.append(result)
 counts=Counter(d['status'] for d in details)
 return {'date':review.DATE,'source_git_blob':review.base.BLOB_SHA_AT_FREEZE,
         'snapshots':manifests,'summary':dict(counts),'evidence_segments':len(details),
         'original_print_images_checked':0,'details':details}


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
 result=run();text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
 if a.write: OUT.write_text(text)
 if OUT.read_text()!=text: raise ValueError('Snapshot reconciliation output drift')
 if result['summary'].get('source_mapping_unresolved',0): raise ValueError('Snapshot source mapping unresolved')
 print(json.dumps({k:v for k,v in result.items() if k not in ['snapshots','details']},ensure_ascii=False,indent=2))
 print('PASS: dated snapshot reconciliation reproduced; differences retained, not silently corrected')

if __name__=='__main__':main()
