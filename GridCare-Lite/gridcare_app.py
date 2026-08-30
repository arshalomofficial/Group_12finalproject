# gridcare_app.py
# GridCare-Lite - Outage and Maintenance Management System
# CS 112 Final Project - Summer 2026
#
# Four roles: admin, engineer, technician, customer_service
#
# Run:
#   cd GridCare-Lite
#   python3 gridcare_app.py

import os
import tkinter as tk
from tkinter import ttk
from datetime import datetime

import database as db


# ── Colour palette ────────────────────────────────────────────────────────────
BG          = "#0f1923"      # very dark navy — main background
PANEL       = "#162030"      # slightly lighter for panels
CARD        = "#1e2d40"      # card / frame background
BORDER      = "#2a3f58"      # borders and separators
GREEN       = "#00c48c"      # primary accent — success / active
GREEN_DK    = "#00916a"      # darker green for hover
AMBER       = "#f59e0b"      # warning / in-progress
RED         = "#ef4444"      # danger / error
BLUE        = "#3b82f6"      # info
WHITE       = "#f0f4f8"      # main text
MUTED       = "#7a93ac"      # secondary text
BTN_TEXT    = "#0f1923"      # text on coloured buttons

FONT_TITLE  = ("Helvetica Neue", 14, "bold")
FONT_HEAD   = ("Helvetica Neue", 11, "bold")
FONT_BODY   = ("Helvetica Neue", 10)
FONT_SMALL  = ("Helvetica Neue", 9)
FONT_MONO   = ("Menlo", 9)

DEMO_ACCOUNTS = """
  admin1        /  Admin@123
  engineer1     /  Engineer@123
  tech1         /  Tech@123
  cs1           /  Service@123
"""


# ── Custom dialog (replaces plain system messagebox) ──────────────────────────
class Dialog(tk.Toplevel):
    """Styled modal dialog — replaces messagebox.showinfo / showerror."""

    ICONS = {
        "info":    ("✓", GREEN),
        "error":   ("✕", RED),
        "warning": ("⚠", AMBER),
        "confirm": ("?", BLUE),
    }

    def __init__(self, parent, title, message, kind="info"):
        super().__init__(parent)
        self.result = False
        self.title(title)
        self.resizable(False, False)
        self.configure(bg=CARD)
        self.grab_set()   # modal
        self.focus_set()

        icon_char, icon_col = self.ICONS.get(kind, ("i", BLUE))

        # icon circle
        top = tk.Frame(self, bg=CARD, pady=22, padx=30)
        top.pack(fill="x")

        circle = tk.Canvas(top, width=52, height=52, bg=CARD, highlightthickness=0)
        circle.pack()
        circle.create_oval(4, 4, 48, 48, fill=icon_col, outline="")
        circle.create_text(26, 27, text=icon_char, fill=BTN_TEXT,
                           font=("Helvetica Neue", 22, "bold"))

        tk.Label(top, text=title, bg=CARD, fg=WHITE,
                 font=FONT_HEAD, pady=8).pack()
        tk.Label(top, text=message, bg=CARD, fg=MUTED,
                 font=FONT_BODY, wraplength=280, justify="center").pack(pady=(0, 18))

        # separator
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # buttons
        btn_row = tk.Frame(self, bg=CARD, pady=14)
        btn_row.pack()

        if kind == "confirm":
            _btn(btn_row, "Cancel", self._cancel, bg=BORDER, fg=WHITE, width=9).pack(side="left", padx=6)
            _btn(btn_row, "Confirm", self._ok, bg=BLUE, fg=BTN_TEXT, width=9).pack(side="left", padx=6)
        else:
            col = icon_col
            _btn(btn_row, "  OK  ", self._ok, bg=col, fg=BTN_TEXT, width=10).pack()

        self._center(parent)
        self.wait_window(self)

    def _ok(self):
        self.result = True
        self.destroy()

    def _cancel(self):
        self.result = False
        self.destroy()

    def _center(self, parent):
        self.update_idletasks()
        pw = parent.winfo_rootx() + parent.winfo_width() // 2
        ph = parent.winfo_rooty() + parent.winfo_height() // 2
        w  = self.winfo_width()
        h  = self.winfo_height()
        self.geometry(f"+{pw - w//2}+{ph - h//2}")


