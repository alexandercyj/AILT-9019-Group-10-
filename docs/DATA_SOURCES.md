# Where the records come from

`data/sources.json` is the machine-readable register; `python3 -m labeldesk --sources`
prints it as a table. This document is the reasoning behind it, source by source, because
a register records verdicts and a verdict without its reason is a preference.

## The question, asked of each source

Four questions, in this order. A source stops at the first one it fails.

1. **What does the host publish about automated access?** `robots.txt` is fetched and read,
   not assumed. The HTTP status, a sha256 prefix of the body, and the verdict drawn from it
   are recorded so `tools/check_sources.py` can tell later whether the answer changed.
2. **What are the terms for the records?** These are not the terms for the website. A
   museum can allow crawling and still hold copyright in its catalogue text.
3. **Can the record supply the five fields?** Title, date, medium, place or culture, credit
   line. An aggregator record that has no credit line cannot, however openly licensed it is.
4. **Is the network path actually open?** A documented API that answers with a bot challenge
   is not available, and working around the challenge is not the same as being allowed.

Only then: is it worth freezing ten records?

## Verdicts

| source | robots | licence | decision |
| --- | --- | --- | --- |
| met | no restriction published (API host 404) | CC0-1.0 | **admitted** |
| cleveland | allowed (only Amazonbot disallowed) | CC0-1.0 | **admitted** |
| british-museum | restricted: `ai-train=no`, training crawlers disallowed | none published | **refused** |
| palace-museum | not published (404, meta refresh) | none published | **refused** |
| artic | unreachable (Cloudflare challenge, 403) | CC0-1.0 | **deferred** |
| wikidata | allowed on the Action API; `/sparql` disallowed | CC0-1.0 | **reference only** |
| nga | not applicable (CC0 bulk dump on GitHub) | CC0-1.0 | **admitted, not frozen** |

---

## The Metropolitan Museum of Art — admitted

The collection API host publishes no `robots.txt` (HTTP 404), and the museum publishes its
Open Access records under CC0 with a documented API and no key. That is a grant on the
terms that matter: the records are offered for reuse.

The website host is a different matter — it answers non-browser clients with a bot
checkpoint. The tool therefore uses the documented API and never the website, which is why
the register's `access.method` says `api` and the endpoint is the object endpoint rather
than a search URL.

Two corpora come from here: 20 records across four departments, and 10 from Egyptian Art.

## The Cleveland Museum of Art — admitted

This one was added for the post-midterm data work, and it is the useful one, because it is
*not* the Met. Different museum, different API, different key names
(`creation_date` / `technique` / `accession_number`), and dates phrased by someone else.

The API host's `robots.txt` disallows one crawler (Amazonbot) and nothing else. Records are
filtered to `share_license_status == "CC0"` at fetch time, so nothing outside the open set
can reach the file. The museum's website separately sets `Crawl-delay: 10` and
`Disallow: /api` on its own host; the tool uses neither, and keeps a 0.5 s gap between API
calls anyway.

Why it matters: the hedge rule had only ever been tested on phrasings the team wrote. This
corpus supplies `c. 1050`, `1100s`, `400–700`, `1800s, before 1896` and `c. 1160–1170` —
none of them our wording. All ten records draft with the four checks passing, and all ten
model rewrites are accepted on replay. See `eval/reports/cross_corpus.md`.

## The British Museum — refused

This was asked for by name in the post-midterm note, and it was refused. The evidence:

- `robots.txt` returns 200 and allows `/` for `*`, but publishes
  `Content-Signal: search=yes, ai-train=no, use=reference` and disallows a long list of
  training crawlers. Crawling for reference is permitted; AI training is not. `ai-input` is
  neither granted nor restricted, so the conservative reading applies.
- No open licence is published for collection records. The site's terms are terms of use,
  not a grant of reuse.
- The site answers non-browser clients with a Cloudflare challenge (HTTP 403).

Getting past that challenge would be evasion. The tool does not attempt it, and the refusal
is recorded as a result rather than a gap — the same posture the pipeline takes on a missing
field.

Records from here can still enter the project through `tools/import_records.py`, supplied
by a person who has legitimate access, with the licence they assert and the basis on which
they hold the records written into the register alongside them.

## The Palace Museum (故宫博物院) — refused

Also asked for by name, also refused, for a blunter reason: there is nothing to read.

- `robots.txt` returns a 70-byte meta refresh to `/Home.html` rather than a robots file.
- Collection paths return 404 with the same redirect.
- No open data licence, no API, no documented bulk access.

A missing `robots.txt` is not a grant. Where nothing is published, there is no basis on
which to harvest records, so none were. The same import route applies.

## The Art Institute of Chicago — deferred

The proposal names this museum as the fallback dataset, and it stays named as the fallback.
The licence and the API are right (CC0, documented, no key); the network path is not. Every
request from this network returns a Cloudflare managed challenge, with a browser user-agent
and without one, so no verdict on `robots.txt` can be reached at all.

Nothing was attempted past the challenge. `tools/check_sources.py` will report it as
reachable-and-drifting if the situation ever changes; the register records the status rather
than a body hash, because a challenge page is generated per request and hashing it would
report drift on every run without anything having changed.

## Wikidata — reference only

Openly licensed (CC0), reachable, and the Action API is allowed. It is rejected as a
*record source* for one reason: an aggregator record has an inventory number, a title and a
material, but no credit line. The five-field contract cannot be satisfied, and filling that
field from the label's own wording would be exactly the failure this tool exists to prevent.

It is also worth recording what the register caught: `query.wikidata.org/robots.txt`
disallows `/sparql` and `/bigdata` outright, so no SPARQL query appears anywhere in this
repository. The convenient path was the disallowed one.

## The National Gallery of Art, Washington — admitted, not frozen

CC0 bulk data on GitHub, no key, no crawling involved. Admitted in principle and not frozen,
because the dump is far larger than a ten-record corpus warrants and the repository keeps its
data small on purpose.

---

## Keeping the register honest

```bash
python3 tools/check_sources.py            # re-fetch every robots.txt, report drift
python3 tools/check_sources.py --json     # the same, machine-readable
```

The check reports three kinds of drift: `status_changed`, `body_changed`, and
`agent_blocked` — the last one because a file can change in one line that applies to us
while the rest is untouched, so the check parses the file rather than only hashing it. It
also flags `ai_input_contradicted` if a host starts publishing `ai-train=no` while the
register still permits sending its records to a model.

A drift is not automatically a violation. It means: re-read the file, decide, then update
the register so the next run compares against the new truth. The register is a claim with a
date on it, and the date is `robots.checked`.

## What the register enforces, not just records

`pipeline.draft()` calls `sources.ai_input_allowed(corpus)` before the model step. A corpus
whose source forbids `ai_input`, or which is not registered at all, never reaches the
network:

```text
$ python3 -m labeldesk 1970.36 --corpus /tmp/unregistered.json --llm --replay
  Model   deepseek-v4.1-flash · replay · refused before sending: source_policy
          source unregistered · licence not on file · ai_input not granted
          offline draft printed instead; no record left this machine
$ echo $?
4
```

Note that the licence reads *not on file* rather than repeating what the corpus file says
about itself. A corpus's own claim is reported separately, as `license_claimed`, because it
is a claim and not a licence.

The offline path is unaffected — a refusal here costs a draft nothing. It costs the
*request* its rewrite, which is the honest outcome, and `4` says so rather than pretending
the draft was what was asked for.
