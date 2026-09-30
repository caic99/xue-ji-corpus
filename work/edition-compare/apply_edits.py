"""Apply image-verified text corrections to source records and migrate every structured record that cites the edited text.

usage:  python3 work/edition-compare/apply_edits.py EDITS.json [--write]

EDITS.json: list of {"source_id", "old", "new", "start"?, "end"?, "page", "note", "evidence"}.
If start/end are absent, `old` must occur exactly once in the source body (pure insertions must carry start==end).
Without --write the result is validated in memory only.

What is migrated for each edited record (all in one pass, then validated with audit_corpus.validate_structured_units):
  * the source body itself;
  * source_start_char / source_end_char_exclusive (and continued_* / continued_source_refs, baseline p{k}_*, c{k}_*, comparison a_*, b_*)
    of every structured record that cites the record: offsets shift by the length change of edits before them;
  * the printed text of case / text-unit blocks (re-rendered from the new spans);
  * every *_quote field (and baseline/comparison quotes) that overlaps an edit;
  * printed quote text in baseline / comparison blocks.
Each edited record also gets `text_correction_applied` + `pre_correction_body_sha256`; all edits are appended to
work/edition-compare/applied_corrections.json (old, new, offsets, evidence) so the change is auditable and reversible.
Insertions that coincide with a structured-span boundary are refused (ambiguous ownership).
"""
import sys, json, re, hashlib, collections, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'work'))
import audit_corpus as ac

MAIN = ac.CORPUS
LOG = ROOT / 'work/edition-compare/applied_corrections.json'


def source_bodies(text):
    """sid -> (abs_start, abs_end, body) using the same boundaries as audit_corpus.books()."""
    out = {}
    starts = list(ac.BOOK_RE.finditer(text))
    for i, st in enumerate(starts):
        stop = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        section = text[st.start():stop]
        for m in ac.RECORD_RE.finditer(section):
            body = m.group(3).rstrip()
            out[m.group(1)] = (st.start() + m.start(3), st.start() + m.start(3) + len(body), body)
    return out


class EditSet:
    def __init__(self, edits):
        self.by = collections.defaultdict(list)
        for e in edits:
            self.by[e['source_id']].append(e)
        for sid, lst in self.by.items():
            lst.sort(key=lambda e: (e['start'], e['end']))
            for a, b in zip(lst, lst[1:]):
                if b['start'] < a['end'] or (b['start'] == a['end'] and a['start'] == a['end'] == b['start'] == b['end']):
                    raise ValueError(f'{sid}: overlapping edits {a} {b}')

    def new_body(self, sid, body):
        out, cur = [], 0
        for e in self.by[sid]:
            out.append(body[cur:e['start']]); out.append(e['new']); cur = e['end']
        out.append(body[cur:])
        return ''.join(out)

    def pos(self, sid, p, bias):
        """Map an old body offset to the new body. bias 'start' keeps an insertion at p outside a span starting at p; 'end' likewise for a span ending at p."""
        shift = 0
        for e in self.by.get(sid, []):
            if e['end'] <= p and not (e['start'] == e['end'] == p):
                shift += len(e['new']) - (e['end'] - e['start'])
            elif e['start'] == e['end'] == p:
                if bias == 'start':
                    shift += len(e['new'])      # insertion at a span start is *before* the span (excluded)
            elif e['start'] < p < e['end']:
                # endpoint inside a replaced run: map to the far edge of the new text
                base = e['start'] + shift
                return base if bias == 'start' else base + len(e['new'])
        return p + shift

    def overlaps(self, sid, a, b):
        for e in self.by.get(sid, []):
            if e['start'] == e['end']:
                if a < e['start'] < b: return True
            elif e['start'] < b and e['end'] > a:
                return True
        return False


def block_printed_region(text, m):
    rest = text[m.end():]
    boundary = re.search(r'\n### |\n<!-- [A-Z0-9]+_[A-Z_]+_END -->', rest)
    seg = rest[:boundary.start()] if boundary else rest
    padding = ' \t\n\r\x0b\x0c'
    stripped = seg.strip(padding)
    lead = len(seg) - len(seg.lstrip(padding))
    return m.end() + lead, m.end() + lead + len(stripped), stripped


def kv_line(key, value):
    return f'{key}: ' + (str(value) if isinstance(value, int) else json.dumps(value, ensure_ascii=False))


def set_line(y, key, value):
    pat = re.compile(r'^%s: .*$' % re.escape(key), re.M)
    assert pat.search(y), key
    return pat.sub(lambda _: kv_line(key, value), y, count=1)


