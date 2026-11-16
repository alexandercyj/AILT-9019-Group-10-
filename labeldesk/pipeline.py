"""The pipeline: one record in, one of two outcomes out.

    request -> look up -> validate -> render -> [licence?] -> [model rewrite] -> check
                                                                                    |
                                                                          drafted | refused

Refusal is a designed outcome, not an error. The refusal reasons are:

    out_of_corpus         the catalogue number is not in the frozen corpus
    out_of_scope          the request asks for value, authenticity or rights
    missing_required_field the record itself cannot supply a required field
    unknown_maker         the request asks who made the object, and the cited
                          fields do not name a maker

The model step is optional and cannot loosen the guardrail: a rewrite is only
substituted for the offline draft after it has passed the same four checks. When
it is discarded, the reason is recorded in the result's `llm` block and the
offline draft is printed — the pre-agreed fallback.

Before the model step there is one more question, asked of `sources.py`: does the
corpus's source permit its records to be sent to a model at all? A corpus that is
not in `data/sources.json`, or whose source says `ai_input: false`, never reaches
the network. The offline path is unaffected, so a refusal here costs a draft
nothing — it costs the *request* its rewrite, which is the honest outcome.
"""

from __future__ import annotations

import re

from .corpus import Corpus
from .grounding import run_checks
from .llm import LLMConfig, config_from_env, policy_block, resolve_mode, rewrite
from .render import render_label
from .sources import ai_input_allowed, provenance
from .validate import describe_missing, missing_fields

OUT_OF_SCOPE_TERMS = (
    "value",
    "worth",
    "price",
    "cost",
    "apprais",
    "authentic",
    "forgery",
    "fake",
    "insur",
    "rights",
    "copyright",
    "sell",
    "sale",
    "auction",
    "how much",
)

# The proposal's unknown-maker case: a request to name an artist is refused.
# The five cited fields have no maker, so the label must not invent one.
ATTRIBUTION_RE = re.compile(
    r"\b(?:who made|who painted|who created|name the artist|the artist|the maker|attribution)\b",
    re.IGNORECASE,
)

REASON_TEXT = {
    "out_of_corpus": (
        "Catalogue number {catalogue_number} is not in the frozen corpus. "
        "No label was drafted: the system does not describe a similar object from "
        "memory. Use --list to see the {count} catalogue numbers it can answer for."
    ),
    "out_of_scope": (
        "This request is outside the tool's scope ({term}). Label Desk drafts "
        "labels from a catalogue record; it does not value, authenticate, insure "
        "or clear rights for any object, and it has no data to do so."
    ),
    "missing_required_field": (
        "Record {catalogue_number} has no {missing}. No label was drafted: a blank "
        "field is not filled from outside the record. Supply the missing catalogue "
        "information and run again."
    ),
    "unknown_maker": (
        "Record {catalogue_number} does not name a maker in the cited catalogue "
        "fields. No artist was named: an unknown maker is not filled from outside "
        "the record."
    ),
}


def asks_for_attribution(question: str | None) -> bool:
    """True when the request asks the tool to name a maker or artist."""
    if not question:
        return False
    return ATTRIBUTION_RE.search(question) is not None


def is_out_of_scope(question: str | None) -> str | None:
    """Return the term that puts a request out of scope, or None."""
    if not question:
        return None
    text = question.casefold()
    for term in OUT_OF_SCOPE_TERMS:
        if term in text:
            return term
    return None


def _refusal(catalogue_number: str, reason: str, reason_text: str, **extra) -> dict:
    payload = {
        "status": "refused",
        "catalogue_number": catalogue_number,
        "reason": reason,
        "reason_text": reason_text,
        "missing_fields": [],
        "label": None,
        "claims": [],
        "citations": [],
        "padding": [],
        "notice": "",
        "word_count": 0,
        "shortened_medium": False,
        "checks": None,
        "label_source": "none",
        "llm": None,
        "record": None,
        "provenance": None,
    }
    payload.update(extra)
    return payload


def draft(
    corpus: Corpus,
    catalogue_number: str,
    question: str | None = None,
    *,
    llm: bool | str | None = None,
    config: LLMConfig | None = None,
    transcripts: dict | None = None,
) -> dict:
    """Run the core path for one catalogue number.

    `llm` is off by default. Pass `True` (or "auto") to use the model when a key
    is available and the recorded transcript when it is not, "live" to insist on a
    call, or "replay" to force the transcript. Refusals never reach the model.
    """
    catalogue_number = str(catalogue_number).strip()

    # Where the records came from, and what may be done with them. Computed before
    # anything else so a refusal carries the same provenance a draft does.
    allowed, _source, _policy = ai_input_allowed(corpus)
    prov = provenance(corpus)

    term = is_out_of_scope(question)
    if term:
        return _refusal(
            catalogue_number,
            "out_of_scope",
            REASON_TEXT["out_of_scope"].format(term=term),
            question=question,
            provenance=prov,
        )

    record = corpus.get(catalogue_number)
    if record is None:
        return _refusal(
            catalogue_number,
            "out_of_corpus",
            REASON_TEXT["out_of_corpus"].format(
                catalogue_number=catalogue_number, count=len(corpus)
            ),
            provenance=prov,
        )

    if asks_for_attribution(question):
        return _refusal(
            catalogue_number,
            "unknown_maker",
            REASON_TEXT["unknown_maker"].format(
                catalogue_number=record["catalogue_number"]
            ),
            question=question,
            record=record,
            provenance=prov,
        )

    missing = missing_fields(record)
    if missing:
        return _refusal(
            catalogue_number,
            "missing_required_field",
            REASON_TEXT["missing_required_field"].format(
                catalogue_number=record["catalogue_number"], missing=describe_missing(missing)
            ),
            missing_fields=missing,
            record=record,
            provenance=prov,
        )

    rendered = render_label(record)
    offline_checks = run_checks(rendered, record)

    llm_config = config or config_from_env()
    mode = resolve_mode(llm, llm_config)
    if mode != "off" and not allowed:
        # The register is consulted *before* the request, not reported after it.
        llm_block = policy_block(mode, llm_config, prov)
    else:
        llm_block = rewrite(
            record,
            rendered,
            mode=mode,
            config=llm_config,
            transcripts=transcripts,
            corpus=corpus.meta.get("name"),
        )

    if llm_block["applied"]:
        candidate = llm_block["candidate"]
        payload = {
            "label": candidate["label"],
            "claims": candidate["claims"],
            "citations": candidate["citations"],
            "padding": candidate["padding"],
            "notice": rendered["notice"],
            "word_count": candidate["word_count"],
            "shortened_medium": candidate["shortened_medium"],
        }
        checks = candidate["checks"]
        label_source = "llm_rewrite"
    else:
        payload = rendered
        checks = offline_checks
        label_source = "offline_template"

    return {
        "status": "drafted",
        "catalogue_number": record["catalogue_number"],
        "reason": None,
        "reason_text": "",
        "missing_fields": [],
        **payload,
        "checks": checks,
        "label_source": label_source,
        "llm": _public_llm_block(llm_block),
        "record": record,
        "provenance": prov,
    }


def _public_llm_block(block: dict) -> dict:
    """Drop the candidate prose: the label already carries it, and `--json` is large."""
    public = {key: value for key, value in block.items() if key != "candidate"}
    if block.get("candidate"):
        public["candidate_word_count"] = block["candidate"].get("word_count")
    return public
