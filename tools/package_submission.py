#!/usr/bin/env python3
"""Build a local draft ZIP and say whether it is ready to submit.

The draft is a dry run. This command does not upload, submit, or push.
It exits 0 only when every required human item is present. Until then it
still writes the draft and a machine-readable preflight, and exits 1.

    python3 tools/package_submission.py
    python3 tools/package_submission.py --out /tmp/draft.zip --preflight /tmp/preflight.json

Secrets, `.env` files, `.git`, caches, and the design-hook directory are left
out. A non-empty API-key assignment other than the test sentinel fails the
build with exit 2 and writes no archive.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 100 * 1024 * 1024
ZIP_DATE = (2026, 11, 16, 0, 0, 0)
SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    ".impeccable",
    "dist",
    ".workbuddy-ai",
}
SKIP_NAMES = {".DS_Store", ".env"}
KEY_ASSIGN = re.compile(
    r"(?im)^[ \t]*(?:export[ \t]+)?(OPENAI_API_KEY|LABELDESK_API_KEY|BAILIAN_API_KEY|"
    r"DASHSCOPE_API_KEY|ALIYUN_API_KEY)[ \t]*=[ \t]*(\S+)"
)
SENTINELS = {"sk-test-sentinel-not-a-credential"}
MEMBERS = (
    "Chen Yongjun",
    "Cheng Chi Man",
    "Gunawan Alexander",
    "Sheikh Mohammad Saarim",
)


def iter_files(root: Path) -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in SKIP_DIRS)
        for name in sorted(filenames):
            if name in SKIP_NAMES or name in {".git"} or name.endswith((".pyc", ".pyo")):
                continue
            if name.endswith(".env") and name != ".env.example":
                continue
            if name.startswith(".rebuilt"):
                continue
            found.append(Path(dirpath) / name)
    return found


def secret_hits(path: Path) -> list[str]:
    if path.name == ".env" or (path.name.endswith(".env") and path.name != ".env.example"):
        return ["env file"]
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    hits = []
    for match in KEY_ASSIGN.finditer(text):
        value = match.group(2).strip().strip("'\"")
        if value and value not in SENTINELS:
            hits.append(match.group(1))
    if ("/" + "Users" + "/") in text:
        hits.append("local home path")
    return hits


def _value(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return ""


def _https(value: str) -> bool:
    return value.startswith("https://") and "NOT YET" not in value


def _host(value: str) -> str:
    return (urlparse(value).hostname or "").lower()


def _is_github_pages_host(host: str) -> bool:
    return host == "github.io" or host.endswith(".github.io")


def _is_raw_github_host(host: str) -> bool:
    return host == "githubusercontent.com" or host.endswith(".githubusercontent.com")


def _is_github_file_cdn(value: str) -> bool:
    """jsDelivr /gh/, githack, and similar hosts only proxy a repository file."""
    host = _host(value)
    path = (urlparse(value).path or "").lower()
    if host in {"raw.githack.com", "rawcdn.githack.com"} or host.endswith(".githack.com"):
        return True
    if host in {"gitcdn.link", "gitcdn.xyz"} or host.endswith(".gitcdn.link") or host.endswith(".gitcdn.xyz"):
        return True
    if host == "jsdelivr.net" or host.endswith(".jsdelivr.net"):
        return path == "/gh" or path.startswith("/gh/")
    if host == "statically.io" or host.endswith(".statically.io"):
        return path == "/gh" or path.startswith("/gh/")
    return False


def _is_local_or_private_host(host: str) -> bool:
    if not host:
        return True
    lowered = host.lower().rstrip(".")
    if lowered == "localhost" or lowered.endswith(".localhost") or lowered.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_unspecified)


def _pages_disabled_in_tree(root: Path) -> bool:
    page = root / "site" / "index.html"
    if not page.is_file():
        return True
    return "GitHub Pages is not enabled" in page.read_text(encoding="utf-8")


def _public_page(value: str, root: Path) -> bool:
    """A hosted page. The GitHub repository URL is the source tree, not a site.

    A github.io URL is also not a public page while this tree still says
    GitHub Pages is not enabled. A raw.githubusercontent.com URL, a
    loopback or private address, and a GitHub file CDN such as jsDelivr
    /gh/ or raw.githack.com, are not hosted public pages either.
    """
    if not _https(value):
        return False
    host = _host(value)
    lowered = value.lower()
    if "github.com/" in lowered and not _is_github_pages_host(host):
        return False
    if _is_github_pages_host(host) and _pages_disabled_in_tree(root):
        return False
    if _is_raw_github_host(host) or _is_local_or_private_host(host):
        return False
    if _is_github_file_cdn(value):
        return False
    return True


YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "www.music.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}


def _video_id(candidate: str) -> str:
    """An 11-character video id. 'videoseries' is a playlist token, not a video."""
    if not candidate or candidate.lower() == "videoseries":
        return ""
    return candidate if YOUTUBE_ID.fullmatch(candidate) else ""


def _youtube_video_id(value: str) -> str:
    """Return the 11-character video id, or empty if this is not a video URL."""
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in YOUTUBE_HOSTS:
        return ""
    parts = [part for part in (parsed.path or "").strip("/").split("/") if part]
    if host in {"youtu.be", "www.youtu.be"}:
        return _video_id(parts[0]) if parts else ""
    if not parts:
        return ""
    if parts[0] == "watch":
        return _video_id((parse_qs(parsed.query).get("v") or [""])[0])
    if parts[0] in {"embed", "shorts", "live", "v"} and len(parts) >= 2:
        # /embed/videoseries is a playlist, but the path segment is 11 characters
        # and would otherwise match the video-id pattern. The same token can
        # appear as youtu.be/videoseries or watch?v=videoseries.
        return _video_id(parts[1])
    return ""


def _youtube(value: str) -> bool:
    """A hosted YouTube video, not a homepage, channel, search, playlist embed, videoseries id, or look-alike path."""
    return _https(value) and bool(_youtube_video_id(value))


def collect_blockers(root: Path) -> list[dict]:
    """Required items the rubric asks a person to supply. Empty means ready."""
    blockers = []
    links_path = root / "links.txt"
    links = links_path.read_text(encoding="utf-8") if links_path.is_file() else ""
    checks = (
        ("public_webpage", "Public webpage:", lambda value: _public_page(value, root), "Public webpage is not a hosted https page."),
        ("presentation_youtube", "Presentation YouTube:", _youtube, "Presentation YouTube link is missing."),
        ("demo_youtube", "Demo YouTube:", _youtube, "Demo YouTube link is missing."),
    )
    for ident, prefix, ok, detail in checks:
        if not ok(_value(links, prefix)):
            blockers.append({"id": ident, "detail": detail})

    approval = root / "docs" / "CONTRIBUTION_APPROVAL.txt"
    text = approval.read_text(encoding="utf-8") if approval.is_file() else ""
    if "approved: yes" not in text.splitlines() or any(name not in text for name in MEMBERS):
        blockers.append({
            "id": "contribution_approval",
            "detail": (
                "docs/CONTRIBUTION_APPROVAL.txt is missing or not signed. "
                "The four named members have to write it. This tool will not."
            ),
        })

    pdf = root / "docs" / "proposed" / "AILT9019_Final_Report_Group10_CANDIDATE.pdf"
    if not pdf.is_file():
        blockers.append({
            "id": "updated_report_pdf",
            "detail": (
                "No updated report PDF. docs/proposed holds a review candidate only. "
                "report.pdf is the earlier teammate draft and was not replaced."
            ),
        })
    return blockers


def status_text(blockers: list[dict]) -> str:
    lines = [
        "Label Desk Group 10 draft package",
        "final_ready: no" if blockers else "final_ready: yes",
        "limit_bytes: 104857600",
        "This file is a dry run. It was not uploaded and it is not a grade.",
        "",
        "Do not treat report.pdf or AILT9019_Final_Report_Group10.docx as the updated report.",
        "The review copy is docs/proposed/REPORT_CANDIDATE.md.",
        "Running tools_build_report.py overwrites the teammate docx. Do not run it for this draft.",
        "",
    ]
    if blockers:
        lines.append("Blockers:")
        for item in blockers:
            lines.append(f"- {item['id']}: {item['detail']}")
    else:
        lines.append("No blockers recorded by this tool.")
    lines.append("")
    return "\n".join(lines)


def _write_zip(out: Path, root: Path, files: list[Path], note: bytes) -> list[dict]:
    inventory = []
    with zipfile.ZipFile(out, "w") as archive:
        for path in files:
            arcname = path.relative_to(root).as_posix()
            data = path.read_bytes()
            info = zipfile.ZipInfo(arcname, ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
            inventory.append({"path": arcname, "bytes": len(data)})
        info = zipfile.ZipInfo("SUBMISSION_STATUS.txt", ZIP_DATE)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, note)
    return inventory


def build(root: Path, out: Path, preflight: Path) -> int:
    files = iter_files(root)
    secrets = []
    for path in files:
        hits = secret_hits(path)
        if hits:
            secrets.append({"path": str(path.relative_to(root)), "hits": hits})
    blockers = collect_blockers(root)
    if secrets:
        preflight.parent.mkdir(parents=True, exist_ok=True)
        preflight.write_text(
            json.dumps({"final_ready": False, "secrets": secrets, "blockers": blockers}, indent=2) + "\n",
            encoding="utf-8",
        )
        print("refusing to write the zip: a packaged file looks like a secret or a home path")
        return 2

    out.parent.mkdir(parents=True, exist_ok=True)
    inventory = _write_zip(out, root, files, status_text(blockers).encode("utf-8"))
    nbytes = out.stat().st_size
    over = nbytes > LIMIT
    report = {
        "final_ready": not blockers and not over,
        "uploaded": False,
        "zip": str(out),
        "zip_bytes": nbytes,
        "limit_bytes": LIMIT,
        "within_limit": not over,
        "file_count": len(inventory) + 1,
        "blockers": blockers,
        "inventory": inventory,
    }
    preflight.parent.mkdir(parents=True, exist_ok=True)
    preflight.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} ({nbytes} bytes)")
    print(f"final_ready {str(report['final_ready']).lower()}")
    if over:
        return 2
    return 0 if report["final_ready"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "labeldesk-g10-draft.zip")
    parser.add_argument("--preflight", type=Path, default=ROOT / "dist" / "preflight.json")
    args = parser.parse_args()
    return build(ROOT, args.out, args.preflight)


if __name__ == "__main__":
    sys.exit(main())
