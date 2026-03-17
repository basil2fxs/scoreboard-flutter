#!/usr/bin/env python3
"""
Mobile-style TF-F6 Scoreboard GUI (UDP)

- Designed for a tall, phone-like window.
- Auto-connects on boot to 192.168.1.252:5959 over UDP.
- Home screen:
    - Connect button
    - Select Sport (disabled until connected)
    - Manage Scores (disabled until connected & sport selected)
    - Small "Edit Home Screen Text" button bottom-right.

- Sports:
    - AFL (count-up)  -> *#1PRGC31,0000
    - AFL (count-down)-> *#1PRGC32,0000
    - Soccer          -> *#1PRGC33,0000
    - Cricket         -> *#1PRGC34,0000

- Manage Scores implemented for Soccer for now.

Soccer Manage Scores:
    - On entering page (and connected):
        - Switch to Soccer program: *#1PRGC33,0000
        - Restore last sport state from JSON (names, scores, half, styles)
        - If no prior saved state, start from HOME/AWAY, 0–0, 1st HALF.

    - Timer1 controls:
        - Start  -> *#1TIMS1,0000
        - Pause  -> *#1TIMP1,0000
        - Reset  -> *#1TIMR1,0000

    - HALF area (RAMT3):
        - 1st HALF -> *#1RAMT3,[A][B]11st HALF0000
        - 2nd HALF -> *#1RAMT3,[A][B]112nd HALF0000
        - Style settings for HALF text (color + size) affect A/B.

    - Team names (default HOME/AWAY) via RAMT1 / RAMT2:
        - Home -> *#1RAMT1,[A][B]11<HOME>0000
        - Away -> *#1RAMT2,[A][B]11<AWAY>0000
        - Each has its own color + size settings.

    - Scores (CNTS1/2):
        - On new match/reset:
            *#1CNTS1,S0,0000
            *#1CNTS2,S0,0000
        - +1 / -1 buttons:
            Home + -> *#1CNTS1,A1,0000
            Home - -> *#1CNTS1,D1,0000
            Away + -> *#1CNTS2,A1,0000
            Away - -> *#1CNTS2,D1,0000
        - App mirrors the score locally and persists it.

    - Half/Full/Return buttons:
        - Half Time Screen:
            *#1PRGC30,0000
            *#1RAMT1,1211Half Time0000
        - Full Time Screen:
            *#1PRGC30,0000
            *#1RAMT1,1211Full Time0000
        - Return to Scores:
            *#1PRGC33,0000
            then resend:
                - current names (RAMT1/2),
                - current half (RAMT3),
                - scores via S command:
                    *#1CNTS1,S<HomeScore>,0000
                    *#1CNTS2,S<AwayScore>,0000

- Edit Home Screen Text:
    - Simple preview + text box for RAMT1.
    - Sends *#1RAMT1,[A][B]11<Text>0000 with chosen color & size.

State persistence:
    - Stored in scoreboard_state.json:
        sport, home_name, away_name, scores, half, styles, home_banner_text.
    - State is updated and saved after every change.
"""

import json
import os
import socket
import tkinter as tk
from tkinter import ttk, messagebox

STATE_FILE = "scoreboard_state.json"


# ----------------------------- Helper: State ----------------------------- #

DEFAULT_STATE = {
    "sport": "Soccer",          # AFL_UP, AFL_DOWN, Soccer, Cricket
    "home_name": "HOME",
    "away_name": "AWAY",
    "home_score": 0,
    "away_score": 0,
    "current_half": 1,          # 1 or 2
    "half_style": {"color": "1", "size": "1"},   # A,B for RAMT3
    "name_style": {             # shared default style for both names
        "home": {"color": "1", "size": "3"},
        "away": {"color": "1", "size": "3"},
    },
    "home_banner_text": "WELCOME",
}


def load_state():
    if not os.path.exists(STATE_FILE):
        return DEFAULT_STATE.copy()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge with defaults in case we add fields later
        state = DEFAULT_STATE.copy()
        state.update(data)
        # Deep merge nested dicts if missing
        if "half_style" not in state:
            state["half_style"] = DEFAULT_STATE["half_style"].copy()
        if "name_style" not in state:
            state["name_style"] = DEFAULT_STATE["name_style"].copy()
        return state
    except Exception:
        return DEFAULT_STATE.copy()


def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to save state: {e}")


# ----------------------------- Main App ----------------------------- #

class ScoreboardApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # Window config – tall, phone-style layout
        self.title("TF-F6 Scoreboard Controller")
        self.geometry("430x800")           # mobile-ish ratio
        self.minsize(380, 720)
        self.configure(bg="#121212")

        # Basic styles
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "TButton",
            font=("Segoe UI", 14),
            padding=10,
        )
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 16, "bold"),
        )
        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 20, "bold"),
            foreground="white",
            background="#121212",
        )
        style.configure(
            "Subtitle.TLabel",
            font=("Segoe UI", 12),
            foreground="#cccccc",
            background="#121212",
        )
        style.configure(
            "Status.TLabel",
            font=("Segoe UI", 11, "bold"),
            background="#121212",
        )
        style.configure(
            "Card.TFrame",
            background="#1f1f1f",
            relief="ridge",
            borderwidth=1,
        )
        style.configure(
            "Card.TLabel",
            background="#1f1f1f",
            foreground="white",
        )

        # UDP controller info
        self.controller_ip = "192.168.1.252"
        self.controller_port = 5959
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.connected = False

        # Persistent state
        self.state = load_state()

        # Tk variables
        self.sport_var = tk.StringVar(value=self.state["sport"])
        self.connection_status_var = tk.StringVar(value="Disconnected")
        self.connection_color = "#ff5555"
        self.home_name_var = tk.StringVar(value=self.state["home_name"])
        self.away_name_var = tk.StringVar(value=self.state["away_name"])
        self.home_score_var = tk.IntVar(value=self.state["home_score"])
        self.away_score_var = tk.IntVar(value=self.state["away_score"])
        self.current_half_var = tk.IntVar(value=self.state["current_half"])
        self.home_banner_var = tk.StringVar(value=self.state["home_banner_text"])

        # Frame container
        container = ttk.Frame(self, padding=8)
        container.pack(fill="both", expand=True)
        container.configure(style="Card.TFrame")

        self.frames = {}

        for F in (HomeScreen, EditHomeTextScreen, SportSelectScreen, SoccerScoresScreen):
            frame = F(parent=container, app=self)
            frame.grid(row=0, column=0, sticky="nsew")
            self.frames[F.__name__] = frame

        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.show_frame("HomeScreen")

        # Auto-connect shortly after start
        self.after(300, self.auto_connect)

    # ------------- Navigation ------------- #

    def show_frame(self, name):
        frame = self.frames[name]
        frame.tkraise()
        if name == "SoccerScoresScreen":
            frame.on_show()

    # ------------- UDP / Commands ------------- #

    def send_command(self, cmd, add_crlf=False):
        """Send ASCII command over UDP. Silent if not connected."""
        if not self.connected:
            print(f"[INFO] Not connected, ignoring command: {cmd}")
            return
        msg = cmd + ("\r\n" if add_crlf else "")
        try:
            print(f"[SEND] {repr(msg)}")
            self.sock.sendto(msg.encode("ascii"), (self.controller_ip, self.controller_port))
        except OSError as e:
            print(f"[ERROR] send_command failed: {e}")
            # keep GUI alive but mark disconnected logically
            self.set_disconnected(message=f"Network error: {e}")

    def auto_connect(self):
        """Try to 'auto search' and connect."""
        if self.connected:
            return
        self.connect_to_controller(auto=True)

    def connect_to_controller(self, auto=False):
        """Update UI state and send initial program command."""
        # For UDP we don't have a real handshake.
        # We'll mark as connected immediately.
        self.connected = True
        self.connection_status_var.set(
            f"Connected to {self.controller_ip}:{self.controller_port}"
        )
        self.connection_color = "#55ff55"
        # Update home screen button states
        home = self.frames["HomeScreen"]
        home.update_connection_state()

        # On first connect, send half-time program as requested
        self.send_command("*#1PRGC30,0000")

        if not auto:
            messagebox.showinfo("Connected", "Connection initialised over UDP.")

    def set_disconnected(self, message=None):
        self.connected = False
        self.connection_status_var.set("Disconnected")
        self.connection_color = "#ff5555"
        home = self.frames["HomeScreen"]
        home.update_connection_state()
        if message:
            messagebox.showwarning("Disconnected", message)

    # ------------- State helpers ------------- #

    def update_state(self, **kwargs):
        """Update state dict + save + sync Tk variables where needed."""
        self.state.update(kwargs)

        # Mirror specific keys to Tk vars
        if "sport" in kwargs:
            self.sport_var.set(self.state["sport"])
        if "home_name" in kwargs:
            self.home_name_var.set(self.state["home_name"])
        if "away_name" in kwargs:
            self.away_name_var.set(self.state["away_name"])
        if "home_score" in kwargs:
            self.home_score_var.set(self.state["home_score"])
        if "away_score" in kwargs:
            self.away_score_var.set(self.state["away_score"])
        if "current_half" in kwargs:
            self.current_half_var.set(self.state["current_half"])
        if "home_banner_text" in kwargs:
            self.home_banner_var.set(self.state["home_banner_text"])

        save_state(self.state)

    # ------------- Convenience wrappers for scoreboard actions ------------- #

    def program_for_current_sport(self):
        """Return PRGC program index for current sport."""
        sport = self.state["sport"]
        if sport == "AFL_UP":
            return "31"
        if sport == "AFL_DOWN":
            return "32"
        if sport == "Soccer":
            return "33"
        if sport == "Cricket":
            return "34"
        # fallback
        return "33"

    def switch_to_sport_program(self):
        """Send PRGC command for selected sport (on Manage Scores)."""
        prog = self.program_for_current_sport()
        cmd = f"*#1PRGC3{prog[-1]},0000" if len(prog) == 2 else f"*#1PRGC3{prog},0000"
        # For given mapping, we know:
        # *#1PRGC31,0000, *#1PRGC32,0000, *#1PRGC33,0000, *#1PRGC34,0000
        self.send_command(cmd)

    # --- Names & Scores ---

    def send_team_names(self):
        """Send HOME/AWAY names with their styles."""
        hs = self.state["name_style"]["home"]
        as_ = self.state["name_style"]["away"]
        home_cmd = f"*#1RAMT1,{hs['color']}{hs['size']}11{self.state['home_name']}0000"
        away_cmd = f"*#1RAMT2,{as_['color']}{as_['size']}11{self.state['away_name']}0000"
        self.send_command(home_cmd)
        self.send_command(away_cmd)

    def send_half_text(self):
        """Send HALF label (1st/2nd) using RAMT3 with stored style."""
        hs = self.state["half_style"]
        half_text = "1st HALF" if self.state["current_half"] == 1 else "2nd HALF"
        cmd = f"*#1RAMT3,{hs['color']}{hs['size']}11{half_text}0000"
        self.send_command(cmd)

    def reset_scores_to_zero(self):
        """Reset both counters locally + on display."""
        self.update_state(home_score=0, away_score=0)
        # Use S0 commands to explicitly set
        self.send_command("*#1CNTS1,S0,0000")
        self.send_command("*#1CNTS2,S0,0000")

    def apply_score_diff(self, team, delta):
        """Apply +1/-1 via A1/D1 commands and update state."""
        if team == "home":
            current = self.state["home_score"]
            new_val = max(0, current + delta)
            if new_val == current:
                return
            if delta > 0:
                for _ in range(delta):
                    self.send_command("*#1CNTS1,A1,0000")
            else:
                for _ in range(-delta):
                    self.send_command("*#1CNTS1,D1,0000")
            self.update_state(home_score=new_val)
        else:
            current = self.state["away_score"]
            new_val = max(0, current + delta)
            if new_val == current:
                return
            if delta > 0:
                for _ in range(delta):
                    self.send_command("*#1CNTS2,A1,0000")
            else:
                for _ in range(-delta):
                    self.send_command("*#1CNTS2,D1,0000")
            self.update_state(away_score=new_val)

    def resend_all_scores_and_names(self):
        """Used on 'Return to Scores' button."""
        # Return to soccer program
        self.send_command("*#1PRGC33,0000")

        # Resend names
        self.send_team_names()

        # Resend half
        self.send_half_text()

        # Resend scores using S-value to ensure correct state
        hs = self.state["home_score"]
        as_ = self.state["away_score"]
        self.send_command(f"*#1CNTS1,S{hs},0000")
        self.send_command(f"*#1CNTS2,S{as_},0000")

    # --- Timer controls ---

    def timer_start(self):
        self.send_command("*#1TIMS1,0000")

    def timer_pause(self):
        self.send_command("*#1TIMP1,0000")

    def timer_reset(self):
        self.send_command("*#1TIMR1,0000")

    # --- Edit Home Banner ---

    def send_home_banner(self, color="1", size="2"):
        """Send home/banner text to RAMT1 (preview + real)."""
        text = self.home_banner_var.get()
        cmd = f"*#1RAMT1,{color}{size}11{text}0000"
        self.send_command(cmd)

    def on_close(self):
        self.destroy()


