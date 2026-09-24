# Data ingestion — how the dataset was actually built

This document exists so the corpus is inspectable rather than a black box. Every
claim the recommender makes traces back to a row written by one of these steps,
and every step writes to the `scrape_log` table (exposed at `GET /api/logs`).

---

## Source 1 — BIS "Know Your Standards" catalogue

**Endpoint (reverse-engineered):**

```
POST https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/knowyourstandards/
     Indian_standards/searchIS?seachby=<base64>&txt_search=<base64>
body: DataTables server-side params (draw, start, length, columns[i][...])
resp: {"iTotalRecords": N, "aaData": [ {...} ]}      # legacy DataTables keys
```

### What made this non-obvious

1. The page renders through DataTables in `serverSide` mode, so a plain HTTP GET
   of the HTML returns an empty table shell. The data only arrives via XHR.
2. **The query parameters are base64-encoded.** Sending `seachby=keywords` in
   plain text returns HTTP 500; sending `seachby=a2V5d29yZHM=` works. This is
   what made the endpoint initially look unusable — the first probes returned
   bare `false` (empty criteria) or a 500 (plaintext criteria).
3. A session cookie (`BISID`) must exist first, obtained by fetching the
   `isdetails/` page once.

The contract was recovered by driving the real page in Playwright and capturing
the outgoing XHR (`scripts/capture_bis_xhr.py`). Once the shape was known, the
scraper dropped the browser entirely and uses plain HTTP, which is far faster.
**Playwright is a development-time tool here, not a runtime dependency of the
scrape.**

### Enumerating the catalogue

The API has no "list everything" mode, so coverage depends entirely on the seed
strategy — and the obvious one is wrong.

**Why single-letter keyword seeds fail.** `seachby=keywords` matches *word
prefixes*. Seeding with `e` returns 24,208 of ~24.2k rows and looks complete,
but it silently misses any standard with no `e`-initial word in its title. That
is how **IS 8623 "Low-voltage switchgear and controlgear assemblies"** — an ETD
standard the sample tender actually cites — went missing from an early run.
A near-total record count is not the same as total coverage.

**What is used instead.** `seachby=isnumber` matches *substrings* of the IS
number, and every IS number contains at least one digit, so the union of seeds
`0`–`9` provably covers the entire catalogue:

| seed | records | seed | records |
|------|---------|------|---------|
| `0`  | 19,245  | `5`  | 16,129  |
| `1`  | 27,301  | `6`  | 16,815  |
| `2`  | 20,780  | `7`  | 15,766  |
| `3`  | 17,251  | `8`  | 15,480  |
| `4`  | 16,416  | `9`  | 15,592  |

Rows are de-duplicated by IS number as they stream in. Paging at `length=1000`,
this is ~200 requests — slower than the letter seeds, but complete rather than
approximately complete.

### Parsing `is_no`

BIS returns an HTML blob with up to three `<br>`-separated segments:

```
"IS 1554 (Part 1):1988<br>IEC 60502<br> (Active)"
 └ number/part/year        └ ISO equivalent  └ status note
```

Measured parse coverage: **99.3%** of catalogue rows. The ~0.7% rejected are
corrupt at source — BIS itself emits entries with the number missing, e.g.
`IS/IEC -1-310:2005` and `IS  (Part 1/Sec 1):1975`. These are **rejected and
logged, never guessed at**, because inventing an identity would violate the
project's core guarantee.

### A field BIS misnames

The API returns a column called `referirmatin_year`. It does **not** contain a
year — it holds the ISO equivalence degree (`Identical under single numbering`,
`Modified/Technically Equivalent`, `Indigenous`, `Not Equivalent`, …). It is
stored as `iso_equiv_degree`.

---

## Source 2 — Internet Archive full text

Public.Resource.Org mirrors BIS standards under identifiers shaped like:

```
gov.in.is.<number>[.<part>].<year>      e.g. gov.in.is.1554.1.1988
```

Each item exposes a pre-OCR'd `<name>_djvu.txt`, so full text is fetched
directly as plain text — **no PDF download and no OCR step**. Content is
CC0 / released under the Right to Information Act.

A fixed RTI disclosure header is prepended to every scan; it terminates at the
Nehru epigraph ("Step Out From the Old to the New") and is stripped before
storage, along with OCR noise lines.

### Identifier matching must be exact (a bug worth documenting)

Identifiers are `gov.in.is.<num>[.<part>[.<section>]].<year>`. Matching them by
prefix is unsafe: searching `gov.in.is.302.2.` also matches
`gov.in.is.302.2.21.2018`, which is Part 2 **Section 21** — a different document.

