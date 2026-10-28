"""Replays the amendment notes of laws.boe.gov.sa into versions: one event (commit) per amending instrument.

Every note is classified by its wording into operations. Only these are applied, mechanically, with the words the note
quotes (nothing is typed by hand):
  delete       "أُلغيت / حُذفت / تم إلغاء هذه المادة", "تم إلغاء الباب ..." (the article is removed)
  replace      "عُدلت هذه المادة ... لتكون بالنص الآتي: "..."", "إلغاء نص هذه المادة ... وإحلال النص الآتي محله"
  multi        "تم تعديل أحكام المواد (..) و(..) ... على النحو الآتي: "المادة X: ..." "المادة Y: ..."" (the listed
               articles not reprinted are removed)
  move         "تم تعديل هذه المادة ونقلها لتكون (X) ... "المادة X: ..."" (old number removed, new number written)
  add          "إضافة مادة تحمل الرقم (X)", "اُضيفت هذه المادة" (an article printed in the text as such a note)
  para         "عُدلت الفقرة (N) من هذه المادة لتكون بالنص الآتي" (the paragraph labelled N gets the quoted words,
               after its printed label)
  lead         "عُدل صدر هذه المادة" (the opening line)
  subst        'إحلال كلمة "X" محل كلمتي "Y" و "Z" أينما وردت' (whole words)
  insert       'بإضافة عبارة "X" بعد كلمة "Y"' (exactly one occurrence in the scope, else not applied)
  append       "بإضافة الفقرات الآتية" (paragraphs added at the end)
  bis          'بإضافة فقرتين ... "N (مكرر)- ..."' (each after paragraph N)
  def-add      "إضافة تعريفين إلى هذه المادة" (definitions added at the end of the list)
  def-replace  "تعديل تعريف X" (the line "X: ..." gets the quoted words)
A note that cannot be applied exactly is NOT applied; the commit says so in a `Not-applied:` trailer with the reason.
"""
import datetime as dt
import re

from hijridate import Gregorian, Hijri

import parse as P
import source as S

LAWS = [
    {'key': 'basic-law', 'folder': 'basic-law-of-governance', 'name_en': 'Basic Law of Governance',
     'name_ar': 'النظام الأساسي للحكم', 'instrument': ('أ', '90', '1412-08-27'),
     'commence_clause': 'ينشر هذا النظام في الجريدة الرسمية ويعمل به اعتبارا من تاريخ نشره', 'commence_days': 0,
     'basis': ('Royal Order A/90, item 3: published in the Official Gazette (Umm al-Qura) and in force from the day of '
               'publication; the portal gives the publication day as 2/9/1412 H = 6/3/1992')},
    {'key': 'labour-law', 'folder': 'labour-law', 'name_en': 'Labour Law', 'name_ar': 'نظام العمل',
     'instrument': ('م', '51', '1426-08-23'),
     'commence_clause': 'ينشر هذا النظام في الجريدة الرسمية، ويعمل به بعد مائة وثمانين يومًا من تاريخ نشره',
     'commence_days': 180,
     'basis': ('art. 245: in force 180 days after publication in the Official Gazette; the portal gives the '
               'publication day as 25/9/1426 H = 28/10/2005, so 180 days later. Art. 74(4) (retirement age) took '
               'effect two years after that (its own last paragraph); not shown as a separate commit')},
]

PREFIX_EN = {'أ': 'A', 'م': 'M'}
KIND_EN = {'أ': 'Royal Order', 'م': 'Royal Decree'}
KIND_AR = {'أ': 'أمر ملكي', 'م': 'مرسوم ملكي'}
DIG = P.AR_DIGITS


def hijri_iso(a: str, b: str, c: str) -> str:
    a, b, c = int(a), int(b), int(c)
    y, m, d = (a, b, c) if a > 31 else (c, b, a)
    return f'{y:04d}-{m:02d}-{d:02d}'


def h2g(h: str) -> str:
    y, m, d = map(int, h.split('-'))
    return Hijri(y, m, d).to_gregorian().isoformat()


def g2h(g: str) -> str:
    y, m, d = map(int, g.split('-'))
    h = Gregorian(y, m, d).to_hijri()
    return f'{h.year:04d}-{h.month:02d}-{h.day:02d}'


DECREE = re.compile(r'\(\s*([مأ])\s*/\s*(\d+)\s*\)\s*(?:و?تاريخ|الصادر بتاريخ|بتاريخ)\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)')
COMMENCE = re.compile(r'ويعمل بها من تاريخ\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)')


