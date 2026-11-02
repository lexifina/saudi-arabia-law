# Reproduce

Data last read 2026-11-02.

## Sources

Each law is the Arabic page of the Bureau of Experts portal, as archived by the Internet Archive on the day given:
- `basic-law-of-governance`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/16b97fcb-4833-4f66-8531-a9a700f161b6/1 (Internet Archive capture `20260114204621`)
- `labour-law`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/08381293-6388-48e2-8ad2-a9a700f2aa94/1 (Internet Archive capture `20260128140901`)
- `companies-law`: https://laws.boe.gov.sa/boelaws/Laws/LawDetails/a8376aea-1bc3-49d4-9027-aed900b555af/1 (Internet Archive capture `20260218115042`)
- `civil-transactions-law`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/655fdb42-8c96-422b-b8c4-b04f0095c94c/1 (Internet Archive capture `20260114005922`)

## Method

- Lines: `<br>`, `<p>`, `<div>` and headings end a line; other markup dropped; entities decoded; NBSP and zero-width
  marks become spaces; runs of spaces become one; empty lines dropped. Nothing else is normalised.
- The original text is `div#divLawText`: the issuing instrument(s) before the law title (`preamble.md`), part/chapter
  headings (`structure.md`), and one block per article. Article headings in ordinal words or digits are read into
  numbers ("الحادية والثلاثون بعد المائة مكرر" -> 131-bis).
- Each amendment note names its instrument (`(م/46) وتاريخ 5/6/1436`) and quotes the new words. Notes are grouped by
  instrument (one commit each) and classified by their wording into operations (add 7, append 1, bis 1, def-add 1, delete 30, insert 3, lead 1, move 2, multi 3, para 9, replace 56, subst 8). Within one instrument: rewrites of several articles first, then repeals, moves,
  additions, whole replacements, and partial changes. A note printed twice is applied once (`Also-printed:`). A note
  that cannot be applied exactly, or whose wording is not one the replay reads, is not applied (`Not-applied:`); a note
  that names no royal decree or order is not replayed (`Note-unread:`).
- Commencement of a law: its own clause ("يعمل به من تاريخ نشره" or "... بعد (N) يومًا من تاريخ نشره"), counted from
  the publication day the portal prints. Hijri to Gregorian: `hijridate` (Umm al-Qura).

## Decisions by hand, and AI

No model wrote legal text or ran at build time. The code was written by Claude Code with Claude Opus 5.5
(`claude-opus-5-5`), which also chose the laws (the most-used codes first: constitution, civil, procedure, companies,
labour) and wrote the English names in the table. Decisions by hand:
- reading the portal through Internet Archive captures;
- the decree day as the in-force day where the notes give none (labelled "not before" in `In-force-basis:`);
- a note naming several instruments is credited to the last one it names;
- definitions added to a definitions article are appended at the end of the list (the notes do not say where);
- the first copy of a note printed twice is used.
