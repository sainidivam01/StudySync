const $ = s => document.querySelector(s);
const pad = n => String(n).padStart(2, "0");
const localDate = (d = new Date()) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const localDT = (d = new Date()) => `${localDate(d)}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
const TODAY = localDate();           // student's own calendar day, avoids server time-zone errors
let weeklyChart, monthlyChart, editingId = null, subjects = [];

async function api(url, opts = {}) {
  const r = await fetch(url, { headers: { "Content-Type": "application/json" }, credentials: "same-origin", ...opts });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || "Request failed");
  return j;
}
const say = (t, bad = false) => { const m = $("#msg"); m.textContent = t; m.className = "msg" + (bad ? " bad" : ""); };
const fmtMins = m => m >= 60 ? `${Math.floor(m / 60)} h${m % 60 ? " " + (m % 60) + " min" : ""}` : `${m} min`;

async function loadSubjects() {
  subjects = await api("/api/subjects");
  const opts = subjects.map(s => `<option value="${s.subject_id}">${s.name}</option>`).join("");
  const keep = $("#subject").value, keepF = $("#filter").value;
  $("#subject").innerHTML = opts;
  $("#filter").innerHTML = `<option value="">All units</option>` + opts;
  if (keep) $("#subject").value = keep;
  if (keepF) $("#filter").value = keepF;
}

async function loadSummary() {
  const f = $("#filter").value;
  const s = await api(`/api/summary?today=${TODAY}${f ? `&subject_id=${f}` : ""}`);
  $("#tWeek").textContent = `${s.week_hours} h`;
  $("#tWeekSub").textContent = s.weekly_goal ? `Goal ${s.weekly_goal} h` : "Set a weekly goal below";
  $("#tAvg").textContent = `${s.daily_average} h`;
  $("#tAvgSub").textContent = s.weekly_goal ? `Target ${(s.weekly_goal / 7).toFixed(1)} h per day` : "";
  $("#tStreak").textContent = `${s.streak} day${s.streak === 1 ? "" : "s"}`;
  $("#tBest").textContent = `Best streak: ${s.best_streak} day${s.best_streak === 1 ? "" : "s"}`;
  $("#tCount").textContent = s.sessions_this_week;
  $("#tUnits").textContent = `Across ${s.units_this_week} unit${s.units_this_week === 1 ? "" : "s"}`;
  if (s.weekly_goal) {
    $("#goalText").textContent = `${s.week_hours} of ${s.weekly_goal} hours`;
    $("#goalBar").style.width = `${s.weekly_pct}%`;
    const left = Math.max(0, s.weekly_goal - s.week_hours).toFixed(1);
    $("#goalPct").textContent = `${s.weekly_pct}% complete · ${left} h to go`;
  } else { $("#goalText").textContent = "No weekly goal set"; $("#goalBar").style.width = "0%"; $("#goalPct").textContent = ""; }
  if (s.monthly_goal) $("#mGoal").placeholder = `Monthly target: ${s.monthly_goal} h (${s.monthly_pct}% done)`;
  if (s.weekly_goal) $("#wGoal").placeholder = `Weekly target: ${s.weekly_goal} h`;
}

async function loadCharts() {
const f = $("#filter").value;
const w = await api(`/api/chart/weekly?today=${TODAY}${f ? `&subject_id=${f}` : ""}`);
  const ds = [{ type: "bar", label: "Hours studied", data: w.hours, backgroundColor: "#2A9D8F", borderRadius: 6 }];
if (w.daily_target) ds.push({ type: "line", label: `Daily target (${w.daily_target} h)`, data: Array(7).fill(w.daily_target),
  borderColor: "#E9A23B", borderDash: [6, 5], pointRadius: 0, borderWidth: 2 });
if (weeklyChart) weeklyChart.destroy();
weeklyChart = new Chart($("#weekly"), { data: { labels: w.labels, datasets: ds },
  options: { maintainAspectRatio: false, animation: false, plugins: { legend: { position: "bottom" } },
    scales: { y: { beginAtZero: true, title: { display: true, text: "Hours" } } } } });
const m = await api(`/api/chart/monthly?today=${TODAY}${f ? `&subject_id=${f}` : ""}`);
  if (monthlyChart) monthlyChart.destroy();
  monthlyChart = new Chart($("#monthly"), { type: "line", data: { labels: m.labels.map(l => "Wk " + l), datasets: [{
      label: "Weekly hours", data: m.hours, borderColor: "#1F3A5F", backgroundColor: "rgba(42,157,143,.15)",
      fill: true, tension: .35, pointBackgroundColor: "#1F3A5F" }] },
    options: { maintainAspectRatio: false, animation: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } } });
}

async function loadRows() {
  const f = $("#filter").value;
  const rows = await api("/api/sessions?limit=12" + (f ? `&subject_id=${f}` : ""));
  $("#rowsEmpty").hidden = rows.length > 0;
  $("#rows").innerHTML = rows.map(r => `<tr><td><span class="dot" style="background:${r.colour}"></span>${r.subject}</td>
    <td>${r.start_time.replace("T", " ")}</td><td>${fmtMins(r.minutes)}</td>
    <td><button class="lnk" data-edit='${JSON.stringify(r)}'>Edit</button><button class="lnk del" data-del="${r.session_id}">Delete</button></td></tr>`).join("");
  if (rows.length && !editingId) { $("#minutes").value = rows[0].minutes; $("#subject").value = rows[0].subject_id; }  // remembered defaults
}

const refresh = () => Promise.all([loadSummary(), loadCharts(), loadRows()]);

function resetForm() { editingId = null; $("#formTitle").textContent = "Quick log"; $("#save").textContent = "Save session"; $("#cancel").hidden = true; $("#start").value = localDT(); }

$("#save").onclick = async () => {
  const body = JSON.stringify({ subject_id: +$("#subject").value, minutes: parseInt($("#minutes").value, 10), start_time: $("#start").value });
  try {
    if (editingId) await api(`/api/sessions/${editingId}`, { method: "PUT", body }); else await api("/api/sessions", { method: "POST", body });
    say(editingId ? "Session updated." : "Session saved."); resetForm(); await refresh();
  } catch (e) { say(e.message, true); }
};
$("#cancel").onclick = resetForm;
$("#rows").onclick = async e => {
  if (e.target.dataset.del) { if (confirm("Delete this session?")) { await api(`/api/sessions/${e.target.dataset.del}`, { method: "DELETE" }); await refresh(); } }
  if (e.target.dataset.edit) {
    const r = JSON.parse(e.target.dataset.edit); editingId = r.session_id;
    $("#subject").value = r.subject_id; $("#minutes").value = r.minutes; $("#start").value = r.start_time;
    $("#formTitle").textContent = "Edit session"; $("#save").textContent = "Update session"; $("#cancel").hidden = false;
  }
};
$("#addSub").onclick = async () => {
  try { const s = await api("/api/subjects", { method: "POST", body: JSON.stringify({ name: $("#newSub").value }) });
    $("#newSub").value = ""; await loadSubjects(); $("#subject").value = s.subject_id; say("Unit added."); } catch (e) { say(e.message, true); }
};
const setGoal = (period, input) => async () => {
  try { await api("/api/goals", { method: "POST", body: JSON.stringify({ period, target_hours: parseFloat($(input).value) }) });
    $(input).value = ""; say("Goal saved."); await loadSummary(); await loadCharts(); } catch (e) { say(e.message, true); }
};
$("#setW").onclick = setGoal("weekly", "#wGoal");
$("#setM").onclick = setGoal("monthly", "#mGoal");
$("#filter").onchange = refresh;

(async () => {
  const email = $("#who").textContent; $("#av").textContent = email.slice(0, 2).toUpperCase();
  $("#who").textContent = email.split("@")[0];
  $("#weekLabel").textContent = "Today is " + new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  $("#start").value = localDT();
  await loadSubjects(); await refresh();
})();
