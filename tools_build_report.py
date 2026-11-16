#!/usr/bin/env python3
"""Build the completed AILT9019 final report from the course template."""
import copy
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph

SRC = "AILT9019_Final_Report_Template.docx"
OUT = "AILT9019_Final_Report_Group10.docx"

doc = Document(SRC)
styles = {s.name for s in doc.styles}
BULLET = "List Bullet" if "List Bullet" in styles else None
TABLE_GRID = "Table Grid" if "Table Grid" in styles else None

# ---------- 1. delete the "How to use this file" block and all blue e.g. examples ----------
to_delete = []
in_howto = False
for p in doc.paragraphs:
    t = p.text.strip()
    if t == "How to use this file":
        in_howto = True
    if in_howto and t.startswith("Team ID:"):
        in_howto = False
        continue  # keep the identification line (we fill it below)
    if in_howto:
        to_delete.append(p)
    elif t.startswith("e.g."):
        to_delete.append(p)

for p in to_delete:
    p._element.getparent().remove(p._element)


def find(prefix):
    for p in doc.paragraphs:
        if p.text.strip().startswith(prefix):
            return p
    raise KeyError(prefix)


def set_text(p, text):
    for r in list(p.runs):
        r._element.getparent().remove(r._element)
    p.add_run(text)


def insert_after(anchor, text, bullet=False):
    new_p = OxmlElement("w:p")
    anchor._p.addnext(new_p)
    np = Paragraph(new_p, anchor._parent)
    if bullet and BULLET:
        np.style = doc.styles[BULLET]
    np.add_run(text)
    return np


def insert_block(anchor, items):
    """items: list of (text, is_bullet) inserted in order after anchor."""
    cur = anchor
    for text, b in items:
        cur = insert_after(cur, text, bullet=b)
    return cur


def insert_table_after(anchor, rows):
    tbl = doc.add_table(rows=len(rows), cols=len(rows[0]))
    if TABLE_GRID:
        tbl.style = doc.styles[TABLE_GRID]
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            tbl.cell(i, j).text = val
    anchor._p.addnext(tbl._tbl)
    return tbl


# ---------- 2. title and identification line ----------
set_text(find("Final Report Template"), "Final Report — Group 10 · Label Desk")
set_text(find("Team ID:"),
    "Team ID: G10 · Project: Label Desk: cited, plain-language exhibition labels from one "
    "open-access collection · Repository: https://github.com/alexandercyj/AILT-9019-Group-10- · "
    "Public webpage: [add URL before submission] · Presentation YouTube link: [add URL before "
    "submission] · Demo YouTube link: [add URL before submission]")

# ---------- 3. Section 1 · Background ----------
insert_block(find("Who is this for, what problem"), [
    ("Label Desk is for student and volunteer curators writing wall labels for small campus or "
     "community exhibitions. They have no museum training, no register to ask and no catalogue "
     "they are licensed to quote; their only source is a museum record written in curatorial "
     "shorthand. Writing one label by hand — record open, second source checked — takes "
     "20–30 minutes, and under that pressure beginners fill the gap from memory. An invented "
     "fact inside a fluent sentence reads exactly like a true one, which is why the safeguard "
     "has to be machine-checked rather than left to the writer.", False),
    ("It is not for museum registrars or art-market users, and it does not authenticate, "
     "appraise, price, insure or clear rights; such requests are refused. The must-have scope "
     "is unchanged from the proposal. Three things changed after the midterm: the corpus grew "
     "from one museum to three corpora across two museums once the source register admitted "
     "them; a source-permission register was added, and the two museums the brief asked for "
     "(British Museum, Palace Museum) were checked and refused rather than worked around; and "
     "the optional model layer, deferred at midterm with a pre-agreed drop date, was kept after "
     "a written Week-10 decision on acceptance-rate evidence. The browser view grew into a "
     "collection reader with cited web research; PDF export was dropped.", False),
])

