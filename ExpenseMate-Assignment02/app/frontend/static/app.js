/* ============================================================
   ExpenseMate — Client-side controller (JWT Authenticated)
   Includes FULL multi-currency support: base-currency switching,
   converted analytics, a quick converter and an exchange-rate table.
   ============================================================ */
let state = { uid: null, month: defaultMonth(), base: 'USD', symbol: '$', currencies: [] };
let pieChart = null, lineChart = null;

function defaultMonth() { return new Date().toISOString().slice(0, 7); }

/* Updated Header Helper: Passes JWT Bearer token instead of X-User-Id */
function hdr() {
  const token = localStorage.getItem('jwt_token') || '';
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };
}

function setMsg(el, text, ok) {
  el.textContent = text;
  el.className = 'msg ' + (ok === undefined ? '' : (ok ? 'ok' : 'err'));
}

/* Format money in the user's BASE currency */
function fmt(n) {
  return state.symbol + (+n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/* Format money in an arbitrary (native) currency */
function fmtCcy(n, code, symbol) {
  const s = symbol || code || '';
  return s + (+n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function $(id) { return document.getElementById(id); }

/* ---------- AUTHENTICATION (JWT) ---------- */
async function register() {
  const msg = $('authMsg');
  const r = await fetch('/api/register', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({
      username: $('user').value,
      password: $('pass').value,
      base_currency: $('regCur').value
    })
  });

  const d = await r.json().catch(() => ({}));
  if (r.ok) {
    // Automatically save token and log in upon successful registration
    if (d.access_token) {
      localStorage.setItem('jwt_token', d.access_token);
      setupUserSession(d);
    } else {
      setMsg(msg, 'Registered — please log in.', true);
    }
  } else {
    setMsg(msg, d.error || 'Registration failed.', false);
  }
}

async function login() {
  const msg = $('authMsg');
  const r = await fetch('/api/login', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ username: $('user').value, password: $('pass').value })
  });

  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    setMsg(msg, d.error || 'Invalid credentials.', false);
    return;
  }

  // Save JWT Token to localStorage
  if (d.access_token) {
    localStorage.setItem('jwt_token', d.access_token);
  }

  setupUserSession(d);
}

async function setupUserSession(userData) {
  state.uid = userData.user_id;
  state.base = userData.base_currency || 'USD';
  state.symbol = userData.base_symbol || '$';

  if (userData.username) {
    $('whoLabel').textContent = 'Hi, ' + userData.username;
  }

  $('auth').classList.add('hidden');
  $('app').classList.remove('hidden');

  await loadCurrencies();
  populateMonths();
  bindNav();
  refresh();
}

function logout() {
  localStorage.removeItem('jwt_token');
  state.uid = null;
  $('app').classList.add('hidden');
  $('auth').classList.remove('hidden');
}

/* Intercept 401 Unauthenticated responses across API calls */
function checkAuth(response) {
  if (response.status === 401) {
    logout();
    setMsg($('authMsg'), 'Session expired. Please log in again.', false);
    return false;
  }
  return true;
}
/* ---------- MULTI-CURRENCY: rates, selectors, converter ---------- */
async function loadCurrencies() {
   // Check if a token actually exists before attaching it
  const token = localStorage.getItem('jwt_token');
  const fetchOptions = token ? { headers: hdr() } : {};

  // Fetch currencies safely
  const r = await fetch('/api/currencies', fetchOptions);

  // If the server rejects an expired token with a 422/401, re-try strictly as a guest visitor
  if (r.status === 422 || r.status === 401) {
    const guestResponse = await fetch('/api/currencies');
    var d = await guestResponse.json().catch(() => ({}));
  } else {
    var d = await r.json().catch(() => ({}));
  }
  state.currencies = d.currencies;
  state.base = d.base_currency || state.base;
  state.symbol = d.base_symbol || state.symbol;

  fillSelect($('txCur'), d.currencies, d.base_currency);
  fillSelect($('baseCurSel'), d.currencies, d.base_currency);
  fillSelect($('convFrom'), d.currencies, 'USD');
  fillSelect($('convTo'), d.currencies, d.base_currency);

  // Populate registration dropdown on initial page visit
  if ($('regCur')) fillSelect($('regCur'), d.currencies, 'USD');

  if ($('baseChip')) $('baseChip').textContent = state.symbol + ' ' + state.base;
  if ($('ratesBaseLabel')) $('ratesBaseLabel').textContent = 'vs ' + state.base;
  renderRates(d.table, d.base_currency);
  doConvert();
}