class NotApplied(Exception):
    pass


# ---- notes -----------------------------------------------------------------------------------------------------------
def note_of(html: str, attached: str, attached_heading: str) -> dict:
    lines = P.lines(html)
    txt = '\n'.join(lines)
    d = txt.translate(DIG)
    decs = [(m.group(1), m.group(2), hijri_iso(m.group(3), m.group(4), m.group(5))) for m in DECREE.finditer(d)]
    if not decs:
        raise SystemExit(f'note on {attached}: no instrument found: {txt[:120]}')
    c = COMMENCE.search(d)
    return {'attached': attached, 'heading': attached_heading, 'html': html, 'lines': lines, 'text': txt,
            'instrument': decs[-1], 'all_instruments': decs,
            'commence': hijri_iso(*c.groups()) if c else None}


def quoted(txt: str) -> str:
    """Everything between the first and the last double quote (the note's quoted new text)."""
    i, j = txt.find('"'), txt.rfind('"')
    if i < 0 or j <= i:
        raise NotApplied('no quoted text in the note')
    return txt[i + 1:j]


def body_lines(s: str) -> list:
    out = []
    for l in s.split('\n'):
        l = l.strip()
        if l:
            out.append(l)
    return out


HEAD = re.compile(r'^"?\s*(المادة\s+[^:]+?)\s*:\s*(.*)$')


def split_heading(lines: list):
    """['المادة الثانية عشرة :', '1 - ...'] -> ('المادة الثانية عشرة', key, ['1 - ...'])"""
    m = HEAD.match(lines[0])
    if not m:
        return None, None, lines
    n, bis = P.ordinal(m.group(1))
    if n is None:
        return None, None, lines
    rest = [m.group(2)] + lines[1:] if m.group(2).strip() else lines[1:]
    return m.group(1).strip(), P.key_of(n, bis), rest


def segments(txt: str) -> list:
    """The quoted articles of a multi-article note: [(heading, key, lines)]."""
    body = quoted(txt)
    parts = re.split(r'"\s*\.?\s*\n\s*"\s*(?=المادة)', body)
    out = []
    for p in parts:
        h, k, ls = split_heading(body_lines(p))
        if k is None:
            raise NotApplied('a quoted article without a heading')
        out.append((h, k, ls))
    return out


def number_phrase(txt: str):
    m = re.search(r'(?:تحمل الرقم|ترتيبها|لتكون)\s*\(\s*([^)]+?)\s*\)', txt)
    return m.group(1) if m else None


