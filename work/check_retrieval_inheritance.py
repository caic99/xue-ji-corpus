"""Check that needs_review status propagates from source records to structured units and whole formula groups.

Read-only. Exit code 1 if any gap is found. Run from the project root.
"""
import sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from audit_corpus import CORPUS, BLOCK_RE, parse_metadata, books

text = CORPUS.read_text(encoding='utf-8')
src_status = {r['meta']['source_id']: r['meta'].get('retrieval_status') for b in books(text) for r in b['rows']}
pending = {s for s, v in src_status.items() if v == 'needs_review'}
rows, groups = [], collections.defaultdict(list)
for m in BLOCK_RE.finditer(text):
    d, _ = parse_metadata(m.group(1))
    uid = d.get('case_id') or d.get('text_unit_id')
    if not uid:
        continue
    refs = [d['source_ref']] + [e.rsplit(':', 2)[0] for e in (d.get('continued_source_refs') or '').split('; ') if e]
    if d.get('continued_source_ref'):
        refs.append(d['continued_source_ref'])
    rows.append((uid, d, refs))
    if d.get('formula_id'):
        groups[d['formula_id']].append((uid, d, refs))
issues = []
for uid, d, refs in rows:
    if any(r in pending for r in refs) and d.get('retrieval_status') != 'needs_review':
        issues.append(f'unit {uid} depends on pending source but is {d.get("retrieval_status")}')
for fid, mem in groups.items():
    st = {d.get('retrieval_status') for _, d, _ in mem}
    if 'needs_review' in st and st != {'needs_review'}:
        issues.append(f'formula group {fid} has mixed statuses {sorted(st)}')
counts = collections.Counter(d.get('retrieval_status') for _, d, _ in rows)
print('pending sources:', len(pending), '| structured records by status:', dict(counts))
print('gaps:', len(issues))
for i in issues:
    print(' ', i)
sys.exit(1 if issues else 0)