def info_dialog(parent, title, message):
    Dialog(parent, title, message, kind="info")

def error_dialog(parent, title, message):
    Dialog(parent, title, message, kind="error")

def confirm_dialog(parent, title, message):
    d = Dialog(parent, title, message, kind="confirm")
    return d.result


# ── Reusable widget helpers ───────────────────────────────────────────────────

def _btn(parent, text, command, bg=GREEN, fg=BTN_TEXT, width=None, small=False):
    f = FONT_SMALL if small else FONT_BODY
    # make sure fg is always readable — if bg is dark, use WHITE
    actual_fg = fg
    kw = dict(text=text, command=command, bg=bg, fg=actual_fg,
               font=f, relief="flat", cursor="hand2",
               activebackground=_darken(bg), activeforeground=actual_fg,
               padx=12, pady=5, bd=0)
    if width:
        kw["width"] = width
    b = tk.Button(parent, **kw)
    def on_enter(e): b.config(bg=_darken(bg))
    def on_leave(e): b.config(bg=bg)
    b.bind("<Enter>", on_enter)
    b.bind("<Leave>", on_leave)
    return b


def _darken(hex_col):
    """Return a slightly darker shade of a hex colour."""
    try:
        r = max(0, int(hex_col[1:3], 16) - 20)
        g = max(0, int(hex_col[3:5], 16) - 20)
        b = max(0, int(hex_col[5:7], 16) - 20)
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_col


def _label(parent, text, fg=WHITE, font=FONT_BODY, **kw):
    return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=fg, font=font, **kw)


def _entry(parent, show=None, width=28):
    e = tk.Entry(parent, bg=BG, fg=WHITE, insertbackground=WHITE,
                 relief="flat", font=FONT_BODY, width=width,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=GREEN)
    if show:
        e.config(show=show)
    return e


def _combo(parent, textvariable, values, width=30):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("G.TCombobox",
                    fieldbackground=BG, background=CARD,
                    foreground=WHITE, selectforeground=WHITE,
                    selectbackground=BLUE, bordercolor=BORDER,
                    arrowcolor=WHITE, insertcolor=WHITE)
    c = ttk.Combobox(parent, textvariable=textvariable, values=values,
                     width=width, state="readonly", style="G.TCombobox",
                     font=FONT_BODY)
    return c


def _tree(parent, columns, heights=10):
    style = ttk.Style()
    style.configure("G.Treeview",
                    background=BG, foreground=WHITE,
                    fieldbackground=BG, rowheight=28,
                    bordercolor=BORDER, font=FONT_BODY)
    style.configure("G.Treeview.Heading",
                    background=CARD, foreground=MUTED,
                    font=FONT_SMALL, relief="flat")
    style.map("G.Treeview", background=[("selected", BLUE)])
    tv = ttk.Treeview(parent, columns=columns, show="headings",
                      height=heights, style="G.Treeview")
    for col in columns:
        tv.heading(col, text=col.replace("_", " ").title())
        tv.column(col, minwidth=60, stretch=True)
    return tv


def _section_label(parent, text):
    """A coloured section heading with a green left bar."""
    f = tk.Frame(parent, bg=PANEL)
    bar  = tk.Frame(f, bg=GREEN, width=3)
    bar.pack(side="left", fill="y", padx=(0, 8))
    tk.Label(f, text=text, bg=PANEL, fg=WHITE,
             font=FONT_HEAD).pack(side="left", pady=6)
    return f


def _card(parent, padx=10, pady=10):
    f = tk.Frame(parent, bg=CARD, bd=0,
                 highlightthickness=1, highlightbackground=BORDER)
    f.pack(fill="x", padx=padx, pady=pady)
    return f


