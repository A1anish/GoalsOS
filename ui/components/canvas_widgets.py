"""Custom Tkinter Canvas widgets, charts, node-graph explorer, and Gantt timeline."""

from datetime import date, timedelta
import tkinter as tk
from typing import Callable, Dict, List, Optional, Tuple

from models.entities import Goal, ProgressStats
from utils.dates import format_relative_deadline, parse_iso_date


def draw_rounded_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float = 10,
    **kwargs,
) -> int:
    """Draws a smooth rounded rectangle polygon on a Tkinter Canvas."""
    r = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    points = [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class CircularProgressRing(tk.Canvas):
    """Custom Canvas circular progress indicator with center percentage label."""

    def __init__(
        self,
        parent: tk.Widget,
        size: int = 68,
        thickness: int = 7,
        percentage: float = 0.0,
        bg_color: str = "#1E293B",
        track_color: str = "#334155",
        fill_color: str = "#6366F1",
        text_color: str = "#F8FAFB",
        sub_label: str = "",
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=bg_color,
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.size = size
        self.thickness = thickness
        self.percentage = max(0.0, min(100.0, percentage))
        self.track_color = track_color
        self.fill_color = fill_color
        self.text_color = text_color
        self.sub_label = sub_label
        self.render()

    def set_value(
        self, percentage: float, fill_color: Optional[str] = None, sub_label: Optional[str] = None
    ) -> None:
        self.percentage = max(0.0, min(100.0, percentage))
        if fill_color:
            self.fill_color = fill_color
        if sub_label is not None:
            self.sub_label = sub_label
        self.render()

    def render(self) -> None:
        self.delete("all")
        pad = self.thickness + 3
        x1, y1 = pad, pad
        x2, y2 = self.size - pad, self.size - pad

        # Background ring
        self.create_oval(
            x1, y1, x2, y2, outline=self.track_color, width=self.thickness
        )

        # Foreground progress arc
        if self.percentage > 0:
            extent = -359.9 if self.percentage >= 100.0 else -(self.percentage / 100.0) * 360.0
            self.create_arc(
                x1,
                y1,
                x2,
                y2,
                start=90,
                extent=extent,
                style="arc",
                outline=self.fill_color,
                width=self.thickness,
            )

        cx, cy = self.size / 2, self.size / 2
        font_sz = max(9, int(self.size * 0.19))
        if self.sub_label:
            self.create_text(
                cx,
                cy - 5,
                text=f"{self.percentage:.0f}%",
                fill=self.text_color,
                font=("Segoe UI", font_sz, "bold"),
            )
            self.create_text(
                cx,
                cy + 10,
                text=self.sub_label,
                fill=self.track_color if self.percentage == 0 else self.fill_color,
                font=("Segoe UI", max(7, font_sz - 3)),
            )
        else:
            self.create_text(
                cx,
                cy,
                text=f"{self.percentage:.0f}%",
                fill=self.text_color,
                font=("Segoe UI", font_sz, "bold"),
            )


class SmoothProgressBar(tk.Canvas):
    """Responsive Canvas horizontal progress bar with pill ends."""

    def __init__(
        self,
        parent: tk.Widget,
        percentage: float = 0.0,
        height: int = 8,
        bg_color: str = "#1E293B",
        track_color: str = "#334155",
        fill_color: str = "#6366F1",
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            height=height,
            bg=bg_color,
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.percentage = max(0.0, min(100.0, percentage))
        self.bar_height = height
        self.track_color = track_color
        self.fill_color = fill_color
        self.bind("<Configure>", lambda _e: self.render())

    def set_progress(self, percentage: float, fill_color: Optional[str] = None) -> None:
        self.percentage = max(0.0, min(100.0, percentage))
        if fill_color:
            self.fill_color = fill_color
        self.render()

    def render(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 40)
        h = self.bar_height
        r = h / 2

        draw_rounded_rect(
            self, 0, 0, w, h, radius=r, fill=self.track_color, outline=""
        )
        if self.percentage > 0:
            fill_w = max(h, (self.percentage / 100.0) * w)
            draw_rounded_rect(
                self, 0, 0, fill_w, h, radius=r, fill=self.fill_color, outline=""
            )


class MetricCard(tk.Frame):
    """Clean, minimalist summary metric card."""

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        value: str,
        subtitle: str,
        accent_color: str,
        colors: Dict[str, str],
        on_click: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(
            parent,
            bg=colors["surface"],
            highlightbackground=colors["border"],
            highlightthickness=1,
            bd=0,
            cursor="hand2" if on_click else "",
        )
        self.colors = colors

        top_bar = tk.Frame(self, bg=accent_color, height=3)
        top_bar.pack(fill="x", side="top")

        body = tk.Frame(self, bg=colors["surface"], padx=18, pady=14)
        body.pack(fill="both", expand=True)

        lbl_title = tk.Label(
            body,
            text=title,
            bg=colors["surface"],
            fg=colors["text_muted"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        lbl_title.pack(fill="x")

        lbl_val = tk.Label(
            body,
            text=value,
            bg=colors["surface"],
            fg=colors["text"],
            font=("Segoe UI", 20, "bold"),
            anchor="w",
        )
        lbl_val.pack(fill="x", pady=(4, 2))

        lbl_sub = tk.Label(
            body,
            text=subtitle,
            bg=colors["surface"],
            fg=accent_color,
            font=("Segoe UI", 8),
            anchor="w",
        )
        lbl_sub.pack(fill="x")

        if on_click:
            for w in (self, body, lbl_title, lbl_val, lbl_sub):
                w.bind("<Button-1>", lambda _e: on_click())


class GoalCard(tk.Frame):
    """Streamlined, clickable Goal card with progress ring and clean metadata."""

    def __init__(
        self,
        parent: tk.Widget,
        goal: Goal,
        progress: ProgressStats,
        colors: Dict[str, str],
        on_open_detail: Callable[[str], None],
        on_open_explorer: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(
            parent,
            bg=colors["surface"],
            highlightbackground=colors["border"],
            highlightthickness=1,
            bd=0,
            cursor="hand2",
        )
        self.goal = goal
        self.colors = colors

        strip_color = goal.color or colors["accent"]
        strip = tk.Frame(self, bg=strip_color, width=4)
        strip.pack(side="left", fill="y")

        content = tk.Frame(self, bg=colors["surface"], padx=18, pady=16)
        content.pack(side="left", fill="both", expand=True)

        # Main row: Left info + Right circular ring
        mid_row = tk.Frame(content, bg=colors["surface"])
        mid_row.pack(fill="x")

        text_col = tk.Frame(mid_row, bg=colors["surface"])
        text_col.pack(side="left", fill="both", expand=True, padx=(0, 14))

        # Subtle top metadata line
        meta_top = tk.Frame(text_col, bg=colors["surface"])
        meta_top.pack(fill="x", pady=(0, 4))

        cat_lbl = tk.Label(
            meta_top,
            text=goal.category,
            bg=colors["surface"],
            fg=strip_color,
            font=("Segoe UI", 8, "bold"),
        )
        cat_lbl.pack(side="left")

        dl_text, dl_state = format_relative_deadline(
            goal.deadline, is_completed=(goal.status == "completed")
        )
        dl_fg = (
            colors.get(dl_state, colors["text_muted"])
            if dl_state in ("danger", "warning")
            else colors["text_muted"]
        )
        dl_lbl = tk.Label(
            meta_top,
            text=f"  •  {dl_text}",
            bg=colors["surface"],
            fg=dl_fg,
            font=("Segoe UI", 8),
        )
        dl_lbl.pack(side="left")

        title_lbl = tk.Label(
            text_col,
            text=goal.title,
            bg=colors["surface"],
            fg=colors["text"],
            font=("Segoe UI", 12, "bold"),
            anchor="w",
            justify="left",
            wraplength=340,
        )
        title_lbl.pack(fill="x")

        sub_lbl = tk.Label(
            text_col,
            text=progress.status_label,
            bg=colors["surface"],
            fg=colors["text_muted"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        sub_lbl.pack(fill="x", pady=(4, 0))

        ring_color = (
            colors["positive"]
            if progress.percentage >= 100.0
            else strip_color
        )
        ring = CircularProgressRing(
            mid_row,
            size=54,
            thickness=5,
            percentage=progress.percentage,
            bg_color=colors["surface"],
            track_color=colors["track"],
            fill_color=ring_color,
            text_color=colors["text"],
        )
        ring.pack(side="right")

        bar = SmoothProgressBar(
            content,
            percentage=progress.percentage,
            height=5,
            bg_color=colors["surface"],
            track_color=colors["track"],
            fill_color=ring_color,
        )
        bar.pack(fill="x", pady=(12, 0))

        # Make entire card clickable to open Goal Workspace
        def _open(_e=None, gid=goal.id) -> None:
            on_open_detail(gid)

        for widget in (
            self,
            content,
            mid_row,
            text_col,
            meta_top,
            cat_lbl,
            dl_lbl,
            title_lbl,
            sub_lbl,
            ring,
            bar,
        ):
            widget.bind("<Button-1>", _open)


class BarChartCanvas(tk.Canvas):
    """Pure Tkinter Canvas interactive Bar Chart with gridlines and value labels."""

    def __init__(
        self,
        parent: tk.Widget,
        colors: Dict[str, str],
        height: int = 220,
        bar_color: Optional[str] = None,
        unit_suffix: str = "",
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            height=height,
            bg=colors["surface"],
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.colors = colors
        self.bar_color = bar_color or colors["accent"]
        self.unit_suffix = unit_suffix
        self.data: List[Tuple[str, float, str]] = []  # (label, value, tooltip)
        self.bind("<Configure>", lambda _e: self.render())

    def set_data(
        self,
        data: List[Tuple[str, float, str]],
        bar_color: Optional[str] = None,
    ) -> None:
        self.data = list(data)
        if bar_color:
            self.bar_color = bar_color
        self.render()

    def render(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 300)
        h = max(self.winfo_height(), 180)
        p = self.colors

        if not self.data:
            self.create_text(
                w / 2,
                h / 2,
                text="No chart data available for this range",
                fill=p["text_muted"],
                font=("Segoe UI", 10),
            )
            return

        pad_left, pad_right, pad_top, pad_bottom = 42, 20, 24, 36
        chart_w = max(w - pad_left - pad_right, 100)
        chart_h = max(h - pad_top - pad_bottom, 60)

        max_val = max((val for _, val, _ in self.data), default=1.0)
        if max_val <= 0:
            max_val = 4.0

        # Horizontal grid lines (4 steps)
        for i in range(5):
            frac = i / 4.0
            y = pad_top + chart_h - (frac * chart_h)
            g_val = max_val * frac
            self.create_line(
                pad_left, y, w - pad_right, y, fill=p["border"], dash=(2, 4)
            )
            lbl = (
                f"{int(round(g_val))}{self.unit_suffix}"
                if g_val == int(g_val)
                else f"{g_val:.1f}{self.unit_suffix}"
            )
            self.create_text(
                pad_left - 8,
                y,
                text=lbl,
                anchor="e",
                fill=p["text_muted"],
                font=("Segoe UI", 8),
            )

        n = len(self.data)
        slot_w = chart_w / max(n, 1)
        bar_w = min(max(slot_w * 0.58, 8), 44)

        for idx, (label, val, _tip) in enumerate(self.data):
            cx = pad_left + idx * slot_w + slot_w / 2
            bar_h = (val / max_val) * chart_h if max_val > 0 else 0
            x1 = cx - bar_w / 2
            x2 = cx + bar_w / 2
            y2 = pad_top + chart_h
            y1 = max(pad_top, y2 - bar_h)

            if val > 0:
                draw_rounded_rect(
                    self,
                    x1,
                    y1,
                    x2,
                    y2,
                    radius=4,
                    fill=self.bar_color,
                    outline="",
                )
                val_str = (
                    f"{int(val)}{self.unit_suffix}"
                    if val == int(val)
                    else f"{val:.1f}{self.unit_suffix}"
                )
                self.create_text(
                    cx,
                    y1 - 9,
                    text=val_str,
                    fill=p["text"],
                    font=("Segoe UI", 8, "bold"),
                )
            else:
                self.create_rectangle(
                    x1, y2 - 2, x2, y2, fill=p["track"], outline=""
                )

            self.create_text(
                cx,
                y2 + 14,
                text=label,
                fill=p["text_muted"],
                font=("Segoe UI", 8),
            )


class DonutChartCanvas(tk.Canvas):
    """Pure Tkinter Canvas multi-segment Donut Chart with legend."""

    PALETTE_CYCLE = [
        "#6366F1",
        "#10B981",
        "#F59E0B",
        "#EC4899",
        "#3B82F6",
        "#8B5CF6",
        "#14B8A6",
        "#EF4444",
    ]

    def __init__(
        self,
        parent: tk.Widget,
        colors: Dict[str, str],
        height: int = 220,
        center_title: str = "Total",
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            height=height,
            bg=colors["surface"],
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.colors = colors
        self.center_title = center_title
        self.segments: List[Tuple[str, int, str]] = []  # (label, count, color)
        self.bind("<Configure>", lambda _e: self.render())

    def set_segments(
        self,
        items: List[Tuple[str, int]],
        custom_colors: Optional[List[str]] = None,
    ) -> None:
        self.segments = []
        for i, (lbl, count) in enumerate(items):
            col = (
                custom_colors[i]
                if custom_colors and i < len(custom_colors)
                else self.PALETTE_CYCLE[i % len(self.PALETTE_CYCLE)]
            )
            self.segments.append((lbl, count, col))
        self.render()

    def render(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 280)
        h = max(self.winfo_height(), 180)
        p = self.colors

        total = sum(cnt for _, cnt, _ in self.segments)
        if total <= 0:
            self.create_text(
                w / 2,
                h / 2,
                text="No data available yet",
                fill=p["text_muted"],
                font=("Segoe UI", 10),
            )
            return

        radius = min(h * 0.38, w * 0.24, 76)
        cx = max(radius + 24, w * 0.28)
        cy = h / 2
        thickness = max(14, int(radius * 0.34))

        start_angle = 90.0
        non_zero = [(l, c, col) for l, c, col in self.segments if c > 0]

        if len(non_zero) == 1:
            _, _, only_col = non_zero[0]
            self.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                outline=only_col,
                width=thickness,
            )
        else:
            for _lbl, cnt, col in non_zero:
                extent = -(cnt / total) * 360.0
                self.create_arc(
                    cx - radius,
                    cy - radius,
                    cx + radius,
                    cy + radius,
                    start=start_angle,
                    extent=extent,
                    style="arc",
                    outline=col,
                    width=thickness,
                )
                start_angle += extent

        self.create_text(
            cx,
            cy - 7,
            text=str(total),
            fill=p["text"],
            font=("Segoe UI", 16, "bold"),
        )
        self.create_text(
            cx,
            cy + 12,
            text=self.center_title,
            fill=p["text_muted"],
            font=("Segoe UI", 8),
        )

        # Legend on the right side
        lx = cx + radius + 28
        ly = max(24, cy - (len(self.segments) * 13))
        for i, (lbl, cnt, col) in enumerate(self.segments):
            y = ly + i * 25
            pct = (cnt / total) * 100.0 if total > 0 else 0
            self.create_oval(lx, y - 5, lx + 10, y + 5, fill=col, outline="")
            self.create_text(
                lx + 18,
                y,
                text=f"{lbl}: {cnt} ({pct:.0f}%)",
                anchor="w",
                fill=p["text"],
                font=("Segoe UI", 9),
            )


class InteractiveGoalTreeCanvas(tk.Frame):
    """Interactive zoomable, pannable Canvas displaying the 4-level Goal Hierarchy
    (Goal -> Milestones -> Projects -> Tasks) with Bezier connectors and click selection.
    """

    def __init__(
        self,
        parent: tk.Widget,
        colors: Dict[str, str],
        on_select_node: Optional[Callable[[str, str], None]] = None,
        on_double_click_node: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        super().__init__(parent, bg=colors["canvas_bg"])
        self.colors = colors
        self.on_select_node = on_select_node
        self.on_double_click_node = on_double_click_node

        self.hierarchy: Optional[Dict] = None
        self.zoom: float = 1.0
        self.selected_key: Optional[Tuple[str, str]] = None  # (entity_type, entity_id)
        self._node_hitboxes: List[Tuple[float, float, float, float, str, str]] = []

        # Toolbar overlay
        toolbar = tk.Frame(self, bg=colors["surface_alt"], padx=10, pady=6)
        toolbar.pack(fill="x", side="top")

        tk.Label(
            toolbar,
            text="VISUAL HIERARCHY CANVAS   •   Drag to Pan   •   Click Node to Inspect   •   Double-Click Task to Complete",
            bg=colors["surface_alt"],
            fg=colors["text_muted"],
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")

        for label, cmd in [
            ("Reset View", self.reset_view),
            ("Zoom +", lambda: self.change_zoom(1.15)),
            ("Zoom −", lambda: self.change_zoom(0.87)),
        ]:
            btn = tk.Button(
                toolbar,
                text=label,
                bg=colors["surface"],
                fg=colors["text"],
                relief="flat",
                bd=0,
                padx=8,
                pady=2,
                font=("Segoe UI", 8, "bold"),
                cursor="hand2",
                command=cmd,
            )
            btn.pack(side="right", padx=3)

        self.canvas = tk.Canvas(
            self,
            bg=colors["canvas_bg"],
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

        # Panning and clicking bindings
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<Control-MouseWheel>", self._on_ctrl_wheel)

    def set_hierarchy(
        self,
        hierarchy: Optional[Dict],
        selected_key: Optional[Tuple[str, str]] = None,
    ) -> None:
        self.hierarchy = hierarchy
        if selected_key is not None:
            self.selected_key = selected_key
        self.render()

    def change_zoom(self, factor: float) -> None:
        self.zoom = max(0.55, min(1.75, self.zoom * factor))
        self.render()

    def reset_view(self) -> None:
        self.zoom = 1.0
        self.canvas.xview_moveto(0.0)
        self.canvas.yview_moveto(0.0)
        self.render()

    def _on_ctrl_wheel(self, event: tk.Event) -> None:
        factor = 1.1 if event.delta > 0 else 0.9
        self.change_zoom(factor)

    def _on_press(self, event: tk.Event) -> None:
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        self.canvas.scan_mark(event.x, event.y)

        for x1, y1, x2, y2, etype, eid in reversed(self._node_hitboxes):
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                self.selected_key = (etype, eid)
                self.render()
                if self.on_select_node:
                    self.on_select_node(etype, eid)
                return

    def _on_drag(self, event: tk.Event) -> None:
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_double_click(self, event: tk.Event) -> None:
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        for x1, y1, x2, y2, etype, eid in reversed(self._node_hitboxes):
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                if self.on_double_click_node:
                    self.on_double_click_node(etype, eid)
                return

    def _draw_bezier_connector(
        self, x1: float, y1: float, x2: float, y2: float, color: str
    ) -> None:
        mid_x = (x1 + x2) / 2
        self.canvas.create_line(
            x1,
            y1,
            mid_x,
            y1,
            mid_x,
            y2,
            x2,
            y2,
            smooth=True,
            splinesteps=24,
            fill=color,
            width=max(1.5, 2 * self.zoom),
        )

    def render(self) -> None:
        self.canvas.delete("all")
        self._node_hitboxes.clear()
        p = self.colors
        self.canvas.configure(bg=p["canvas_bg"])

        if not self.hierarchy or not self.hierarchy.get("goal"):
            self.canvas.create_text(
                320,
                220,
                text="Select or create a goal to visualize its execution hierarchy.",
                fill=p["text_muted"],
                font=("Segoe UI", 11),
            )
            return

        z = self.zoom
        goal: Goal = self.hierarchy["goal"]
        g_prog: ProgressStats = self.hierarchy["progress"]
        milestones = self.hierarchy.get("milestones", [])

        # Layout coordinates across 4 columns:
        # Col 0: Goal, Col 1: Milestones, Col 2: Projects, Col 3: Tasks
        col_x = [
            40 * z,
            290 * z,
            560 * z,
            830 * z,
        ]
        node_w = [200 * z, 210 * z, 210 * z, 235 * z]
        node_h = [86 * z, 68 * z, 60 * z, 42 * z]
        v_gap = 16 * z

        # First pass: compute vertical leaf positions bottom-up so branches never overlap
        current_y = 40 * z
        milestone_layouts = []

        for m_entry in milestones:
            m = m_entry["milestone"]
            m_prog = m_entry["progress"]
            proj_entries = m_entry["projects"]
            project_layouts = []

            if not proj_entries:
                py = current_y
                current_y += node_h[1] + v_gap * 1.5
                milestone_layouts.append(
                    {
                        "milestone": m,
                        "progress": m_prog,
                        "y": py,
                        "projects": [],
                    }
                )
                continue

            for p_entry in proj_entries:
                proj = p_entry["project"]
                p_prog = p_entry["progress"]
                tasks = p_entry["tasks"]
                task_layouts = []

                if not tasks:
                    ty = current_y
                    current_y += node_h[2] + v_gap
                    project_layouts.append(
                        {
                            "project": proj,
                            "progress": p_prog,
                            "y": ty,
                            "tasks": [],
                        }
                    )
                else:
                    for t in tasks:
                        task_layouts.append({"task": t, "y": current_y})
                        current_y += node_h[3] + v_gap * 0.75
                    current_y += v_gap * 0.5
                    avg_ty = (task_layouts[0]["y"] + task_layouts[-1]["y"]) / 2
                    project_layouts.append(
                        {
                            "project": proj,
                            "progress": p_prog,
                            "y": avg_ty,
                            "tasks": task_layouts,
                        }
                    )

            avg_py = (project_layouts[0]["y"] + project_layouts[-1]["y"]) / 2
            milestone_layouts.append(
                {
                    "milestone": m,
                    "progress": m_prog,
                    "y": avg_py,
                    "projects": project_layouts,
                }
            )
            current_y += v_gap

        goal_y = (
            (milestone_layouts[0]["y"] + milestone_layouts[-1]["y"]) / 2
            if milestone_layouts
            else 120 * z
        )

        # Draw connectors first (behind nodes)
        gx2 = col_x[0] + node_w[0]
        gy_mid = goal_y + node_h[0] / 2

        for m_lay in milestone_layouts:
            mx1 = col_x[1]
            mx2 = col_x[1] + node_w[1]
            my_mid = m_lay["y"] + node_h[1] / 2
            m_col = (
                p["positive"]
                if m_lay["progress"].percentage >= 100
                else (goal.color or p["accent"])
            )
            self._draw_bezier_connector(gx2, gy_mid, mx1, my_mid, m_col)

            for p_lay in m_lay["projects"]:
                px1 = col_x[2]
                px2 = col_x[2] + node_w[2]
                py_mid = p_lay["y"] + node_h[2] / 2
                p_col = (
                    p["positive"]
                    if p_lay["progress"].percentage >= 100
                    else p["border"]
                )
                self._draw_bezier_connector(mx2, my_mid, px1, py_mid, p_col)

                for t_lay in p_lay["tasks"]:
                    tx1 = col_x[3]
                    ty_mid = t_lay["y"] + node_h[3] / 2
                    t_obj = t_lay["task"]
                    t_col = (
                        p["positive"]
                        if t_obj.status == "completed"
                        else p["border"]
                    )
                    self._draw_bezier_connector(px2, py_mid, tx1, ty_mid, t_col)

        # Draw Goal Node
        self._draw_node_card(
            x=col_x[0],
            y=goal_y,
            w=node_w[0],
            h=node_h[0],
            badge="GOAL",
            title=goal.title,
            subtitle=f"{g_prog.percentage:.0f}%  •  {g_prog.completed_tasks}/{g_prog.total_eligible_tasks} tasks",
            accent=goal.color or p["accent"],
            entity_type="goal",
            entity_id=goal.id,
            is_completed=(goal.status == "completed"),
        )

        # Draw Milestone, Project, and Task Nodes
        for m_lay in milestone_layouts:
            m = m_lay["milestone"]
            m_prog = m_lay["progress"]
            m_comp = m.status == "completed" or (
                m_prog.has_eligible_tasks and m_prog.percentage >= 100.0
            )
            self._draw_node_card(
                x=col_x[1],
                y=m_lay["y"],
                w=node_w[1],
                h=node_h[1],
                badge="MILESTONE",
                title=m.title,
                subtitle=f"{m_prog.percentage:.0f}% ({m_prog.completed_tasks}/{m_prog.total_eligible_tasks})  •  {m.deadline or 'No date'}",
                accent=p["positive"] if m_comp else p["info"],
                entity_type="milestone",
                entity_id=m.id,
                is_completed=m_comp,
            )

            for p_lay in m_lay["projects"]:
                proj = p_lay["project"]
                p_prog = p_lay["progress"]
                p_comp = proj.status == "completed" or (
                    p_prog.has_eligible_tasks and p_prog.percentage >= 100.0
                )
                self._draw_node_card(
                    x=col_x[2],
                    y=p_lay["y"],
                    w=node_w[2],
                    h=node_h[2],
                    badge=f"PROJECT • {proj.priority.upper()}",
                    title=proj.title,
                    subtitle=f"{p_prog.completed_tasks}/{p_prog.total_eligible_tasks} tasks ({p_prog.percentage:.0f}%)",
                    accent=p["positive"] if p_comp else p["warning"],
                    entity_type="project",
                    entity_id=proj.id,
                    is_completed=p_comp,
                )

                for t_lay in p_lay["tasks"]:
                    t = t_lay["task"]
                    t_comp = t.status == "completed"
                    t_canc = t.status == "cancelled"
                    status_icon = (
                        "[✓]"
                        if t_comp
                        else ("[~]" if t.status == "in_progress" else ("[-]" if t_canc else "[ ]"))
                    )
                    t_accent = (
                        p["positive"]
                        if t_comp
                        else (p["danger"] if t.priority == "high" else p["text_muted"])
                    )
                    self._draw_node_card(
                        x=col_x[3],
                        y=t_lay["y"],
                        w=node_w[3],
                        h=node_h[3],
                        badge="",
                        title=f"{status_icon} {t.title}",
                        subtitle=f"{t.priority.upper()} • {t.estimated_minutes}m • {t.due_date or 'No due date'}",
                        accent=t_accent,
                        entity_type="task",
                        entity_id=t.id,
                        is_completed=t_comp,
                        compact=True,
                    )

        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(
                scrollregion=(
                    bbox[0] - 40,
                    bbox[1] - 40,
                    bbox[2] + 80,
                    bbox[3] + 80,
                )
            )

    def _draw_node_card(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        badge: str,
        title: str,
        subtitle: str,
        accent: str,
        entity_type: str,
        entity_id: str,
        is_completed: bool = False,
        compact: bool = False,
    ) -> None:
        p = self.colors
        z = self.zoom
        is_selected = self.selected_key == (entity_type, entity_id)

        outline_col = p["accent"] if is_selected else (p["positive"] if is_completed else p["border"])
        outline_w = 2.5 if is_selected else 1.2
        bg_col = p["surface_hover"] if is_selected else p["surface"]

        draw_rounded_rect(
            self.canvas,
            x,
            y,
            x + w,
            y + h,
            radius=8 * z,
            fill=bg_col,
            outline=outline_col,
            width=outline_w,
        )

        # Left accent pill
        self.canvas.create_rectangle(
            x + 2,
            y + 6 * z,
            x + 6 * z,
            y + h - 6 * z,
            fill=accent,
            outline="",
        )

        max_chars = max(16, int(w / (6.8 * z)))
        clean_title = (
            title[: max_chars - 1] + "…" if len(title) > max_chars else title
        )

        f_badge = ("Segoe UI", max(7, int(7 * z)), "bold")
        f_title = ("Segoe UI", max(8, int(9.5 * z)), "bold")
        f_sub = ("Segoe UI", max(7, int(8 * z)))

        if compact:
            self.canvas.create_text(
                x + 12 * z,
                y + 13 * z,
                text=clean_title,
                anchor="w",
                fill=p["positive"] if is_completed else p["text"],
                font=f_title,
            )
            self.canvas.create_text(
                x + 12 * z,
                y + 29 * z,
                text=subtitle,
                anchor="w",
                fill=p["text_muted"],
                font=f_sub,
            )
        else:
            self.canvas.create_text(
                x + 12 * z,
                y + 13 * z,
                text=badge,
                anchor="w",
                fill=accent,
                font=f_badge,
            )
            self.canvas.create_text(
                x + 12 * z,
                y + 31 * z,
                text=clean_title,
                anchor="w",
                fill=p["text"],
                font=f_title,
            )
            self.canvas.create_text(
                x + 12 * z,
                y + 49 * z,
                text=subtitle,
                anchor="w",
                fill=p["text_muted"],
                font=f_sub,
            )

        self._node_hitboxes.append((x, y, x + w, y + h, entity_type, entity_id))


class GanttTimelineCanvas(tk.Canvas):
    """Graphical Canvas Gantt Timeline plotting Goals, Milestones, Projects, and Tasks."""

    def __init__(
        self,
        parent: tk.Widget,
        colors: Dict[str, str],
        height: int = 440,
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            height=height,
            bg=colors["surface"],
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.colors = colors
        self.rows: List[Dict] = []
        self.bind("<Configure>", lambda _e: self.render())

    def set_items(self, rows: List[Dict]) -> None:
        self.rows = list(rows)
        self.render()

    def render(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 640)
        p = self.colors
        self.configure(bg=p["surface"])

        if not self.rows:
            self.create_text(
                w / 2,
                160,
                text="No dated milestones or tasks to plot on the graphical Gantt timeline.",
                fill=p["text_muted"],
                font=("Segoe UI", 10),
            )
            return

        today = date.today()
        win_start = today - timedelta(days=7)
        win_end = today + timedelta(days=28)
        total_days = (win_end - win_start).days

        label_col_w = 250
        pad_right = 24
        header_h = 38
        row_h = 34
        chart_w = max(w - label_col_w - pad_right, 280)
        day_w = chart_w / total_days

        total_h = max(header_h + len(self.rows) * row_h + 24, 320)

        # Header background
        self.create_rectangle(
            0, 0, w, header_h, fill=p["surface_alt"], outline=""
        )
        self.create_text(
            14,
            header_h / 2,
            text="ENTITY / GOAL HIERARCHY",
            anchor="w",
            fill=p["text_muted"],
            font=("Segoe UI", 8, "bold"),
        )

        # Draw date ticks every 3 days
        for d_idx in range(0, total_days + 1, 3):
            cur_d = win_start + timedelta(days=d_idx)
            x = label_col_w + d_idx * day_w
            self.create_line(
                x, header_h, x, total_h, fill=p["border"], dash=(2, 4)
            )
            self.create_text(
                x,
                header_h / 2,
                text=cur_d.strftime("%b %d"),
                fill=p["text_muted"],
                font=("Segoe UI", 8),
            )

        # Draw rows
        for idx, item in enumerate(self.rows):
            y1 = header_h + idx * row_h
            y2 = y1 + row_h
            cy = (y1 + y2) / 2

            if idx % 2 == 1:
                self.create_rectangle(
                    0, y1, w, y2, fill=p["surface_alt"], outline=""
                )

            prefix = "◆ " if item["type"] == "Milestone" else "  • "
            title = item["title"]
            if len(title) > 28:
                title = title[:27] + "…"

            self.create_text(
                12,
                cy,
                text=f"{prefix}{title}",
                anchor="w",
                fill=p["text"],
                font=(
                    "Segoe UI",
                    9,
                    "bold" if item["type"] == "Milestone" else "normal",
                ),
            )

            s_d = parse_iso_date(item.get("start_date"))
            e_d = parse_iso_date(item.get("end_date"))
            if not e_d and s_d:
                e_d = s_d
            if not s_d and e_d:
                s_d = e_d - timedelta(days=2 if item["type"] == "Milestone" else 1)

            if s_d and e_d:
                s_offset = max(0, min(total_days, (s_d - win_start).days))
                e_offset = max(
                    s_offset + 0.6,
                    min(total_days, (e_d - win_start).days + 1),
                )
                bx1 = label_col_w + s_offset * day_w
                bx2 = label_col_w + e_offset * day_w
                bar_col = item.get("color") or p["accent"]

                draw_rounded_rect(
                    self,
                    bx1,
                    y1 + 8,
                    max(bx1 + 12, bx2),
                    y2 - 8,
                    radius=5,
                    fill=bar_col,
                    outline="",
                )

        # Draw TODAY vertical marker line
        today_offset = (today - win_start).days
        tx = label_col_w + today_offset * day_w
        self.create_line(tx, header_h - 6, tx, total_h, fill=p["danger"], width=2)
        self.create_rectangle(
            tx - 22, 4, tx + 22, 20, fill=p["danger"], outline=""
        )
        self.create_text(
            tx,
            12,
            text="TODAY",
            fill="#FFFFFF",
            font=("Segoe UI", 7, "bold"),
        )

        self.configure(scrollregion=(0, 0, w, total_h))
