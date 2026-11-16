"""The optional model layer, behind the same guardrail as the offline path.

    fact sheet + offline draft -> model -> claims
                                        |
                              same four checks
                                        |
                            accepted | discarded -> offline draft

The model is allowed to improve the prose and is not allowed to change the facts.
Nothing it returns reaches the label directly: a rewrite is parsed into the same
claim-plus-field structure the renderer emits, and then handed to
`grounding.run_checks` — the identical check the offline draft faces. A rewrite
that fails one check, loses a field, cites a field it was not given, or breaks the
word band is discarded, its reason is recorded, and the offline draft is printed.
That is the no-regression rule from the proposal: turning the model on can cost
prose quality, never a fact or a citation.

Three modes, resolved by `resolve_mode`:

    live    one call, temperature 0, prompt read from prompts/rewrite.txt
    replay  the recorded response for this record, no network, no key
    off     no model at all — the offline draft is the whole system

Replay is keyed by catalogue number *and* the sha256 of the prompt, so editing the
prompt invalidates the transcript instead of silently replaying an answer to a
question that is no longer being asked. That case is reported as `transcript_stale`
and falls back to the offline draft.

The standard library alone is enough: the OpenAI SDK is used when it is installed
(the proposal's choice), and a plain HTTP POST to the same compatible-mode
endpoint is used when it is not. Both paths send the same body.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from .corpus import FIELD_LABELS, REQUIRED_FIELDS, ROOT
from .grounding import run_checks
from .net import ssl_context
from .render import assemble
from .text import FREE_WORDS, content_tokens, normalise, words

PROMPT_PATH = ROOT / "prompts" / "rewrite.txt"
TRANSCRIPT_PATH = ROOT / "data" / "llm_transcripts.json"
ENV_PATH = ROOT / ".env"

DEFAULT_BASE_URL = "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "deepseek-v4.1-flash"

MODES = ("off", "live", "replay")

# A claim sentence must be prose, not a fragment and not a run-on. The band is
# deliberately wide: the readability check on the whole label is the strict one,
# and a short sentence is legal there. This band only catches a fragment and a
# paragraph-length sentence.
CLAIM_WORD_BAND = (4, 30)


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LLMConfig:
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    api_key: str | None = None
    temperature: float = 0.0
    timeout: float = 90.0
    max_tokens: int = 4000
    retries: int = 1
    # deepseek-v4.1-flash reasons before it answers. For a rewrite that must be
    # reproducible and cheap, the reasoning trace is not wanted: with it on, a
    # 900-token budget was spent entirely on hidden reasoning and the answer came
    # back empty. Off, the same request costs six completion tokens.
    thinking: bool = False

    @property
    def has_key(self) -> bool:
        return bool(self.api_key)

    @property
    def key_fingerprint(self) -> str | None:
        return fingerprint(self.api_key)

    @property
    def extra_body(self) -> dict:
        """Provider switch sent with every call. Documented in README, not hidden."""
        return {"enable_thinking": self.thinking}

    def describe(self) -> dict:
        """Everything about the config that is safe to print or commit."""
        return {
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
            "thinking": self.thinking,
            "has_key": self.has_key,
            "key_fingerprint": self.key_fingerprint,
        }


def fingerprint(key: str | None) -> str | None:
    """Last four characters only — enough to tell two keys apart, not to leak one."""
    if not key:
        return None
    tail = key[-4:]
    return f"…{tail} ({hashlib.sha256(key.encode()).hexdigest()[:8]})"


def read_env_file(path: Path = ENV_PATH) -> dict[str, str]:
    """Minimal KEY=VALUE reader. No python-dotenv, no interpolation, no surprises."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        if key.strip():
            values[key.strip()] = value
    return values


def config_from_env(env: dict[str, str] | None = None) -> LLMConfig:
    """Environment first, then .env, then the built-in defaults."""
    file_values = read_env_file()
    source = {**file_values, **(env if env is not None else os.environ)}

    def pick(*names: str, default: str = "") -> str:
        for name in names:
            value = source.get(name)
            if value:
                return value
        return default

    return LLMConfig(
        base_url=pick("LABELDESK_BASE_URL", "OPENAI_BASE_URL", default=DEFAULT_BASE_URL),
        model=pick("LABELDESK_MODEL", "OPENAI_MODEL", default=DEFAULT_MODEL),
        api_key=pick("LABELDESK_API_KEY", "OPENAI_API_KEY") or None,
        thinking=pick("LABELDESK_THINKING", default="0").strip().lower()
        in ("1", "true", "yes", "on"),
    )


