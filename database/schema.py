"""SQLite database schema and initialization for GoalOS."""

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS goals (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT NOT NULL DEFAULT 'Other',
    start_date TEXT,
    deadline TEXT,
    priority TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'active',
    target_value REAL,
    target_unit TEXT DEFAULT '',
    color TEXT DEFAULT '#6366F1',
    completion_notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS milestones (
    id TEXT PRIMARY KEY,
    goal_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    start_date TEXT,
    deadline TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    position INTEGER NOT NULL DEFAULT 0,
    completion_notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    milestone_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    start_date TEXT,
    deadline TEXT,
    priority TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'active',
    position INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (milestone_id) REFERENCES milestones(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    due_date TEXT,
    scheduled_date TEXT,
    estimated_minutes INTEGER DEFAULT 30,
    actual_minutes INTEGER DEFAULT 0,
    priority TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'todo',
    position INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS weekly_reviews (
    id TEXT PRIMARY KEY,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    went_well TEXT DEFAULT '',
    challenges TEXT DEFAULT '',
    lessons_learned TEXT DEFAULT '',
    next_week_changes TEXT DEFAULT '',
    planned_priorities TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_goals (
    review_id TEXT NOT NULL,
    goal_id TEXT NOT NULL,
    PRIMARY KEY (review_id, goal_id),
    FOREIGN KEY (review_id) REFERENCES weekly_reviews(id) ON DELETE CASCADE,
    FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activity_log (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_milestones_goal_id ON milestones(goal_id);
CREATE INDEX IF NOT EXISTS idx_projects_milestone_id ON projects(milestone_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_date ON tasks(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_tasks_completed_at ON tasks(completed_at);
CREATE INDEX IF NOT EXISTS idx_activity_created_at ON activity_log(created_at);
"""

DEFAULT_SETTINGS = {
    "theme": "dark",
    "accent_color": "#6366F1",
    "default_task_sort": "due_date",
    "date_format": "YYYY-MM-DD",
    "effort_weighted_progress": "false",
    "daily_capacity_minutes": "180",
}