# ----------------------------- Frames / Screens ----------------------------- #

class HomeScreen(ttk.Frame):
    def __init__(self, parent, app: ScoreboardApp):
        super().__init__(parent)
        self.app = app
        self.configure(style="Card.TFrame")

        # Layout
        top = ttk.Frame(self, style="Card.TFrame")
        top.pack(fill="x", pady=(8, 16))

        label_title = ttk.Label(top, text="Scoreboard", style="Title.TLabel")
        label_title.pack(anchor="center")

        subtitle = ttk.Label(
            top,
            text="TF-F6 Controller · Mobile UI",
            style="Subtitle.TLabel",
        )
        subtitle.pack(anchor="center", pady=(4, 0))

        # Connection status
        status_frame = ttk.Frame(self, style="Card.TFrame")
        status_frame.pack(fill="x", pady=(8, 8))
        self.status_label = ttk.Label(
            status_frame,
            textvariable=self.app.connection_status_var,
            style="Status.TLabel",
        )
        self.status_label.pack(anchor="center")

        # Sport in use
        sport_frame = ttk.Frame(self, style="Card.TFrame")
        sport_frame.pack(fill="x", pady=(4, 16))
        ttk.Label(sport_frame, text="Current Sport:", style="Subtitle.TLabel").pack(
            side="left"
        )
        self.sport_label = ttk.Label(
            sport_frame,
            textvariable=self.app.sport_var,
            style="Subtitle.TLabel",
        )
        self.sport_label.pack(side="left", padx=(4, 0))

        # Main buttons (large)
        btn_frame = ttk.Frame(self, style="Card.TFrame")
        btn_frame.pack(fill="both", expand=True)

        self.connect_btn = ttk.Button(
            btn_frame,
            text="Connect",
            style="Primary.TButton",
            command=lambda: self.app.connect_to_controller(auto=False),
        )
        self.connect_btn.pack(fill="x", pady=(16, 12))

        self.select_sport_btn = ttk.Button(
            btn_frame,
            text="Select Sport",
            command=lambda: self.app.show_frame("SportSelectScreen"),
            state="disabled",
        )
        self.select_sport_btn.pack(fill="x", pady=8)

        self.manage_scores_btn = ttk.Button(
            btn_frame,
            text="Manage Scores",
            command=lambda: self.app.show_frame("SoccerScoresScreen"),
            state="disabled",
        )
        self.manage_scores_btn.pack(fill="x", pady=8)

        # Edit home screen text small button bottom-right
        bottom = ttk.Frame(self, style="Card.TFrame")
        bottom.pack(side="bottom", fill="x", pady=(8, 8))

        edit_btn = ttk.Button(
            bottom,
            text="Edit Home Screen Text",
            command=lambda: self.app.show_frame("EditHomeTextScreen"),
        )
        edit_btn.pack(side="right")

        # Initial state
        self.update_connection_state()

    def update_connection_state(self):
        if self.app.connected:
            self.select_sport_btn.config(state="normal")
            # Manage scores only if sport set
            self.manage_scores_btn.config(
                state="normal" if self.app.sport_var.get() else "disabled"
            )
            self.connect_btn.config(text="Reconnect")
        else:
            self.select_sport_btn.config(state="disabled")
            self.manage_scores_btn.config(state="disabled")
            self.connect_btn.config(text="Connect")

        # Status colour
        self.status_label.configure(
            foreground=self.app.connection_color,
        )


