"""Check that the correction log is a complete, reversible record of every change to the source text.

Undoes work/edition-compare/applied_corrections.json on the current source bodies (batches in reverse order; inside a batch, edits in reverse
of (start, end); each new text is expected at `new_start`) and compares the recovered source-text digest with the pre-correction baseline.
Run from the project root:  python3 work/edition-compare/verify_reversible.py
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'work'))
import audit_corpus as ac

ORIGINAL = '20077b83bcb6a1e8a437a43ad5141ad8274cb8656135dbd8a6934d112ad1abe9'
items = ac.books(ac.CORPUS.read_text(encoding='utf-8'))
log = json.loads((ROOT / 'work/edition-compare/applied_corrections.json').read_text(encoding='utf-8'))['applied']
bodies = {r['meta']['source_id']: r['body'] for b in items for r in b['rows']}
bad = 0
for batch in sorted({e['batch'] for e in log}, reverse=True):
    for e in sorted((e for e in log if e['batch'] == batch), key=lambda e: (e['source_id'], e['start'], e['end']), reverse=True):
        b = bodies[e['source_id']]; s = e['new_start']; n = e['new']
        if b[s:s + len(n)] != n:
            bad += 1; print('unmatched', e['source_id'], e['batch_name']); continue
        bodies[e['source_id']] = b[:s] + e['old'] + b[s + len(n):]
for b in items:
    for r in b['rows']:
        r['body'] = bodies[r['meta']['source_id']]
for b in items:  # records added later (record_added_status) are not part of the pre-correction baseline
    b['rows'] = [r for r in b['rows'] if not r['meta'].get('record_added_status')]
digest = ac.text_digest(items)
print(f'log entries {len(log)}, unmatched {bad}, recovered digest {digest}')
ok = bad == 0 and digest == ORIGINAL
print('REVERSIBLE: recovered the pre-correction source text exactly' if ok else 'NOT reversible')
sys.exit(0 if ok else 1)
