# Saudi law, change by change

4 Saudi laws as a git repository, in Arabic, from the Bureau of Experts at the Council of Ministers
(laws.boe.gov.sa). Each law starts as enacted; each later royal order or decree that amended it is one commit, credited
to that instrument and dated the day it took effect, at noon in Riyadh. Hijri dates are in the trailers.
13 commits of law: 4 enactments and 9 amending instruments.

**Every version after the first is a replay.** The portal prints each law's original text and, under each changed
article, editorial notes naming the amending instrument and quoting the new words. No consolidated text of any later
version is published, so each later version here is the original with the notes applied mechanically (see
REPRODUCE.md). Notes that cannot be applied exactly are left out and named in `Not-applied:` trailers.

## The laws

| Folder | Name | English name (ours) | Issued by | In force | Amending instruments |
| --- | --- | --- | --- | --- | --- |
| `basic-law-of-governance` | النظام الأساسي للحكم | Basic Law of Governance | Royal Order A/90 of 27/8/1412 H | 1992-03-06 | 2 |
| `labour-law` | نظام العمل | Labour Law | Royal Decree M/51 of 23/8/1426 H | 2006-04-26 | 7 |
| `companies-law` | نظام الشركات | Companies Law | Royal Decree M/132 of 1/12/1443 H | 2023-01-18 | 0 |
| `civil-transactions-law` | نظام المعاملات المدنية | Civil Transactions Law | Royal Decree M/191 of 29/11/1444 H | 2023-12-16 | 0 |

The first two (the Basic Law of Governance and the Labour Law) were built first; the others were appended later, each as
one block of commits on top of the history, so `git log` lists them after the first two. Read versions by their
`In-force:` trailer, as `tools/salaw.py` does.

## The questions, as git commands

| Question | Command |
| --- | --- |
| What did Labour Law art. 74 say on 1 January 2016? | `python tools/salaw.py 2016-01-01 labour-law 74` |
| The whole Basic Law on 1 January 2000 | `python tools/salaw.py 2000-01-01 basic-law-of-governance` |
| Any law, any day | `python tools/salaw.py <YYYY-MM-DD> <folder> [article]` |
| Which instrument wrote each line of an article | `git blame main -- labour-law/article-074.md` |
| Every change to an article, with its instrument and day | `git log --format="%an %(trailers:key=In-force,valueonly,separator=)" main -- labour-law/article-074.md` |
| Exactly what one instrument changed, word by word | `git show --word-diff labour-law/m-44-1446` |
| The instruments, with their in-force days | `git log --format="%an, in force %(trailers:key=In-force,valueonly,separator=)" main` |
| How each in-force day was read | `git log --format="%an: %(trailers:key=In-force-basis,valueonly,separator=)" main` |
| Notes that could not be applied | `git log --format="%an: %(trailers:key=Not-applied,valueonly,separator=; )" main` |

For a date, prefer `tools/salaw.py`, which reads the `In-force:` trailer: `git rev-list --before=DATE` compares commit
times, and the appended laws' commits come after the first two in the log.

See [`instruments.csv`](instruments.csv) for every instrument, its Hijri dates and the basis of its in-force day.

## The dates, and which one we use

The portal prints Hijri (Umm al-Qura) dates; they are converted to Gregorian with the Umm al-Qura tables of the
`hijridate` package and both are kept (`Enacted:` / `Enacted-hijri:`, `In-force:` / `In-force-hijri:`). Commits are
dated the day the text took effect, at noon in Riyadh (UTC+3). How that day was read is in `In-force-basis:`:
- A law's first version: its own commencement clause, counted from the publication day the portal gives ("in force
  N days after publication" is publication day + N). Laws whose commencement could not be read as a number of days
  are not included yet.
- An amending instrument whose notes give a commencement day: that day.
- Every other instrument: **the day of the instrument**, because the notes give no publication or commencement day.
  Under Basic Law art. 71 a law takes effect on publication in Umm al-Qura unless it says otherwise, so the true day is
  that day or some days later. Read these dates as "not before".
- Git cannot store dates before 1970; a commit for an earlier day carries 1970-01-01 as its git date and the true day in
  `In-force:`.

## What "author" means

The author of a commit is the instrument that made the text (`Royal Decree M/46 of 5/6/1436 H`, address
`m-46-1436@boe.invalid`), so `git blame` names it. The committer is always `Lexifina`.

## Read this before comparing versions

- **Replayed, not consolidated.** Only the first commit of each law is the portal's own text; later files are built
  from the notes' quoted words. Typography inside a quote is the note's.
- **Not applied** (1):
- `labour-law/m-134-1440`, labour-law/article-002.md (def-replace): the definition "العامل:" is not printed in the article (found 0)
- **Article files** hold the article of that number in the text in force; a renumbering moves text between files.
- **The portal's own text has errors**, kept as printed.
- **Blame credits whole lines**: one line is one paragraph. Use `--word-diff` for the words.

## How it is checked

Before each publication every version is read back from git and compared with the source page: each file a version did
not change must equal the original text byte for byte and as a stream of letters and digits read from the raw page by a
separate minimal extractor; each change an instrument made must consist only of words found in that instrument's notes.
That shows each change is the notes' own words, not that the result matches an official consolidation (none exists).

## Files

`<law>/article-NNN.md` is one article (`article-011-bis.md` is art. 11 مكرر); the `#` line is its heading as printed,
then one line per paragraph, exactly as the portal prints it. `preamble.md` is the issuing instrument(s) as printed, and
`structure.md` the parts and chapters of the original text, each with the article it opens.

## What it does not show

- Implementing regulations, ministerial decisions and court practice; words unchanged does not mean law unchanged.
- Amendments the portal does not record as notes.
- The English translation, which is not authoritative.

## Licence

See [`LICENSE`](LICENSE). Tools, history and tables: CC0.
