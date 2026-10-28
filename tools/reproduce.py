"""Writes the repository's documentation (README.md, LICENSE, REPRODUCE.md, corpus.json, instruments.csv) and the tools.
Called by build.py; returns {path: text}. Deterministic (no clock, no network). verification.json (written by
check_repo.py and test_repo.py with --record) is read when it exists, so a second build carries the check results."""
import hashlib
import json
import subprocess
from pathlib import Path

import source as S

TOOLS = ('build.py', 'source.py', 'parse.py', 'replay.py', 'reproduce.py', 'check_repo.py', 'test_repo.py')


def blob(p: Path) -> str:
    return subprocess.run(['git', 'hash-object', str(p)], capture_output=True, text=True).stdout.strip()


def docs(events, day: str, here: Path, wip: bool = False) -> dict:
    out = {}
    ver = {}
    vp = here / 'verification.json'
    if vp.exists():
        ver = json.loads(vp.read_text(encoding='utf-8'))
    laws = []
    for e in events:
        if e['law'] not in laws:
            laws.append(e['law'])
    first = events[0]['in_force']
    last = max(e['in_force'] for e in events if e['in_force'] <= day)
    n_na = sum(len(e.get('not_applied', [])) for e in events)
    corpus = {
        'corpus': 'sa/national/acts',
        'name': 'Saudi law: the Basic Law of Governance (1992) and the Labour Law (2005), with their amendments',
        'label': 'Saudi Arabia',
        'language': 'ar',
        'acts': [f'{l["name_ar"]} ({l["name_en"]})' for l in laws],
        'history': 'in-force',
        'history_from': first,
        'record_to': last,
        'checked_on': day,
        'built': day,
        'record_note': ("Later versions are replayed from the BOE's amendment notes; no official consolidation exists "
                        'to check them. '
                        f'Original texts and every amendment note printed by the Bureau of Experts portal '
                        f'(laws.boe.gov.sa, Wayback captures of January 2026), replayed; checked {day}. Later versions '
                        f'are replays of editorial notes, not official consolidations; {n_na} note(s) could not be '
                        f'applied exactly and are named in Not-applied trailers. Dates of royal decrees without a '
                        f'stated commencement are the decree day (In-force-basis).'),
        'in_force_trailer': 'In-force',
        'has_future_branch': False,
        'dates': {'commit': 'in-force',
                  'other_trailers': ['Enacted', 'Enacted-hijri', 'Published', 'Published-hijri', 'In-force-hijri',
                                     'In-force-basis'],
                  'time': '12:00 Asia/Riyadh (UTC+3; no summer time)', 'calendar': 'Gregorian dates converted '
                  'from the Hijri (Umm al-Qura) dates printed by the source; Hijri kept in *-hijri trailers'},
        'scope': {
            'trailer': 'Applies',
            'when_absent': 'this corpus records no scope notes (no commit carries Applies:); the absence is not a '
                           'statement that the change reaches every case',
            'default_reach': {
                'rule': 'no retroactive effect of laws; no crime or penalty without a text, and no punishment for '
                        'acts before the text',
                'meaning': 'a law applies from its in-force day and does not reach back unless it says so; penal '
                           'provisions never reach acts done before them',
                'authority': 'Basic Law of Governance, art. 38 ("ولا عقاب إلا على الأعمال اللاحقة للعمل بالنص '
                             'النظامي") and art. 71 (laws take effect on publication unless another date is set)',
                'decided_here': False}},
        'replayed': 'yes: every version after the original text of each law is replayed from the portal\'s notes',
        'tool': 'tools/salaw.py',
        'citation': {'file': '([a-z-]+)/article-0*([0-9]+(?:-bis)?)\\.md',
                     'cites': '(المادة|مادة) ?\\(? ?{n} ?\\)?([^0-9]|$)'},
        'citation_note': 'Saudi texts cite articles by ordinal words (المادة (السابعة والثلاثين)), so the numeric '
                         'rule finds few citations',
    }
    out['corpus.json'] = json.dumps(corpus, indent=2, ensure_ascii=False) + '\n'

    rows = ['tag,law,instrument,enacted,enacted_hijri,in_force,in_force_hijri,files_changed,operations,not_applied,'
            'in_force_basis']
    from replay import g2h
    for e in events:
        p, num, h = e['instrument']
        rows.append(','.join('"' + str(x).replace('"', '""') + '"' for x in [
            e['tag'], e['law']['name_en'], e['author'], e.get('enacted', ''), h, e['in_force'], g2h(e['in_force']),
            len(e['changed']), len(e.get('applied', [])), len(e.get('not_applied', [])), e['basis']]))
    out['instruments.csv'] = '\n'.join(rows) + '\n'

    out['LICENSE'] = (
        'Source of the legal texts: the Bureau of Experts at the Council of Ministers (هيئة الخبراء بمجلس الوزراء),\n'
        'Kingdom of Saudi Arabia, laws portal https://laws.boe.gov.sa/ , read through Internet Archive captures.\n\n'
        'Terms of use (https://www.boe.gov.sa/ar/Pages/TermsOfUse.aspx, capture 20261022175531): the portal is\n'
        '"available for your personal use" (متاحة لاستخدامك الشخصي); the terms forbid loads that burden the portal and\n'
        'interfering with it, and say nothing about copying, reuse or databases. No reuse licence is published. The\n'
        'reuse terms are therefore unclear: this repository is private and is not to be published until they are settled.\n\n'
        'Only the Official Gazette (Umm al-Qura) is authoritative. Every version after the original text of each law is\n'
        'derived (replayed) from the portal\'s amendment notes by the method in REPRODUCE.md; it is not published by\n'
        'the Bureau of Experts.\n\n'
        'Attribution for the legal texts: "Texts: Bureau of Experts at the Council of Ministers, https://laws.boe.gov.sa/".\n\n'
        'The history (commits and commit messages), the tables and the tools are dedicated to the public domain under\n'
        'CC0 1.0 Universal: https://creativecommons.org/publicdomain/zero/1.0/legalcode\n')

    ok = ''
    if ver:
        c, s = ver.get('check', {}), ver.get('smoke', {})
        ok = (f'- check_repo.py: {c.get("summary", "not recorded")}\n'
              f'- test_repo.py: {s.get("passed", "?")}/{s.get("total", "?")} passed\n')
    table = '\n'.join(
        f'| `{e["tag"]}` | {e["author"]} | {e["in_force"]} | {len(e["changed"])} | {len(e.get("not_applied", []))} |'
        for e in events)
    na = '\n'.join(f'- `{e["tag"]}`, {e["law"]["folder"]}/article-{k}.md ({o}): {why}'
                   for e in events for o, k, why, _ in e.get('not_applied', [])) or '- none'
    status = ('**Status: building, source laws.boe.gov.sa (Bureau of Experts). Work in progress on the `wip` branch; '
              'not final.**\n\n') if wip else ''
    out['README.md'] = f'''# Saudi law, change by change: the Basic Law of Governance and the Labour Law

{status}Two Saudi laws as a git repository, in Arabic: the Basic Law of Governance (النظام الأساسي للحكم, 1992) and the
Labour Law (نظام العمل, 2005). Each law starts as enacted; each later royal order or decree that amended it is one
commit, credited to that instrument and dated the day it took effect, at noon in Riyadh. Hijri dates are in the
trailers. Source: the Bureau of Experts at the Council of Ministers, laws.boe.gov.sa.

**Every version after the first is a replay.** The portal prints each law's original text and, under each changed
article, editorial notes naming the amending instrument and quoting the new words. No consolidated text of any later
version is published, so each later version here is the original with the notes applied mechanically (see
REPRODUCE.md). Notes that cannot be applied exactly are left out and named in `Not-applied:` trailers.

## The questions, as git commands

| Question | Command |
| --- | --- |
| What did Labour Law art. 74 say on 1 January 2016? | `python tools/salaw.py 2016-01-01 labour-law 74` |
| ... and on 1 March 2025, after Royal Decree M/44? | `python tools/salaw.py 2025-03-01 labour-law 74` |
| Basic Law art. 5 before and after Royal Order A/256 (2017) | `python tools/salaw.py 2017-06-20 basic-law-of-governance 5` |
| The whole Basic Law on 1 January 2000 | `python tools/salaw.py 2000-01-01 basic-law-of-governance` |
| Which instrument wrote each line of art. 74 today? | `git blame main -- labour-law/article-074.md` |
| Every change to Labour Law art. 74, with its instrument and day | `git log --format="%an %(trailers:key=In-force,valueonly,separator=)" main -- labour-law/article-074.md` |
| Exactly what Royal Decree M/44 changed, word by word | `git show --word-diff labour-law/m-44-1446` |
| Everything one instrument changed | `git show --stat labour-law/m-46-1436` |
| The instruments, with their in-force days | `git log --format="%an, in force %(trailers:key=In-force,valueonly,separator=)" main` |
| The Hijri dates | `git log --format="%an: %(trailers:key=Enacted-hijri,valueonly,separator=)" main` |
| One tag per instrument | `git tag --list` |
| How each in-force day was read | `git log --format="%an: %(trailers:key=In-force-basis,valueonly,separator=)" main` |
| Notes that could not be applied | `git log --format="%an: %(trailers:key=Not-applied,valueonly,separator=; )" main` |

PowerShell splits `git show $(...):path`; use `$r = git rev-list -1 main; git show "$($r):labour-law/article-074.md"`.
For a date, prefer `tools/salaw.py`, which reads the `In-force:` trailer: `git rev-list --before=DATE` compares commit
times in your own time zone and flips at noon on the day itself.

## The instruments

| Tag | Author | In force | Files changed | Notes not applied |
| --- | --- | --- | --- | --- |
{table}

See [`instruments.csv`](instruments.csv) for Hijri dates and the basis of each in-force day.

## The dates, and which one we use

The portal prints Hijri (Umm al-Qura) dates; they are converted to Gregorian with the Umm al-Qura tables of the
`hijridate` package and both are kept (`Enacted:` / `Enacted-hijri:`, `In-force:` / `In-force-hijri:`). Commits are
dated the day the text took effect, at noon in Riyadh (UTC+3). How that day was read is in `In-force-basis:`:
- Basic Law: in force on publication (Royal Order A/90, item 3); the portal gives 2/9/1412 H = 6 March 1992.
- Labour Law: in force 180 days after publication (art. 245); published 25/9/1426 H = 28 October 2005.
- Royal Decree M/44 of 8/2/1446 H: the notes say its amendments apply from 20/8/1446 H (19 February 2025).
- Every other instrument: **the day of the instrument**, because the notes give no publication or commencement day.
  Under Basic Law art. 71 a law takes effect on publication in Umm al-Qura unless it says otherwise, so the true day is
  that day or some days later. Read these dates as "not before".

## What "author" means

The author of a commit is the instrument that made the text (`Royal Decree M/46 of 5/6/1436 H`, address
`m-46-1436@boe.invalid`), so `git blame` names it. The committer is always `Lexifina`.

## Read this before comparing versions

- **Replayed, not consolidated.** Only the first commit of each law is the portal's own text; later files are built
  from the notes' quoted words. Typography inside a quote is the note's (for example "-" or "–").
- **Not applied:**
{na}
- **Renumbering.** Royal Decree M/46 of 1436 H rewrote Labour Law arts. 229-239 and 241 as two articles (229, 230),
  moved art. 240 to 231 and art. 242 to 232, and added 233. A file name holds the article of that number in the text in
  force.
- **Article 74(4)** of the Labour Law took effect two years after the law (its own last paragraph); not a separate commit.
- **The portal's own text has errors.** In the original definitions of art. 2 the worker's definition is printed under
  "صاحب العمل:" and "العامل:" is missing; the later amendment to "العامل" therefore cannot be applied (see above).
- **Blame credits whole lines**: one line is one paragraph. Use `--word-diff` for the words.

## How it is checked

`tools/check_repo.py` reads every version back from git and compares it with the source page: each file a version did
not change must equal the original text byte for byte and as a stream of letters and digits read from the raw page by a
separate minimal extractor; each change an instrument made must consist only of words found in that instrument's notes.
`tools/test_repo.py` checks that the commands above work. See [`REPRODUCE.md`](REPRODUCE.md).
Later versions are replayed from the BOE's amendment notes; no official consolidation exists to check them, so the
checks show that each change is the notes' own words, not that the result matches an official text.
{ok}
## Files

`<law>/article-NNN.md` is one article (`article-011-bis.md` is art. 11 مكرر); the `#` line is its heading as printed,
then one line per paragraph, exactly as the portal prints it. `preamble.md` is the issuing instrument(s) as printed, and
`structure.md` the parts and chapters of the original text, each with the article it opens.

## What it does not show

- Implementing regulations, ministerial decisions and court practice; words unchanged does not mean law unchanged.
- Amendments the portal does not record as notes.
- The English translation, which is not authoritative.

## Licence

Reuse terms are unclear and the repository is private. See [`LICENSE`](LICENSE). Tools, history and tables: CC0.
'''

    man = S.manifest(offline=True)
    src_rows = '\n'.join(f'- `{k}`: {v["url"]} (Wayback capture `{v["capture"]}`, {v["bytes"]} bytes, sha256 '
                         f'`{v["sha256"]}`)' for k, v in man.items())
    blobs = '\n'.join(f'- `{n}`: `{blob(here / n)}`' for n in TOOLS) + \
        f'\n- `salaw.py`: `{blob(here / "repo/tools/salaw.py")}`'
    try:
        import importlib.metadata as im
        hv = im.version('hijridate')
    except Exception:
        hv = '?'
    ops = {}
    for e in events:
        for o, _, _ in e.get('applied', []):
            ops[o] = ops.get(o, 0) + 1
    out['REPRODUCE.md'] = f'''# Reproduce

Data retrieved {day}. The build is deterministic: the same data gives the same commit hashes.

## Sources and requests

The Bureau of Experts portal (https://laws.boe.gov.sa/) does not answer from the build machine's network (TCP connect
to 66.9.136.215 on ports 443 and 80 times out). Every page is read from a pinned Internet Archive capture through the
raw-bytes form `http://web.archive.org/web/<capture>id_/<url>`, which returns what the portal served that day:
{src_rows}

The build reads the two law pages; robots.txt and the terms page were read for the gate. Requests went one at a time
with a 10-second pause (the portal's robots.txt `Crawl-delay: 10`), cached gzip-compressed in `cache/` (git-ignored).
Before the build, exploration made about 20 further requests to archive.org (CDX listings of laws.boe.gov.sa, the
"basic laws" folder page, the English terms page, which is not archived).

robots.txt of laws.boe.gov.sa (capture 20251020104010, unchanged in later captures): `User-agent: *`, `Crawl-delay: 10`,
Disallow `/Identity/`, `/admin/`, `/search/` and a few Drupal paths; no rule for ClaudeBot, Claude-Web or anthropic-ai.
Terms: see LICENSE.

## Steps

1. `python -X utf8 tools/build.py --repo <dir>` (online once; then `--offline` rebuilds from the cache).
   `--verify-rebuild` builds again in a temporary folder and compares HEAD.
2. `python -X utf8 tools/check_repo.py --repo <dir> --record`, `python -X utf8 tools/test_repo.py --repo <dir> --record`.
3. Build again (the documentation then carries the results of step 2) and run `--verify-rebuild`.

Tool versions: Python 3.12, `hijridate` {hv} (Umm al-Qura calendar, the only dependency outside the standard library),
git (history written with one `git fast-import` stream), curl (Windows). Builder blob hashes (`git hash-object`):
{blobs}

## Method

- `parse.lines`: `<br>`, `<p>`, `<div>` and headings end a line; other markup dropped; entities decoded; NBSP and
  zero-width marks become spaces; runs of spaces become one; empty lines dropped. Nothing else is normalised.
- `parse.law`: the original text is `div#divLawText`: the issuing instrument(s) before the law title (`preamble.md`),
  part/chapter headings (`structure.md`), and one block per article; Arabic ordinal headings are read into numbers
  ("الحادية والثلاثون بعد المائة مكرر" -> 131-bis). The build stops on a duplicate or unreadable number.
- `replay.py`: each amendment note names its instrument (`(م/46) وتاريخ 5/6/1436`) and quotes the new words. Notes are
  grouped by instrument (one commit each) and classified by their wording into operations ({", ".join(f"{k} {v}" for
  k, v in sorted(ops.items()))}); the module docstring lists them. Within one instrument: rewrites of several articles
  first, then repeals, moves, additions, whole replacements, and partial changes. A note printed twice is applied once
  (`Also-printed:`). A note that cannot be applied exactly is not applied (`Not-applied:`).
- In-force days and their basis: see README and `instruments.csv`. Hijri to Gregorian: `hijridate` (Umm al-Qura).

## Decisions by hand, and AI

No model wrote legal text or ran at build time. The code was written by Claude Code with Claude Opus 5.5
(`claude-opus-5-5`), which also chose the acts (the Basic Law and the Labour Law, the most amended law with notes on the
portal) and wrote the note classifier. Decisions by hand:
- reading the portal through Wayback captures (the portal is unreachable from here);
- the decree day as the in-force day where the notes give none (labelled "not before" in `In-force-basis:`);
- the note on Labour Law art. 74(4) that names two instruments (M/46 of 1436 and M/134 of 1440) and quotes only the
  final words is credited to the later one; M/46's own whole-article replacement of art. 74 is applied as printed;
- definitions added by M/44 to art. 2 are appended at the end of the list (the note does not say where);
- the first copy of a note printed twice is used.

## Verification record

{ok or '(not yet recorded)'}'''
    for n in TOOLS:
        out[f'tools/{n}'] = (here / n).read_text(encoding='utf-8')
    out['tools/salaw.py'] = (here / 'repo/tools/salaw.py').read_text(encoding='utf-8')
    out['.gitattributes'] = '* text eol=lf\n'
    return out
