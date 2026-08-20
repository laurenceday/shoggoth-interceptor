// Shoggoth console client. Ticket bodies are untrusted, so all board text
// lands in the DOM through textContent; no HTML-injecting sink is used here,
// and tests/test_mutations.py enforces that mechanically.
"use strict";

const $ = (id) => document.getElementById(id);

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function getJSON(path) {
  const res = await fetch(path);
  return res.json();
}

async function postJSON(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "X-Shoggoth": "1", "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  return res.json();
}

function setStatus(text, ok) {
  const node = $("status");
  node.textContent = text;
  node.className = ok === undefined ? "" : ok ? "ok" : "err";
}

function fmtAge(seconds) {
  if (seconds === null || seconds === undefined) return "never";
  if (seconds < 90) return seconds + "s";
  if (seconds < 5400) return Math.round(seconds / 60) + "m";
  return Math.round(seconds / 3600) + "h";
}

async function loadHealth() {
  const health = await getJSON("/api/health");
  const ages = health.state_age_seconds;
  $("age").textContent =
    "issues " + fmtAge(ages["board.json"]);
}

let selectedRow = null;

async function loadRoster() {
  const roster = await getJSON("/api/roster");
  const body = $("roster");
  body.textContent = "";
  for (const row of roster.candidates) {
    const tr = el("tr", "row");
    tr.appendChild(el("td", "pipe", row.repository));
    tr.appendChild(el("td", "num", "#" + row.number));
    const title = el("td", null, row.title + " ");
    for (const label of row.labels) title.appendChild(el("span", "label", label));
    tr.appendChild(title);
    tr.appendChild(el("td", "num", String(row.comments_count)));
    tr.addEventListener("click", () => {
      if (selectedRow) selectedRow.classList.remove("selected");
      selectedRow = tr;
      tr.classList.add("selected");
      loadIssue(row.key);
    });
    body.appendChild(tr);
  }
  setStatus(roster.candidates.length + " candidates in scope, " +
            roster.excluded_count + " excluded", true);
}

async function loadIssue(key) {
  const parts = key.split(/[\/#]/);
  const issue = await getJSON("/api/issue/" + parts[0] + "/" + parts[1] + "/" + parts[2]);
  const box = $("detail");
  box.textContent = "";
  box.appendChild(el("h2", null, "#" + issue.number + " " + issue.title));
  const meta = el("p", "meta",
    issue.repository + (issue.pipeline ? " · " + issue.pipeline : "") +
    " · " + issue.author + " · updated " + issue.updated_at + " · ");
  if (/^https:\/\/github\.com\//.test(issue.html_url)) {
    const link = el("a", null, "open on GitHub");
    link.href = issue.html_url;
    link.target = "_blank";
    link.rel = "noopener";
    meta.appendChild(link);
  }
  box.appendChild(meta);
  box.appendChild(el("pre", "text", issue.body || "(empty)"));
  for (const comment of issue.comments) {
    const wrap = el("div", "comment");
    wrap.appendChild(el("div", "who", comment.author + " · " + comment.created_at));
    wrap.appendChild(el("pre", "text", comment.body));
    box.appendChild(wrap);
  }
  const deliverables = el("p", "meta",
    issue.deliverables.length
      ? "deliverables for " + issue.key + ": " + issue.deliverables.join(", ")
      : "no deliverables yet");
  box.appendChild(deliverables);

  const form = el("div");
  form.id = "excludeForm";
  const input = el("input");
  input.placeholder = "exclusion reason (closes this ticket's loop)";
  input.maxLength = 300;
  const btn = el("button", null, "Exclude #" + issue.number);
  btn.addEventListener("click", async () => {
    if (!input.value.trim()) { setStatus("reason required", false); return; }
    setStatus("excluding…");
    const result = await postJSON("/api/exclude",
      { key: issue.key, reason: input.value.trim() });
    setStatus(result.ok ? "excluded " + issue.key : (result.error || "failed"), result.ok);
    if (result.ok) { loadRoster(); loadExcluded(); }
  });
  form.appendChild(input);
  form.appendChild(btn);
  box.appendChild(form);
}

async function loadRankings() {
  const docs = await getJSON("/api/rankings");
  const box = $("rankings");
  box.textContent = "";
  box.appendChild(el("h2", null, "Rankings and loop notes"));
  for (const doc of docs) {
    const details = el("details");
    details.appendChild(el("summary", null, doc.name));
    details.appendChild(el("pre", "text", doc.text));
    box.appendChild(details);
  }
}

async function loadExcluded() {
  const entries = await getJSON("/api/excluded");
  const box = $("excludedList");
  box.textContent = "";
  box.appendChild(el("h2", null, "Excluded (" + entries.length + ")"));
  for (const entry of entries) {
    box.appendChild(el("p", "meta",
      (entry.key || "#" + entry.number) + " — " + entry.reason + " (" + entry.excluded_at + ")"));
  }
}

$("btnRefresh").addEventListener("click", async () => {
  setStatus("refreshing configured GitHub repositories…");
  const result = await postJSON("/api/refresh");
  setStatus(result.ok ? "board refreshed" : "refresh failed — see server log", result.ok);
  if (result.ok) { loadHealth(); loadRoster(); }
});

async function startLoop(mode) {
  setStatus("launching " + mode + " session…");
  const result = await postJSON("/api/start-loop", { mode });
  setStatus(
    result.ok ? "launched " + result.name + " (pid " + result.pid + ")"
              : (result.error || "launch failed"),
    result.ok,
  );
  loadLaunches();
}

async function loadLaunches() {
  const launches = await getJSON("/api/loops");
  const box = $("launches");
  box.textContent = "";
  box.appendChild(el("h2", null, "Loop launches (" + launches.length + ")"));
  for (const launch of launches) {
    const details = el("details");
    details.appendChild(el("summary", null,
      launch.name + (launch.running ? " · running" : " · finished")));
    details.appendChild(el("pre", "text", launch.log_tail || "(no output yet)"));
    box.appendChild(details);
  }
}

$("btnSmoke").addEventListener("click", () => startLoop("smoke"));
$("btnLoop").addEventListener("click", () => startLoop("loop"));

$("btnArchive").addEventListener("click", async () => {
  setStatus("archiving…");
  const result = await postJSON("/api/archive");
  setStatus(result.ok ? result.output.trim().split("\n").pop() : "archive failed", result.ok);
});

loadHealth();
loadRoster();
loadRankings();
loadExcluded();
loadLaunches();
