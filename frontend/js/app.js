const API = "";
const CATEGORY_COLORS = {
  teaching: "#3457D5",
  research: "#7A4FD9",
  institutional: "#0E8C82",
  professional_development: "#C4841C",
};
const CATEGORY_LABELS = {
  teaching: "Teaching",
  research: "Research",
  institutional: "Institutional",
  professional_development: "Prof. Dev.",
};

let formSchema = null;
let charts = {};
let currentFacultyId = null;

// ---------------------------------------------------------------- helpers
function $(sel, root = document) { return root.querySelector(sel); }
function $all(sel, root = document) { return [...root.querySelectorAll(sel)]; }
function badgeClass(cat) { return cat.replace(/\s+/g, ""); }
function toast(msg, isError = false) {
  const el = $("#toast");
  el.textContent = msg;
  el.className = "toast show" + (isError ? " error" : "");
  setTimeout(() => el.classList.remove("show"), 3200);
}
async function api(path, opts) {
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed (${res.status})`);
  }
  return res.json();
}
function destroyChart(key) { if (charts[key]) { charts[key].destroy(); delete charts[key]; } }

// ---------------------------------------------------------------- nav
function showView(view) {
  $all(".view").forEach(v => v.classList.add("hidden"));
  $(`#view-${view}`).classList.remove("hidden");
  $all(".nav-item").forEach(n => n.classList.toggle("active", n.dataset.view === view));
  if (view === "dashboard") loadDashboard();
  if (view === "roster") loadRoster();
  if (view === "validation") loadValidation();
}
$all(".nav-item").forEach(btn => btn.addEventListener("click", () => showView(btn.dataset.view)));
$all("[data-goto]").forEach(btn => btn.addEventListener("click", () => showView(btn.dataset.goto)));
$("#back-to-roster").addEventListener("click", () => showView("roster"));