def resolve_mode(requested: bool | str | None, config: LLMConfig) -> str:
    """Turn a CLI flag into one of the three modes.

    `--llm` with a key is live; `--llm` without a key is replay, because the
    proposal promises the tool still runs — and still shows the model path — with
    no key at all. `--llm --replay` forces replay even when a key is present.
    """
    if requested in (None, False, "", "off"):
        return "off"
    if requested is True or requested == "auto":
        return "live" if config.has_key else "replay"
    if requested not in MODES:
        raise ValueError(f"unknown llm mode {requested!r}; expected one of {MODES}")
    return requested


# --------------------------------------------------------------------------- #
# prompt and request
# --------------------------------------------------------------------------- #


def prompt_text(path: Path = PROMPT_PATH) -> str:
    return path.read_text(encoding="utf-8")


def prompt_hash(text: str | None = None) -> str:
    return hashlib.sha256((text if text is not None else prompt_text()).encode("utf-8")).hexdigest()


def build_messages(record: dict, offline: dict, prompt: str | None = None) -> list[dict]:
    """System prompt from disk, then the fact sheet as data.

    The record values are passed as JSON, never interpolated into the prompt, so a
    field value cannot change the instruction the model is following. Rule 6 in the
    prompt says the same thing; this is the structural version of it.
    """
    facts = [
        {
            "source_field": field_name,
            "label": FIELD_LABELS[field_name],
            "value": str(record.get(field_name, "") or ""),
        }
        for field_name in REQUIRED_FIELDS
    ]
    draft = [
        {
            "source_field": claim["source_field"],
            "text": claim["text"],
            "value_span": claim["value_span"],
        }
        for claim in offline["claims"]
    ]
    payload = {
        "task": "rewrite_five_sentences",
        "fact_sheet": facts,
        "offline_draft": draft,
        "notice_that_follows": offline["notice"],
        "target_words": {
            "per_sentence": "8-16",
            "body_total": "40-68",
            "with_notice_and_framing": "60-80",
            "note": "the tool appends its own fact-free framing sentences if the body is short",
        },
        # The exact vocabulary the grounding check treats as free. Sent with the
        # request so the model is not guessing at it, and read from text.py so the
        # prompt cannot drift away from the check.
        "free_words": sorted(FREE_WORDS),
    }
    return [
        {"role": "system", "content": prompt if prompt is not None else prompt_text()},
        {
            "role": "user",
            "content": "Fact sheet and offline draft, as JSON:\n"
            + json.dumps(payload, ensure_ascii=False, indent=2),
        },
    ]


class RewriteRejected(Exception):
    """A rewrite that did not survive the guardrail."""

    def __init__(self, reason: str, detail: dict | None = None):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail or {}


def _post_with_sdk(config: LLMConfig, messages: list[dict]) -> tuple[str, dict]:
    from openai import OpenAI  # imported lazily: the core path never needs it

    client = OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=config.timeout,
        max_retries=config.retries,
    )
    response = client.chat.completions.create(
        model=config.model,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        response_format={"type": "json_object"},
        extra_body=config.extra_body,
    )
    usage = response.usage.model_dump() if response.usage else {}
    return response.choices[0].message.content or "", usage


def _post_with_urllib(config: LLMConfig, messages: list[dict]) -> tuple[str, dict]:
    import urllib.error
    import urllib.request

    body = json.dumps(
        {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "response_format": {"type": "json_object"},
            **config.extra_body,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        config.base_url.rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=config.timeout, context=ssl_context()) as response:
        payload = json.load(response)
    return payload["choices"][0]["message"].get("content") or "", payload.get("usage", {})


def call_model(config: LLMConfig, messages: list[dict]) -> tuple[str, dict]:
    """One call, one attempt policy, no silent second model."""
    try:
        return _post_with_sdk(config, messages)
    except ImportError:
        return _post_with_urllib(config, messages)


# --------------------------------------------------------------------------- #
# parsing and validation
# --------------------------------------------------------------------------- #


def _strip_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3]
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    return text.strip()


