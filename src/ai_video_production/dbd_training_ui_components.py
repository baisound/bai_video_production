"""Reusable Tk layout helpers for Training Studio form/media workflows."""
from __future__ import annotations


class ScrollableForm:
    """Vertical scroll container whose inner frame follows the visible width."""

    def __init__(self, parent, *, padding: int = 8, height: int | None = None):
        import tkinter as tk
        from tkinter import ttk

        self.outer = ttk.Frame(parent)
        self.outer.columnconfigure(0, weight=1)
        self.outer.rowconfigure(0, weight=1)
        options = {"highlightthickness": 0, "borderwidth": 0}
        if height is not None:
            options["height"] = int(height)
        self.canvas = tk.Canvas(self.outer, **options)
        self.scrollbar = ttk.Scrollbar(
            self.outer, orient="vertical", command=self.canvas.yview
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.inner = ttk.Frame(self.canvas, padding=padding)
        self.window = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._refresh, add="+")
        self.canvas.bind("<Configure>", self._fit_width, add="+")
        self.canvas.bind("<Enter>", self._bind_wheel, add="+")
        self.canvas.bind("<Leave>", self._unbind_wheel, add="+")

    def _refresh(self, _event=None):
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=bbox)

    def _fit_width(self, event):
        self.canvas.itemconfigure(self.window, width=max(1, event.width))
        self._refresh()

    def _wheel(self, event):
        if getattr(event, "delta", 0):
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _bind_wheel(self, _event=None):
        self.canvas.bind_all("<MouseWheel>", self._wheel)

    def _unbind_wheel(self, _event=None):
        self.canvas.unbind_all("<MouseWheel>")

    def grid(self, **kwargs):
        self.outer.grid(**kwargs)

    def pack(self, **kwargs):
        self.outer.pack(**kwargs)


def bind_media_minimum_height(
    paned,
    *,
    media_first: bool,
    minimum_fraction: float = 0.5,
    minimum_pixels: int = 260,
) -> None:
    """Keep the media pane usable while allowing the form pane to scroll.

    The shared Training Studio UX never solves an overfull form by cropping the
    video.  A vertical two-pane workflow therefore reserves at least half of the
    available height (and a practical pixel floor where possible) for media.
    """

    if not 0.3 <= float(minimum_fraction) <= 0.8:
        raise ValueError("minimum_fraction must be 0.3..0.8")
    minimum_pixels = max(120, int(minimum_pixels))

    def enforce(_event=None) -> None:
        try:
            total = int(paned.winfo_height())
            if total <= 1:
                return
            media_minimum = min(total - 80, max(minimum_pixels, int(total * minimum_fraction)))
            if media_minimum <= 0:
                return
            sash = int(paned.sashpos(0))
            if media_first:
                desired = media_minimum
                if sash < desired:
                    paned.sashpos(0, desired)
            else:
                desired = max(80, total - media_minimum)
                if sash > desired:
                    paned.sashpos(0, desired)
        except Exception:
            # Geometry managers may call Configure before a sash exists. The
            # next Configure event reapplies the invariant.
            return

    paned.bind("<Configure>", enforce, add="+")
    try:
        paned.after_idle(enforce)
    except Exception:
        pass


__all__ = ["ScrollableForm", "bind_media_minimum_height"]
