/* ExpenseMate — Client-side controller (the "Client" in client-server). */
let state = { uid: null, month: defaultMonth() };
let pieChart, lineChart;
const curSelect = document.getElementById('txCur');

function defaultMonth() { return new Date().toISOString().slice(0, 7); }
function hdr() { return { 'Content-Type': 'application/json', 'X-User-Id': state.uid }; }
function setMsg(el, text, ok) {
  el.textContent = text;
  el.className = 'msg ' + (ok === undefined ? '' : (ok ? 'ok' : 'err'));
}

/* ---------- auth ---------- */
async function register() {
  const msg = document.getElementById('authMsg');
  const r = await fetch('/api/register', { method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ username: user.value, password: pass.value }) });
  if (r.ok) { setMsg(msg, 'Registered — please log in.', true); } else {
    setMsg(msg, 'Registration failed or user exists.', false); }
}
async function login() {
  const msg = document.getElementById('authMsg');
  const r = await fetch('/api/login', { method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ username: user.value, password: pass.value }) });
  const d = await r.json();
  if (!r.ok) { setMsg(msg, 'Invalid credentials.', false); return; }
  state.uid = d.user_id;
  document.getElementById('whoLabel').textContent = 'Hi, ' + d.username;
  document.getElementById('auth').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
  populateCurrencies(); populateMonths(); refresh();
}
function logout() {
  state.uid = null;
  document.getElementById('app').classList.add('hidden');
  document.getElementById('auth').classList.remove('hidden');
}

/* ---------- currencies & months ---------- */
async function populateCurrencies() {
  const r = await fetch('/api/currencies');
  const d = await r.json();
  curSelect.innerHTML = '';
  Object.keys(d.rates).forEach(c => {
    const o = document.createElement('option'); o.value = c; o.textContent = c; curSelect.appendChild(o);
  });
}
function populateMonths() {
  const sel = document.getElementById('monthSel');
  for (let i = 0; i < 6; i++) {
    const d = new Date(); d.setMonth(d.getMonth() - i);
    const m = d.toISOString().slice(0, 7);
    const o = document.createElement('option'); o.value = m; o.textContent = m; sel.appendChild(o);
  }
  sel.value = state.month;
  sel.onchange = () => { state.month = sel.value; refresh(); };
}

/* ---------- refresh dashboard ---------- */
async function refresh() {
  const r = await fetch(`/api/summary?month=${state.month}`, { headers: hdr() });
  const d = await r.json();
  document.getElementById('cIncome').textContent = fmt(d.total_income);
  document.getElementById('cExpense').textContent = fmt(d.total_expense);
  document.getElementById('cBalance').textContent = fmt(d.balance);
  document.getElementById('cAlerts').textContent = d.budget.alerts.length;
  renderAlerts(d.budget.alerts);
  renderBudget(d.budget.status);
  drawPie(d.by_category);
  drawTrend(d.trend);
  loadTransactions();
}
function fmt(n) { return '$' + (+n).toLocaleString(undefined, { minimumFractionDigits: 2 }); }

function renderAlerts(alerts) {
  const box = document.getElementById('alertBox');
  box.innerHTML = '<h3>Budget Alerts</h3>';
  if (!alerts.length) { box.innerHTML += '<div class="none">✅ No budget alerts — you are on track!</div>'; return; }
  alerts.forEach(a => {
    box.innerHTML += `<div class="alert ${a.level}">${a.message}</div>`;
  });
}
function renderBudget(status) {
  const box = document.getElementById('budgetList');
  box.innerHTML = '';
  status.forEach(b => {
    box.innerHTML += `
      <div class="bg-item">
        <span style="width:90px">${b.category}</span>
        <div class="bg-bar"><div class="bg-fill ${b.level}" style="width:${Math.min(b.ratio*100,100)}%"></div></div>
        <span style="width:150px;text-align:right">${fmt(b.spent)} / ${fmt(b.limit)}</span>
      </div>`;
  });
  if (!status.length) box.innerHTML = '<div class="none">No budgets set for this month.</div>';
}

