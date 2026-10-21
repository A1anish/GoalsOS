"""Theme engine, color palettes, typography, and ttk styling for GoalOS."""

import tkinter as tk
from tkinter import ttk
from typing import Dict


DARK_PALETTE: Dict[str, str] = {
    "name": "dark",
    "bg": "#0F172A",           # Main app background (Slate 900)
    "sidebar_bg": "#090E1A",   # Deep sidebar background
    "header_bg": "#111827",    # Top bar background
    "surface": "#1E293B",      # Card surface (Slate 800)
    "surface_hover": "#263449",# Card hover state
    "surface_alt": "#162032",  # Secondary surface / table row alt
    "input_bg": "#0F172A",     # Entry / input background
    "border": "#334155",       # Subtle border (Slate 700)
    "text": "#F8FAFB",         # Primary text
    "text_muted": "#94A3B8",   # Secondary text
    "text_dim": "#64748B",     # Tertiary / hint text
    "accent": "#6366F1",       # Primary accent (Indigo 500)
    "accent_hover": "#818CF8", # Accent hover
    "accent_subtle": "#1E1B4B",# Subtle accent tint background
    "positive": "#22C55E",     # Success / Completed (Green 500)
    "positive_bg": "#052E16",
    "warning": "#F59E0B",      # Warning / Due soon (Amber 500)
    "warning_bg": "#451A03",
    "danger": "#EF4444",       # Error / Overdue / High priority (Red 500)
    "danger_bg": "#450A0A",
    "info": "#3B82F6",         # Info (Blue 500)
    "info_bg": "#172554",
    "track": "#334155",        # Progress bar background track
    "canvas_bg": "#0B1120",    # Node explorer / chart canvas background
    "grid_line": "#1E293B",    # Chart grid line
}

LIGHT_PALETTE: Dict[str, str] = {
    "name": "light",
    "bg": "#F1F5F9",           # Main app background (Slate 100)
    "sidebar_bg": "#0F172A",   # Keep sidebar sleek dark or high-contrast
    "header_bg": "#FFFFFF",    # Top bar background
    "surface": "#FFFFFF",      # Card surface
    "surface_hover": "#F8FAFC",# Card hover state
    "surface_alt": "#F8FAFC",  # Secondary surface
    "input_bg": "#F8FAFC",     # Entry / input background
    "border": "#E2E8F0",       # Subtle border (Slate 200)
    "text": "#0F172A",         # Primary text
    "text_muted": "#475569",   # Secondary text
    "text_dim": "#94A3B8",     # Tertiary / hint text
    "accent": "#4F46E5",       # Primary accent (Indigo 600)
    "accent_hover": "#4338CA", # Accent hover
    "accent_subtle": "#EEF2FF",# Subtle accent tint background
    "positive": "#16A34A",     # Success / Completed
    "positive_bg": "#DCFCE7",
    "warning": "#D97706",      # Warning / Due soon
    "warning_bg": "#FEF3C7",
    "danger": "#DC2626",       # Error / Overdue
    "danger_bg": "#FEE2E2",
    "info": "#2563EB",         # Info
    "info_bg": "#DBEAFE",
    "track": "#E2E8F0",        # Progress bar background track
    "canvas_bg": "#F8FAFC",    # Node explorer / chart canvas background
    "grid_line": "#E2E8F0",    # Chart grid line
}


class ThemeManager:
    """Manages active color palette, typography, and ttk widget styles."""

    FONT_FAMILY = "Segoe UI"

    FONTS = {
        "display": (FONT_FAMILY, 20, "bold"),
        "h1": (FONT_FAMILY, 16, "bold"),
        "h2": (FONT_FAMILY, 13, "bold"),
        "h3": (FONT_FAMILY, 11, "bold"),
        "body": (FONT_FAMILY, 10),
        "body_bold": (FONT_FAMILY, 10, "bold"),
        "small": (FONT_FAMILY, 9),
        "small_bold": (FONT_FAMILY, 9, "bold"),
        "tiny": (FONT_FAMILY, 8),
        "mono": ("Consolas", 10),
        "metric": (FONT_FAMILY, 22, "bold"),
    }

    def __init__(self, mode: str = "dark", accent: str = "#6366F1") -> None:
        self.mode = mode if mode in ("dark", "light") else "dark"
        self.accent = accent or "#6366F1"
        self.palette = self._build_palette()

    def _build_palette(self) -> Dict[str, str]:
        base = dict(DARK_PALETTE if self.mode == "dark" else LIGHT_PALETTE)
        if self.accent:
            base["accent"] = self.accent
        return base

    def set_theme(self, mode: str, accent: str = "") -> Dict[str, str]:
        self.mode = mode if mode in ("dark", "light") else "dark"
        if accent:
            self.accent = accent
        self.palette = self._build_palette()
        return self.palette

    def apply_to_root(self, root: tk.Misc) -> None:
        """Configures ttk.Style rules to match the current theme palette."""
        p = self.palette
        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            ".",
            background=p["surface"],
            foreground=p["text"],
            fieldbackground=p["input_bg"],
            bordercolor=p["border"],
            font=self.FONTS["body"],
        )

        style.configure(
            "Treeview",
            background=p["surface"],
            foreground=p["text"],
            fieldbackground=p["surface"],
            borderwidth=0,
            rowheight=32,
            font=self.FONTS["body"],
        )
        style.configure(
            "Treeview.Heading",
            background=p["surface_alt"],
            foreground=p["text_muted"],
            relief="flat",
            padding=(8, 6),
            font=self.FONTS["small_bold"],
        )
        style.map(
            "Treeview",
            background=[("selected", p["accent"])],
            foreground=[("selected", "#FFFFFF")],
        )
        style.map(
            "Treeview.Heading",
            background=[("active", p["border"])],
        )

        style.configure(
            "TCombobox",
            fieldbackground=p["input_bg"],
            background=p["surface_alt"],
            foreground=p["text"],
            arrowcolor=p["text_muted"],
            bordercolor=p["border"],
            padding=5,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", p["input_bg"])],
            selectbackground=[("readonly", p["input_bg"])],
            selectforeground=[("readonly", p["text"])],
        )

        style.configure(
            "Vertical.TScrollbar",
            background=p["surface_alt"],
            troughcolor=p["bg"],
            bordercolor=p["bg"],
            arrowcolor=p["text_muted"],
            gripcount=0,
        )
        style.configure(
            "Horizontal.TScrollbar",
            background=p["surface_alt"],
            troughcolor=p["bg"],
            bordercolor=p["bg"],
            arrowcolor=p["text_muted"],
            gripcount=0,
        )