function fillSelect(sel, list, selected) {
  if (!sel) return;
  sel.innerHTML = '';
  list.forEach(c => {
    const o = document.createElement('option');
    o.value = c; o.textContent = c;
    sel.appendChild(o);
  });
  if (selected && list.includes(selected)) sel.value = selected;
}

async function saveBaseCurrency() {
  const code = $('baseCurSel').value;
  const r = await fetch('/api/settings/base_currency', {
    method: 'POST',
    headers: hdr(),
    body: JSON.stringify({ base_currency: code })
  });
  if (!checkAuth(r)) return;

  const d = await r.json();
  if (!r.ok) {
    setMsg($('baseMsg'), d.error || 'Could not change currency.', false);
    return;
  }

  // 1. Explicitly update local app state with what the database returned
  state.base = d.base_currency;
  state.symbol = d.base_symbol;

  setMsg($('baseMsg'), `Base currency is now ${state.base} — everything re-converted ✓`, true);

  // 2. Refresh lists but ensure state parameters aren't implicitly wiped
  await loadCurrencies();

  // 3. Force state persistence over fallback definitions manually if needed
  state.base = d.base_currency;
  state.symbol = d.base_symbol;

  refresh();
}

async function doConvert() {
  const body = { amount: $('convAmt').value || 0, from: $('convFrom').value, to: $('convTo').value };
  const r = await fetch('/api/convert', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body)
  });
  const d = await r.json();
  $('convResult').innerHTML = r.ok
    ? `${d.from_symbol}${(+d.amount).toLocaleString()} ${d.from} &nbsp;=&nbsp; <strong>${d.to_symbol}${(+d.result).toLocaleString(undefined,{maximumFractionDigits:4})} ${d.to}</strong>`
    : '—';
}

function renderRates(table, base) {
  const tb = $('ratesTable');
  if (!table) return;
  tb.innerHTML = table.map(x => `
    <tr${x.code === base ? ' class="base-row"' : ''}>
      <td><strong>${x.code}</strong></td><td>${x.name}</td>
      <td>${x.symbol}${x.per_base}</td><td>${x.symbol}${x.one_base_equals.toLocaleString()}</td>
    </tr>`).join('');
}

function renderByCurrency(byCcy) {
  const box = $('byCurrencyBox');
  const keys = Object.keys(byCcy || {});
  if (!keys.length) { box.innerHTML = '<div class="none">No transactions this month.</div>'; return; }
  box.innerHTML = keys.map(c => {
    const v = byCcy[c];
    return `<div class="ccy-card">
        <div class="ccy-head"><span class="ccy-code">${v.symbol} ${c}</span>
          <span class="ccy-count">${v.count} tx</span></div>
        <div class="ccy-line">Income <strong class="am-pos">${fmtCcy(v.income, c, v.symbol)}</strong></div>
        <div class="ccy-line">Expense <strong class="am-neg">${fmtCcy(v.expense, c, v.symbol)}</strong></div>
      </div>`;
  }).join('');
}

/* ---------- MONTHS ---------- */
function populateMonths() {
  const sel = $('monthSel');
  sel.innerHTML = '';
  for (let i = 0; i < 8; i++) {
    const d = new Date(); d.setMonth(d.getMonth() - i);
    const m = d.toISOString().slice(0, 7);
    const o = document.createElement('option'); o.value = m; o.textContent = m; sel.appendChild(o);
  }
  sel.value = state.month;
  sel.onchange = () => { state.month = sel.value; refresh(); };
}

/* ---------- NAVIGATION BAR ---------- */
function bindNav() {
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      const target = $(link.getAttribute('data-target'));
      if (!target) return;
      document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
      link.classList.add('active');
      target.classList.remove('slide-section');
      void target.offsetWidth;
      target.classList.add('slide-section');
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}

