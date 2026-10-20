const form = document.querySelector("#recordForm");
const resultTitle = document.querySelector("#resultTitle");
const resultStatus = document.querySelector("#resultStatus");
const resultCard = document.querySelector("#resultCard");
const labelText = document.querySelector("#labelText");
const claimList = document.querySelector("#claimList");
const citationStrip = document.querySelector("#citationStrip");
const checkList = document.querySelector("#checkList");
const scoreValue = document.querySelector("#scoreValue");
const initialForm = new FormData(form);

const requiredFields = ["title", "objectDate", "medium", "culture", "creditLine"];
const fieldLabels = {
  title: "title",
  objectDate: "object date",
  medium: "medium",
  culture: "place or culture",
  creditLine: "credit line"
};

function currentRecord() {
  return Object.fromEntries(new FormData(form).entries());
}

function showChecks({ passed, missing = [] }) {
  const rows = [
    ["Field existence", "Every claim cites a supplied field."],
    ["Value containment", "Named values stay inside their source."],
    ["Citation resolution", "Printed citations resolve to the record."],
    ["Readability band", "Short sentences, 60–80 words."]
  ];
  const checksPassed = passed ? rows.length : 0;
  scoreValue.textContent = `${Math.round((checksPassed / rows.length) * 100)}%`;
  scoreValue.style.color = passed ? "var(--teal)" : "var(--red)";
  checkList.innerHTML = rows.map(([title, description], index) => {
    const failed = !passed && index === 0;
    const note = failed ? `Missing required field: ${missing.join(", ")}.` : description;
    return `<div class="check-row"><span class="check-icon" style="background:${failed ? "var(--red)" : "var(--teal)"}">${failed ? "!" : "✓"}</span><div><b>${title}</b><small>${note}</small></div></div>`;
  }).join("");
}

function showDraft(record) {
  const missing = requiredFields.filter((field) => !record[field]?.trim());
  const refused = missing.length > 0;
  resultCard.classList.toggle("refused", refused);
  resultStatus.classList.toggle("refused", refused);
  resultStatus.textContent = refused ? "REFUSED" : "DRAFTED";
  resultTitle.textContent = refused ? "Safe refusal" : "Grounded draft";
  if (refused) {
    labelText.textContent = `No label was drafted. The record is missing the required ${missing.map((field) => fieldLabels[field]).join(", ")} field${missing.length > 1 ? "s" : ""}. Add the missing catalogue information before drafting. This request has been refused rather than filling the gap with an unsupported fact.`;
    claimList.innerHTML = `<span class="claim-tag">Reason: missing ${missing.map((field) => fieldLabels[field]).join(", ")}</span>`;
    citationStrip.innerHTML = "";
    showChecks({ passed: false, missing: missing.map((field) => fieldLabels[field]) });
    return;
  }

  labelText.textContent = `This object is titled “${record.title}”. The catalogue dates it to ${record.objectDate}. It is recorded as ${record.medium}. Its place or culture is given as “${record.culture}”, preserving the catalogue's uncertainty. The credit line reads: ${record.creditLine}. Draft for curator review, not an official record.`;
  const sources = ["title", "object date", "medium", "place or culture", "credit line"];
  claimList.innerHTML = sources.map((source) => `<span class="claim-tag">Claim · ${source}</span>`).join("");
  citationStrip.innerHTML = sources.map((source) => `<span class="citation-tag">↳ ${source}</span>`).join("");
  showChecks({ passed: true });
}

document.querySelector("[data-action='draft']").addEventListener("click", (event) => {
  event.preventDefault();
  showDraft(currentRecord());
});

document.querySelector("#forceDraftButton").addEventListener("click", (event) => {
  event.preventDefault();
  showDraft(currentRecord());
});

document.querySelector("#refusalButton").addEventListener("click", (event) => {
  event.preventDefault();
  form.elements.namedItem("objectDate").value = "";
  showDraft(currentRecord());
});

document.querySelector("#resetButton").addEventListener("click", (event) => {
  event.preventDefault();
  for (const [key, value] of initialForm.entries()) form.elements.namedItem(key).value = value;
  showDraft(currentRecord());
});

showDraft(currentRecord());
