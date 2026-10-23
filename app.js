/* Label Desk browser view.
 *
 * This file does no grounding, no rendering and no refusal logic of its own: it
 * posts a catalogue number to /api/draft and draws the result the Python
 * pipeline returns. The command line and this page therefore cannot disagree.
 */

const els = {
  select: document.querySelector("#catalogueSelect"),
  form: document.querySelector("#recordForm"),
  title: document.querySelector("#fieldTitle"),
  date: document.querySelector("#fieldDate"),
  medium: document.querySelector("#fieldMedium"),
  culture: document.querySelector("#fieldCulture"),
  credit: document.querySelector("#fieldCredit"),
  previewNumber: document.querySelector("#previewNumber"),
  sourceLink: document.querySelector("#sourceLink"),
  banner: document.querySelector("#banner"),
  status: document.querySelector("#serverStatus"),
  resultTitle: document.querySelector("#resultTitle"),
  resultStatus: document.querySelector("#resultStatus"),
  resultCard: document.querySelector("#resultCard"),
  labelText: document.querySelector("#labelText"),
  claimList: document.querySelector("#claimList"),
  citationStrip: document.querySelector("#citationStrip"),
  score: document.querySelector("#scoreValue"),
  scoreLabel: document.querySelector("#scoreLabel"),
  shield: document.querySelector("#shield"),
  checkList: document.querySelector("#checkList"),
  command: document.querySelector("#commandBlock"),
  corpusVersion: document.querySelector("#corpusVersion"),
  corpusCount: document.querySelector("#corpusCount"),
  corpusChecksum: document.querySelector("#corpusChecksum"),
  draftButton: document.querySelector("#draftButton"),
  refusalButton: document.querySelector("#refusalButton"),
  resetButton: document.querySelector("#resetButton"),
};

const CHECK_ORDER = [
  ["field_existence", "Field existence", "Every claim cites a supplied field."],
  ["value_containment", "Value containment", "Every claim stays inside its cited value."],
  ["citation_resolution", "Citation resolution", "Printed citations resolve to the record."],
  ["readability", "Readability", "60–80 words, short sentences."],
];

const state = { records: [], corpus: null, selected: null, initial: null };

function setStatus(text, ok) {
  els.status.innerHTML = `<span class="status-dot"></span>${text}`;
  els.status.style.color = ok ? "var(--teal)" : "var(--red)";
  els.status.style.background = ok ? "var(--teal-soft)" : "var(--red-soft)";
}

function showBanner(show) {
  els.banner.hidden = !show;
}

function recordByNumber(number) {
  return state.records.find((record) => record.catalogue_number === number) || null;
}

function fillRecord(record) {
  if (!record) return;
  state.selected = record;
  els.select.value = record.catalogue_number;
  els.title.value = record.title || "";
  els.date.value = record.object_date || "";
  els.medium.value = record.medium || "";
  els.culture.value = record.place_or_culture || "";
  els.credit.value = record.credit_line || "";
  els.previewNumber.textContent = record.catalogue_number;
  if (record.source_url) {
    els.sourceLink.href = record.source_url;
    els.sourceLink.textContent = `Met object ${record.object_id}`;
  }
  els.command.textContent = `python3 -m labeldesk ${record.catalogue_number}`;
  for (const input of [els.title, els.date, els.medium, els.culture, els.credit]) {
    const missing = !input.value.trim();
    input.classList.toggle("missing", missing);
    input.value = missing ? "— not in the record —" : input.value;
  }
}