def apply(edits, write):
    text = MAIN.read_text(encoding='utf-8')
    items = ac.books(text)
    bodies = {r['meta']['source_id']: r['body'] for b in items for r in b['rows']}
    src = source_bodies(text)
    # resolve start/end
    resolved = []
    for e in edits:
        body = bodies[e['source_id']]
        if 'start' not in e:
            hits = [m.start() for m in re.finditer(re.escape(e['old']), body)] if e['old'] else []
            if len(hits) != 1:
                raise ValueError(f"{e['source_id']}: old text {e['old']!r} occurs {len(hits)} times")
            e = dict(e, start=hits[0], end=hits[0] + len(e['old']))
        assert body[e['start']:e['end']] == e['old'], (e['source_id'], e)
        assert e['old'] != e['new']
        resolved.append(e)
    es = EditSet(resolved)
    edited = set(es.by)
    repl = []  # (abs_start, abs_end, new_text)
    # 1) source bodies + per-record annotation
    for sid in edited:
        a, b, body = src[sid]
        nb = es.new_body(sid, body)
        repl.append((a, b, nb))
    # 2) structured blocks
    span_keys = []  # (metadata prefix, source key, start key, end key, continued spec)
    for m in ac.BLOCK_RE.finditer(text):
        meta, _ = ac.parse_metadata(m.group(1))
        uid = meta.get('case_id') or meta.get('text_unit_id') or meta.get('baseline_id') or meta.get('comparison_id')
        if not uid:
            continue
        y = m.group(1)
        ychanged = False

        def spans_of(prefix):
            """list of (sid, start, end, setter(kind, values))"""
            out = []
            if prefix == '':
                out.append((meta['source_ref'], int(meta['source_start_char']), int(meta['source_end_char_exclusive']), ('source_start_char', 'source_end_char_exclusive')))
                if meta.get('continued_source_ref'):
                    out.append((meta['continued_source_ref'], int(meta['continued_start_char']), int(meta['continued_end_char_exclusive']), ('continued_start_char', 'continued_end_char_exclusive')))
                if meta.get('continued_source_refs'):
                    for entry in meta['continued_source_refs'].split('; '):
                        s, a, b = entry.rsplit(':', 2)
                        out.append((s, int(a), int(b), ('chain',)))
            else:
                out.append((meta[f'{prefix}_source_ref'], int(meta[f'{prefix}_start_char']), int(meta[f'{prefix}_end_char_exclusive']), (f'{prefix}_start_char', f'{prefix}_end_char_exclusive')))
                if meta.get(f'{prefix}_continued_source_refs'):
                    for entry in meta[f'{prefix}_continued_source_refs'].split('; '):
                        s, a, b = entry.rsplit(':', 2)
                        out.append((s, int(a), int(b), ('chain',)))
            return out

        if meta.get('case_id') or meta.get('text_unit_id'):
            groups = [('', 'block')]
        elif meta.get('baseline_id'):
            groups = [(f'p{k}', 'q') for k in range(1, int(meta['supporting_passage_count']) + 1)] + [(f'c{k}', 'q') for k in range(1, int(meta.get('counterexample_count', '0')) + 1)]
        else:
            groups = [('a', 'q'), ('b', 'q')]
        touched = False
        for prefix, kind in groups:
            sp = spans_of(prefix)
            if not any(s in edited for s, _, _, _ in sp):
                continue
            touched = True
            new_sp = []
            old_text = []
            for s, a, b, keys in sp:
                old_text.append(bodies[s][a:b])
                for e in es.by.get(s, []):
                    if e['start'] == e['end'] and e['start'] in (a, b):
                        raise ValueError(f'{uid}: insertion in {s} at {e["start"]} coincides with a span boundary')
                na, nb_ = es.pos(s, a, 'start'), es.pos(s, b, 'end')
                new_sp.append((s, na, nb_, keys))
            newbodies = lambda s: es.new_body(s, bodies[s]) if s in edited else bodies[s]
            joiner = '\n\n' if kind == 'block' else ''
            old_expected = joiner.join(old_text)
            new_expected = joiner.join(newbodies(s)[na:nb_] for s, na, nb_, _ in new_sp)
            # update offsets in yaml
            chain = []
            for (s, a, b, keys), (_, na, nb_, _) in zip(sp, new_sp):
                if keys[0] == 'chain':
                    chain.append(f'{s}:{na}:{nb_}')
                else:
                    if (na, nb_) != (a, b):
                        y = set_line(y, keys[0], na); y = set_line(y, keys[1], nb_)
            if chain:
                ckey = 'continued_source_refs' if prefix == '' else f'{prefix}_continued_source_refs'
                y = set_line(y, ckey, '; '.join(chain))
            # quotes
            if kind == 'q':
                y = set_line(y, f'{prefix}_quote', new_expected)
            else:
                for key, val in meta.items():
                    if key.endswith('_quote') and val:
                        occ = [mm.start() for mm in re.finditer(re.escape(val), old_expected)]
                        if not occ:
                            raise ValueError(f'{uid}: {key} not found in old text')
                        # map occurrence to new text through segment offsets
                        chosen = None
                        off = 0
                        segs = []
                        for (s, a, b, _), (_, na, nb_, _) in zip(sp, new_sp):
                            segs.append((off, off + (b - a), s, a, na, nb_)); off += (b - a) + len(joiner)
                        for q in occ:
                            for (o0, o1, s, a, na, nb_) in [(x[0], x[1], x[2], x[3], x[4], x[5]) for x in segs]:
                                if o0 <= q and q + len(val) <= o1:
                                    la, lb = a + (q - o0), a + (q - o0) + len(val)
                                    if es.overlaps(s, la, lb):
                                        nq_a, nq_b = es.pos(s, la, 'start'), es.pos(s, lb, 'end')
                                        chosen = newbodies(s)[nq_a:nq_b]
                                    break
                            else:
                                if any(es.overlaps(s2, a2, b2) for (_, _, s2, a2, _, _) in segs for b2 in [a2]):
                                    raise ValueError(f'{uid}: {key} crosses spans and overlaps an edit')
                            if chosen is not None:
                                break
                        if chosen is not None and chosen != val:
                            y = set_line(y, key, chosen)
            # printed text
            pa, pb, printed = block_printed_region(text, m)
            if kind == 'block':
                assert printed == old_expected, f'{uid}: printed text differs from old expected'
                repl.append((pa, pb, new_expected))
            ychanged = True
        if touched:
            if y != m.group(1):
                repl.append((m.start(1), m.end(1), y))
            if not (meta.get('case_id') or meta.get('text_unit_id')):
                # baseline / comparison printed text: swap old quote text for new quote text
                pa, pb, printed = block_printed_region(text, m)
                new_printed = printed
                for prefix, _ in groups:
                    sp = spans_of(prefix)
                    if any(s in edited for s, _, _, _ in sp):
                        oldq = meta[f'{prefix}_quote']
                        newq = ac.parse_metadata(y)[0][f'{prefix}_quote']
                        new_printed = new_printed.replace(oldq, newq)
                if new_printed != printed:
                    repl.append((pa, pb, new_printed))
    # 3) per-record annotations on the source yaml
    log = json.loads(LOG.read_text(encoding='utf-8')) if LOG.exists() else {'applied': []}
    today = datetime.date.today().isoformat()
    for sid in edited:
        pat = re.compile(r'^##### %s\n\n```yaml\n(.*?)\n```' % re.escape(sid), re.M | re.S)
        for m in pat.finditer(text):
            y = m.group(1)
            desc = '；'.join(f"「{e['old']}」→「{e['new']}」（承應本影像PDF第{e.get('page','?')}頁；{e.get('evidence','承應本影像與四庫本一致')}）" for e in es.by[sid])
            ex = re.search(r'^text_correction_applied: (".*")$', y, re.M)
            if ex:
                # record already corrected once: extend the note, keep the first pre-correction digest
                prev = json.loads(ex.group(1))
                repl.append((m.start(1) + ex.start(1), m.start(1) + ex.end(1), json.dumps(prev + f'；{today} 追加：{desc}', ensure_ascii=False)))
                continue
            add = [kv_line('text_correction_applied', f'{today} 依承應本影像與四庫本對照改正：{desc}。原轉錄讀法見 edition-compare/applied_corrections.json'),
                   kv_line('pre_correction_body_sha256', hashlib.sha256(bodies[sid].encode()).hexdigest())]
            repl.append((m.end(1), m.end(1), '\n' + '\n'.join(add)))
    # apply replacements (descending)
    repl.sort(key=lambda r: (r[0], r[1]), reverse=True)
    for (a, b, t), (a2, b2, _) in zip(repl, repl[1:]):
        if b > a2 and a < b2 and not (a == b == b2):
            pass
    for a, b, t in repl:
        text = text[:a] + t + text[b:]
    # validate in memory
    items2 = ac.books(text)
    ac.validate_structured_units(text, items2)
    if write:
        batch = 1 + max([e.get('batch', 0) for e in log['applied']] or [0])
        per = collections.defaultdict(list)
        for e in resolved:
            per[e['source_id']].append(e)
        for sid, lst in per.items():
            lst.sort(key=lambda e: (e['start'], e['end'])); delta = 0
            for e in lst:
                e['new_start'] = e['start'] + delta; delta += len(e['new']) - len(e['old'])
        for e in resolved:
            log['applied'].append({'source_id': e['source_id'], 'start': e['start'], 'end': e['end'], 'new_start': e['new_start'], 'old': e['old'], 'new': e['new'], 'batch': batch, 'batch_name': e.get('batch_name', f'batch{batch}'), 'page': e.get('page'), 'note': e.get('note'), 'evidence': e.get('evidence', '承應本影像與四庫本一致'), 'date': today})
        LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8')
        MAIN.write_text(text, encoding='utf-8')
    return text, len(resolved), len(edited)


if __name__ == '__main__':
    edits = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    text, n, r = apply(edits, '--write' in sys.argv)
    print(f'{n} edits in {r} records; validation passed; written={"--write" in sys.argv}')