/* ---------- REFRESH DASHBOARD ---------- */
async function refresh() {
  const r = await fetch(`/api/summary?month=${state.month}`, { headers: hdr() });
  if (!checkAuth(r)) return;

  const d = await r.json();
  state.base = d.base_currency || state.base;
  state.symbol = d.base_symbol || state.symbol;
  $('baseChip').textContent = state.symbol + ' ' + state.base;
  $('dashCurrencyNote').textContent =
    d.foreign_count ? `All amounts shown in ${state.base} (${d.foreign_count} foreign-currency record(s) converted)`
                    : `Reporting in ${state.base}`;

  $('cIncome').textContent = fmt(d.total_income);
  $('cExpense').textContent = fmt(d.total_expense);
  $('cBalance').textContent = fmt(d.balance);
  $('cAlerts').textContent = d.budget.alerts.length;

  renderAlerts(d.budget.alerts);
  renderBudgetsDetail(d.budget.status);
  renderCostBudgets(d.budget.status);
  renderByCurrency(d.by_currency);
  drawPie(d.by_category);
  drawTrend(d.trend);
  loadTransactions();
  populateBudgetCats();
}

function renderAlerts(alerts) {
  const box = $('alertBox');
  box.innerHTML = '<h3>Budget Alerts</h3>';
  if (!alerts.length) { box.innerHTML += '<div class="none">✅ No budget alerts — you are on track!</div>'; return; }
  alerts.forEach(a => { box.innerHTML += `<div class="alert ${a.level}">${a.message}</div>`; });
}

function renderCostBudgets(status) {
  const box = $('budgetList');
  box.innerHTML = '';
  if (!status.length) { box.innerHTML = '<div class="none">No budgets set for this month.</div>'; return; }
  status.forEach(b => {
    box.innerHTML += `
      <div class="bg-item">
        <span class="bg-name">${b.category}</span>
        <div class="bg-bar"><div class="bg-fill ${b.level}" style="width:${Math.min(b.ratio*100,100)}%"></div></div>
        <span class="bg-nums">${fmt(b.spent)} / ${fmt(b.limit)}</span>
      </div>`;
  });
}

function renderBudgetsDetail(status) {
  const box = $('budgetsDetail');
  if (!status.length) { box.innerHTML = '<div class="none">No budgets set for this month yet.</div>'; return; }
  box.innerHTML = status.map(b => {
    const rem = b.remaining >= 0
      ? `<span class="ok">Remaining: ${fmt(b.remaining)}</span>`
      : `<span class="bad">Over by: ${fmt(-b.remaining)}</span>`;
    const conv = b.converted
      ? `<div class="budget-meta">budget set in ${b.budget_currency}
           (${fmtCcy(b.budget_amount_native, b.budget_currency)} → converted to ${b.currency})</div>`
      : '';
    return `<div class="budget-row">
        <div class="budget-top">
          <strong>${b.category}</strong>
          <div>
            ${rem}
            <span class="del-budget" onclick="delBudgetByCategory('${b.category}')" title="Delete Budget">✕</span>
          </div>
        </div>
        <div class="bg-bar"><div class="bg-fill ${b.level}" style="width:${Math.min(b.ratio*100,100)}%"></div></div>
        <div class="budget-meta">spent ${fmt(b.spent)} of ${fmt(b.limit)} · ${Math.round(b.ratio*100)}%</div>
        ${conv}
      </div>`;
  }).join('');
}

/* ---------- CHARTS (Chart.js) ---------- */
function drawPie(byCat) {
  const keys = Object.keys(byCat || {});
  const empty = $('pieEmpty'), canvas = $('pieChart');
  if (!keys.length) {
    if (pieChart) { pieChart.destroy(); pieChart = null; }
    canvas.style.display = 'none'; empty.classList.remove('hidden'); return;
  }
  canvas.style.display = ''; empty.classList.add('hidden');
  if (pieChart) pieChart.destroy();
  pieChart = new Chart(canvas, {
    type: 'doughnut',
    data: { labels: keys, datasets: [{ data: keys.map(k => byCat[k]), backgroundColor: palette(keys.length) }] },
    options: { maintainAspectRatio: false, responsive: true,
      plugins: {
        legend: { position: 'right', labels: { color: '#5b6b8c', boxWidth: 12, font: {size:11} } },
        tooltip: { callbacks: { label: c => ` ${c.label}: ${fmt(c.parsed)}` } }
      } }
  });
}