def classify(n: dict) -> list:
    """The operations a note asks for (see the module docstring)."""
    t = n['text']
    i = t.find('"')
    intro = t if i < 0 else t[:i]
    flat = re.sub(r'\s+', ' ', t)
    k = n['attached']
    if n.get('added_in_text') or re.search(r'إضافة مادة|اُضيفت هذه المادة|أُضيفت هذه المادة', intro):
        ph = number_phrase(intro) if not n.get('added_in_text') else None
        if ph:
            num, bis = P.ordinal(ph)
            if num is None:
                raise SystemExit(f'add note on {k}: number not read: {ph}')
            key = P.key_of(num, bis)
        else:
            key, ph = k, n['heading'].strip('() :')
            ph = re.sub(r'^المادة\s+', '', ph)
        return [{'op': 'add', 'key': key, 'phrase': ph}]
    if re.search(r'تم تعديل أحكام (?:المواد|المادتين)', intro):
        listed = []
        for x in re.findall(r'\(([^()]+)\)', intro.split('وإعادة')[0]):
            num, bis = P.ordinal(x)
            if num:
                listed.append(P.key_of(num, bis))
        return [{'op': 'multi', 'listed': sorted(set(listed))}]
    if 'ونقلها لتكون' in intro:
        return [{'op': 'move'}]
    if re.search(r'تم إلغاء الباب', intro):
        return [{'op': 'delete', 'why': 'chapter repealed'}]
    if re.search(r'(?:أُلغيت|ألغيت|حُذفت|حذفت|تم الغاء|تم إلغاء) هذه المادة', intro):
        return [{'op': 'delete', 'why': 'article repealed'}]
    if 'تعديل تعريف' in intro:
        m = re.search(r'تعديل تعريف\s+(\S+)', intro)
        return [{'op': 'def-replace', 'term': m.group(1)}]
    if re.search(r'إضافة تعريف', intro):
        return [{'op': 'def-add'}]
    if 'إحلال' in flat and 'محل' in flat and 'إحلال النص الآتي محله' not in flat:
        pairs = re.findall(r'إحلال (?:كلمة|عبارة) "([^"]+)" محل (?:كلمتي|كلمة|عبارة|عبارتي) "([^"]+)"'
                           r'(?:\s*و\s*"([^"]+)")?', flat)
        if not pairs:
            raise SystemExit(f'subst note on {k} not read')
        return [{'op': 'subst', 'new': a, 'old': [x for x in (b, c) if x]} for a, b, c in pairs]
    if 'بإضافة عبارة' in flat:
        m = re.search(r'بإضافة عبارة\s*"\s*([^"]+?)\s*"\s*بعد كلمة\s*"\s*([^"]+?)\s*"', flat)
        para = re.search(r'الفقرة \((\d+)\)', intro)
        return [{'op': 'insert', 'phrase': m.group(1), 'after': m.group(2), 'para': para.group(1) if para else None}]
    if 'بإضافة الفقرات' in intro:
        return [{'op': 'append'}]
    if 'بإضافة فقرتين' in intro:
        return [{'op': 'bis'}]
    if 'عُدل صدر هذه المادة' in flat:
        ops = [{'op': 'lead', 'n': 0}]
        for m in re.finditer(r'عُدلت الفقرة \(([^)]+)\)', flat):
            ops.append({'op': 'para', 'label': m.group(1), 'n': len(ops)})
        return ops
    m = re.search(r'عدلت الفقرة\s*\(\s*([^)]+?)\s*\)', intro.replace('عُدلت', 'عدلت'))
    if m and re.search(r'لتكون بالنص|بالنص التالي', intro):
        return [{'op': 'para', 'label': m.group(1)}]
    if 'وإحلال النص الآتي محله' in intro or (re.search(r'هذه المادة', intro) and re.search(r'لتكون|لتصبح', intro)):
        return [{'op': 'replace'}]
    raise SystemExit(f'note on {k} not classified: {intro[:200]}')


# ---- operations ------------------------------------------------------------------------------------------------------
LABEL = re.compile(r'^\s*([^\s\-–)]{1,3}(?:\s*/\s*\d+)?)\s*(?:\(مكرر\))?\s*[-–)]\s*')


def label_of(line: str):
    m = LABEL.match(line)
    return re.sub(r'\s+', '', m.group(1)).translate(DIG) if m else None


def find_para(lines: list, label: str) -> int:
    want = re.sub(r'\s+', '', label).translate(DIG)
    hits = [i for i, l in enumerate(lines) if label_of(l) == want and '(مكرر)' not in l[:12]]
    if len(hits) != 1:
        raise NotApplied(f'paragraph ({label}) found {len(hits)} times')
    return hits[0]


def word_re(w: str, clitic: bool = False):
    return re.compile(r'(?<!\w)' + ('(?:[وفبل])?' if clitic else '') + re.escape(w) + r'(?!\w)')