def _stat_badge(parent, num, label, colour=GREEN):
    f = tk.Frame(parent, bg=CARD, padx=14, pady=10,
                 highlightthickness=1, highlightbackground=BORDER)
    tk.Label(f, text=str(num), bg=CARD, fg=colour,
             font=("Helvetica Neue", 22, "bold")).pack()
    tk.Label(f, text=label, bg=CARD, fg=MUTED,
             font=FONT_SMALL).pack()
    return f


# ── Login window ──────────────────────────────────────────────────────────────

class LoginWindow(tk.Frame):

    def __init__(self, master, on_success):
        super().__init__(master, bg=BG)
        self.master     = master
        self.on_success = on_success
        master.title("GridCare-Lite")
        master.geometry("460x520")
        master.configure(bg=BG)
        master.resizable(False, False)

        self._build()
        self.pack(fill="both", expand=True)

    def _build(self):
        # top green accent bar
        tk.Frame(self, bg=GREEN, height=4).pack(fill="x")

        # logo area
        logo_f = tk.Frame(self, bg=BG, pady=30)
        logo_f.pack(fill="x")

        # icon circle
        c = tk.Canvas(logo_f, width=60, height=60, bg=BG, highlightthickness=0)
        c.pack()
        c.create_oval(4, 4, 56, 56, fill=GREEN, outline="")
        c.create_text(30, 32, text="⚡", fill=BTN_TEXT,
                      font=("Helvetica Neue", 24, "bold"))

        tk.Label(logo_f, text="GridCare-Lite", bg=BG, fg=WHITE,
                 font=("Helvetica Neue", 20, "bold")).pack(pady=(8, 2))
        tk.Label(logo_f, text="Outage & Maintenance Management", bg=BG, fg=MUTED,
                 font=FONT_SMALL).pack()

        # form card
        card = tk.Frame(self, bg=CARD, padx=36, pady=28,
                        highlightthickness=1, highlightbackground=BORDER)
        card.pack(padx=40, pady=10, fill="x")

        _label(card, "Username", fg=MUTED, font=FONT_SMALL).pack(anchor="w")
        self.uname = _entry(card)
        self.uname.pack(fill="x", pady=(3, 12))

        _label(card, "Password", fg=MUTED, font=FONT_SMALL).pack(anchor="w")
        self.pw = _entry(card, show="●")
        self.pw.pack(fill="x", pady=(3, 20))
        self.pw.bind("<Return>", lambda _: self.attempt_login())

        _btn(card, "  Log In  ", self.attempt_login,
             bg=GREEN, fg=BTN_TEXT).pack(fill="x", ipady=4)

        tk.Label(self, text="Demo accounts printed in terminal",
                 bg=BG, fg=MUTED, font=FONT_SMALL).pack(pady=8)
        self.uname.focus_set()

    def attempt_login(self):
        username = self.uname.get().strip()
        password = self.pw.get()
        if not username or not password:
            error_dialog(self.master, "Login Failed", "Enter both username and password.")
            return
        user = db.authenticate_user(username, password)
        if user is None:
            error_dialog(self.master, "Login Failed", "Wrong username or password.")
            return
        self.on_success(username, user["user_id"], user["role"])


# ── Shared base dashboard ─────────────────────────────────────────────────────

