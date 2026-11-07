/* Label Desk browser view.
 *
 * This file does no grounding, no refusal logic and no drafting of its own: it
 * posts to /api/draft, /api/fetch and /api/search and draws what the Python
 * pipeline returns. The command line and this page therefore cannot disagree.
 * Icons are inline SVG so buttons and badges render the same on every platform.
 *
 * One extra responsibility this view does carry: source attribution. Every part
 * of the structured introduction is tagged with where it came from —
 *   .source-tag.web     field values copied verbatim from a museum record
 *   .source-tag.offline the deterministic renderer, no model involved
 *   .source-tag.ai      a model rewrite, shown only when it passed the checks
 */

const ICONS = {
  "arrow-right":
    '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.5 8h10"/><path d="M9 3.5 13.5 8 9 12.5"/></svg>',
  citation:
    '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 3v7a3 3 0 0 0 3 3h7"/></svg>',
  check:
    '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3.5 8.5 6.5 11.5 12.5 4.5"/></svg>',
  warn:
    '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M8 4v5.5"/><circle cx="8" cy="12.2" r="1.1" fill="currentColor" stroke="none"/></svg>',
};

for (const slot of document.querySelectorAll("[data-icon]")) {
  slot.innerHTML = ICONS[slot.dataset.icon] || "";
}

const els = {
  select: document.querySelector("#catalogueSelect"),
  form: document.querySelector("#recordForm"),
  title: document.querySelector("#fieldTitle"),
  date: document.querySelector("#fieldDate"),
  medium: document.querySelector("#fieldMedium"),
  culture: document.querySelector("#fieldCulture"),
  credit: document.querySelector("#fieldCredit"),
  plateInitials: document.querySelector("#plateInitials"),
  previewNumber: document.querySelector("#previewNumber"),
  sourceLink: document.querySelector("#sourceLink"),
  sourceBadge: document.querySelector("#sourceBadge"),
  provenanceLine: document.querySelector("#provenanceLine"),
  banner: document.querySelector("#banner"),
  status: document.querySelector("#serverStatus"),
  metricRecords: document.querySelector("#metricRecords"),
  footerMeta: document.querySelector("#footerMeta"),
  resultTitle: document.querySelector("#resultTitle"),
  resultStatus: document.querySelector("#resultStatus"),
  resultCard: document.querySelector("#resultCard"),
  introHint: document.querySelector("#introHint"),
  introList: document.querySelector("#introList"),
  summaryTag: document.querySelector("#summaryTag"),
  labelText: document.querySelector("#labelText"),
  claimList: document.querySelector("#claimList"),
  citationStrip: document.querySelector("#citationStrip"),
  score: document.querySelector("#scoreValue"),
  scoreLabel: document.querySelector("#scoreLabel"),
  shield: document.querySelector("#shield"),
  checkList: document.querySelector("#checkList"),
  draftButton: document.querySelector("#draftButton"),
  refusalButton: document.querySelector("#refusalButton"),
  resetButton: document.querySelector("#resetButton"),
  llmToggle: document.querySelector("#llmToggle"),
  modelNote: document.querySelector("#modelNote"),
  askInput: document.querySelector("#askInput"),
  askButton: document.querySelector("#askButton"),
  liveProvider: document.querySelector("#liveProvider"),
  liveObjectId: document.querySelector("#liveObjectId"),
  liveFetchButton: document.querySelector("#liveFetchButton"),
  liveExamples: document.querySelector("#liveExamples"),
  liveStatus: document.querySelector("#liveStatus"),
  searchProvider: document.querySelector("#searchProvider"),
  nameInput: document.querySelector("#nameInput"),
  nameSearchButton: document.querySelector("#nameSearchButton"),
  nameStatus: document.querySelector("#nameStatus"),
  searchResults: document.querySelector("#searchResults"),
  googleLink: document.querySelector("#googleLink"),
};

const CHECK_ORDER = [
  ["field_existence", "Field existence", "Every claim cites a supplied field."],
  ["value_containment", "Value containment", "Every claim stays inside its cited value."],
  ["citation_resolution", "Citation resolution", "Printed citations resolve to the record."],
  ["readability", "Readability", "60–80 words, short sentences."],
];