def apply(arts: dict, n: dict, op: dict) -> list:
    """Applies one operation; returns the keys it touched. Raises NotApplied."""
    k, t = n['attached'], n['text']
    o = op['op']
    if o == 'delete':
        if k not in arts:
            raise NotApplied(f'article {k} is not in the text')
        del arts[k]
        return [k]
    if o == 'replace':
        if k not in arts:
            raise NotApplied(f'article {k} is not in the text')
        h, key, ls = split_heading(body_lines(quoted(t)))
        if key is not None and key != k:
            raise NotApplied(f'quoted heading is article {key}, note is on {k}')
        arts[k] = {'heading': arts[k]['heading'], 'lines': ls}
        return [k]
    if o == 'multi':
        segs = segments(t)
        keys = [s[1] for s in segs]
        for key in op['listed']:
            if key not in keys:
                arts.pop(key, None)
        for h, key, ls in segs:
            arts[key] = {'heading': h, 'lines': ls}
        return sorted(set(op['listed']) | set(keys))
    if o == 'move':
        h, key, ls = split_heading(body_lines(quoted(t)))
        if key is None:
            raise NotApplied('moved article without a heading')
        if k not in arts:
            raise NotApplied(f'article {k} is not in the text')
        del arts[k]
        arts[key] = {'heading': h, 'lines': ls}
        return [k, key]
    if o == 'add':
        ls = body_lines(quoted(t))
        h, key, ls2 = split_heading(ls)
        if key is not None:
            if key != op['key']:
                raise NotApplied(f'quoted heading is article {key}, note says {op["key"]}')
            ls = ls2
        if op['key'] in arts:
            raise NotApplied(f'article {op["key"]} already in the text')
        arts[op['key']] = {'heading': h or ('المادة ' + op['phrase']), 'lines': ls}
        return [op['key']]
    if k not in arts:
        raise NotApplied(f'article {k} is not in the text')
    a = arts[k]
    ls = list(a['lines'])
    if o == 'para':
        if 'n' in op:                               # a second change in a "عُدل صدر" note: its own quote
            q = re.findall(r'"([^"]+)"', t)[op['n']]
        else:
            q = quoted(t) if '"' in t else None
        if q is None:
            m = re.search(r'(?:الآتى|الآتي|التالي)\s*:\s*\((.*)\)\s*\.?\s*$', t, re.S)
            if not m:
                raise NotApplied('no quoted text')
            q = m.group(1)
        q = ' '.join(body_lines(q)).strip()
        i = find_para(ls, op['label'])
        if label_of(q) == label_of(ls[i]):
            ls[i] = q
        else:
            ls[i] = LABEL.match(ls[i]).group(0) + q
    elif o == 'lead':
        qs = re.findall(r'"([^"]+)"', t)
        ls[0] = qs[op['n']].strip()
    elif o == 'subst':
        total = 0
        for old in op['old']:
            ls2 = []
            for l in ls:
                l, c = word_re(old).subn(op['new'], l)
                total += c
                ls2.append(l)
            ls = ls2
        if not total:
            raise NotApplied(f'none of {op["old"]} found')
    elif o == 'insert':
        scope = [find_para(ls, op['para'])] if op['para'] else range(len(ls))
        hits = [(i, m) for i in scope for m in word_re(op['after'], clitic=True).finditer(ls[i])]
        if len(hits) != 1:
            raise NotApplied(f'"{op["after"]}" found {len(hits)} times in the scope')
        i, m = hits[0]
        ls[i] = ls[i][:m.end()] + ' ' + op['phrase'] + ls[i][m.end():]
    elif o == 'append':
        ls += body_lines(quoted(t))
    elif o == 'bis':
        for seg in re.findall(r'"([^"]+)"', t):
            seg = seg.strip()
            m = re.match(r'(\d+)\s*\(مكرر\)', seg.translate(DIG))
            if not m:
                raise NotApplied(f'bis paragraph not read: {seg[:30]}')
            i = find_para(ls, m.group(1))
            ls.insert(i + 1, seg)
    elif o == 'def-add':
        new = []
        for l in body_lines(quoted(t)):
            l = re.sub(r'^\d+\s*-\s*"?', '', l.translate(DIG)) if re.match(r'^[\d٠-٩]+\s*-', l) else l
            new.append(l.strip('"').strip())
        ls += new
    elif o == 'def-replace':
        hits = [i for i, l in enumerate(ls) if l.startswith(op['term'] + ':')]
        if len(hits) != 1:
            raise NotApplied(f'the definition "{op["term"]}:" is not printed in the article (found {len(hits)})')
        ls[hits[0]] = op['term'] + ': ' + quoted(t).strip()
    else:
        raise SystemExit(o)
    arts[k] = {'heading': a['heading'], 'lines': ls}
    return [k]


# ---- events ----------------------------------------------------------------------------------------------------------
ORDER = {'multi': 0, 'delete': 1, 'move': 2, 'add': 3, 'replace': 4}


def fname(key: str) -> str:
    return f'article-{key}.md'


def render(law: dict, arts: dict, preamble: list, structure: list) -> dict:
    f = law['folder']
    d = {f'{f}/preamble.md': '\n'.join(preamble) + '\n',
         f'{f}/structure.md': ''.join(f'{h} [article {k}]\n' for h, k in structure)}
    for key in sorted(arts):
        a = arts[key]
        d[f'{f}/{fname(key)}'] = f'# {a["heading"]}\n\n' + '\n'.join(a['lines']) + '\n'
    return d


def instrument_id(ins) -> str:
    p, num, h = ins
    return f'{PREFIX_EN[p]}/{num} of {int(h[8:])}/{int(h[5:7])}/{int(h[:4])} H'