def parse_claims(raw: str) -> list[dict]:
    """Read the model's JSON. Anything but a claim list is a rejection, not a repair."""
    try:
        payload = json.loads(_strip_fence(raw))
    except json.JSONDecodeError as error:
        raise RewriteRejected("not_json", {"error": str(error), "raw_head": raw[:200]}) from None
    if not isinstance(payload, dict):
        raise RewriteRejected("not_an_object", {"type": type(payload).__name__})
    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        raise RewriteRejected("no_claims", {"keys": sorted(payload)[:8]})
    return claims


def validate_structure(claims: list[dict], record: dict) -> list[dict]:
    """Everything that can be judged without the grounding check."""
    problems: list[dict] = []

    if len(claims) != len(REQUIRED_FIELDS):
        problems.append({"reason": "claim_count", "got": len(claims), "want": len(REQUIRED_FIELDS)})

    seen: list[str] = []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            problems.append({"reason": "claim_not_object", "index": index})
            continue
        text = str(claim.get("text") or "").strip()
        field_name = str(claim.get("source_field") or "").strip()
        span = str(claim.get("value_span") or "").strip()

        if not text:
            problems.append({"reason": "empty_text", "index": index})
        if not span:
            problems.append({"reason": "empty_span", "index": index})
        if field_name not in REQUIRED_FIELDS:
            problems.append({"reason": "unknown_field", "index": index, "field": field_name})
            continue
        seen.append(field_name)

        count = words(text)
        if not CLAIM_WORD_BAND[0] <= count <= CLAIM_WORD_BAND[1]:
            problems.append(
                {"reason": "claim_word_band", "index": index, "words": count, "band": CLAIM_WORD_BAND}
            )

        value = str(record.get(field_name, "") or "")
        if span and normalise(span) not in normalise(value):
            problems.append(
                {"reason": "span_not_in_field", "index": index, "field": field_name, "span": span}
            )

    if len(set(seen)) != len(seen):
        problems.append({"reason": "duplicate_field", "fields": seen})
    missing = [field_name for field_name in REQUIRED_FIELDS if field_name not in seen]
    if missing:
        problems.append({"reason": "missing_field_claim", "fields": missing})
    return problems


def apply_claims(claims: list[dict], record: dict) -> dict:
    """Turn validated claims into the same result shape the renderer emits.

    Assembly is the renderer's own: if the rewrite comes back short, the same
    fact-free framing sentences are appended. The model is not asked to pad its
    sentences to reach a word count, because padding is what makes forced prose
    read like a form.
    """
    ordered = {claim["source_field"]: claim for claim in claims}
    normalised = []
    for index, field_name in enumerate(REQUIRED_FIELDS, start=1):
        claim = ordered[field_name]
        normalised.append(
            {
                "id": f"c{index}",
                "text": " ".join(str(claim["text"]).split()),
                "source_field": field_name,
                "value_span": str(claim["value_span"]).strip(),
            }
        )
    label, padding = assemble(normalised)
    return {
        "label": label,
        "claims": normalised,
        "citations": [
            {
                "field": claim["source_field"],
                "value_span": claim["value_span"],
                "label": FIELD_LABELS[claim["source_field"]],
            }
            for claim in normalised
        ],
        "padding": padding,
        "word_count": words(label),
        "shortened_medium": any(
            claim["source_field"] == "medium"
            and claim["value_span"] != str(record.get("medium", "") or "").strip()
            for claim in normalised
        ),
    }


def validate_coverage(claims: list[dict], offline: dict) -> list[dict]:
    """A rewrite may reword a field; it may not keep less of it than the draft did.

    Without this rule a model can pass every grounding test by citing a narrower
    slice than the offline renderer chose — "Clay; moulded frame ... (Tokyo ware)"
    becomes "Clay", the citation still resolves, and the label quietly loses the
    one word that identifies the ware. Factual grounding cannot see that loss
    because nothing false was added. Coverage can.
    """
    problems: list[dict] = []
    reference = {claim["source_field"]: claim["value_span"] for claim in offline["claims"]}
    for claim in claims:
        field_name = claim.get("source_field")
        if field_name not in reference:
            continue
        want = set(content_tokens(str(reference[field_name])))
        got = set(content_tokens(str(claim.get("value_span") or "")))
        missing = sorted(want - got)
        if missing:
            problems.append(
                {
                    "reason": "drops_field_content",
                    "field": field_name,
                    "missing": missing,
                    "offline_span": reference[field_name],
                    "rewrite_span": claim.get("value_span"),
                }
            )
    return problems