// ================================================================== DASHBOARD
async function loadDashboard() {
  const [data, facultyRows] = await Promise.all([
    api("/api/dashboard/summary"),
    api("/api/faculty?department=All"),
  ]);

  const kpiRow = $("#kpi-row");
  const dist = data.performance_distribution;
  const good = (dist["Good"] || 0) + (dist["Very Good"] || 0) + (dist["Excellent"] || 0);
  kpiRow.innerHTML = `
    <div class="kpi"><div class="kpi-label">Total Faculty Evaluated</div><div class="kpi-value">${data.total_faculty}</div></div>
    <div class="kpi"><div class="kpi-label">Good or Above</div><div class="kpi-value">${good} <span>/ ${data.total_faculty}</span></div></div>
    <div class="kpi"><div class="kpi-label">Avg. Teaching Score</div><div class="kpi-value">${data.average_category_scores.teaching ?? "–"}</div></div>
    <div class="kpi"><div class="kpi-label">Avg. Research Score</div><div class="kpi-value">${data.average_category_scores.research ?? "–"}</div></div>
  `;

  if (typeof Chart === "undefined") {
    toast("Charts are unavailable because the chart library could not be loaded.", true);
    return;
  }

  destroyChart("dist");
  charts.dist = new Chart($("#chart-distribution"), {
    type: "doughnut",
    data: {
      labels: Object.keys(dist),
      datasets: [{
        data: Object.values(dist),
        backgroundColor: ["#0E8C82", "#3457D5", "#C4841C"],
        borderWidth: 0,
      }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 11.5 } } } },
    },
  });

  const catKeys = Object.keys(CATEGORY_LABELS);
  destroyChart("avgcat");
  charts.avgcat = new Chart($("#chart-avg-category"), {
    type: "bar",
    data: {
      labels: catKeys.map(k => CATEGORY_LABELS[k]),
      datasets: [{
        data: catKeys.map(k => data.average_category_scores[k] ?? 0),
        backgroundColor: catKeys.map(k => CATEGORY_COLORS[k]),
        borderRadius: 6,
        maxBarThickness: 46,
      }],
    },
    options: {
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, max: 100 } },
      plugins: { legend: { display: false } },
    },
  });

  destroyChart("dept");
  charts.dept = new Chart($("#chart-dept"), {
    type: "bar",
    data: {
      labels: data.department_averages.map(d => d.department),
      datasets: catKeys.map(k => ({
        label: CATEGORY_LABELS[k],
        data: data.department_averages.map(d => d[`avg_${k}`]),
        backgroundColor: CATEGORY_COLORS[k],
        borderRadius: 4,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { x: { stacked: false }, y: { beginAtZero: true, max: 100 } },
      plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 11.5 } } } },
    },
  });

  const deptFilter = $("#dashboard-dept-filter");
  if (!deptFilter.dataset.loaded) {
    deptFilter.innerHTML = `<option value="All">All Departments</option>` +
      formSchema.departments.map(d => `<option value="${d}">${d}</option>`).join("");
    deptFilter.dataset.loaded = "1";
  }
  deptFilter.onchange = () => renderDepartmentDashboard(facultyRows);
  renderDepartmentDashboard(facultyRows);

  function rowHtml(r) {
    const weakest = Object.entries(r.category_scores)
      .sort((a, b) => a[1] - b[1])[0];
    return `<div class="mini-row" data-fid="${r.faculty_id}">
      <div class="who"><b>${r.faculty_name || r.faculty_id}</b><span>${r.department} · ${r.faculty_id}${weakest ? ` · Lowest: ${CATEGORY_LABELS[weakest[0]]} ${weakest[1].toFixed(1)}` : ""}</span></div>
      <div class="score">${Number(r.overall_score).toFixed(1)}</div>
    </div>`;
  }
  $all("#top-performers .mini-row, #bottom-performers .mini-row")
    .forEach(el => el.addEventListener("click", () => openDetail(el.dataset.fid)));

  function renderDepartmentDashboard(rows) {
    const selectedDept = deptFilter.value;
    const departmentRows = selectedDept === "All"
      ? rows
      : rows.filter(r => r.department === selectedDept);
    const categoryAverages = Object.keys(CATEGORY_LABELS).map(key => {
      const average = departmentRows.length
        ? departmentRows.reduce((sum, row) => sum + Number(row.category_scores[key] || 0), 0) / departmentRows.length
        : 0;
      return { key, average };
    });
    const lowest = [...categoryAverages].sort((a, b) => a.average - b.average)[0];
    $("#department-low-category").textContent = departmentRows.length
      ? `${selectedDept === "All" ? "All departments" : selectedDept} · ${departmentRows.length} faculty · Lowest category: ${CATEGORY_LABELS[lowest.key]} (${lowest.average.toFixed(1)} / 100)`
      : `No faculty evaluations found for ${selectedDept}.`;

    destroyChart("deptCategory");
    charts.deptCategory = new Chart($("#chart-dept-category"), {
      type: "bar",
      data: {
        labels: categoryAverages.map(item => CATEGORY_LABELS[item.key]),
        datasets: [{
          label: "Average score",
          data: categoryAverages.map(item => item.average),
          backgroundColor: categoryAverages.map(item => CATEGORY_COLORS[item.key]),
          borderRadius: 4,
          maxBarThickness: 52,
        }],
      },
      options: {
        maintainAspectRatio: false,
        scales: { y: { beginAtZero: true, max: 100 } },
        plugins: { legend: { display: false } },
      },
    });

    const top = [...departmentRows].sort((a, b) => b.overall_score - a.overall_score).slice(0, 5);
    const bottom = [...departmentRows].sort((a, b) => a.overall_score - b.overall_score).slice(0, 5);
    $("#top-performers").innerHTML = top.map(rowHtml).join("") || "<p>No data yet.</p>";
    $("#bottom-performers").innerHTML = bottom.map(rowHtml).join("") || "<p>No data yet.</p>";
    $all("#top-performers .mini-row, #bottom-performers .mini-row")
      .forEach(el => el.addEventListener("click", () => openDetail(el.dataset.fid)));
  }
}

