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
// null keeps the server's order: repository, then title, then number. Clicking
// the column cycles ascending, descending, then back to that default.
let numberSort = null;
// Which column is sorting, so the two cannot both claim to be.
let sortColumn = null;

// The special value for "the board says nothing about this one". Kept distinct
// from the empty string, which means no filter at all.
const UNRANKED = "\u0000unranked";

function syncFilter(id, allLabel, values, extra) {
  const select = $(id);
  // The choice outlives a reload: rebuilding the options would otherwise reset
  // the filter every time the roster refreshes.
  const chosen = select.value;
  const offered = [...(values || []), ...(extra ? [extra.value] : [])];
  select.textContent = "";
  const first = el("option", null, allLabel);
  first.value = "";
  select.appendChild(first);
  for (const value of values || []) {
    const option = el("option", null, value);
    option.value = value;
    select.appendChild(option);
  }
  if (extra) {
    const option = el("option", null, extra.label);
    option.value = extra.value;
    select.appendChild(option);
  }
  select.value = offered.includes(chosen) ? chosen : "";
  return select.value;
}

async function loadRoster() {
  const roster = await getJSON("/api/roster");
  const body = $("roster");
  body.textContent = "";
  const chosen = syncFilter("repoFilter", "all repositories", roster.repositories);
  const category = syncFilter("pipeFilter", "all categories", roster.pipelines,
                              {value: UNRANKED, label: "no category"});
  let rows = roster.candidates.filter((row) =>
    (!chosen || row.repository === chosen) &&
    (!category || (category === UNRANKED ? !row.pipeline : row.pipeline === category)));
  if (numberSort) {
    // Sorts across every visible repository rather than within each one, so a
    // filtered view and an unfiltered one order the same way.
    const dir = numberSort === "asc" ? 1 : -1;
    if (sortColumn === "position") {
      // Unranked issues sink to the bottom in both directions. They are not
      // ranked last; they are not ranked, and floating them to the top of a
      // descending sort would read as though they were the board's priority.
      rows.sort((a, b) => {
        const x = a.position, y = b.position;
        if (x === null || x === undefined) return (y === null || y === undefined) ? 0 : 1;
        if (y === null || y === undefined) return -1;
        return (x - y) * dir;
      });
    } else {
      rows.sort((a, b) => (a.number - b.number) * dir);
    }
  }
  const arrow = numberSort === "asc" ? " \u2191" : numberSort === "desc" ? " \u2193" : "";
  $("thNum").textContent = "#" + (sortColumn === "number" ? arrow : "");
  $("thPos").textContent = "pos" + (sortColumn === "position" ? arrow : "");
  const shown = rows.length;
  for (const row of rows) {
    const tr = el("tr", "row");
    tr.appendChild(el("td", "pipe", row.repository));
    tr.appendChild(el("td", "num", "#" + row.number));
    tr.appendChild(el("td", row.pipeline ? "pipe" : "pipe unranked", row.pipeline || "N/A"));
    // Absent is not zero: an issue the board never ranked is shown as N/A
    // rather than sorted above the one the board actually ranked first.
    const ranked = row.position !== null && row.position !== undefined;
    tr.appendChild(el("td", ranked ? "num pos" : "num pos unranked",
                      ranked ? String(row.position) : "N/A"));
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
  // With a filter on, the exclusion count is the one for that repository:
  // a count drawn from repositories the console is hiding reports something
  // the reader can neither see nor act on.
  const excluded = chosen
    ? (roster.excluded_by_repository || {})[chosen.toLowerCase()] || 0
    : roster.excluded_count;
  setStatus(shown + " of " + roster.candidates.length + " candidates shown, " +
            excluded + " excluded", true);
  loadExcluded();
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
  box.appendChild(el("h2", null, "Rankings"));
  for (const doc of docs) {
    const details = el("details");
    details.appendChild(el("summary", null, doc.name));
    details.appendChild(el("pre", "text", doc.text));
    box.appendChild(details);
  }
}

async function loadExcluded() {
  const all = await getJSON("/api/excluded");
  const chosen = $("repoFilter").value;
  const entries = chosen
    ? all.filter((entry) => typeof entry.key === "string" &&
                            entry.key.toLowerCase().startsWith(chosen.toLowerCase() + "#"))
    : all;
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

// Which launches the operator has opened, so a poll does not shut them.
const openLaunches = new Set();
let launchTimer = null;

async function loadLaunches() {
  const launches = await getJSON("/api/loops");
  const box = $("launches");
  box.textContent = "";
  const running = launches.filter((launch) => launch.running).length;
  box.appendChild(el("h2", null,
    "Loop launches (" + launches.length + (running ? ", " + running + " running" : "") + ")"));
  for (const launch of launches) {
    const details = el("details");
    // A running loop opens itself: watching it is the reason to be here. Any
    // launch the operator opened stays open across the poll.
    details.open = launch.running || openLaunches.has(launch.name);
    details.addEventListener("toggle", () => {
      if (details.open) openLaunches.add(launch.name);
      else openLaunches.delete(launch.name);
    });
    const size = launch.size ? " · " + launch.size + " chars" : "";
    const cut = launch.truncated ? " · showing the tail" : "";
    details.appendChild(el("summary", null,
      launch.name + (launch.running ? " · running" : " · finished") + size + cut));
    const pre = el("pre", "text", launch.log_tail || "(no output yet)");
    if (launch.running) {
      // Newest output is at the bottom, which is where a reader watching a live
      // run wants to be. Only for a running one: scrolling a finished log out
      // from under someone reading it is worse than leaving it where they put it.
      requestAnimationFrame(() => { pre.scrollTop = pre.scrollHeight; });
    }
    details.appendChild(pre);
    box.appendChild(details);
  }
  // The newest launch drives the eye and the failure panel: older runs are
  // history, and a failure from three loops ago is not the current state.
  showRunState(launches[0]);
  // Poll only while something is running, so an idle console is quiet.
  if (launchTimer) { clearTimeout(launchTimer); launchTimer = null; }
  if (running) launchTimer = setTimeout(loadLaunches, 3000);
}

function showRunState(latest) {
  const eye = $("eye");
  const title = $("eyeTitle");
  const panel = $("failure");
  eye.classList.remove("running", "failed");
  panel.hidden = true;
  panel.textContent = "";
  if (!latest) {
    title.textContent = "no run";
    return;
  }
  if (latest.outcome === "running") {
    eye.classList.add("running");
    title.textContent = latest.name + " is running";
    return;
  }
  if (latest.outcome === "failed") {
    eye.classList.add("failed");
    title.textContent = latest.name + " failed with exit " + latest.exit_code;
    panel.hidden = false;
    panel.appendChild(el("h2", null, "Run failed: " + latest.name));
    panel.appendChild(el("p", "meta", "exit " + latest.exit_code +
      " · " + latest.size + " chars of output" +
      (latest.truncated ? " · last " + latest.log_tail.length + " shown" : "")));
    // The end of the log is where a failure says why, so the panel opens there
    // rather than making the reader scroll a wall of successful steps.
    const lines = (latest.log_tail || "").trimEnd().split("\n");
    panel.appendChild(el("pre", "text", lines.slice(-25).join("\n") || "(no output)"));
    return;
  }
  title.textContent = latest.outcome === "succeeded"
    ? latest.name + " finished cleanly"
    : latest.name + " ended without a recorded status";
}

$("repoFilter").addEventListener("change", loadRoster);
function cycleSort(column) {
  // Clicking a different column starts it ascending rather than inheriting the
  // other one's direction.
  if (sortColumn !== column) { sortColumn = column; numberSort = "asc"; }
  else if (numberSort === "asc") numberSort = "desc";
  else if (numberSort === "desc") { numberSort = null; sortColumn = null; }
  else numberSort = "asc";
  loadRoster();
}
$("thNum").addEventListener("click", () => cycleSort("number"));
$("thPos").addEventListener("click", () => cycleSort("position"));
$("pipeFilter").addEventListener("change", loadRoster);
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
