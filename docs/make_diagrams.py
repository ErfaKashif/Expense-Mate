"""
Builds all project diagrams (Phase 1 & 2 deliverables) with matplotlib,
so no external diagramming tool is required.
Outputs PNGs into docs/diagrams.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Ellipse
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagrams")
os.makedirs(OUT, exist_ok=True)

BG = "#f4f6fb"
BOX = "#ffffff"
INK = "#1a1f36"
MUT = "#5a6480"


def box(ax, x, y, w, h, text, fc="#ffffff", ec="#6c7bff", fs=9, tc="#1a1f36", lw=1.4, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.03",
                                fc=fc, ec=ec, lw=lw, mutation_aspect=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=tc, weight="bold" if bold else "normal", wrap=True)


def arrow(ax, x1, y1, x2, y2, dash=False, color="#6c7bff", double=False):
    st = {} if not double else {"arrowstyle": "<|-|>"}
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=12, color=color, lw=1.5,
                                 linestyle="--" if dash else "-", **st))


def clean(ax, xm, ym):
    ax.set_xlim(0, xm); ax.set_ylim(0, ym)
    ax.axis("off"); ax.set_facecolor(BG)


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=120, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("wrote", name, os.path.getsize(os.path.join(OUT, name)), "bytes")


# ===================================================================== #
# USE CASE DIAGRAM (Phase 1)
# ===================================================================== #
def use_case():
    fig, ax = plt.subplots(figsize=(9, 6.5)); clean(ax, 10, 10)
    # system boundary
    ax.add_patch(FancyBboxPatch((2.3, 0.5), 7.4, 8.6, boxstyle="round,pad=0.02,rounding_size=0.10",
                                fc="#eef1ff", ec="#9aa3c7", lw=1.6))
    ax.text(6, 9.0, "ExpenseMate System", ha="center", fontsize=11, weight="bold", color="#3a4dbd")

    # actor
    box(ax, 0.2, 3.9, 1.7, 1.7, "User\n(Owner)", fc="#fff2cc", ec="#d9a800", fs=10, bold=True)

    # three columns, wide boundary to avoid overlap
    cols = [3.5, 5.4, 7.3]
    W, H, FS = 1.7, 1.05, 7.6
    cases = [
        ("Log in / Register", cols[1], 7.6),
        ("Add Income", cols[0], 6.1), ("Add Expense", cols[1], 6.1),
        ("Set Monthly Budget", cols[2], 6.1),
        ("View Budget Alerts", cols[0], 4.6),
        ("View Charts & Reports", cols[1], 4.6),
        ("Export CSV", cols[2], 4.6),
        ("Manage Transactions", cols[0], 3.1),
        ("Import CSV", cols[1], 3.1),
    ]
    centers = []
    for t, x, y in cases:
        box(ax, x - W / 2, y - H / 2, W, H, t, fs=FS, ec="#6c7bff", lw=1.2)
        centers.append((x, y))
    # actor -> each case
    for x, y in centers:
        arrow(ax, 1.9, 4.75, x - W / 2 + 0.1, y, color="#8892c0", dash=False)
    save(fig, "use_case_diagram.png")


# ===================================================================== #
# LOGICAL VIEW (layered / component) -- Phase 2
# ===================================================================== #
def logical():
    fig, ax = plt.subplots(figsize=(9.5, 6.5)); clean(ax, 10, 10)
    labels = [
        ("Presentation (Client)\nindex.html + app.js + style.css\n(Chart.js)", 0.2, 8.0, 9.6, 1.5, "#e7f6ef", "#2f9e6e"),
        ("Server / REST API (Flask)\napp/backend/server.py\n/routes for auth, tx, budget, csv", 0.2, 5.9, 9.6, 1.6, "#eaf0ff", "#3a4dbd"),
        ("Business Logic\napp/backend/logic.py\nvalidation, budget alerts, analytics, csv, currency", 0.2, 3.9, 9.6, 1.5, "#fff6e6", "#c98a00"),
        ("Persistence\napp/backend/db.py +\nSQLite 'expensemate.db'", 0.2, 1.9, 9.6, 1.5, "#fdeef0", "#c23b52"),
    ]
    for t, x, y, w, h, fc, ec in labels:
        box(ax, x, y, w, h, t, fc=fc, ec=ec, fs=9)
    for y1, y2 in [(7.5, 8.0), (5.4, 5.9), (3.4, 3.9)]:
        arrow(ax, 5, y1, 5, y2, color="#777fa8")
    ax.text(5.02, 5.65, "HTTP / REST", fontsize=7, color="#777fa8")
    ax.text(5.02, 4.65, "call", fontsize=7, color="#777fa8")
    ax.text(5.02, 2.65, "SQL", fontsize=7, color="#777fa8")
    save(fig, "logical_view.png")


# ===================================================================== #
# PROCESS VIEW (component/process interactions) -- Phase 2
# ===================================================================== #
def process():
    fig, ax = plt.subplots(figsize=(9.5, 6)); clean(ax, 10, 8)
    box(ax, 0.3, 6.0, 2.0, 1.4, "Browser\n(Client Process)\nHTML/JS", fc="#e7f6ef", ec="#2f9e6e")
    box(ax, 3.2, 6.0, 2.2, 1.4, "Flask Web\nServer Process\n(worker)", fc="#eaf0ff", ec="#3a4dbd")
    box(ax, 6.3, 6.0, 2.0, 1.4, "SQLite\nDB Process\n(file I/O)", fc="#fdeef0", ec="#c23b52")
    arrow(ax, 2.3, 6.7, 3.2, 6.7, color="#777fa8"); ax.text(2.75, 6.85, "register/login\n+REST JSON", fontsize=6.5, ha="center")
    arrow(ax, 5.4, 6.7, 6.3, 6.7, color="#777fa8")
    ax.text(5.85, 6.85, "SQL", fontsize=7, ha="center", color="#777fa8")
    ax.text(2.3, 5.7, "static assets /=  and  /static/*", fontsize=7, color="#777fa8")
    ax.text(2.3, 5.5, "CSV download/anchor from /api/export", fontsize=7, color="#777fa8")
    # flow of a request
    ax.text(0.4, 5.0, "Request flow:", fontsize=9, weight="bold", color="#3a4dbd")
    box(ax, 0.4, 3.4, 2.4, 1.2, "User action in\nUI (add expense)", fc="#ffffff", ec="#8892c0", fs=8.5)
    box(ax, 3.3, 3.4, 2.4, 1.2, "POST /api/transactions\nserver.py add_transaction", fc="#ffffff", ec="#8892c0", fs=8.5)
    box(ax, 6.2, 3.4, 2.4, 1.2, "logic validates + stores\n(db.add_transaction)", fc="#ffffff", ec="#8892c0", fs=8.5)
    arrow(ax, 2.8, 4.0, 3.3, 4.0); arrow(ax, 5.7, 4.0, 6.2, 4.0)
    box(ax, 6.2, 1.6, 2.4, 1.1, "return new id\n-> 201 JSON", fc="#ffffff", ec="#8892c0", fs=8.5)
    arrow(ax, 6.2, 2.3, 5.7, 2.8, color="#c23b52")  # down-left
    save(fig, "process_view.png")


# ===================================================================== #
# PHYSICAL VIEW (nodes & deployment environment) -- Phase 2
# ===================================================================== #
def physical():
    fig, ax = plt.subplots(figsize=(9.5, 5.5)); clean(ax, 10, 7)
    ax.add_patch(FancyBboxPatch((0.3, 0.5), 9.3, 6.0, boxstyle="round,pad=0.02,rounding_size=0.1",
                                fc="#fbfcff", ec="#9aa3c7", lw=1.5))
    ax.text(5, 6.2, "Build / Deployment Environment", ha="center", fontsize=10, weight="bold", color="#5a6480")
    box(ax, 0.7, 4.6, 2.6, 1.2, "Laptop / PC\n(Client)", fc="#e7f6ef", ec="#2f9e6e", fs=9)
    box(ax, 3.8, 4.6, 2.6, 1.2, "localhost:5000\n(Server node)", fc="#eaf0ff", ec="#3a4dbd", fs=9)
    box(ax, 7.0, 4.6, 2.3, 1.2, "DB file\nexpensemate.db", fc="#fdeef0", ec="#c23b52", fs=9)
    arrow(ax, 3.3, 5.2, 3.8, 5.2, color="#777fa8"); ax.text(3.55, 5.3, "TCP", fontsize=7, ha="center")
    arrow(ax, 6.4, 5.2, 7.0, 5.2, color="#777fa8"); ax.text(6.7, 5.3, "file", fontsize=7, ha="center")
    box(ax, 0.7, 2.9, 2.6, 1.1, "Python 3.11+\nFlask 3.x", fc="#ffffff", ec="#8892c0", fs=8.5)
    box(ax, 3.8, 2.9, 2.6, 1.1, "SQLite (stdlib)\nNo external DB server", fc="#ffffff", ec="#8892c0", fs=8.5)
    box(ax, 7.0, 2.9, 2.3, 1.1, "CSV files\n(sample_data/)", fc="#ffffff", ec="#8892c0", fs=8.5)
    ax.text(0.7, 2.0, "All nodes run on one machine — a LOCAL client-server system.", fontsize=8.5, color="#5a6480")
    save(fig, "physical_view.png")


# ===================================================================== #
# DEPLOYMENT VIEW -- Phase 2
# ===================================================================== #
def deployment():
    fig, ax = plt.subplots(figsize=(8.5, 5.5)); clean(ax, 10, 7)
    # node
    node = FancyBboxPatch((0.5, 0.5), 9.0, 6.0, boxstyle="round,pad=0.02,rounding_size=0.1",
                          fc="#fbfcff", ec="#5a6480", lw=1.8)
    ax.add_patch(node)
    ax.text(5, 6.2, "«device» User Workstation", ha="center", fontsize=10, weight="bold", color="#333b52")
    def component(x, y, w, h, name, tag, fc="#eef1ff", ec="#6c7bff"):
        box(ax, x, y, w, h, f"{name}\n«{tag}»", fc=fc, ec=ec, fs=9)
    # column A (server-side components) and column B (db / test)
    component(0.8, 4.5, 3.3, 1.2, "Browser UI\nindex.html / app.js", "Component", "#e7f6ef", "#2f9e6e")
    component(0.8, 2.7, 3.3, 1.2, "Flask App\nserver.py", "Process", "#eaf0ff", "#3a4dbd")
    component(0.8, 0.9, 3.3, 1.2, "Logic\nlogic.py", "Component", "#fff6e6", "#c98a00")
    component(6.0, 4.5, 3.5, 1.2, "SQLite\nexpensemate.db", "Database", "#fdeef0", "#c23b52")
    component(6.0, 2.7, 3.4, 1.2, "Unit tests\ntests/", "Test Harness", "#ffffff", "#8892c0")
    # vertical flow on left column
    arrow(ax, 2.45, 4.5, 2.45, 3.9, color="#8892c0", dash=True)
    arrow(ax, 2.45, 2.7, 2.45, 2.1, color="#8892c0", dash=True)
    # connectors
    arrow(ax, 4.1, 5.1, 6.0, 5.1); ax.text(5.05, 5.2, "HTTP", fontsize=7, ha="center", color="#777fa8")
    arrow(ax, 4.1, 3.3, 6.0, 3.3); ax.text(5.05, 3.4, "pytest", fontsize=7, ha="center", color="#777fa8")
    arrow(ax, 7.75, 2.7, 7.75, 4.5, dash=True, color="#8892c0")
    ax.text(8.15, 3.6, "SQL", fontsize=7.5, color="#c23b52")
    ax.text(0.8, 0.35, "All components run inside one workstation (a local client-server system).",
            fontsize=8, color="#5a6480")
    save(fig, "deployment_view.png")


# ===================================================================== #
# GANTT CHART -- Phase 2 planning
# ===================================================================== #
def gantt():
    tasks = [
        ("Phase 1: Requirements & SRS", 0, 6, "A"),          # (start, dur days)
        ("P1: Use Case Diagram", 0, 4, "B"),
        ("Phase 2: Architecture Plan", 6, 4, "Both"),
        ("P2: 4 Architectural Views", 7, 5, "A"),
        ("P2: Standards & Timeline", 7, 4, "B"),
        ("Phase 3: Coding - Backend", 11, 12, "A"),
        ("P3: Coding - Frontend / UI", 11, 12, "B"),
        ("P3: Unit Tests (per module)", 15, 9, "Both"),
        ("Phase 4: Integration Testing", 23, 5, "A"),
        ("P4: System Testing", 24, 5, "B"),
        ("P4: Complexity & Fault Metrics", 25, 4, "A"),
        ("Phase 5: Maintenance (new feat + 2 bugs + refactor)", 28, 6, "Both"),
        ("Phase 6: Final Report & Demo", 34, 5, "Both"),
    ]
    fig, ax = plt.subplots(figsize=(11.5, 7))
    phase_colors = ["#6c7bff", "#3ecf8e", "#ffb547", "#ff5d73", "#c084fc", "#f472b6"]
    for i, (name, start, dur, who) in enumerate(tasks):
        col = phase_colors[i // 2] if i < 12 else phase_colors[5]
        ax.barh(i, dur, left=start, height=0.62, color=col, edgecolor="white")
        # owner label to the right of the bar (kept short)
        ax.text(start + dur + 0.6, i, who, va="center", fontsize=9, color="#444", weight="bold")
    ax.set_yticks(range(len(tasks)))
    ax.set_yticklabels([t[0] for t in tasks], fontsize=9)
    ax.invert_yaxis()
    ax.set_xticks(range(0, 44, 4))
    ax.set_xlabel("Working days from project start (≈ 7 weeks / 40 working days)")
    ax.set_title("ExpenseMate — Construction Gantt Chart (Phase 1 → Phase 6)", fontsize=13, weight="bold")
    ax.grid(axis="x", linestyle=":", color="#ccc", zorder=0)
    ax.set_facecolor("#fbfcff")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in phase_colors]
    ax.legend(handles, ["Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5", "Phase 6"],
              loc="lower right", fontsize=9, frameon=False, ncol=2)
    fig.tight_layout()
    save(fig, "gantt_chart.png")


for fn in [use_case, logical, process, physical, deployment, gantt]:
    fn()
print("ALL DIAGRAMS DONE")