def law_events(law: dict, offline: bool) -> list:
    page = S.fetch(law['key'], offline).decode('utf-8')
    d = P.law(page)
    meta = d['meta']
    arts, notes, structure, pending = {}, [], [], []
    for t, x in d['items']:
        if t == 'heading':
            pending.append(x)
            continue
        key = P.key_of(x['num'], x['bis'])
        for h in pending:
            structure.append((h, key))
        pending = []
        if x['added_in_text']:
            n = note_of('<br>'.join(x['lines']), key, x['heading'])
            n['added_in_text'] = True
            notes.append(n)
            continue
        if key in arts:
            raise SystemExit(f'{law["key"]}: duplicate article {key}')
        arts[key] = {'heading': x['heading'].rstrip(':').strip(), 'lines': x['lines']}
        for nh in x['notes']:
            notes.append(note_of(nh, key, x['heading']))
    if pending:
        raise SystemExit('headings after the last article')
    if law['commence_clause'] not in '\n'.join(d['preamble'] + [l for a in arts.values() for l in a['lines']]):
        raise SystemExit(f'{law["key"]}: commencement clause not found as read')
    ins = law['instrument']
    if meta['issued']['hijri'] != ins[2]:
        raise SystemExit(f'{law["key"]}: issue date {meta["issued"]} != {ins[2]}')
    pub = meta['published']['gregorian']
    if h2g(meta['published']['hijri']) != pub:
        raise SystemExit(f'{law["key"]}: publication Hijri/Gregorian mismatch {meta["published"]}')
    start = (dt.date.fromisoformat(pub) + dt.timedelta(days=law['commence_days'])).isoformat()
    events = [{'law': law, 'instrument': ins, 'kind': 'original', 'in_force': start, 'arts': dict(arts),
               'notes': [], 'applied': [], 'not_applied': [], 'meta': meta, 'basis': law['basis'],
               'published': meta['published']}]
    # group notes by instrument (number + date); a multi-article note printed on each article counts once
    groups = {}
    seen = set()
    for n in notes:
        sig = (n['instrument'], n['text'] if 'تم تعديل أحكام' in n['text'] else (n['attached'], n['text']))
        if sig in seen:
            continue
        seen.add(sig)
        groups.setdefault(n['instrument'], []).append(n)
    for ins2 in sorted(groups, key=lambda i: i[2]):
        ns = groups[ins2]
        commence = sorted({n['commence'] for n in ns if n['commence']})
        if len(commence) > 1:
            raise SystemExit(f'{ins2}: several commencement dates {commence}')
        if commence:
            day = h2g(commence[0])
            basis = (f'the notes say the amendments apply from {int(commence[0][8:])}/{int(commence[0][5:7])}/'
                     f'{commence[0][:4]} H')
        else:
            day = h2g(ins2[2])
            basis = ('the day of the instrument: the notes give no publication or commencement day; under Basic Law '
                     'art. 71 a law takes effect on publication in the Official Gazette unless it says otherwise, so the '
                     'true day is this day or some days later')
        events.append({'law': law, 'instrument': ins2, 'kind': 'amendment', 'in_force': day, 'commence': commence,
                       'notes': ns, 'basis': basis})
    # replay in order
    cur = dict(arts)
    for ev in events[1:]:
        work, added, dups = [], {}, []
        for i, n in enumerate(ev['notes']):
            for op in classify(n):
                if op['op'] == 'add' and op['key'] in added:
                    dups.append((op['key'], n, added[op['key']]))   # the same added article printed twice
                    continue
                if op['op'] == 'add':
                    added[op['key']] = n
                if op['op'] == 'multi':
                    sig = ('multi',) + tuple(op['listed'])
                    if sig in added:
                        dups.append((','.join(op['listed']), n, added[sig]))
                        continue
                    added[sig] = n
                work.append((ORDER.get(op['op'], 5), i, n, op))
        ev['duplicates'] = dups
        applied, not_applied = [], []
        for _, _, n, op in sorted(work, key=lambda x: (x[0], x[1])):
            try:
                keys = apply(cur, n, op)
                applied.append((op['op'], keys, n))
            except NotApplied as e:
                not_applied.append((op['op'], n['attached'], str(e), n))
        ev['arts'] = dict(cur)
        ev['applied'], ev['not_applied'] = applied, not_applied
    for ev in events:
        ev['files'] = render(law, ev['arts'], d['preamble'], structure)
        ev['folder'] = law['folder']
        ev['page'] = d
    return events


