# Reproduce

Data retrieved 2026-10-28. The build is deterministic: the same data gives the same commit hashes.

## Sources and requests

The Bureau of Experts portal (https://laws.boe.gov.sa/) does not answer from the build machine's network (TCP connect
to 66.9.136.215 on ports 443 and 80 times out). Every page is read from a pinned Internet Archive capture through the
raw-bytes form `http://web.archive.org/web/<capture>id_/<url>`, which returns what the portal served that day:
- `basic-law`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/16b97fcb-4833-4f66-8531-a9a700f161b6/1 (Wayback capture `20260114204621`, 105812 bytes, sha256 `d22c50f069bd1ace05320303790348a112c3c68a752e4290ee03d593dc57c450`)
- `labour-law`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/08381293-6388-48e2-8ad2-a9a700f2aa94/1 (Wayback capture `20260128140901`, 566959 bytes, sha256 `a6ddeb0a2c70812332c93dd54da268e07b5108ae750a268e3dcd53584fced55a`)
- `robots`: https://laws.boe.gov.sa/robots.txt (Wayback capture `20251020104010`, 808 bytes, sha256 `50eb41f3da7f4066a3f272124ff0665eae189ef6c4e16f08f16210844b1403b8`)
- `terms`: https://www.boe.gov.sa/ar/Pages/TermsOfUse.aspx (Wayback capture `20261022175531`, 44729 bytes, sha256 `73f4db07ea364c6b0666a7c620cc33365286b4b61ba37abec1b4797c93cdcbd0`)

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

Tool versions: Python 3.12, `hijridate` 2.5.0 (Umm al-Qura calendar, the only dependency outside the standard library),
git (history written with one `git fast-import` stream), curl (Windows). Builder blob hashes (`git hash-object`):
- `build.py`: `7c11ace0803a53cc5a3511f3d1205f622d14ab25`
- `source.py`: `dbf396b9f5784e1d6b186d3370a20ee84e0f27b4`
- `parse.py`: `e4ecdf79f0193abb3dfa36641730a72b0e992eca`
- `replay.py`: `4f06197df05a381cfcf1e181ba4742c6e3ef5085`
- `reproduce.py`: `6a492c9ffb3b25731ed6ca9412b79d1cc419daa5`
- `check_repo.py`: `afce58511143bf1993d4c5fcc7067f754fc65d74`
- `test_repo.py`: `6a1b1ab02b89645c700dcfb34ec82744588b9fc2`
- `salaw.py`: `6b21f168969a90ce88aa17e7fb11838a569eddc9`

## Method

- `parse.lines`: `<br>`, `<p>`, `<div>` and headings end a line; other markup dropped; entities decoded; NBSP and
  zero-width marks become spaces; runs of spaces become one; empty lines dropped. Nothing else is normalised.
- `parse.law`: the original text is `div#divLawText`: the issuing instrument(s) before the law title (`preamble.md`),
  part/chapter headings (`structure.md`), and one block per article; Arabic ordinal headings are read into numbers
  ("الحادية والثلاثون بعد المائة مكرر" -> 131-bis). The build stops on a duplicate or unreadable number.
- `replay.py`: each amendment note names its instrument (`(م/46) وتاريخ 5/6/1436`) and quotes the new words. Notes are
  grouped by instrument (one commit each) and classified by their wording into operations (add 7, append 1, bis 1, def-add 1, delete 30, insert 3, lead 1, move 2, multi 3, para 9, replace 56, subst 8); the module docstring lists them. Within one instrument: rewrites of several articles
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

- check_repo.py: 11 versions, 2104 file checks: 0 mismatches with the page, 0 unsourced changes, 0 Affecting-trailer differences
- test_repo.py: 6/6 passed
