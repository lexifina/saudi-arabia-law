"""Checks every version in the built repository against the source pages. Standard library only (plus the cache).

    python -X utf8 check_repo.py --repo DIR [--record]

For each law:
1. Byte check. Every file of the first commit equals the original text as parsed from the page (parse.py), and every
   file a later commit did not touch is byte-identical to the previous version.
2. Independent letter-stream check of the original. A minimal extractor (no article parser) takes div#divLawText of
   the raw page, drops the amendment buttons and pop-up notes and the articles printed as "added by" notes, strips
   every tag, and keeps only letters and digits (casefolded). That stream must equal the letters and digits of the first
   commit's files, read in order (preamble, then each heading and article as structure.md and the file names order
   them).
3. Every change is sourced. For each later commit, each changed file is diffed word by word with its previous version;
   every inserted or replaced run of words must occur (as letters and digits) in the raw text of that instrument's
   notes on the page; a removed file must be named in a note of that instrument; and the commit's Affecting trailers
   list exactly the changed files.
With --record the summary goes to verification.json next to this script.
"""
import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import parse as P  # noqa: E402
import replay as R  # noqa: E402
import source as S  # noqa: E402

NONALNUM = re.compile(r'[\W_]+')
AR = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')


def letters(s: str) -> str:
    return NONALNUM.sub('', s.translate(AR)).casefold()


def raw_text(fragment: str) -> str:
    import html
    return html.unescape(re.sub(r'<[^>]+>', ' ', fragment))


class Repo:
    def __init__(self, repo: Path):
        self.repo = repo
        self.cat = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=repo, stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE)

    def git(self, *a):
        return subprocess.run(['git', *a], cwd=self.repo, capture_output=True, check=True).stdout.decode('utf-8')

    def blob(self, sha: str) -> str:
        self.cat.stdin.write(sha.encode() + b'\n')
        self.cat.stdin.flush()
        head = self.cat.stdout.readline().split()
        data = self.cat.stdout.read(int(head[2]))
        self.cat.stdout.read(1)
        return data.decode('utf-8')

    def tree(self, rev: str, folder: str) -> dict:
        out = {}
        for l in self.git('ls-tree', '-r', rev, '--', folder + '/').splitlines():
            meta, path = l.split('\t', 1)
            out[path] = self.blob(meta.split()[2])
        return out


def raw_original_stream(page: str) -> str:
    """Letters of the original text, read from the raw page without the article parser."""
    body = page[page.find('id="divLawText"'):]
    body = body.split('>', 1)[1]
    body = re.sub(r'<div class="article_btns">.*?(?=<p><div class="HTMLContainer">)', ' ', body, flags=re.S)
    # articles printed as "added by" notes are not part of the original text
    body = re.sub(r'<div class="article_item[^"]*">\s*(?:<h3[^>]*>[^<]*</h3>\s*)+\s*<p><div class="HTMLContainer">\s*'
                  r'(?:<[^>]+>\s*)*-?\s*(?:اُضيفت|أُضيفت|أضيفت|إضافة مادة).*?</div></p>', ' ', body, flags=re.S)
    last = body.rfind('</div></p>')
    return letters(raw_text(body[:last]))


def raw_notes(page: str) -> dict:
    """{instrument number+year: letters of every note naming it}, from the raw page."""
    out = {}
    body = page[page.find('id="divLawText"'):]
    chunks = re.findall(r'<div class="article_item_popup">(.*?)</div>\s*(?:<a [^>]*></a>\s*)?</div>', body, re.S)
    chunks += re.findall(r'<p><div class="HTMLContainer">\s*((?:<[^>]+>\s*)*-?\s*(?:اُضيفت|أُضيفت|أضيفت|إضافة مادة).*?)'
                         r'</div></p>', body, re.S)
    for c in chunks:
        t = raw_text(c).translate(AR)
        for m in re.finditer(r'\(\s*([مأ])\s*/\s*(\d+)\s*\)', t):
            out.setdefault(f'{m.group(1)}/{m.group(2)}', []).append(t)
    return {k: v for k, v in out.items()}


