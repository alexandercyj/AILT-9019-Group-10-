"""The draft package stays unready until a person supplies the missing rubric items."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from package_submission import collect_blockers, secret_hits  # noqa: E402


def test_current_tree_is_not_final_ready(tmp_path):
    completed = __import__("subprocess").run(
        [
            sys.executable,
            str(ROOT / "tools" / "package_submission.py"),
            "--out",
            str(tmp_path / "draft.zip"),
            "--preflight",
            str(tmp_path / "preflight.json"),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert completed.returncode == 1, completed.stdout + completed.stderr
    report = json.loads((tmp_path / "preflight.json").read_text(encoding="utf-8"))
    assert report["final_ready"] is False
    assert report["uploaded"] is False
    assert report["within_limit"] is True
    assert report["zip_bytes"] <= report["limit_bytes"]
    ids = {item["id"] for item in report["blockers"]}
    assert {
        "public_webpage",
        "contribution_approval",
        "updated_report_pdf",
    } <= ids
    names = zipfile.ZipFile(tmp_path / "draft.zip").namelist()
    assert "SUBMISSION_STATUS.txt" in names
    assert "links.txt" in names
    assert "docs/proposed/REPORT_CANDIDATE.md" in names
    assert not any(name.startswith(".git/") or name == ".env" or ".impeccable/" in name for name in names)
    assert all(".ailt9019-group10.env" not in name for name in names)
    status = zipfile.ZipFile(tmp_path / "draft.zip").read("SUBMISSION_STATUS.txt").decode("utf-8")
    assert "final_ready: no" in status
    assert "NOT" in Path(ROOT / "links.txt").read_text(encoding="utf-8")
    assert "presentation_youtube" not in ids
    assert "demo_youtube" not in ids


def test_supplied_items_clear_the_gate(tmp_path):
    (tmp_path / "links.txt").write_text(
        "Public webpage: https://example.edu/g10\n"
        "Presentation YouTube: https://www.youtube.com/watch?v=aaaaaaaaaaa\n"
        "Demo YouTube: https://youtu.be/bbbbbbbbbbb\n",
        encoding="utf-8",
    )
    approval = tmp_path / "docs"
    approval.mkdir()
    (approval / "CONTRIBUTION_APPROVAL.txt").write_text(
        "approved: yes\n"
        "Chen Yongjun\nCheng Chi Man\nGunawan Alexander\nSheikh Mohammad Saarim\n",
        encoding="utf-8",
    )
    proposed = tmp_path / "docs" / "proposed"
    proposed.mkdir()
    (proposed / "AILT9019_Final_Report_Group10_CANDIDATE.pdf").write_bytes(b"%PDF-1.4\n")
    assert collect_blockers(tmp_path) == []


def test_secret_assignment_is_rejected(tmp_path):
    sample = tmp_path / "notes.txt"
    sample.write_text("BAILIAN_API_KEY=sk-not-a-real-value\n", encoding="utf-8")
    assert secret_hits(sample) == ["BAILIAN_API_KEY"]
    sample.write_text("BAILIAN_API_KEY=\n", encoding="utf-8")
    assert secret_hits(sample) == []
    sample.write_text("BAILIAN_API_KEY=sk-test-sentinel-not-a-credential\n", encoding="utf-8")
    assert secret_hits(sample) == []


def test_repository_url_is_not_a_public_webpage(tmp_path):
    (tmp_path / "links.txt").write_text(
        "Public webpage: https://github.com/alexandercyj/AILT-9019-Group-10-\n"
        "Presentation YouTube: https://www.youtube.com/watch?v=aaaaaaaaaaa\n"
        "Demo YouTube: https://youtu.be/bbbbbbbbbbb\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "CONTRIBUTION_APPROVAL.txt").write_text(
        "approved: yes\n"
        "Chen Yongjun\nCheng Chi Man\nGunawan Alexander\nSheikh Mohammad Saarim\n",
        encoding="utf-8",
    )
    proposed = docs / "proposed"
    proposed.mkdir()
    (proposed / "AILT9019_Final_Report_Group10_CANDIDATE.pdf").write_bytes(b"%PDF-1.4\n")
    ids = {item["id"] for item in collect_blockers(tmp_path)}
    assert ids == {"public_webpage"}



def test_github_io_is_not_a_public_webpage_while_pages_are_off(tmp_path):
    (tmp_path / "links.txt").write_text(
        "Public webpage: https://alexandercyj.github.io/AILT-9019-Group-10-/\n"
        "Presentation YouTube: https://www.youtube.com/watch?v=aaaaaaaaaaa\n"
        "Demo YouTube: https://youtu.be/bbbbbbbbbbb\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "CONTRIBUTION_APPROVAL.txt").write_text(
        "approved: yes\n"
        "Chen Yongjun\nCheng Chi Man\nGunawan Alexander\nSheikh Mohammad Saarim\n",
        encoding="utf-8",
    )
    proposed = docs / "proposed"
    proposed.mkdir()
    (proposed / "AILT9019_Final_Report_Group10_CANDIDATE.pdf").write_bytes(b"%PDF-1.4\n")
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(
        "<!DOCTYPE html><html lang='en'><body>"
        "GitHub Pages is not enabled on the repository. "
        "Do not treat a github.io address as this page."
        "</body></html>\n",
        encoding="utf-8",
    )
    ids = {item["id"] for item in collect_blockers(tmp_path)}
    assert ids == {"public_webpage"}


def test_raw_githubusercontent_is_not_a_public_webpage(tmp_path):
    (tmp_path / "links.txt").write_text(
        "Public webpage: https://raw.githubusercontent.com/alexandercyj/AILT-9019-Group-10-/cursor/ailt9019-release-69c3/site/index.html\n"
        "Presentation YouTube: https://www.youtube.com/watch?v=aaaaaaaaaaa\n"
        "Demo YouTube: https://youtu.be/bbbbbbbbbbb\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "CONTRIBUTION_APPROVAL.txt").write_text(
        "approved: yes\n"
        "Chen Yongjun\nCheng Chi Man\nGunawan Alexander\nSheikh Mohammad Saarim\n",
        encoding="utf-8",
    )
    proposed = docs / "proposed"
    proposed.mkdir()
    (proposed / "AILT9019_Final_Report_Group10_CANDIDATE.pdf").write_bytes(b"%PDF-1.4\n")
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(
        "<!DOCTYPE html><html lang='en'><body>Local landing page.</body></html>\n",
        encoding="utf-8",
    )
    ids = {item["id"] for item in collect_blockers(tmp_path)}
    assert ids == {"public_webpage"}


def test_loopback_or_private_host_is_not_a_public_webpage(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "CONTRIBUTION_APPROVAL.txt").write_text(
        "approved: yes\n"
        "Chen Yongjun\nCheng Chi Man\nGunawan Alexander\nSheikh Mohammad Saarim\n",
        encoding="utf-8",
    )
    proposed = docs / "proposed"
    proposed.mkdir()
    (proposed / "AILT9019_Final_Report_Group10_CANDIDATE.pdf").write_bytes(b"%PDF-1.4\n")
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(
        "<!DOCTYPE html><html lang='en'><body>Local landing page.</body></html>\n",
        encoding="utf-8",
    )
    for url in (
        "https://127.0.0.1:8000/",
        "https://localhost/site/index.html",
        "https://192.168.1.10/labeldesk.html",
    ):
        (tmp_path / "links.txt").write_text(
            f"Public webpage: {url}\n"
            "Presentation YouTube: https://www.youtube.com/watch?v=aaaaaaaaaaa\n"
            "Demo YouTube: https://youtu.be/bbbbbbbbbbb\n",
            encoding="utf-8",
        )
        ids = {item["id"] for item in collect_blockers(tmp_path)}
        assert ids == {"public_webpage"}, url


def test_github_file_cdn_is_not_a_public_webpage(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "CONTRIBUTION_APPROVAL.txt").write_text(
        "approved: yes\n"
        "Chen Yongjun\nCheng Chi Man\nGunawan Alexander\nSheikh Mohammad Saarim\n",
        encoding="utf-8",
    )
    proposed = docs / "proposed"
    proposed.mkdir()
    (proposed / "AILT9019_Final_Report_Group10_CANDIDATE.pdf").write_bytes(b"%PDF-1.4\n")
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(
        "<!DOCTYPE html><html lang='en'><body>Local landing page.</body></html>\n",
        encoding="utf-8",
    )
    for url in (
        "https://cdn.jsdelivr.net/gh/alexandercyj/AILT-9019-Group-10-@cursor/ailt9019-release-69c3/site/index.html",
        "https://raw.githack.com/alexandercyj/AILT-9019-Group-10-/cursor/ailt9019-release-69c3/site/index.html",
        "https://rawcdn.githack.com/alexandercyj/AILT-9019-Group-10-/cursor/ailt9019-release-69c3/site/index.html",
        "https://cdn.statically.io/gh/alexandercyj/AILT-9019-Group-10-/cursor/ailt9019-release-69c3/site/index.html",
        "https://gitcdn.link/repo/alexandercyj/AILT-9019-Group-10-/cursor/ailt9019-release-69c3/site/index.html",
    ):
        (tmp_path / "links.txt").write_text(
            f"Public webpage: {url}\n"
            "Presentation YouTube: https://www.youtube.com/watch?v=aaaaaaaaaaa\n"
            "Demo YouTube: https://youtu.be/bbbbbbbbbbb\n",
            encoding="utf-8",
        )
        ids = {item["id"] for item in collect_blockers(tmp_path)}
        assert ids == {"public_webpage"}, url


def test_youtube_url_that_is_not_a_video_is_refused(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "CONTRIBUTION_APPROVAL.txt").write_text(
        "approved: yes\n"
        "Chen Yongjun\nCheng Chi Man\nGunawan Alexander\nSheikh Mohammad Saarim\n",
        encoding="utf-8",
    )
    proposed = docs / "proposed"
    proposed.mkdir()
    (proposed / "AILT9019_Final_Report_Group10_CANDIDATE.pdf").write_bytes(b"%PDF-1.4\n")
    good_page = "https://example.edu/g10"
    good_video = "https://www.youtube.com/watch?v=aaaaaaaaaaa"
    for presentation, demo in (
        ("https://www.youtube.com/", good_video),
        ("https://www.youtube.com/channel/UCaaaaaaaaaaaaaaaaaaaaaa", good_video),
        ("https://www.youtube.com/results?search_query=label+desk", good_video),
        ("https://youtu.be/", good_video),
        ("https://www.youtube.com/watch?v=", good_video),
        ("https://example.edu/youtube.com/watch?v=aaaaaaaaaaa", good_video),
        ("https://youtube.com.example.edu/watch?v=aaaaaaaaaaa", good_video),
        (good_video, "https://www.youtube.com/"),
    ):
        (tmp_path / "links.txt").write_text(
            f"Public webpage: {good_page}\n"
            f"Presentation YouTube: {presentation}\n"
            f"Demo YouTube: {demo}\n",
            encoding="utf-8",
        )
        ids = {item["id"] for item in collect_blockers(tmp_path)}
        assert "presentation_youtube" in ids or "demo_youtube" in ids, (presentation, demo)
        assert "public_webpage" not in ids


def test_youtube_playlist_embed_is_refused(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "CONTRIBUTION_APPROVAL.txt").write_text(
        "approved: yes\n"
        "Chen Yongjun\nCheng Chi Man\nGunawan Alexander\nSheikh Mohammad Saarim\n",
        encoding="utf-8",
    )
    proposed = docs / "proposed"
    proposed.mkdir()
    (proposed / "AILT9019_Final_Report_Group10_CANDIDATE.pdf").write_bytes(b"%PDF-1.4\n")
    good_page = "https://example.edu/g10"
    good_video = "https://www.youtube.com/watch?v=aaaaaaaaaaa"
    for presentation, demo in (
        ("https://www.youtube.com/embed/videoseries?list=PLaaaaaaaaaaaaaaaaaaaaaa", good_video),
        ("https://www.youtube-nocookie.com/embed/videoseries?list=PLaaaaaaaaaaaaaaaaaaaaaa", good_video),
        ("https://m.youtube.com/embed/videoseries?list=PLaaaaaaaaaaaaaaaaaaaaaa", good_video),
        (good_video, "https://www.youtube.com/embed/videoseries?list=PLaaaaaaaaaaaaaaaaaaaaaa"),
    ):
        (tmp_path / "links.txt").write_text(
            f"Public webpage: {good_page}\n"
            f"Presentation YouTube: {presentation}\n"
            f"Demo YouTube: {demo}\n",
            encoding="utf-8",
        )
        ids = {item["id"] for item in collect_blockers(tmp_path)}
        assert "presentation_youtube" in ids or "demo_youtube" in ids, (presentation, demo)
        assert "public_webpage" not in ids


def test_youtube_videoseries_id_is_refused(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "CONTRIBUTION_APPROVAL.txt").write_text(
        "approved: yes\n"
        "Chen Yongjun\nCheng Chi Man\nGunawan Alexander\nSheikh Mohammad Saarim\n",
        encoding="utf-8",
    )
    proposed = docs / "proposed"
    proposed.mkdir()
    (proposed / "AILT9019_Final_Report_Group10_CANDIDATE.pdf").write_bytes(b"%PDF-1.4\n")
    good_page = "https://example.edu/g10"
    good_video = "https://www.youtube.com/watch?v=aaaaaaaaaaa"
    for presentation, demo in (
        ("https://youtu.be/videoseries?list=PLaaaaaaaaaaaaaaaaaaaaaa", good_video),
        ("https://www.youtube.com/watch?v=videoseries&list=PLaaaaaaaaaaaaaaaaaaaaaa", good_video),
        ("https://www.youtube-nocookie.com/watch?v=videoseries&list=PLaaaaaaaaaaaaaaaaaaaaaa", good_video),
        ("https://m.youtube.com/watch?v=videoseries&list=PLaaaaaaaaaaaaaaaaaaaaaa", good_video),
        (good_video, "https://youtu.be/videoseries?list=PLaaaaaaaaaaaaaaaaaaaaaa"),
    ):
        (tmp_path / "links.txt").write_text(
            f"Public webpage: {good_page}\n"
            f"Presentation YouTube: {presentation}\n"
            f"Demo YouTube: {demo}\n",
            encoding="utf-8",
        )
        ids = {item["id"] for item in collect_blockers(tmp_path)}
        assert "presentation_youtube" in ids or "demo_youtube" in ids, (presentation, demo)
        assert "public_webpage" not in ids


def test_youtube_url_is_not_a_public_webpage(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "CONTRIBUTION_APPROVAL.txt").write_text(
        "approved: yes\n"
        "Chen Yongjun\nCheng Chi Man\nGunawan Alexander\nSheikh Mohammad Saarim\n",
        encoding="utf-8",
    )
    proposed = docs / "proposed"
    proposed.mkdir()
    (proposed / "AILT9019_Final_Report_Group10_CANDIDATE.pdf").write_bytes(b"%PDF-1.4\n")
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(
        "<!DOCTYPE html><html lang='en'><body>Local landing page.</body></html>\n",
        encoding="utf-8",
    )
    for url in (
        "https://www.youtube.com/watch?v=aaaaaaaaaaa",
        "https://youtu.be/bbbbbbbbbbb",
        "https://www.youtube.com/embed/aaaaaaaaaaa",
        "https://www.youtube-nocookie.com/embed/aaaaaaaaaaa",
        "https://m.youtube.com/watch?v=aaaaaaaaaaa",
        "https://www.youtube.com/",
        "https://img.youtube.com/vi/aaaaaaaaaaa/0.jpg",
    ):
        (tmp_path / "links.txt").write_text(
            f"Public webpage: {url}\n"
            "Presentation YouTube: https://www.youtube.com/watch?v=aaaaaaaaaaa\n"
            "Demo YouTube: https://youtu.be/bbbbbbbbbbb\n",
            encoding="utf-8",
        )
        ids = {item["id"] for item in collect_blockers(tmp_path)}
        assert ids == {"public_webpage"}, url
