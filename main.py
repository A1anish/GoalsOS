"""GoalOS — Personal Goal Planning & Execution Desktop Application.

Entry point for launching the Tkinter desktop application.
"""

import argparse
from typing import Optional

from ui.app_controller import AppController
from ui.main_window import MainWindow, PAGE_CLASSES


def run_app(
    db_path: Optional[str] = None,
    seed_if_empty: bool = True,
    smoke_test: bool = False,
) -> None:
    """Initializes the application controller and launches the main Tkinter window."""
    controller = AppController(db_path=db_path, seed_if_empty=seed_if_empty)
    app = MainWindow(controller)

    if smoke_test:
        # Programmatically exercise every navigation page and theme switch
        def _run_smoke() -> None:
            for page_key in PAGE_CLASSES:
                controller.navigate(page_key)
                app.update_idletasks()
            controller.switch_theme("light")
            app.update_idletasks()
            controller.switch_theme("dark")
            app.update_idletasks()
            controller.navigate("dashboard")
            app.update_idletasks()
            app.destroy()

        app.after(150, _run_smoke)

    app.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GoalOS — Local-first personal goal planning and execution desktop app."
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Optional custom SQLite database file path.",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Do not automatically seed demo data when database is empty.",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Launch UI, cycle through all pages and themes, and exit cleanly.",
    )
    args = parser.parse_args()
    run_app(
        db_path=args.db,
        seed_if_empty=not args.no_seed,
        smoke_test=args.smoke_test,
    )


if __name__ == "__main__":
    main()
