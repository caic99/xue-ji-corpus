"""Machine alignment of each book's working text against Wikisource's 四庫全書本 transcription.

Run from the project root:  python3 work/compare_wikisource_skqs.py
Reads work/source-snapshots/wikisource-skqs/vNN.json and the corpus; writes work/edition-compare/raw_alignment_summary.json.
Only Chinese characters are compared (punctuation, spaces, markup removed); Wikisource {{SK notes}} and {{SK anchor}} contents are kept,
{{SKchar|N}} and Kanripo &KRnnnn; placeholders are treated as one unresolved glyph. Frequent one-character pairs (>=5 occurrences pooled
over all books) are set aside as glyph variants. The classification of the residual differences (glyph_variant / content / structure,
importance) was done by model review and is stored in work/edition-compare/edition_diffs_all.json; this script does not reproduce it.
"""
import sys, json, re, difflib, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from audit_corpus import books, CORPUS

BOOKS = {'XJ-NKZY': [1, 2], 'XJ-NKCZ': [3, 4], 'XJ-BYCY': [5], 'XJ-KCLY': [10], 'XJ-ZTLY': [11, 12],
         'XJ-WKSY': [13, 14, 15, 16], 'XJ-LYJY': [17, 18, 19]}
CJK = re.compile(r'[㐀-䶿一-鿿豈-﫿\U00020000-\U0002ffff]')


def clean_ws(w):
    w = re.sub(r'<!--.*?-->', '', w, flags=re.S)
    w = re.sub(r'\{\{SKQS (?:header|footer).*?\}\}', '', w, flags=re.S)
    w = re.sub(r'\{\{PD[^}]*\}\}', '', w)
    w = re.sub(r'\{\{SK (?:anchor|notes)\|([^}]*)\}\}', r'\1', w)
    w = re.sub(r'\{\{SKchar\|\d+\}\}', '〓', w)
    return w.replace('欽定四庫全書', '', 1)


def norm(s):
    s = re.sub(r'&KR\d+;', '〓', s)
    return ''.join(ch for ch in s if CJK.match(ch) or ch == '〓')


def compute(bodies):
    """Return (per-book raw diff rows, glyph-pair set, per-book summary). Row: (op, source_id, working_run, skqs_run)."""
    snap = ROOT / 'work/source-snapshots/wikisource-skqs'
    summary, pairs, all_diffs = {}, collections.Counter(), {}
    for work, vols in BOOKS.items():
        ws = ''.join(clean_ws(json.loads((snap / f'v{v:02d}.json').read_text(encoding='utf-8'))['parse']['wikitext']['*']) for v in vols)
        wn = norm(ws)
        recs = sorted((k for k in bodies if k.startswith(work + '-')), key=lambda k: [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', k)])
        wk, spans = '', []
        for k in recs:
            n = norm(bodies[k]); spans.append((k, len(wk), len(wk) + len(n))); wk += n
        sm = difflib.SequenceMatcher(None, wk, wn, autojunk=False)
        diffs, equal = [], 0
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                equal += i2 - i1; continue
            sid = next(k for k, a, b in spans if b > min(i1, len(wk) - 1))
            diffs.append((tag, sid, wk[i1:i2], wn[j1:j2]))
            if tag == 'replace' and len(wk[i1:i2]) == 1 and len(wn[j1:j2]) == 1 and '〓' not in wk[i1:i2] + wn[j1:j2]:
                pairs[(wk[i1:i2], wn[j1:j2])] += 1
        all_diffs[work] = diffs
        summary[work] = {'volumes': vols, 'working_chars': len(wk), 'skqs_chars': len(wn), 'equal_ratio': round(equal / max(len(wk), 1), 4), 'raw_diffs': len(diffs)}
    table = {p for p, c in pairs.items() if c >= 5}
    for work, diffs in all_diffs.items():
        resid = [d for d in diffs if '〓' not in d[2] + d[3] and not (d[0] == 'replace' and (d[2], d[3]) in table and len(d[2]) == 1 and len(d[3]) == 1)]
        summary[work]['residual_after_glyph_pairs'] = len(resid)
    return all_diffs, table, summary


def main():
    bodies = {r['meta']['source_id']: r['body'] for b in books(CORPUS.read_text(encoding='utf-8')) for r in b['rows']}
    all_diffs, table, summary = compute(bodies)
    out = ROOT / 'work/edition-compare/raw_alignment_summary.json'
    out.write_text(json.dumps({'glyph_pair_threshold': 5, 'glyph_pairs': len(table), 'books': summary}, ensure_ascii=False, indent=1), encoding='utf-8')
    for w, s in summary.items():
        print(w, s)


if __name__ == '__main__':
    main()