const state = {
  records: [],
  corpus: null,
  providers: {},
  selected: null,
  initial: null,
  token: 0,
  // How the current record arrived: { kind: "corpus" | "live", label: "..." }.
  // Drives the Web source tag on every structured-introduction row.
  source: { kind: "corpus", label: "Frozen corpus (CC0)" },
};

function setStatus(text, ok) {
  els.status.innerHTML = `<span class="status-dot"></span>${escapeHtml(text)}`;
  els.status.classList.toggle("is-bad", !ok);
}

function showBanner(show) {
  els.banner.hidden = !show;
}

function recordByNumber(number) {
  return state.records.find((record) => record.catalogue_number === number) || null;
}

function plateInitials(title) {
  const words = String(title || "")
    .split(/\s+/)
    .map((word) => word.replace(/[^A-Za-zÀ-ÿ0-9]/g, ""))
    .filter((word) => word && !/^(a|an|the|of|and)$/i.test(word));
  if (!words.length) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

function setBadge(text, live) {
  els.sourceBadge.textContent = text;
  els.sourceBadge.classList.toggle("is-live", Boolean(live));
}

function setBusy(button, busy, busyLabel) {
  if (!button) return;
  button.classList.toggle("is-loading", busy);
  button.disabled = busy;
  if (busyLabel) {
    if (busy) {
      button.dataset.idleLabel = button.querySelector(".button-label")
        ? button.querySelector(".button-label").textContent
        : button.textContent;
      const label = button.querySelector(".button-label");
      if (label) label.textContent = busyLabel;
      else button.textContent = busyLabel;
    } else {
      const label = button.querySelector(".button-label");
      if (label) label.textContent = button.dataset.idleLabel;
      else button.textContent = button.dataset.idleLabel;
    }
  }
}

function fillRecord(record, meta = {}) {
  if (!record) return;
  state.selected = record;
  if (meta.select !== false) els.select.value = record.catalogue_number;
  els.title.value = record.title || "";
  els.date.value = record.object_date || "";
  els.medium.value = record.medium || "";
  els.culture.value = record.place_or_culture || "";
  els.credit.value = record.credit_line || "";
  els.plateInitials.textContent = plateInitials(record.title);
  els.previewNumber.textContent = record.catalogue_number;
  if (record.source_url) {
    els.sourceLink.href = record.source_url;
    els.sourceLink.textContent = "Open the museum record";
  } else {
    els.sourceLink.removeAttribute("href");
    els.sourceLink.textContent = "No museum link in the record";
  }
  if (meta.live) {
    setBadge(`Live · ${meta.providerName}`, true);
    state.source = { kind: "live", label: `${meta.providerName} open access API (CC0)` };
  } else {
    const license = (state.corpus && state.corpus.license) || "CC0";
    setBadge(`Frozen corpus · ${license.split(" ")[0]}`, false);
    state.source = { kind: "corpus", label: `Frozen corpus · ${license}` };
  }
  for (const input of [els.title, els.date, els.medium, els.culture, els.credit]) {
    const missing = !input.value.trim();
    input.classList.toggle("missing", missing);
    input.value = missing ? "— not in the record —" : input.value;
  }
}

async function post(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

async function draft(meta = {}) {
  const number = els.select.value;
  if (!number) return;
  const token = ++state.token;
  setBusy(els.draftButton, true, "Drafting…");
  try {
    const result = await post("/api/draft", {
      catalogue_number: number,
      question: meta.question || null,
      llm: els.llmToggle.checked ? "auto" : null,
    });
    if (token !== state.token) return;
    // /api/draft always answers from the frozen corpus; make sure the badge and
    // the source tags agree even when the previous view was a live lookup.
    const license = (state.corpus && state.corpus.license) || "CC0";
    setBadge(`Frozen corpus · ${license.split(" ")[0]}`, false);
    state.source = { kind: "corpus", label: `Frozen corpus · ${license}` };
    renderResult(result);
  } catch (error) {
    if (token !== state.token) return;
    showBanner(true);
    setStatus("Pipeline unreachable", false);
    console.error(error);
  } finally {
    if (token === state.token) setBusy(els.draftButton, false);
  }
}

function liveErrorMessage(error) {
  const data = error.data || {};
  if (data.error === "upstream_http") {
    return `The museum's API answered with HTTP ${data.status}. Check the object ID — nothing was drafted.`;
  }
  if (data.error === "upstream_unreachable") {
    return "The museum's API could not be reached from this machine. Nothing was drafted.";
  }
  if (data.error === "bad_object_id") {
    return "That object ID does not parse as a number.";
  }
  return "The fetch failed. Nothing was drafted.";
}

// One live record by provider + object ID, then the identical pipeline. Used by
// both the object-ID box and a candidate picked from a name search.
async function fetchLive(options = {}) {
  const provider = options.provider || els.liveProvider.value;
  const objectId = options.objectId || els.liveObjectId.value.trim();
  if (!objectId) {
    els.liveStatus.hidden = false;
    els.liveStatus.textContent = "Type an object ID first — the examples below are one click away.";
    return;
  }
  const token = ++state.token;
  setBusy(options.button || els.liveFetchButton, true, "Fetching…");
  els.liveStatus.hidden = true;
  try {
    const body = await post("/api/fetch", {
      provider,
      object_id: objectId,
      llm: els.llmToggle.checked ? "auto" : null,
    });
    if (token !== state.token) return;
    const spec = state.providers[provider] || {};
    fillRecord(body.record, {
      live: true,
      providerName: body.provider_name,
      endpoint: spec.endpoint || "",
    });
    els.select.value = "";
    renderResult(body.result);
    setStatus("Local pipeline connected", true);
  } catch (error) {
    if (token !== state.token) return;
    els.liveStatus.hidden = false;
    els.liveStatus.textContent = liveErrorMessage(error);
  } finally {
    if (token === state.token) setBusy(options.button || els.liveFetchButton, false);
  }
}

// ---------------------------------------------------------------- name search

function updateGoogleLink() {
  const name = els.nameInput.value.trim();
  const provider = state.providers[els.searchProvider.value] || {};
  const query = name ? `"${name}" ${(provider.name || "").replace(/^The /, "")} collection` : "museum collection";
  els.googleLink.href = `https://www.google.com/search?q=${encodeURIComponent(query)}`;
}

function searchErrorMessage(error) {
  const data = error.data || {};
  if (data.error === "upstream_http") {
    return `The museum's search API answered with HTTP ${data.status}. Nothing was fetched.`;
  }
  if (data.error === "upstream_unreachable") {
    return "The museum's search API could not be reached from this machine. Nothing was fetched.";
  }
  if (data.error === "name_required") {
    return "Type a collection name first.";
  }
  return "The search failed. Nothing was fetched.";
}

function renderSearchResults(body) {
  els.searchResults.innerHTML = "";
  if (!body.results.length) {
    els.searchResults.hidden = true;
    els.nameStatus.hidden = false;
    els.nameStatus.classList.add("is-empty");
    els.nameStatus.textContent =
      `No CC0 match for that name in ${body.provider_name}'s API. ` +
      "Try the other museum, or use the Google search below to look further afield.";
    return;
  }
  els.nameStatus.hidden = true;
  els.searchResults.hidden = false;
  for (const record of body.results) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "result-candidate";
    const meta = [
      record.catalogue_number,
      record.object_date,
      String(record.medium || "").slice(0, 70),
    ].filter(Boolean).join(" · ");
    const flag = record.missing && record.missing.length ? " · incomplete" : "";
    card.innerHTML =
      `<b>${escapeHtml(record.title)}</b>` +
      `<small>${escapeHtml(meta)}${flag}</small>` +
      `<span class="source-tag web">Web · ${escapeHtml(body.provider_name)} open access API (CC0)</span>`;
    card.addEventListener("click", () => {
      // Drafting a candidate is just a live fetch with known coordinates.
      fetchLive({ provider: body.provider, objectId: String(record.object_id) });
    });
    els.searchResults.appendChild(card);
  }
}

async function searchByName() {
  const name = els.nameInput.value.trim();
  if (!name) {
    els.nameStatus.hidden = false;
    els.nameStatus.classList.remove("is-empty");
    els.nameStatus.textContent = "Type a collection name first — for example: Wheat Field with Cypresses.";
    els.nameInput.focus();
    return;
  }
  const token = ++state.token;
  setBusy(els.nameSearchButton, true, "Searching…");
  els.nameStatus.hidden = true;
  els.searchResults.hidden = true;
  try {
    const body = await post("/api/search", {
      provider: els.searchProvider.value,
      name,
    });
    if (token !== state.token) return;
    renderSearchResults(body);
  } catch (error) {
    if (token !== state.token) return;
    els.searchResults.hidden = true;
    els.nameStatus.hidden = false;
    els.nameStatus.classList.remove("is-empty");
    els.nameStatus.textContent = searchErrorMessage(error);
  } finally {
    if (token === state.token) setBusy(els.nameSearchButton, false);
  }
}

async function ask() {
  const question = els.askInput.value.trim();
  if (!question) {
    els.askInput.focus();
    return;
  }
  await draft({ question });
  els.askInput.select();
}

// --------------------------------------------------------- structured intro

// The summary's source tag: AI only when a requested rewrite was actually
// applied; the offline renderer is deterministic, so it gets its own label.
function summaryTag(result) {
  const block = result.llm;
  if (block && block.requested && block.applied) {
    return `<span class="source-tag ai">AI generated · ${escapeHtml(block.model)}</span>`;
  }
  if (result.status === "refused") {
    return '<span class="source-tag refused">Refused · nothing invented</span>';
  }
  return '<span class="source-tag offline">Offline renderer · record-grounded</span>';
}

function renderIntro(result) {
  const record = state.selected;
  if (!record) return;
  els.introHint.hidden = true;

  const webTag = `<span class="source-tag web">Web · ${escapeHtml(state.source.label)}</span>`;
  const rows = [
    ["Title", record.title],
    ["Object date", record.object_date],
    ["Medium", record.medium],
    ["Place or culture", record.place_or_culture],
    ["Credit line", record.credit_line],
  ];
  els.introList.innerHTML = rows
    .map(([key, value]) => {
      const empty = !String(value || "").trim();
      return (
        `<div class="intro-row">` +
        `<span class="intro-key">${key}</span>` +
        `<span class="intro-value${empty ? " is-missing" : ""}">${empty ? "— not in the record —" : escapeHtml(value)}</span>` +
        webTag +
        `</div>`
      );
    })
    .join("");

  els.summaryTag.innerHTML = summaryTag(result);
  els.labelText.textContent = result.status === "refused" ? result.reason_text : result.label;
}

function renderModelNote(result) {
  const block = result.llm;
  if (!block || !block.requested) {
    els.modelNote.hidden = true;
    els.modelNote.textContent = "";
    return;
  }
  els.modelNote.hidden = false;
  if (block.applied) {
    els.modelNote.textContent =
      `Model rewrite accepted (${block.model}, ${block.mode}) · ${result.word_count} words`;
    return;
  }
  els.modelNote.textContent =
    `Model rewrite discarded (${block.reason}) · the offline draft is shown instead, ` +
    `because a rewrite is never printed unchecked`;
}

function renderResult(result) {
  const refused = result.status === "refused";
  els.resultStatus.textContent = refused ? "REFUSED" : "DRAFTED";
  els.resultStatus.classList.toggle("refused", refused);
  els.resultCard.classList.toggle("refused", refused);
  els.resultTitle.textContent = refused ? "Refusal" : "Structured introduction";
  renderIntro(result);
  renderModelNote(result);

  els.claimList.innerHTML = refused
    ? `<span class="claim-tag">Reason · ${escapeHtml(result.reason)}</span>`
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
        .map(
          (citation) =>
            `<span class="citation-tag"><span class="tag-icon">${ICONS.citation}</span>` +
            `${escapeHtml(citation.value_span)}</span>`,
        )
        .join("");

  if (refused) {
    els.score.textContent = "0";
    els.score.style.color = "var(--red)";
    els.scoreLabel.textContent = "no claims emitted · refused by design";
    els.shield.innerHTML = ICONS.warn;
    els.shield.classList.add("is-bad");
    els.checkList.innerHTML =
      `<div class="check-row"><span class="check-icon is-bad">${ICONS.warn}</span>` +
      `<div><b>No label produced</b><small>${escapeHtml(result.reason_text)}</small></div></div>`;
    return;
  }

  const checks = result.checks;
  const passed = CHECK_ORDER.filter(([key]) => checks[key].passed).length;
  els.score.textContent = `${passed}/4`;
  els.score.style.color = passed === 4 ? "var(--teal)" : "var(--red)";
  els.scoreLabel.textContent = `checks passed · ${checks.word_count} words · ${checks.average_sentence_length} words per sentence`;
  els.shield.innerHTML = passed === 4 ? ICONS.check : ICONS.warn;
  els.shield.classList.toggle("is-bad", passed !== 4);

  els.checkList.innerHTML = CHECK_ORDER.map(([key, title]) => {
    const check = checks[key];
    const ok = check.passed;
    return (
      `<div class="check-row"><span class="check-icon${ok ? "" : " is-bad"}">${ok ? ICONS.check : ICONS.warn}</span>` +
      `<div><b>${title}</b><small>${escapeHtml(check.detail)}</small></div></div>`
    );
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

function renderProviders(providers) {
  state.providers = Object.fromEntries(providers.map((p) => [p.id, p]));
  els.liveProvider.innerHTML = providers
    .map((p) => `<option value="${p.id}">${escapeHtml(p.name)}</option>`)
    .join("");
  els.searchProvider.innerHTML = els.liveProvider.innerHTML;
  els.liveExamples.innerHTML = providers
    .map((p) =>
      p.examples
        .map(
          (id) =>
            `<button class="chip" type="button" data-provider="${p.id}" data-id="${id}">` +
            `${escapeHtml(p.name.split(",")[0].replace(/^The /, ""))} · ${id}</button>`,
        )
        .join(""),
    )
    .join("");
  updateGoogleLink();
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
    renderProviders(data.live_providers || []);

    els.metricRecords.textContent = String(data.corpus.record_count);
    const prov = data.provenance || {};
    els.provenanceLine.innerHTML =
      `Corpus <b>${escapeHtml(data.corpus.name)}</b> · v${escapeHtml(data.corpus.version)} · ` +
      `${escapeHtml(data.corpus.license)} · ${data.corpus.record_count} records · ` +
      `sha256 <code>${escapeHtml(data.corpus.checksum.slice(0, 12))}</code> · ` +
      `source register: ${prov.registered ? `${escapeHtml(prov.id)} · ai input ${prov.ai_input ? "yes" : "no"}` : "unregistered"}`;
    els.footerMeta.textContent =
      `${data.corpus.name} · v${data.corpus.version} · sha256 ${data.corpus.checksum.slice(0, 12)}`;

    showBanner(false);
    setStatus("Pipeline connected", true);
    fillRecord(state.records.find((record) => !record.missing.length) || state.records[0]);
    state.initial = els.select.value;
    await draft();
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

els.askButton.addEventListener("click", ask);
els.askInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    ask();
  }
});

els.liveFetchButton.addEventListener("click", () => fetchLive());
els.liveObjectId.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    fetchLive();
  }
});

els.liveExamples.addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  els.liveProvider.value = chip.dataset.provider;
  els.liveObjectId.value = chip.dataset.id;
  fetchLive();
});

els.nameSearchButton.addEventListener("click", searchByName);
els.nameInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    searchByName();
  }
});
els.nameInput.addEventListener("input", updateGoogleLink);
els.searchProvider.addEventListener("change", updateGoogleLink);

boot();