class EditHomeTextScreen(ttk.Frame):
    def __init__(self, parent, app: ScoreboardApp):
        super().__init__(parent)
        self.app = app
        self.configure(style="Card.TFrame")

        # Header
        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill="x", pady=(8, 12))

        back_btn = ttk.Button(
            header,
            text="← Back",
            command=lambda: self.app.show_frame("HomeScreen"),
        )
        back_btn.pack(side="left")

        title = ttk.Label(header, text="Edit Home Screen Text", style="Title.TLabel")
        title.pack(side="left", padx=(12, 0))

        # Body
        body = ttk.Frame(self, style="Card.TFrame", padding=10)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="Banner Text:", style="Subtitle.TLabel").pack(
            anchor="w", pady=(4, 2)
        )
        entry = ttk.Entry(body, textvariable=self.app.home_banner_var, font=("Segoe UI", 16))
        entry.pack(fill="x", pady=(0, 8))

        # Color & size options for banner
        options_frame = ttk.Frame(body, style="Card.TFrame")
        options_frame.pack(fill="x", pady=8)

        ttk.Label(options_frame, text="Color:", style="Subtitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.color_var = tk.StringVar(value="1")
        color_menu = ttk.Combobox(
            options_frame,
            textvariable=self.color_var,
            values=[
                "1 Red",
                "2 Green",
                "3 Yellow",
                "4 Blue",
                "5 Purple",
                "6 Cyan",
                "7 White",
            ],
            state="readonly",
        )
        color_menu.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        color_menu.current(0)

        ttk.Label(options_frame, text="Size:", style="Subtitle.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )
        self.size_var = tk.StringVar(value="2")
        size_menu = ttk.Combobox(
            options_frame,
            textvariable=self.size_var,
            values=[
                "1 Small",
                "2 Medium",
                "3 Large",
                "4 Largest",
            ],
            state="readonly",
        )
        size_menu.grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=(4, 0))
        size_menu.current(1)

        options_frame.columnconfigure(1, weight=1)

        # Preview
        preview_frame = ttk.LabelFrame(body, text="Preview", style="Card.TFrame")
        preview_frame.pack(fill="x", pady=16)

        self.preview_label = tk.Label(
            preview_frame,
            textvariable=self.app.home_banner_var,
            font=("Segoe UI", 20, "bold"),
            bg="black",
            fg="red",
            height=3,
        )
        self.preview_label.pack(fill="x", padx=4, pady=6)

        # Update preview when text or style changes
        def update_preview(*_):
            color_code = self.color_var.get().split()[0]
            size_code = self.size_var.get().split()[0]
            # simple font scaling
            size_map = {"1": 14, "2": 18, "3": 24, "4": 30}
            color_map = {
                "1": "red",
                "2": "lime",
                "3": "yellow",
                "4": "deepskyblue",
                "5": "magenta",
                "6": "cyan",
                "7": "white",
            }
            self.preview_label.configure(
                fg=color_map.get(color_code, "red"),
                font=("Segoe UI", size_map.get(size_code, 18), "bold"),
            )

        self.app.home_banner_var.trace_add("write", update_preview)
        self.color_var.trace_add("write", update_preview)
        self.size_var.trace_add("write", update_preview)
        update_preview()

        # Buttons
        btn_frame = ttk.Frame(body, style="Card.TFrame")
        btn_frame.pack(fill="x", pady=(8, 0))

        send_btn = ttk.Button(
            btn_frame,
            text="Send to Screen",
            style="Primary.TButton",
            command=self.on_send,
        )
        send_btn.pack(fill="x")

    def on_send(self):
        if not self.app.connected:
            messagebox.showwarning(
                "Not Connected", "Connect to the controller before sending text."
            )
            return
        color_code = self.color_var.get().split()[0]
        size_code = self.size_var.get().split()[0]
        self.app.update_state(home_banner_text=self.app.home_banner_var.get())
        self.app.send_home_banner(color=color_code, size=size_code)
        messagebox.showinfo("Sent", "Home screen text updated on display.")


class SportSelectScreen(ttk.Frame):
    def __init__(self, parent, app: ScoreboardApp):
        super().__init__(parent)
        self.app = app
        self.configure(style="Card.TFrame")

        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill="x", pady=(8, 12))

        back_btn = ttk.Button(
            header,
            text="← Back",
            command=lambda: self.app.show_frame("HomeScreen"),
        )
        back_btn.pack(side="left")

        title = ttk.Label(header, text="Select Sport", style="Title.TLabel")
        title.pack(side="left", padx=(12, 0))

        body = ttk.Frame(self, style="Card.TFrame", padding=10)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="Choose which sport layout to use:", style="Subtitle.TLabel").pack(
            anchor="w", pady=(4, 12)
        )

        # Radiobuttons
        self.choice_var = tk.StringVar(value=self.app.sport_var.get())

        options = [
            ("AFL (count-up)", "AFL_UP"),
            ("AFL (count-down)", "AFL_DOWN"),
            ("Soccer", "Soccer"),
            ("Cricket", "Cricket"),
        ]

        for text, value in options:
            ttk.Radiobutton(
                body,
                text=text,
                value=value,
                variable=self.choice_var,
            ).pack(anchor="w", pady=4)

        info = ttk.Label(
            body,
            text="Currently only the Soccer score UI is implemented.\n"
                 "Other sports will reuse the same commands later.",
            style="Subtitle.TLabel",
        )
        info.pack(anchor="w", pady=(12, 0))

        btn_frame = ttk.Frame(body, style="Card.TFrame")
        btn_frame.pack(fill="x", pady=(24, 0))

        apply_btn = ttk.Button(
            btn_frame,
            text="Save Sport",
            style="Primary.TButton",
            command=self.apply_selection,
        )
        apply_btn.pack(fill="x")

    def apply_selection(self):
        new_sport = self.choice_var.get()
        self.app.update_state(sport=new_sport)
        # After selection, manage scores is allowed (for Soccer now)
        home = self.app.frames["HomeScreen"]
        home.update_connection_state()

        if self.app.connected:
            # Switch program immediately
            self.app.switch_to_sport_program()

        messagebox.showinfo("Sport Saved", f"Sport set to {new_sport}.")
        self.app.show_frame("HomeScreen")