An earlier version did exactly that and attached Section 21's text to
Part 2/Sec 28, Sec 16, Sec 36 and 12 others: the right standard number over the
wrong document's content. 147 rows were affected (~18% of those fetched).

Matching is now anchored to the full number/part/section. A standard whose own
part/section was never mirrored stays `metadata_only` instead of borrowing a
sibling's text. `scripts/repair_fulltext_assignment.py` detaches any row that
fails this check.

### Record the search, not just the result

A standard with no mirror leaves no trace unless one is written deliberately. An
early version recorded only successes, so every subsequent run re-queried the
thousands of standards that simply do not exist on archive.org — the candidate
list stayed huge and the hit rate collapsed to near zero after the first few
hundred.

`archive_checked` now records that archive.org *was searched*, whether or not
anything was found. Transport errors deliberately do **not** set it: a network
failure is not evidence of absence, so those are retried later. Backfilling this
flag from the audit log removed 1,275 dead-end retries from a single run.

### Fetch order matters

Candidates are fetched `ORDER BY is_active DESC, year ASC`, not by recency. The
Public.Resource.Org scanning effort predates current editions, so a 2026 entry is
very unlikely to be mirrored while a 1990 one usually is. Fetching newest-first
produced **0 hits in the first 125 attempts**; oldest-active-first produced 49 in
the first 225. Same total work, but the useful results land early, so a run that
has to be cut short still leaves the corpus in its most useful state.

### Edition mismatch — an important caveat

archive.org does not mirror every edition. The catalogue may list
`IS 732:2019` while only the 1989 scan exists. In that case the 1989 text *is*
ingested (it is the best available evidence) but `full_text_year` records which
edition the text actually came from, and any mismatch is surfaced as a currency
flag:

> Full text held is from the 1989 edition, but this entry is IS 732:2019.
> Cited passages come from 1989 and may not reflect the current edition.

Without this, the system would cite 1989 text as though it were the 2019
standard — precisely the kind of unverifiable claim this project must not make.

Measured across the ingested corpus after strict identifier matching: **84% of
full-text standards hold their exact catalogue edition**, and **16% hold an
earlier one** — occasionally much earlier (IS 2264:2026 is backed by 1963 text),
because the Public.Resource.Org scanning effort predates current editions. The
flag is load-bearing, not decorative.

An earlier measurement put the mismatch near 80%. That figure came from a sample
collected *before* identifier matching was anchored to number + part + section,
when a loose prefix match would accept any edition — and any sibling part — that
shared the base number. Tightening the match is what moved it.

---

## Withdrawn standards

Complete enumeration surfaced something the earlier partial scrape had hidden:
**2,190 of 5,054 ETD/LITD entries (43%) are marked withdrawn.** The old
letter-seed corpus contained almost none, which made the problem invisible.

Withdrawn standards are kept in the corpus deliberately — a tender may cite one,
and the user needs to be told that. But:

* retrieval **demotes** them, so an active standard of equal similarity always
  ranks higher (ordering only; the true similarity is preserved so confidence
  signals are not distorted);
* the critic applies a **near-veto** if one is recommended as primary, which in
  practice forces abstention with an explicit reason;
* they are labelled `WITHDRAWN` everywhere they appear in the UI.

## Trust levels in the corpus

| Flag | Meaning | Effect on output |
|---|---|---|
| `metadata_only = 0` | Full text ingested | Claims verifiable against real passages |
| `is_active = 0` | Withdrawn in the BIS catalogue | Demoted in retrieval; near-veto if recommended |
| `metadata_only = 1` | Catalogue metadata only | Retrievable, but confidence is reduced and the limitation is stated |
| `full_text_year != year` | Text is from another edition | Currency flag raised |
| edge `confidence = confirmed` | Read from the source standard's own text, with the sentence as evidence | Shown solid in the graph |
| edge `confidence = inferred` | Heuristic from shared committee + complementary aspect | Shown dashed, labelled unverified |

---

## Reproducing the build

```bash
python -m backend.ingestion.scrape_catalogue --departments ETD,LITD   # catalogue
python scripts/migrate_full_text_year.py                             # schema top-up
python -m backend.ingestion.fetch_fulltext --workers 8               # archive text
python -m backend.kb.build_kb                                        # chunk + embed
python -m backend.kb.build_graph                                     # dependency graph
```

Each run writes a JSON summary to `data/logs/<run_id>.json` and rows to
`scrape_log`. Rate limits are respected throughout (`BIS_DELAY_SEC`,
`ARCHIVE_DELAY` in `backend/config.py`).
