"""Parses a laws.boe.gov.sa LawDetails page (Arabic) into metadata, preamble, articles and amendment notes.

Page shape (2026 captures):
  - metadata block: تاريخ الإصدار / تاريخ النشر (Hijri + Gregorian), أدوات إصدار النظام (issuing instruments)
  - div#divLawText: the ORIGINAL enacted text. Headings (الباب / الفصل) are <h3 class="center"> between articles;
    each article is <div class="article_item ..."> with <h3> heading and a <div class="HTMLContainer"> body.
  - a changed article also holds <div class="... popup-list"> with one <div class="article_item_popup"> per amendment
    note: an editorial note naming the amending royal decree/order and its date, with the new words in quotes.
Text is kept as printed: tags removed, <br>/<p> are line breaks, entities decoded, runs of spaces and NBSP collapsed to
one space, each line stripped. Nothing else is normalised.
"""
import html as H
import re

WS = re.compile(r'[ \t ​‌‏‎﻿]+')
TAG = re.compile(r'<[^>]+>')
BREAK = re.compile(r'<br\s*/?>|</?p[^>]*>|</div>|<div[^>]*>|</h\d>|<h\d[^>]*>', re.I)
AR_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')


def lines(fragment: str) -> list:
    t = BREAK.sub('\n', fragment)
    t = TAG.sub('', t)
    t = H.unescape(t)
    out = []
    for l in t.split('\n'):
        l = WS.sub(' ', l).strip()
        if l:
            out.append(l)
    return out


def text(fragment: str) -> str:
    return WS.sub(' ', H.unescape(TAG.sub(' ', fragment))).strip()


# ---- Arabic ordinals -------------------------------------------------------------------------------------------------
UNITS = {'الأولى': 1, 'الاولى': 1, 'الحادية': 1, 'الثانية': 2, 'الثالثة': 3, 'الرابعة': 4, 'الخامسة': 5,
         'السادسة': 6, 'السابعة': 7, 'الثامنة': 8, 'التاسعة': 9, 'العاشرة': 10}
TENS = {'العشرون': 20, 'العشرين': 20, 'الثلاثون': 30, 'الثلاثين': 30, 'الأربعون': 40, 'الأربعين': 40,
        'الاربعون': 40, 'الاربعين': 40, 'الخمسون': 50, 'الخمسين': 50, 'الستون': 60, 'الستين': 60,
        'السبعون': 70, 'السبعين': 70, 'الثمانون': 80, 'الثمانين': 80, 'التسعون': 90, 'التسعين': 90}
HUNDREDS = {'المائة': 100, 'المئة': 100, 'المائتين': 200, 'المائتان': 200, 'المئتان': 200, 'المئتين': 200}


def ordinal(s: str):
    """'الحادية والثلاثون بعد المائة مكرر' -> (131, True). Returns (None, False) when not an ordinal."""
    s = WS.sub(' ', s).strip().rstrip(':').strip()
    m = re.search(r'\(([^()]*)\s+سابقاً\)', s)          # '(... حالياً) (المادة ... سابقاً)': the original number
    if m:
        s = m.group(1)
    s = s.strip('() ').strip()
    s = re.sub(r'^المادة\s+', '', s)
    bis = False
    if s.endswith('مكرر') or s.endswith('مكررة'):
        bis = True
        s = re.sub(r'\s*مكرر[ة]?$', '', s)
    base = 0
    m = re.search(r'\s*بعد\s+(المائة|المئة|المائتين)$', s)
    if m:
        base = HUNDREDS[m.group(1)]
        s = s[:m.start()].strip()
    elif s in HUNDREDS:
        return HUNDREDS[s], bis
    n = 0
    parts = [p.strip() for p in re.split(r'\s+و', ' ' + s) if p.strip()]
    for p in parts:
        p = p if p.startswith('ال') else 'ال' + p
        if p in UNITS:
            n += UNITS[p]
        elif p in TENS:
            n += TENS[p]
        elif p == 'العشرة' or p == 'عشرة' or p == 'العشر':
            n += 10
        else:
            m2 = re.fullmatch(r'(ال\S+) عشرة', p)
            if m2 and m2.group(1) in UNITS:
                n += UNITS[m2.group(1)] + 10
            else:
                return None, False
    return (base + n if n else None), bis


def key_of(n: int, bis: bool) -> str:
    return f'{n:03d}' + ('-bis' if bis else '')


