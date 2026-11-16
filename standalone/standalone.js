(function () {
  "use strict";
  var DATA = JSON.parse(document.getElementById("labeldesk-data").textContent);
  var CORPORA = DATA.corpora;
  var NAMES = { primary: "The Metropolitan Museum of Art", egyptian: "The Met · Egyptian Art", cleveland: "The Cleveland Museum of Art" };
  var state = { corpus: 0, record: null };
  var els = {};
  [
    "corpusTabs", "standaloneSearchForm", "standaloneSearchInput", "standaloneSearchSection",
    "standaloneSearchMessage", "standaloneSearchResults", "standaloneArticle", "standaloneBreadcrumb",
    "standaloneRecordSelect", "standaloneImage", "standaloneImageEmpty", "standaloneImageCaption",
    "standaloneTitle", "standaloneSubtitle", "standaloneTags", "standaloneSource", "standaloneLabel",
    "standaloneFacts"
  ].forEach(function (id) { els[id] = document.getElementById(id); });
  if (!els.standaloneImage && els.standaloneImageEmpty) {
    var image = document.createElement("img");
    image.id = "standaloneImage";
    image.alt = "";
    image.hidden = true;
    els.standaloneImageEmpty.before(image);
    els.standaloneImage = image;
  }

  function node(tag, className, text) {
    var element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined && text !== null) element.textContent = text;
    return element;
  }

  function safeUrl(value) {
    try {
      var url = new URL(String(value || ""));
      return url.protocol === "https:" ? url.href : "";
    } catch (_) { return ""; }
  }

  function currentCorpus() { return CORPORA[state.corpus]; }
  function currentRecord() {
    return currentCorpus().records.find(function (record) { return record === state.record; });
  }

  function renderTabs() {
    els.corpusTabs.innerHTML = "";
    CORPORA.forEach(function (entry, index) {
      var button = node("button", "corpus-tab", NAMES[entry.alias] || entry.corpus.source);
      button.type = "button";
      button.setAttribute("role", "tab");
      button.setAttribute("aria-selected", index === state.corpus ? "true" : "false");
      button.addEventListener("click", function () { selectCorpus(index); });
      els.corpusTabs.appendChild(button);
    });
  }

  function renderPicker() {
    els.standaloneRecordSelect.innerHTML = "";
    currentCorpus().records.forEach(function (record) {
      var option = node("option", "", record.title + (record.object_date ? " · " + record.object_date : ""));
      option.value = record.catalogue_number;
      els.standaloneRecordSelect.appendChild(option);
    });
  }

  function selectCorpus(index) {
    state.corpus = index;
    renderTabs();
    renderPicker();
    var record = currentCorpus().records.find(function (item) { return !item.missing.length; }) || currentCorpus().records[0];
    showRecord(record);
  }

  function showRecord(record) {
    state.record = record;
    els.standaloneRecordSelect.value = record.catalogue_number;
    els.standaloneBreadcrumb.textContent = "Open collections / " + (NAMES[currentCorpus().alias] || currentCorpus().corpus.source);
    els.standaloneTitle.textContent = record.title || "Untitled object";
    els.standaloneSubtitle.textContent = [record.object_date, record.place_or_culture].filter(Boolean).join(" · ");
    els.standaloneTags.innerHTML = "";
    [record.department, record.catalogue_number].filter(Boolean).forEach(function (value) {
      els.standaloneTags.appendChild(node("span", "", value));
    });
    var source = safeUrl(record.source_url);
    els.standaloneSource.hidden = !source;
    if (source) els.standaloneSource.href = source;
    renderImage(record);
    renderFacts(record);
    var bundle = currentCorpus().results[record.catalogue_number];
    var result = bundle && bundle.offline;
    els.standaloneLabel.textContent = (result && result.label)
      ? result.label
      : ((result && result.reason_text) || "This record lacks the fields required for a complete summary. The missing information remains visible in the museum record.");
  }

  function renderImage(record) {
    var url = safeUrl(record.image_url || record.image_thumbnail);
    els.standaloneImage.hidden = !url;
    els.standaloneImageEmpty.hidden = Boolean(url);
    els.standaloneImage.removeAttribute("src");
    els.standaloneImageCaption.textContent = url ? "Object image · Museum open collection" : "No open image is available for this record";
    if (!url) return;
    els.standaloneImage.alt = record.title || "Object image";
    els.standaloneImage.referrerPolicy = "no-referrer";
    els.standaloneImage.onerror = function () {
      els.standaloneImage.hidden = true;
      els.standaloneImageEmpty.hidden = false;
      els.standaloneImageEmpty.querySelector("p").textContent = "The image could not be loaded";
    };
    els.standaloneImage.src = url;
  }

  function renderFacts(record) {
    els.standaloneFacts.innerHTML = "";
    [
      ["Title", record.title], ["Date", record.object_date], ["Medium and technique", record.medium],
      ["Place or culture", record.place_or_culture], ["Accession number", record.catalogue_number],
      ["Credit line", record.credit_line]
    ].forEach(function (pair) {
      var wrap = node("div", "fact-row");
      wrap.appendChild(node("dt", "", pair[0]));
      wrap.appendChild(node("dd", pair[1] ? "" : "missing", pair[1] || "Not supplied by the museum"));
      els.standaloneFacts.appendChild(wrap);
    });
  }

  function renderCard(record, entry) {
    var button = node("button", "object-card");
    button.type = "button";
    var imageWrap = node("span", "card-image");
    var url = safeUrl(record.image_thumbnail || record.image_url);
    if (url) {
      var image = node("img");
      image.src = url;
      image.alt = record.title;
      image.loading = "lazy";
      image.referrerPolicy = "no-referrer";
      image.onerror = function () {
        image.remove();
        imageWrap.appendChild(node("span", "card-no-image", "The image could not be loaded"));
      };
      imageWrap.appendChild(image);
    } else { imageWrap.appendChild(node("span", "card-no-image", "No image available")); }
    button.appendChild(imageWrap);
    var content = node("span", "card-content");
    content.appendChild(node("small", "", NAMES[entry.alias] || entry.corpus.source));
    content.appendChild(node("b", "", record.title));
    content.appendChild(node("span", "card-meta", [record.object_date, record.place_or_culture].filter(Boolean).join(" · ")));
    content.appendChild(node("span", "card-action", "Read object entry →"));
    button.appendChild(content);
    button.addEventListener("click", function () {
      selectCorpus(CORPORA.indexOf(entry));
      showRecord(record);
      els.standaloneSearchSection.hidden = true;
      els.standaloneArticle.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    return button;
  }

  function search(event) {
    if (event) event.preventDefault();
    var query = els.standaloneSearchInput.value.trim().toLowerCase();
    if (!query) { els.standaloneSearchInput.focus(); return; }
    var matches = [];
    CORPORA.forEach(function (entry) {
      entry.records.forEach(function (record) {
        if (String(record.title || "").toLowerCase().indexOf(query) !== -1) matches.push({ record: record, entry: entry });
      });
    });
    els.standaloneSearchSection.hidden = false;
    els.standaloneSearchResults.innerHTML = "";
    matches.slice(0, 12).forEach(function (match) { els.standaloneSearchResults.appendChild(renderCard(match.record, match.entry)); });
    els.standaloneSearchMessage.hidden = Boolean(matches.length);
    els.standaloneSearchMessage.textContent = matches.length ? "" : "No matching title was found in this offline selection. The full encyclopedia can search more collection records and web sources.";
  }

  els.standaloneRecordSelect.addEventListener("change", function () {
    var record = currentCorpus().records.find(function (item) { return item.catalogue_number === els.standaloneRecordSelect.value; });
    if (record) showRecord(record);
  });
  els.standaloneSearchForm.addEventListener("submit", search);
  selectCorpus(0);
})();