function drawTrend(trend) {
  const labels = (trend || []).map(t => t[0]);
  const empty = $('lineEmpty'), canvas = $('lineChart');
  if (!labels.length) {
    if (lineChart) { lineChart.destroy(); lineChart = null; }
    canvas.style.display = 'none'; empty.classList.remove('hidden'); return;
  }
  canvas.style.display = ''; empty.classList.add('hidden');
  if (lineChart) lineChart.destroy();
  lineChart = new Chart(canvas, {
    type: 'line',
    data: { labels, datasets: [
      { label: 'Income', data: trend.map(t => t[1]), borderColor: '#6fae8f',
        backgroundColor: 'rgba(111,174,143,.15)', tension: .3, fill: true, pointRadius: 3 },
      { label: 'Expense', data: trend.map(t => t[2]), borderColor: '#7a9bd0',
        backgroundColor: 'rgba(122,155,208,.12)', tension: .3, fill: true, pointRadius: 3 } ]},
    options: { maintainAspectRatio: false, responsive: true,
      plugins: { legend: { labels: { color: '#5b6b8c', boxWidth: 12, font: {size:11} } },
        tooltip: { callbacks: { label: c => ` ${c.dataset.label}: ${fmt(c.parsed.y)}` } } },
      scales: { x: { ticks: { color: '#7c8aa5' }, grid: { color: '#e7ecf5' } },
                y: { ticks: { color: '#7c8aa5', callback: v => state.symbol + v }, grid: { color: '#e7ecf5' } } } }
  });
}

function palette(n) {
  const c = ['#7a9bd0','#6fae8f','#f2c07a','#e28ba6','#8fa3c9','#9bc6b0','#d9c2a0','#a6b3d6'];
  return Array.from({length:n}, (_,i) => c[i % c.length]);
}

/* ---------- TRANSACTIONS ---------- */
function updateCategories() {
  const typeSelect = document.getElementById("txType");
  const catSelect = document.getElementById("txCat");
  if (!typeSelect || !catSelect) return;

  const selectedType = typeSelect.value;
  catSelect.innerHTML = "";

  const defaultCategories = {
    expense: ["Food", "Groceries", "Rent", "Utilities", "Dining","Shopping" ,"Entertainment", "Fitness", "Transport", "Misc"],
    income: ["Salary", "Freelance", "Investments", "Gifts", "Other"]
  };

  defaultCategories[selectedType].forEach(category => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    catSelect.appendChild(option);
  });
}

window.addEventListener("DOMContentLoaded", () => {
  updateCategories();
  const txType = document.getElementById("txType");
  if (txType) txType.onchange = updateCategories;
});

async function addTx() {
  const msg = $('txMsg');
  const body = {
    date: $('txDate').value || new Date().toISOString().slice(0,10),
    description: $('txDesc').value,
    amount: $('txAmt').value,
    type: $('txType').value,
    category: $('txCat').value,
    currency: $('txCur').value
  };

  const r = await fetch('/api/transactions', {
    method: 'POST',
    headers: hdr(),
    body: JSON.stringify(body)
  });

  if (!checkAuth(r)) return;

  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    setMsg(msg, d.error || 'Error adding.', false);
    return;
  }

  setMsg(msg, `Added ✓ — recorded in ${body.currency}, reported in ${state.base}.`, true);
  ['txDesc', 'txAmt'].forEach(id => $(id).value = '');

  if (d.alert) {
    alert(`[BUDGET ALERT - ${d.alert.level.toUpperCase()}] ${d.alert.message}`);
  }

  refresh();
}

async function loadTransactions() {
  const r = await fetch(`/api/transactions?month=${state.month}`, { headers: hdr() });
  if (!checkAuth(r)) return;

  const rows = await r.json();
  $('txCount').textContent = rows.length + ' record(s) · amounts converted to ' + state.base;
  const tb = $('txTable');
  tb.innerHTML = rows.map(t => `
    <tr>
      <td>${t.date}</td>
      <td>${t.description}</td>
      <td class="${t.type==='income'?'am-pos':'am-neg'}">${t.type==='income'?'+':'\u2212'}${fmtCcy(t.amount, t.currency, t.currency_symbol)}</td>
      <td>${t.currency}${t.is_foreign ? ' <span class="fx" title="Converted from '+t.currency+'">⇄</span>' : ''}</td>
      <td class="${t.type==='income'?'am-pos':'am-neg'}">${fmtCcy(t.amount_base, state.base, state.symbol)}</td>
      <td>${t.type}</td>
      <td>${t.category_name || '—'}</td>
      <td class="del" onclick="delTx(${t.id})" title="Delete">✕</td>
    </tr>`).join('') ||
    `<tr><td colspan="8" style="color:var(--muted)">No transactions.</td></tr>`;
}

async function delTx(id) {
  const r = await fetch('/api/transactions/' + id, { method: 'DELETE', headers: hdr() });
  if (checkAuth(r)) refresh();
}

