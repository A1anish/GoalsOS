"""Settings, Theme Customization, and Data Management page for GoalOS."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from models.entities import GOAL_ACCENT_COLORS
from ui.app_controller import AppController
from ui.components.scrollable import ScrollableFrame
from utils.validators import ValidationError


class SettingsPage(tk.Frame):
    """Configures theme, accent colors, progress calculation mode, and backups."""

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])

        self.scroll = ScrollableFrame(self, bg=p["bg"])
        self.scroll.pack(fill="both", expand=True)
        self.render()

    def render(self) -> None:
        p = self.controller.colors
        self.configure(bg=p["bg"])
        self.scroll.set_bg(p["bg"])
        container = self.scroll.inner

        for child in container.winfo_children():
            child.destroy()

        # Header
        header = tk.Frame(container, bg=p["bg"], padx=26, pady=18)
        header.pack(fill="x")
        tk.Label(
            header,
            text="Settings, Appearance & Data Management",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Customize themes, progress algorithms, daily capacity, and manage local SQLite backups.",
            bg=p["bg"],
            fg=p["text_muted"],
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(anchor="w")

        # --- Section 1: Appearance & Theme ---
        app_card = self._make_section_card(
            container, "1. APPEARANCE & DESIGN SYSTEM"
        )

        mode_row = tk.Frame(app_card, bg=p["surface"], pady=6)
        mode_row.pack(fill="x")
        tk.Label(
            mode_row,
            text="Application Theme Mode",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        cur_mode = self.controller.theme.mode
        for m_key, m_lbl in [
            ("dark", "🌙 Dark Theme"),
            ("light", "☀ Light Theme"),
        ]:
            is_sel = cur_mode == m_key
            tk.Button(
                mode_row,
                text=m_lbl,
                bg=p["accent"] if is_sel else p["surface_alt"],
                fg="#FFFFFF" if is_sel else p["text"],
                font=("Segoe UI", 9, "bold" if is_sel else "normal"),
                relief="flat",
                padx=14,
                pady=5,
                cursor="hand2",
                command=lambda mk=m_key: self.controller.switch_theme(mk),
            ).pack(side="right", padx=4)

        acc_row = tk.Frame(app_card, bg=p["surface"], pady=10)
        acc_row.pack(fill="x")
        tk.Label(
            acc_row,
            text="Primary Accent Color",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        swatches = tk.Frame(acc_row, bg=p["surface"])
        swatches.pack(side="right")
        cur_acc = self.controller.theme.accent
        for col_hex in GOAL_ACCENT_COLORS:
            is_cur = col_hex.lower() == cur_acc.lower()
            tk.Button(
                swatches,
                text="✓" if is_cur else " ",
                bg=col_hex,
                fg="#FFFFFF",
                activebackground=col_hex,
                width=3,
                relief="flat",
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
                command=lambda c=col_hex: self.controller.switch_theme(
                    self.controller.theme.mode, accent=c
                ),
            ).pack(side="left", padx=4)

        # --- Section 2: Planning & Progress Calculation Preferences ---
        pref_card = self._make_section_card(
            container, "2. PROGRESS ENGINE & PLANNING PREFERENCES"
        )

        # Effort-weighted vs Equal task weighting
        ew_row = tk.Frame(pref_card, bg=p["surface"], pady=6)
        ew_row.pack(fill="x")
        ew_left = tk.Frame(ew_row, bg=p["surface"])
        ew_left.pack(side="left")
        tk.Label(
            ew_left,
            text="Progress Calculation Algorithm",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            ew_left,
            text="Equal Task Weighting counts each eligible task equally. Effort-Weighted weights tasks by estimated minutes.",
            bg=p["surface"],
            fg=p["text_muted"],
            font=("Segoe UI", 8),
            anchor="w",
        ).pack(anchor="w")

        is_ew = self.controller.progress_service.is_effort_weighted()
        for val_str, lbl in [
            ("false", "Equal Task Count (Default)"),
            ("true", "Effort-Weighted (Minutes)"),
        ]:
            active_btn = (is_ew and val_str == "true") or (
                not is_ew and val_str == "false"
            )
            tk.Button(
                ew_row,
                text=lbl,
                bg=p["accent"] if active_btn else p["surface_alt"],
                fg="#FFFFFF" if active_btn else p["text"],
                font=("Segoe UI", 9, "bold" if active_btn else "normal"),
                relief="flat",
                padx=12,
                pady=5,
                cursor="hand2",
                command=lambda v=val_str: self._save_setting(
                    "effort_weighted_progress", v
                ),
            ).pack(side="right", padx=4)

        # Daily work capacity setting
        cap_row = tk.Frame(pref_card, bg=p["surface"], pady=10)
        cap_row.pack(fill="x")
        tk.Label(
            cap_row,
            text="Daily Available Work Capacity (Minutes / Day for Schedule Feasibility)",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        cur_cap = self.controller.settings_repo.get(
            "daily_capacity_minutes", "180"
        )
        self.cap_combo = ttk.Combobox(
            cap_row,
            values=["60", "120", "180", "240", "300", "360"],
            state="readonly",
            width=10,
        )
        self.cap_combo.set(cur_cap)
        self.cap_combo.pack(side="right")
        self.cap_combo.bind(
            "<<ComboboxSelected>>",
            lambda _e: self._save_setting(
                "daily_capacity_minutes", self.cap_combo.get()
            ),
        )

        # Default Task Planner Sorting
        sort_row = tk.Frame(pref_card, bg=p["surface"], pady=6)
        sort_row.pack(fill="x")
        tk.Label(
            sort_row,
            text="Default Task Planner Sort Order",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        cur_sort = self.controller.settings_repo.get(
            "default_task_sort", "due_date"
        )
        self.sort_combo = ttk.Combobox(
            sort_row,
            values=[
                "due_date",
                "priority",
                "estimated_minutes",
                "status",
                "created_at",
            ],
            state="readonly",
            width=16,
        )
        self.sort_combo.set(cur_sort)
        self.sort_combo.pack(side="right")
        self.sort_combo.bind(
            "<<ComboboxSelected>>",
            lambda _e: self._save_setting(
                "default_task_sort", self.sort_combo.get()
            ),
        )

        # --- Section 3: Data Management, Backup & Export ---
        data_card = self._make_section_card(
            container, "3. LOCAL DATABASE STORAGE, BACKUP & EXPORT"
        )

        db_info = tk.Frame(data_card, bg=p["surface_alt"], padx=12, pady=10)
        db_info.pack(fill="x", pady=(0, 12))
        tk.Label(
            db_info,
            text="ACTIVE SQLITE DATABASE LOCATION:",
            bg=p["surface_alt"],
            fg=p["text_muted"],
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            db_info,
            text=self.controller.db.db_path,
            bg=p["surface_alt"],
            fg=p["accent"],
            font=("Consolas", 9),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        btn_row = tk.Frame(data_card, bg=p["surface"])
        btn_row.pack(fill="x", pady=4)

        tk.Button(
            btn_row,
            text="⬇ Export All Data to JSON",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2",
            command=self._export_json,
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            btn_row,
            text="💾 Backup SQLite Database",
            bg=p["surface_alt"],
            fg=p["text"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2",
            command=self._backup_sqlite,
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            btn_row,
            text="📂 Restore from Validated Backup",
            bg=p["surface_alt"],
            fg=p["warning"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2",
            command=self._restore_sqlite,
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            btn_row,
            text="+ Add Sample Demo Goals",
            bg=p["surface_alt"],
            fg=p["positive"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2",
            command=self._seed_demo,
        ).pack(side="right")

    def _make_section_card(self, parent: tk.Widget, title: str) -> tk.Frame:
        p = self.controller.colors
        card = tk.Frame(
            parent,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=20,
            pady=16,
        )
        card.pack(fill="x", padx=26, pady=(0, 16))
        tk.Label(
            card,
            text=title,
            bg=p["surface"],
            fg=p["accent"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 10))
        return card

    def _save_setting(self, key: str, value: str) -> None:
        self.controller.settings_repo.set(key, value)
        self.controller.show_toast("Preference saved!", "positive")
        self.controller.notify_data_changed("settings_updated")

    def _export_json(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export GoalOS Data to JSON",
            defaultextension=".json",
            initialfile="goalos_export.json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            out = self.controller.backup_service.export_to_json(path)
            self.controller.show_toast(
                f"Exported JSON to {out}", "positive"
            )
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))

    def _backup_sqlite(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save SQLite Database Backup",
            defaultextension=".db",
            initialfile="goalos_backup.db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            out = self.controller.backup_service.create_backup(path)
            self.controller.show_toast(
                f"Created backup at {out}", "positive"
            )
        except Exception as exc:
            messagebox.showerror("Backup Failed", str(exc))

    def _restore_sqlite(self) -> None:
        path = filedialog.askopenfilename(
            title="Select GoalOS SQLite Backup to Restore",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
        )
        if not path:
            return
        if not messagebox.askyesno(
            "Confirm Database Restore",
            "Restoring from backup will replace your current GoalOS database after validating integrity.\n\nProceed with restore?",
        ):
            return
        try:
            self.controller.backup_service.restore_backup(path)
            self.controller.show_toast(
                "Database restored and validated!", "positive"
            )
            self.controller.notify_data_changed("db_restored")
        except ValidationError as exc:
            messagebox.showerror("Invalid Backup File", str(exc))
        except Exception as exc:
            messagebox.showerror("Restore Failed", str(exc))

    def _seed_demo(self) -> None:
        self.controller.backup_service.seed_sample_data_if_empty(force=True)
        self.controller.show_toast(
            "Added sample goals, milestones, projects, and tasks!", "positive"
        )
        self.controller.notify_data_changed("demo_seeded")
