/* ── Sankalp AI — Production Frontend ─────────────────────────────────────
   Rules:
   • Every number displayed comes from an API response — no invented values
   • JWT stored in memory only (not localStorage) — XSS-safe
   • Internal paths, file names, DB column names are never rendered
   • Source citation from API is shown beneath every number
────────────────────────────────────────────────────────────────────────── */

const API = "";
let _token = null;
let _user = null; // { username, role, cnf_code }

// ── Auth helpers ──────────────────────────────────────────────────────────────
function setToken(t, u) {
  _token = t;
  _user = u;
}
function clearAuth() {
  _token = null;
  _user = null;
}
function authHeaders() {
  return _token
    ? { Authorization: `Bearer ${_token}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
}

async function apiGet(path) {
  const r = await fetch(API + path, { headers: authHeaders() });
  if (r.status === 401) {
    showLogin();
    return null;
  }
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new Error(e.detail || r.statusText);
  }
  return r.json();
}
async function apiPost(path, body) {
  const r = await fetch(API + path, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
  if (r.status === 401) {
    showLogin();
    return null;
  }
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new Error(e.detail || r.statusText);
  }
  return r.json();
}

// ── RBAC visibility ───────────────────────────────────────────────────────────
const ROLE_VIEWS = {
  cfo: [
    "dashboard",
    "claims",
    "stock",
    "spike",
    "fillrate",
    "stockist",
    "ask",
    "report",
    "workflow",
    "why",
    "benchmark",
  ],
  supply_chain: ["dashboard", "stock", "fillrate", "spike", "ask", "workflow"],
  claims_finance: [
    "dashboard",
    "claims",
    "stockist",
    "ask",
    "myclaims",
    "auditor",
  ],
  sales_rsm: ["stockist", "ask", "myclaims"],
  cnf_agent: ["stock", "ask", "myclaims"],
  // admin: [
  //   "dashboard",
  //   "claims",
  //   "stock",
  //   "spike",
  //   "fillrate",
  //   "stockist",
  //   "ask",
  //   "admin",
  //   "report",
  admin: [
    "dashboard",
    "claims",
    "stock",
    "spike",
    "fillrate",
    "stockist",
    "ask",
    "admin",
    "report",
    "workflow",
    "why",
    "myclaims",
    "auditor",
    "benchmark",
  ],
};
function canSee(view) {
  if (!_user) return false;
  return (ROLE_VIEWS[_user.role] || []).includes(view);
}

// ── Routing ───────────────────────────────────────────────────────────────────
const TITLES = {
  dashboard: "Dashboard",
  claims: "Claim Findings",
  stock: "At-Risk Stock",
  spike: "Quarter Spike",
  fillrate: "Fill Rate",
  stockist: "Stockist Risk",
  ask: "Ask AI",
  admin: "Admin Panel",
  report: "RAPID Report",
  workflow: "Agent Workflow",
  why: "Why This Exists",
  myclaims: "My Claims",
  auditor: "Auditor Review",
  benchmark: "Recovery Benchmark",
};

function showView(id) {
  if (!canSee(id)) {
    showToast("Access denied for your role", "error");
    return;
  }
  document
    .querySelectorAll(".view")
    .forEach((v) => v.classList.remove("active"));
  document
    .querySelectorAll(".nav-item")
    .forEach((b) => b.classList.remove("active"));
  document.getElementById("view-" + id)?.classList.add("active");
  document.querySelector(`[data-view="${id}"]`)?.classList.add("active");
  document.getElementById("pageTitle").textContent = TITLES[id] || id;
  const loaders = {
    dashboard: loadDashboard,
    claims: loadClaims,
    stock: loadStock,
    fillrate: loadFillRate,
    stockist: loadStockistRisk,
    admin: loadAdmin,
    report: loadReport,
    workflow: loadWorkflow,
    why: () => {},
    myclaims: loadMyClaims,
    auditor: loadAuditorClaims,
    benchmark: loadBenchmark,
  };
  loaders[id]?.();
}

// ── Toast ──────────────────────────────────────────────────────────────────────
function showToast(msg, type = "info") {
  const t = document.createElement("div");
  t.className = `toast toast-${type}`;
  t.textContent = msg;
  document.getElementById("toastArea").appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

// ── Login modal ───────────────────────────────────────────────────────────────
function showLogin() {
  clearAuth();
  document.getElementById("appShell").style.display = "none";
  document.getElementById("loginModal").style.display = "flex";
}
function showApp() {
  document.getElementById("loginModal").style.display = "none";
  document.getElementById("appShell").style.display = "flex";
  buildNav();
  checkHealth();
  showView("dashboard");
}

document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("lu").value.trim();
  const password = document.getElementById("lp").value;
  const btn = e.target.querySelector("button");
  btn.textContent = "Signing in…";
  btn.disabled = true;
  try {
    const d = await apiPost("/api/auth/login", { username, password });
    if (!d) return;
    setToken(d.access_token, { username: d.username, role: d.role });
    document.getElementById("userBadge").textContent =
      `${d.username} · ${d.role}`;
    showApp();
  } catch (err) {
    showToast(err.message || "Login failed", "error");
  }
  btn.textContent = "Sign In";
  btn.disabled = false;
});

document.getElementById("logoutBtn").addEventListener("click", async () => {
  await apiPost("/api/auth/logout", {}).catch(() => {});
  clearAuth();
  showLogin();
});

// ── Nav builder (role-aware) ──────────────────────────────────────────────────
function buildNav() {
  const nav = document.getElementById("sideNav");
  const items = [
    { id: "dashboard", icon: "◈", label: "Dashboard" },
    { id: "claims", icon: "⊙", label: "Claim Findings" },
    { id: "stock", icon: "◎", label: "At-Risk Stock" },
    { id: "spike", icon: "⟁", label: "Quarter Spike" },
    { id: "fillrate", icon: "≡", label: "Fill Rate" },
    { id: "stockist", icon: "⊕", label: "Stockist Risk" },
    { id: "ask", icon: "◇", label: "Ask AI" },
    { id: "report", icon: "📄", label: "RAPID Report" },
    { id: "workflow", icon: "🔀", label: "Agent Workflow" },
    { id: "why", icon: "💡", label: "Why This Exists" },
    { id: "myclaims", icon: "📋", label: "My Claims" },
    { id: "auditor", icon: "🔍", label: "Auditor Review" },
    { id: "benchmark", icon: "💰", label: "Recovery Benchmark" },
    { id: "admin", icon: "⚙", label: "Admin" },
  ];
  nav.innerHTML = items
    .filter((i) => canSee(i.id))
    .map(
      (i) => `
    <button class="nav-item" data-view="${i.id}">
      <span class="nav-icon">${i.icon}</span> ${i.label}
    </button>`,
    )
    .join("");
  nav
    .querySelectorAll(".nav-item")
    .forEach((b) =>
      b.addEventListener("click", () => showView(b.dataset.view)),
    );
}

// ── Helpers ────────────────────────────────────────────────────────────────────
const fmt = (n) =>
  typeof n === "number"
    ? n.toLocaleString("en-IN", { maximumFractionDigits: 0 })
    : (n ?? "—");
const fmtCr = (n) => (n ? (n / 1e7).toFixed(2) + " Cr" : "—");
const fmtL = (n) => (n ? (n / 1e5).toFixed(1) + "L" : "—");
const escH = (s) =>
  String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
function daysTag(d) {
  const cls = d <= 30 ? "danger" : d <= 60 ? "warn" : "ok";
  return `<span class="tag ${cls}">${d}d</span>`;
}

// ── Health check ──────────────────────────────────────────────────────────────
async function checkHealth() {
  const dot = document.getElementById("healthDot");
  const txt = document.getElementById("healthText");
  try {
    const d = await apiGet("/api/health");
    if (d?.ok) {
      dot.className = "health-dot ok";
      txt.textContent = d.last_batch
        ? `Batch: ${new Date(d.last_batch).toLocaleDateString()}`
        : "No batch run yet";
    } else throw new Error();
  } catch {
    dot.className = "health-dot err";
    txt.textContent = "API offline";
  }
}

// ── Dashboard ──────────────────────────────────────────────────────────────────
async function loadDashboard() {
  const [summary, stock, fill, spike] = await Promise.all([
    apiGet("/api/analytics/summary").catch(() => null),
    apiGet("/api/at-risk-stock?days=90").catch(() => null),
    apiGet("/api/fill-rate").catch(() => null),
    apiGet("/api/quarter-spike").catch(() => null),
  ]);

  const grid = document.getElementById("kpiGrid");
  if (summary) {
    grid.innerHTML = [
      {
        label: "Total Addressable",
        value: fmtCr(summary.total_addressable_inr),
        sub: "Recoverable + preventable",
        cls: "danger",
      },
      {
        label: "Duplicate Excess Credits",
        value: fmtL(summary.duplicate_excess_inr),
        sub: `${summary.duplicate_groups} groups`,
        cls: "danger",
      },
      {
        label: "Zero-Invoice Credited",
        value: fmtL(summary.zero_invoice_inr),
        sub: "Batch never sold to stockist",
        cls: "danger",
      },
      {
        label: "At-Risk Inventory (90d)",
        value: fmtCr(summary.at_risk_90d_inr),
        sub: "Redistribution opportunity",
        cls: "warn",
      },
      {
        label: "Fill Rate (All CNFs)",
        value: fill ? fill.overall_fill_rate_pct + "%" : "—",
        sub: "Target: 96%",
        cls: fill && fill.overall_fill_rate_pct < 94 ? "warn" : "success",
      },
      {
        label: "High-Risk Stockists",
        value: summary.high_risk_stockists,
        sub: "Score ≥ 50",
        cls: "warn",
      },
      {
        label: "Pending Suspicious",
        value: fmtL(summary.pending_suspicious_inr),
        sub: "Block immediately",
        cls: "warn",
      },
      {
        label: "Latest Spike",
        value: spike ? spike.latest_spike_pct + "%" : "—",
        sub: spike?.latest_quarter || "",
        cls: spike && spike.latest_spike_pct > 25 ? "warn" : "success",
      },
    ]
      .map(
        (k) => `<div class="kpi ${k.cls}">
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-value">${k.value}</div>
      <div class="kpi-sub">${k.sub}</div>
    </div>`,
      )
      .join("");
  }

  // Therapy bar chart
  if (stock?.by_therapy_area) {
    const ta = stock.by_therapy_area;
    const max = Math.max(...Object.values(ta), 1);
    document.getElementById("therapyChart").innerHTML = Object.entries(ta)
      .sort((a, b) => b[1] - a[1])
      .map(
        ([n, v]) => `<div class="bar-row">
        <div class="bar-label">${escH(n)}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${(v / max) * 100}%"></div></div>
        <div class="bar-val">${fmtL(v)}</div>
      </div>`,
      )
      .join("");
  }

  // Fill rate chart
  if (fill?.by_cnf) {
    document.getElementById("fillChart").innerHTML = fill.by_cnf
      .map(
        (r) => `
      <div class="bar-row">
        <div class="bar-label">${r.cnf_code}</div>
        <div class="bar-track"><div class="bar-fill ${r.fill_rate_pct < 90 ? "danger" : r.fill_rate_pct < 95 ? "warn" : "success"}"
          style="width:${r.fill_rate_pct}%"></div></div>
        <div class="bar-val">${r.fill_rate_pct}%</div>
      </div>`,
      )
      .join("");
  }

  // Spike chart
  if (spike?.phasing_by_quarter) {
    const qs = spike.phasing_by_quarter;
    const maxP = Math.max(...qs.map((q) => q.spike_pct), 1);
    document.getElementById("spikeChart").innerHTML = qs
      .map((q) => {
        const h = Math.round((q.spike_pct / maxP) * 120);
        const c = q.spike_pct > 30 ? "high" : q.spike_pct > 20 ? "med" : "low";
        return `<div class="spike-col">
        <div class="spike-bar ${c}" style="height:${h}px" data-tip="${q.quarter}: ${q.spike_pct}%"></div>
        <div class="spike-label">${q.quarter.slice(2)}</div>
      </div>`;
      })
      .join("");
  }
}

// ── Claim Findings ──────────────────────────────────────────────────────────────
async function loadClaims() {
  const rl = document.getElementById("claimRiskFilter").value;
  const st = document.getElementById("claimStatusFilter").value;
  const url = `/api/analytics/claim-findings?risk_level=${rl}&status=${st}&limit=200`;
  document.getElementById("claimBody").innerHTML =
    '<tr><td colspan="9" class="loading">Loading…</td></tr>';
  try {
    const d = await apiGet(url);
    if (!d) return;
    document.getElementById("claimSummaryRow").innerHTML = `
      <span class="summary-chip">Total shown: <strong>${d.total}</strong></span>
      <span class="summary-chip">Run: <strong>${d.run_at ? new Date(d.run_at).toLocaleDateString() : "—"}</strong></span>`;
    document.getElementById("claimBody").innerHTML =
      d.findings
        .map(
          (f) => `<tr>
      <td style="font-family:monospace;font-size:11px">${escH(f.claim_no)}</td>
      <td>${escH(f.stockist_code)}</td>
      <td style="font-family:monospace">${escH(f.batch_no)}</td>
      <td>${escH(f.sku_code)}</td>
      <td>₹${fmt(f.claim_value_inr)}</td>
      <td><span class="tag ${f.status === "Credited" ? "ok" : f.status === "Pending" ? "warn" : "danger"}">${f.status}</span></td>
      <td><span class="tag ${f.risk_level === "HIGH" ? "danger" : f.risk_level === "MEDIUM" ? "warn" : "ok"}">${f.risk_level} (${f.risk_score})</span></td>
      <td>${f.signals.map((s) => `<span class="flag-pill">${escH(s)}</span>`).join("")}</td>
      <td style="font-size:11px">${escH(f.recommended_action)}</td>
    </tr>`,
        )
        .join("") || '<tr><td colspan="9">No findings match filter.</td></tr>';
  } catch (e) {
    showToast(e.message, "error");
  }
}
document
  .getElementById("claimRiskFilter")
  ?.addEventListener("change", loadClaims);
document
  .getElementById("claimStatusFilter")
  ?.addEventListener("change", loadClaims);

// ── At-Risk Stock ──────────────────────────────────────────────────────────────
async function loadStock() {
  const cnf = document.getElementById("cnfFilter").value;
  const days = document.getElementById("daysFilter").value;
  document.getElementById("stockBody").innerHTML =
    '<tr><td colspan="9" class="loading">Loading…</td></tr>';
  try {
    const d = await apiGet(
      `/api/analytics/at-risk-stock?cnf_code=${cnf}&days=${days}`,
    );
    if (!d) return;
    document.getElementById("stockSummary").innerHTML = `
      <span class="summary-chip">Batches: <strong>${d.total_batches}</strong></span>
      <span class="summary-chip">Value: <strong>${fmtCr(d.total_value_inr)}</strong></span>`;
    document.getElementById("stockBody").innerHTML =
      d.batches
        .map(
          (b) => `<tr>
      <td>${b.cnf_code}</td><td>${escH(b.cnf_city)}</td>
      <td>${b.sku_code}</td><td>${escH(b.product)}</td>
      <td style="font-family:monospace">${b.batch_no}</td>
      <td>${b.expiry_date}</td>
      <td>${daysTag(b.days_to_expiry)}</td>
      <td>${fmt(b.qty_packs)}</td>
      <td>₹${fmt(b.value_inr)}</td>
      <td><span class="tag ${b.recommend_redistribute ? "warn" : "ok"}">${b.recommend_redistribute ? "Redistribute" : "Monitor"}</span></td>
    </tr>`,
        )
        .join("") || '<tr><td colspan="10">No batches found.</td></tr>';
  } catch (e) {
    showToast(e.message, "error");
  }
}
document.getElementById("loadStock")?.addEventListener("click", loadStock);
document.getElementById("cnfFilter")?.addEventListener("change", loadStock);
document.getElementById("daysFilter")?.addEventListener("change", loadStock);

// ── Fill Rate ──────────────────────────────────────────────────────────────────
async function loadFillRate() {
  const body = document.getElementById("fillRateBody");
  body.innerHTML = '<div class="loading">Loading…</div>';
  try {
    const d = await apiGet("/api/fill-rate");
    if (!d) return;
    body.innerHTML = `
      <div class="summary-chip" style="margin-bottom:14px;display:inline-block">
        Overall: <strong>${d.overall_fill_rate_pct}%</strong>
        <span style="font-size:11px;color:var(--text-3)"> Target: 96%</span>
      </div>
      <div class="bar-chart">${d.by_cnf
        .map(
          (r) => `
        <div class="bar-row">
          <div class="bar-label">${r.cnf_code}</div>
          <div class="bar-track"><div class="bar-fill ${r.fill_rate_pct < 88 ? "danger" : r.fill_rate_pct < 93 ? "warn" : "success"}" style="width:${r.fill_rate_pct}%"></div></div>
          <div class="bar-val">${r.fill_rate_pct}%</div>
        </div>
        <div style="font-size:11px;color:var(--text-3);padding-left:170px;margin-top:-2px;margin-bottom:4px">
          Ordered: ${fmt(r.ordered_qty)} · Invoiced: ${fmt(r.invoiced_qty)} · Unfilled: ${fmt(r.unfilled_qty)}
        </div>`,
        )
        .join("")}
      </div>`;
  } catch (e) {
    showToast(e.message, "error");
  }
}

// ── Stockist Risk ──────────────────────────────────────────────────────────────
async function loadStockistRisk() {
  const body = document.getElementById("stockistRiskBody");
  body.innerHTML = '<div class="loading">Loading…</div>';
  try {
    const d = await apiGet(
      "/api/analytics/stockist-risk?min_score=25&limit=100",
    );
    if (!d) return;
    body.innerHTML = `<div class="table-wrap"><table class="data-table">
      <thead><tr><th>Code</th><th>Name</th><th>CNF</th><th>Score</th><th>Claim Rate</th><th>Claim INR</th><th>Zero-Inv INR</th><th>Dup Credit</th><th>Signals</th></tr></thead>
      <tbody>${d.profiles
        .map(
          (p) => `<tr>
        <td>${p.stockist_code}</td>
        <td>${escH(p.stockist_name)}</td>
        <td>${p.cnf_code}</td>
        <td><span class="tag ${p.risk_score >= 50 ? "danger" : p.risk_score >= 25 ? "warn" : "ok"}">${p.risk_score}</span></td>
        <td>${p.claim_rate_pct}%</td>
        <td>₹${fmt(p.total_claim_inr)}</td>
        <td>₹${fmt(p.zero_inv_inr)}</td>
        <td>₹${fmt(p.dup_credit_inr)}</td>
        <td>${p.signals.map((s) => `<span class="flag-pill">${s}</span>`).join("")}</td>
      </tr>`,
        )
        .join("")}
      </tbody></table></div>`;
  } catch (e) {
    showToast(e.message, "error");
    body.innerHTML = '<div class="loading">Failed.</div>';
  }
}

// ── Ask AI (secure) ────────────────────────────────────────────────────────────
const chatWindow = document.getElementById("chatWindow");
function addBubble(text, role) {
  const d = document.createElement("div");
  d.className = `chat-bubble ${role}`;
  d.textContent = text;
  chatWindow.appendChild(d);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return d;
}
function addAIBubble(data) {
  const d = document.createElement("div");
  d.className = "chat-bubble ai";
  const main = document.createElement("div");
  main.textContent = data.answer;
  d.appendChild(main);

  // Blocked indicator
  if (data.blocked) {
    const blk = document.createElement("div");
    blk.style.cssText =
      "margin-top:8px;padding:4px 10px;background:#ef444420;border-radius:4px;font-size:11px;color:var(--danger)";
    blk.textContent = "⛔ Blocked by input guardrail";
    d.appendChild(blk);
  }

  // Guardrail flags (monitoring transparency)
  if (data.flags && data.flags.length > 0) {
    const fg = document.createElement("div");
    fg.style.cssText = "margin-top:6px;font-size:10px;color:var(--warn)";
    fg.textContent = "⚠ Guardrails: " + data.flags.join(", ");
    d.appendChild(fg);
  }

  if (data.evidence?.length) {
    const ev = document.createElement("div");
    ev.className = "evidence";
    ev.textContent =
      "🔍 " +
      data.evidence.map((e) => e.tool).join(", ") +
      ` · ${data.model_calls} call${data.model_calls !== 1 ? "s" : ""}`;
    d.appendChild(ev);
  }
  chatWindow.appendChild(d);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}
document.getElementById("chatForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("chatInput");
  const q = input.value.trim();
  if (!q) return;
  input.value = "";
  addBubble(q, "user");
  const thinking = addBubble("Analysing…", "thinking");
  try {
    const d = await apiPost("/api/chat/ask", { question: q });
    thinking.remove();
    if (d?.error) addBubble("Error: " + d.error, "ai");
    else if (d) addAIBubble(d);
  } catch (err) {
    thinking.remove();
    addBubble("Error: " + err.message, "ai");
  }
});
document.querySelectorAll(".sq").forEach((b) =>
  b.addEventListener("click", () => {
    document.getElementById("chatInput").value = b.dataset.q;
    document.getElementById("chatForm").dispatchEvent(new Event("submit"));
  }),
);

// ── Admin ──────────────────────────────────────────────────────────────────────
async function loadAdmin() {
  try {
    const [history, users] = await Promise.all([
      apiGet("/api/admin/batch-history?limit=5"),
      apiGet("/api/admin/users"),
    ]);
    if (history) {
      document.getElementById("batchHistory").innerHTML = history
        .map(
          (r) => `
        <div class="result-row">
          <strong>${new Date(r.run_at).toLocaleString()}</strong> —
          INR ${fmtL(r.total_addressable_inr)} addressable ·
          ${r.duplicate_groups} dup groups ·
          ${r.high_risk_stockists} high-risk stockists
        </div>`,
        )
        .join("");
    }
    if (users) {
      document.getElementById("userTable").innerHTML = users
        .map(
          (u) => `<tr>
        <td>${u.id}</td><td>${u.username}</td><td>${u.email}</td>
        <td><span class="tag ok">${u.role}</span></td>
        <td>${u.cnf_code || "—"}</td>
        <td><span class="tag ${u.is_active ? "ok" : "danger"}">${u.is_active ? "Active" : "Disabled"}</span></td>
      </tr>`,
        )
        .join("");
    }
  } catch (e) {
    showToast(e.message, "error");
  }
}
document.getElementById("runBatchBtn")?.addEventListener("click", async () => {
  const btn = document.getElementById("runBatchBtn");
  btn.textContent = "Running…";
  btn.disabled = true;
  try {
    const d = await apiPost("/api/admin/run-batch", {});
    if (d)
      showToast(
        `Batch complete — INR ${fmtL(d.total_addressable_inr)} addressable`,
        "success",
      );
    loadAdmin();
    checkHealth();
  } catch (e) {
    showToast(e.message, "error");
  }
  btn.textContent = "Run Batch Now";
  btn.disabled = false;
});

// ── Report ─────────────────────────────────────────────────────────────────────
async function loadReport() {
  const body = document.getElementById("reportBody");
  body.innerHTML = '<div class="loading">Loading report…</div>';
  try {
    const r = await fetch("/RAPID_REPORT.md");
    if (!r.ok) throw new Error("Report not found");
    const md = await r.text();
    // Simple markdown renderer (headings, bold, tables, lists)
    body.innerHTML = renderMd(md);
  } catch (e) {
    body.innerHTML =
      '<div class="loading">Report not generated yet. Run a batch first.</div>';
  }
}
function renderMd(md) {
  return md
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, "<code>$1</code>")
    .replace(/^---$/gm, "<hr>")
    .replace(/^\| (.+) \|$/gm, (row) => {
      const cells = row.slice(2, -2).split(" | ");
      return (
        "<tr>" + cells.map((c) => `<td>${c.trim()}</td>`).join("") + "</tr>"
      );
    })
    .replace(
      /(<tr>.*<\/tr>\n?)+/gs,
      (m) =>
        `<div class="table-wrap"><table class="data-table">${m}</table></div>`,
    )
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/gs, (m) => `<ul>${m}</ul>`)
    .replace(/\n\n/g, "</p><p>")
    .replace(/^(?!<[h|t|u|l|h])(.+)$/gm, "<p>$1</p>");
}

// ── Workflow ────────────────────────────────────────────────────────────────
function loadWorkflow() {
  const wrap = document.getElementById("workflowBody");
  if (!wrap) return;
  wrap.innerHTML = `
    <div style="text-align:center">
      <img src="workflow.svg" alt="Sankalp AI Agent Workflow"
           style="max-width:680px;width:100%;border:1px solid var(--border);border-radius:var(--radius)"/>
    </div>
    <div class="card mt-16" style="overflow:visible">
      <div class="card-header">Guardrail Summary</div>
      <div class="card-body" style="line-height:1.8;font-size:13px;color:var(--text-2)">
        <p><strong style="color:var(--accent)">3 guardrail gates</strong> protect every request:</p>
        <ul style="padding-left:20px;margin-top:8px">
          <li><strong>① input_guard</strong> — blocks prompt injection, off-domain questions, length > 800 chars</li>
          <li><strong>② tool_guard</strong> — validates every tool call against an allow-list of 7 tools; blocks unknown tools and injected arguments</li>
          <li><strong>③ output_guard</strong> — scrubs internal paths, DB filenames, bcrypt hashes, API keys, connection strings; truncates answers > 4000 chars; flags bare INR numbers without tool citation</li>
        </ul>
        <p style="margin-top:12px">
          <strong>Max tool trips:</strong> 6 &nbsp; · &nbsp;
          <strong>Max question:</strong> 800 chars &nbsp; · &nbsp;
          <strong>Max answer:</strong> 4000 chars &nbsp; · &nbsp;
          <strong>Audit logged:</strong> every interaction
        </p>
      </div>
    </div>`;
}

// ── Quarter Spike load ────────────────────────────────────────────────────────
document.getElementById("loadSpike")?.addEventListener("click", async () => {
  const sku = document.getElementById("skuFilterSpike").value;
  const wrap = document.getElementById("spikeResultWrap");
  wrap.innerHTML = '<div class="loading">Analysing…</div>';
  try {
    const d = await apiGet(`/api/quarter-spike?sku_code=${sku}`);
    if (!d || d.found === false) {
      wrap.innerHTML = '<div class="loading">No data.</div>';
      return;
    }
    const rCls =
      d.risk_level === "HIGH"
        ? "danger"
        : d.risk_level === "MEDIUM"
          ? "warn"
          : "ok";
    const qs = d.phasing_by_quarter || [];
    const maxH = 140;
    const maxP = Math.max(...qs.map((q) => q.spike_pct), 1);
    wrap.innerHTML = `
      <div class="result-row" style="margin-bottom:12px">
        <strong>${escH(d.product || d.sku_code)}</strong> &nbsp;
        <span class="tag ${rCls}">${d.risk_level} RISK</span> &nbsp;
        Avg last-9d spike: <strong>${d.avg_spike_pct_last4q}%</strong> &nbsp;
        Projected return: <strong>₹${fmt(d.projected_expiry_return_inr)}</strong>
      </div>
      <div class="spike-chart" style="margin:0">
        ${qs
          .map((q) => {
            const h = Math.max(Math.round((q.spike_pct / maxP) * maxH), 4);
            const c =
              q.spike_pct > 30 ? "high" : q.spike_pct > 20 ? "med" : "low";
            return `<div class="spike-col">
            <div class="spike-bar ${c}" style="height:${h}px" data-tip="${q.quarter}: ${q.spike_pct}%"></div>
            <div class="spike-label">${q.quarter.slice(2)}</div>
          </div>`;
          })
          .join("")}
      </div>`;
  } catch (e) {
    wrap.innerHTML = `<div class="loading">Error: ${escH(e.message)}</div>`;
  }
});

document
  .getElementById("menuBtn")
  ?.addEventListener("click", () =>
    document.getElementById("sidebar").classList.toggle("open"),
  );

// ── My Claims ────────────────────────────────────────────────────────────────
let _claimsSessionId = "";

document
  .getElementById("claimsChatForm")
  ?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = document.getElementById("claimsChatInput");
    const q = input.value.trim();
    if (!q) return;
    input.value = "";

    const win = document.getElementById("claimsChatWindow");
    const ub = document.createElement("div");
    ub.className = "chat-bubble user";
    ub.textContent = q;
    win.appendChild(ub);
    win.scrollTop = win.scrollHeight;

    const thinking = document.createElement("div");
    thinking.className = "chat-bubble thinking";
    thinking.textContent = "Processing…";
    win.appendChild(thinking);

    try {
      const d = await apiPost("/api/claims/chat", {
        message: q,
        session_id: _claimsSessionId,
      });
      thinking.remove();
      if (!d) return;
      _claimsSessionId = d.session_id;
      const ab = document.createElement("div");
      ab.className = "chat-bubble ai";
      ab.textContent = d.answer;
      if (d.intent && d.intent !== "general") {
        const tag = document.createElement("div");
        tag.style.cssText = "margin-top:6px;font-size:10px;color:var(--text-3)";
        tag.textContent = "Intent: " + d.intent;
        ab.appendChild(tag);
      }
      win.appendChild(ab);
      win.scrollTop = win.scrollHeight;
      // Refresh claim list if a claim was created
      if (d.claim_no) loadMyClaimsList();
    } catch (err) {
      thinking.remove();
      const eb = document.createElement("div");
      eb.className = "chat-bubble ai";
      eb.textContent = "Error: " + err.message;
      win.appendChild(eb);
    }
  });

document.querySelectorAll("[data-cq]").forEach((b) =>
  b.addEventListener("click", () => {
    document.getElementById("claimsChatInput").value = b.dataset.cq;
    document
      .getElementById("claimsChatForm")
      .dispatchEvent(new Event("submit"));
  }),
);

async function loadMyClaims() {
  await loadMyClaimsList();
}

async function loadMyClaimsList() {
  const filter = document.getElementById("myClaimsFilter")?.value || "";
  const body = document.getElementById("myClaimsBody");
  if (!body) return;
  body.innerHTML = '<tr><td colspan="8" class="loading">Loading…</td></tr>';
  try {
    const d = await apiGet(`/api/claims/my?status_filter=${filter}`);
    if (!d) return;
    document.getElementById("myClaimsSummary").innerHTML = `
      <span class="summary-chip">Claims: <strong>${d.total}</strong></span>
      <span class="summary-chip">Total Value: <strong>₹${fmt(d.total_claim_value_inr)}</strong></span>
      <span class="summary-chip">Total Recovery: <strong>₹${fmt(d.total_recovery_inr)}</strong></span>`;
    body.innerHTML =
      d.claims
        .map(
          (c) => `<tr>
      <td style="font-family:monospace;font-size:11px">${escH(c.claim_no)}</td>
      <td><span class="tag ${c.status === "Credited" ? "ok" : c.status === "Submitted" ? "warn" : c.status === "Rejected" ? "danger" : "ok"}">${c.status}</span></td>
      <td style="font-family:monospace">${escH(c.batch_no)}</td>
      <td>${escH(c.claim_type)}</td>
      <td>₹${fmt(c.claim_value_inr)}</td>
      <td>₹${fmt(c.recovery_amount_inr)}</td>
      <td><span class="tag ${c.risk_score >= 50 ? "danger" : c.risk_score >= 25 ? "warn" : "ok"}">${c.risk_score}</span></td>
      <td style="font-size:11px">${c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}</td>
    </tr>`,
        )
        .join("") ||
      '<tr><td colspan="8">No claims yet. Use the chat to create one.</td></tr>';
  } catch (e) {
    showToast(e.message, "error");
  }
}
document
  .getElementById("myClaimsFilter")
  ?.addEventListener("change", loadMyClaimsList);

// ── Auditor Review ───────────────────────────────────────────────────────────
async function loadAuditorClaims() {
  const body = document.getElementById("auditorBody");
  if (!body) return;
  body.innerHTML = '<tr><td colspan="13" class="loading">Loading…</td></tr>';
  const st = document.getElementById("auditorStatusFilter")?.value || "";
  const us = document.getElementById("auditorUserFilter")?.value || "";
  const rs = document.getElementById("auditorRiskFilter")?.value || "0";
  try {
    const d = await apiGet(
      `/api/claims/all?status_filter=${st}&submitted_by=${encodeURIComponent(us)}&min_risk=${rs}&limit=200`,
    );
    if (!d) return;
    body.innerHTML =
      d.claims
        .map(
          (c) => `<tr>
      <td style="font-family:monospace;font-size:11px">${escH(c.claim_no)}</td>
      <td>${escH(c.submitted_by)}</td>
      <td><span class="tag ${c.status === "Credited" ? "ok" : c.status === "Submitted" ? "warn" : c.status === "Rejected" ? "danger" : "ok"}">${c.status}</span></td>
      <td>${escH(c.stockist_code)}</td>
      <td style="font-family:monospace">${escH(c.batch_no)}</td>
      <td>${escH(c.sku_code)}</td>
      <td>${escH(c.claim_type)}</td>
      <td>${fmt(c.qty_claimed)}</td>
      <td>₹${fmt(c.claim_value_inr)}</td>
      <td>₹${fmt(c.recovery_amount_inr)}</td>
      <td><span class="tag ${c.risk_score >= 50 ? "danger" : c.risk_score >= 25 ? "warn" : "ok"}">${c.risk_score}</span></td>
      <td>${(c.risk_flags || []).map((f) => `<span class="flag-pill">${escH(f)}</span>`).join("")}</td>
      <td>
        <button class="btn-secondary" style="font-size:10px;padding:3px 8px" onclick="reviewClaim(${c.id},'Approved')">Approve</button>
        <button class="btn-secondary" style="font-size:10px;padding:3px 8px" onclick="reviewClaim(${c.id},'Rejected')">Reject</button>
      </td>
    </tr>`,
        )
        .join("") || '<tr><td colspan="13">No claims found.</td></tr>';
  } catch (e) {
    showToast(e.message, "error");
  }
}
window.reviewClaim = async function (id, decision) {
  try {
    await apiPost(`/api/claims/${id}/review`, { decision, notes: "" });
    showToast(`Claim ${decision.toLowerCase()}`, "success");
    loadAuditorClaims();
  } catch (e) {
    showToast(e.message, "error");
  }
};
document
  .getElementById("loadAuditorClaims")
  ?.addEventListener("click", loadAuditorClaims);

// ── CFO Recovery Benchmark ──────────────────────────────────────────────────
async function loadBenchmark() {
  try {
    const d = await apiGet("/api/claims/benchmark");
    if (!d) return;

    // KPI cards
    const bm = d.benchmark;
    document.getElementById("benchmarkKpis").innerHTML = [
      {
        label: "Total Addressable",
        val: fmtCr(bm.total_addressable_inr),
        cls: "danger",
      },
      {
        label: "Already Recovered",
        val: fmtL(bm.recovered_inr),
        cls: "success",
      },
      {
        label: "Recoverable Now",
        val: fmtL(bm.recoverable_now_inr),
        cls: "warn",
      },
      { label: "At-Risk (90d)", val: fmtCr(bm.at_risk_inr), cls: "warn" },
      {
        label: "Projected Annual",
        val: fmtCr(bm.projected_annual_inr),
        cls: "danger",
      },
    ]
      .map(
        (k) => `<div class="kpi ${k.cls}">
      <div class="kpi-label">${k.label}</div><div class="kpi-value">${k.val}</div>
    </div>`,
      )
      .join("");

    // Benchmark table
    const rows = [];
    if (d.batch_analysis) {
      rows.push({
        cat: "Duplicate excess credits (recoverable)",
        amt: d.batch_analysis.duplicate_excess_inr,
        type: "Recover",
        src: "Batch analysis",
      });
      rows.push({
        cat: "Zero-invoice match (investigate)",
        amt: d.batch_analysis.zero_invoice_inr,
        type: "Investigate",
        src: "Batch analysis",
      });
      rows.push({
        cat: "Qty overclaim excess",
        amt: d.batch_analysis.qty_overclaim_inr,
        type: "Recover",
        src: "Batch analysis",
      });
      rows.push({
        cat: "At-risk inventory 0-30d",
        amt: d.batch_analysis.at_risk_30d_inr,
        type: "Save",
        src: "CNF snapshot",
      });
      rows.push({
        cat: "At-risk inventory 0-60d",
        amt: d.batch_analysis.at_risk_60d_inr,
        type: "Save",
        src: "CNF snapshot",
      });
      rows.push({
        cat: "At-risk inventory 0-90d",
        amt: d.batch_analysis.at_risk_90d_inr,
        type: "Save",
        src: "CNF snapshot",
      });
      rows.push({
        cat: "Total addressable",
        amt: d.batch_analysis.total_addressable_inr,
        type: "Total",
        src: "Batch analysis",
      });
    }
    if (d.user_claims) {
      const uc = d.user_claims;
      rows.push({
        cat: "User claims — pending review",
        amt: uc.pending_value_inr,
        type: "Pending",
        src: "AI agent",
      });
      rows.push({
        cat: "User claims — approved",
        amt: uc.approved_value_inr,
        type: "Approved",
        src: "AI agent",
      });
      rows.push({
        cat: "User claims — recovery from blocks",
        amt: uc.recovery_from_blocks_inr,
        type: "Recovered",
        src: "AI agent",
      });
    }

    document.getElementById("benchmarkBody").innerHTML = rows
      .map(
        (r) => `<tr>
      <td>${escH(r.cat)}</td>
      <td>₹${fmt(r.amt)}</td>
      <td><span class="tag ${r.type === "Recovered" ? "ok" : r.type === "Pending" ? "warn" : "danger"}">${r.type}</span></td>
      <td style="font-size:11px;color:var(--text-3)">${escH(r.src)}</td>
    </tr>`,
      )
      .join("");
  } catch (e) {
    showToast(e.message, "error");
  }
}

// ── Init ───────────────────────────────────────────────────────────────────────
showLogin();
