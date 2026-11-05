"""Minimal Settings page for GoalOS."""

import tkinter as tk
from tkinter import messagebox

from ui.app_controller import AppController


class SettingsPage(tk.Frame):
    """Minimal settings page with Theme toggle and Sample Data reset."""

    def __init__(self, parent: tk.Widget, controller: AppController) -> None:
        self.controller = controller
        p = controller.colors
        super().__init__(parent, bg=p["bg"])
        self.render()

    def render(self) -> None:
        p = self.controller.colors
        self.configure(bg=p["bg"])

        for child in self.winfo_children():
            child.destroy()

        header = tk.Frame(self, bg=p["bg"], padx=32, pady=20)
        header.pack(fill="x")
        tk.Label(
            header,
            text="Settings",
            bg=p["bg"],
            fg=p["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(anchor="w")

        card = tk.Frame(
            self,
            bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1,
            padx=24,
            pady=20,
        )
        card.pack(fill="x", padx=32)

        # 1. Theme Mode
        mode_row = tk.Frame(card, bg=p["surface"], pady=8)
        mode_row.pack(fill="x")
        tk.Label(
            mode_row,
            text="Theme",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")

        cur_mode = self.controller.theme.mode
        for m_key, m_lbl in [
            ("dark", "🌙 Dark"),
            ("light", "☀ Light"),
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

        tk.Frame(card, bg=p["border"], height=1).pack(fill="x", pady=14)

        # 2. Reset Dummy Data
        data_row = tk.Frame(card, bg=p["surface"], pady=8)
        data_row.pack(fill="x")
        tk.Label(
            data_row,
            text="Sample Data",
            bg=p["surface"],
            fg=p["text"],
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")

        tk.Button(
            data_row,
            text="↻ Reset Dummy Data",
            bg=p["accent"],
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._reset_dummy_data,
        ).pack(side="right")

    def _reset_dummy_data(self) -> None:
        if not messagebox.askyesno(
            "Reset Dummy Data",
            "Replace current goals and tasks with fresh sample data?",
        ):
            return
        self.controller.backup_service.reset_sample_data()
        self.controller.show_toast("Dummy data reset!", "positive")
        self.controller.notify_data_changed("demo_reset")
