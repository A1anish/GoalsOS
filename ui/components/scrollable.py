"""Reusable mousewheel-enabled scrollable frame for Tkinter."""

import tkinter as tk
from tkinter import ttk


class ScrollableFrame(tk.Frame):
    """A vertically scrollable container that resizes its inner frame to match canvas width."""

    def __init__(self, parent: tk.Widget, bg: str = "#0F172A", **kwargs) -> None:
        super().__init__(parent, bg=bg, highlightthickness=0, **kwargs)
        self.bg_color = bg

        self.canvas = tk.Canvas(
            self, bg=bg, highlightthickness=0, bd=0, yscrollincrement=20
        )
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.inner = tk.Frame(self.canvas, bg=bg, highlightthickness=0)

        self.inner_id = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _on_inner_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.inner_id, width=event.width)

    def _bind_mousewheel(self, _event: tk.Event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

    def _unbind_mousewheel(self, _event: tk.Event) -> None:
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event: tk.Event) -> None:
        if not self.canvas.winfo_exists():
            return
        delta = int(-1 * (event.delta / 120)) if event.delta else 0
        self.canvas.yview_scroll(delta * 3, "units")

    def _on_mousewheel_linux(self, event: tk.Event) -> None:
        if not self.canvas.winfo_exists():
            return
        if event.num == 4:
            self.canvas.yview_scroll(-3, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(3, "units")

    def set_bg(self, bg: str) -> None:
        self.bg_color = bg
        self.configure(bg=bg)
        self.canvas.configure(bg=bg)
        self.inner.configure(bg=bg)