/* ---------- charts (Chart.js) ---------- */
function drawPie(byCat) {
  const keys = Object.keys(byCat);
  const data = keys.map(k => byCat[k]);
  if (pieChart) pieChart.destroy();
  pieChart = new Chart(document.getElementById('pieChart'), {
    type: 'doughnut',
    data: { labels: keys, datasets: [{ data, backgroundColor: palette(keys.length) }] },
    options: { plugins: { legend: { position: 'right', labels: { color: '#e8ecff' } } } }
  });
}
function drawTrend(trend) {
  const labels = trend.map(t => t[0]);
  if (lineChart) lineChart.destroy();
  lineChart = new Chart(document.getElementById('lineChart'), {
    type: 'line',
    data: { labels,
      datasets: [
        { label: 'Income', data: trend.map(t => t[1]), borderColor: '#3ecf8e', tension: .3, fill: false },
        { label: 'Expense', data: trend.map(t => t[2]), borderColor: '#ff5d73', tension: .3, fill: false }
      ]},
    options: { plugins: { legend: { labels: { color: '#e8ecff' } } },
      scales: { x: { ticks: { color: '#9aa3c7' } }, y: { ticks: { color: '#9aa3c7' } } } }
  });
}
function palette(n) {
  const c = ['#6c7bff','#3ecf8e','#ffb547','#ff5d73','#38bdf8','#c084fc','#f472b6','#4ade80'];
  return Array.from({length:n}, (_,i) => c[i % c.length]);
}

/* ---------- transactions ---------- */
async function addTx() {
  const msg = document.getElementById('txMsg');
  const body = {
    date: document.getElementById('txDate').value || new Date().toISOString().slice(0,10),
    description: document.getElementById('txDesc').value,
    amount: document.getElementById('txAmt').value,
    type: document.getElementById('txType').value,
    category: document.getElementById('txCat').value,
    currency: curSelect.value
  };
  const r = await fetch('/api/transactions', { method: 'POST', headers: hdr(), body: JSON.stringify(body) });
  if (!r.ok) { setMsg(msg, 'Error adding.', false); return; }
  setMsg(msg, 'Added ✓', true);
  ['txDesc','txAmt','txCat'].forEach(id => document.getElementById(id).value = '');
  refresh();
}
async function loadTransactions() {
  const r = await fetch(`/api/transactions?month=${state.month}`, { headers: hdr() });
  const rows = await r.json();
  const tb = document.getElementById('txTable');
  tb.innerHTML = rows.map(t => `
    <tr><td>${t.date}</td><td>${t.description}</td><td>${t.type==='income'?'+':'−'}${fmt(t.amount)}</td>
    <td>${t.type}</td><td>${t.category_name || '—'}</td>
    <td class="del" onclick="delTx(${t.id})">✕</td></tr>`).join('') ||
    '<tr><td colspan="6" style="color:var(--muted)">No transactions.</td></tr>';
}
async function delTx(id) {
  await fetch('/api/transactions/' + id, { method: 'DELETE', headers: hdr() });
  refresh();
}

/* ---------- budgets ---------- */
async function setBudget() {
  const msg = document.getElementById('bgMsg');
  const body = { category: document.getElementById('bgCat').value,
    month: state.month, amount: document.getElementById('bgAmt').value, currency: curSelect.value };
  const r = await fetch('/api/budgets', { method: 'POST', headers: hdr(), body: JSON.stringify(body) });
  if (!r.ok) { setMsg(msg, 'Error.', false); return; }
  setMsg(msg, 'Budget set ✓', true);
  document.getElementById('bgAmt').value = '';
  refresh();
}
async function populateBudgetCats() {
  const r = await fetch('/api/summary?month=' + state.month, { headers: hdr() });
  const d = await r.json();
  const cats = Object.keys(d.by_category);
  const sel = document.getElementById('bgCat');
  sel.innerHTML = '';
  cats.concat(['Misc']).forEach(c => { const o = document.createElement('option'); o.value = c; o.textContent = c; sel.appendChild(o); });
  refreshBudgetCats();
}

/* ---------- csv ---------- */
async function exportCsv() {
  const a = document.createElement('a');
  a.href = `/api/export?month=${state.month}&uid=${state.uid}`;
  a.download = 'expensemate-' + state.month + '.csv';
  a.click();
  setMsg(document.getElementById('csvMsg'), 'Exported ✓', true);
}
async function importCsv(ev) {
  const f = ev.target.files[0]; if (!f) return;
  const text = await f.text();
  const r = await fetch('/api/import', { method: 'POST', headers: hdr(), body: JSON.stringify({ csv: text }) });
  const d = await r.json();
  setMsg(document.getElementById('csvMsg'), `Imported ${d.imported} rows ✓`, true);
  ev.target.value = '';
  refresh();
}

/* keep budget category selector refreshed */
function refreshBudgetCats() { populateBudgetCats(); }

/* bootstrap */
document.getElementById('txDate').value = new Date().toISOString().slice(0,10);
