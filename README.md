# GoalOS — Personal Goal Planning & Execution System

**GoalOS** is a frontend-heavy, local-first desktop application built purely with the **Python Standard Library (`tkinter`, `tkinter.ttk`, `sqlite3`, `datetime`, `uuid`, `json`, `unittest`)** — zero external third-party packages required.

It bridges the gap between high-level long-term outcomes and daily execution by organizing work into a strict 4-level hierarchy:

$$\text{Goal} \longrightarrow \text{Milestone} \longrightarrow \text{Project} \longrightarrow \text{Task}$$

---

## Key Features

1. **Execution Command Center (Dashboard)**
   - Live summary cards (`Active Goals`, `Completed This Week` with week-over-week comparison, `Tasks Due Today`, `Overdue Tasks`, `Overall Progress`).
   - **Next Best Action Recommendation Engine**: Transparent rule-based scoring ($S = 40D + 30P + 20G + 10R$) combining deadline urgency, task priority, goal importance, and scheduling readiness with human-readable explanations.
   - Interactive Goal Cards with custom `tk.Canvas` circular progress rings, Today's Priorities checklist, Upcoming Milestones, and Recent Activity feed.

2. **Hierarchical Goal Explorer & Visual Node Builder**
   - Synchronized split workspace featuring a `ttk.Treeview` hierarchy editor on the left and a custom zoomable, pannable **`tk.Canvas` Node-Graph Visualizer** with cubic Bezier curve connectors on the right.
   - Click any node in the tree or canvas to inspect, edit, reorder siblings (`↑`/`↓`), add child entities, or double-click tasks to toggle completion.

3. **Deep Goal Workspace & Schedule Feasibility Analyzer**
   - Expandable/collapsible Milestone, Project, and Task sections.
   - Automatic **Schedule Feasibility Analysis** comparing remaining estimated task minutes against days remaining before the goal's deadline based on your daily work capacity setting.
   - Smart completion safeguards: prevents accidentally completing a goal with unfinished tasks without explicit confirmation, suggests completing a goal when 100% of eligible tasks finish, and prompts to reopen a completed goal if a task is reopened.

4. **Unified Task Planner**
   - Multi-dimensional filtering (`Status`, `Due Window`, `Priority`, `Goal`, `Keyword Search`) and sorting (`Due Date`, `Priority`, `Estimated Duration`, `Status`, `Creation Date`).
   - One-click priority cycling, quick rescheduling dialog with presets (`Today`, `Tomorrow`, `+3 Days`, `Next Week`), and instant completion toggles.

5. **Timeline & Graphical Canvas Gantt View**
   - Switch between Chronological Deadline Buckets (`Overdue`, `Today`, `Next 7 Days`, `Later`, `Unscheduled`) and a custom `tk.Canvas` **Graphical Gantt Chart** with a live `TODAY` marker line.

6. **Pure-Canvas Progress Analytics**
   - Custom `tk.Canvas` **Bar Charts** and **Donut Charts** (no Matplotlib dependency required):
     - Active Goal Progress Leaderboard (supports both Equal Task Weighting and Effort-Weighted Progress by estimated minutes).
     - Daily Completed Tasks History (`7`, `14`, or `21` days).
     - Planned Workload Distribution (Minutes/Day over the next 7 days + overdue/unscheduled backlogs).
     - Goal Category Distribution & Task Deadline Compliance (`Completed On Time`, `Completed Late`, `Currently Overdue`, `On Track`).

7. **Guided 5-Step Weekly Review**
   - Automatically aggregates past 7-day metrics (completed tasks, finished milestones, missed deadlines, stagnant goals), provides structured reflection prompts, priority goal selection, and archives reviews locally.

8. **Settings, Live Theme Engine & Validated Backups**
   - Instant switching between **Dark Theme** and **Light Theme** plus 8 customizable primary accent colors.
   - One-click JSON export, SQLite database backup, and integrity-validated database restore.

---

## Project Architecture

```text
GoalsOS/
├── main.py                        # Application entry point & CLI flags
├── requirements.txt               # Zero external dependencies required
├── README.md                      # Documentation
├── database/
│   ├── schema.py                  # SQLite tables, foreign keys, and indexes
│   └── connection.py              # Transaction manager & SQLite backup validator
├── models/
│   └── entities.py                # Dataclasses (Goal, Milestone, Project, Task, etc.)
├── repositories/                  # Data access layer (parameterized SQL)
│   ├── goal_repository.py
│   ├── milestone_repository.py
│   ├── project_repository.py
│   ├── task_repository.py
│   ├── review_repository.py
│   └── activity_repository.py
├── services/                      # Business logic & calculation engines
│   ├── progress_service.py        # Bottom-up progress & effort-weighted option
│   ├── recommendation_service.py  # Next Best Action scoring & explanations
│   ├── goal_service.py            # Hierarchy CRUD & completion rules
│   ├── task_service.py            # Task lifecycle, filtering & sorting
│   ├── analytics_service.py       # Dashboard, timeline, charts & feasibility
│   ├── review_service.py          # Weekly review aggregation
│   └── backup_service.py          # JSON export, SQLite backup/restore & demo seeder
├── ui/                            # Tkinter Frontend Layer
│   ├── theme.py                   # Dark/Light palettes & ttk styling
│   ├── app_controller.py          # Shared state & reactive UI event bus
│   ├── main_window.py             # Persistent sidebar + header + page router
│   ├── components/
│   │   ├── canvas_widgets.py      # Custom Canvas rings, charts, node tree & Gantt
│   │   ├── dialogs.py             # Validated modal forms
│   │   ├── scrollable.py          # Mousewheel-enabled ScrollableFrame
│   │   └── sidebar.py             # Navigation sidebar with live progress bar
│   └── pages/                     # 9 modular application screens
└── tests/
    └── test_goalos.py             # Automated unit & integration tests
```

---

## Running the Application

### 1. Launch GoalOS (auto-seeds rich sample data on first run)
```bash
python main.py
```

### 2. Launch with an empty database (no sample data)
```bash
python main.py --no-seed
```

### 3. Run the automated test suite
```bash
python -m unittest discover -s tests -v
```