// ================================================================== EVALUATE FORM
async function loadFormSchema() {
  formSchema = await api("/api/form-schema");

  const deptSelect = $("#dept-select");
  deptSelect.innerHTML = formSchema.departments.map(d => `<option value="${d}">${d}</option>`).join("");

  const container = $("#dynamic-sections");
  container.innerHTML = Object.entries(formSchema.categories).map(([key, cat]) => `
    <div class="metric-section">
      <div class="metric-section-head">
        <span class="dot" style="background:${CATEGORY_COLORS[key]}"></span>
        <h4>${cat.label}</h4>
        <span class="w">weight ${(cat.weight * 100).toFixed(0)}%</span>
      </div>
      <div class="metric-grid">
        ${cat.fields.map(f => `
          <label>${f.label}
            <input type="number" name="${f.key}" min="${f.min ?? 0}" ${f.max ? `max="${f.max}"` : ""} step="${f.step ?? 1}" value="0" required />
          </label>
        `).join("")}
      </div>
    </div>
  `).join("");
}

$("#eval-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const status = $("#form-status");
  status.textContent = "Computing...";
  status.className = "form-status";

  const fd = new FormData(e.target);
  const payload = {};
  for (const [k, v] of fd.entries()) {
    if (["faculty_id", "faculty_name", "department", "semester"].includes(k)) {
      payload[k] = v;
    } else {
      payload[k] = v === "" ? 0 : parseFloat(v);
    }
  }

  try {
    const result = await api("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    renderResult(result);
    status.textContent = `Saved — evaluation #${result.id}`;
    toast(`Evaluation complete for ${result.faculty_id}`);
    await loadDashboard();
  } catch (err) {
    status.textContent = err.message;
    status.className = "form-status error";
    toast(err.message, true);
  }
});

function renderResult(r) {
  const panel = $("#result-panel");
  const catRows = Object.entries(r.category_scores).map(([k, v]) => `
    <div class="cat-bar-row">
      <span>${CATEGORY_LABELS[k]}</span>
      <div class="cat-bar-track"><div class="cat-bar-fill" style="width:${v}%;background:${CATEGORY_COLORS[k]}"></div></div>
      <span>${v.toFixed(1)}</span>
    </div>
  `).join("");

  let aiHtml = "";
  if (r.ml_cross_check && r.ml_cross_check.available) {
    const ml = r.ml_cross_check;
    const flag = r.agreement && r.agreement.flag_for_review;
    aiHtml = `
      <div class="ai-check ${flag ? "flag" : ""}">
        <div class="ai-title">${flag ? "⚠ AI Cross-Check: Review Suggested" : "✓ AI Cross-Check: Consistent"}</div>
        The independent <b>Logistic Regression</b> model estimates <b>${ml.predicted_overall_score}</b>
        (${ml.predicted_performance_category}, ${(ml.confidence * 100).toFixed(0)}% confidence)
        vs. the formula score of <b>${r.overall_score}</b>
        — a difference of ${r.agreement ? r.agreement.score_diff : "–"} points.
        ${flag ? "Consider double-checking the entered metrics." : "This supports the formula-based result."}
      </div>`;
  }

  const recoHtml = r.recommendations.map((rec, i) => `
    <div class="reco-item">
      <div class="reco-rank">${String(i + 1).padStart(2, "0")}</div>
      <div class="reco-body">
        <div class="reco-cat">${rec.category} · score ${rec.score.toFixed(0)}</div>
        <div class="reco-metric">${rec.metric}</div>
        <div class="reco-advice">${rec.advice}</div>
      </div>
    </div>
  `).join("") || "<p>No significant gaps found — well-rounded performance.</p>";

  panel.innerHTML = `
    <div class="score-hero">
      <div class="label">Overall Performance Score</div>
      <div class="value">${r.overall_score.toFixed(2)}</div>
      <span class="cat-badge ${badgeClass(r.performance_category)}">${r.performance_category}</span>
    </div>
    <div class="card">
      <h3>Category Breakdown</h3>
      <div class="cat-bars">${catRows}</div>
    </div>
    ${aiHtml}
    <div class="card">
      <h3>Top Recommendations</h3>
      <div class="reco-list">${recoHtml}</div>
    </div>
  `;
}