async function draft() {
  const number = els.select.value;
  if (!number) return;
  els.draftButton.disabled = true;
  try {
    const response = await fetch("/api/draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ catalogue_number: number }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    renderResult(await response.json());
  } catch (error) {
    showBanner(true);
    setStatus("Pipeline unreachable", false);
    console.error(error);
  } finally {
    els.draftButton.disabled = false;
  }
}

function renderResult(result) {
  const refused = result.status === "refused";
  els.resultStatus.textContent = refused ? "REFUSED" : "DRAFTED";
  els.resultStatus.classList.toggle("refused", refused);
  els.resultCard.classList.toggle("refused", refused);
  els.resultTitle.textContent = refused ? "Safe refusal" : "Grounded draft";
  els.labelText.textContent = refused ? result.reason_text : result.label;

  els.claimList.innerHTML = refused
    ? `<span class="claim-tag">Reason · ${result.reason}</span>`
    : result.claims
        .map(
          (claim) =>
            `<span class="claim-tag" title="cited value: ${escapeHtml(claim.value_span)}">` +
            `${claim.id} · ${claim.source_field.replace(/_/g, " ")}</span>`,
        )
        .join("");

  els.citationStrip.innerHTML = refused
    ? ""
    : result.citations
        .map((citation) => `<span class="citation-tag">↳ ${escapeHtml(citation.value_span)}</span>`)
        .join("");

  if (refused) {
    els.score.textContent = "0";
    els.score.style.color = "var(--red)";
    els.scoreLabel.textContent = "claims emitted · refused by design";
    els.shield.textContent = "!";
    els.shield.style.color = "var(--red)";
    els.shield.style.background = "var(--red-soft)";
    els.checkList.innerHTML = `<div class="check-row"><span class="check-icon" style="background:var(--red)">!</span><div><b>No label produced</b><small>${escapeHtml(result.reason_text)}</small></div></div>`;
    return;
  }

  const checks = result.checks;
  const passed = CHECK_ORDER.filter(([key]) => checks[key].passed).length;
  els.score.textContent = `${passed}/4`;
  els.score.style.color = passed === 4 ? "var(--teal)" : "var(--red)";
  els.scoreLabel.textContent = `checks passed · ${checks.word_count} words · ${checks.average_sentence_length} words per sentence`;
  els.shield.textContent = passed === 4 ? "✓" : "!";
  els.shield.style.color = passed === 4 ? "var(--teal)" : "var(--red)";
  els.shield.style.background = passed === 4 ? "var(--teal-soft)" : "var(--red-soft)";

  els.checkList.innerHTML = CHECK_ORDER.map(([key, title, description]) => {
    const check = checks[key];
    const color = check.passed ? "var(--teal)" : "var(--red)";
    const icon = check.passed ? "✓" : "!";
    return `<div class="check-row"><span class="check-icon" style="background:${color}">${icon}</span><div><b>${title}</b><small>${escapeHtml(check.detail)}</small></div></div>`;
  }).join("");
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

async function boot() {
  try {
    const response = await fetch("/api/records");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    state.records = data.records;
    state.corpus = data.corpus;

    els.select.innerHTML = data.records
      .map((record) => {
        const flag = record.missing.length ? " · incomplete" : "";
        return `<option value="${record.catalogue_number}">${record.catalogue_number} — ${escapeHtml(record.title)}${flag}</option>`;
      })
      .join("");

    els.corpusVersion.textContent = `v${data.corpus.version}`;
    els.corpusCount.textContent = `${data.corpus.record_count}`;
    els.corpusChecksum.textContent = data.corpus.checksum.slice(0, 12);

    showBanner(false);
    setStatus("Local pipeline connected", true);
    fillRecord(state.records.find((record) => !record.missing.length) || state.records[0]);
    state.initial = els.select.value;
    await draft();

    // #refuse opens the page already on the refusal path, for demo recordings.
    if (location.hash === "#refuse") {
      const target = state.records.find((record) => record.missing.length);
      if (target) {
        fillRecord(target);
        await draft();
      }
    }
  } catch (error) {
    showBanner(true);
    setStatus("Pipeline unreachable", false);
    console.error(error);
  }
}

els.select.addEventListener("change", async () => {
  fillRecord(recordByNumber(els.select.value));
  await draft();
});

els.form.addEventListener("submit", (event) => {
  event.preventDefault();
  draft();
});

els.refusalButton.addEventListener("click", async () => {
  const target = state.records.find((record) => record.missing.length) || state.records[0];
  fillRecord(target);
  await draft();
});

els.resetButton.addEventListener("click", async () => {
  if (state.initial) fillRecord(recordByNumber(state.initial));
  await draft();
});

boot();