def events(offline: bool) -> list:
    out = []
    for law in LAWS:
        out += law_events(law, offline)
    out.sort(key=lambda e: (e['in_force'], e['law']['key']))
    prev = {}
    for e in out:
        p, num, h = e['instrument']
        e['tag'] = f'{e["law"]["key"]}/{PREFIX_EN[p].lower()}-{num}-{h[:4]}'
        e['author'] = f'{KIND_EN[p]} {instrument_id(e["instrument"])}'
        e['email'] = f'{PREFIX_EN[p].lower()}-{num}-{h[:4]}@boe.invalid'
        e['enacted'] = h2g(h)
        before = prev.get(e['folder'], {})
        e['changed'] = sorted(k for k in set(before) | set(e['files']) if before.get(k) != e['files'].get(k))
        e['message'] = message(e)
        prev[e['folder']] = e['files']
    return out


def message(e: dict) -> str:
    law, (p, num, h) = e['law'], e['instrument']
    g = h2g(h)
    ar = f'{KIND_AR[p]} رقم ({p}/{num}) وتاريخ {int(h[8:])}/{int(h[5:7])}/{int(h[:4])}هـ'
    src = S.wayback(law['key'])
    if e['kind'] == 'original':
        subj = f'{law["name_en"]}: enacted by {KIND_EN[p]} {instrument_id(e["instrument"])}'
        body = [f'{law["name_ar"]} — {ar}.', '',
                f'The text as enacted, from the Bureau of Experts portal, which prints the original text of each '
                f'article with the later amendments as notes. {len([k for k in e["files"] if "/article-" in k])} '
                f'articles; preamble.md holds the issuing instrument(s), structure.md the parts and chapters.']
        tr = ['Kind: original', f'Instrument: {KIND_EN[p]} {PREFIX_EN[p]}/{num}', f'Enacted: {g}',
              f'Enacted-hijri: {h}', f'Published: {e["published"]["gregorian"]}',
              f'Published-hijri: {e["published"]["hijri"]}']
    else:
        subj = f'{law["name_en"]}: {KIND_EN[p]} {instrument_id(e["instrument"])}'
        if len(subj) > 72:
            subj = subj[:72]
        counts = {}
        for o, _, _ in e['applied']:
            counts[o] = counts.get(o, 0) + 1
        body = [f'{law["name_ar"]}: {ar}.', '',
                'REPLAYED from the portal\'s amendment notes: ' + ', '.join(f'{v} {k}' for k, v in sorted(counts.items()))
                + ' (operations, see REPRODUCE.md). No official consolidated text of this version exists to compare it '
                'with; every other file is unchanged.']
        if e['not_applied']:
            body += ['', f'{len(e["not_applied"])} note(s) could not be applied exactly and are NOT in the text; see '
                     'the Not-applied trailers.']
        if len(e['notes'][0]['all_instruments']) > 1 or any(len(n['all_instruments']) > 1 for n in e['notes']):
            body += ['', 'One note names two instruments (art. 74(4): Royal Decrees M/46 of 1436 and M/134 of 1440) '
                     'and quotes only the final words; they are credited to the later instrument.']
        tr = ['Kind: amendment', f'Instrument: {KIND_EN[p]} {PREFIX_EN[p]}/{num}', f'Enacted: {g}',
              f'Enacted-hijri: {h}']
        if e.get('commence'):
            tr.append(f'In-force-hijri: {e["commence"][0]}')
        tr.append('Evidence: replay of the amendment notes on laws.boe.gov.sa')
    tr += [f'In-force: {e["in_force"]}']
    if e['kind'] == 'original' or not e.get('commence'):
        tr.append(f'In-force-hijri: {g2h(e["in_force"])}')
    tr.append(f'In-force-basis: {e["basis"]}')
    for f in e['changed']:
        tr.append(f'Affecting: {f}')
    for k, n, first in e.get('duplicates', []):
        where = lambda x: 'in the text' if x.get('added_in_text') else f'as a note on article {x["attached"]}'
        if ',' in k:
            tr.append(f'Also-printed: the note rewriting articles {k.replace(",", " ")} is printed again '
                      f'{where(n)} (first {where(first)}); the copies differ only in punctuation; the first is used')
        else:
            tr.append(f'Also-printed: {law["folder"]}/{fname(k)}: the added article is printed twice ({where(first)} '
                      f'and {where(n)}, with small differences of punctuation); the first is used')
    for o, k, why, _ in e.get('not_applied', []):
        tr.append(f'Not-applied: {law["folder"]}/{fname(k)}: {o}: {why}')
    tr.append(f'Source: {src}')
    return subj + '\n\n' + '\n'.join(body) + '\n\n' + '\n'.join(tr) + '\n'
