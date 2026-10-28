# Saudi law, change by change: the Basic Law of Governance and the Labour Law

Two Saudi laws as a git repository, in Arabic: the Basic Law of Governance (النظام الأساسي للحكم, 1992) and the
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
| `basic-law/a-90-1412` | Royal Order A/90 of 27/8/1412 H | 1992-03-06 | 85 | 0 |
| `labour-law/m-51-1426` | Royal Decree M/51 of 23/8/1426 H | 2006-04-26 | 247 | 0 |
| `basic-law/a-135-1427` | Royal Order A/135 of 26/9/1427 H | 2006-10-19 | 1 | 0 |
| `labour-law/m-24-1434` | Royal Decree M/24 of 12/5/1434 H | 2013-03-24 | 2 | 0 |
| `labour-law/m-1-1435` | Royal Decree M/1 of 22/1/1435 H | 2013-11-25 | 19 | 0 |
| `labour-law/m-46-1436` | Royal Decree M/46 of 5/6/1436 H | 2015-03-25 | 51 | 0 |
| `basic-law/a-256-1438` | Royal Order A/256 of 26/9/1438 H | 2017-06-21 | 1 | 0 |
| `labour-law/m-14-1440` | Royal Decree M/14 of 22/2/1440 H | 2018-10-31 | 2 | 0 |
| `labour-law/m-134-1440` | Royal Decree M/134 of 27/11/1440 H | 2019-07-30 | 4 | 1 |
| `labour-law/m-5-1442` | Royal Decree M/5 of 7/1/1442 H | 2020-08-26 | 4 | 0 |
| `labour-law/m-44-1446` | Royal Decree M/44 of 8/2/1446 H | 2025-02-19 | 47 | 0 |

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
- `labour-law/m-134-1440`, labour-law/article-002.md (def-replace): the definition "العامل:" is not printed in the article (found 0)
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
- check_repo.py: 11 versions, 2104 file checks: 0 mismatches with the page, 0 unsourced changes, 0 Affecting-trailer differences
- test_repo.py: 6/6 passed

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
