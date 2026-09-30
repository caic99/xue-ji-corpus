"""Turn image-verified proposed corrections into exact edits on source-record bodies (dry run; writes edit_list.json).

An edit is {source_id, start, end, old, new} in body coordinates (Python characters). Tiers: 'auto' when the differing run is located
uniquely in the record and expressible as a plain substitution/insert/delete; otherwise 'manual' with the reason.
Glyph forms: the 四庫 reading uses 四庫 variant glyphs (隂, 术, 茋 ...); new text is converted back to the working text's own forms
with the pooled glyph-pair table so corrections do not import variant glyphs.
"""
import json, re, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'work'))
from audit_corpus import books, CORPUS

CJK = re.compile(r'[㐀-䶿一-鿿豈-﫿\U00020000-\U0002ffff]')
DOSE = re.compile(r'[錢分兩斤片枚個各半一二三四五六七八九十]')
res = json.loads((ROOT / 'work/edition-compare/image_check_results.json').read_text(encoding='utf-8'))
pairs = json.loads((ROOT / 'work/edition-compare/glyph_variant_pairs_ge5.json').read_text(encoding='utf-8'))
to_working = {}
for k, c in pairs.items():
    w, s = k.split('>')
    if len(w) == 1 and len(s) == 1:
        to_working.setdefault(s, []).append((c, w))
to_working = {s: max(v)[1] for s, v in to_working.items()}
items = books(CORPUS.read_text(encoding='utf-8'))
bodies = {r['meta']['source_id']: r['body'] for b in items for r in b['rows']}
vocab = collections.Counter(ch for b in bodies.values() for ch in b)


def ctx(c):
    return re.match(r'^(.*?)【(.*?)】(.*)$', c, re.S).groups()


def body_index(body):
    idx = [i for i, ch in enumerate(body) if CJK.match(ch)]
    return idx, ''.join(body[i] for i in idx)


def locate(nstr, left, w, right):
    for k in range(min(8, len(left)), -1, -1):
        for kr in range(min(8, len(right)), -1, -1):
            pat = (left[len(left) - k:] if k else '') + w + (right[:kr] if kr else '')
            if not w and not (k and kr):
                continue
            hits = [m.start() for m in re.finditer(re.escape(pat), nstr)]
            if len(hits) == 1:
                return hits[0] + k
    return None


def convert(s):
    out = []
    for ch in s:
        ch2 = to_working.get(ch, ch)
        out.append(ch2)
    return ''.join(out)


edits, manual = [], []
for x in res:
    if not (x['verdict'] == 'skqs' and x['confidence'] == 'high'):
        continue
    sid = x['source_id']; body = bodies[sid]
    L, w, R = ctx(x['working_ctx']); _, s, _ = ctx(x['skqs_ctx'])
    base = {'source_id': sid, 'page': x['page'], 'note': x['note'], 'working_run': w, 'skqs_run': s, 'print_reading': x['image_reading']}
    if '〓' in w + s:
        manual.append({**base, 'reason': 'unresolved glyph placeholder'}); continue
    new = convert(s)
    bad = [ch for ch in new if vocab[ch] < 2 and CJK.match(ch)]
    if bad:
        manual.append({**base, 'reason': f'unfamiliar glyphs {bad} after conversion'}); continue
    idx, nstr = body_index(body)
    pos = locate(nstr, L, w, R)
    if pos is None:
        manual.append({**base, 'reason': 'run not uniquely located in record'}); continue
    if max(len(w), len(s)) > 6:
        manual.append({**base, 'reason': 'long run (clause-level difference)'}); continue
    if w:
        a, b = idx[pos], idx[pos + len(w) - 1] + 1
        inner = body[a:b]
        if len(w) == len(s):
            # equal length: replace char-by-char at the CJK positions (punctuation between stays)
            e_list = [(idx[pos + k], idx[pos + k] + 1, w[k], new[k]) for k in range(len(w)) if w[k] != new[k]]
            for (a1, b1, o, n2) in e_list:
                assert body[a1:b1] == o, (sid, o, body[a1:b1])
                edits.append({**base, 'start': a1, 'end': b1, 'old': o, 'new': n2, 'tier': 'auto'})
            continue
        if inner != w:
            manual.append({**base, 'reason': 'run spans punctuation with unequal replacement'}); continue
        edits.append({**base, 'start': a, 'end': b, 'old': w, 'new': new, 'tier': 'auto'}); continue
    # pure insertion: after previous CJK char, unless an opening bracket sits between (then after the bracket)
    prev, nxt = idx[pos - 1], idx[pos] if pos < len(idx) else len(body)
    gap = body[prev + 1:nxt]
    at = prev + 1
    m = re.search(r'[（(]', gap)
    if m: at = prev + 1 + m.end()
    edits.append({**base, 'start': at, 'end': at, 'old': '', 'new': new, 'tier': 'auto'})

# detect overlapping edits in one record
by = collections.defaultdict(list)
for e in edits: by[e['source_id']].append(e)
for sid, lst in by.items():
    lst.sort(key=lambda e: (e['start'], e['end']))
    for a, b in zip(lst, lst[1:]):
        if b['start'] < a['end']:
            a['tier'] = b['tier'] = 'manual'
out = {'edits': [e for e in edits if e['tier'] == 'auto'], 'manual': manual + [dict(e, reason='overlapping edits') for e in edits if e['tier'] == 'manual']}
(ROOT / 'work/edition-compare/edit_list.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print('auto edits', len(out['edits']), 'records', len({e['source_id'] for e in out['edits']}), 'manual', len(out['manual']))
print(collections.Counter(m['reason'].split(' [')[0][:40] for m in out['manual']))