/* ---------- BUDGETS ---------- */
async function setBudget() {
  const msg = $('bgMsg');
  const body = {
    category: $('bgCat').value,
    month: state.month,
    amount: $('bgAmt').value,
    currency: $('bgCur').value || $('txCur').value
  };
  const r = await fetch('/api/budgets', { method: 'POST', headers: hdr(), body: JSON.stringify(body) });
  if (!checkAuth(r)) return;

  if (!r.ok) {
    const d = await r.json().catch(()=>({}));
    setMsg(msg, d.error || 'Error.', false);
    return;
  }
  setMsg(msg, `Budget set in ${body.currency} ✓`, true);
  $('bgAmt').value = '';
  refresh();
}

async function populateBudgetCats() {
  const r = await fetch('/api/summary?month=' + state.month, { headers: hdr() });
  if (!checkAuth(r)) return;

  const d = await r.json();
  const cats = Object.keys(d.by_category || {});
  const sel = $('bgCat');
  const prev = sel.value;
  sel.innerHTML = '';
  //BudgetCategories
  cats.concat(["Food", "Groceries", "Rent", "Utilities", "Dining","Shopping" ,"Entertainment", "Fitness", "Transport", "Misc"],
    )
    .filter((v,i,a) => a.indexOf(v) === i)
    .forEach(c => { const o = document.createElement('option'); o.value = c; o.textContent = c; sel.appendChild(o); });
  if (prev) sel.value = prev;
  fillSelect($('bgCur'), state.currencies.length ? state.currencies : ['USD'], state.base);
}

async function delBudgetByCategory(categoryName) {
  if (!confirm(`Are you sure you want to delete the budget for '${categoryName}'?`)) return;

  const payload = {
    category: categoryName,
    month: state.month
  };

  const r = await fetch('/api/budgets/by-category', {
    method: 'DELETE',
    headers: hdr(),
    body: JSON.stringify(payload)
  });
  if (!checkAuth(r)) return;

  if (r.ok) {
    refresh();
  } else {
    const d = await r.json().catch(() => ({}));
    alert(d.error || 'Failed to remove budget entry.');
  }
}

/* ---------- CSV EXPORT / IMPORT ---------- */
async function exportCsv() {
  const msg = $('csvMsg');

  // Fetch the CSV directly with JWT headers attached
  const r = await fetch(`/api/export?month=${state.month}`, {
    method: 'GET',
    headers: hdr()
  });

  if (!checkAuth(r)) return;

  if (!r.ok) {
    setMsg(msg, 'Failed to export CSV.', false);
    return;
  }

  // Convert response stream to a Blob file object
  const blob = await r.blob();
  const url = window.URL.createObjectURL(blob);

  // Trigger file download dynamically in browser
  const a = document.createElement('a');
  a.href = url;
  a.download = `expensemate-${state.month}.csv`;
  document.body.appendChild(a);
  a.click();

  // Cleanup memory
  a.remove();
  window.URL.revokeObjectURL(url);

  setMsg(msg, `Exported ✓ (includes native currency + amount in ${state.base})`, true);
}

async function importCsv(ev) {
  const f = ev.target.files[0]; if (!f) return;
  let text = await f.text();

  if (text.includes('\t') && !text.includes(',')) {
    text = text.replace(/\t/g, ',');
  }

  const r = await fetch('/api/import', {
    method: 'POST',
    headers: hdr(),
    body: JSON.stringify({ csv: text })
  });
  if (!checkAuth(r)) return;

  const d = await r.json();
  if (!r.ok) { setMsg($('csvMsg'), d.error || 'Import failed.', false); return; }

  setMsg($('csvMsg'), `Imported ${d.imported} rows, skipped ${d.skipped} invalid rows ✓`, true);
  ev.target.value = '';

  setTimeout(() => { refresh(); }, 300);
}

/* ---------- INIT (Auto-login check via JWT) ---------- */
(async function init() {
  $('txDate').value = new Date().toISOString().slice(0,10);
  await loadCurrencies();
  // Check if user has an existing JWT token stored
  const token = localStorage.getItem('jwt_token');
  if (token) {
    // Attempt fetching settings to test token validity
    const r = await fetch('/api/settings', { headers: hdr() });
    if (r.ok) {
      const d = await r.json();
      setupUserSession({
        base_currency: d.base_currency,
        base_symbol: d.base_symbol
      });
      return;
    } else {
      // Invalid or expired token
      localStorage.removeItem('jwt_token');
    }
  }

})();