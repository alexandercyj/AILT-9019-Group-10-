const els = Object.fromEntries([
  "searchForm", "searchInput", "providerSelect", "searchButton", "searchSection",
  "searchHeading", "resultCount", "searchMessage", "searchResults", "articleShell",
  "articleBreadcrumb", "objectImage", "imageEmpty", "imageCaption", "articleKind",
  "articleTitle", "articleSubtitle", "articleTags", "museumLink", "researchNotice",
  "articleLead", "articleSections", "conclusionCard", "conclusionText",
  "referencesSection", "referenceList", "factCard", "factList", "processList",
].map((id) => [id, document.getElementById(id)]));

if (!els.objectImage && els.imageEmpty) {
  const image = document.createElement("img");
  image.id = "objectImage";
  image.alt = "";
  image.hidden = true;
  els.imageEmpty.before(image);
  els.objectImage = image;
}

const state = { token: 0, record: null, selection: null, query: "" };

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined && text !== null) element.textContent = text;
  return element;
}

function safeUrl(value) {
  try {
    const url = new URL(String(value));
    return url.protocol === "https:" ? url.href : "";
  } catch {
    return "";
  }
}

async function post(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "request_failed");
  return data;
}

function setSearchMessage(text, kind = "") {
  els.searchMessage.hidden = !text;
  els.searchMessage.className = `search-message${kind ? ` ${kind}` : ""}`;
  els.searchMessage.textContent = text || "";
}

function clearArticle() {
  els.articleShell.hidden = true;
  state.record = null;
  state.selection = null;
}

function showSearchError(error) {
  const messages = {
    upstream_unreachable: "The collection service is temporarily unavailable. Please try again later; web research may still be available.",
    upstream_http: "The museum did not return results. Try different keywords or try again later.",
  };
  setSearchMessage(messages[error.message] || "The search could not be completed. Please try again later.", "error");
}

async function searchObjects(event) {
  if (event) event.preventDefault();
  const query = els.searchInput.value.trim();
  if (!query) {
    els.searchInput.focus();
    return;
  }
  const token = ++state.token;
  state.query = query;
  clearArticle();
  els.searchSection.hidden = false;
  els.searchResults.innerHTML = "";
  els.resultCount.textContent = "";
  els.searchHeading.textContent = `Search results for “${query}”`;
  setSearchMessage("Searching museum open collections…", "loading");
  els.searchButton.disabled = true;
  try {
    const body = await post("/api/search", {
      provider: els.providerSelect.value,
      name: query,
      limit: 4,
    });
    if (token !== state.token) return;
    renderSearchResults(body);
    if (!body.results.length) {
      setSearchMessage("No matching object in the museum search. Web research stays off unless this server was started with --allow-research.", "");
    }
  } catch (error) {
    if (token !== state.token) return;
    showSearchError(error);
  } finally {
    if (token === state.token) els.searchButton.disabled = false;
  }
}

function renderSearchResults(body) {
  els.searchResults.innerHTML = "";
  els.resultCount.textContent = body.results.length ? `${body.results.length} related objects found` : "";
  for (const record of body.results) {
    const button = node("button", "object-card");
    button.type = "button";
    const imageWrap = node("span", "card-image");
    const imageUrl = safeUrl(record.image_thumbnail || record.image_url);
    if (imageUrl) {
      const image = node("img");
      image.src = imageUrl;
      image.alt = record.title || "Object image";
      image.loading = "lazy";
      image.referrerPolicy = "no-referrer";
      image.addEventListener("error", () => {
        image.remove();
        imageWrap.appendChild(node("span", "card-no-image", "No image available"));
      });
      imageWrap.appendChild(image);
    } else {
      imageWrap.appendChild(node("span", "card-no-image", "No image available"));
    }
    button.appendChild(imageWrap);
    const content = node("span", "card-content");
    content.appendChild(node("small", "", record.provider_short_name || record.provider_name));
    content.appendChild(node("b", "", record.title));
    content.appendChild(node("span", "card-meta", [record.object_date, record.place_or_culture].filter(Boolean).join(" · ") || "View collection details"));
    content.appendChild(node("span", "card-action", "Read object entry →"));
    button.appendChild(content);
    button.addEventListener("click", () => selectRecord(record));
    els.searchResults.appendChild(button);
  }
  if (!body.results.length) setSearchMessage("No directly matching collection objects found.", "");
  if (body.errors && body.errors.length && body.results.length) {
    setSearchMessage("Some museums did not respond. The results found so far are shown below.", "warning");
  } else if (body.results.length) {
    setSearchMessage("");
  }
}