class BaseDashboard(tk.Frame):

    def __init__(self, master, username, role, on_logout):
        super().__init__(master, bg=PANEL)
        self.master    = master
        self.username  = username
        self.role      = role
        self.on_logout = on_logout

        # header bar
        hdr = tk.Frame(self, bg=BG, pady=0,
                       highlightthickness=1, highlightbackground=BORDER)
        hdr.pack(fill="x")

        # left: logo
        left = tk.Frame(hdr, bg=BG)
        left.pack(side="left", padx=14, pady=10)
        c = tk.Canvas(left, width=22, height=22, bg=BG, highlightthickness=0)
        c.pack(side="left", padx=(0, 6))
        c.create_oval(2, 2, 20, 20, fill=GREEN, outline="")
        c.create_text(11, 12, text="⚡", fill=BTN_TEXT, font=("Helvetica Neue", 10, "bold"))
        tk.Label(left, text="GridCare-Lite", bg=BG, fg=WHITE,
                 font=("Helvetica Neue", 12, "bold")).pack(side="left")

        # right: user chip + logout
        right = tk.Frame(hdr, bg=BG)
        right.pack(side="right", padx=14, pady=10)
        logout_btn = tk.Button(
            right, text="  Log Out  ",
            command=self.on_logout,
            bg="#e53e3e", fg=WHITE,
            font=FONT_SMALL, relief="flat", cursor="hand2",
            activebackground="#c53030", activeforeground=WHITE,
            padx=10, pady=5, bd=0
        )
        logout_btn.pack(side="right", padx=(8, 0))

        chip = tk.Frame(right, bg="#1e3a5f",
                        highlightthickness=1, highlightbackground="#2a5080")
        chip.pack(side="right")
        tk.Label(chip, text=f"  👤  {username}  ·  {role}  ",
                 bg="#1e3a5f", fg=WHITE, font=FONT_SMALL, pady=5).pack()

        # thin green accent line under header
        tk.Frame(self, bg=GREEN, height=2).pack(fill="x")

        self.pack(fill="both", expand=True)


# ── Engineer dashboard ────────────────────────────────────────────────────────

