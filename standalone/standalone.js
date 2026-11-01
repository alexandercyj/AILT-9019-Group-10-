/* Standalone view over a precomputed run of the pipeline.
 *
 * This file computes no labels, no claims, no citations and no checks. Every one of
 * those was produced by labeldesk at build time (tools/build_standalone.py) and is
 * embedded above as JSON. What runs here is presentation, plus two lookups that are
 * pure functions of the embedded data:
 *
 *   1. is this catalogue number in this corpus?      -> array membership
 *   2. does this question contain an out-of-scope term? -> substring test over the
 *      term list the build copied out of labeldesk.pipeline
 *
 * Both are the same decisions the CLI makes, made over data the build embedded, so
 * the page cannot disagree with the pipeline about a record. It can only fail to
 * contain one, which is why the refusal text is built from the pipeline's own
 * template rather than typed out here.
 */
(function () {
  "use strict";

  var DATA = JSON.parse(document.getElementById("labeldesk-data").textContent);
  var META = DATA.meta;
  var CORPORA = DATA.corpora;

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
    previewNumber: document.getElementById("previewNumber"),
    sourceLink: document.getElementById("sourceLink"),
    sourceBadge: document.getElementById("sourceBadge"),
    resultTitle: document.getElementById("resultTitle"),
    resultStatus: document.getElementById("resultStatus"),
    resultCard: document.getElementById("resultCard"),
    labelText: document.getElementById("labelText"),
    claimList: document.getElementById("claimList"),
    citationStrip: document.getElementById("citationStrip"),
    modelNote: document.getElementById("modelNote"),
    reasonNote: document.getElementById("reasonNote"),
    score: document.getElementById("scoreValue"),
    scoreLabel: document.getElementById("scoreLabel"),
    shield: document.getElementById("shield"),
    checkList: document.getElementById("checkList"),
    command: document.getElementById("commandBlock"),
    corpusVersion: document.getElementById("corpusVersion"),
    corpusCount: document.getElementById("corpusCount"),
    corpusChecksum: document.getElementById("corpusChecksum"),
    corpusSource: document.getElementById("corpusSource"),
    probeNumber: document.getElementById("probeNumber"),
    probeButton: document.getElementById("probeButton"),
    probeQuestion: document.getElementById("probeQuestion"),
    askButton: document.getElementById("askButton"),
    sourceTable: document.getElementById("sourceTable"),
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

  var state = { corpus: DEFAULT_CORPUS, number: null, mode: "offline" };

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

  function recordFor(number) {
    var list = corpus().records;
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

  function renderCorpusMeta() {
    var entry = corpus();
    var prov = entry.provenance || {};
    els.corpusVersion.textContent = "v" + entry.corpus.version;
    els.corpusCount.textContent = String(entry.corpus.record_count);
    els.corpusChecksum.textContent = String(entry.corpus.checksum).slice(0, 12);
    els.corpusSource.textContent = prov.registered
      ? prov.id + " · " + prov.license + " · ai " + (prov.ai_input ? "yes" : "no")
      : "unregistered · ai no";
    els.sourceBadge.textContent = prov.registered
      ? "Frozen corpus · " + prov.license
      : "Frozen corpus";
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

  function fillRecord(record) {
    FIELDS.forEach(function (pair) {
      var input = document.getElementById(pair[1]);
      var value = record ? record[pair[0]] : "";
      var missing = record && record.missing && record.missing.indexOf(pair[0]) !== -1;
      input.value = value ? value : "— (missing)";
      input.classList.toggle("missing", !!missing);
    });
    els.previewNumber.textContent = record ? record.catalogue_number : "—";
    if (record && record.source_url) {
      els.sourceLink.href = record.source_url;
      els.sourceLink.textContent = "Museum record";
      els.sourceLink.removeAttribute("aria-disabled");
    } else {
      els.sourceLink.href = "#";
      els.sourceLink.textContent = "No record URL";
      els.sourceLink.setAttribute("aria-disabled", "true");
    }
  }

  function commandFor(number) {
    var entry = corpus();
    var parts = ["python3 -m labeldesk", '"' + number + '"'];
    if (entry.alias !== "primary") parts.push("--corpus " + entry.alias);
    if (state.mode === "replay") parts.push("--llm --replay");
    return parts.join(" ");
  }

  // ------------------------------------------------------------------ results

  function resetPanels() {
    els.claimList.innerHTML = "";
    els.citationStrip.innerHTML = "";
    els.checkList.innerHTML = "";
    els.modelNote.hidden = true;
    els.modelNote.textContent = "";
    els.reasonNote.hidden = true;
    els.reasonNote.textContent = "";
  }

  function renderChecks(checks) {
    if (!checks) {
      els.score.textContent = "—";
      els.scoreLabel.textContent = "refused before any check";
      els.shield.textContent = "✕";
      els.shield.style.color = "var(--red)";
      els.shield.style.background = "var(--red-soft)";
      els.checkList.innerHTML =
        '<div class="check-row"><span class="check-icon" style="background:var(--red)">✕</span>' +
        "<div><b>Not run</b><small>A refusal produces no label, so there is nothing to check.</small></div></div>";
      return;
    }
    els.score.textContent = Math.round(checks.claim_precision * 100) + "%";
    els.scoreLabel.textContent = checks.passed ? "all four checks pass" : "a check failed";
    els.shield.textContent = checks.passed ? "✓" : "✕";
    els.shield.style.color = checks.passed ? "var(--teal)" : "var(--red)";
    els.shield.style.background = checks.passed ? "var(--teal-soft)" : "var(--red-soft)";
    els.checkList.innerHTML = CHECK_ORDER.map(function (row) {
      var check = checks[row[0]] || {};
      var ok = !!check.passed;
      return (
        '<div class="check-row">' +
        '<span class="check-icon"' + (ok ? "" : ' style="background:var(--red)"') + ">" +
        (ok ? "✓" : "✕") + "</span>" +
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
        '<span class="citation-tag">' + escapeHtml(citation.field) + " → " +
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
    els.resultTitle.textContent = "Grounded draft";
    els.resultStatus.textContent = "DRAFTED · " + result.word_count + " words";
    els.resultStatus.className = "result-status drafted";
    els.resultCard.className = "result-card";
    els.labelText.textContent = result.label;
    renderClaims(result);
    renderChecks(result.checks);
    renderModelNote(result.llm);
    setNote(els.reasonNote, "");
    els.command.textContent = commandFor(number);
  }

  function showRefused(result, number) {
    els.resultTitle.textContent = "Refused";
    els.resultStatus.textContent = "REFUSED · " + result.reason;
    els.resultStatus.className = "result-status refused";
    els.resultCard.className = "result-card refused";
    els.labelText.textContent = "No label was drafted.";
    els.claimList.innerHTML = "";
    els.citationStrip.innerHTML = "";
    renderChecks(null);
    setNote(els.modelNote, "");
    setNote(els.reasonNote, result.reason_text);
    els.command.textContent = commandFor(number);
  }

  function render(result, number) {
    if (!result) {
      els.resultTitle.textContent = "Not in this snapshot";
      els.resultStatus.textContent = "NO RESULT";
      els.resultStatus.className = "result-status refused";
      els.labelText.textContent = "This build has no result for that record.";
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
    var record = recordFor(number);
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

  // ------------------------------------------------------------------ sources

  function renderSourceTable() {
    var rows = ['<thead><tr><th>source</th><th>robots</th><th>licence</th><th>ai</th><th>decision</th></tr></thead><tbody>'];
    META.sources.forEach(function (source) {
      var status = source.decision.status;
      rows.push(
        '<tr class="' + (status === "refused" ? "is-refused" : "") + '">' +
        "<td>" + escapeHtml(source.id) + "</td>" +
        "<td>" + escapeHtml(source.robots.verdict) + "</td>" +
        "<td>" + escapeHtml(source.license.id) + "</td>" +
        "<td>" + (source.policy.ai_input ? "yes" : "no") + "</td>" +
        '<td><span class="tag ' + escapeHtml(status) + '">' + escapeHtml(status.replace(/_/g, " ")) +
        "</span></td></tr>"
      );
    });
    rows.push("</tbody>");
    els.sourceTable.innerHTML = rows.join("");
  }

  // ------------------------------------------------------------------ wiring

  els.tabs.addEventListener("click", function (event) {
    var button = event.target.closest(".corpus-tab");
    if (!button) return;
    selectCorpus(Number(button.getAttribute("data-index")));
  });

  els.select.addEventListener("change", function () {
    var record = recordFor(els.select.value);
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

  renderSourceTable();
  selectCorpus(DEFAULT_CORPUS);
})();