class SoccerScoresScreen(ttk.Frame):
    def __init__(self, parent, app: ScoreboardApp):
        super().__init__(parent)
        self.app = app
        self.configure(style="Card.TFrame")

        # Header
        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill="x", pady=(8, 8))

        back_btn = ttk.Button(
            header,
            text="← Home",
            command=lambda: self.app.show_frame("HomeScreen"),
        )
        back_btn.pack(side="left")

        title = ttk.Label(header, text="Manage Scores (Soccer)", style="Title.TLabel")
        title.pack(side="left", padx=(12, 0))

        # Timer & Reset row
        top_bar = ttk.Frame(self, style="Card.TFrame")
        top_bar.pack(fill="x", pady=(4, 8))

        ttk.Label(top_bar, text="Timer 1:", style="Subtitle.TLabel").pack(side="left")
        ttk.Button(top_bar, text="Start", command=self.app.timer_start).pack(
            side="left", padx=2
        )
        ttk.Button(top_bar, text="Pause", command=self.app.timer_pause).pack(
            side="left", padx=2
        )
        ttk.Button(top_bar, text="Reset", command=self.app.timer_reset).pack(
            side="left", padx=2
        )

        ttk.Button(
            top_bar,
            text="Reset Scores",
            command=self.on_reset_scores,
        ).pack(side="right")

        # HALF section
        half_card = ttk.LabelFrame(self, text="Half", style="Card.TFrame")
        half_card.pack(fill="x", pady=(4, 8), padx=4)

        self.half_label_var = tk.StringVar()
        self.update_half_label()

        ttk.Label(
            half_card,
            textvariable=self.half_label_var,
            style="Subtitle.TLabel",
        ).pack(anchor="w", padx=6, pady=(4, 4))

        half_btn_frame = ttk.Frame(half_card, style="Card.TFrame")
        half_btn_frame.pack(fill="x", pady=(2, 4))

        self.btn_1st = ttk.Button(
            half_btn_frame,
            text="1st HALF",
            command=lambda: self.set_half(1),
        )
        self.btn_1st.pack(side="left", expand=True, fill="x", padx=(4, 2))

        self.btn_2nd = ttk.Button(
            half_btn_frame,
            text="2nd HALF",
            command=lambda: self.set_half(2),
        )
        self.btn_2nd.pack(side="left", expand=True, fill="x", padx=(2, 4))

        settings_btn = ttk.Button(
            half_card,
            text="Half Text Settings",
            command=self.open_half_settings,
        )
        settings_btn.pack(pady=(4, 4))

        # TEAMS section
        teams_card = ttk.LabelFrame(self, text="Teams & Scores", style="Card.TFrame")
        teams_card.pack(fill="both", expand=True, pady=(4, 8), padx=4)

        # Home row
        home_row = ttk.Frame(teams_card, style="Card.TFrame")
        home_row.pack(fill="x", pady=(6, 3))

        ttk.Label(home_row, text="Home:", style="Subtitle.TLabel").pack(
            side="left", padx=4
        )
        home_entry = ttk.Entry(
            home_row, textvariable=self.app.home_name_var, font=("Segoe UI", 14)
        )
        home_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        ttk.Button(
            home_row,
            text="Settings",
            command=lambda: self.open_name_settings("home"),
        ).pack(side="left", padx=(0, 4))

        ttk.Button(
            home_row,
            text="Update",
            command=self.update_names_and_send,
        ).pack(side="left")

        # Away row
        away_row = ttk.Frame(teams_card, style="Card.TFrame")
        away_row.pack(fill="x", pady=(3, 6))

        ttk.Label(away_row, text="Away:", style="Subtitle.TLabel").pack(
            side="left", padx=4
        )
        away_entry = ttk.Entry(
            away_row, textvariable=self.app.away_name_var, font=("Segoe UI", 14)
        )
        away_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        ttk.Button(
            away_row,
            text="Settings",
            command=lambda: self.open_name_settings("away"),
        ).pack(side="left", padx=(0, 4))

        ttk.Button(
            away_row,
            text="Update",
            command=self.update_names_and_send,
        ).pack(side="left")

        # Scores area
        score_frame = ttk.Frame(teams_card, style="Card.TFrame")
        score_frame.pack(fill="both", expand=True, pady=(8, 4))

        # Home score controls
        home_score_card = ttk.Frame(score_frame, style="Card.TFrame")
        home_score_card.pack(side="left", expand=True, fill="both", padx=(4, 2))

        ttk.Label(home_score_card, text="HOME", style="Subtitle.TLabel").pack(
            pady=(2, 2)
        )
        self.home_score_label = ttk.Label(
            home_score_card,
            textvariable=self.app.home_score_var,
            font=("Segoe UI", 40, "bold"),
            anchor="center",
            style="Card.TLabel",
        )
        self.home_score_label.pack(pady=(0, 4))

        home_btn_row = ttk.Frame(home_score_card, style="Card.TFrame")
        home_btn_row.pack()
        ttk.Button(
            home_btn_row,
            text="-",
            width=4,
            command=lambda: self.change_score("home", -1),
        ).pack(side="left", padx=2)
        ttk.Button(
            home_btn_row,
            text="+",
            width=4,
            command=lambda: self.change_score("home", +1),
        ).pack(side="left", padx=2)

        # Away score controls
        away_score_card = ttk.Frame(score_frame, style="Card.TFrame")
        away_score_card.pack(side="left", expand=True, fill="both", padx=(2, 4))

        ttk.Label(away_score_card, text="AWAY", style="Subtitle.TLabel").pack(
            pady=(2, 2)
        )
        self.away_score_label = ttk.Label(
            away_score_card,
            textvariable=self.app.away_score_var,
            font=("Segoe UI", 40, "bold"),
            anchor="center",
            style="Card.TLabel",
        )
        self.away_score_label.pack(pady=(0, 4))

        away_btn_row = ttk.Frame(away_score_card, style="Card.TFrame")
        away_btn_row.pack()
        ttk.Button(
            away_btn_row,
            text="-",
            width=4,
            command=lambda: self.change_score("away", -1),
        ).pack(side="left", padx=2)
        ttk.Button(
            away_btn_row,
            text="+",
            width=4,
            command=lambda: self.change_score("away", +1),
        ).pack(side="left", padx=2)

        # Bottom Half/Full/Return buttons
        bottom_bar = ttk.Frame(self, style="Card.TFrame")
        bottom_bar.pack(fill="x", pady=(4, 8))

        ttk.Button(
            bottom_bar,
            text="Half Time Screen",
            command=self.on_half_time_screen,
        ).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(
            bottom_bar,
            text="Full Time Screen",
            command=self.on_full_time_screen,
        ).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(
            bottom_bar,
            text="Return to Scores",
            command=self.app.resend_all_scores_and_names,
        ).pack(side="left", expand=True, fill="x", padx=2)

    # --- Lifecycle ---

    def on_show(self):
        """Called when this frame is raised."""
        if self.app.state["sport"] != "Soccer":
            messagebox.showinfo(
                "Sport Mismatch",
                "Currently, the Manage Scores UI is implemented for Soccer only.\n"
                "Switching sport to Soccer.",
            )
            self.app.update_state(sport="Soccer")
            home = self.app.frames["HomeScreen"]
            home.update_connection_state()

        if not self.app.connected:
            messagebox.showwarning(
                "Not Connected",
                "Connect to the controller first. Commands will be queued only locally.",
            )

        # Switch to soccer program and restore state
        if self.app.connected:
            self.app.switch_to_sport_program()

        # Restore HALF label and button styles
        self.update_half_label()
        self.update_half_button_styles()

        # Make sure labels show current names and scores
        self.app.home_name_var.set(self.app.state["home_name"])
        self.app.away_name_var.set(self.app.state["away_name"])
        self.app.home_score_var.set(self.app.state["home_score"])
        self.app.away_score_var.set(self.app.state["away_score"])

        # Send initial names/half/scores when opening page
        if self.app.connected:
            self.app.send_team_names()
            self.app.send_half_text()
            # Resend scores explicitly
            hs = self.app.state["home_score"]
            as_ = self.app.state["away_score"]
            self.app.send_command(f"*#1CNTS1,S{hs},0000")
            self.app.send_command(f"*#1CNTS2,S{as_},0000")

    # --- HALF ---

    def update_half_label(self):
        half = self.app.current_half_var.get()
        self.half_label_var.set("Currently: 1st HALF" if half == 1 else "Currently: 2nd HALF")

    def update_half_button_styles(self):
        half = self.app.current_half_var.get()
        if half == 1:
            self.btn_1st.configure(style="Primary.TButton")
            self.btn_2nd.configure(style="TButton")
        else:
            self.btn_2nd.configure(style="Primary.TButton")
            self.btn_1st.configure(style="TButton")

    def set_half(self, half):
        self.app.update_state(current_half=half)
        self.update_half_label()
        self.update_half_button_styles()
        if self.app.connected:
            self.app.send_half_text()

    def open_half_settings(self):
        """Pop-up window for HALF text colour and size."""
        win = tk.Toplevel(self)
        win.title("Half Text Settings")
        win.geometry("260x200")
        win.transient(self)
        win.grab_set()

        hs = self.app.state["half_style"].copy()
        color_var = tk.StringVar(value=hs["color"])
        size_var = tk.StringVar(value=hs["size"])

        ttk.Label(win, text="Color:", style="Subtitle.TLabel").pack(anchor="w", padx=8, pady=(8, 2))
        color_combo = ttk.Combobox(
            win,
            textvariable=color_var,
            values=[
                "1 Red",
                "2 Green",
                "3 Yellow",
                "4 Blue",
                "5 Purple",
                "6 Cyan",
                "7 White",
            ],
            state="readonly",
        )
        # Position at current color index if possible
        idx = int(hs["color"]) - 1 if hs["color"].isdigit() else 0
        if 0 <= idx < 7:
            color_combo.current(idx)
        color_combo.pack(fill="x", padx=8)

        ttk.Label(win, text="Size:", style="Subtitle.TLabel").pack(anchor="w", padx=8, pady=(8, 2))
        size_combo = ttk.Combobox(
            win,
            textvariable=size_var,
            values=[
                "1 Small",
                "2 Medium",
                "3 Large",
                "4 Largest",
            ],
            state="readonly",
        )
        s_idx = int(hs["size"]) - 1 if hs["size"].isdigit() else 1
        if 0 <= s_idx < 4:
            size_combo.current(s_idx)
        size_combo.pack(fill="x", padx=8)

        def apply():
            c = color_var.get().split()[0]
            s = size_var.get().split()[0]
            self.app.state["half_style"] = {"color": c, "size": s}
            save_state(self.app.state)
            if self.app.connected:
                self.app.send_half_text()
            win.destroy()

        ttk.Button(win, text="Apply", command=apply).pack(fill="x", padx=8, pady=12)

    # --- Names & Scores ---

    def open_name_settings(self, which):
        """Pop-up colour/size settings per team name (home/away)."""
        ns = self.app.state["name_style"][which].copy()

        win = tk.Toplevel(self)
        win.title(f"{which.capitalize()} Name Settings")
        win.geometry("260x200")
        win.transient(self)
        win.grab_set()

        color_var = tk.StringVar(value=ns["color"])
        size_var = tk.StringVar(value=ns["size"])

        ttk.Label(win, text="Color:", style="Subtitle.TLabel").pack(anchor="w", padx=8, pady=(8, 2))
        color_combo = ttk.Combobox(
            win,
            textvariable=color_var,
            values=[
                "1 Red",
                "2 Green",
                "3 Yellow",
                "4 Blue",
                "5 Purple",
                "6 Cyan",
                "7 White",
            ],
            state="readonly",
        )
        idx = int(ns["color"]) - 1 if ns["color"].isdigit() else 0
        if 0 <= idx < 7:
            color_combo.current(idx)
        color_combo.pack(fill="x", padx=8)

        ttk.Label(win, text="Size:", style="Subtitle.TLabel").pack(anchor="w", padx=8, pady=(8, 2))
        size_combo = ttk.Combobox(
            win,
            textvariable=size_var,
            values=[
                "1 Small",
                "2 Medium",
                "3 Large",
                "4 Largest",
            ],
            state="readonly",
        )
        s_idx = int(ns["size"]) - 1 if ns["size"].isdigit() else 2
        if 0 <= s_idx < 4:
            size_combo.current(s_idx)
        size_combo.pack(fill="x", padx=8)

        def apply():
            c = color_var.get().split()[0]
            s = size_var.get().split()[0]
            self.app.state["name_style"][which] = {"color": c, "size": s}
            save_state(self.app.state)
            if self.app.connected:
                self.app.send_team_names()
            win.destroy()

        ttk.Button(win, text="Apply", command=apply).pack(fill="x", padx=8, pady=12)

    def update_names_and_send(self):
        self.app.update_state(
            home_name=self.app.home_name_var.get(),
            away_name=self.app.away_name_var.get(),
        )
        if self.app.connected:
            self.app.send_team_names()

    def change_score(self, team, delta):
        self.app.apply_score_diff(team, delta)

    def on_reset_scores(self):
        if messagebox.askyesno(
            "Reset Scores",
            "Reset both scores to 0? This will also send S0 to the scoreboard.",
        ):
            self.app.reset_scores_to_zero()

    # --- Half/Full/Return buttons ---

    def on_half_time_screen(self):
        if not self.app.connected:
            messagebox.showwarning(
                "Not Connected",
                "Connect to the controller to send Half Time Screen command.",
            )
            return
        self.app.send_command("*#1PRGC30,0000")
        self.app.send_command("*#1RAMT1,1211Half Time0000")

    def on_full_time_screen(self):
        if not self.app.connected:
            messagebox.showwarning(
                "Not Connected",
                "Connect to the controller to send Full Time Screen command.",
            )
            return
        self.app.send_command("*#1PRGC30,0000")
        self.app.send_command("*#1RAMT1,1211Full Time0000")


# ----------------------------- Main entry ----------------------------- #

def main():
    app = ScoreboardApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