# ---- page ------------------------------------------------------------------------------------------------------------
def meta(page: str) -> dict:
    def field(label):
        m = re.search(label + r'\s*</[^>]+>\s*<[^>]+>(.*?)</', page, re.S)
        return text(m.group(1)) if m else ''
    out = {}
    head = page[:page.find('id="divLawText"')]
    t = '\n'.join(lines(head))
    for k, label in (('issued', 'تاريخ الإصدار'), ('published', 'تاريخ النشر')):
        m = re.search(label + r'\s*\n\s*(\d{4})/(\d{2})/(\d{2})\s*هـ\s*الموافق\s*:\s*(\d{2})/(\d{2})/(\d{4})', t)
        if not m:
            raise SystemExit(f'metadata: {label} not found')
        out[k] = {'hijri': f'{m.group(1)}-{m.group(2)}-{m.group(3)}',
                  'gregorian': f'{m.group(6)}-{m.group(5)}-{m.group(4)}'}
    m = re.search(r'الحالة\s*\n\s*(\S+)', t)
    out['status'] = m.group(1) if m else ''
    m = re.search(r'أدوات إصدار النظام\s*\n(.*?)\nالبحث في النظام', t, re.S)
    out['instruments'] = m.group(1).split('\n') if m else []
    m = re.search(r'Law name\s*\n(.*?)\n', t)
    out['name_en'] = m.group(1).strip() if m else ''
    m = re.search(r'\nالاسم\s*\n(.*?)\n', t)
    out['name_ar'] = m.group(1).strip() if m else ''
    return out


def law(page: str) -> dict:
    """{'meta', 'preamble': [lines], 'items': [('heading', line) | ('article', dict)]}"""
    start = page.find('id="divLawText"')
    if start < 0:
        raise SystemExit('no divLawText')
    body = page[start:]
    end = body.find('<div class="system_info')
    first = body.find('<div class="article_item ')
    pre_html = body[:first]
    cut = pre_html.find('<h1 class="system_title">')
    if cut < 0:
        raise SystemExit('no law title before the first article')
    preamble = lines(pre_html.split('>', 1)[1][:cut - len(pre_html.split('>', 1)[0]) - 1])
    title = re.search(r'<h1 class="system_title">(.*?)</h1>', pre_html[cut:], re.S)
    preamble.append(text(title.group(1)))       # the law's title as printed above its first article
    items = [('heading', text(h)) for h in re.findall(r'<h3 class="center">(.*?)</h3>', pre_html[cut:], re.S)]
    # split into article blocks; headings between articles are <h3 class="center"> outside article_item
    parts = re.split(r'(<div class="article_item [^"]*">)', body[first:])
    pending = parts[0]
    for i in range(1, len(parts), 2):
        cls = parts[i]
        blk = parts[i + 1]
        # heading text before this article (from the previous block's tail) is handled below
        hs = re.match(r'(\s*<h3 class="center">.*?</h3>)+', blk, re.S)
        if not hs:
            raise SystemExit('article without heading')
        h3 = [text(x) for x in re.findall(r'<h3 class="center">(.*?)</h3>', hs.group(0), re.S)]
        items += [('heading', x) for x in h3[:-1]]
        heading = h3[-1]
        notes = []
        pop = re.search(r'<div style="display: none;" class="[^"]*popup-list">(.*?)\n\s*</div>\s*\n\s*<p>', blk,
                        re.S)
        rest = blk
        if pop:
            for nb in re.findall(r'<div class="article_item_popup">\s*<h3>.*?</h3>\s*<div class="HTMLContainer">'
                                 r'(.*?)</div>\s*(?:<a [^>]*></a>\s*)?</div>', pop.group(1), re.S):
                notes.append(nb)
            rest = blk[pop.end() - len('<p>'):]
        mb = re.search(r'<p><div class="HTMLContainer">(.*?)</div></p>', rest, re.S)
        if not mb:
            raise SystemExit(f'no body for {heading}')
        tail = rest[mb.end():]
        n, bis = ordinal(heading)
        body_lines = lines(mb.group(1))
        added = bool(body_lines) and re.match(r'-?\s*(اُضيفت|أُضيفت|أضيفت|إضافة مادة)', body_lines[0]) is not None
        items.append(('article', {'heading': heading, 'num': n, 'bis': bis, 'lines': body_lines, 'added_in_text': added,
                                  'notes': notes, 'changed': 'changed-article' in cls,
                                  'canceled': 'canceled' in cls or 'cancel' in cls}))
        for hh in re.findall(r'<h3 class="center">(.*?)</h3>', tail, re.S):
            items.append(('heading', text(hh)))
    del pending, end
    return {'meta': meta(page), 'preamble': preamble, 'items': items}
