# 60-second recording: shot list

One real input, the system processing it, the result. No slides. Keep the terminal font
large (18pt or more) and the window at 1440×900 so the text is readable when compressed.

Record at 1080p, 30fps, and keep the whole thing under 60 seconds.

| Time | Screen | Narration (say this) |
| --- | --- | --- |
| 0:00–0:06 | Terminal, repository root. | "This is Label Desk. It turns one museum catalogue record into a draft exhibition label, and checks every sentence against that record." |
| 0:06–0:12 | Type `python3 -m labeldesk --list`. Twenty rows scroll. | "The corpus is twenty real Met Open Access records, frozen on disk. No network, no model." |
| 0:12–0:16 | Clear. Type `python3 -m labeldesk 14.40.377`. | "One catalogue number in." |
| 0:16–0:28 | Output appears: STATUS DRAFTED, the label, five claims with their cited values. | "Out comes a 65-word label. Each sentence is a claim, and each claim points at the field it came from — title, date, medium, place, credit line." |
| 0:28–0:36 | Scroll to the Checks block. | "Four checks run on every claim: the field exists, every word comes from it, the citation resolves, and the label sits in the sixty to eighty word band. All four pass." |
| 0:36–0:44 | Type `python3 -m labeldesk 36.120.655`. Point at `ca. 1740`. | "A hedged record keeps its hedge. The label says 'ca. 1740', not '1740' — the tool never states a firmer date than the museum does." |
| 0:44–0:54 | Type `python3 -m labeldesk 62.98.1`. Output: STATUS REFUSED. | "This record has no object date. The system refuses, names the missing field, and prints no label. It does not fill the gap from memory." |
| 0:54–0:59 | Type `python3 -m pytest -q`, then `python3 eval/evaluate.py`. Show `51 passed` and `17/17`. | "Fifty-one tests, and a seventeen-case golden set, all passing on this commit." |
| 0:59–1:00 | Cut. | — |

## Pre-flight checks

- Terminal: clear scrollback, no personal paths in view, notifications off, no API keys on
  screen.
- Font: at least 18pt. Do not record a full 4K desktop.
- Run `python3 eval/evaluate.py` once before recording so the report files already exist.
- If the browser view is used instead of the terminal: `python3 server.py`, then
  `http://127.0.0.1:8000/` and `http://127.0.0.1:8000/#refuse`. It calls the same pipeline,
  so the claims and checks on screen are the real ones.

## Two commands to keep ready

```bash
python3 -m labeldesk 14.40.377      # drafted
python3 -m labeldesk 62.98.1        # refused
```
