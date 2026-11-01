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
| 0:54–0:59 | Type `python3 -m pytest -q`, then `python3 eval/evaluate.py`. Show `191 passed` and `17/17`. | "A hundred and ninety-one tests, and a seventeen-case golden set, all passing on this commit." |
| 0:59–1:00 | Cut. | — |

## Optional: the model layer on camera

The sixty-second cut above is the offline path, which is the whole system the midterm
submission describes. If the final recording should show the model layer, swap the pytest
shot for these three — the total stays under 60 seconds because the `--replay` calls are
instant.

| Time | Screen | Narration (say this) |
| --- | --- | --- |
| 0:50–0:55 | `python3 -m labeldesk 14.40.377 --llm --replay`. Point at `Model … rewrite accepted`. | "The same record with the model layer on. The model rewords the five sentences, and the rewrite is kept because it passed the same four checks." |
| 0:55–1:00 | `python3 -m labeldesk 36.120.655 --llm --replay`. Point at `rewrite discarded`. | "Here the rewrite was thrown away — it cited a shorter slice of the medium than the draft did. The offline draft prints instead, so turning the model on can cost prose, never a fact." |

## Optional: the second museum on camera

This is the strongest thirty seconds in the deck if there is room, because it answers the
obvious objection — that the tool was tuned to twenty records the team picked.

| Time | Screen | Narration (say this) |
| --- | --- | --- |
| 0:00–0:06 | `python3 -m labeldesk --sources`. Point at the `refused` rows. | "Seven sources were checked, by reading their robots files. Two were refused — the British Museum and the Palace Museum — and the refusal is in the table, not in a footnote." |
| 0:06–0:16 | `python3 -m labeldesk 1926.428 --corpus cleveland --llm --replay`. Point at `c. 1160–1170`. | "A different museum, a different API, and a date phrase the team did not write. The hedge survives the model rewrite intact." |
| 0:16–0:26 | `python3 -m labeldesk 1970.36 --corpus /tmp/private.json --llm --replay`. Point at `refused before sending: source_policy`, then at `echo $?` → `4`. | "And a corpus whose source does not permit it never reaches the model at all. Nothing was sent. The licence is checked before the call, not reported after it." |

Do not run `--llm` without `--replay` while recording: a live call is slow, and the pre-flight
rule about no API keys on screen applies either way.

## Pre-flight checks

- Terminal: clear scrollback, no personal paths in view, notifications off, no API keys on
  screen. `python3 -m labeldesk --status` prints a key fingerprint, not the key — if you show
  that screen, the last four characters are visible, so prefer `--replay` and skip `--status`.
- Font: at least 18pt. Do not record a full 4K desktop.
- Run `python3 eval/evaluate.py` and `python3 eval/cross_corpus.py` once before recording so
  the report files already exist.
- If the browser view is used instead of the terminal: `python3 server.py`, then
  `http://127.0.0.1:8000/` and `http://127.0.0.1:8000/#refuse`. It calls the same pipeline,
  so the claims and checks on screen are the real ones.
- If the presenting machine may not have Python, open `labeldesk.html` instead. Same
  records, same labels, same checks — precomputed by the pipeline at build time. Say so
  on camera: it is a snapshot, and the command under 04 · REPRODUCE is how to verify it.

## Two commands to keep ready

```bash
python3 -m labeldesk 14.40.377      # drafted
python3 -m labeldesk 62.98.1        # refused
python3 -m labeldesk 1970.36 --corpus cleveland   # a second museum
python3 -m labeldesk --sources      # what was admitted, and what was refused
```