# ---------- 4. Section 2 · Pipeline ----------
insert_block(find("Explain the actual input"), [
    ("Input: a catalogue number in a frozen, checksummed corpus (plus an optional corpus alias, "
     "or an --ask question). Processing: look up the record; validate the five required fields "
     "(title, object date, medium, place or culture, credit line); build a fact sheet in which "
     "every value keeps a pointer to the field it came from; render five fixed sentences "
     "deterministically, each emitted as a claim — a span of label text plus its source field "
     "plus the exact slice of that field it cites; run four checks on every claim (field "
     "existence, token-level value containment against a documented free-word list, citation "
     "resolution, readability of 60–80 words with sentences under 20). An optional --llm pass "
     "then asks a model at temperature 0, under a guardrail prompt stored as a hashed file, to "
     "reword the five sentences; the rewrite is accepted only if it returns the same "
     "claim-plus-field structure, keeps at least as much of each field as the offline draft, "
     "and passes the identical checks — otherwise it is discarded, the reason is logged, and "
     "the offline draft prints. Output: the label with one citation per claim and four PASS "
     "lines, or a refusal naming its specific reason (missing field, out of corpus, out of "
     "scope). A refusal never reaches the model.", False),
    ("We built the validator, fact sheet, renderer, grounding checks, source register, refusal "
     "paths, evaluation scripts, browser and standalone views, and the single-file agent skill "
     "contract. The model API supplies only rewording; the museum open APIs supplied the "
     "records, frozen once so a run needs no network.", False),
    ("Domain customisation — the claim-plus-source-field output contract. A label sentence is "
     "not checked as prose but as a structured claim, which is what makes grounding exact: a "
     "claim may restate a field including the museum's own hedges (ca., probably, (?), or) but "
     "may not sharpen, narrow, date or relocate it — \u201cprobably Iran\u201d may not become \u201cmade in "
     "Iran\u201d. Implementation evidence: labeldesk/render.py and labeldesk/grounding.py, the "
     "twelve hand-labelled probes in eval/probes.json, and tests/test_grounding.py, which break "
     "sentences on purpose and require the check to catch them.", False),
    ("Two further customisations: corpus-level field maps (Egyptian Art records place in "
     "country rather than culture, declared inside the corpus file) keep the pipeline "
     "museum-agnostic — adding a museum is a data change, not a code change; and a fifth rule, "
     "drops_field_content, exists only for the model, catching a rewrite that cites a narrower "
     "slice of a field than the draft did (a real discard on record 1970.103a–e, committed in "
     "the model-on golden report).", False),
])

# ---------- 5. Section 3 · Evaluation ----------
insert_block(find("State a task-aligned evaluation question"), [
    ("Question: does every printed claim restate the field it cites — required at 100%, a "
     "single invented fact fails the run — does every citation resolve, and does the system "
     "refuse when the record cannot support a label? Data: a golden set of 17 cases (13 records "
     "expected to draft, 2 expected to refuse for a missing field, plus 2 request cases: an "
     "out-of-corpus number and an out-of-scope question), each with hand-written expectations, "
     "and 12 single-sentence boundary probes for the grounding rule. Method: one evaluation "
     "script (eval/evaluate.py) scores every case on five gates, run twice — model off and "
     "model on (recorded transcripts, temperature 0) — plus a cross-corpus run over all 40 "
     "records with no per-record expectations.", False),
])
tbl_anchor = find("Question: does every printed claim")
insert_table_after(tbl_anchor, [
    ["Gate", "Model off", "Model on", "Required"],
    ["Golden cases passed", "17/17", "17/17", "all"],
    ["Claim precision", "100%", "100%", "100%"],
    ["Citation resolution", "100%", "100%", "100%"],
    ["Readability pass rate", "100%", "100%", "100%"],
    ["Restatements matched", "72/72", "72/72", "all"],
    ["Probe agreement (false accepts / spurious rejections)", "100% (0 / 0)", "100% (0 / 0)", "100%"],
    ["Rewrites accepted", "—", "11/13 (85%)", "no-regression only"],
])
# content after the table, inserted before the Section 4 heading
h4 = find("4. Reproducibility")
def insert_before(paragraph, text):
    paragraph.insert_paragraph_before(text)