class EngineerDashboard(BaseDashboard):

    def __init__(self, master, username, user_id, role, on_logout):
        super().__init__(master, username, role, on_logout)
        self.user_id = user_id
        master.title(f"GridCare-Lite — Engineer")

        # scrollable main area
        main = tk.Frame(self, bg=PANEL)
        main.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Report form ──
        _section_label(main, "Report a New Outage").pack(fill="x", padx=14, pady=(14, 4))

        form_card = tk.Frame(main, bg=CARD, padx=16, pady=14,
                             highlightthickness=1, highlightbackground=BORDER)
        form_card.pack(fill="x", padx=14, pady=(0, 10))

        _label(form_card, "Substation", fg=MUTED, font=FONT_SMALL).grid(row=0, column=0, sticky="w", pady=4)
        self.subs    = db.get_all_substations()
        sub_names    = [f"{sid} — {name}  ({region})" for sid, name, region in self.subs]
        self.sub_var = tk.StringVar()
        _combo(form_card, self.sub_var, sub_names, width=44).grid(row=0, column=1, padx=8, pady=4)

        _label(form_card, "Severity", fg=MUTED, font=FONT_SMALL).grid(row=1, column=0, sticky="w", pady=4)
        self.sev_var = tk.StringVar(value="Medium")
        sev_combo = _combo(form_card, self.sev_var, ["Low", "Medium", "High", "Critical"], width=44)
        sev_combo.grid(row=1, column=1, padx=8, pady=4)

        _label(form_card, "Description", fg=MUTED, font=FONT_SMALL).grid(row=2, column=0, sticky="nw", pady=4)
        self.desc = tk.Text(form_card, width=44, height=3, bg=BG, fg=WHITE,
                            insertbackground=WHITE, relief="flat", font=FONT_BODY,
                            highlightthickness=1, highlightbackground=BORDER,
                            highlightcolor=GREEN)
        self.desc.grid(row=2, column=1, padx=8, pady=4)

        btn_row = tk.Frame(form_card, bg=CARD)
        btn_row.grid(row=3, column=0, columnspan=2, pady=(8, 0))
        _btn(btn_row, "  Log Outage  ", self.submit, bg=GREEN, fg=BTN_TEXT).pack()

        # ── Outage list ──
        _section_label(main, "Recent Outages").pack(fill="x", padx=14, pady=(6, 4))

        tree_card = tk.Frame(main, bg=CARD, padx=8, pady=8,
                             highlightthickness=1, highlightbackground=BORDER)
        tree_card.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        cols = ("id", "substation", "description", "severity", "status", "reported_at")
        self.tree = _tree(tree_card, cols, heights=8)
        vsb = ttk.Scrollbar(tree_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        _btn(main, "  ↻  Refresh  ", self.load, bg="#2a5080", fg=WHITE, small=True).pack(pady=(0, 10))
        self.load()

    def submit(self):
        sel  = self.sub_var.get()
        desc = self.desc.get("1.0", "end").strip()
        if not sel:
            error_dialog(self.master, "Missing", "Please select a substation.")
            return
        if not desc:
            error_dialog(self.master, "Missing", "Please add a description.")
            return
        sub_id = int(sel.split(" — ")[0])
        db.log_outage(sub_id, self.user_id, desc, self.sev_var.get())
        info_dialog(self.master, "Outage Logged", "The outage has been recorded.")
        self.desc.delete("1.0", "end")
        self.sub_var.set("")
        self.load()

    def load(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for o in db.get_outages():
            self.tree.insert("", "end", values=o)


# ── Report window ─────────────────────────────────────────────────────────────

class ReportWindow(tk.Toplevel):

    def __init__(self, master):
        super().__init__(master)
        self.title("Operational Report")
        self.geometry("580x560")
        self.configure(bg=PANEL)
        self.resizable(False, False)

        tk.Frame(self, bg=GREEN, height=3).pack(fill="x")
        _label(self, "Operational Report", fg=WHITE,
               font=("Helvetica Neue", 14, "bold")).pack(pady=(16, 0))

        stats = db.get_report_stats()

        # stat badges
        badges = tk.Frame(self, bg=PANEL)
        badges.pack(pady=14)
        _stat_badge(badges, stats["open"],        "Open",        RED).pack(side="left", padx=8)
        _stat_badge(badges, stats["in_progress"], "In Progress", AMBER).pack(side="left", padx=8)
        _stat_badge(badges, stats["resolved"],    "Resolved",    GREEN).pack(side="left", padx=8)

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=16)

        # filter
        flt_row = tk.Frame(self, bg=PANEL)
        flt_row.pack(fill="x", padx=16, pady=10)
        _label(flt_row, "Filter:", fg=MUTED, font=FONT_SMALL).pack(side="left")
        self.flt = tk.StringVar(value="All")
        _combo(flt_row, self.flt,
               ["All", "Open", "In Progress", "Resolved"], width=16).pack(side="left", padx=8)
        _btn(flt_row, "Apply", self._apply, bg=BLUE, fg=WHITE, small=True).pack(side="left")

        # by region
        _section_label(self, "Outages by Region").pack(fill="x", padx=16, pady=(6, 4))
        r_card = tk.Frame(self, bg=CARD, padx=8, pady=8,
                          highlightthickness=1, highlightbackground=BORDER)
        r_card.pack(fill="x", padx=16)
        self.rtree = _tree(r_card, ("region", "count"), heights=4)
        self.rtree.pack(fill="x")
        for region, count in stats["by_region"]:
            self.rtree.insert("", "end", values=(region, count))

        # filtered outages
        _section_label(self, "Filtered Outages").pack(fill="x", padx=16, pady=(10, 4))
        d_card = tk.Frame(self, bg=CARD, padx=8, pady=8,
                          highlightthickness=1, highlightbackground=BORDER)
        d_card.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        dcols = ("id", "substation", "severity", "status", "reported_at")
        self.dtree = _tree(d_card, dcols, heights=6)
        self.dtree.pack(fill="both", expand=True)
        self._apply()

        _btn(self, "  Close  ", self.destroy, bg="#2a5080", fg=WHITE, small=True).pack(pady=(0, 12))

    def _apply(self):
        for row in self.dtree.get_children():
            self.dtree.delete(row)
        for o in db.get_outages(status_filter=self.flt.get()):
            self.dtree.insert("", "end", values=(o[0], o[1], o[3], o[4], o[5]))


# ── Admin dashboard ───────────────────────────────────────────────────────────

class AdminDashboard(BaseDashboard):

    def __init__(self, master, username, user_id, role, on_logout):
        super().__init__(master, username, role, on_logout)
        self.user_id = user_id
        master.title("GridCare-Lite — Admin")

        main = tk.Frame(self, bg=PANEL)
        main.pack(fill="both", expand=True)

        # top bar with report button
        top = tk.Frame(main, bg=PANEL)
        top.pack(fill="x", padx=14, pady=(12, 4))
        _section_label(top, "All Outages").pack(side="left")
        _btn(top, "  📊  View Report  ",
             lambda: ReportWindow(self.master),
             bg=BLUE, fg=WHITE, small=True).pack(side="right")

        # outage list
        tree_card = tk.Frame(main, bg=CARD, padx=8, pady=8,
                             highlightthickness=1, highlightbackground=BORDER)
        tree_card.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        cols = ("id", "substation", "description", "severity", "status", "reported_at")
        self.tree = _tree(tree_card, cols, heights=7)
        vsb = ttk.Scrollbar(tree_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        _btn(main, " ↻ Refresh ", self.load, bg="#2a5080", fg=WHITE, small=True).pack(pady=(0, 6))

        # work order form
        _section_label(main, "Assign Work Order").pack(fill="x", padx=14, pady=(4, 4))
        wo_card = tk.Frame(main, bg=CARD, padx=16, pady=12,
                           highlightthickness=1, highlightbackground=BORDER)
        wo_card.pack(fill="x", padx=14, pady=(0, 8))

        _label(wo_card, "Technician", fg=MUTED, font=FONT_SMALL).grid(row=0, column=0, sticky="w", pady=4)
        self.techs    = db.get_all_technicians()
        self.tech_var = tk.StringVar()
        _combo(wo_card, self.tech_var,
               [f"{tid} — {n}" for tid, n in self.techs], width=36).grid(row=0, column=1, padx=8, pady=4)

        _label(wo_card, "Scheduled Date", fg=MUTED, font=FONT_SMALL).grid(row=1, column=0, sticky="w", pady=4)
        self.date_e = _entry(wo_card, width=36)
        self.date_e.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_e.grid(row=1, column=1, padx=8, pady=4)

        _btn(wo_card, "  Assign Work Order  ", self.create_wo,
             bg=GREEN, fg=BTN_TEXT).grid(row=2, column=0, columnspan=2, pady=(8, 0))

        # resolve form
        _section_label(main, "Resolve Selected Outage").pack(fill="x", padx=14, pady=(4, 4))
        res_card = tk.Frame(main, bg=CARD, padx=16, pady=12,
                            highlightthickness=1, highlightbackground=BORDER)
        res_card.pack(fill="x", padx=14, pady=(0, 12))

        _label(res_card, "Resolution Notes", fg=MUTED, font=FONT_SMALL).grid(row=0, column=0, sticky="nw", pady=4)
        self.res_notes = tk.Text(res_card, width=38, height=2, bg=BG, fg=WHITE,
                                 insertbackground=WHITE, relief="flat", font=FONT_BODY,
                                 highlightthickness=1, highlightbackground=BORDER,
                                 highlightcolor=GREEN)
        self.res_notes.grid(row=0, column=1, padx=8, pady=4)

        _btn(res_card, "  Mark Resolved  ", self.resolve,
             bg=AMBER, fg=BTN_TEXT).grid(row=1, column=0, columnspan=2, pady=(8, 0))

        self.load()

    def load(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for o in db.get_outages():
            self.tree.insert("", "end", values=o)

    def create_wo(self):
        sel = self.tree.selection()
        if not sel:
            error_dialog(self.master, "Nothing Selected", "Click an outage in the list first.")
            return
        oid = self.tree.item(sel[0])["values"][0]
        if not self.techs:
            error_dialog(self.master, "No Technicians", "No technician accounts found.")
            return
        if not self.tech_var.get():
            error_dialog(self.master, "Missing", "Choose a technician.")
            return
        dt = self.date_e.get().strip()
        try:
            datetime.strptime(dt, "%Y-%m-%d")
        except ValueError:
            error_dialog(self.master, "Bad Date", "Use YYYY-MM-DD format.")
            return
        tid = int(self.tech_var.get().split(" — ")[0])
        db.create_work_order(oid, tid, dt, self.user_id)
        info_dialog(self.master, "Work Order Created", f"Work order created for outage #{oid}.")
        self.load()

    def resolve(self):
        sel = self.tree.selection()
        if not sel:
            error_dialog(self.master, "Nothing Selected", "Click an outage in the list first.")
            return
        oid   = self.tree.item(sel[0])["values"][0]
        notes = self.res_notes.get("1.0", "end").strip()
        if confirm_dialog(self.master, "Confirm Resolve",
                          f"Mark outage #{oid} as Resolved?"):
            db.resolve_outage(oid, notes)
            info_dialog(self.master, "Resolved", f"Outage #{oid} has been resolved.")
            self.res_notes.delete("1.0", "end")
            self.load()


# ── Technician dashboard ──────────────────────────────────────────────────────

class TechnicianDashboard(BaseDashboard):

    def __init__(self, master, username, user_id, role, on_logout):
        super().__init__(master, username, role, on_logout)
        self.user_id = user_id
        master.title("GridCare-Lite — Technician")

        main = tk.Frame(self, bg=PANEL)
        main.pack(fill="both", expand=True)

        _section_label(main, "My Work Orders").pack(fill="x", padx=14, pady=(14, 4))

        tree_card = tk.Frame(main, bg=CARD, padx=8, pady=8,
                             highlightthickness=1, highlightbackground=BORDER)
        tree_card.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        cols = ("wo_id", "outage_id", "substation", "description", "status", "scheduled_date")
        self.tree = _tree(tree_card, cols, heights=12)
        vsb = ttk.Scrollbar(tree_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        btn_row = tk.Frame(main, bg=PANEL)
        btn_row.pack(fill="x", padx=14, pady=(0, 12))
        _btn(btn_row, " ↻ Refresh ", self.load, bg="#2a5080", fg=WHITE, small=True).pack(side="left", padx=(0, 6))
        _btn(btn_row, "  Mark 'In Progress'  ",
             lambda: self.update("In Progress"), bg=AMBER, fg=BTN_TEXT, small=True).pack(side="left", padx=6)
        _btn(btn_row, "  Mark 'Completed'  ",
             lambda: self.update("Completed"), bg=GREEN, fg=BTN_TEXT, small=True).pack(side="left", padx=6)
        self.load()

    def load(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for wo in db.get_work_orders_for_technician(self.user_id):
            self.tree.insert("", "end", values=wo)

    def update(self, status):
        sel = self.tree.selection()
        if not sel:
            error_dialog(self.master, "Nothing Selected", "Click a work order first.")
            return
        wid = self.tree.item(sel[0])["values"][0]
        db.update_work_order_status(wid, status)
        info_dialog(self.master, "Updated", f"Work order #{wid} is now '{status}'.")
        self.load()


# ── Customer service dashboard ────────────────────────────────────────────────

class CustomerServiceDashboard(BaseDashboard):

    def __init__(self, master, username, user_id, role, on_logout):
        super().__init__(master, username, role, on_logout)
        self.user_id = user_id
        master.title("GridCare-Lite — Customer Service")

        main = tk.Frame(self, bg=PANEL)
        main.pack(fill="both", expand=True)

        _section_label(main, "Log a Customer Complaint").pack(fill="x", padx=14, pady=(14, 4))

        form_card = tk.Frame(main, bg=CARD, padx=16, pady=14,
                             highlightthickness=1, highlightbackground=BORDER)
        form_card.pack(fill="x", padx=14, pady=(0, 10))

        _label(form_card, "Customer Name", fg=MUTED, font=FONT_SMALL).grid(row=0, column=0, sticky="w", pady=4)
        self.name_e = _entry(form_card, width=38)
        self.name_e.grid(row=0, column=1, padx=8, pady=4)

        _label(form_card, "Contact Info", fg=MUTED, font=FONT_SMALL).grid(row=1, column=0, sticky="w", pady=4)
        self.contact_e = _entry(form_card, width=38)
        self.contact_e.grid(row=1, column=1, padx=8, pady=4)

        _label(form_card, "Related Outage", fg=MUTED, font=FONT_SMALL).grid(row=2, column=0, sticky="w", pady=4)
        outages        = db.get_outages()
        self.out_opts  = ["None"] + [f"{o[0]} — {o[1]} ({o[4]})" for o in outages]
        self.out_var   = tk.StringVar(value="None")
        _combo(form_card, self.out_var, self.out_opts, width=36).grid(row=2, column=1, padx=8, pady=4)

        _label(form_card, "Description", fg=MUTED, font=FONT_SMALL).grid(row=3, column=0, sticky="nw", pady=4)
        self.desc = tk.Text(form_card, width=38, height=3, bg=BG, fg=WHITE,
                            insertbackground=WHITE, relief="flat", font=FONT_BODY,
                            highlightthickness=1, highlightbackground=BORDER,
                            highlightcolor=GREEN)
        self.desc.grid(row=3, column=1, padx=8, pady=4)

        _btn(form_card, "  Log Complaint  ", self.submit,
             bg=GREEN, fg=BTN_TEXT).grid(row=4, column=0, columnspan=2, pady=(10, 0))

        _section_label(main, "Logged Complaints").pack(fill="x", padx=14, pady=(6, 4))

        lc = tk.Frame(main, bg=CARD, padx=8, pady=8,
                      highlightthickness=1, highlightbackground=BORDER)
        lc.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        cols = ("id", "outage_id", "customer", "contact", "description", "logged_at")
        self.tree = _tree(lc, cols, heights=7)
        vsb = ttk.Scrollbar(lc, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        _btn(main, " ↻ Refresh ", self.load, bg="#2a5080", fg=WHITE, small=True).pack(pady=(0, 10))
        self.load()

    def submit(self):
        name = self.name_e.get().strip()
        desc = self.desc.get("1.0", "end").strip()
        if not name or not desc:
            error_dialog(self.master, "Missing", "Name and description are required.")
            return
        oid = None
        if self.out_var.get() != "None":
            oid = int(self.out_var.get().split(" — ")[0])
        db.log_complaint(oid, name, self.contact_e.get().strip(), desc, self.user_id)
        info_dialog(self.master, "Logged", "Complaint has been recorded.")
        self.name_e.delete(0, "end")
        self.contact_e.delete(0, "end")
        self.desc.delete("1.0", "end")
        self.load()

    def load(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for c in db.get_complaints():
            self.tree.insert("", "end", values=c)


# ── App controller ────────────────────────────────────────────────────────────

class GridCareApp:

    def __init__(self, root):
        self.root = root
        self.root.configure(bg=BG)
        self.show_login()

    def _clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    def show_login(self):
        self._clear()
        self.root.geometry("460x520")
        self.root.resizable(False, False)
        LoginWindow(self.root, on_success=self.show_dashboard)

    def show_dashboard(self, username, user_id, role):
        self._clear()
        self.root.geometry("860x680")
        self.root.resizable(True, True)
        MAP = {
            "engineer":         EngineerDashboard,
            "admin":            AdminDashboard,
            "technician":       TechnicianDashboard,
            "customer_service": CustomerServiceDashboard,
        }
        cls = MAP.get(role)
        if cls is None:
            error_dialog(self.root, "Unknown Role", f"No dashboard for role '{role}'.")
            self.show_login()
            return
        cls(self.root, username, user_id, role, on_logout=self.show_login)


# ── Startup ───────────────────────────────────────────────────────────────────

def bootstrap_database():
    db.init_db()
    db.seed_demo_users()
    paths = [
        os.path.join("..", "DataScience", "substations.csv"),
        os.path.join("DataScience", "substations.csv"),
        "substations.csv",
    ]
    for p in paths:
        if os.path.exists(p):
            n = db.import_substations_from_csv(p)
            print(f"Imported {n} substations from {p}")
            return
    print("Warning: substations.csv not found.")


def main():
    bootstrap_database()
    print("\nDemo accounts (username / password)")
    print(DEMO_ACCOUNTS)
    root = tk.Tk()
    root.configure(bg=BG)
    GridCareApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
