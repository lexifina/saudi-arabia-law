# Reproduce

Data last read 2026-11-03.

## Sources

Each law is the Arabic page of the Bureau of Experts portal, as archived by the Internet Archive on the day given:
- `basic-law-of-governance`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/16b97fcb-4833-4f66-8531-a9a700f161b6/1 (Internet Archive capture `20260114204621`)
- `law-m-76-1424`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/4943163b-a079-4beb-b544-a9a700f286b1/1 (Internet Archive capture `20260225112415`)
- `labour-law`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/08381293-6388-48e2-8ad2-a9a700f2aa94/1 (Internet Archive capture `20260128140901`)
- `arbitration-law`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/5535039e-13da-43f6-8f53-a9a700f26485/1 (Internet Archive capture `20260123203858`)
- `law-of-procedure-before-sharia-courts`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/f0eaae46-9f84-40ee-815e-a9a700f268b3/1 (Internet Archive capture `20260301031524`)
- `law-m-61-1435`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/9da91b16-62ba-41d8-b6f7-a9a700f21d07/1 (Internet Archive capture `20250806235634`)
- `food-law`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/9167ec51-a011-4a22-b6c3-a9a700f290f8/1 (Internet Archive capture `20251212211808`)
- `law-of-civil-society-associations-and-organizations`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/37e0768f-8e3c-493a-b951-a9a700f2bbb1/1 (Internet Archive capture `20251017141427`)
- `law-m-128-1440`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/24c563f9-7292-49c8-b0fb-aa9800b999f1/1 (Internet Archive capture `20251215151035`)
- `law-m-165-1441`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/63831ff6-63d9-4212-8b54-abf800e146bd/1 (Internet Archive capture `20251015123655`)
- `notarization-law`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/40754577-f250-47f6-8a5a-abf600af7d72/1 (Internet Archive capture `20251116122303`)
- `personal-status-law`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/4d72d829-947b-45d5-b9b5-ae5800d6bac2/1 (Internet Archive capture `20260215024832`)
- `law-of-evidence`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/2716057c-c097-4bad-8e1e-ae1400c678d5/1 (Internet Archive capture `20260209124327`)
- `law-m-106-1443`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/ae610645-e094-48ef-814e-aeb4009d244f/1 (Internet Archive capture `20250912165002`)
- `companies-law`: https://laws.boe.gov.sa/boelaws/Laws/LawDetails/a8376aea-1bc3-49d4-9027-aed900b555af/1 (Internet Archive capture `20260218115042`)
- `civil-transactions-law`: https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/655fdb42-8c96-422b-b8c4-b04f0095c94c/1 (Internet Archive capture `20260114005922`)

## Method

- Lines: `<br>`, `<p>`, `<div>` and headings end a line; other markup dropped; entities decoded; NBSP and zero-width
  marks become spaces; runs of spaces become one; empty lines dropped. Nothing else is normalised.
- The original text is `div#divLawText`: the issuing instrument(s) before the law title (`preamble.md`), part/chapter
  headings (`structure.md`), and one block per article. Article headings in ordinal words or digits are read into
  numbers ("الحادية والثلاثون بعد المائة مكرر" -> 131-bis).
- Each amendment note names its instrument (`(م/46) وتاريخ 5/6/1436`) and quotes the new words. Notes are grouped by
  instrument (one commit each) and classified by their wording into operations (add 8, append 1, bis 1, def-add 1, delete 47, insert 3, lead 1, move 2, multi 3, para 11, replace 64, subst 8). Within one instrument: rewrites of several articles first, then repeals, moves,
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