insert_before(h4, "Boundary and refusal cases behaved as expected: record 62.98.1 (no object "
                  "date) was refused with the reason named — \u201cRecord 62.98.1 has no object date. "
                  "No label was drafted: a blank field is not filled from outside the record\u201d; "
                  "99.99.99 was refused as out_of_corpus rather than describing a similar object; "
                  "\u201cwhat is it worth?\u201d was refused as out_of_scope. Evidence: the committed, "
                  "reproducible reports eval/reports/golden_report.md, golden_report_llm.md and "
                  "cross_corpus.md.")
insert_before(h4, "Across all 40 records in the three corpora: 0 check failures in either mode, "
                  "35/37 rewrites accepted, 2 discarded (drops_field_content). The pytest suite "
                  "passes 224 tests, including 43 that break the model layer on purpose — prose "
                  "answers, stale prompts, dropped coverage, and a refusal that must never reach "
                  "the model.")

# ---------- 6. Section 4 · Reproducibility ----------
insert_block(find("Briefly explain how another person"), [
    ("The README takes a classmate from a fresh clone to a correct label in one sitting: "
     "git clone; python3 -m pip install -r requirements.txt (pytest plus the optional model "
     "SDK); then one command, python3 -m labeldesk 14.40.377, which prints a 65-word label, "
     "five claims, five citations and four passing checks. No environment variables and no API "
     "key are needed for the core path. To verify: python3 -m pytest -q reports 224 passed; "
     "python3 eval/evaluate.py and python3 eval/evaluate.py --llm --replay reproduce both golden "
     "reports; python3 tools/fetch_corpus.py --check rebuilds all three corpora byte-identically. "
     "Without a key, --llm replays the 37 recorded transcripts and says so on its output line; "
     "with a key in .env it makes one live call at temperature 0.", False),
    ("Observed failure and response: on record 1970.103a–e the model rewrite kept the first two "
     "parts of a four-part medium description and cited only what it kept. Every printed word "
     "was true and the citation resolved — but the label had silently lost the ware. Cause: the "
     "four checks verify addition and resolution, not subtraction. Response: the "
     "drops_field_content coverage rule was added as a fifth gate; such rewrites are now "
     "discarded with the reason logged and the offline draft printed (2 discards in the golden "
     "run, 2 across the 37 cross-corpus rewrites). A second observed failure: the reasoning "
     "model spent its 900-token budget on a hidden reasoning trace and returned an empty "
     "string; the response was enable_thinking set to false, after which one call costs six "
     "completion tokens.", False),
    ("Limitations, stated with evidence: the 60–80-word band is met partly with carrier-only "
     "framing sentences (flagged as padding in the output; they add no facts but are not "
     "exhibition prose); the check is deliberately conservative and can reject a sentence a "
     "curator would accept — those rejections are counted in the evaluation rather than tuned "
     "away; five fields with one claim each cap prose quality by construction; the three "
     "admitted corpora are a selection effect, because a museum that refuses automated access "
     "also tends not to publish usable records; the 40-record frozen corpus is a regression "
     "baseline, not a collection; and citation resolution plus the research layer's retrieved-"
     "URL rule verify traceability, not that a source supports the wording — that judgement "
     "stays with the curator review checklist (docs/REVIEW_CHECKLIST.md).", False),
])