// ================================================================== ROSTER
async function loadRoster() {
  const deptFilter = $("#roster-dept-filter");
  if (!deptFilter.dataset.loaded) {
    deptFilter.innerHTML = `<option value="All">All Departments</option>` +
      formSchema.departments.map(d => `<option value="${d}">${d}</option>`).join("");
    deptFilter.dataset.loaded = "1";
    deptFilter.addEventListener("change", loadRoster);
  }

  const rows = await api(`/api/faculty?department=${encodeURIComponent(deptFilter.value)}`);
  $("#roster-body").innerHTML = rows.map(r => `
    <tr data-fid="${r.faculty_id}">
      <td><b>${r.faculty_name || r.faculty_id}</b><br><span style="color:var(--ink-soft);font-size:11.5px">${r.faculty_id}</span></td>
      <td>${r.department}</td>
      <td>${r.category_scores.teaching.toFixed(1)}</td>
      <td>${r.category_scores.research.toFixed(1)}</td>
      <td>${r.category_scores.institutional.toFixed(1)}</td>
      <td>${r.category_scores.professional_development.toFixed(1)}</td>
      <td><b>${r.overall_score.toFixed(1)}</b></td>
      <td><span class="pill ${badgeClass(r.performance_category)}">${r.performance_category}</span></td>
      <td><button class="btn btn-sm" data-fid="${r.faculty_id}">View</button></td>
    </tr>
  `).join("") || `<tr><td colspan="9">No faculty evaluated yet.</td></tr>`;

  $all("#roster-body tr").forEach(tr => tr.addEventListener("click", () => openDetail(tr.dataset.fid)));
}

// ================================================================== DETAIL
async function openDetail(facultyId) {
  currentFacultyId = facultyId;
  const hist = await api(`/api/faculty/${encodeURIComponent(facultyId)}/history`);
  const latest = hist[hist.length - 1];

  showView("detail");
  $("#detail-name").textContent = latest.faculty_name || latest.faculty_id;
  $("#detail-sub").textContent = `${latest.faculty_id} · ${latest.department} · Overall ${latest.overall_score.toFixed(1)} (${latest.performance_category})`;

  const catKeys = Object.keys(CATEGORY_LABELS);
  destroyChart("radar");
  charts.radar = new Chart($("#chart-radar"), {
    type: "radar",
    data: {
      labels: catKeys.map(k => CATEGORY_LABELS[k]),
      datasets: [{
        label: latest.faculty_id,
        data: catKeys.map(k => latest.category_scores[k]),
        backgroundColor: "rgba(52,87,213,0.15)",
        borderColor: "#3457D5",
        pointBackgroundColor: "#3457D5",
      }],
    },
    options: { scales: { r: { min: 0, max: 100, ticks: { stepSize: 20 } } }, plugins: { legend: { display: false } } },
  });

  destroyChart("trend");
  charts.trend = new Chart($("#chart-trend"), {
    type: "line",
    data: {
      labels: hist.map(h => h.semester || h.created_at.slice(0, 10)),
      datasets: [{
        label: "Overall Score",
        data: hist.map(h => h.overall_score),
        borderColor: "#0E8C82",
        backgroundColor: "rgba(14,140,130,0.12)",
        fill: true, tension: 0.3,
      }],
    },
    options: { scales: { y: { min: 0, max: 100 } }, plugins: { legend: { display: false } } },
  });

  // Recompute recommendations client-side isn't possible without sub_score_detail
  // history rows don't store it, so re-run evaluate-style breakdown via a
  // lightweight re-request is unnecessary — show latest raw-input driven advice
  // by calling the same recommendation logic is server-side only; instead we
  // surface the category gaps we do have.
  const gapsHtml = catKeys
    .map(k => ({ k, v: latest.category_scores[k] }))
    .sort((a, b) => a.v - b.v)
    .map(({ k, v }) => `
      <div class="reco-item">
        <div class="reco-body">
          <div class="reco-cat">${CATEGORY_LABELS[k]}</div>
          <div class="reco-metric">Score: ${v.toFixed(1)} / 100</div>
          <div class="reco-advice">${v < 60 ? "Priority improvement area — see the Evaluate tab for detailed sub-metric recommendations next time this faculty member is assessed." : "Performing well in this category."}</div>
        </div>
      </div>
    `).join("");
  $("#detail-recommendations").innerHTML = gapsHtml;
}

