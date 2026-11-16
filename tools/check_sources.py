"""Re-fetch every robots.txt in the register and report whether it still says the same.

`data/sources.json` records a verdict, an HTTP status and a sha256 prefix of the
body for each host. A record like that is only worth having if something re-checks
it, otherwise it is a claim with a date on it. This is the something.

It reports three kinds of drift:

    status_changed   the file is now served, or no longer served, where it was not
    body_changed     the file is served and its bytes differ from the recorded prefix
    agent_blocked    the file now disallows the user-agent this project sends

The third is the one that matters. A robots file can be byte-identical and still
matter less than it did, and it can change in one line that applies to us while
the rest is untouched. So the check reads the file, not only its hash.

Usage:
    python3 tools/check_sources.py            # human-readable report
    python3 tools/check_sources.py --json     # machine-readable
    python3 tools/check_sources.py --only met,cleveland

Exit codes: 0 everything matches the register, 1 something drifted, 2 network
failure on a host the register says is reachable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from labeldesk.net import ssl_context  # noqa: E402
from labeldesk.sources import REGISTER_PATH, sources  # noqa: E402

# Must match tools/fetch_corpus.py: the register's verdict is about *this* client.
USER_AGENT = "LabelDesk-AILT9019/1.1 (course project; educational use)"
AGENT_TOKEN = "labeldesk"


def fetch(url: str) -> tuple[int, bytes]:
    """Return (status, body). A 4xx is a result, not an exception."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20, context=ssl_context()) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read() or b""
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ConnectionError(str(error)) from error


def parse_robots(text: str) -> dict:
    """The two things worth reading out of a robots file.

    Full RFC 9309 group matching is more than this needs. What the register has to
    answer is narrow: does this file name us, and does it publish a content signal?
    """
    groups: list[dict] = []
    current: dict | None = None
    signals: dict[str, str] = {}

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        if key == "user-agent":
            if current is None or current["rules"]:
                current = {"agents": [], "rules": []}
                groups.append(current)
            current["agents"].append(value.lower())
        elif key in {"allow", "disallow"}:
            if current is None:
                current = {"agents": ["*"], "rules": []}
                groups.append(current)
            current["rules"].append((key, value))
        elif key == "content-signal":
            for part in value.split(","):
                name, _, setting = part.partition("=")
                if name.strip():
                    signals[name.strip().lower()] = setting.strip().lower()

    blocked: list[str] = []
    for group in groups:
        applies = "*" in group["agents"] or any(AGENT_TOKEN in agent for agent in group["agents"])
        if not applies:
            continue
        for kind, path in group["rules"]:
            if kind == "disallow" and path == "/":
                blocked.append(f"{','.join(group['agents'])}: Disallow: /")

    return {
        "groups": len(groups),
        "content_signal": signals,
        "blanket_disallow": blocked,
        "names_us": any(AGENT_TOKEN in agent for group in groups for agent in group["agents"]),
    }


def check(source: dict) -> dict:
    robots = source["robots"]
    result = {
        "id": source["id"],
        "url": robots.get("url"),
        "registered_status": robots["http_status"],
        "registered_sha256_prefix": robots["body_sha256_prefix"],
        "registered_verdict": robots["verdict"],
        "drift": [],
        "status": None,
        "sha256_prefix": None,
        "reachable": True,
    }

    if not robots.get("url"):
        # No robots file applies: the data is a bulk file, not a crawled page.
        result["skipped"] = True
        return result

    try:
        status, body = fetch(robots["url"])
    except ConnectionError as error:
        result["reachable"] = False
        result["error"] = str(error)
        result["drift"].append("unreachable")
        return result

    result["status"] = status
    if body:
        result["sha256_prefix"] = hashlib.sha256(body).hexdigest()[:16]

    if status != robots["http_status"]:
        result["drift"].append("status_changed")

    # Only compare bytes when a prefix was recorded. A 404 error page has a body,
    # but it is the server's, not a policy, and it changes without meaning anything.
    if robots["body_sha256_prefix"] and result["sha256_prefix"] != robots["body_sha256_prefix"]:
        result["drift"].append("body_changed")

    if body:
        parsed = parse_robots(body.decode("utf-8", errors="replace"))
        result["content_signal"] = parsed["content_signal"]
        result["blanket_disallow"] = parsed["blanket_disallow"]
        result["names_us"] = parsed["names_us"]
        if parsed["blanket_disallow"] and robots["verdict"] in {"allowed", "no_restriction_published"}:
            result["drift"].append("agent_blocked")
        if parsed["content_signal"].get("ai-train") == "no" and source["policy"]["ai_input"]:
            result["drift"].append("ai_input_contradicted")

    return result


def render(rows: list[dict]) -> str:
    lines = []
    clean = 0
    for row in rows:
        if row.get("skipped"):
            lines.append(
                f"n/a  {row['id']:<16} no robots file applies · verdict {row['registered_verdict']}"
            )
            clean += 1
            continue
        mark = "ok  " if not row["drift"] else "DRIFT"
        clean += not row["drift"]
        lines.append(
            f"{mark} {row['id']:<16} status {row['status']} "
            f"(registered {row['registered_status']}) · verdict {row['registered_verdict']}"
        )
        if row["drift"]:
            lines.append(f"      drift: {', '.join(row['drift'])}")
        signal = row.get("content_signal")
        if signal:
            readable = ", ".join(f"{k}={v}" for k, v in sorted(signal.items()))
            lines.append(f"      content-signal: {readable}")
        if row.get("blanket_disallow"):
            lines.append(f"      disallows us: {'; '.join(row['blanket_disallow'])}")
        if not row["reachable"]:
            lines.append(f"      unreachable: {row.get('error')}")
    lines.append("")
    lines.append(f"{clean}/{len(rows)} sources match the register")
    if clean < len(rows):
        lines.append(
            "A drift is not automatically a violation: re-read the file, decide, then "
            "update data/sources.json so the next run compares against the new truth."
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--only", help="comma-separated source ids")
    args = parser.parse_args()

    wanted = {name.strip() for name in args.only.split(",")} if args.only else None
    chosen = [s for s in sources() if wanted is None or s["id"] in wanted]
    if not chosen:
        print(f"no sources matched {args.only!r}", file=sys.stderr)
        return 2

    rows = [check(source) for source in chosen]

    if args.json:
        print(
            json.dumps(
                {
                    "register": str(REGISTER_PATH.relative_to(ROOT)),
                    "checked": len(rows),
                    "drifted": sum(1 for row in rows if row["drift"]),
                    "results": rows,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(render(rows))

    drifted = any(row["drift"] for row in rows)
    unreachable = any(not row["reachable"] for row in rows)
    if drifted:
        return 1
    return 2 if unreachable else 0


if __name__ == "__main__":
    sys.exit(main())
