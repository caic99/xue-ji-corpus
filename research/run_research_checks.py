#!/usr/bin/env python3
"""Run read-only checks and save real command results for this research pass."""
import argparse
import datetime
import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
commands=[
 ['work/validate_complete_corpus.py'], ['work/audit_corpus.py'],
 ['work/check_retrieval_inheritance.py'], ['research/reproduce_sample.py'],
 ['research/build_close_read_160.py'], ['research/check_sample_snapshots.py'],
 ['research/build_extended_kcly.py'], ['research/build_extended_kcly.py','--work','ZTLY'],
 ['research/build_extended_kcly.py','--work','NKCZ'], ['research/build_extended_kcly.py','--work','NKZY'], ['research/build_extended_kcly.py','--work','WKSY'],
 ['research/build_event_pilot.py'], ['research/build_event_pilot.py','--work','NKCZ'], ['research/build_event_pilot.py','--work','NKZY'], ['research/build_event_pilot.py','--work','WKSY'], ['research/check_scan_spots.py'],
 ['research/build_extended_kcly.py','--work','LYJY'],
 ['research/check_publication.py'],
 ['-m','unittest','discover','-s','research','-p','test_close_read_160.py','-v'],
]


def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--report-date",default=datetime.date.today().isoformat())
 parser.add_argument("--label",default="")
 args=parser.parse_args()
 if args.label and not re.fullmatch(r"[a-z0-9-]+",args.label):
  parser.error("label must contain lowercase letters, digits or hyphens")
 datetime.date.fromisoformat(args.report_date)
 results=[]
 for command in commands:
  p=subprocess.run([sys.executable,*command],cwd=ROOT,text=True,capture_output=True)
  row={'command':['python3',*command],'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
  results.append(row)
  if p.returncode: raise RuntimeError(json.dumps(row,ensure_ascii=False))
 structural=json.loads(results[0]['stdout'])['summary']
 if structural['errors']!=0 or structural['records']!=5361 or structural['duplicate_source_ids']!=0:
  raise ValueError(f'Invalid corpus: {structural}')
 audit_result=json.loads(results[1]['stdout'])
 audit=audit_result.get('summary',audit_result)
 if audit['text_sha256']!='a719e844641d9b610848a923e108f663d0fc1620d4f28c26f1925bfc9d5d27aa':
  raise ValueError('Source text digest drift')
 tracked=[ROOT/p for p in ['research/reproduce_sample.py','research/build_close_read_160.py',
           'research/check_sample_snapshots.py','research/test_close_read_160.py',
           'research/run_research_checks.py','research/check_publication.py',
           'research/build_extended_kcly.py','research/build_event_pilot.py','research/check_scan_spots.py']]
 tracked += sorted((ROOT/'research/review_inputs').glob('*'))
 tracked += sorted((ROOT/'research/scan_reviews').glob('*.json'))
 report={'date_client_timezone_Asia_Shanghai':args.report_date,
         'execution':'actual_local_subprocess_execution', 'python_version':platform.python_version(),
         'source_baseline_commit':'3266f7ba3bbf01806b44e01f7cfe415b03f8da2a',
         'files_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked},
         'structural_summary':structural,'source_summary':audit,
         'commands':results,'remote_ci_status':'not_established_by_this_local_run'}
 out=ROOT/'research/validation'/f'{args.report_date}{"-"+args.label if args.label else ""}-local.json';out.parent.mkdir(exist_ok=True)
 out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(f'PASS: {len(commands)} real commands; corpus errors=0; warnings='+str(structural['warnings']))
 print('Evidence log: '+str(out.relative_to(ROOT)))


if __name__=='__main__':main()