function selectRecord(record) {
  state.selection = { provider: record.provider, objectId: record.object_id };
  state.record = record;
  els.searchSection.hidden = true;
  renderRecord(record, record.provider_short_name || record.provider_name);
  els.researchNotice.hidden = false;
  els.researchNotice.className = "research-notice unavailable";
  els.researchNotice.textContent = "Web research is off. This page shows the museum record and does not spend the sponsored quota.";
  els.articleShell.hidden = false;
  els.articleShell.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderRecord(record, providerName) {
  els.articleBreadcrumb.textContent = `Open collections / ${providerName}`;
  els.articleKind.textContent = "MUSEUM OBJECT · CATALOGUE ENTRY";
  els.articleTitle.textContent = record.title || "Untitled object";
  els.articleSubtitle.textContent = [record.object_date, record.place_or_culture].filter(Boolean).join(" · ");
  els.articleTags.innerHTML = "";
  for (const value of [record.department, record.catalogue_number].filter(Boolean)) {
    els.articleTags.appendChild(node("span", "", value));
  }
  renderImage(record);
  const source = safeUrl(record.source_url);
  els.museumLink.hidden = !source;
  if (source) els.museumLink.href = source;
  els.factCard.hidden = false;
  els.factList.innerHTML = "";
  const facts = [
    ["Title", record.title], ["Date", record.object_date], ["Medium and technique", record.medium],
    ["Place or culture", record.place_or_culture], ["Accession number", record.catalogue_number],
    ["Credit line", record.credit_line],
  ];
  for (const [label, value] of facts) {
    const wrap = node("div", "fact-row");
    wrap.appendChild(node("dt", "", label));
    wrap.appendChild(node("dd", value ? "" : "missing", value || "Not supplied by the museum"));
    els.factList.appendChild(wrap);
  }
  els.articleLead.textContent = "";
  els.articleSections.innerHTML = "";
  els.conclusionCard.hidden = true;
  els.referencesSection.hidden = true;
  els.processList.innerHTML = "";
}

function renderImage(record) {
  const url = safeUrl(record.image_url || record.image_thumbnail);
  els.objectImage.hidden = !url;
  els.objectImage.removeAttribute("src");
  els.imageEmpty.hidden = Boolean(url);
  els.imageCaption.textContent = url ? "Object image · Museum open collection" : "No open image is available for this record";
  if (!url) {
    els.imageEmpty.querySelector("p").textContent = "No object image available";
    return;
  }
  els.imageEmpty.querySelector("p").textContent = "Finding the object image";
  els.objectImage.alt = record.title || "Object image";
  els.objectImage.referrerPolicy = "no-referrer";
  els.objectImage.onerror = () => {
    els.objectImage.hidden = true;
    els.imageEmpty.hidden = false;
    els.imageEmpty.querySelector("p").textContent = "The image could not be loaded";
  };
  els.objectImage.src = url;
}

function renderResearchPending() {
  els.researchNotice.hidden = false;
  els.researchNotice.className = "research-notice";
  els.researchNotice.innerHTML = '<span class="loading-mark" aria-hidden="true"></span><div><b>Reading relevant sources</b><p>AI will search and read web pages. Only information traceable to an actual source will appear in the article.</p></div>';
}

async function runResearch(token) {
  if (!state.selection) return;
  try {
    const body = await post("/api/research", {
      provider: state.selection.provider,
      object_id: state.selection.objectId,
      query: state.record.title,
    });
    if (token !== state.token) return;
    if (body.record) renderRecord(body.record, body.provider_short_name || body.provider_name);
    renderResearch(body.research);
  } catch {
    if (token !== state.token) return;
    renderResearch({ status: "unavailable", message: "Web research could not be completed. The museum record and image remain available; please try again later.", steps: [] });
  }
}

async function researchWeb(query, token) {
  clearArticle();
  state.query = query;
  els.articleShell.hidden = false;
  els.factCard.hidden = true;
  els.museumLink.hidden = true;
  els.articleBreadcrumb.textContent = "Web sources / Encyclopedia entry";
  els.articleKind.textContent = "WEB RESEARCH · OPEN SOURCES";
  els.articleTitle.textContent = query;
  els.articleSubtitle.textContent = "Confirming this topic through public web sources";
  els.articleTags.innerHTML = "";
  els.objectImage.hidden = true;
  els.imageEmpty.hidden = false;
  els.imageEmpty.querySelector("p").textContent = "No confirmed open image for this web entry";
  els.imageCaption.textContent = "Images with unclear reuse rights are not used";
  renderResearchPending();
  try {
    const body = await post("/api/research", { query });
    if (token !== state.token) return;
    if (body.research.status === "ready") els.articleTitle.textContent = body.research.title;
    setSearchMessage("");
    renderResearch(body.research);
  } catch {
    if (token !== state.token) return;
    renderResearch({ status: "unavailable", message: "Web research could not be completed. Please try again later or use different keywords.", steps: [] });
  }
}

function renderResearch(result) {
  els.researchNotice.hidden = result.status === "ready";
  els.processList.innerHTML = "";
  for (const step of result.steps || []) {
    const item = node("li");
    item.appendChild(node("b", "", step.title));
    item.appendChild(node("p", "", step.detail));
    els.processList.appendChild(item);
  }
  if (result.status !== "ready") {
    els.researchNotice.className = "research-notice unavailable";
    els.researchNotice.textContent = result.message || "No expanded article was generated for this request.";
    return;
  }
  els.articleLead.textContent = result.lead.text;
  els.articleLead.appendChild(citations(result.lead.citation_ids));
  els.articleSections.innerHTML = "";
  for (const section of result.sections) {
    const wrapper = node("section", "article-section");
    wrapper.appendChild(node("h3", "", section.heading));
    for (const paragraph of section.paragraphs) {
      const p = node("p", "", paragraph.text);
      p.appendChild(citations(paragraph.citation_ids));
      wrapper.appendChild(p);
    }
    els.articleSections.appendChild(wrapper);
  }
  els.conclusionCard.hidden = false;
  els.conclusionText.textContent = result.conclusion.text;
  els.conclusionText.appendChild(citations(result.conclusion.citation_ids));
  els.referencesSection.hidden = false;
  els.referenceList.innerHTML = "";
  for (const source of result.sources) {
    const item = node("li");
    item.id = `reference-${source.id}`;
    const link = node("a", "", source.title);
    link.href = safeUrl(source.url);
    link.target = "_blank";
    link.rel = "noopener";
    item.appendChild(link);
    item.appendChild(node("small", "", source.domain));
    els.referenceList.appendChild(item);
  }
}

function citations(ids) {
  const span = node("sup", "citations");
  for (const id of ids || []) {
    const link = node("a", "", `[${id}]`);
    link.href = `#reference-${id}`;
    link.setAttribute("aria-label", `View reference ${id}`);
    span.appendChild(link);
  }
  return span;
}

document.querySelectorAll("[data-query]").forEach((button) => {
  button.addEventListener("click", () => {
    els.searchInput.value = button.dataset.query;
    searchObjects();
  });
});
els.searchForm.addEventListener("submit", searchObjects);
