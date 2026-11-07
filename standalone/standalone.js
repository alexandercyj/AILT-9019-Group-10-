/* Standalone view over a precomputed run of the pipeline.
 *
 * This file computes no labels, no claims, no citations and no checks. Every one of
 * those was produced by labeldesk at build time (tools/build_standalone.py) and is
 * embedded above as JSON. What runs here is presentation, plus lookups that are
 * pure functions of the embedded data:
 *
 *   1. is this catalogue number in this corpus?        -> array membership
 *   2. does this question contain an out-of-scope term? -> substring test over the
 *      term list the build copied out of labeldesk.pipeline
 *   3. which embedded records match a collection name?  -> substring test over the
 *      embedded titles, so the name search is as honest as the rest of the page
 *
 * All are the same decisions the CLI makes, made over data the build embedded, so
 * the page cannot disagree with the pipeline about a record. It can only fail to
 * contain one, which is why the refusal text is built from the pipeline's own
 * template rather than typed out here.
 *
 * The page also carries the source contract: every part of the structured
 * introduction is tagged with where it came from — web source for field values
 * copied verbatim from the museum record, offline renderer for the deterministic
 * draft, AI generated for a recorded model rewrite that passed the same checks.
 */
(function () {
  "use strict";

  var DATA = JSON.parse(document.getElementById("labeldesk-data").textContent);
  var META = DATA.meta;
  var CORPORA = DATA.corpora;

  // Icons are inline SVG so buttons and badges render the same on every
  // platform — no font glyphs that can fall back to a mismatched sticker.
  var ICONS = {
    "arrow-right":
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.5 8h10"/><path d="M9 3.5 13.5 8 9 12.5"/></svg>',
    citation:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 3v7a3 3 0 0 0 3 3h7"/></svg>',
    check:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3.5 8.5 6.5 11.5 12.5 4.5"/></svg>',
    warn:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M8 4v5.5"/><circle cx="8" cy="12.2" r="1.1" fill="currentColor" stroke="none"/></svg>'
  };

  Array.prototype.forEach.call(document.querySelectorAll("[data-icon]"), function (slot) {
    slot.innerHTML = ICONS[slot.getAttribute("data-icon")] || "";
  });

  var CHECK_ORDER = [
    ["field_existence", "Field existence", "Every claim cites a supplied field."],
    ["value_containment", "Value containment", "Every claim stays inside its cited value."],
    ["citation_resolution", "Citation resolution", "Printed citations resolve to the record."],
    ["readability", "Readability", "60–80 words, short sentences."]
  ];

  var FIELDS = [
    ["title", "fieldTitle"],
    ["object_date", "fieldDate"],
    ["medium", "fieldMedium"],
    ["place_or_culture", "fieldCulture"],
    ["credit_line", "fieldCredit"]
  ];

  var els = {
    status: document.getElementById("serverStatus"),
    tabs: document.getElementById("corpusTabs"),
    select: document.getElementById("catalogueSelect"),
    form: document.getElementById("recordForm"),
    draftButton: document.getElementById("draftButton"),
    refusalButton: document.getElementById("refusalButton"),
    resetButton: document.getElementById("resetButton"),
    llmToggle: document.getElementById("llmToggle"),
    plateInitials: document.getElementById("plateInitials"),
    previewNumber: document.getElementById("previewNumber"),
    sourceLink: document.getElementById("sourceLink"),
    sourceBadge: document.getElementById("sourceBadge"),
    provenanceLine: document.getElementById("provenanceLine"),
    resultTitle: document.getElementById("resultTitle"),
    resultStatus: document.getElementById("resultStatus"),
    resultCard: document.getElementById("resultCard"),
    introHint: document.getElementById("introHint"),
    introList: document.getElementById("introList"),
    summaryTag: document.getElementById("summaryTag"),
    labelText: document.getElementById("labelText"),
    claimList: document.getElementById("claimList"),
    citationStrip: document.getElementById("citationStrip"),
    modelNote: document.getElementById("modelNote"),
    reasonNote: document.getElementById("reasonNote"),
    score: document.getElementById("scoreValue"),
    scoreLabel: document.getElementById("scoreLabel"),
    shield: document.getElementById("shield"),
    checkList: document.getElementById("checkList"),
    probeNumber: document.getElementById("probeNumber"),
    probeButton: document.getElementById("probeButton"),
    probeQuestion: document.getElementById("probeQuestion"),
    askButton: document.getElementById("askButton"),
    nameInput: document.getElementById("nameInput"),
    nameSearchButton: document.getElementById("nameSearchButton"),
    nameStatus: document.getElementById("nameStatus"),
    searchResults: document.getElementById("searchResults"),
    googleLink: document.getElementById("googleLink"),
    metricRecords: document.getElementById("metricRecords"),
    footerCorpora: document.getElementById("footerCorpora"),
    footerHash: document.getElementById("footerHash")
  };

  // Open on the corpus the README's examples use, not whichever sorts first.
  var DEFAULT_CORPUS = (function () {
    for (var i = 0; i < CORPORA.length; i += 1) {
      if (CORPORA[i].alias === "primary") return i;
    }
    return 0;
  })();

  var state = {
    corpus: DEFAULT_CORPUS,
    number: null,
    mode: "offline",
    // How the current record is labelled in the structured introduction.
    sourceLabel: "Frozen corpus"
  };

  // ------------------------------------------------------------------ helpers

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function corpus() {
    return CORPORA[state.corpus];
  }

  function currentRecord() {
    return recordIn(corpus(), state.number);
  }

  function recordIn(entry, number) {
    var list = entry.records;
    for (var i = 0; i < list.length; i += 1) {
      if (list[i].catalogue_number === number) return list[i];
    }
    return null;
  }

  function fill(template, values) {
    return String(template).replace(/\{(\w+)\}/g, function (whole, key) {
      return Object.prototype.hasOwnProperty.call(values, key) ? values[key] : whole;
    });
  }

  function setNote(node, text) {
    if (text) {
      node.textContent = text;
      node.hidden = false;
    } else {
      node.textContent = "";
      node.hidden = true;
    }
  }

  // ------------------------------------------------------------------ chrome

  function renderTabs() {
    els.tabs.innerHTML = CORPORA.map(function (entry, index) {
      var selected = index === state.corpus ? "true" : "false";
      var count = entry.corpus.record_count;
      return (
        '<button type="button" class="corpus-tab" role="tab" aria-selected="' + selected +
        '" data-index="' + index + '">' + escapeHtml(entry.alias) +
        "<small>" + count + " records · " + escapeHtml(entry.provenance.id || "unregistered") +
        "</small></button>"
      );
    }).join("");
  }

  function sourceLabelFor(entry) {
    var prov = entry.provenance || {};
    return prov.registered
      ? "Frozen corpus · " + prov.id + " · " + prov.license
      : "Frozen corpus · unregistered";
  }

  function renderCorpusMeta() {
    var entry = corpus();
    var prov = entry.provenance || {};
    els.sourceBadge.textContent = prov.registered
      ? "Frozen corpus · " + prov.license
      : "Frozen corpus";
    state.sourceLabel = sourceLabelFor(entry);
    els.provenanceLine.innerHTML =
      "Corpus <b>" + escapeHtml(entry.corpus.name) + "</b> · v" + escapeHtml(entry.corpus.version) +
      " · " + escapeHtml(entry.corpus.license) + " · " + entry.corpus.record_count + " records" +
      " · sha256 <code>" + escapeHtml(String(entry.corpus.checksum).slice(0, 12)) + "</code>" +
      " · source register: " + (prov.registered
        ? escapeHtml(prov.id) + " · ai input " + (prov.ai_input ? "yes" : "no")
        : "unregistered");
  }

  function renderSelect() {
    els.select.innerHTML = corpus().records.map(function (record) {
      var flag = record.missing && record.missing.length ? " · incomplete" : "";
      return (
        '<option value="' + escapeHtml(record.catalogue_number) + '">' +
        escapeHtml(record.catalogue_number) + " — " + escapeHtml(record.title) + flag +
        "</option>"
      );
    }).join("");
  }

  function plateInitials(title) {
    var words = String(title || "")
      .split(/\s+/)
      .map(function (word) { return word.replace(/[^A-Za-zÀ-ÿ0-9]/g, ""); })
      .filter(function (word) { return word && !/^(a|an|the|of|and)$/i.test(word); });
    if (!words.length) return "?";
    if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
    return (words[0][0] + words[1][0]).toUpperCase();
  }

  function fillRecord(record) {
    FIELDS.forEach(function (pair) {
      var input = document.getElementById(pair[1]);
      var value = record ? record[pair[0]] : "";
      var missing = record && record.missing && record.missing.indexOf(pair[0]) !== -1;
      input.value = value ? value : "— (missing)";
      input.classList.toggle("missing", !!missing);
    });
    els.plateInitials.textContent = plateInitials(record ? record.title : "");
    els.previewNumber.textContent = record ? record.catalogue_number : "—";
    if (record && record.source_url) {
      els.sourceLink.href = record.source_url;
      els.sourceLink.textContent = "Open the museum record";
      els.sourceLink.removeAttribute("aria-disabled");
    } else {
      els.sourceLink.href = "#";
      els.sourceLink.textContent = "No museum link in the record";
      els.sourceLink.setAttribute("aria-disabled", "true");
    }
  }

  // --------------------------------------------------------- structured intro

  // The summary's source tag: AI only for a recorded rewrite that was actually
  // applied; the offline renderer is deterministic, so it gets its own label.
  function summaryTagFor(result) {
    var block = result.llm;
    if (block && block.requested && block.applied) {
      return '<span class="source-tag ai">AI generated · ' + escapeHtml(block.model) + "</span>";
    }
    if (result.status === "refused") {
      return '<span class="source-tag refused">Refused · nothing invented</span>';
    }
    return '<span class="source-tag offline">Offline renderer · record-grounded</span>';
  }

  function renderIntro(result) {
    var record = currentRecord();
    if (!record) return;
    els.introHint.hidden = true;
    var webTag = '<span class="source-tag web">Web · ' + escapeHtml(state.sourceLabel) + "</span>";
    var rows = [
      ["Title", record.title],
      ["Object date", record.object_date],
      ["Medium", record.medium],
      ["Place or culture", record.place_or_culture],
      ["Credit line", record.credit_line]
    ];
    els.introList.innerHTML = rows.map(function (row) {
      var empty = !String(row[1] == null ? "" : row[1]).trim();
      return (
        '<div class="intro-row">' +
        '<span class="intro-key">' + row[0] + "</span>" +
        '<span class="intro-value' + (empty ? " is-missing" : "") + '">' +
        (empty ? "— not in the record —" : escapeHtml(row[1])) + "</span>" +
        webTag + "</div>"
      );
    }).join("");
    els.summaryTag.innerHTML = summaryTagFor(result);
  }

  // ------------------------------------------------------------------ results

  function renderChecks(checks) {
    if (!checks) {
      els.score.textContent = "—";
      els.scoreLabel.textContent = "refused before any check";
      els.shield.innerHTML = ICONS.warn;
      els.shield.classList.add("is-bad");
      els.checkList.innerHTML =
        '<div class="check-row"><span class="check-icon is-bad">' + ICONS.warn + "</span>" +
        "<div><b>Not run</b><small>A refusal produces no label, so there is nothing to check.</small></div></div>";
      return;
    }
    els.score.textContent = Math.round(checks.claim_precision * 100) + "%";
    els.scoreLabel.textContent = checks.passed ? "all four checks pass" : "a check failed";
    els.shield.innerHTML = checks.passed ? ICONS.check : ICONS.warn;
    els.shield.classList.toggle("is-bad", !checks.passed);
    els.checkList.innerHTML = CHECK_ORDER.map(function (row) {
      var check = checks[row[0]] || {};
      var ok = !!check.passed;
      return (
        '<div class="check-row">' +
        '<span class="check-icon' + (ok ? "" : " is-bad") + '">' +
        (ok ? ICONS.check : ICONS.warn) + "</span>" +
        "<div><b>" + row[1] + "</b><small>" + escapeHtml(check.detail || row[2]) + "</small></div>" +
        "</div>"
      );
    }).join("");
  }

  function renderClaims(result) {
    els.claimList.innerHTML = (result.claims || []).map(function (claim) {
      return (
        '<span class="claim-tag">' + escapeHtml(claim.id) +
        '<span class="claim-field">' + escapeHtml(claim.source_field) + "</span></span>"
      );
    }).join("");
    els.citationStrip.innerHTML = (result.citations || []).map(function (citation) {
      return (
        '<span class="citation-tag"><span class="tag-icon">' + ICONS.citation + "</span>" +
        escapeHtml(citation.value_span) + "</span>"
      );
    }).join("");
  }

  function renderModelNote(block) {
    if (!block || !block.requested) {
      setNote(els.modelNote, "");
      return;
    }
    if (block.applied) {
      setNote(
        els.modelNote,
        "Model rewrite accepted · " + block.model + " · " + block.mode +
        ". The label above is the rewrite; it passed the same four checks as the offline draft."
      );
      return;
    }
    if (block.reason === "source_policy") {
      setNote(
        els.modelNote,
        "Refused before sending: source_policy. Nothing was sent to a model — the source's terms " +
        "do not permit it. The offline draft is shown."
      );
      return;
    }
    setNote(
      els.modelNote,
      "Rewrite discarded: " + block.reason + ". The offline draft is shown instead " +
      "(no-regression rule), so turning the model on can cost prose, never a fact."
    );
  }

  function showDrafted(result, number) {
    els.resultTitle.textContent = "Structured introduction";
    els.resultStatus.textContent = "DRAFTED · " + result.word_count + " words";
    els.resultStatus.className = "result-status drafted";
    els.resultCard.className = "result-card";
    els.labelText.textContent = result.label;
    renderIntro(result);
    renderClaims(result);
    renderChecks(result.checks);
    renderModelNote(result.llm);
    setNote(els.reasonNote, "");
  }

  function showRefused(result, number) {
    els.resultTitle.textContent = "Refusal";
    els.resultStatus.textContent = "REFUSED · " + result.reason;
    els.resultStatus.className = "result-status refused";
    els.resultCard.className = "result-card refused";
    els.labelText.textContent = "No label was drafted.";
    els.claimList.innerHTML = "";
    els.citationStrip.innerHTML = "";
    renderIntro(result);
    renderChecks(null);
    setNote(els.modelNote, "");
    setNote(els.reasonNote, result.reason_text);
  }

  function render(result, number) {
    if (!result) {
      els.resultTitle.textContent = "Not in this snapshot";
      els.resultStatus.textContent = "NO RESULT";
      els.resultStatus.className = "result-status refused";
      els.labelText.textContent = "This build has no result for that record.";
      els.introList.innerHTML = "";
      return;
    }
    if (result.status === "refused") {
      showRefused(result, number);
    } else {
      showDrafted(result, number);
    }
  }

  // ------------------------------------------------------------------ actions

  function draftSelected() {
    var number = els.select.value;
    var entry = corpus();
    var bundle = entry.results[number];
    if (!bundle) {
      render(null, number);
      return;
    }
    state.number = number;
    var result = state.mode === "replay" ? bundle.replay : bundle.offline;
    render(result, number);
  }

  function lookupUnknown(number) {
    var count = corpus().corpus.record_count;
    render(
      {
        status: "refused",
        reason: "out_of_corpus",
        reason_text: fill(META.reason_text.out_of_corpus, {
          catalogue_number: number,
          count: count
        }),
        label: null
      },
      number
    );
  }

  function probeNumber() {
    var number = els.probeNumber.value.trim();
    if (!number) return;
    var record = recordIn(corpus(), number);
    if (!record) {
      lookupUnknown(number);
      return;
    }
    els.select.value = number;
    draftSelected();
  }

  function askQuestion() {
    var question = els.probeQuestion.value;
    if (!question.trim()) return;
    var lowered = question.toLowerCase();
    var term = null;
    for (var i = 0; i < META.out_of_scope_terms.length; i += 1) {
      if (lowered.indexOf(META.out_of_scope_terms[i]) !== -1) {
        term = META.out_of_scope_terms[i];
        break;
      }
    }
    if (term) {
      render(
        {
          status: "refused",
          reason: "out_of_scope",
          reason_text: fill(META.reason_text.out_of_scope, { term: term }),
          label: null
        },
        els.select.value
      );
      return;
    }
    // In scope: the CLI drafts the selected record, so show that same result.
    draftSelected();
  }

  function testRefusal() {
    var list = corpus().records;
    for (var i = 0; i < list.length; i += 1) {
      if (list[i].missing && list[i].missing.length) {
        els.select.value = list[i].catalogue_number;
        fillRecord(list[i]);
        draftSelected();
        return;
      }
    }
    lookupUnknown("99.99.99");
  }

  function selectCorpus(index) {
    state.corpus = index;
    renderTabs();
    renderCorpusMeta();
    renderSelect();
    var first = corpus().records.filter(function (record) {
      return !(record.missing && record.missing.length);
    })[0] || corpus().records[0];
    els.select.value = first.catalogue_number;
    fillRecord(first);
    draftSelected();
  }

  // ---------------------------------------------------------------- name search

  // A pure lookup over the embedded records: no network, no API, no invention.
  // Matching is a case-insensitive substring test over the embedded titles, so
  // the page can only find records the pipeline actually ran on.
  function updateGoogleLink() {
    var name = els.nameInput.value.trim();
    els.googleLink.href = "https://www.google.com/search?q=" +
      encodeURIComponent(name ? '"' + name + '" museum collection' : "museum collection");
  }

  function searchCorporaByName() {
    var name = els.nameInput.value.trim().toLowerCase();
    if (!name) {
      els.nameStatus.hidden = false;
      els.nameStatus.classList.remove("is-empty");
      els.nameStatus.textContent = "Type a collection name first — for example: Wheat Field with Cypresses.";
      els.nameInput.focus();
      return;
    }
    var matches = [];
    CORPORA.forEach(function (entry) {
      entry.records.forEach(function (record) {
        if (String(record.title || "").toLowerCase().indexOf(name) !== -1) {
          matches.push({ entry: entry, record: record });
        }
      });
    });
    els.nameStatus.hidden = true;
    if (!matches.length) {
      els.searchResults.hidden = true;
      els.searchResults.innerHTML = "";
      els.nameStatus.hidden = false;
      els.nameStatus.classList.add("is-empty");
      els.nameStatus.textContent =
        "No embedded record has that name in its title. The frozen corpora are all this " +
        "offline page can search — use the Google link below to look further afield.";
      return;
    }
    els.searchResults.hidden = false;
    els.searchResults.innerHTML = "";
    matches.slice(0, 6).forEach(function (match) {
      var card = document.createElement("button");
      card.type = "button";
      card.className = "result-candidate";
      var meta = [
        match.record.catalogue_number,
        match.record.object_date,
        String(match.record.medium || "").slice(0, 70)
      ].filter(Boolean).join(" · ");
      var flag = match.record.missing && match.record.missing.length ? " · incomplete" : "";
      card.innerHTML =
        "<b>" + escapeHtml(match.record.title) + "</b>" +
        "<small>" + escapeHtml(meta) + flag + "</small>" +
        '<span class="source-tag web">Web · ' + escapeHtml(sourceLabelFor(match.entry)) + "</span>";
      card.addEventListener("click", function () {
        selectCorpus(CORPORA.indexOf(match.entry));
        els.select.value = match.record.catalogue_number;
        fillRecord(match.record);
        draftSelected();
      });
      els.searchResults.appendChild(card);
    });
  }

  // ------------------------------------------------------------------ wiring

  els.tabs.addEventListener("click", function (event) {
    var button = event.target.closest(".corpus-tab");
    if (!button) return;
    selectCorpus(Number(button.getAttribute("data-index")));
  });

  els.select.addEventListener("change", function () {
    var record = recordIn(corpus(), els.select.value);
    fillRecord(record);
    draftSelected();
  });

  els.form.addEventListener("submit", function (event) {
    event.preventDefault();
    draftSelected();
  });

  els.refusalButton.addEventListener("click", testRefusal);
  els.probeButton.addEventListener("click", probeNumber);
  els.askButton.addEventListener("click", askQuestion);
  els.nameSearchButton.addEventListener("click", searchCorporaByName);
  els.nameInput.addEventListener("input", updateGoogleLink);
  els.nameInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      searchCorporaByName();
    }
  });
  els.probeNumber.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      probeNumber();
    }
  });
  els.probeQuestion.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      askQuestion();
    }
  });

  els.llmToggle.addEventListener("change", function () {
    state.mode = els.llmToggle.checked ? "replay" : "offline";
    draftSelected();
  });

  els.resetButton.addEventListener("click", function () {
    els.llmToggle.checked = false;
    state.mode = "offline";
    els.probeNumber.value = "";
    els.probeQuestion.value = "";
    els.nameInput.value = "";
    els.searchResults.hidden = true;
    els.searchResults.innerHTML = "";
    els.nameStatus.hidden = true;
    updateGoogleLink();
    selectCorpus(DEFAULT_CORPUS);
  });

  els.status.innerHTML = '<span class="status-dot"></span>Standalone · no server';

  var totalRecords = CORPORA.reduce(function (sum, entry) {
    return sum + entry.corpus.record_count;
  }, 0);
  els.metricRecords.textContent = String(totalRecords);
  els.footerCorpora.textContent = CORPORA.map(function (entry) {
    return entry.corpus.name;
  }).join(" · ");
  els.footerHash.textContent = "prompt sha256 " + String(META.prompt_sha256).slice(0, 12) +
    " · " + META.labeldesk_version;
  updateGoogleLink();
  selectCorpus(DEFAULT_CORPUS);
})();