def guard(claims: list[dict], record: dict, offline: dict) -> dict:
    """Structure, coverage, then the identical four checks the offline draft faces."""
    problems = validate_structure(claims, record) + validate_coverage(claims, offline)
    if problems:
        raise RewriteRejected(problems[0]["reason"], {"problems": problems})

    candidate = apply_claims(claims, record)
    checks = run_checks(candidate, record)
    if not checks["passed"]:
        failures = [
            {"check": name, **failure}
            for name in ("field_existence", "value_containment", "citation_resolution", "readability")
            for failure in checks[name]["failures"]
        ]
        raise RewriteRejected(
            failures[0]["check"] if failures else "checks_failed",
            {"failures": failures, "checks": {k: checks[k]["passed"] for k in (
                "field_existence",
                "value_containment",
                "citation_resolution",
                "readability",
            )}},
        )
    candidate["checks"] = checks
    return candidate


# --------------------------------------------------------------------------- #
# transcripts
# --------------------------------------------------------------------------- #


def load_transcripts(path: Path = TRANSCRIPT_PATH) -> dict:
    if not path.exists():
        return {"meta": {}, "transcripts": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_transcripts(payload: dict, path: Path = TRANSCRIPT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def transcript_key(catalogue_number: str, corpus: str | None = None) -> str:
    """Where a response is stored. Scoped by corpus when the caller knows it.

    Catalogue numbers are unique inside a museum, not across museums. Two
    collections can both call something "1" or "1970.36", so a flat key would let
    one corpus replay another's answer — the exact substitution the rest of the
    project refuses to make. The plain key is still accepted on read, because the
    first transcripts were recorded before there was a second museum.
    """
    return f"{corpus}::{catalogue_number}" if corpus else str(catalogue_number)


def _lookup(entries: dict, catalogue_number: str, corpus: str | None) -> tuple[str | None, dict | None]:
    for key in (transcript_key(catalogue_number, corpus), str(catalogue_number)):
        if key and key in entries:
            return key, entries[key]
    return None, None


def transcript_for(
    catalogue_number: str, transcripts: dict | None = None, corpus: str | None = None
) -> dict | None:
    payload = transcripts if transcripts is not None else load_transcripts()
    _key, entry = _lookup(payload.get("transcripts") or {}, catalogue_number, corpus)
    return entry


# --------------------------------------------------------------------------- #
# the entry point
# --------------------------------------------------------------------------- #


def _empty_block(mode: str, config: LLMConfig, requested: bool = False) -> dict:
    # Offline and replay never send the record. Copying config.has_key into
    # those results made labeldesk.html differ between a machine that had a
    # key and a clean checkout. has_key is true only when this run is live.
    live = mode == "live"
    return {
        "requested": requested,
        "mode": mode,
        "applied": False,
        "label_source": "offline_template",
        "reason": None,
        "detail": {},
        "model": config.model if live else DEFAULT_MODEL,
        "base_url": config.base_url if live else DEFAULT_BASE_URL,
        "has_key": bool(config.has_key) if live else False,
        "prompt_sha256": None,
        "attempts": 0,
        "latency_ms": None,
        "usage": {},
        "transcript": None,
        "candidate": None,
    }


def policy_block(mode: str, config: LLMConfig, provenance_block: dict) -> dict:
    """The block returned when the source's terms forbid sending records to a model.

    This is not a rewrite failure — nothing was sent and nothing was tried. It is
    the licence being read before the request, which is the only order that makes
    the check worth having.
    """
    block = _empty_block(mode, config, requested=mode != "off")
    block["reason"] = "source_policy"
    block["detail"] = {
        "source": provenance_block.get("id"),
        "license": provenance_block.get("license"),
        "registered": provenance_block.get("registered"),
        "robots_verdict": provenance_block.get("robots_verdict"),
        "hint": (
            "This corpus's source does not permit ai_input, so the records were not "
            "sent. Offline drafting is unaffected. Register a source that grants it, "
            "or run without --llm."
        ),
    }
    return block


def rewrite(
    record: dict,
    offline: dict,
    *,
    mode: str = "off",
    config: LLMConfig | None = None,
    transcripts: dict | None = None,
    prompt: str | None = None,
    corpus: str | None = None,
) -> dict:
    """Try the model path for one record. Never raises; always returns a block.

    The returned dict always has `applied` and `label_source`, so the pipeline can
    decide without a try/except of its own.
    """
    config = config or config_from_env()
    block = _empty_block(mode, config, requested=mode != "off")
    if mode == "off":
        return block

    text = prompt if prompt is not None else prompt_text()
    digest = prompt_hash(text)
    block["prompt_sha256"] = digest
    messages = build_messages(record, offline, prompt=text)

    if mode == "replay":
        entries = (transcripts if transcripts is not None else load_transcripts()).get("transcripts") or {}
        key, entry = _lookup(entries, record["catalogue_number"], corpus)
        block["transcript"] = key
        if entry is None:
            block["reason"] = "no_transcript"
            return block
        if entry.get("prompt_sha256") != digest:
            block["reason"] = "transcript_stale"
            block["detail"] = {
                "recorded": entry.get("prompt_sha256"),
                "current": digest,
                "hint": "re-record with tools/record_transcripts.py",
            }
            return block
        block["usage"] = entry.get("usage", {})
        block["model"] = entry.get("model", config.model)
        raw = entry.get("response", "")
        block["attempts"] = 1
        return _finish(block, raw, record, offline, source="replay")

    if not config.has_key:
        block["reason"] = "no_key"
        return block

    started = time.monotonic()
    try:
        raw, usage = call_model(config, messages)
    except Exception as error:  # noqa: BLE001 - any transport failure is a fallback
        block["reason"] = "call_failed"
        block["detail"] = {"error": f"{type(error).__name__}: {error}"}
        block["latency_ms"] = round((time.monotonic() - started) * 1000)
        return block
    block["latency_ms"] = round((time.monotonic() - started) * 1000)
    block["usage"] = usage
    block["attempts"] = 1
    return _finish(block, raw, record, offline, source="live")


def _finish(block: dict, raw: str, record: dict, offline: dict, *, source: str) -> dict:
    try:
        claims = parse_claims(raw)
        candidate = guard(claims, record, offline)
    except RewriteRejected as rejection:
        block["reason"] = rejection.reason
        block["detail"] = rejection.detail
        block["candidate"] = {"raw_head": (raw or "")[:400], "source": source}
        return block
    block.update(
        {
            "applied": True,
            "label_source": "llm_rewrite",
            "reason": None,
            "detail": {},
            "candidate": candidate,
        }
    )
    return block


def record_one(
    record: dict, offline: dict, config: LLMConfig | None = None, corpus: str | None = None
) -> dict:
    """Make one live call and return the transcript entry for it. Used by the tool."""
    config = config or config_from_env()
    if not config.has_key:
        raise RuntimeError("no API key: set LABELDESK_API_KEY or put it in .env")
    text = prompt_text()
    messages = build_messages(record, offline, prompt=text)
    raw, usage = call_model(config, messages)
    return {
        "model": config.model,
        "base_url": config.base_url,
        "prompt_sha256": prompt_hash(text),
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "response": raw,
        "usage": usage,
        "record_title": record.get("title", ""),
        "corpus": corpus,
        "catalogue_number": record.get("catalogue_number", ""),
    }


__all__ = [
    "LLMConfig",
    "RewriteRejected",
    "MODES",
    "PROMPT_PATH",
    "TRANSCRIPT_PATH",
    "apply_claims",
    "build_messages",
    "call_model",
    "config_from_env",
    "fingerprint",
    "guard",
    "load_transcripts",
    "parse_claims",
    "policy_block",
    "prompt_hash",
    "prompt_text",
    "read_env_file",
    "record_one",
    "resolve_mode",
    "rewrite",
    "save_transcripts",
    "transcript_for",
    "transcript_key",
    "validate_coverage",
    "validate_structure",
]