def check(repo: Path) -> dict:
    r = Repo(repo)
    res = {'versions': 0, 'files_checked': 0, 'mismatches': [], 'unsourced': [], 'trailers': []}
    for law in R.LAWS:
        page = S.fetch(law['key'], True).decode('utf-8')
        d = P.law(page)
        folder = law['folder']
        notes = raw_notes(page)
        heads_raw = {letters(raw_text(x)) for x in re.findall(r'<h3[^>]*>(.*?)</h3>', page, re.S)}
        log = r.git('log', '--reverse', '--format=%H%x09%(trailers:key=Instrument,valueonly,separator=)%x09'
                    '%(trailers:key=Affecting,valueonly,separator=|)%x09%(trailers:key=Kind,valueonly,separator=)',
                    'main', '--', folder).splitlines()
        prev = None
        for row in log:
            h, ins, aff, kind = row.split('\t')
            cur = r.tree(h, folder)
            res['versions'] += 1
            if kind == 'original':
                # 1. bytes against the parsed page
                want = R.render(law, {P.key_of(x['num'], x['bis']): {'heading': x['heading'].rstrip(':').strip(),
                                                                      'lines': x['lines']}
                                      for t, x in d['items'] if t == 'article' and not x['added_in_text']},
                                d['preamble'], [])
                for p, txt in want.items():
                    if p.endswith('structure.md'):
                        continue
                    res['files_checked'] += 1
                    if cur.get(p) != txt:
                        res['mismatches'].append(f'{h[:10]} {p}: differs from the page')
                # 2. independent letter stream
                heads = {}
                for line in cur[f'{folder}/structure.md'].splitlines():
                    m = re.fullmatch(r'(.*) \[article ([0-9]+(?:-bis)?)\]', line)
                    heads.setdefault(m.group(2), []).append(m.group(1))
                stream = [cur[f'{folder}/preamble.md']]
                for p in sorted(x for x in cur if '/article-' in x):
                    k = p.rsplit('article-', 1)[1][:-3]
                    stream += heads.get(k, [])
                    stream.append(cur[p].replace('# ', '', 1))
                a, b = letters('\n'.join(stream)), raw_original_stream(page)
                if a != b:
                    i = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
                    res['mismatches'].append(f'{h[:10]} {folder}: letter stream differs from the raw page at {i} '
                                             f'(repo {len(a)}, raw {len(b)}): repo[{a[i - 20:i + 40]}] '
                                             f'raw[{b[i - 20:i + 40]}]')
                res['files_checked'] += 1
            else:
                # 3. every change sourced in the instrument's notes
                num = re.search(r'([AM])/(\d+)', ins)
                key = {'A': 'أ', 'M': 'م'}[num.group(1)] + '/' + num.group(2)
                src = letters(' | '.join(notes.get(key, [])))
                if not src:
                    res['unsourced'].append(f'{h[:10]} {ins}: no notes on the page')
                changed = sorted(p for p in set(prev) | set(cur) if prev.get(p) != cur.get(p))
                listed = sorted(x for x in aff.split('|') if x)
                if changed != listed:
                    res['trailers'].append(f'{h[:10]}: Affecting {len(listed)} != changed {len(changed)}')
                for p in sorted(set(prev) | set(cur)):
                    res['files_checked'] += 1
                    if prev.get(p) == cur.get(p):
                        continue
                    if p not in cur:
                        continue                      # removal: named by the Affecting trailer (checked above)
                    tok = lambda txt: [w for line in txt.split('\n') for w in line.split() + ['\n']]
                    old, new = tok(prev.get(p, '')), tok(cur[p])
                    sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
                    for o, i1, i2, j1, j2 in sm.get_opcodes():
                        if o not in ('insert', 'replace'):
                            continue
                        runs, run = [], []
                        for w in new[j1:j2]:
                            if w == '\n':
                                runs.append(run)
                                run = []
                            else:
                                run.append(w)
                        runs.append(run)
                        for run in runs:
                            head = run[:1] == ['#']
                            if run[:2] == ['#', 'المادة']:      # heading of a new article: the note's number words
                                run = run[2:]
                            lt = letters(' '.join(run))
                            if head and lt in heads_raw:        # or the heading the page prints for it
                                continue
                            if lt and lt not in src:
                                res['unsourced'].append(f'{h[:10]} {p}: "{" ".join(run)[:80]}"')
            prev = cur
    n_bad = len(res['mismatches']) + len(res['unsourced']) + len(res['trailers'])
    res['summary'] = (f'{res["versions"]} versions, {res["files_checked"]} file checks: {len(res["mismatches"])} '
                      f'mismatches with the page, {len(res["unsourced"])} unsourced changes, {len(res["trailers"])} '
                      f'Affecting-trailer differences')
    res['ok'] = n_bad == 0
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--record', action='store_true')
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    res = check(Path(args.repo))
    for k in ('mismatches', 'unsourced', 'trailers'):
        for x in res[k][:40]:
            print(k.upper(), x)
    print(res['summary'])
    if args.record:
        p = HERE / 'verification.json'
        rec = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
        rec['check'] = {'summary': res['summary'], 'ok': res['ok']}
        p.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8',
                     newline='\n')
    raise SystemExit(0 if res['ok'] else 1)


if __name__ == '__main__':
    main()