# ---------- 7. Section 5 · Ethics & AI-use ----------
insert_block(find("State data sources, permissions"), [
    ("Data and permissions: every record comes from The Metropolitan Museum of Art Open Access "
     "or The Cleveland Museum of Art Open Access, both CC0-1.0; field values are copied "
     "verbatim, blanks are the museums' own, each corpus is frozen once with its sha256 recorded, "
     "and no personal data is processed. A source register (data/sources.json) records, per "
     "source, the robots.txt signal, the licence, and an ai-input verdict. The two museums the "
     "brief named — the British Museum and the Palace Museum — publish no open licence for "
     "collection records and were refused; the Art Institute of Chicago was deferred "
     "(unreachable). These refusals are recorded in docs/DATA_SOURCES.md and enforced in code: "
     "pipeline.draft() asks the register before any record can be sent to a model, so an "
     "unregistered or refused corpus exits 4 without a byte leaving the machine.", False),
    ("Risks and mitigations: (1) a fluent label invents a plausible fact — facts may come only "
     "from the frozen record, every claim is machine-checked, and a missing required field "
     "triggers refusal by default; (2) the model rewrite drifts from a correct offline draft — "
     "the rewrite is accepted only under the identical checks plus the coverage rule, the "
     "offline draft is always the fallback, and the model-off run is the canonical one; "
     "(3) a label flattens cultural context or misstates credit — hedges (probably, attributed "
     "to, ca., (?)) are carried verbatim, the credit line is reproduced rather than paraphrased, "
     "and every label ends \u201cdraft for curator review, not an official record\u201d. Remaining risk: "
     "the evaluation measures that a label is grounded, not that it is good; taste and emphasis "
     "stay with the curator.", False),
])
set_text(find("Tools/models used:"),
    "Tools/models used: DeepSeek models deepseek-v4.1-flash (label rewrites) and "
    "deepseek-v4.1-flash-1017 (browser research) via an OpenAI-compatible Responses API, "
    "official openai Python SDK; pytest; certifi; museum open APIs for the one-time corpus fetch.")
set_text(find("Tasks supported:"),
    "Tasks supported: drafting and debugging of the model layer (llm.py), research layer "
    "(research.py) and browser server (server.py); writing unit and evaluation tests; polishing "
    "README and report prose.")
set_text(find("Representative prompts"),
    "Representative prompts: the label guardrail prompt prompts/rewrite.txt — forbids new facts "
    "and requires claim-plus-field JSON (its sha256 is stored in every transcript); the research "
    "prompt prompts/research.txt — requires every paragraph to cite a URL actually retrieved by "
    "the web-extraction tool.")
set_text(find("Material outputs retained:"),
    "Material outputs retained: 37 recorded model transcripts (data/llm_transcripts.json); "
    "AI-suggested code and text retained only after passing the test suite and human review.")
set_text(find("Verification performed:"),
    "Verification performed: every model rewrite machine-checked against five gates before "
    "acceptance; 224 pytest tests including 43 that break the model layer on purpose; all "
    "AI-assisted code and report text reviewed by Chen Yongjun; each other member checked this "
    "disclosure and their own contribution entry.")
set_text(find("Known limitations:"),
    "Known limitations: replayed transcripts are recorded answers, not live execution, and are "
    "labelled as such on every run; live runs are not reproducible and are kept only as "
    "evidence; research citations verify that a page was retrieved, not that it supports the "
    "wording.")
set_text(find("Team members responsible:"),
    "Team members responsible: Chen Yongjun — verification of all AI-assisted work and of the "
    "submitted report; CHENG Chi Man, GUNAWAN Alexander, SHEIKH Mohammad — checked this "
    "disclosure and their own entries.")