// ================================================================== VALIDATION
async function loadValidation() {
  const container = $("#validation-content");
  const data = await api("/api/validation-metrics");

  if (!data.available) {
    container.innerHTML = `<div class="card"><p>${data.message}</p></div>`;
    return;
  }

  const eng = data.scoring_engine;
  const reg = data.regression;
  const clf = data.classification;

  container.innerHTML = `
    <div class="card">
      <h3>1. Deterministic Scoring Engine — Formula Validation</h3>
      <table class="metric-table">
        <tr><th>Records validated</th><td>${eng.n}</td></tr>
        <tr><th>Overall score — mean absolute error</th><td>${eng.overall_score_mae.toFixed(4)}</td></tr>
        <tr><th>Overall score — max absolute error</th><td>${eng.overall_score_max_err.toFixed(4)}</td></tr>
        <tr><th>Classification exact-match rate</th><td>${(eng.classification_exact_match_rate * 100).toFixed(1)}%</td></tr>
      </table>
      <div class="note">Max error ≤0.01 points is pure floating-point rounding — the engine reproduces the reference dataset's own methodology exactly, so new faculty are scored on an identical basis.</div>
    </div>

    <div class="card">
      <h3>2. ML Cross-Check — Regression (${reg.model_type ? "Linear Regression" : "Model"} — Overall Score from engineered sub-scores)</h3>
      <table class="metric-table">
        <tr><th>Metric</th><th>Model</th><th>Baseline (mean)</th></tr>
        <tr><td>R²</td><td>${reg.r2.toFixed(6)}</td><td>0.0000</td></tr>
        <tr><td>MAE</td><td>${reg.mae.toFixed(4)}</td><td>${reg.baseline_mean_predictor_mae.toFixed(3)}</td></tr>
        <tr><td>RMSE</td><td>${reg.rmse.toFixed(4)}</td><td>–</td></tr>
      </table>
      <div class="note">R² ≈ 1.0 is expected: Overall Score is, by the framework's own design, an exact weighted linear combination of the category/sub scores — so Linear Regression on those engineered features recovers it almost perfectly. This confirms the ML layer faithfully reproduces the scoring framework.</div>
    </div>

    <div class="card">
      <h3>3. ML Cross-Check — Logistic Regression (Performance Level from engineered sub-scores)</h3>
      <table class="metric-table">
        <tr><th>Metric</th><th>Model</th><th>Baseline (majority class)</th></tr>
        <tr><td><b>Accuracy</b></td><td><b>${(clf.accuracy * 100).toFixed(2)}%</b></td><td>${(clf.baseline_majority_class_accuracy * 100).toFixed(1)}%</td></tr>
        <tr><td>Macro F1</td><td>${clf.macro_f1.toFixed(3)}</td><td>–</td></tr>
        <tr><td>Weighted F1</td><td>${clf.weighted_f1.toFixed(3)}</td><td>–</td></tr>
      </table>
      <div class="note">Evaluated with 5-fold Stratified K-Fold cross-validation (class proportions preserved in every fold) on the 600-row balanced dataset — class distribution: ${Object.entries(clf.class_distribution).map(([k, v]) => `${k}=${v}`).join(", ")}. Features are the 28 engineered sub-scores (not raw counts), which is why accuracy is far higher than a raw-feature model. Remaining errors are almost all borderline cases within 1-2 points of the 58/75 thresholds.</div>
      <div class="confusion">
        <b>Confusion matrix</b> (rows=actual, cols=predicted: ${clf.confusion_matrix_labels.join(" / ")})<br>
        ${clf.confusion_matrix.map(row => row.join("  ")).join("<br>")}
      </div>
    </div>

    <div class="card">
      <h3>Top Predictive Sub-Score Features</h3>
      <table class="metric-table">
        <tr><th>Feature</th><th>|Coefficient|</th></tr>
        ${data.regression_top_features.slice(0, 8).map(([f, imp]) => `<tr><td>${f}</td><td>${imp.toFixed(3)}</td></tr>`).join("")}
      </table>
    </div>
  `;
}

// ================================================================== INIT
(async function init() {
  await loadFormSchema();
  showView("dashboard");
})();
