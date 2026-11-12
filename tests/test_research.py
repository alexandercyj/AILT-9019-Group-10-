"""Web research uses retrieved pages, never model-supplied citation URLs alone."""

from __future__ import annotations

import json

from labeldesk.research import ResearchConfig, extract_research_trace, parse_article, prompt_text, research

URL = "https://www.metmuseum.org/art/collection/search/436535"
SECOND_URL = "https://www.vangoghmuseum.nl/en/collection/s0160V1962"
SEARCH_ONLY_URL = "https://invented.example/fact"
RECORD = {
    "title": "Self-Portrait with a Straw Hat",
    "catalogue_number": "64.165",
    "object_date": "1887",
    "medium": "Oil on canvas",
    "place_or_culture": "Netherlands",
    "source_url": URL,
}


def response_payload(citations=None) -> dict:
    article = {
        "title": RECORD["title"],
        "lead": {"text": "This is a self-portrait by Vincent van Gogh.", "citations": citations or [URL]},
        "sections": [{
            "heading": "Background",
            "paragraphs": [{"text": "The museum records the work's medium and date.", "citations": [URL]}],
        }],
        "conclusion": {"text": "The catalogue establishes the basic facts, while external pages add artistic context.", "citations": [SECOND_URL]},
    }
    return {
        "output": [
            {
                "type": "web_search_call",
                "action": {
                    "query": "Van Gogh self portrait 64.165",
                    "sources": [{"url": SEARCH_ONLY_URL, "title": "Search result only"}],
                },
            },
            {
                "type": "web_extractor_call",
                "urls": [URL, SECOND_URL],
                "goal": "Read museum records",
                "output": "Evidence in pages",
                "status": "completed",
            },
            {"type": "message", "content": [{"type": "output_text", "text": json.dumps(article, ensure_ascii=False)}]},
        ]
    }


def config() -> ResearchConfig:
    return ResearchConfig(base_url="https://example.invalid/v1", api_key="test")


def test_research_returns_cited_article_and_readable_trace():
    result = research(RECORD["title"], RECORD, provider_name="The Met", config=config(), transport=lambda *_: response_payload())
    assert result["status"] == "ready"
    assert result["lead"]["citation_ids"] == [1]
    assert result["conclusion"]["citation_ids"] == [2]
    assert result["sources"][0]["url"] == URL
    assert [step["kind"] for step in result["steps"]] == ["identify", "search", "read", "synthesis"]
    assert "example.invalid" not in json.dumps(result)
    assert "test" not in json.dumps(result)


def test_research_prompt_requires_english_reader_output():
    prompt = prompt_text()
    assert "write an encyclopedia-style article in English" in prompt
    assert "All reader-facing text in the JSON must be English." in prompt
    assert prompt.isascii()


def test_search_result_alone_cannot_be_cited():
    result = research(
        RECORD["title"], RECORD, config=config(),
        transport=lambda *_: response_payload([SEARCH_ONLY_URL]),
    )
    assert result["status"] == "unavailable"
    assert result["reason"] == "invalid_response"
    assert "lead" not in result


def test_missing_key_never_calls_transport():
    called = False
    def transport(*_):
        nonlocal called
        called = True
        return response_payload()
    result = research("Van Gogh", config=ResearchConfig(base_url="https://example.invalid"), transport=transport)
    assert result["reason"] == "no_key"
    assert called is False


def test_transport_failure_has_a_user_safe_fallback():
    def failing(*_):
        raise TimeoutError("private host detail")
    result = research("Van Gogh", config=config(), transport=failing)
    assert result["reason"] == "call_failed"
    assert "private" not in result["message"]


def test_known_refused_websites_are_not_used_as_evidence():
    raw = json.dumps({
        "title": "x", "lead": {"text": "x", "citations": ["https://www.britishmuseum.org/object"]},
        "sections": [], "conclusion": {"text": "x", "citations": []},
    })
    payload = {"output": [
        {"type": "web_search_call", "action": {"query": "x", "sources": [{"url": "https://www.britishmuseum.org/object"}]}},
        {"type": "message", "content": [{"type": "output_text", "text": raw}]},
    ]}
    _text, _steps, sources = extract_research_trace(payload)
    assert sources == []


def test_parser_requires_evidence_for_every_paragraph():
    raw, _steps, sources = extract_research_trace(response_payload())
    payload = json.loads(raw)
    payload["lead"]["citations"] = []
    try:
        parse_article(json.dumps(payload), sources)
    except ValueError as error:
        assert str(error) == "paragraph_without_evidence"
    else:
        raise AssertionError("an uncited paragraph must not become an article")


def test_model_preamble_does_not_hide_an_otherwise_valid_json_article():
    payload = response_payload()
    message = payload["output"][-1]["content"][0]
    message["text"] = "I will check the sources first.\n" + message["text"]
    result = research(RECORD["title"], RECORD, config=config(), transport=lambda *_: payload)
    assert result["status"] == "ready"
    assert result["lead"]["text"] == "This is a self-portrait by Vincent van Gogh."


def test_read_step_uses_the_actual_extracted_page_url():
    _raw, steps, _sources = extract_research_trace(response_payload())
    read = next(step for step in steps if step["kind"] == "read")
    assert read["detail"] == URL


def test_page_dictionary_urls_remain_supported():
    payload = response_payload()
    payload["output"][1] = {
        "type": "web_extractor_call",
        "output": {"pages": [
            {"url": URL, "title": "Met record", "text": "object"},
            {"url": SECOND_URL, "title": "Van Gogh Museum", "text": "background"},
        ]},
    }
    _raw, steps, sources = extract_research_trace(payload)
    assert [source["url"] for source in sources] == [URL, SECOND_URL]
    assert steps[1]["detail"] == URL