# ---------- 8. Section 6 · Contributions ----------
insert_block(find("For every section, list every member"), [
    ("Member key: A = Chen Yongjun; B = CHENG, Chi Man; C = GUNAWAN, Alexander; D = SHEIKH, "
     "Mohammad.", False),
    ("1. Background — A: wrote the user-needs analysis, the problem statement and the final "
     "scope-change statement. B: checked the problem statement against the approved proposal. "
     "C: none. D: none.", False),
    ("2. Pipeline and domain customisation — A: built the three frozen corpora and fetch/check "
     "tools; the validator, fact sheet, deterministic renderer and grounding checks; the model "
     "layer with the coverage rule; the source register; the browser view, standalone reader "
     "and agent skill contract. B: tested the three refusal paths and the browser-to-pipeline "
     "wiring. C: reviewed the domain rules (hedge handling, corpus field maps) against the "
     "museum records. D: none.", False),
    ("3. Evaluation and results — A: wrote the golden set, the boundary probes and the "
     "evaluation scripts; ran the model-off, model-on and cross-corpus evaluations. B: verified "
     "the committed reports against fresh runs. C: ran the pytest suite and recorded pass "
     "counts. D: none.", False),
    ("4. Reproducibility and limitations — A: wrote the README, the standalone builder and the "
     "corpus checksum checks; analysed the drops_field_content and empty-response failures. "
     "B: tested a fresh clone using only the README. C: checked the setup instructions and "
     "troubleshooting table. D: none.", False),
    ("5. Ethics & AI-use disclosure — A: compiled the source register and the licence/robots "
     "checks; recorded AI-supported tasks, prompts and retained outputs. B: checked data "
     "permissions and privacy statements. C: recorded the AI-use fields. D: checked the section "
     "for completeness.", False),
    ("6. Contribution statement — A: compiled the entries from the project work log. B: checked "
     "their entry. C: checked their entry. D: checked their entry.", False),
    ("7. References — A: listed the data sources, models and tools with versions. B: checked "
     "citations against the repository. C: none. D: none.", False),
])
insert_block(find("Also list each member’s completed webpage"), [
    ("Other project work — A: the Label Desk webpage (labeldesk.html standalone reader and the "
     "server.py browser view), the 58-second demo recording, and the presentation slides and "
     "speaking. B: checked the demo captions and the repository-link file. C: reviewed the "
     "presentation. D: checked the README links and the Moodle submission items. All four "
     "members spoke in the presentation. Statement reviewed: agreed by all members on "
     "13 November 2026; no unresolved disagreement. Evidence: git history, the committed "
     "eval/reports logs, and the Moodle group receipt.", False),
])

# ---------- 9. Section 7 · References ----------
insert_block(find("List cited data sources"), [
    ("The Metropolitan Museum of Art, Open Access collection (CC0-1.0), open-access dataset and "
     "API — github.com/metmuseum/openaccess. Records frozen 23 Oct and 1 Nov 2026.", False),
    ("Cleveland Museum of Art, Open Access API (CC0-1.0) — clevelandart.org/open-access/api. "
     "Records frozen 1 Nov 2026.", False),
    ("DeepSeek API documentation (OpenAI-compatible Responses API), models deepseek-v4.1-flash "
     "and deepseek-v4.1-flash-1017 — api-docs.deepseek.com.", False),
    ("OpenAI Python SDK — github.com/openai/openai-python (MIT).", False),
    ("pytest — pytest.org (MIT); certifi — github.com/certifi/python-certifi (MPL-2.0).", False),
    ("Source-permission register and per-source reasoning: repository files data/sources.json "
     "and docs/DATA_SOURCES.md.", False),
])

# ---------- 10. Appendix ----------
find("Appendix (optional)").paragraph_format.page_break_before = True
insert_block(find("Delete if unused"), [
    ("Appendix A — full evaluation evidence: eval/reports/ (golden_report.md, "
     "golden_report_llm.md, golden_report_llm_live.md, model_comparison.md, cross_corpus.md) "
     "and the 224-test suite under tests/.", False),
    ("Appendix B — contribution evidence: git history and the Moodle group receipt.", False),
])

doc.save(OUT)
print("saved", OUT)
print("paragraph count:", len(doc.paragraphs))
