#!/usr/bin/env python3
"""
Professional Scoreboard Control
Supports Soccer, AFL, Cricket and more
Controls LED displays via UDP (TF-F6 controller)
Optimized for mobile-friendly interface
"""

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont
import socket
import json
import os
from pathlib import Path

# Configuration
CONTROLLER_IP = "192.168.1.252"
CONTROLLER_PORT = 5959
CONFIG_FILE = os.path.join(Path.home(), "scoreboard_config.json")


class ScoreboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sports Scoreboard")
        
        # Make window mobile-friendly size (portrait orientation)
        self.root.geometry("400x700")
        self.root.configure(bg='#1a1a1a')
        
        # Disable window resize for consistency
        self.root.resizable(False, False)
        
        # Connection state
        self.connected = False
        self.connection_tried = False
        self.reconnect_timer = None
        
        # Sport settings
        self.current_sport = None
        self.sport_programs = {
            "AFL": "1",
            "Soccer": "2",
            "Cricket": "3",
            "Rugby": "4",
            "Hockey": "5",
            "Basketball": "6"
        }

        # Score data
        self.home_score = 0
        self.away_score = 0
        self.home_name = "HOME"
        self.away_name = "AWAY"
        self.timer_running = False

        # Python-side timer engine
        self.timer_seconds = 0        # current seconds (elapsed or remaining)
        self.timer_countdown = False  # True=countdown, False=count-up
        self.timer_target_seconds = 0 # countdown start value (for reset)
        self.timer_job = None         # root.after job ID
        self.timer_configured_for = None  # which sport last set the timer defaults

        # Shot clock (Basketball / Hockey)
        self.shot_clock_seconds = 30
        self.shot_clock_running = False
        self.shot_clock_target = 30   # reset value
        self.shot_clock_job = None

        # Basketball extras
        self.home_timeouts = 0
        self.away_timeouts = 0
        self.home_fouls = 0
        self.away_fouls = 0

        # Rugby scoring totals (calculated from try/conv/pen/drop)
        self.rugby_home_score = 0
        self.rugby_away_score = 0

        # AFL-specific score tracking
        self.home_goals = 0
        self.home_points = 0
        self.away_goals = 0
        self.away_points = 0

        # Text settings for different areas
        self.team_settings = {"color": "1", "size": "2", "h_align": "1", "v_align": "2"}  # RAMT1 — default M, Mid
        self.home_screen_settings = {"color": "7", "size": "2"}  # RAMT1 for home screen

        # AFL team name display style
        self.afl_team_color   = '1'
        self.afl_team_size    = '2'   # default M
        self.afl_team_h_align = '3'
        self.afl_team_v_align = '2'   # default Mid

        # Cricket team name display style
        self.cricket_team_color   = '1'
        self.cricket_team_size    = '2'   # default M
        self.cricket_team_h_align = '3'
        self.cricket_team_v_align = '2'   # default Mid
        
        # Debounce timers for live updates
        self.home_update_timer = None
        self.away_update_timer = None
        self.home_score_update_timer = None
        self.away_score_update_timer = None
        
        # Command queue system for 100ms delay between commands
        self.command_queue = []
        self.processing_queue = False
        
        # Scrolling text support
        self.scroll_active = False
        self.scroll_timer = None
        self.scroll_text = ""
        self.scroll_position = 0

        # Snake scroll support
        self.snake_active = False
        self.snake_timer = None

        # Single-row scroll support
        self.single_scroll_active = False
        self.single_scroll_timer = None
        self.single_scroll_rows = []

        # Timer display settings (RAMT5=mins, RAMT6=:tens, RAMT7=units)
        self.timer_color          = '7'   # white
        self.timer_size           = '2'   # medium (default)
        self.timer_h_align        = '3'   # left (always left)
        self.timer_v_align        = '1'   # top
        self.timer_offset_afl     = 1     # leading spaces for AFL timer (default 1)
        self.timer_offset_default = 0     # leading spaces for all other sports (default 0)

        # Shot clock display settings (RAMT8=full value — Basketball/Hockey)
        self.shot_clock_color   = '7'
        self.shot_clock_size    = '2'   # medium (default)
        self.shot_clock_h_align = '3'   # left
        self.shot_clock_v_align = '1'

        # AFL quarter settings (RAMT8)
        self.afl_quarter       = 1
        self.afl_quarter_color   = '7'
        self.afl_quarter_size    = '2'   # medium (default)
        self.afl_quarter_h_align = '3'   # left
        self.afl_quarter_v_align = '1'
        
        # Advertisement management
        self.advertisements = []  # List of saved advertisements
        self.current_ad_index = 0  # Currently selected advertisement
        # Persisted per-ad selection state: {ad_name: {'selected': bool, 'duration': '4'}}
        self.ad_selections = {}

        # Ad loop (plays a playlist of ads in rotation)
        self.ad_loop_active   = False
        self.ad_loop_job      = None
        self.ad_loop_playlist = []   # list of (ad_dict, duration_ms)
        self.ad_loop_idx      = 0

        # Bypass connection mode (persists across screen navigation)
        self.bypass_connection = tk.BooleanVar(value=False)

        # Display dimensions - configured on first run
        self.display_width = None
        self.display_height = None
        
        # Load saved config
        self.load_config()
        
        # Save session on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Check if display is configured - if not, show setup
        if self.display_width is None or self.display_height is None:
            self.show_display_setup()
        else:
            # Create UI
            self.create_home_screen()

            # Auto-connect on startup
            self.root.after(100, self.start_auto_reconnect)
    
    def on_close(self):
        """Save config then exit cleanly"""
        self.save_config()
        self.root.destroy()

    def send_udp_command(self, command):
        """Add command to queue for sending with 100ms delay"""
        self.command_queue.append(command)
        if not self.processing_queue:
            self.process_command_queue()
        return True
    
    def process_command_queue(self):
        """Process command queue with 120ms delay between commands"""
        if not self.command_queue:
            self.processing_queue = False
            return
        
        self.processing_queue = True
        command = self.command_queue.pop(0)
        
        # Send the command
        self._send_udp_now(command)
        
        # Schedule next command after 120ms
        self.root.after(120, self.process_command_queue)
    
    def _send_udp_now(self, command):
        """Actually send UDP command to controller (internal use only)"""
        if not self.connected:
            return False

        # Bypass mode: log what would be sent without touching network
        if self.bypass_connection.get():
            print(f"[BYPASS] Would send: {command}")
            return True

        try:
            data = command.encode("ascii")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            sock.sendto(data, (CONTROLLER_IP, CONTROLLER_PORT))
            sock.close()
            print(f"[SENT] {command}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send: {e}")
            return False
    
    def start_auto_reconnect(self):
        """Start continuous auto-reconnect attempts"""
        self.auto_reconnect()
        # Health check disabled - was interfering with game display
    
    def auto_reconnect(self):
        """Try to reconnect every 2 seconds if not connected"""
        if not self.connected and not self.bypass_connection.get():
            print("[INFO] Auto-reconnect: Testing connection...")
            self.test_connection()

        # Schedule next reconnection attempt (every 2 seconds to avoid spam)
        self.reconnect_timer = self.root.after(2000, self.auto_reconnect)
    
    def connection_health_check(self):
        """Disabled - health check was interfering with game commands"""
        # Only test connection when user returns to home screen or clicks Connect
        # Automatic background checking was sending commands that blanked the display
        pass
    
    def test_connection(self):
        """Test connection to controller - requires actual response/handshake"""
        try:
            # Create a socket for UDP communication
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)  # 1 second timeout for response
            
            # Send a simple PRGC command that controller should acknowledge
            # Using program 0 query - should return status code
            test_cmd = "*#1PRGC30,0000"
            
            print(f"[CONN] Sending handshake to {CONTROLLER_IP}:{CONTROLLER_PORT}...")
            print(f"[CONN] Command: {test_cmd}")
            sock.sendto(test_cmd.encode("ascii"), (CONTROLLER_IP, CONTROLLER_PORT))
            
            # Wait for response (return code: 00=success, 04/05/06/0A=errors)
            try:
                data, addr = sock.recvfrom(1024)
                
                # Verify response came from correct IP and port
                if addr[0] == CONTROLLER_IP and addr[1] == CONTROLLER_PORT:
                    response = data.decode('ascii', errors='ignore')
                    print(f"[CONN] ✓ Response received from {addr[0]}:{addr[1]}")
                    print(f"[CONN] Response: {response[:100]}")
                    
                    # Connection verified - controller responded
                    self.connected = True
                    if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                        try:
                            self.status_label.config(text=f"● Connected to {CONTROLLER_IP}", fg='#00ff00', bg='#2a2a2a')
                        except:
                            pass
                    if hasattr(self, 'connect_btn') and self.connect_btn.winfo_exists():
                        try:
                            self.connect_btn.config(state='disabled')
                        except:
                            pass
                    self.enable_sport_buttons()
                    print(f"[INFO] ✓✓✓ Connection VERIFIED - Controller is responding!")
                else:
                    raise Exception(f"Response from wrong address: {addr} (expected {CONTROLLER_IP}:{CONTROLLER_PORT})")
                    
            except socket.timeout:
                raise Exception(f"Controller not responding - no reply after 1 second (is controller at {CONTROLLER_IP}:{CONTROLLER_PORT}?)")
            
            sock.close()
            
        except Exception as e:
            # Don't update connection state or print errors if bypass is active
            if self.bypass_connection.get():
                return
            self.connected = False
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                try:
                    self.status_label.config(text=f"● Disconnected", fg='#ff3333', bg='#2a2a2a')
                except:
                    pass  # Widget was destroyed, ignore
            if hasattr(self, 'connect_btn') and self.connect_btn.winfo_exists():
                try:
                    self.connect_btn.config(state='normal')
                except:
                    pass
            if hasattr(self, 'select_sport_btn') and self.select_sport_btn.winfo_exists():
                try:
                    self.select_sport_btn.config(bg='#555555', state='disabled')
                except:
                    pass
            if hasattr(self, 'manage_scores_btn') and self.manage_scores_btn.winfo_exists():
                try:
                    self.manage_scores_btn.config(bg='#555555', state='disabled')
                except:
                    pass
            print(f"[ERROR] ✗✗✗ Connection FAILED: {e}")
    
    def create_home_screen(self):
        """Create main home screen"""
        # Clear any existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Send blank screen and set to page 0 (menu screen)
        self.stop_scrolling_text()
        self.send_udp_command("*#1PRGC30,0000")
        self.root.after(120, lambda: self.send_udp_command("*#1RAMT1,1211 0000"))  # Blank text
        
        # Main container
        main_frame = tk.Frame(self.root, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title with professional styling
        title_frame = tk.Frame(main_frame, bg='#1a1a1a')
        title_frame.pack(fill='x', pady=(20, 5))
        
        title = tk.Label(title_frame, text="Scoreboard Control", 
                        font=('Helvetica', 26, 'bold'),
                        bg='#1a1a1a', fg='#00aaff')
        title.pack(side='left', expand=True)
        
        # Subtitle
        subtitle = tk.Label(main_frame, text="Professional LED Display Management", 
                           font=('Helvetica', 10),
                           bg='#1a1a1a', fg='#888888')
        subtitle.pack(pady=(0, 15))
        
        # Status indicator with frame border
        status_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='solid', bd=1)
        status_frame.pack(pady=(0, 5), padx=50)
        
        self.status_label = tk.Label(status_frame, text="● Testing connection...", 
                                     font=('Helvetica', 11, 'bold'),
                                     bg='#2a2a2a', fg='#ffaa00', padx=20, pady=8)
        self.status_label.pack()
        
        # Show selected sport
        if self.current_sport:
            sport_label = tk.Label(main_frame, text=f"Sport: {self.current_sport}",
                                  font=('Helvetica', 14),
                                  bg='#1a1a1a', fg='#00aaff')
            sport_label.pack(pady=(0, 20))
        else:
            sport_label = tk.Label(main_frame, text="No sport selected",
                                  font=('Helvetica', 14),
                                  bg='#1a1a1a', fg='#888888')
            sport_label.pack(pady=(0, 20))
        
        # Connect button with polished styling
        self.connect_btn = tk.Button(main_frame, text="🔌 Connect to Controller",
                                     font=('Helvetica', 16, 'bold'),
                                     bg='#00aa00', fg='white',
                                     activebackground='#00dd00',
                                     activeforeground='white',
                                     relief='flat', bd=0,
                                     padx=40, pady=15,
                                     cursor='hand2',
                                     state='disabled',
                                     command=self.test_connection)
        self.connect_btn.pack(pady=(15, 10), fill='x', padx=20)
        
        # Select Sport button
        self.select_sport_btn = tk.Button(main_frame, text="🏆 Select Sport",
                                         font=('Helvetica', 16, 'bold'),
                                         bg='#555555', fg='white',
                                         activebackground='#0088ff',
                                         activeforeground='white',
                                         relief='flat', bd=0,
                                         padx=40, pady=15,
                                         cursor='hand2',
                                         state='disabled',
                                         command=self.show_sport_selection)
        self.select_sport_btn.pack(pady=10, fill='x', padx=20)
        
        # Manage Scores button
        self.manage_scores_btn = tk.Button(main_frame, text="⚽ Manage Scores",
                                          font=('Helvetica', 16, 'bold'),
                                          bg='#555555', fg='white',
                                          activebackground='#ff8800',
                                          activeforeground='white',
                                          relief='flat', bd=0,
                                          padx=40, pady=15,
                                          cursor='hand2',
                                          state='disabled',
                                          command=self.show_manage_scores)
        self.manage_scores_btn.pack(pady=10, fill='x', padx=20)
        
        # Spacer
        tk.Frame(main_frame, bg='#1a1a1a', height=50).pack(fill='x')
        
        # Edit Home Screen Text button (bottom right) - polished
        edit_btn = tk.Button(main_frame, text="✏️ Edit\nScreen Text",
                            font=('Helvetica', 10, 'bold'),
                            bg='#444444', fg='white',
                            activebackground='#666666',
                            activeforeground='white',
                            relief='flat', bd=0,
                            padx=15, pady=10,
                            cursor='hand2',
                            command=self.show_edit_home_text)
        edit_btn.pack(side='right', anchor='se', padx=10, pady=10)
        
        # Bypass connection toggle (bottom left)
        bypass_check = tk.Checkbutton(main_frame, text="Bypass Connection",
                                      variable=self.bypass_connection,
                                      font=('Helvetica', 9),
                                      bg='#1a1a1a', fg='#888888',
                                      selectcolor='#333333',
                                      activebackground='#1a1a1a',
                                      activeforeground='#ffaa00',
                                      command=self.toggle_bypass)
        bypass_check.pack(side='left', anchor='sw', padx=10, pady=10)

        # Reset all settings button (bottom centre)
        tk.Button(main_frame, text="⚠ Reset Settings",
                  font=('Helvetica', 9), bg='#3a1a1a', fg='#cc4444',
                  activebackground='#551111', activeforeground='#ff6666',
                  relief='flat', padx=8, pady=4,
                  command=self.reset_to_defaults).pack(side='bottom', pady=(0, 12))
        
        # Professional footer
        footer_frame = tk.Frame(main_frame, bg='#1a1a1a')
        footer_frame.pack(side='bottom', fill='x', pady=(20, 0))
        
        footer_text = tk.Label(footer_frame, 
                              text=f"Controller: {CONTROLLER_IP}:{CONTROLLER_PORT} • v1.0",
                              font=('Helvetica', 8),
                              bg='#1a1a1a', fg='#666666')
        footer_text.pack()
        
        # If bypass is already active, enable buttons immediately without a network test
        if self.bypass_connection.get():
            self.connected = True
            self.status_label.config(text="● Bypass Mode (No Connection)", fg='#ffaa00', bg='#2a2a2a')
            self.connect_btn.config(state='disabled')
            self.enable_sport_buttons()
        else:
            # Auto-attempt connection when returning to home screen
            self.root.after(100, self.test_connection)
    
    def toggle_bypass(self):
        """Toggle bypass connection mode"""
        if self.bypass_connection.get():
            # Bypass enabled - unlock everything immediately
            self.connected = True
            if hasattr(self, 'status_label'):
                self.status_label.config(text="● Bypass Mode (No Connection)", fg='#ffaa00', bg='#2a2a2a')
            self.connect_btn.config(state='disabled')
            self.enable_sport_buttons()
            print("[INFO] Bypass mode enabled")
        else:
            # Bypass disabled - reset to disconnected state and test real connection
            self.connected = False
            self.select_sport_btn.config(bg='#555555', state='disabled')
            self.manage_scores_btn.config(bg='#555555', state='disabled')
            self.connect_btn.config(state='normal')
            self.status_label.config(text="● Testing connection...", fg='#ffaa00', bg='#2a2a2a')
            print("[INFO] Bypass mode disabled - testing real connection")
            self.test_connection()
    
    def enable_sport_buttons(self):
        """Enable sport selection and manage scores buttons when connected"""
        self.select_sport_btn.config(bg='#0066cc', state='normal')
        if self.current_sport:
            self.manage_scores_btn.config(bg='#ff6600', state='normal')
    
    def show_sport_selection(self):
        """Show sport selection screen"""
        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        main_frame = tk.Frame(self.root, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Top bar with back button
        top_bar = tk.Frame(main_frame, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 10))
        
        tk.Button(top_bar, text="← Controller", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 activebackground='#555555', activeforeground='white',
                 command=self.create_home_screen).pack(side='left', anchor='w')
        
        # Title
        title = tk.Label(main_frame, text="Select Sport",
                        font=('Helvetica', 28, 'bold'),
                        bg='#1a1a1a', fg='white')
        title.pack(pady=(0, 30))
        
        # Sport buttons
        for sport_name in self.sport_programs.keys():
            btn = tk.Button(main_frame, text=sport_name,
                          font=('Helvetica', 18, 'bold'),
                          bg='#0066cc', fg='white',
                          activebackground='#0088ee',
                          activeforeground='white',
                          relief='flat', bd=0,
                          padx=40, pady=20,
                          command=lambda s=sport_name: self.select_sport(s))
            btn.pack(pady=10, fill='x')
    
    def select_sport(self, sport_name):
        """Select a sport and save it"""
        self.current_sport = sport_name
        self.save_config()
        
        # Enable manage scores button
        self.create_home_screen()
        
        # Show confirmation
        messagebox.showinfo("Sport Selected", f"{sport_name} selected!")
    
    def show_manage_scores(self):
        """Show score management screen"""
        if not self.current_sport:
            messagebox.showwarning("No Sport", "Please select a sport first!")
            return
        
        # Stop any scrolling text
        self.stop_scrolling_text()
        
        # Send program change command based on sport
        program_num = self.sport_programs[self.current_sport]
        self.send_udp_command(f"*#1PRGC3{program_num},0000")
        
        # Initialize scores
        self.send_udp_command(f"*#1CNTS1,S{self.home_score},0000")
        self.send_udp_command(f"*#1CNTS2,S{self.away_score},0000")
        
        # Show appropriate UI
        if self.current_sport == "Soccer":
            self.show_soccer_ui()
        elif self.current_sport == "AFL":
            self.show_afl_ui()
        elif self.current_sport == "Cricket":
            self.show_cricket_ui()
        elif self.current_sport in ["Rugby", "Hockey", "Basketball"]:
            self.show_simple_sport_ui()
        else:
            self.show_coming_soon()
    
    def show_soccer_ui(self):
        """Show soccer score management UI"""
        self.root.geometry("520x700")
        # Soccer default: count-up from 0
        if self.timer_configured_for != 'Soccer' and not self.timer_running:
            self.timer_countdown = False
            self.timer_target_seconds = 0
            self.timer_seconds = 0
            self.timer_configured_for = 'Soccer'
        # Stop any scrolling text immediately
        self.stop_scrolling_text()

        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Main container with scrollbar for mobile
        canvas = tk.Canvas(self.root, bg='#1a1a1a', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#1a1a1a')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        main_frame = tk.Frame(scrollable_frame, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Top bar with back button and title
        top_bar = tk.Frame(main_frame, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 15))
        
        # Back to controller button (top left)
        tk.Button(top_bar, text="← Controller", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 activebackground='#555555', activeforeground='white',
                 command=self.back_to_home).pack(side='left', anchor='w')
        
        # Title (centered)
        title = tk.Label(top_bar, text="Soccer Match",
                        font=('Helvetica', 24, 'bold'),
                        bg='#1a1a1a', fg='white')
        title.pack(side='left', expand=True)
        
        # Team names
        team_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        team_frame.pack(fill='x', pady=(0, 15), padx=5, ipady=10)

        team_header = tk.Frame(team_frame, bg='#2a2a2a')
        team_header.pack(fill='x', padx=10, pady=5)

        tk.Label(team_header, text="Team Names", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left')

        tk.Button(team_header, text="⚙", font=('Helvetica', 10), bg='#555555', fg='white',
                 relief='flat', padx=8, pady=2, command=self.show_team_name_settings).pack(side='right')

        # Home team
        home_team_frame = tk.Frame(team_frame, bg='#2a2a2a')
        home_team_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(home_team_frame, text="Home:", font=('Helvetica', 11),
                bg='#2a2a2a', fg='white', width=6, anchor='w').pack(side='left')

        self.home_name_entry = tk.Entry(home_team_frame, font=('Helvetica', 14), bg='#333333',
                                        fg='white', relief='flat', insertbackground='white')
        self.home_name_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.home_name_entry.insert(0, self.home_name)
        self.home_name_entry.bind('<KeyRelease>', lambda e: self.update_team_name_live('home'))
        self.home_name_entry.bind('<FocusOut>', lambda e: self.update_team_name('home'))

        # Timer controls
        timer_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        timer_frame.pack(fill='x', pady=(0, 15), padx=5, ipady=10)

        timer_header = tk.Frame(timer_frame, bg='#2a2a2a')
        timer_header.pack(fill='x', padx=10, pady=(5, 0))
        tk.Label(timer_header, text="Timer", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left')
        tk.Button(timer_header, text="⚙", font=('Helvetica', 10), bg='#555555', fg='white',
                 relief='flat', padx=8, pady=2, command=self.show_timer_settings).pack(side='right')



        self.timer_display_label = tk.Label(timer_frame,
                text=f"{self.timer_seconds//60:02d}:{self.timer_seconds%60:02d}",
                font=('Helvetica', 28, 'bold'), bg='#2a2a2a', fg='#00ff00')
        self.timer_display_label.pack(pady=(2, 5))

        timer_btns = tk.Frame(timer_frame, bg='#2a2a2a')
        timer_btns.pack(pady=(0, 5))
        tk.Button(timer_btns, text="▶ Start", font=('Helvetica', 12), bg='#00aa00', fg='white',
                 relief='flat', padx=15, pady=8, command=self.start_timer).pack(side='left', padx=5)
        tk.Button(timer_btns, text="⏸ Pause", font=('Helvetica', 12), bg='#ffaa00', fg='white',
                 relief='flat', padx=15, pady=8, command=self.pause_timer).pack(side='left', padx=5)
        tk.Button(timer_btns, text="↻ Reset", font=('Helvetica', 12), bg='#ff3333', fg='white',
                 relief='flat', padx=15, pady=8, command=self.reset_timer).pack(side='left', padx=5)

        # Away team
        away_team_frame = tk.Frame(team_frame, bg='#2a2a2a')
        away_team_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(away_team_frame, text="Away:", font=('Helvetica', 11),
                bg='#2a2a2a', fg='white', width=6, anchor='w').pack(side='left')
        
        self.away_name_entry = tk.Entry(away_team_frame, font=('Helvetica', 14), bg='#333333',
                                        fg='white', relief='flat', insertbackground='white')
        self.away_name_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.away_name_entry.insert(0, self.away_name)
        self.away_name_entry.bind('<KeyRelease>', lambda e: self.update_team_name_live('away'))
        self.away_name_entry.bind('<FocusOut>', lambda e: self.update_team_name('away'))
        
        # Scores
        score_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        score_frame.pack(fill='x', pady=(0, 15), padx=5, ipady=15)
        
        score_header = tk.Frame(score_frame, bg='#2a2a2a')
        score_header.pack(fill='x', padx=10, pady=(5, 0))
        
        tk.Label(score_header, text="SCORES", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left')
        
        # Reset scores icon button
        tk.Button(score_header, text="↻", font=('Helvetica', 14, 'bold'), 
                 bg='#ff3333', fg='white', relief='flat', width=3, 
                 command=self.reset_scores).pack(side='right')
        
        # Home score
        home_score_frame = tk.Frame(score_frame, bg='#2a2a2a')
        home_score_frame.pack(pady=10)

        self.score_home_name_lbl = tk.Label(home_score_frame, text=self.home_name[:8], font=('Helvetica', 11),
                bg='#2a2a2a', fg='#00ff00', width=8)
        self.score_home_name_lbl.pack(side='left', padx=5)

        tk.Button(home_score_frame, text="−", font=('Helvetica', 20, 'bold'), bg='#ff3333', fg='white',
                 relief='flat', width=3, command=lambda: self.adjust_score('home', -1)).pack(side='left', padx=5)

        self.home_score_entry = tk.Entry(home_score_frame, font=('Helvetica', 32, 'bold'),
                                         bg='#1a1a1a', fg='white', width=4, relief='sunken', bd=2,
                                         justify='center', insertbackground='white')
        self.home_score_entry.pack(side='left', padx=10)
        self.home_score_entry.insert(0, str(self.home_score))
        self.home_score_entry.bind('<KeyRelease>', lambda e: self.update_score_live('home'))
        self.home_score_entry.bind('<FocusOut>', lambda e: self.validate_score('home'))

        tk.Button(home_score_frame, text="+", font=('Helvetica', 20, 'bold'), bg='#00aa00', fg='white',
                 relief='flat', width=3, command=lambda: self.adjust_score('home', 1)).pack(side='left', padx=5)

        # Away score
        away_score_frame = tk.Frame(score_frame, bg='#2a2a2a')
        away_score_frame.pack(pady=10)

        self.score_away_name_lbl = tk.Label(away_score_frame, text=self.away_name[:8], font=('Helvetica', 11),
                bg='#2a2a2a', fg='#ffaa00', width=8)
        self.score_away_name_lbl.pack(side='left', padx=5)

        tk.Button(away_score_frame, text="−", font=('Helvetica', 20, 'bold'), bg='#ff3333', fg='white',
                 relief='flat', width=3, command=lambda: self.adjust_score('away', -1)).pack(side='left', padx=5)

        self.away_score_entry = tk.Entry(away_score_frame, font=('Helvetica', 32, 'bold'),
                                         bg='#1a1a1a', fg='white', width=4, relief='sunken', bd=2,
                                         justify='center', insertbackground='white')
        self.away_score_entry.pack(side='left', padx=10)
        self.away_score_entry.insert(0, str(self.away_score))
        self.away_score_entry.bind('<KeyRelease>', lambda e: self.update_score_live('away'))
        self.away_score_entry.bind('<FocusOut>', lambda e: self.validate_score('away'))

        tk.Button(away_score_frame, text="+", font=('Helvetica', 20, 'bold'), bg='#00aa00', fg='white',
                 relief='flat', width=3, command=lambda: self.adjust_score('away', 1)).pack(side='left', padx=5)

        # Advertisements section
        ads_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        ads_frame.pack(fill='x', pady=(15, 5), padx=5)
        self._build_ads_panel(ads_frame, self.return_to_scores)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Send program and refresh all data on screen
        program_num = self.sport_programs.get(self.current_sport, 3)
        self.send_udp_command(f"*#1PRGC3{program_num},0000")
        
        # Resend all current data after a brief delay
        self.root.after(150, self.resend_all_data)
    
    # AFL-specific functions and UI
    def show_afl_ui(self):
        """Show AFL score management UI"""
        self.root.geometry("520x700")
        # Set default timer for AFL: 20 min countdown when entering this sport
        if self.timer_configured_for != 'AFL' and not self.timer_running:
            self.timer_countdown = True
            self.timer_target_seconds = 20 * 60
            self.timer_seconds = 20 * 60
            self.timer_configured_for = 'AFL'
        # Initialize AFL-specific scores if not exists
        if not hasattr(self, 'afl_home_goals'):
            self.afl_home_goals = 0
            self.afl_home_points = 0
            self.afl_away_goals = 0
            self.afl_away_points = 0
        # Stop any scrolling text
        self.stop_scrolling_text()
        
        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Main container with scrollbar
        canvas = tk.Canvas(self.root, bg='#1a1a1a', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#1a1a1a')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        main_frame = tk.Frame(scrollable_frame, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Top bar
        top_bar = tk.Frame(main_frame, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 15))
        
        tk.Button(top_bar, text="← Controller", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 command=self.back_to_home).pack(side='left')
        
        title = tk.Label(top_bar, text="AFL Match",
                        font=('Helvetica', 24, 'bold'),
                        bg='#1a1a1a', fg='white')
        title.pack(side='left', expand=True)
        
        # Team names
        team_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        team_frame.pack(fill='x', pady=(0, 15), padx=5, ipady=10)

        team_header = tk.Frame(team_frame, bg='#2a2a2a')
        team_header.pack(fill='x', padx=10, pady=5)

        tk.Label(team_header, text="Team Names", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left')

        tk.Button(team_header, text="⚙", font=('Helvetica', 11),
                 bg='#444444', fg='white', relief='flat', width=3,
                 command=self.show_afl_team_settings).pack(side='right')

        # HOME team name
        home_team_frame = tk.Frame(team_frame, bg='#2a2a2a')
        home_team_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(home_team_frame, text="Home:", font=('Helvetica', 11),
                bg='#2a2a2a', fg='white', width=6, anchor='w').pack(side='left')

        self.afl_home_name_entry = tk.Entry(home_team_frame, font=('Helvetica', 14),
                                            bg='#333333', fg='white', relief='flat',
                                            insertbackground='white')
        self.afl_home_name_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.afl_home_name_entry.insert(0, getattr(self, 'afl_home_name', 'HOME'))
        self.afl_home_name_entry.bind('<KeyRelease>', lambda e: self.update_afl_team_name('home'))

        # AWAY team name
        away_team_frame = tk.Frame(team_frame, bg='#2a2a2a')
        away_team_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(away_team_frame, text="Away:", font=('Helvetica', 11),
                bg='#2a2a2a', fg='white', width=6, anchor='w').pack(side='left')

        self.afl_away_name_entry = tk.Entry(away_team_frame, font=('Helvetica', 14),
                                            bg='#333333', fg='white', relief='flat',
                                            insertbackground='white')
        self.afl_away_name_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.afl_away_name_entry.insert(0, getattr(self, 'afl_away_name', 'AWAY'))
        self.afl_away_name_entry.bind('<KeyRelease>', lambda e: self.update_afl_team_name('away'))

        # Timer controls
        timer_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        timer_frame.pack(fill='x', pady=(0, 15), padx=5, ipady=10)

        timer_header = tk.Frame(timer_frame, bg='#2a2a2a')
        timer_header.pack(fill='x', padx=10, pady=(5, 0))
        tk.Label(timer_header, text="Timer", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left')
        tk.Button(timer_header, text="⚙", font=('Helvetica', 10), bg='#555555', fg='white',
                 relief='flat', padx=8, pady=2, command=self.show_timer_settings).pack(side='right')



        self.timer_display_label = tk.Label(timer_frame,
                text=f"{self.timer_seconds//60:02d}:{self.timer_seconds%60:02d}",
                font=('Helvetica', 28, 'bold'), bg='#2a2a2a', fg='#00ff00')
        self.timer_display_label.pack(pady=(2, 5))

        timer_btns = tk.Frame(timer_frame, bg='#2a2a2a')
        timer_btns.pack(pady=(0, 5))
        tk.Button(timer_btns, text="▶ Start", font=('Helvetica', 13, 'bold'),
                 bg='#00aa00', fg='white', relief='flat', padx=20, pady=10,
                 command=self.start_timer).pack(side='left', padx=5)
        tk.Button(timer_btns, text="⏸ Pause", font=('Helvetica', 13, 'bold'),
                 bg='#ffaa00', fg='white', relief='flat', padx=20, pady=10,
                 command=self.pause_timer).pack(side='left', padx=5)
        tk.Button(timer_btns, text="↻ Reset", font=('Helvetica', 13, 'bold'),
                 bg='#cc0000', fg='white', relief='flat', padx=20, pady=10,
                 command=self.reset_timer).pack(side='left', padx=5)

        # ── Quarter selector (RAMT8 for AFL) ──────────────────────────────────
        quarter_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        quarter_frame.pack(fill='x', pady=(0, 10), padx=5, ipady=6)

        quarter_header = tk.Frame(quarter_frame, bg='#2a2a2a')
        quarter_header.pack(fill='x', padx=10, pady=(5, 0))
        tk.Label(quarter_header, text="Quarter", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left')
        tk.Button(quarter_header, text="⚙", font=('Helvetica', 10), bg='#555555', fg='white',
                 relief='flat', padx=8, pady=2,
                 command=self.show_afl_quarter_settings).pack(side='right')

        self.afl_quarter_label = tk.Label(quarter_frame,
                text=f"Q{getattr(self, 'afl_quarter', 1)}",
                font=('Helvetica', 28, 'bold'), bg='#2a2a2a', fg='#ffcc00')
        self.afl_quarter_label.pack(pady=(3, 2))

        q_var = tk.IntVar(value=getattr(self, 'afl_quarter', 1))

        def set_quarter(q):
            self.afl_quarter = q
            q_var.set(q)
            self._send_afl_quarter()
            self.save_config()

        q_btns = tk.Frame(quarter_frame, bg='#2a2a2a')
        q_btns.pack(pady=(0, 5))
        # Off button (value 0 = blank RAMT8)
        tk.Radiobutton(q_btns, text="Off", variable=q_var, value=0,
                      font=('Helvetica', 13, 'bold'), bg='#2a2a2a', fg='#888888',
                      selectcolor='#330000', indicatoron=False,
                      relief='flat', width=5, pady=6,
                      command=lambda: set_quarter(0)).pack(side='left', padx=3)
        for _q in range(1, 5):
            tk.Radiobutton(q_btns, text=f"Q{_q}", variable=q_var, value=_q,
                          font=('Helvetica', 13, 'bold'), bg='#2a2a2a', fg='white',
                          selectcolor='#0055cc', indicatoron=False,
                          relief='flat', width=5, pady=6,
                          command=lambda __q=_q: set_quarter(__q)).pack(side='left', padx=3)

        # HOME TEAM SCORES
        home_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        home_frame.pack(fill='x', pady=(0, 10), padx=5, ipady=10)
        
        home_header = tk.Frame(home_frame, bg='#2a2a2a')
        home_header.pack(fill='x', padx=10, pady=(5, 0))
        
        self.afl_score_home_lbl = tk.Label(home_header, text=f"{self.home_name[:8]}", font=('Helvetica', 13, 'bold'),
                bg='#2a2a2a', fg='#00aaff')
        self.afl_score_home_lbl.pack(side='left')
        
        tk.Button(home_header, text="↻", font=('Helvetica', 12),
                 bg='#cc0000', fg='white', relief='flat', width=3,
                 command=lambda: self.reset_afl_scores('home')).pack(side='right', padx=2)
        
        # HOME Goals
        home_goals_frame = tk.Frame(home_frame, bg='#2a2a2a')
        home_goals_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(home_goals_frame, text="Goals:", font=('Helvetica', 11, 'bold'),
                bg='#2a2a2a', fg='white', width=8, anchor='w').pack(side='left')
        
        tk.Button(home_goals_frame, text="−", font=('Helvetica', 16, 'bold'),
                 bg='#cc0000', fg='white', width=3, relief='flat',
                 command=lambda: self.adjust_afl_score('home', 'goals', -1)).pack(side='left', padx=2)
        
        self.afl_home_goals_entry = tk.Entry(home_goals_frame, font=('Helvetica', 14),
                                             bg='#333333', fg='white', width=6,
                                             relief='flat', insertbackground='white',
                                             justify='center')
        self.afl_home_goals_entry.pack(side='left', padx=5)
        self.afl_home_goals_entry.insert(0, str(self.afl_home_goals))
        self.afl_home_goals_entry.bind('<KeyRelease>', lambda e: self.manual_afl_score('home', 'goals'))
        
        tk.Button(home_goals_frame, text="+", font=('Helvetica', 16, 'bold'),
                 bg='#00aa00', fg='white', width=3, relief='flat',
                 command=lambda: self.adjust_afl_score('home', 'goals', 1)).pack(side='left', padx=2)
        
        # HOME Points
        home_points_frame = tk.Frame(home_frame, bg='#2a2a2a')
        home_points_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(home_points_frame, text="Points:", font=('Helvetica', 11, 'bold'),
                bg='#2a2a2a', fg='white', width=8, anchor='w').pack(side='left')
        
        tk.Button(home_points_frame, text="−", font=('Helvetica', 16, 'bold'),
                 bg='#cc0000', fg='white', width=3, relief='flat',
                 command=lambda: self.adjust_afl_score('home', 'points', -1)).pack(side='left', padx=2)
        
        self.afl_home_points_entry = tk.Entry(home_points_frame, font=('Helvetica', 14),
                                              bg='#333333', fg='white', width=6,
                                              relief='flat', insertbackground='white',
                                              justify='center')
        self.afl_home_points_entry.pack(side='left', padx=5)
        self.afl_home_points_entry.insert(0, str(self.afl_home_points))
        self.afl_home_points_entry.bind('<KeyRelease>', lambda e: self.manual_afl_score('home', 'points'))
        
        tk.Button(home_points_frame, text="+", font=('Helvetica', 16, 'bold'),
                 bg='#00aa00', fg='white', width=3, relief='flat',
                 command=lambda: self.adjust_afl_score('home', 'points', 1)).pack(side='left', padx=2)
        
        # HOME Total (read-only)
        home_total_frame = tk.Frame(home_frame, bg='#2a2a2a')
        home_total_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(home_total_frame, text="TOTAL:", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='#ffaa00', width=8, anchor='w').pack(side='left')
        
        self.afl_home_total_label = tk.Label(home_total_frame, text="0",
                                             font=('Helvetica', 18, 'bold'),
                                             bg='#333333', fg='#00ff00',
                                             width=6, relief='sunken', bd=2)
        self.afl_home_total_label.pack(side='left', padx=5)
        
        # AWAY TEAM SCORES
        away_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        away_frame.pack(fill='x', pady=(0, 10), padx=5, ipady=10)
        
        away_header = tk.Frame(away_frame, bg='#2a2a2a')
        away_header.pack(fill='x', padx=10, pady=(5, 0))
        
        self.afl_score_away_lbl = tk.Label(away_header, text=f"{self.away_name[:8]}", font=('Helvetica', 13, 'bold'),
                bg='#2a2a2a', fg='#ff6600')
        self.afl_score_away_lbl.pack(side='left')
        
        tk.Button(away_header, text="↻", font=('Helvetica', 12),
                 bg='#cc0000', fg='white', relief='flat', width=3,
                 command=lambda: self.reset_afl_scores('away')).pack(side='right', padx=2)
        
        # AWAY Goals
        away_goals_frame = tk.Frame(away_frame, bg='#2a2a2a')
        away_goals_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(away_goals_frame, text="Goals:", font=('Helvetica', 11, 'bold'),
                bg='#2a2a2a', fg='white', width=8, anchor='w').pack(side='left')
        
        tk.Button(away_goals_frame, text="−", font=('Helvetica', 16, 'bold'),
                 bg='#cc0000', fg='white', width=3, relief='flat',
                 command=lambda: self.adjust_afl_score('away', 'goals', -1)).pack(side='left', padx=2)
        
        self.afl_away_goals_entry = tk.Entry(away_goals_frame, font=('Helvetica', 14),
                                             bg='#333333', fg='white', width=6,
                                             relief='flat', insertbackground='white',
                                             justify='center')
        self.afl_away_goals_entry.pack(side='left', padx=5)
        self.afl_away_goals_entry.insert(0, str(self.afl_away_goals))
        self.afl_away_goals_entry.bind('<KeyRelease>', lambda e: self.manual_afl_score('away', 'goals'))
        
        tk.Button(away_goals_frame, text="+", font=('Helvetica', 16, 'bold'),
                 bg='#00aa00', fg='white', width=3, relief='flat',
                 command=lambda: self.adjust_afl_score('away', 'goals', 1)).pack(side='left', padx=2)
        
        # AWAY Points
        away_points_frame = tk.Frame(away_frame, bg='#2a2a2a')
        away_points_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(away_points_frame, text="Points:", font=('Helvetica', 11, 'bold'),
                bg='#2a2a2a', fg='white', width=8, anchor='w').pack(side='left')
        
        tk.Button(away_points_frame, text="−", font=('Helvetica', 16, 'bold'),
                 bg='#cc0000', fg='white', width=3, relief='flat',
                 command=lambda: self.adjust_afl_score('away', 'points', -1)).pack(side='left', padx=2)
        
        self.afl_away_points_entry = tk.Entry(away_points_frame, font=('Helvetica', 14),
                                              bg='#333333', fg='white', width=6,
                                              relief='flat', insertbackground='white',
                                              justify='center')
        self.afl_away_points_entry.pack(side='left', padx=5)
        self.afl_away_points_entry.insert(0, str(self.afl_away_points))
        self.afl_away_points_entry.bind('<KeyRelease>', lambda e: self.manual_afl_score('away', 'points'))
        
        tk.Button(away_points_frame, text="+", font=('Helvetica', 16, 'bold'),
                 bg='#00aa00', fg='white', width=3, relief='flat',
                 command=lambda: self.adjust_afl_score('away', 'points', 1)).pack(side='left', padx=2)
        
        # AWAY Total (read-only)
        away_total_frame = tk.Frame(away_frame, bg='#2a2a2a')
        away_total_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(away_total_frame, text="TOTAL:", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='#ffaa00', width=8, anchor='w').pack(side='left')
        
        self.afl_away_total_label = tk.Label(away_total_frame, text="0",
                                             font=('Helvetica', 18, 'bold'),
                                             bg='#333333', fg='#00ff00',
                                             width=6, relief='sunken', bd=2)
        self.afl_away_total_label.pack(side='left', padx=5)
        
        # Advertisements
        ads_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        ads_frame.pack(fill='x', pady=(15, 5), padx=5)
        self._build_ads_panel(ads_frame, self.return_to_afl_scores)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Send initial data
        self.update_afl_display()
    
    def update_afl_team_name(self, team):
        """Update AFL team name across RAMT slots using current afl_team_* style settings."""
        c = getattr(self, 'afl_team_color',   '1')
        s = getattr(self, 'afl_team_size',    '2')
        h = getattr(self, 'afl_team_h_align', '3')
        v = getattr(self, 'afl_team_v_align', '2')
        if team == 'home':
            name = self.afl_home_name_entry.get().strip()
            if name:
                self.afl_home_name = name
                self.home_name = name
                self.send_name_ramt(name, 1, c, s, h, v)
                self._refresh_score_name_labels('home')
        else:
            name = self.afl_away_name_entry.get().strip()
            if name:
                self.afl_away_name = name
                self.away_name = name
                self.send_name_ramt(name, 3, c, s, h, v)
                self._refresh_score_name_labels('away')
        self.save_config()
    
    def adjust_afl_score(self, team, score_type, delta):
        """Adjust AFL score (goals or points) by delta"""
        if team == 'home':
            if score_type == 'goals':
                self.afl_home_goals = max(0, self.afl_home_goals + delta)
                self.afl_home_goals_entry.delete(0, tk.END)
                self.afl_home_goals_entry.insert(0, str(self.afl_home_goals))
                # Counter 1 = HOME goals
                if delta > 0:
                    self.send_udp_command(f"*#1CNTS1,A{abs(delta)},0000")
                else:
                    self.send_udp_command(f"*#1CNTS1,D{abs(delta)},0000")
            else:  # points
                self.afl_home_points = max(0, self.afl_home_points + delta)
                self.afl_home_points_entry.delete(0, tk.END)
                self.afl_home_points_entry.insert(0, str(self.afl_home_points))
                # Counter 3 = HOME points
                if delta > 0:
                    self.send_udp_command(f"*#1CNTS3,A{abs(delta)},0000")
                else:
                    self.send_udp_command(f"*#1CNTS3,D{abs(delta)},0000")
        else:  # away
            if score_type == 'goals':
                self.afl_away_goals = max(0, self.afl_away_goals + delta)
                self.afl_away_goals_entry.delete(0, tk.END)
                self.afl_away_goals_entry.insert(0, str(self.afl_away_goals))
                # Counter 2 = AWAY goals
                if delta > 0:
                    self.send_udp_command(f"*#1CNTS2,A{abs(delta)},0000")
                else:
                    self.send_udp_command(f"*#1CNTS2,D{abs(delta)},0000")
            else:  # points
                self.afl_away_points = max(0, self.afl_away_points + delta)
                self.afl_away_points_entry.delete(0, tk.END)
                self.afl_away_points_entry.insert(0, str(self.afl_away_points))
                # Counter 4 = AWAY points
                if delta > 0:
                    self.send_udp_command(f"*#1CNTS4,A{abs(delta)},0000")
                else:
                    self.send_udp_command(f"*#1CNTS4,D{abs(delta)},0000")
        
        self.update_afl_totals()
    
    def manual_afl_score(self, team, score_type):
        """Handle manual AFL score entry"""
        try:
            if team == 'home':
                if score_type == 'goals':
                    value = int(self.afl_home_goals_entry.get())
                    self.afl_home_goals = max(0, value)
                    self.send_udp_command(f"*#1CNTS1,S{self.afl_home_goals},0000")
                else:
                    value = int(self.afl_home_points_entry.get())
                    self.afl_home_points = max(0, value)
                    self.send_udp_command(f"*#1CNTS3,S{self.afl_home_points},0000")
            else:
                if score_type == 'goals':
                    value = int(self.afl_away_goals_entry.get())
                    self.afl_away_goals = max(0, value)
                    self.send_udp_command(f"*#1CNTS2,S{self.afl_away_goals},0000")
                else:
                    value = int(self.afl_away_points_entry.get())
                    self.afl_away_points = max(0, value)
                    self.send_udp_command(f"*#1CNTS4,S{self.afl_away_points},0000")
            
            self.update_afl_totals()
        except ValueError:
            pass
    
    def update_afl_totals(self):
        """Calculate and update AFL total scores (Goals×6 + Points)"""
        home_total = (self.afl_home_goals * 6) + self.afl_home_points
        away_total = (self.afl_away_goals * 6) + self.afl_away_points
        
        self.afl_home_total_label.config(text=str(home_total))
        self.afl_away_total_label.config(text=str(away_total))
        
        # Counter 5 = HOME total, Counter 6 = AWAY total
        self.send_udp_command(f"*#1CNTS5,S{home_total},0000")
        self.send_udp_command(f"*#1CNTS6,S{away_total},0000")
    
    def return_to_afl_scores(self):
        """Return to AFL scores screen"""
        self.save_config()  # Save AFL scores
        self.stop_scrolling_text()
        program_num = self.sport_programs[self.current_sport]
        self.send_udp_command(f"*#1PRGC3{program_num},0000")
        self.root.after(100, self.update_afl_display)
        print("[AFL] Returned to scores screen")
    
    def update_afl_display(self):
        """Send all AFL data to display"""
        # Set all counters
        self.send_udp_command(f"*#1CNTS1,S{self.afl_home_goals},0000")
        self.send_udp_command(f"*#1CNTS2,S{self.afl_away_goals},0000")
        self.send_udp_command(f"*#1CNTS3,S{self.afl_home_points},0000")
        self.send_udp_command(f"*#1CNTS4,S{self.afl_away_points},0000")
        
        home_total = (self.afl_home_goals * 6) + self.afl_home_points
        away_total = (self.afl_away_goals * 6) + self.afl_away_points
        self.send_udp_command(f"*#1CNTS5,S{home_total},0000")
        self.send_udp_command(f"*#1CNTS6,S{away_total},0000")
        
        # Set team names using current afl_team_* style settings
        home_name = getattr(self, 'afl_home_name', 'HOME')
        away_name = getattr(self, 'afl_away_name', 'AWAY')
        c = getattr(self, 'afl_team_color',   '1')
        s = getattr(self, 'afl_team_size',    '2')
        h = getattr(self, 'afl_team_h_align', '3')
        v = getattr(self, 'afl_team_v_align', '2')
        self.send_name_ramt(home_name, 1, c, s, h, v)
        self.send_name_ramt(away_name, 3, c, s, h, v)

        # Send quarter to RAMT8
        self._send_afl_quarter()

    def start_advertisement_from_afl(self):
        """Start advertisement from AFL screen"""
        all_ads = self._get_all_ads()
        if all_ads:
            self._play_advertisement(all_ads[self.current_ad_index])
    
    def reset_afl_scores(self, team):
        """Reset AFL scores for a team"""
        if team == 'home':
            self.afl_home_goals = 0
            self.afl_home_points = 0
            self.afl_home_goals_entry.delete(0, tk.END)
            self.afl_home_goals_entry.insert(0, "0")
            self.afl_home_points_entry.delete(0, tk.END)
            self.afl_home_points_entry.insert(0, "0")
            self.send_udp_command("*#1CNTS1,S0,0000")
            self.send_udp_command("*#1CNTS3,S0,0000")
        else:
            self.afl_away_goals = 0
            self.afl_away_points = 0
            self.afl_away_goals_entry.delete(0, tk.END)
            self.afl_away_goals_entry.insert(0, "0")
            self.afl_away_points_entry.delete(0, tk.END)
            self.afl_away_points_entry.insert(0, "0")
            self.send_udp_command("*#1CNTS2,S0,0000")
            self.send_udp_command("*#1CNTS4,S0,0000")
        
        self.update_afl_totals()
        print(f"[AFL] {team.upper()} scores reset")
    
    def show_afl_team_settings(self):
        """Popup to configure AFL team name display style (colour, size, alignment)."""
        win = tk.Toplevel(self.root)
        win.title("Team Name Settings")
        win.configure(bg='#1a1a1a')
        win.geometry("390x290")
        win.grab_set()

        tk.Label(win, text="Team Name Style", font=('Helvetica', 15, 'bold'),
                 bg='#1a1a1a', fg='white').pack(pady=(14, 4))
        tk.Label(win, text="(updates live on display)", font=('Helvetica', 10),
                 bg='#1a1a1a', fg='#888888').pack()

        color_var = tk.StringVar(value=getattr(self, 'afl_team_color',   '1'))
        size_var  = tk.StringVar(value=getattr(self, 'afl_team_size',    '2'))
        h_var     = tk.StringVar(value=getattr(self, 'afl_team_h_align', '3'))
        v_var     = tk.StringVar(value=getattr(self, 'afl_team_v_align', '2'))

        def on_live():
            self.afl_team_color   = color_var.get()
            self.afl_team_size    = size_var.get()
            self.afl_team_h_align = h_var.get()
            self.afl_team_v_align = v_var.get()
            home = getattr(self, 'afl_home_name', self.home_name)
            away = getattr(self, 'afl_away_name', self.away_name)
            self.send_name_ramt(home, 1, self.afl_team_color, self.afl_team_size,
                                self.afl_team_h_align, self.afl_team_v_align)
            self.send_name_ramt(away, 3, self.afl_team_color, self.afl_team_size,
                                self.afl_team_h_align, self.afl_team_v_align)

        # show_h_align=False: team names always left-aligned (forced in send_name_ramt)
        self._build_display_settings(win, color_var, size_var, h_var, v_var, on_live,
                                     show_h_align=False)

        def apply():
            on_live()
            self.save_config()
            win.destroy()

        tk.Button(win, text="Apply & Close", font=('Helvetica', 12, 'bold'),
                  bg='#0066cc', fg='white', relief='flat', padx=20, pady=8,
                  command=apply).pack(pady=10)

    def show_cricket_ui(self):
        """Show Cricket score management UI"""
        self.root.geometry("520x700")
        # Initialize Cricket-specific scores if not exists
        if not hasattr(self, 'cricket_home_runs'):
            self.cricket_home_runs = 0
            self.cricket_home_wickets = 0
            self.cricket_away_runs = 0
            self.cricket_away_wickets = 0
            self.cricket_extras = 0
            self.cricket_overs = 0
            self.cricket_balls = 0
            self.cricket_home_name = "HOME"
            self.cricket_away_name = "AWAY"
        
        # Stop any scrolling text
        self.stop_scrolling_text()
        
        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Main container with scrollbar
        canvas = tk.Canvas(self.root, bg='#1a1a1a', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#1a1a1a')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        main_frame = tk.Frame(scrollable_frame, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Top bar
        top_bar = tk.Frame(main_frame, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 15))
        
        tk.Button(top_bar, text="← Controller", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 command=self.back_to_home).pack(side='left')
        
        title = tk.Label(top_bar, text="Cricket Match",
                        font=('Helvetica', 24, 'bold'),
                        bg='#1a1a1a', fg='white')
        title.pack(side='left', expand=True)
        
        # Team names
        team_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        team_frame.pack(fill='x', pady=(0, 15), ipady=10)

        team_header = tk.Frame(team_frame, bg='#2a2a2a')
        team_header.pack(fill='x', padx=10, pady=5)

        tk.Label(team_header, text="Team Names", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left')

        tk.Button(team_header, text="⚙", font=('Helvetica', 11),
                 bg='#444444', fg='white', relief='flat', width=3,
                 command=self.show_cricket_team_settings).pack(side='right')

        # HOME team name
        home_team_frame = tk.Frame(team_frame, bg='#2a2a2a')
        home_team_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(home_team_frame, text="Home:", font=('Helvetica', 11),
                bg='#2a2a2a', fg='white', width=6, anchor='w').pack(side='left')
        
        self.cricket_home_name_entry = tk.Entry(home_team_frame, font=('Helvetica', 14),
                                                bg='#333333', fg='white', relief='flat',
                                                insertbackground='white')
        self.cricket_home_name_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.cricket_home_name_entry.insert(0, self.cricket_home_name)
        self.cricket_home_name_entry.bind('<KeyRelease>', lambda e: self.update_cricket_team_name('home'))
        
        # AWAY team name
        away_team_frame = tk.Frame(team_frame, bg='#2a2a2a')
        away_team_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(away_team_frame, text="Away:", font=('Helvetica', 11),
                bg='#2a2a2a', fg='white', width=6, anchor='w').pack(side='left')
        
        self.cricket_away_name_entry = tk.Entry(away_team_frame, font=('Helvetica', 14),
                                                bg='#333333', fg='white', relief='flat',
                                                insertbackground='white')
        self.cricket_away_name_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.cricket_away_name_entry.insert(0, self.cricket_away_name)
        self.cricket_away_name_entry.bind('<KeyRelease>', lambda e: self.update_cricket_team_name('away'))
        
        # HOME TEAM SCORES
        home_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        home_frame.pack(fill='x', pady=(0, 10), ipady=10)
        
        home_header = tk.Frame(home_frame, bg='#2a2a2a')
        home_header.pack(fill='x', padx=10, pady=(5, 0))
        
        self.cricket_score_home_lbl = tk.Label(home_header, text=f"{self.home_name[:8]} BATTING",
                font=('Helvetica', 13, 'bold'), bg='#2a2a2a', fg='#00aaff')
        self.cricket_score_home_lbl.pack(side='left')
        
        tk.Button(home_header, text="↻", font=('Helvetica', 12),
                 bg='#cc0000', fg='white', relief='flat', width=3,
                 command=lambda: self.reset_cricket_scores('home')).pack(side='right', padx=2)
        
        # HOME Runs - compact layout
        home_runs_frame = tk.Frame(home_frame, bg='#2a2a2a')
        home_runs_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(home_runs_frame, text="Runs:", font=('Helvetica', 11, 'bold'),
                bg='#2a2a2a', fg='white', width=6, anchor='w').pack(side='left')
        
        # Quick run buttons - more compact
        for runs in [1, 2, 3, 4, 6]:
            tk.Button(home_runs_frame, text=f"+{runs}", font=('Helvetica', 9, 'bold'),
                     bg='#00aa00', fg='white', relief='flat', width=2,
                     command=lambda r=runs: self.adjust_cricket_runs('home', r)).pack(side='left', padx=1)
        
        tk.Button(home_runs_frame, text="−", font=('Helvetica', 11, 'bold'),
                 bg='#cc0000', fg='white', relief='flat', width=2,
                 command=lambda: self.adjust_cricket_runs('home', -1)).pack(side='left', padx=2)
        
        self.cricket_home_runs_entry = tk.Entry(home_runs_frame, font=('Helvetica', 12),
                                                bg='#333333', fg='white', width=4,
                                                relief='flat', insertbackground='white',
                                                justify='center')
        self.cricket_home_runs_entry.pack(side='left', padx=3)
        self.cricket_home_runs_entry.insert(0, str(self.cricket_home_runs))
        self.cricket_home_runs_entry.bind('<KeyRelease>', lambda e: self.manual_cricket_score('home', 'runs'))
        
        # HOME Wickets
        home_wickets_frame = tk.Frame(home_frame, bg='#2a2a2a')
        home_wickets_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(home_wickets_frame, text="Wickets:", font=('Helvetica', 11, 'bold'),
                bg='#2a2a2a', fg='white', width=8, anchor='w').pack(side='left')
        
        tk.Button(home_wickets_frame, text="−", font=('Helvetica', 16, 'bold'),
                 bg='#cc0000', fg='white', width=3, relief='flat',
                 command=lambda: self.adjust_cricket_wickets('home', -1)).pack(side='left', padx=2)
        
        self.cricket_home_wickets_entry = tk.Entry(home_wickets_frame, font=('Helvetica', 14),
                                                   bg='#333333', fg='white', width=5,
                                                   relief='flat', insertbackground='white',
                                                   justify='center')
        self.cricket_home_wickets_entry.pack(side='left', padx=5)
        self.cricket_home_wickets_entry.insert(0, str(self.cricket_home_wickets))
        self.cricket_home_wickets_entry.bind('<KeyRelease>', lambda e: self.manual_cricket_score('home', 'wickets'))
        
        tk.Button(home_wickets_frame, text="+", font=('Helvetica', 16, 'bold'),
                 bg='#00aa00', fg='white', width=3, relief='flat',
                 command=lambda: self.adjust_cricket_wickets('home', 1)).pack(side='left', padx=2)
        
        # AWAY TEAM SCORES
        away_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        away_frame.pack(fill='x', pady=(0, 10), ipady=10)
        
        away_header = tk.Frame(away_frame, bg='#2a2a2a')
        away_header.pack(fill='x', padx=10, pady=(5, 0))
        
        self.cricket_score_away_lbl = tk.Label(away_header, text=f"{self.away_name[:8]} BATTING",
                font=('Helvetica', 13, 'bold'), bg='#2a2a2a', fg='#ff6600')
        self.cricket_score_away_lbl.pack(side='left')
        
        tk.Button(away_header, text="↻", font=('Helvetica', 12),
                 bg='#cc0000', fg='white', relief='flat', width=3,
                 command=lambda: self.reset_cricket_scores('away')).pack(side='right', padx=2)
        
        # AWAY Runs - compact layout
        away_runs_frame = tk.Frame(away_frame, bg='#2a2a2a')
        away_runs_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(away_runs_frame, text="Runs:", font=('Helvetica', 11, 'bold'),
                bg='#2a2a2a', fg='white', width=6, anchor='w').pack(side='left')
        
        # Quick run buttons - more compact
        for runs in [1, 2, 3, 4, 6]:
            tk.Button(away_runs_frame, text=f"+{runs}", font=('Helvetica', 9, 'bold'),
                     bg='#00aa00', fg='white', relief='flat', width=2,
                     command=lambda r=runs: self.adjust_cricket_runs('away', r)).pack(side='left', padx=1)
        
        tk.Button(away_runs_frame, text="−", font=('Helvetica', 11, 'bold'),
                 bg='#cc0000', fg='white', relief='flat', width=2,
                 command=lambda: self.adjust_cricket_runs('away', -1)).pack(side='left', padx=2)
        
        self.cricket_away_runs_entry = tk.Entry(away_runs_frame, font=('Helvetica', 12),
                                                bg='#333333', fg='white', width=4,
                                                relief='flat', insertbackground='white',
                                                justify='center')
        self.cricket_away_runs_entry.pack(side='left', padx=3)
        self.cricket_away_runs_entry.insert(0, str(self.cricket_away_runs))
        self.cricket_away_runs_entry.bind('<KeyRelease>', lambda e: self.manual_cricket_score('away', 'runs'))
        
        # AWAY Wickets
        away_wickets_frame = tk.Frame(away_frame, bg='#2a2a2a')
        away_wickets_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(away_wickets_frame, text="Wickets:", font=('Helvetica', 11, 'bold'),
                bg='#2a2a2a', fg='white', width=8, anchor='w').pack(side='left')
        
        tk.Button(away_wickets_frame, text="−", font=('Helvetica', 16, 'bold'),
                 bg='#cc0000', fg='white', width=3, relief='flat',
                 command=lambda: self.adjust_cricket_wickets('away', -1)).pack(side='left', padx=2)
        
        self.cricket_away_wickets_entry = tk.Entry(away_wickets_frame, font=('Helvetica', 14),
                                                   bg='#333333', fg='white', width=5,
                                                   relief='flat', insertbackground='white',
                                                   justify='center')
        self.cricket_away_wickets_entry.pack(side='left', padx=5)
        self.cricket_away_wickets_entry.insert(0, str(self.cricket_away_wickets))
        self.cricket_away_wickets_entry.bind('<KeyRelease>', lambda e: self.manual_cricket_score('away', 'wickets'))
        
        tk.Button(away_wickets_frame, text="+", font=('Helvetica', 16, 'bold'),
                 bg='#00aa00', fg='white', width=3, relief='flat',
                 command=lambda: self.adjust_cricket_wickets('away', 1)).pack(side='left', padx=2)
        
        # EXTRAS AND OVERS
        extras_overs_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        extras_overs_frame.pack(fill='x', pady=(0, 10), ipady=10)
        
        tk.Label(extras_overs_frame, text="EXTRAS & OVERS", font=('Helvetica', 13, 'bold'),
                bg='#2a2a2a', fg='#ffaa00').pack(pady=(5, 10))
        
        # Extras (C5)
        extras_frame = tk.Frame(extras_overs_frame, bg='#2a2a2a')
        extras_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(extras_frame, text="Extras:", font=('Helvetica', 11, 'bold'),
                bg='#2a2a2a', fg='white', width=8, anchor='w').pack(side='left')
        
        tk.Button(extras_frame, text="−", font=('Helvetica', 16, 'bold'),
                 bg='#cc0000', fg='white', width=3, relief='flat',
                 command=lambda: self.adjust_cricket_extras(-1)).pack(side='left', padx=2)
        
        self.cricket_extras_entry = tk.Entry(extras_frame, font=('Helvetica', 14),
                                            bg='#333333', fg='white', width=5,
                                            relief='flat', insertbackground='white',
                                            justify='center')
        self.cricket_extras_entry.pack(side='left', padx=5)
        self.cricket_extras_entry.insert(0, str(self.cricket_extras))
        self.cricket_extras_entry.bind('<KeyRelease>', lambda e: self.manual_cricket_extras())
        
        tk.Button(extras_frame, text="+", font=('Helvetica', 16, 'bold'),
                 bg='#00aa00', fg='white', width=3, relief='flat',
                 command=lambda: self.adjust_cricket_extras(1)).pack(side='left', padx=2)
        tk.Button(extras_frame, text="↻", font=('Helvetica', 12, 'bold'),
                 bg='#555555', fg='white', width=2, relief='flat',
                 command=self.reset_cricket_extras).pack(side='left', padx=(8, 2))

        # Overs (C6) and Balls (C7) — separate +/- for each part
        tk.Label(extras_overs_frame, text="Overs:", font=('Helvetica', 11, 'bold'),
                bg='#2a2a2a', fg='#ffaa00').pack(pady=(8, 2))

        overs_row = tk.Frame(extras_overs_frame, bg='#2a2a2a')
        overs_row.pack(fill='x', padx=10, pady=2)

        # --- Overs integer part ---
        tk.Label(overs_row, text="Overs:", font=('Helvetica', 10),
                bg='#2a2a2a', fg='white', width=7, anchor='w').pack(side='left')
        tk.Button(overs_row, text="−", font=('Helvetica', 14, 'bold'),
                 bg='#cc0000', fg='white', width=2, relief='flat',
                 command=lambda: self.adjust_cricket_overs(-1)).pack(side='left', padx=2)
        self.cricket_overs_entry = tk.Entry(overs_row, font=('Helvetica', 13),
                                           bg='#333333', fg='white', width=4,
                                           relief='flat', insertbackground='white', justify='center')
        self.cricket_overs_entry.pack(side='left', padx=4)
        self.cricket_overs_entry.insert(0, str(self.cricket_overs))
        self.cricket_overs_entry.bind('<KeyRelease>', lambda e: self.manual_cricket_overs())
        tk.Button(overs_row, text="+", font=('Helvetica', 14, 'bold'),
                 bg='#00aa00', fg='white', width=2, relief='flat',
                 command=lambda: self.adjust_cricket_overs(1)).pack(side='left', padx=2)

        balls_row = tk.Frame(extras_overs_frame, bg='#2a2a2a')
        balls_row.pack(fill='x', padx=10, pady=2)

        # --- Balls (after decimal) ---
        tk.Label(balls_row, text="Balls:", font=('Helvetica', 10),
                bg='#2a2a2a', fg='white', width=7, anchor='w').pack(side='left')
        tk.Button(balls_row, text="−", font=('Helvetica', 14, 'bold'),
                 bg='#cc0000', fg='white', width=2, relief='flat',
                 command=lambda: self.adjust_cricket_balls(-1)).pack(side='left', padx=2)
        self.cricket_balls_entry = tk.Entry(balls_row, font=('Helvetica', 13),
                                           bg='#333333', fg='white', width=4,
                                           relief='flat', insertbackground='white', justify='center')
        self.cricket_balls_entry.pack(side='left', padx=4)
        self.cricket_balls_entry.insert(0, str(self.cricket_balls))
        self.cricket_balls_entry.bind('<KeyRelease>', lambda e: self.manual_cricket_balls())
        tk.Button(balls_row, text="+", font=('Helvetica', 14, 'bold'),
                 bg='#00aa00', fg='white', width=2, relief='flat',
                 command=lambda: self.adjust_cricket_balls(1)).pack(side='left', padx=2)

        overs_reset_row = tk.Frame(extras_overs_frame, bg='#2a2a2a')
        overs_reset_row.pack(fill='x', padx=10, pady=(4, 2))
        tk.Button(overs_reset_row, text="↻ Reset Overs & Balls", font=('Helvetica', 11),
                 bg='#555555', fg='white', relief='flat', padx=10, pady=4,
                 command=self.reset_cricket_overs).pack(side='left')

        self.cricket_overs_label = tk.Label(extras_overs_frame,
                text=f"Current: {self.cricket_overs}.{self.cricket_balls} overs",
                font=('Helvetica', 10), bg='#2a2a2a', fg='#aaaaaa')
        self.cricket_overs_label.pack(pady=(2, 5))
        
        # Advertisements
        ads_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        ads_frame.pack(fill='x', pady=(15, 5))
        self._build_ads_panel(ads_frame, self.return_to_cricket_scores)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Send initial data
        self.update_cricket_display()
    
    # Cricket supporting functions
    def update_cricket_team_name(self, team):
        """Update Cricket team name across RAMT slots using current cricket_team_* style settings."""
        c = getattr(self, 'cricket_team_color',   '1')
        s = getattr(self, 'cricket_team_size',    '2')
        h = getattr(self, 'cricket_team_h_align', '3')
        v = getattr(self, 'cricket_team_v_align', '2')
        if team == 'home':
            name = self.cricket_home_name_entry.get().strip()
            if name:
                self.cricket_home_name = name
                self.home_name = name
                self.send_name_ramt(name, 1, c, s, h, v)
                if hasattr(self, 'cricket_score_home_lbl'):
                    try:
                        self.cricket_score_home_lbl.config(text=f"{name[:8]} BATTING")
                    except Exception:
                        pass
                self._refresh_score_name_labels('home')
        else:
            name = self.cricket_away_name_entry.get().strip()
            if name:
                self.cricket_away_name = name
                self.away_name = name
                self.send_name_ramt(name, 3, c, s, h, v)
                if hasattr(self, 'cricket_score_away_lbl'):
                    try:
                        self.cricket_score_away_lbl.config(text=f"{name[:8]} BATTING")
                    except Exception:
                        pass
                self._refresh_score_name_labels('away')
        self.save_config()
    
    def adjust_cricket_runs(self, team, delta):
        """Adjust cricket runs"""
        if team == 'home':
            self.cricket_home_runs = max(0, self.cricket_home_runs + delta)
            self.cricket_home_runs_entry.delete(0, tk.END)
            self.cricket_home_runs_entry.insert(0, str(self.cricket_home_runs))
            # Counter 1 = HOME runs
            self.send_udp_command(f"*#1CNTS1,S{self.cricket_home_runs},0000")
        else:
            self.cricket_away_runs = max(0, self.cricket_away_runs + delta)
            self.cricket_away_runs_entry.delete(0, tk.END)
            self.cricket_away_runs_entry.insert(0, str(self.cricket_away_runs))
            # Counter 2 = AWAY runs
            self.send_udp_command(f"*#1CNTS2,S{self.cricket_away_runs},0000")
        self.save_config()
    
    def adjust_cricket_wickets(self, team, delta):
        """Adjust cricket wickets"""
        if team == 'home':
            self.cricket_home_wickets = max(0, min(10, self.cricket_home_wickets + delta))
            self.cricket_home_wickets_entry.delete(0, tk.END)
            self.cricket_home_wickets_entry.insert(0, str(self.cricket_home_wickets))
            # Counter 3 = HOME wickets
            self.send_udp_command(f"*#1CNTS3,S{self.cricket_home_wickets},0000")
        else:
            self.cricket_away_wickets = max(0, min(10, self.cricket_away_wickets + delta))
            self.cricket_away_wickets_entry.delete(0, tk.END)
            self.cricket_away_wickets_entry.insert(0, str(self.cricket_away_wickets))
            # Counter 4 = AWAY wickets
            self.send_udp_command(f"*#1CNTS4,S{self.cricket_away_wickets},0000")
        self.save_config()
    
    def adjust_cricket_extras(self, delta):
        """Adjust cricket extras"""
        self.cricket_extras = max(0, self.cricket_extras + delta)
        self.cricket_extras_entry.delete(0, tk.END)
        self.cricket_extras_entry.insert(0, str(self.cricket_extras))
        # Counter 5 = Extras
        self.send_udp_command(f"*#1CNTS5,S{self.cricket_extras},0000")
        self.save_config()
    
    def adjust_cricket_overs(self, delta):
        """Adjust cricket overs"""
        self.cricket_overs = max(0, self.cricket_overs + delta)
        self.cricket_overs_entry.delete(0, tk.END)
        self.cricket_overs_entry.insert(0, str(self.cricket_overs))
        # Counter 6 = Overs (before decimal)
        self.send_udp_command(f"*#1CNTS6,S{self.cricket_overs},0000")
        self.save_config()
    
    def adjust_cricket_balls(self, delta):
        """Adjust cricket balls (0-5, auto-increment over)"""
        self.cricket_balls = self.cricket_balls + delta
        
        # Auto-increment over when reaching 6 balls
        if self.cricket_balls >= 6:
            self.cricket_overs += 1
            self.cricket_balls = 0
            self.cricket_overs_entry.delete(0, tk.END)
            self.cricket_overs_entry.insert(0, str(self.cricket_overs))
            self.send_udp_command(f"*#1CNTS6,S{self.cricket_overs},0000")
        elif self.cricket_balls < 0:
            if self.cricket_overs > 0:
                self.cricket_overs -= 1
                self.cricket_balls = 5
                self.cricket_overs_entry.delete(0, tk.END)
                self.cricket_overs_entry.insert(0, str(self.cricket_overs))
                self.send_udp_command(f"*#1CNTS6,S{self.cricket_overs},0000")
            else:
                self.cricket_balls = 0
        
        self.cricket_balls_entry.delete(0, tk.END)
        self.cricket_balls_entry.insert(0, str(self.cricket_balls))
        # Counter 7 = Balls (after decimal)
        self.send_udp_command(f"*#1CNTS7,S{self.cricket_balls},0000")
        self.save_config()
    
    def manual_cricket_score(self, team, score_type):
        """Handle manual cricket score entry"""
        try:
            if team == 'home':
                if score_type == 'runs':
                    value = int(self.cricket_home_runs_entry.get())
                    self.cricket_home_runs = max(0, value)
                    self.send_udp_command(f"*#1CNTS1,S{self.cricket_home_runs},0000")
                else:  # wickets
                    value = int(self.cricket_home_wickets_entry.get())
                    self.cricket_home_wickets = max(0, min(10, value))
                    self.send_udp_command(f"*#1CNTS3,S{self.cricket_home_wickets},0000")
            else:
                if score_type == 'runs':
                    value = int(self.cricket_away_runs_entry.get())
                    self.cricket_away_runs = max(0, value)
                    self.send_udp_command(f"*#1CNTS2,S{self.cricket_away_runs},0000")
                else:  # wickets
                    value = int(self.cricket_away_wickets_entry.get())
                    self.cricket_away_wickets = max(0, min(10, value))
                    self.send_udp_command(f"*#1CNTS4,S{self.cricket_away_wickets},0000")
            self.save_config()
        except ValueError:
            pass
    
    def manual_cricket_extras(self):
        """Handle manual cricket extras entry"""
        try:
            value = int(self.cricket_extras_entry.get())
            self.cricket_extras = max(0, value)
            self.send_udp_command(f"*#1CNTS5,S{self.cricket_extras},0000")
            self.save_config()
        except ValueError:
            pass
    
    def manual_cricket_overs(self):
        """Handle manual cricket overs entry"""
        try:
            value = int(self.cricket_overs_entry.get())
            self.cricket_overs = max(0, value)
            self.send_udp_command(f"*#1CNTS6,S{self.cricket_overs},0000")
            self.save_config()
        except ValueError:
            pass
    
    def manual_cricket_balls(self):
        """Handle manual cricket balls entry"""
        try:
            value = int(self.cricket_balls_entry.get())
            self.cricket_balls = max(0, min(5, value))
            self.send_udp_command(f"*#1CNTS7,S{self.cricket_balls},0000")
            self.save_config()
        except ValueError:
            pass
    
    def reset_cricket_scores(self, team):
        """Reset Cricket scores for a team"""
        if team == 'home':
            self.cricket_home_runs = 0
            self.cricket_home_wickets = 0
            self.cricket_home_runs_entry.delete(0, tk.END)
            self.cricket_home_runs_entry.insert(0, "0")
            self.cricket_home_wickets_entry.delete(0, tk.END)
            self.cricket_home_wickets_entry.insert(0, "0")
            self.send_udp_command("*#1CNTS1,S0,0000")
            self.send_udp_command("*#1CNTS3,S0,0000")
        else:
            self.cricket_away_runs = 0
            self.cricket_away_wickets = 0
            self.cricket_away_runs_entry.delete(0, tk.END)
            self.cricket_away_runs_entry.insert(0, "0")
            self.cricket_away_wickets_entry.delete(0, tk.END)
            self.cricket_away_wickets_entry.insert(0, "0")
            self.send_udp_command("*#1CNTS2,S0,0000")
            self.send_udp_command("*#1CNTS4,S0,0000")
        
        self.save_config()
        print(f"[CRICKET] {team.upper()} scores reset")
    
    def reset_cricket_extras(self):
        """Reset cricket extras to 0"""
        self.cricket_extras = 0
        self.cricket_extras_entry.delete(0, tk.END)
        self.cricket_extras_entry.insert(0, "0")
        self.send_udp_command("*#1CNTS5,S0,0000")
        self.save_config()

    def reset_cricket_overs(self):
        """Reset cricket overs and balls to 0"""
        self.cricket_overs = 0
        self.cricket_balls = 0
        self.cricket_overs_entry.delete(0, tk.END)
        self.cricket_overs_entry.insert(0, "0")
        self.cricket_balls_entry.delete(0, tk.END)
        self.cricket_balls_entry.insert(0, "0")
        self.send_udp_command("*#1CNTS6,S0,0000")
        self.send_udp_command("*#1CNTS7,S0,0000")
        if hasattr(self, 'cricket_overs_label'):
            self.cricket_overs_label.config(text="Current: 0.0 overs")
        self.save_config()

    def show_cricket_team_settings(self):
        """Popup to configure Cricket team name display style (colour, size, alignment)."""
        win = tk.Toplevel(self.root)
        win.title("Team Name Settings")
        win.configure(bg='#1a1a1a')
        win.geometry("390x290")
        win.grab_set()

        tk.Label(win, text="Team Name Style", font=('Helvetica', 15, 'bold'),
                 bg='#1a1a1a', fg='white').pack(pady=(14, 4))
        tk.Label(win, text="(updates live on display)", font=('Helvetica', 10),
                 bg='#1a1a1a', fg='#888888').pack()

        color_var = tk.StringVar(value=getattr(self, 'cricket_team_color',   '1'))
        size_var  = tk.StringVar(value=getattr(self, 'cricket_team_size',    '2'))
        h_var     = tk.StringVar(value=getattr(self, 'cricket_team_h_align', '3'))
        v_var     = tk.StringVar(value=getattr(self, 'cricket_team_v_align', '2'))

        def on_live():
            self.cricket_team_color   = color_var.get()
            self.cricket_team_size    = size_var.get()
            self.cricket_team_h_align = h_var.get()
            self.cricket_team_v_align = v_var.get()
            home = getattr(self, 'cricket_home_name', self.home_name)
            away = getattr(self, 'cricket_away_name', self.away_name)
            self.send_name_ramt(home, 1, self.cricket_team_color, self.cricket_team_size,
                                self.cricket_team_h_align, self.cricket_team_v_align)
            self.send_name_ramt(away, 3, self.cricket_team_color, self.cricket_team_size,
                                self.cricket_team_h_align, self.cricket_team_v_align)

        # show_h_align=False: team names always left-aligned (forced in send_name_ramt)
        self._build_display_settings(win, color_var, size_var, h_var, v_var, on_live,
                                     show_h_align=False)

        def apply():
            on_live()
            self.save_config()
            win.destroy()

        tk.Button(win, text="Apply & Close", font=('Helvetica', 12, 'bold'),
                  bg='#0066cc', fg='white', relief='flat', padx=20, pady=8,
                  command=apply).pack(pady=10)
    
    def return_to_cricket_scores(self):
        """Return to Cricket scores screen"""
        self.save_config()
        self.stop_scrolling_text()
        program_num = self.sport_programs.get(self.current_sport, "4")
        self.send_udp_command(f"*#1PRGC3{program_num},0000")
        self.root.after(100, self.update_cricket_display)
        print("[CRICKET] Returned to scores screen")
    
    def update_cricket_display(self):
        """Send all Cricket data to display"""
        # Set all counters
        self.send_udp_command(f"*#1CNTS1,S{self.cricket_home_runs},0000")
        self.send_udp_command(f"*#1CNTS2,S{self.cricket_away_runs},0000")
        self.send_udp_command(f"*#1CNTS3,S{self.cricket_home_wickets},0000")
        self.send_udp_command(f"*#1CNTS4,S{self.cricket_away_wickets},0000")
        self.send_udp_command(f"*#1CNTS5,S{self.cricket_extras},0000")
        self.send_udp_command(f"*#1CNTS6,S{self.cricket_overs},0000")
        self.send_udp_command(f"*#1CNTS7,S{self.cricket_balls},0000")
        
        # Set team names using current cricket_team_* style settings
        c = getattr(self, 'cricket_team_color',   '1')
        s = getattr(self, 'cricket_team_size',    '2')
        h = getattr(self, 'cricket_team_h_align', '3')
        v = getattr(self, 'cricket_team_v_align', '2')
        self.send_name_ramt(self.cricket_home_name, 1, c, s, h, v)
        self.send_name_ramt(self.cricket_away_name, 3, c, s, h, v)
    
    def start_advertisement_from_cricket(self):
        """Start advertisement from Cricket screen"""
        all_ads = self._get_all_ads()
        if all_ads:
            self._play_advertisement(all_ads[self.current_ad_index])
    
    def show_current_sport_ui(self):
        """Route back to the correct sport UI based on current_sport"""
        if self.current_sport == "Soccer":
            self.show_soccer_ui()
        elif self.current_sport == "AFL":
            self.show_afl_ui()
        elif self.current_sport == "Cricket":
            self.show_cricket_ui()
        elif self.current_sport in ["Rugby", "Hockey", "Basketball"]:
            self.show_simple_sport_ui()
        else:
            self.create_home_screen()

    def show_simple_sport_ui(self):
        """Generic score UI for Rugby, Hockey, Basketball"""
        self.root.geometry("520x700")
        # Set sport-specific timer defaults when entering a new sport
        _countdown_defaults = {"Basketball": 12*60, "Hockey": 20*60}
        _countup_sports = {"Rugby"}
        if self.timer_configured_for != self.current_sport and not self.timer_running:
            if self.current_sport in _countdown_defaults:
                self.timer_countdown = True
                self.timer_target_seconds = _countdown_defaults[self.current_sport]
                self.timer_seconds = self.timer_target_seconds
            elif self.current_sport in _countup_sports:
                self.timer_countdown = False
                self.timer_target_seconds = 0
                self.timer_seconds = 0
            self.timer_configured_for = self.current_sport
        # Shot clock defaults
        _sc_defaults = {"Basketball": 30, "Hockey": 40}
        if self.current_sport in _sc_defaults and self.shot_clock_target in (30, 40):
            self.shot_clock_target = _sc_defaults[self.current_sport]
            self.shot_clock_seconds = self.shot_clock_target
        self.stop_scrolling_text()
        for widget in self.root.winfo_children():
            widget.destroy()

        canvas = tk.Canvas(self.root, bg='#1a1a1a', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#1a1a1a')
        scrollable_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        main_frame = tk.Frame(scrollable_frame, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        top_bar = tk.Frame(main_frame, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 15))
        tk.Button(top_bar, text="← Controller", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 command=self.back_to_home).pack(side='left')
        tk.Label(top_bar, text=f"{self.current_sport} Match",
                font=('Helvetica', 24, 'bold'), bg='#1a1a1a', fg='white').pack(side='left', expand=True)

        # Team names
        team_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        team_frame.pack(fill='x', pady=(0, 15), padx=5, ipady=10)
        team_header = tk.Frame(team_frame, bg='#2a2a2a')
        team_header.pack(fill='x', padx=10, pady=5)
        tk.Label(team_header, text="Team Names", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left')
        tk.Button(team_header, text="⚙", font=('Helvetica', 10), bg='#555555', fg='white',
                 relief='flat', padx=8, pady=2,
                 command=self.show_team_name_settings).pack(side='right')

        home_team_frame = tk.Frame(team_frame, bg='#2a2a2a')
        home_team_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(home_team_frame, text="Home:", font=('Helvetica', 11),
                bg='#2a2a2a', fg='white', width=6, anchor='w').pack(side='left')
        self.home_name_entry = tk.Entry(home_team_frame, font=('Helvetica', 14),
                                        bg='#333333', fg='white', relief='flat', insertbackground='white')
        self.home_name_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.home_name_entry.insert(0, self.home_name)
        self.home_name_entry.bind('<KeyRelease>', lambda e: self.update_team_name_live('home'))

        away_team_frame = tk.Frame(team_frame, bg='#2a2a2a')
        away_team_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(away_team_frame, text="Away:", font=('Helvetica', 11),
                bg='#2a2a2a', fg='white', width=6, anchor='w').pack(side='left')
        self.away_name_entry = tk.Entry(away_team_frame, font=('Helvetica', 14),
                                        bg='#333333', fg='white', relief='flat', insertbackground='white')
        self.away_name_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.away_name_entry.insert(0, self.away_name)
        self.away_name_entry.bind('<KeyRelease>', lambda e: self.update_team_name_live('away'))

        # Timer
        timer_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        timer_frame.pack(fill='x', pady=(0, 15), padx=5, ipady=10)

        timer_header = tk.Frame(timer_frame, bg='#2a2a2a')
        timer_header.pack(fill='x', padx=10, pady=(5, 0))
        tk.Label(timer_header, text="Timer", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left')
        tk.Button(timer_header, text="⚙", font=('Helvetica', 10), bg='#555555', fg='white',
                 relief='flat', padx=8, pady=2, command=self.show_timer_settings).pack(side='right')



        self.timer_display_label = tk.Label(timer_frame,
                text=f"{self.timer_seconds//60:02d}:{self.timer_seconds%60:02d}",
                font=('Helvetica', 28, 'bold'), bg='#2a2a2a', fg='#00ff00')
        self.timer_display_label.pack(pady=(2, 5))

        timer_btns = tk.Frame(timer_frame, bg='#2a2a2a')
        timer_btns.pack(pady=(0, 5))
        tk.Button(timer_btns, text="▶ Start", font=('Helvetica', 13, 'bold'),
                 bg='#00aa00', fg='white', relief='flat', padx=20, pady=10,
                 command=self.start_timer).pack(side='left', padx=5)
        tk.Button(timer_btns, text="⏸ Pause", font=('Helvetica', 13, 'bold'),
                 bg='#ffaa00', fg='white', relief='flat', padx=20, pady=10,
                 command=self.pause_timer).pack(side='left', padx=5)
        tk.Button(timer_btns, text="↻ Reset", font=('Helvetica', 13, 'bold'),
                 bg='#cc0000', fg='white', relief='flat', padx=20, pady=10,
                 command=self.reset_timer).pack(side='left', padx=5)

        # Scores
        score_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        score_frame.pack(fill='x', pady=(0, 15), padx=5, ipady=15)
        score_header = tk.Frame(score_frame, bg='#2a2a2a')
        score_header.pack(fill='x', padx=10, pady=(5, 0))
        tk.Label(score_header, text="SCORES", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left')
        tk.Button(score_header, text="↻", font=('Helvetica', 14, 'bold'),
                 bg='#ff3333', fg='white', relief='flat', width=3,
                 command=self.reset_scores).pack(side='right')

        is_basketball = (self.current_sport == "Basketball")

        home_score_frame = tk.Frame(score_frame, bg='#2a2a2a')
        home_score_frame.pack(pady=10)
        self.score_home_name_lbl = tk.Label(home_score_frame, text=self.home_name[:8], font=('Helvetica', 11),
                bg='#2a2a2a', fg='#00ff00', width=8)
        self.score_home_name_lbl.pack(side='left', padx=5)
        tk.Button(home_score_frame, text="−", font=('Helvetica', 20, 'bold'), bg='#ff3333', fg='white',
                 relief='flat', width=3, command=lambda: self.adjust_score('home', -1)).pack(side='left', padx=5)
        self.home_score_entry = tk.Entry(home_score_frame, font=('Helvetica', 32, 'bold'),
                                         bg='#1a1a1a', fg='white', width=4, relief='sunken', bd=2,
                                         justify='center', insertbackground='white')
        self.home_score_entry.pack(side='left', padx=10)
        self.home_score_entry.insert(0, str(self.home_score))
        self.home_score_entry.bind('<KeyRelease>', lambda e: self.update_score_live('home'))
        self.home_score_entry.bind('<FocusOut>', lambda e: self.validate_score('home'))
        if is_basketball:
            tk.Button(home_score_frame, text="+1", font=('Helvetica', 14, 'bold'), bg='#007700', fg='white',
                     relief='flat', width=3, command=lambda: self.adjust_score('home', 1)).pack(side='left', padx=2)
            tk.Button(home_score_frame, text="+2", font=('Helvetica', 14, 'bold'), bg='#009900', fg='white',
                     relief='flat', width=3, command=lambda: self.adjust_score('home', 2)).pack(side='left', padx=2)
            tk.Button(home_score_frame, text="+3", font=('Helvetica', 14, 'bold'), bg='#00bb00', fg='white',
                     relief='flat', width=3, command=lambda: self.adjust_score('home', 3)).pack(side='left', padx=2)
        else:
            tk.Button(home_score_frame, text="+", font=('Helvetica', 20, 'bold'), bg='#00aa00', fg='white',
                     relief='flat', width=3, command=lambda: self.adjust_score('home', 1)).pack(side='left', padx=5)

        away_score_frame = tk.Frame(score_frame, bg='#2a2a2a')
        away_score_frame.pack(pady=10)
        self.score_away_name_lbl = tk.Label(away_score_frame, text=self.away_name[:8], font=('Helvetica', 11),
                bg='#2a2a2a', fg='#ffaa00', width=8)
        self.score_away_name_lbl.pack(side='left', padx=5)
        tk.Button(away_score_frame, text="−", font=('Helvetica', 20, 'bold'), bg='#ff3333', fg='white',
                 relief='flat', width=3, command=lambda: self.adjust_score('away', -1)).pack(side='left', padx=5)
        self.away_score_entry = tk.Entry(away_score_frame, font=('Helvetica', 32, 'bold'),
                                         bg='#1a1a1a', fg='white', width=4, relief='sunken', bd=2,
                                         justify='center', insertbackground='white')
        self.away_score_entry.pack(side='left', padx=10)
        self.away_score_entry.insert(0, str(self.away_score))
        self.away_score_entry.bind('<KeyRelease>', lambda e: self.update_score_live('away'))
        self.away_score_entry.bind('<FocusOut>', lambda e: self.validate_score('away'))
        if is_basketball:
            tk.Button(away_score_frame, text="+1", font=('Helvetica', 14, 'bold'), bg='#775500', fg='white',
                     relief='flat', width=3, command=lambda: self.adjust_score('away', 1)).pack(side='left', padx=2)
            tk.Button(away_score_frame, text="+2", font=('Helvetica', 14, 'bold'), bg='#997700', fg='white',
                     relief='flat', width=3, command=lambda: self.adjust_score('away', 2)).pack(side='left', padx=2)
            tk.Button(away_score_frame, text="+3", font=('Helvetica', 14, 'bold'), bg='#bb9900', fg='white',
                     relief='flat', width=3, command=lambda: self.adjust_score('away', 3)).pack(side='left', padx=2)
        else:
            tk.Button(away_score_frame, text="+", font=('Helvetica', 20, 'bold'), bg='#00aa00', fg='white',
                     relief='flat', width=3, command=lambda: self.adjust_score('away', 1)).pack(side='left', padx=5)

        # Basketball-specific: Timeouts, Fouls, Shot Clock
        if self.current_sport == "Basketball":
            # Timeouts
            tout_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
            tout_frame.pack(fill='x', pady=(0, 10), padx=5, ipady=8)
            tout_header_row = tk.Frame(tout_frame, bg='#2a2a2a')
            tout_header_row.pack(fill='x', padx=10, pady=(5, 8))
            tk.Label(tout_header_row, text="TIMEOUTS", font=('Helvetica', 12, 'bold'),
                    bg='#2a2a2a', fg='#ffaa00').pack(side='left')
            tk.Button(tout_header_row, text="↻", font=('Helvetica', 11), bg='#555555', fg='white',
                     relief='flat', width=2, command=self.reset_bball_timeouts).pack(side='right')
            tout_row = tk.Frame(tout_frame, bg='#2a2a2a')
            tout_row.pack()

            home_tout = tk.Frame(tout_row, bg='#2a2a2a')
            home_tout.pack(side='left', padx=20)
            tk.Label(home_tout, text=self.home_name[:8], font=('Helvetica', 10, 'bold'),
                    bg='#2a2a2a', fg='#00ff00').pack()
            tout_home_ctrl = tk.Frame(home_tout, bg='#2a2a2a')
            tout_home_ctrl.pack()
            tk.Button(tout_home_ctrl, text="−", font=('Helvetica', 14, 'bold'), bg='#cc0000', fg='white',
                     relief='flat', width=2, command=lambda: self._adj_bball('home_timeouts', -1, home_tout_lbl)).pack(side='left', padx=2)
            home_tout_lbl = tk.Label(tout_home_ctrl, text=str(self.home_timeouts), font=('Helvetica', 18, 'bold'),
                                    bg='#2a2a2a', fg='white', width=3)
            home_tout_lbl.pack(side='left')
            self.home_tout_lbl = home_tout_lbl
            tk.Button(tout_home_ctrl, text="+", font=('Helvetica', 14, 'bold'), bg='#007700', fg='white',
                     relief='flat', width=2, command=lambda: self._adj_bball('home_timeouts', 1, home_tout_lbl)).pack(side='left', padx=2)

            away_tout = tk.Frame(tout_row, bg='#2a2a2a')
            away_tout.pack(side='left', padx=20)
            tk.Label(away_tout, text=self.away_name[:8], font=('Helvetica', 10, 'bold'),
                    bg='#2a2a2a', fg='#ffaa00').pack()
            tout_away_ctrl = tk.Frame(away_tout, bg='#2a2a2a')
            tout_away_ctrl.pack()
            tk.Button(tout_away_ctrl, text="−", font=('Helvetica', 14, 'bold'), bg='#cc0000', fg='white',
                     relief='flat', width=2, command=lambda: self._adj_bball('away_timeouts', -1, away_tout_lbl)).pack(side='left', padx=2)
            away_tout_lbl = tk.Label(tout_away_ctrl, text=str(self.away_timeouts), font=('Helvetica', 18, 'bold'),
                                    bg='#2a2a2a', fg='white', width=3)
            away_tout_lbl.pack(side='left')
            self.away_tout_lbl = away_tout_lbl
            tk.Button(tout_away_ctrl, text="+", font=('Helvetica', 14, 'bold'), bg='#007700', fg='white',
                     relief='flat', width=2, command=lambda: self._adj_bball('away_timeouts', 1, away_tout_lbl)).pack(side='left', padx=2)

            # Fouls
            foul_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
            foul_frame.pack(fill='x', pady=(0, 10), padx=5, ipady=8)
            foul_header_row = tk.Frame(foul_frame, bg='#2a2a2a')
            foul_header_row.pack(fill='x', padx=10, pady=(5, 8))
            tk.Label(foul_header_row, text="FOULS", font=('Helvetica', 12, 'bold'),
                    bg='#2a2a2a', fg='#ff6600').pack(side='left')
            tk.Button(foul_header_row, text="↻", font=('Helvetica', 11), bg='#555555', fg='white',
                     relief='flat', width=2, command=self.reset_bball_fouls).pack(side='right')
            foul_row = tk.Frame(foul_frame, bg='#2a2a2a')
            foul_row.pack()

            home_foul = tk.Frame(foul_row, bg='#2a2a2a')
            home_foul.pack(side='left', padx=20)
            tk.Label(home_foul, text=self.home_name[:8], font=('Helvetica', 10, 'bold'),
                    bg='#2a2a2a', fg='#00ff00').pack()
            foul_home_ctrl = tk.Frame(home_foul, bg='#2a2a2a')
            foul_home_ctrl.pack()
            tk.Button(foul_home_ctrl, text="−", font=('Helvetica', 14, 'bold'), bg='#cc0000', fg='white',
                     relief='flat', width=2, command=lambda: self._adj_bball('home_fouls', -1, home_foul_lbl)).pack(side='left', padx=2)
            home_foul_lbl = tk.Label(foul_home_ctrl, text=str(self.home_fouls), font=('Helvetica', 18, 'bold'),
                                    bg='#2a2a2a', fg='white', width=3)
            home_foul_lbl.pack(side='left')
            self.home_foul_lbl = home_foul_lbl
            tk.Button(foul_home_ctrl, text="+", font=('Helvetica', 14, 'bold'), bg='#007700', fg='white',
                     relief='flat', width=2, command=lambda: self._adj_bball('home_fouls', 1, home_foul_lbl)).pack(side='left', padx=2)

            away_foul = tk.Frame(foul_row, bg='#2a2a2a')
            away_foul.pack(side='left', padx=20)
            tk.Label(away_foul, text=self.away_name[:8], font=('Helvetica', 10, 'bold'),
                    bg='#2a2a2a', fg='#ffaa00').pack()
            foul_away_ctrl = tk.Frame(away_foul, bg='#2a2a2a')
            foul_away_ctrl.pack()
            tk.Button(foul_away_ctrl, text="−", font=('Helvetica', 14, 'bold'), bg='#cc0000', fg='white',
                     relief='flat', width=2, command=lambda: self._adj_bball('away_fouls', -1, away_foul_lbl)).pack(side='left', padx=2)
            away_foul_lbl = tk.Label(foul_away_ctrl, text=str(self.away_fouls), font=('Helvetica', 18, 'bold'),
                                    bg='#2a2a2a', fg='white', width=3)
            away_foul_lbl.pack(side='left')
            self.away_foul_lbl = away_foul_lbl
            tk.Button(foul_away_ctrl, text="+", font=('Helvetica', 14, 'bold'), bg='#007700', fg='white',
                     relief='flat', width=2, command=lambda: self._adj_bball('away_fouls', 1, away_foul_lbl)).pack(side='left', padx=2)

        # Basketball / Hockey: Shot Clock
        if self.current_sport in ("Basketball", "Hockey"):
            sc_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
            sc_frame.pack(fill='x', pady=(0, 10), padx=5, ipady=8)
            sc_header = tk.Frame(sc_frame, bg='#2a2a2a')
            sc_header.pack(fill='x', padx=10, pady=(5, 0))
            tk.Label(sc_header, text="Shot Clock", font=('Helvetica', 12, 'bold'),
                    bg='#2a2a2a', fg='#00aaff').pack(side='left')
            tk.Button(sc_header, text="⚙", font=('Helvetica', 10), bg='#555555', fg='white',
                     relief='flat', padx=8, pady=2, command=self.show_shot_clock_settings).pack(side='right')
            self.shot_clock_display_label = tk.Label(sc_frame, text=str(self.shot_clock_seconds),
                    font=('Helvetica', 36, 'bold'), bg='#2a2a2a', fg='#ff6600')
            self.shot_clock_display_label.pack(pady=(2, 5))
            sc_btns = tk.Frame(sc_frame, bg='#2a2a2a')
            sc_btns.pack(pady=(0, 5))
            if self.current_sport == 'Hockey':
                # Hockey: Start (appear) and Stop (reset + disappear) only
                tk.Button(sc_btns, text="▶ Start", font=('Helvetica', 12, 'bold'), bg='#00aa00', fg='white',
                         relief='flat', padx=18, pady=8,
                         command=self.start_shot_clock).pack(side='left', padx=6)
                tk.Button(sc_btns, text="■ Stop", font=('Helvetica', 12, 'bold'), bg='#cc0000', fg='white',
                         relief='flat', padx=18, pady=8,
                         command=self.stop_shot_clock_with_blank).pack(side='left', padx=6)
            else:
                # Basketball: Start, Stop (reset + disappear), Reset (restart immediately)
                tk.Button(sc_btns, text="▶ Start", font=('Helvetica', 12, 'bold'), bg='#00aa00', fg='white',
                         relief='flat', padx=12, pady=8,
                         command=self.start_shot_clock).pack(side='left', padx=4)
                tk.Button(sc_btns, text="■ Stop", font=('Helvetica', 12, 'bold'), bg='#cc0000', fg='white',
                         relief='flat', padx=12, pady=8,
                         command=self.stop_shot_clock_with_blank).pack(side='left', padx=4)
                tk.Button(sc_btns, text="↺ Reset", font=('Helvetica', 12, 'bold'), bg='#ff8800', fg='white',
                         relief='flat', padx=12, pady=8,
                         command=self.reset_shot_clock_and_start).pack(side='left', padx=4)

        # Rugby-specific: scoring by type
        if self.current_sport == "Rugby":
            rug_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
            rug_frame.pack(fill='x', pady=(0, 10), padx=5, ipady=8)
            tk.Label(rug_frame, text="SCORE BY TYPE", font=('Helvetica', 12, 'bold'),
                    bg='#2a2a2a', fg='#ffaa00').pack(pady=(5, 8))
            for label, points in [("Try", 5), ("Conversion", 2), ("Penalty", 3), ("Drop Goal", 3)]:
                row = tk.Frame(rug_frame, bg='#2a2a2a')
                row.pack(fill='x', padx=10, pady=3)
                tk.Label(row, text=f"{label} (+{points})", font=('Helvetica', 11),
                        bg='#2a2a2a', fg='white', width=16, anchor='w').pack(side='left')
                tk.Button(row, text=self.home_name[:6], font=('Helvetica', 10, 'bold'),
                         bg='#006600', fg='white', relief='flat', padx=8, pady=4,
                         command=lambda p=points: self.adjust_score('home', p)).pack(side='left', padx=3)
                tk.Button(row, text=self.away_name[:6], font=('Helvetica', 10, 'bold'),
                         bg='#884400', fg='white', relief='flat', padx=8, pady=4,
                         command=lambda p=points: self.adjust_score('away', p)).pack(side='left', padx=3)

        # Advertisements
        ads_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        ads_frame.pack(fill='x', pady=(15, 5), padx=5)
        self._build_ads_panel(ads_frame, self.return_to_scores)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Send initial data to display
        program_num = self.sport_programs[self.current_sport]
        self.send_udp_command(f"*#1PRGC3{program_num},0000")
        self.root.after(150, self.resend_all_data)

    def _adj_bball(self, attr, delta, label):
        """Adjust a basketball counter (timeouts/fouls), update UI label and send via CNTS."""
        current = getattr(self, attr, 0)
        new_val = max(0, current + delta)
        setattr(self, attr, new_val)
        label.config(text=str(new_val))
        # Send to dedicated CNTS slots so display always reflects current value
        cnts_map = {
            'home_timeouts': 3,
            'away_timeouts': 4,
            'home_fouls':    5,
            'away_fouls':    6,
        }
        if attr in cnts_map:
            slot = cnts_map[attr]
            self.send_udp_command(f"*#1CNTS{slot},S{new_val},0000")
        self.save_config()

    def reset_bball_timeouts(self):
        """Reset both teams' timeouts to 0"""
        self.home_timeouts = 0
        self.away_timeouts = 0
        if hasattr(self, 'home_tout_lbl'):
            self.home_tout_lbl.config(text='0')
        if hasattr(self, 'away_tout_lbl'):
            self.away_tout_lbl.config(text='0')
        self.send_udp_command("*#1CNTS3,S0,0000")
        self.send_udp_command("*#1CNTS4,S0,0000")
        self.save_config()

    def reset_bball_fouls(self):
        """Reset both teams' fouls to 0"""
        self.home_fouls = 0
        self.away_fouls = 0
        if hasattr(self, 'home_foul_lbl'):
            self.home_foul_lbl.config(text='0')
        if hasattr(self, 'away_foul_lbl'):
            self.away_foul_lbl.config(text='0')
        self.send_udp_command("*#1CNTS5,S0,0000")
        self.send_udp_command("*#1CNTS6,S0,0000")
        self.save_config()

    def show_coming_soon(self):
        """Show coming soon screen for sports not yet implemented"""
        for widget in self.root.winfo_children():
            widget.destroy()
        
        main_frame = tk.Frame(self.root, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Top bar with back button
        top_bar = tk.Frame(main_frame, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 30))
        
        tk.Button(top_bar, text="← Controller", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 activebackground='#555555', activeforeground='white',
                 command=self.create_home_screen).pack(side='left', anchor='w')
        
        tk.Label(main_frame, text=f"{self.current_sport}",
                font=('Helvetica', 24, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=(50, 20))
        
        tk.Label(main_frame, text="Coming Soon!",
                font=('Helvetica', 20),
                bg='#1a1a1a', fg='#ffaa00').pack(pady=20)
    
    # ── Timer engine ──────────────────────────────────────────────────────────
    def start_timer(self):
        """Start game timer (Python-side, sends RAMT5–7 every second)."""
        if not self.timer_running:
            self.timer_running = True
            self._timer_tick()

    def pause_timer(self):
        """Pause game timer."""
        self.timer_running = False
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

    def reset_timer(self):
        """Reset game timer to initial value."""
        self.timer_running = False
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None
        self.timer_seconds = self.timer_target_seconds if self.timer_countdown else 0
        self._send_timer_display()

    def _timer_tick(self):
        if not self.timer_running:
            return
        if self.timer_countdown:
            if self.timer_seconds > 0:
                self.timer_seconds -= 1
            else:
                self.timer_running = False
                self._send_timer_display()
                return
        else:
            self.timer_seconds += 1
        self._send_timer_display()
        self.timer_job = self.root.after(1000, self._timer_tick)

    # ─────────────────────────────────────────────────────────────────────────
    # Shared display-style settings helper
    # ─────────────────────────────────────────────────────────────────────────
    def _build_display_settings(self, win, color_var, size_var, h_var, v_var, on_change,
                                show_h_align=True):
        """Add colour / size / alignment rows to a settings Toplevel popup.
        on_change() is called immediately when any control changes (live preview).
        show_h_align=False hides the H-Align row (used for multi-slot text like team names
        where h-align is always forced to Left and cannot be meaningfully changed)."""
        COLOR_OPTIONS = [
            ('R', '1', '#ff4444'), ('G', '2', '#44ff44'), ('Y', '3', '#ffff33'),
            ('B', '4', '#4488ff'), ('M', '5', '#ff44ff'), ('C', '6', '#44ffff'),
            ('W', '7', '#ffffff'),
        ]
        SIZE_OPTIONS  = [('S', '1'), ('M', '2'), ('L', '3'), ('XL', '4')]
        H_OPTIONS     = [('Center', '1'), ('Right', '2'), ('Left', '3')]
        V_OPTIONS     = [('Top', '1'), ('Mid', '2'), ('Bot', '3')]

        # Colour row
        cf = tk.Frame(win, bg='#1a1a1a')
        cf.pack(fill='x', padx=20, pady=(4, 2))
        tk.Label(cf, text="Colour:", font=('Helvetica', 10), bg='#1a1a1a',
                 fg='#aaaaaa', width=7, anchor='w').pack(side='left')
        for lbl, val, hex_c in COLOR_OPTIONS:
            tk.Radiobutton(cf, text=lbl, variable=color_var, value=val,
                           font=('Helvetica', 9, 'bold'), bg='#1a1a1a', fg=hex_c,
                           selectcolor='#333333', indicatoron=False, width=3,
                           activebackground='#1a1a1a', activeforeground=hex_c,
                           relief='flat', command=on_change).pack(side='left', padx=1)

        # Size row
        sf = tk.Frame(win, bg='#1a1a1a')
        sf.pack(fill='x', padx=20, pady=2)
        tk.Label(sf, text="Size:", font=('Helvetica', 10), bg='#1a1a1a',
                 fg='#aaaaaa', width=7, anchor='w').pack(side='left')
        for lbl, val in SIZE_OPTIONS:
            tk.Radiobutton(sf, text=lbl, variable=size_var, value=val,
                           font=('Helvetica', 9), bg='#1a1a1a', fg='white',
                           selectcolor='#333333', indicatoron=False, width=4,
                           activebackground='#1a1a1a', activeforeground='white',
                           relief='flat', command=on_change).pack(side='left', padx=2)

        # H-Align row — hidden for multi-slot text (team names) where Left is always forced
        if show_h_align:
            hf = tk.Frame(win, bg='#1a1a1a')
            hf.pack(fill='x', padx=20, pady=2)
            tk.Label(hf, text="H-Align:", font=('Helvetica', 10), bg='#1a1a1a',
                     fg='#aaaaaa', width=7, anchor='w').pack(side='left')
            for lbl, val in H_OPTIONS:
                tk.Radiobutton(hf, text=lbl, variable=h_var, value=val,
                               font=('Helvetica', 9), bg='#1a1a1a', fg='white',
                               selectcolor='#333333', indicatoron=False, width=7,
                               activebackground='#1a1a1a', activeforeground='white',
                               relief='flat', command=on_change).pack(side='left', padx=2)

        # V-Align row
        vf = tk.Frame(win, bg='#1a1a1a')
        vf.pack(fill='x', padx=20, pady=(2, 4))
        tk.Label(vf, text="V-Align:", font=('Helvetica', 10), bg='#1a1a1a',
                 fg='#aaaaaa', width=7, anchor='w').pack(side='left')
        for lbl, val in V_OPTIONS:
            tk.Radiobutton(vf, text=lbl, variable=v_var, value=val,
                           font=('Helvetica', 9), bg='#1a1a1a', fg='white',
                           selectcolor='#333333', indicatoron=False, width=7,
                           activebackground='#1a1a1a', activeforeground='white',
                           relief='flat', command=on_change).pack(side='left', padx=2)

    def show_timer_settings(self):
        """Popup to configure timer mode, start time, and display style."""
        win = tk.Toplevel(self.root)
        win.title("Timer Settings")
        win.configure(bg='#1a1a1a')
        win.geometry("390x420")
        win.grab_set()

        tk.Label(win, text="Timer Settings", font=('Helvetica', 15, 'bold'),
                 bg='#1a1a1a', fg='white').pack(pady=(14, 8))

        # Count-up / count-down
        mode_var = tk.StringVar(value='countdown' if self.timer_countdown else 'countup')
        mode_frame = tk.Frame(win, bg='#1a1a1a')
        mode_frame.pack(fill='x', padx=20, pady=(0, 4))
        for lbl, val in [("Count Up", "countup"), ("Count Down", "countdown")]:
            tk.Radiobutton(mode_frame, text=lbl, variable=mode_var, value=val,
                           bg='#1a1a1a', fg='white', selectcolor='#333',
                           font=('Helvetica', 11), activebackground='#1a1a1a',
                           activeforeground='white').pack(side='left', padx=12)

        # Start time
        time_frame = tk.Frame(win, bg='#1a1a1a')
        time_frame.pack(pady=4)
        tk.Label(time_frame, text="Start time (MM:SS):", font=('Helvetica', 11),
                 bg='#1a1a1a', fg='white').pack(side='left', padx=(20, 6))
        init_mins = self.timer_target_seconds // 60
        init_secs = self.timer_target_seconds % 60
        mins_var = tk.StringVar(value=f"{init_mins:02d}")
        secs_var = tk.StringVar(value=f"{init_secs:02d}")
        tk.Entry(time_frame, textvariable=mins_var, width=3, font=('Helvetica', 13),
                 bg='#333', fg='white', insertbackground='white', justify='center').pack(side='left')
        tk.Label(time_frame, text=":", font=('Helvetica', 13, 'bold'),
                 bg='#1a1a1a', fg='white').pack(side='left')
        tk.Entry(time_frame, textvariable=secs_var, width=3, font=('Helvetica', 13),
                 bg='#333', fg='white', insertbackground='white', justify='center').pack(side='left')

        # Display style section
        tk.Frame(win, bg='#444444', height=1).pack(fill='x', padx=16, pady=(8, 4))
        tk.Label(win, text="Display Style  (updates live)", font=('Helvetica', 10, 'bold'),
                 bg='#1a1a1a', fg='#aaaaaa').pack(anchor='w', padx=20)

        color_var = tk.StringVar(value=getattr(self, 'timer_color',   '7'))
        size_var  = tk.StringVar(value=getattr(self, 'timer_size',    '2'))
        h_var     = tk.StringVar(value=getattr(self, 'timer_h_align', '3'))
        v_var     = tk.StringVar(value=getattr(self, 'timer_v_align', '1'))

        def on_live():
            self.timer_color   = color_var.get()
            self.timer_size    = size_var.get()
            self.timer_h_align = h_var.get()
            self.timer_v_align = v_var.get()
            self._send_timer_display()

        self._build_display_settings(win, color_var, size_var, h_var, v_var, on_live)

        # Leading spaces (shifts timer right on hardware display)
        is_afl = getattr(self, 'current_sport', None) == 'AFL'
        offset_attr = 'timer_offset_afl' if is_afl else 'timer_offset_default'
        sp_frame = tk.Frame(win, bg='#1a1a1a')
        sp_frame.pack(fill='x', padx=20, pady=(2, 4))
        tk.Label(sp_frame, text="Offset:", font=('Helvetica', 10), bg='#1a1a1a',
                 fg='#aaaaaa', width=7, anchor='w').pack(side='left')
        spaces_var = tk.IntVar(value=getattr(self, offset_attr, 1 if is_afl else 0))

        def _update_spaces(delta):
            new_val = max(0, min(10, spaces_var.get() + delta))
            spaces_var.set(new_val)
            setattr(self, offset_attr, new_val)
            self._send_timer_display()

        tk.Button(sp_frame, text="◀", font=('Helvetica', 10), bg='#444', fg='white',
                  relief='flat', width=3, command=lambda: _update_spaces(-1)).pack(side='left', padx=(0, 4))
        tk.Label(sp_frame, textvariable=spaces_var, font=('Helvetica', 11, 'bold'),
                 bg='#1a1a1a', fg='white', width=3).pack(side='left')
        tk.Button(sp_frame, text="▶", font=('Helvetica', 10), bg='#444', fg='white',
                  relief='flat', width=3, command=lambda: _update_spaces(1)).pack(side='left', padx=(4, 8))
        tk.Label(sp_frame, text="spaces before timer", font=('Helvetica', 9),
                 bg='#1a1a1a', fg='#666666').pack(side='left')

        def apply():
            try:
                m = int(mins_var.get()); s = int(secs_var.get())
                total = m * 60 + s
            except ValueError:
                total = 0
            self.timer_countdown = (mode_var.get() == 'countdown')
            self.timer_target_seconds = total
            on_live()
            self.reset_timer()
            self.save_config()
            win.destroy()

        tk.Button(win, text="Apply & Close", font=('Helvetica', 12, 'bold'),
                  bg='#0066cc', fg='white', relief='flat', padx=20, pady=8,
                  command=apply).pack(pady=10)

    # ── Shot clock engine ─────────────────────────────────────────────────────
    def start_shot_clock(self):
        """Start (or resume) the shot clock; display appears immediately."""
        if not self.shot_clock_running:
            self.shot_clock_running = True
            self._send_shot_clock_display()   # show value immediately
            self.shot_clock_job = self.root.after(1000, self._shot_clock_tick)

    def stop_shot_clock_with_blank(self):
        """Stop clock, reset to target, blank the display (used for Stop on Hockey & Basketball)."""
        self.shot_clock_running = False
        if self.shot_clock_job:
            self.root.after_cancel(self.shot_clock_job)
            self.shot_clock_job = None
        self.shot_clock_seconds = self.shot_clock_target
        # Force display blank by temporarily zeroing seconds, then restore
        self.shot_clock_seconds = 0
        self._send_shot_clock_display()   # sends blank
        self.shot_clock_seconds = self.shot_clock_target  # restore ready for next Start

    def reset_shot_clock_and_start(self):
        """Basketball Reset: reset to target and immediately start counting down."""
        self.shot_clock_running = False
        if self.shot_clock_job:
            self.root.after_cancel(self.shot_clock_job)
            self.shot_clock_job = None
        self.shot_clock_seconds = self.shot_clock_target
        self.shot_clock_running = True
        self._send_shot_clock_display()   # show target immediately
        self.shot_clock_job = self.root.after(1000, self._shot_clock_tick)

    def reset_shot_clock(self):
        """Internal reset (used by settings apply)."""
        self.shot_clock_running = False
        if self.shot_clock_job:
            self.root.after_cancel(self.shot_clock_job)
            self.shot_clock_job = None
        self.shot_clock_seconds = self.shot_clock_target
        self._send_shot_clock_display()

    def _shot_clock_tick(self):
        if not self.shot_clock_running:
            return
        if self.shot_clock_seconds > 0:
            self.shot_clock_seconds -= 1
            self._send_shot_clock_display()
            self.shot_clock_job = self.root.after(1000, self._shot_clock_tick)
        else:
            self.shot_clock_running = False
            # Display blanks for 10 s then keep blank
            self._blank_shot_clock_for(10)

    def _blank_shot_clock_for(self, remaining=10):
        """Send blank to shot clock RAMT slots, repeat for `remaining` seconds."""
        self._send_shot_clock_display()   # sends blank because seconds == 0
        if remaining > 1:
            self.root.after(1000, lambda: self._blank_shot_clock_for(remaining - 1))

    def show_shot_clock_settings(self):
        """Popup to set shot clock reset value and display style."""
        win = tk.Toplevel(self.root)
        win.title("Shot Clock Settings")
        win.configure(bg='#1a1a1a')
        win.geometry("390x340")
        win.grab_set()

        tk.Label(win, text="Shot Clock Settings", font=('Helvetica', 15, 'bold'),
                 bg='#1a1a1a', fg='white').pack(pady=(14, 8))

        row = tk.Frame(win, bg='#1a1a1a')
        row.pack(pady=4)
        tk.Label(row, text="Reset value (seconds):", font=('Helvetica', 11),
                 bg='#1a1a1a', fg='white').pack(side='left', padx=(20, 6))
        sec_var = tk.StringVar(value=str(self.shot_clock_target))
        tk.Entry(row, textvariable=sec_var, width=4, font=('Helvetica', 13),
                 bg='#333', fg='white', insertbackground='white', justify='center').pack(side='left')

        tk.Frame(win, bg='#444444', height=1).pack(fill='x', padx=16, pady=(8, 4))
        tk.Label(win, text="Display Style  (updates live)", font=('Helvetica', 10, 'bold'),
                 bg='#1a1a1a', fg='#aaaaaa').pack(anchor='w', padx=20)

        color_var = tk.StringVar(value=getattr(self, 'shot_clock_color',   '7'))
        size_var  = tk.StringVar(value=getattr(self, 'shot_clock_size',    '2'))
        h_var     = tk.StringVar(value=getattr(self, 'shot_clock_h_align', '1'))
        v_var     = tk.StringVar(value=getattr(self, 'shot_clock_v_align', '1'))

        def on_live():
            self.shot_clock_color   = color_var.get()
            self.shot_clock_size    = size_var.get()
            self.shot_clock_h_align = h_var.get()
            self.shot_clock_v_align = v_var.get()
            self._send_shot_clock_display()

        self._build_display_settings(win, color_var, size_var, h_var, v_var, on_live)

        def apply():
            try:
                val = int(sec_var.get())
                self.shot_clock_target = max(1, val)
            except ValueError:
                pass
            on_live()
            self.reset_shot_clock()
            self.save_config()
            win.destroy()

        tk.Button(win, text="Apply & Close", font=('Helvetica', 12, 'bold'),
                  bg='#0066cc', fg='white', relief='flat', padx=20, pady=8,
                  command=apply).pack(pady=10)

    def show_afl_quarter_settings(self):
        """Popup to configure AFL quarter display style on RAMT8."""
        win = tk.Toplevel(self.root)
        win.title("Quarter Display Settings")
        win.configure(bg='#1a1a1a')
        win.geometry("390x280")
        win.grab_set()

        tk.Label(win, text="Quarter Display Style", font=('Helvetica', 15, 'bold'),
                 bg='#1a1a1a', fg='white').pack(pady=(14, 8))
        tk.Label(win, text="(updates live on display)", font=('Helvetica', 10),
                 bg='#1a1a1a', fg='#888888').pack()

        color_var = tk.StringVar(value=getattr(self, 'afl_quarter_color',   '7'))
        size_var  = tk.StringVar(value=getattr(self, 'afl_quarter_size',    '2'))
        h_var     = tk.StringVar(value=getattr(self, 'afl_quarter_h_align', '1'))
        v_var     = tk.StringVar(value=getattr(self, 'afl_quarter_v_align', '1'))

        def on_live():
            self.afl_quarter_color   = color_var.get()
            self.afl_quarter_size    = size_var.get()
            self.afl_quarter_h_align = h_var.get()
            self.afl_quarter_v_align = v_var.get()
            self._send_afl_quarter()

        self._build_display_settings(win, color_var, size_var, h_var, v_var, on_live)

        def apply():
            on_live()
            self.save_config()
            win.destroy()

        tk.Button(win, text="Apply & Close", font=('Helvetica', 12, 'bold'),
                  bg='#0066cc', fg='white', relief='flat', padx=20, pady=8,
                  command=apply).pack(pady=10)

    # Team name functions
    def _refresh_score_name_labels(self, team):
        """Update all score-section name labels that reference home/away name."""
        if team == 'home':
            name = self.home_name[:8]
            for attr in ('score_home_name_lbl', 'afl_score_home_lbl', 'cricket_score_home_lbl'):
                lbl = getattr(self, attr, None)
                if lbl:
                    try:
                        lbl.config(text=name)
                    except Exception:
                        pass
        else:
            name = self.away_name[:8]
            for attr in ('score_away_name_lbl', 'afl_score_away_lbl', 'cricket_score_away_lbl'):
                lbl = getattr(self, attr, None)
                if lbl:
                    try:
                        lbl.config(text=name)
                    except Exception:
                        pass

    def update_team_name_live(self, team):
        """Update team name live as user types (with debouncing)"""
        # Cancel any pending update
        if hasattr(self, f'{team}_update_timer'):
            timer = getattr(self, f'{team}_update_timer')
            if timer:
                self.root.after_cancel(timer)
        
        # Schedule update after 300ms of no typing
        timer = self.root.after(300, lambda: self.update_team_name(team))
        setattr(self, f'{team}_update_timer', timer)
    
    def update_team_name(self, team):
        """Update team name from entry widget"""
        if team == 'home':
            new_name = self.home_name_entry.get().strip()
            if new_name:
                self.home_name = new_name
                self.send_team_name_update('home')
                self._refresh_score_name_labels('home')
                self.save_config()
                print(f"[INFO] Home team updated to: {self.home_name}")
        else:
            new_name = self.away_name_entry.get().strip()
            if new_name:
                self.away_name = new_name
                self.send_team_name_update('away')
                self._refresh_score_name_labels('away')
                self.save_config()
                print(f"[INFO] Away team updated to: {self.away_name}")
    
    def send_team_name_update(self, team):
        """Send team name update, splitting across RAMT slots 1-3 (home) or 4-6 (away)."""
        color = self.team_settings['color']
        size = self.team_settings['size']
        h_align = self.team_settings.get('h_align', '1')
        v_align = self.team_settings.get('v_align', '2')
        if team == 'home':
            self.send_name_ramt(self.home_name, 1, color, size, h_align, v_align)
        else:
            self.send_name_ramt(self.away_name, 3, color, size, h_align, v_align)
    
    # Score functions
    def update_score_live(self, team):
        """Update score live as user types (with debouncing)"""
        # Cancel any pending update
        if hasattr(self, f'{team}_score_update_timer'):
            timer = getattr(self, f'{team}_score_update_timer')
            if timer:
                self.root.after_cancel(timer)
        
        # Schedule update after 500ms of no typing
        timer = self.root.after(500, lambda: self.validate_score(team))
        setattr(self, f'{team}_score_update_timer', timer)
    
    def validate_score(self, team):
        """Validate and send score from entry field"""
        if team == 'home':
            try:
                new_score = int(self.home_score_entry.get())
                if new_score < 0:
                    new_score = 0
                self.home_score = new_score
                self.home_score_entry.delete(0, tk.END)
                self.home_score_entry.insert(0, str(self.home_score))
                
                # Send set command
                self.send_udp_command(f"*#1CNTS1,S{self.home_score},0000")
                self.save_config()
                print(f"[INFO] Home score set to: {self.home_score}")
            except ValueError:
                # Invalid input, restore previous value
                self.home_score_entry.delete(0, tk.END)
                self.home_score_entry.insert(0, str(self.home_score))
        else:
            try:
                new_score = int(self.away_score_entry.get())
                if new_score < 0:
                    new_score = 0
                self.away_score = new_score
                self.away_score_entry.delete(0, tk.END)
                self.away_score_entry.insert(0, str(self.away_score))
                
                # Send set command
                self.send_udp_command(f"*#1CNTS2,S{self.away_score},0000")
                self.save_config()
                print(f"[INFO] Away score set to: {self.away_score}")
            except ValueError:
                # Invalid input, restore previous value
                self.away_score_entry.delete(0, tk.END)
                self.away_score_entry.insert(0, str(self.away_score))
    
    def adjust_score(self, team, delta):
        """Adjust score by delta"""
        if team == 'home':
            self.home_score = max(0, self.home_score + delta)
            self.home_score_entry.delete(0, tk.END)
            self.home_score_entry.insert(0, str(self.home_score))

            if delta > 0:
                self.send_udp_command(f"*#1CNTS1,A{delta},0000")
            else:
                self.send_udp_command(f"*#1CNTS1,D{abs(delta)},0000")

            print(f"[INFO] Home score: {self.home_score}")
        else:
            self.away_score = max(0, self.away_score + delta)
            self.away_score_entry.delete(0, tk.END)
            self.away_score_entry.insert(0, str(self.away_score))

            if delta > 0:
                self.send_udp_command(f"*#1CNTS2,A{delta},0000")
            else:
                self.send_udp_command(f"*#1CNTS2,D{abs(delta)},0000")

            print(f"[INFO] Away score: {self.away_score}")
        
        self.save_config()
    
    def reset_scores(self):
        """Reset all scores to 0"""
        self.home_score = 0
        self.away_score = 0
        self.home_score_entry.delete(0, tk.END)
        self.home_score_entry.insert(0, '0')
        self.away_score_entry.delete(0, tk.END)
        self.away_score_entry.insert(0, '0')
        self.send_udp_command("*#1CNTS1,S0,0000")
        self.send_udp_command("*#1CNTS2,S0,0000")
        self.save_config()
        print("[INFO] Scores reset to 0")
    

    def show_add_advertisement(self):
        """Open the advertisement creator (delegates to unified text editor)."""
        self.show_text_editor(mode='ad')

    def remove_advertisement(self, index):
        """Remove advertisement at index and persist."""
        if 0 <= index < len(self.advertisements):
            self.advertisements.pop(index)
            self.current_ad_index = max(0, min(self.current_ad_index, len(self.advertisements) - 1))
            self.save_config()

    # ── Advertisement panel (shared across all sport screens) ─────────────────
    def _build_ads_panel(self, parent_frame, return_cmd):
        """Build the advertisements panel with a live checklist, play loop, and new-ad button.
        Selections and durations are persisted in self.ad_selections keyed by ad name."""
        BG = '#2a2a2a'
        ITEM_BG = '#1e1e1e'

        tk.Label(parent_frame, text="Advertisements", font=('Helvetica', 13, 'bold'),
                 bg=BG, fg='white').pack(pady=(10, 4))

        # ── List area ─────────────────────────────────────────────────────────
        list_frame = tk.Frame(parent_frame, bg=BG)
        list_frame.pack(fill='x', padx=10, pady=(0, 4))

        ad_checks = []   # BooleanVar per ad
        dur_vars  = []   # StringVar for duration (seconds)

        def _save_selections():
            """Persist current checkbox + duration state keyed by ad name."""
            for i, (chk, dv) in enumerate(zip(ad_checks, dur_vars)):
                if i < len(self.advertisements):
                    key = self.advertisements[i].get('name', '') or f"Ad {i+1}"
                    self.ad_selections[key] = {
                        'selected': chk.get(),
                        'duration': dv.get(),
                    }
            self.save_config()

        def rebuild_list():
            for w in list_frame.winfo_children():
                w.destroy()
            ad_checks.clear()
            dur_vars.clear()

            if not self.advertisements:
                tk.Label(list_frame, text="No advertisements saved yet  —  create one below",
                         font=('Helvetica', 10), bg=BG, fg='#666666').pack(pady=10)
                return

            for i, ad in enumerate(self.advertisements):
                key = ad.get('name', '') or f"Ad {i+1}"
                saved = self.ad_selections.get(key, {})

                item = tk.Frame(list_frame, bg=ITEM_BG, relief='ridge', bd=1)
                item.pack(fill='x', pady=2)

                # Checkbox — restore saved selection
                chk = tk.BooleanVar(value=saved.get('selected', False))
                ad_checks.append(chk)
                tk.Checkbutton(item, variable=chk, bg=ITEM_BG,
                               activebackground=ITEM_BG, selectcolor='#0055cc',
                               command=_save_selections).pack(side='left', padx=(6, 2))

                # Name label
                label_text = key[:24]
                tk.Label(item, text=label_text, font=('Helvetica', 10), bg=ITEM_BG,
                         fg='white', anchor='w').pack(side='left', fill='x', expand=True)

                # Duration entry — restore saved duration, default 4s
                dur = tk.StringVar(value=saved.get('duration', '4'))
                dur_vars.append(dur)
                dur_entry = tk.Entry(item, textvariable=dur, width=3, font=('Helvetica', 10),
                         bg='#333333', fg='white', insertbackground='white',
                         justify='center')
                dur_entry.pack(side='left', padx=(4, 1))
                dur_entry.bind('<FocusOut>', lambda e: _save_selections())
                tk.Label(item, text="s", font=('Helvetica', 9), bg=ITEM_BG,
                         fg='#888888').pack(side='left', padx=(0, 4))

                # Edit button
                tk.Button(item, text="✎", font=('Helvetica', 9), bg='#004488', fg='white',
                          relief='flat', padx=6,
                          command=lambda idx=i: self.show_text_editor(mode='ad', edit_index=idx)
                          ).pack(side='left', padx=(0, 2))

                # Delete button — with confirmation
                def _delete(idx, _rebuild=rebuild_list):
                    ad_name = (self.advertisements[idx].get('name', '') or f"Ad {idx+1}")[:30]
                    if not messagebox.askyesno("Delete Advertisement",
                            f"Delete \"{ad_name}\"?\nThis cannot be undone.",
                            parent=self.root):
                        return
                    # Remove persisted selection for this ad
                    self.ad_selections.pop(
                        self.advertisements[idx].get('name', '') or f"Ad {idx+1}", None)
                    self.remove_advertisement(idx)
                    _rebuild()
                tk.Button(item, text="✕", font=('Helvetica', 9), bg='#880000', fg='white',
                          relief='flat', padx=6,
                          command=lambda idx=i: _delete(idx)
                          ).pack(side='left', padx=(0, 6))

        rebuild_list()

        # ── Action row: Play Selected + Return to Scores ──────────────────────
        action = tk.Frame(parent_frame, bg=BG)
        action.pack(fill='x', padx=10, pady=(4, 2))

        def play_selected():
            _save_selections()
            playlist = []
            for i, (chk, dv) in enumerate(zip(ad_checks, dur_vars)):
                if chk.get() and i < len(self.advertisements):
                    try:
                        secs = max(1, int(dv.get()))
                    except ValueError:
                        secs = 4
                    playlist.append((self.advertisements[i], secs * 1000))
            if playlist:
                self.start_ad_loop(playlist)

        tk.Button(action, text="▶  Play Selected", font=('Helvetica', 11, 'bold'),
                  bg='#007700', fg='white', relief='flat', pady=8,
                  command=play_selected).pack(side='left', fill='x', expand=True, padx=(0, 3))

        tk.Button(action, text="↩  Return to Scores", font=('Helvetica', 11, 'bold'),
                  bg='#005599', fg='white', relief='flat', pady=8,
                  command=lambda: [self.stop_ad_loop(), return_cmd()]
                  ).pack(side='left', fill='x', expand=True)

        # ── New Advertisement button ──────────────────────────────────────────
        tk.Button(parent_frame, text="＋  New Advertisement", font=('Helvetica', 11, 'bold'),
                  bg='#550088', fg='white', relief='flat', pady=8,
                  command=self.show_add_advertisement
                  ).pack(fill='x', padx=10, pady=(5, 10))

    # ── Ad loop engine ────────────────────────────────────────────────────────
    def start_ad_loop(self, playlist):
        """Start looping through a playlist of (ad_dict, duration_ms) pairs."""
        self.stop_ad_loop()
        self.ad_loop_active   = True
        self.ad_loop_playlist = playlist
        self.ad_loop_idx      = 0
        self._ad_loop_next()

    def _ad_loop_next(self):
        if not self.ad_loop_active or not self.ad_loop_playlist:
            return
        ad, duration_ms = self.ad_loop_playlist[self.ad_loop_idx]
        self._play_advertisement(ad)
        # Single ad: play once and leave it on — no cycling timer
        if len(self.ad_loop_playlist) == 1:
            self.ad_loop_job = None
            return
        self.ad_loop_idx = (self.ad_loop_idx + 1) % len(self.ad_loop_playlist)
        self.ad_loop_job = self.root.after(duration_ms, self._ad_loop_next)

    def stop_ad_loop(self):
        """Cancel any running ad loop."""
        self.ad_loop_active = False
        if self.ad_loop_job:
            self.root.after_cancel(self.ad_loop_job)
            self.ad_loop_job = None

    def return_to_scores(self):
        """Return to scores screen"""
        # Stop any scrolling text
        self.stop_scrolling_text()
        
        program_num = self.sport_programs[self.current_sport]
        self.send_udp_command(f"*#1PRGC3{program_num},0000")
        
        # Resend all current data
        self.root.after(100, self.resend_all_data)
        print("[INFO] Returned to scores screen")
    
    def resend_all_data(self):
        """Resend all current scores and names"""
        # Send scores
        self.send_udp_command(f"*#1CNTS1,S{self.home_score},0000")
        self.send_udp_command(f"*#1CNTS2,S{self.away_score},0000")

        # Basketball: resend timeouts and fouls via CNTS
        if getattr(self, 'current_sport', None) == 'Basketball':
            self.send_udp_command(f"*#1CNTS3,S{getattr(self, 'home_timeouts', 0)},0000")
            self.send_udp_command(f"*#1CNTS4,S{getattr(self, 'away_timeouts', 0)},0000")
            self.send_udp_command(f"*#1CNTS5,S{getattr(self, 'home_fouls', 0)},0000")
            self.send_udp_command(f"*#1CNTS6,S{getattr(self, 'away_fouls', 0)},0000")

        # Send team names — use sport-specific settings so all RAMT boxes
        # receive the same v_align that the settings popup configured
        sport = getattr(self, 'current_sport', None)
        if sport == 'AFL':
            c = getattr(self, 'afl_team_color',   '1')
            s = getattr(self, 'afl_team_size',    '2')
            v = getattr(self, 'afl_team_v_align', '2')
            self.send_name_ramt(getattr(self, 'afl_home_name', self.home_name), 1, c, s, '3', v)
            self.send_name_ramt(getattr(self, 'afl_away_name', self.away_name), 3, c, s, '3', v)
        elif sport == 'Cricket':
            c = getattr(self, 'cricket_team_color',   '1')
            s = getattr(self, 'cricket_team_size',    '2')
            v = getattr(self, 'cricket_team_v_align', '2')
            self.send_name_ramt(getattr(self, 'cricket_home_name', self.home_name), 1, c, s, '3', v)
            self.send_name_ramt(getattr(self, 'cricket_away_name', self.away_name), 3, c, s, '3', v)
        else:
            c = self.team_settings['color']
            s = self.team_settings['size']
            v = self.team_settings.get('v_align', '2')
            self.send_name_ramt(self.home_name, 1, c, s, '3', v)
            self.send_name_ramt(self.away_name, 3, c, s, '3', v)

        # Resend timer at current size so program load doesn't revert to hardware default
        self._send_timer_display()


    # ── RAMT name helpers ─────────────────────────────────────────────────────
    def send_name_ramt(self, name, start_slot, color, size, h_align='3', v_align='2'):
        """Split name into chunks and send each chunk to successive RAMT slots.
        Chunk sizes: XL(4)=1, L(3)=2, M(2)=4, S(1)=7.
        Home: start_slot=1 → RAMT1,2.  Away: start_slot=3 → RAMT3,4.
        h_align ALWAYS forced '3' (Left) — multi-slot text must flow left-to-right.
        v_align ALWAYS sourced from the current sport's authoritative settings,
        regardless of what the caller passes — this guarantees all 4 team-name
        RAMT boxes (RAMT1, RAMT2, RAMT3, RAMT4) always share identical v_align."""
        # Authoritative v_align — ignore caller value to prevent any mismatch
        sport = getattr(self, 'current_sport', None)
        if sport == 'AFL':
            v_align = getattr(self, 'afl_team_v_align', '2')
        elif sport == 'Cricket':
            v_align = getattr(self, 'cricket_team_v_align', '2')
        else:
            v_align = self.team_settings.get('v_align', '2')

        chunk_size = {'4': 1, '3': 2, '2': 4, '1': 7, '9': 10}.get(size, 4)
        chunks = [name[i:i+chunk_size] for i in range(0, max(len(name), 1), chunk_size)]
        # Pad/trim to exactly 2 slots; blank unused slot so stale text doesn't linger
        while len(chunks) < 2:
            chunks.append('')
        for i, chunk in enumerate(chunks[:2]):
            # Pad chunk to exactly chunk_size chars so hardware renders consistently
            padded = chunk.ljust(chunk_size)
            slot = start_slot + i
            cmd = f"*#1RAMT{slot},{color}{size}3{v_align}{padded}0000"
            self.send_udp_command(cmd)

    def _send_timer_display(self):
        """Chunk MM:SS across RAMT5–7 using the same size-based logic as team names.
        chunk_size: XL(4)=1, L(3)=2, M(2)=4, S(1)=7.
        e.g. at M(4 chars/slot): '12:35' → RAMT5='12:3', RAMT6='5   ', RAMT7='    '
             at L(2 chars/slot): '12:35' → RAMT5='12', RAMT6=':3', RAMT7='5 '
        AFL: right-aligned (h='2'); other sports: left-aligned (h='3')."""
        mins = self.timer_seconds // 60
        secs = self.timer_seconds % 60
        c = getattr(self, 'timer_color',   '7')
        s = getattr(self, 'timer_size',    '2')
        h = '3'   # always left
        v = getattr(self, 'timer_v_align', '1')
        if getattr(self, 'current_sport', None) == 'AFL':
            leading = ' ' * getattr(self, 'timer_offset_afl', 1)
        else:
            leading = ' ' * getattr(self, 'timer_offset_default', 0)
        text = f"{leading}{mins:02d}:{secs:02d}"
        chunk_size = {'4': 1, '3': 2, '2': 4, '1': 7, '9': 10}.get(s, 4)
        chunks = [text[i:i+chunk_size] for i in range(0, max(len(text), 1), chunk_size)]
        # Pad/trim to exactly 3 slots (RAMT5, RAMT6, RAMT7)
        while len(chunks) < 3:
            chunks.append('')
        for i, chunk in enumerate(chunks[:3]):
            padded = chunk.ljust(chunk_size)
            self.send_udp_command(f"*#1RAMT{5 + i},{c}{s}{h}{v}{padded}0000")
        if hasattr(self, 'timer_display_label'):
            try:
                self.timer_display_label.config(text=text)
            except Exception:
                pass

    def _send_shot_clock_display(self):
        """Show shot clock in a single RAMT slot: RAMT8=full value.
        Sends blank when at zero (display clears instead of showing 0)."""
        secs = self.shot_clock_seconds
        c = getattr(self, 'shot_clock_color',   '7')
        s = getattr(self, 'shot_clock_size',    '2')
        # Shot clock always left-aligned
        h = '3'
        v = getattr(self, 'shot_clock_v_align', '1')
        if secs == 0:
            # Blank slot — stays blank until reset
            self.send_udp_command(f"*#1RAMT8,{c}{s}{h}{v} 0000")
            if hasattr(self, 'shot_clock_display_label'):
                try:
                    self.shot_clock_display_label.config(text='  ')
                except Exception:
                    pass
        else:
            self.send_udp_command(f"*#1RAMT8,{c}{s}{h}{v}{secs}0000")
            if hasattr(self, 'shot_clock_display_label'):
                try:
                    self.shot_clock_display_label.config(text=str(secs))
                except Exception:
                    pass

    def _send_afl_quarter(self):
        """Push current AFL quarter (Q1–Q4) to RAMT8, or blank if Off (quarter=0)."""
        c = getattr(self, 'afl_quarter_color',   '7')
        s = getattr(self, 'afl_quarter_size',    '2')
        h = '3'   # left
        v = getattr(self, 'afl_quarter_v_align', '1')
        q = getattr(self, 'afl_quarter', 1)
        if q == 0:
            self.send_udp_command(f"*#1RAMT8,{c}{s}{h}{v} 0000")
            display = "Off"
        else:
            display = f"Q{q}"
            self.send_udp_command(f"*#1RAMT8,{c}{s}{h}{v}{display}0000")
        if hasattr(self, 'afl_quarter_label'):
            try:
                self.afl_quarter_label.config(text=display)
            except Exception:
                pass

    def back_to_home(self):
        """Return to home screen"""
        self.root.geometry("400x700")
        self.save_config()

        # Stop ads and scrolling
        self.stop_ad_loop()
        self.stop_scrolling_text()
        
        # Send command to return to page 0 (home screen)
        self.send_udp_command("*#1PRGC30,0000")
        
        # Send blank screen command
        self.root.after(120, lambda: self.send_udp_command("*#1RAMT1,1211 0000"))
        
        # Recreate home screen
        self.create_home_screen()
        
        # Force reconnection check if not connected
        if not self.connected:
            self.test_connection()

    def reset_to_defaults(self):
        """Wipe all user settings and restore factory defaults."""
        confirmed = messagebox.askyesno(
            "Reset All Settings",
            "This will erase ALL saved settings including:\n\n"
            "• Sport selection\n"
            "• Team names and scores\n"
            "• Timer and display settings\n"
            "• Advertisements\n"
            "• All other user changes\n\n"
            "Are you sure you want to reset to defaults?",
            icon='warning',
            parent=self.root
        )
        if not confirmed:
            return

        # Delete config file
        import os
        config_path = os.path.expanduser("~/scoreboard_config.json")
        try:
            if os.path.exists(config_path):
                os.remove(config_path)
        except Exception:
            pass

        # Reset all settings to defaults
        self.current_sport        = None
        self.home_name            = "HOME"
        self.away_name            = "AWAY"
        self.home_score           = 0
        self.away_score           = 0
        self.team_settings        = {"color": "1", "size": "2", "h_align": "1", "v_align": "2"}
        self.home_screen_settings = {"color": "7", "size": "2"}
        self.advertisements       = []
        self.current_ad_index     = 0
        self.ad_selections        = {}
        # Timer
        self.timer_seconds        = 0
        self.timer_target_seconds = 0
        self.timer_countdown      = False
        self.timer_color          = '7'
        self.timer_size           = '2'
        self.timer_v_align        = '1'
        self.timer_offset_afl     = 1
        self.timer_offset_default = 0
        # AFL
        self.afl_team_color       = '1'
        self.afl_team_size        = '2'
        self.afl_team_h_align     = '3'
        self.afl_team_v_align     = '2'
        self.afl_home_name        = 'HOME'
        self.afl_away_name        = 'AWAY'
        self.afl_quarter          = 1
        self.afl_quarter_color    = '7'
        self.afl_quarter_size     = '2'
        self.afl_quarter_h_align  = '3'
        self.afl_quarter_v_align  = '1'
        # Cricket
        self.cricket_team_color   = '1'
        self.cricket_team_size    = '2'
        self.cricket_team_h_align = '3'
        self.cricket_team_v_align = '2'
        self.cricket_home_name    = 'HOME'
        self.cricket_away_name    = 'AWAY'
        # Shot clock
        self.shot_clock_seconds   = 24
        self.shot_clock_color     = '7'
        self.shot_clock_size      = '2'
        self.shot_clock_v_align   = '1'

        self.save_config()
        self.create_home_screen()
        messagebox.showinfo("Reset Complete", "All settings have been reset to defaults.", parent=self.root)

    def show_team_name_settings(self):
        """Popup to configure team name display style (colour, size, v-align).
        Used by Soccer, Rugby, Hockey, Basketball — same style as AFL/Cricket popups.
        H-align is always Left (forced in send_name_ramt) so it is not shown."""
        win = tk.Toplevel(self.root)
        win.title("Team Name Settings")
        win.configure(bg='#1a1a1a')
        win.geometry("390x270")
        win.grab_set()

        tk.Label(win, text="Team Name Style", font=('Helvetica', 15, 'bold'),
                 bg='#1a1a1a', fg='white').pack(pady=(14, 4))
        tk.Label(win, text="(updates live on display)", font=('Helvetica', 10),
                 bg='#1a1a1a', fg='#888888').pack()

        color_var = tk.StringVar(value=self.team_settings.get('color', '1'))
        size_var  = tk.StringVar(value=self.team_settings.get('size',  '2'))
        h_var     = tk.StringVar(value='3')   # always Left — not shown in UI
        v_var     = tk.StringVar(value=self.team_settings.get('v_align', '2'))

        def on_live():
            self.team_settings['color']   = color_var.get()
            self.team_settings['size']    = size_var.get()
            self.team_settings['v_align'] = v_var.get()
            self.send_team_name_update('home')
            self.send_team_name_update('away')

        self._build_display_settings(win, color_var, size_var, h_var, v_var, on_live,
                                     show_h_align=False)

        def apply():
            on_live()
            self.save_config()
            win.destroy()

        tk.Button(win, text="Apply & Close", font=('Helvetica', 12, 'bold'),
                  bg='#0066cc', fg='white', relief='flat', padx=20, pady=8,
                  command=apply).pack(pady=10)

    def show_text_editor(self, mode='text', edit_index=None):
        """
        Unified editor used for both the home text editor and advertisement creator/editor.
        mode='text': home text editor (Apply / Blank buttons, back → home)
        mode='ad':   advertisement editor (Save / Preview buttons, back → sport UI)
        edit_index:  index into self.advertisements to pre-fill (ad mode only)
        """
        is_ad = (mode == 'ad')
        self.root.geometry("420x800")
        for widget in self.root.winfo_children():
            widget.destroy()

        main = tk.Frame(self.root, bg='#0f0f0f')
        main.pack(fill='both', expand=True)

        # ── TOP BAR ──────────────────────────────────────────────────────────
        topbar = tk.Frame(main, bg='#1a1a1a', height=50)
        topbar.pack(fill='x')
        topbar.pack_propagate(False)

        if is_ad:
            back_cmd = self.show_current_sport_ui
            title_text = ("Edit Ad" if edit_index is not None else "New Advertisement")
        else:
            back_cmd = lambda: [self.root.geometry("400x700"), self.create_home_screen()]
            title_text = "Text Editor"

        tk.Button(topbar, text="← Back", font=('Helvetica', 10, 'bold'),
                 bg='#2a2a2a', fg='white', relief='flat', padx=15, pady=6,
                 command=back_cmd).pack(side='left', padx=10, pady=8)
        tk.Label(topbar, text=title_text, font=('Helvetica', 14, 'bold'),
                bg='#1a1a1a', fg='white').pack(side='left')
        if not is_ad:
            tk.Button(topbar, text=f"⚙{self.display_width}×{self.display_height}",
                     font=('Helvetica', 9), bg='#2a2a2a', fg='#00aaff', relief='flat',
                     padx=10, pady=6, command=self.show_display_setup).pack(side='right', padx=10, pady=8)

        # ── CANVAS ───────────────────────────────────────────────────────────
        canvas_frame = tk.Frame(main, bg='#0f0f0f')
        canvas_frame.pack(fill='x', padx=10, pady=(5, 0))

        canvas_width = 380
        canvas_height = int(canvas_width * (self.display_height / self.display_width))

        canvas = tk.Canvas(canvas_frame, width=canvas_width, height=canvas_height,
                          bg='black', highlightthickness=2, highlightbackground='#333333')
        canvas.pack()

        info_frame = tk.Frame(canvas_frame, bg='#0f0f0f')
        info_frame.pack(fill='x', pady=(3, 0))
        tk.Label(info_frame, text=f"{self.display_width}×{self.display_height}",
                font=('Helvetica', 8), bg='#0f0f0f', fg='#555555').pack(side='left')
        char_label = tk.Label(info_frame, text="", font=('Helvetica', 9, 'bold'),
                             bg='#0f0f0f', fg='#00ff00')
        char_label.pack(side='right')

        # ── CONTROLS ─────────────────────────────────────────────────────────
        controls = tk.Frame(main, bg='#1a1a1a')
        controls.pack(fill='both', expand=True, padx=10, pady=(5, 10))

        # ── CHAR LIMITS — scale with display width (baseline 128 px) ─────────
        _ws = self.display_width / 128
        CHAR_LIMITS = {
            "4": max(1, round(5  * _ws)),   # XL
            "3": max(1, round(7  * _ws)),   # L
            "2": max(1, round(15 * _ws)),   # M
        }

        # ── PRECOMPUTE ARIAL FONT SIZES for each size × num_rows ─────────────
        # For every combination, find the largest pt that fits char_limit chars
        # horizontally AND fits inside one zone vertically.
        _font_size_cache = {}
        for _sz in ('4', '3', '2'):
            for _nr in range(1, 5):
                _zone_h   = canvas_height / _nr
                _cl       = CHAR_LIMITS[_sz]
                _target_w = (canvas_width - 4) / _cl   # px per char
                _best = 6
                for _pt in range(80, 4, -1):
                    _f = tkfont.Font(family='Arial', size=_pt, weight='bold')
                    if (_f.measure('M') <= _target_w and
                            _f.metrics('linespace') <= _zone_h - 2):
                        _best = _pt
                        break
                _font_size_cache[(_sz, _nr)] = _best

        def get_font_size(size):
            return _font_size_cache.get((size, num_rows[0]), 10)

        # ── STATE ─────────────────────────────────────────────────────────────
        # Load from existing ad or set fresh defaults
        if is_ad and edit_index is not None and 0 <= edit_index < len(self.advertisements):
            existing = self.advertisements[edit_index]
            if 'rows' in existing:
                saved_rows = [dict(r) for r in existing['rows']]
            else:
                saved_rows = [{'text': existing.get('text', ''),
                                'color': existing.get('colour', existing.get('color', '1')),
                                'size': existing.get('size', '3'),
                                'h_align': existing.get('h_align', '1'),
                                'v_align': existing.get('v_align', '2'),
                                'scroll': existing.get('scroll', False),
                                'scroll_speed': existing.get('scroll_speed', 700)}]
            init_name = existing.get('name', '')
            init_border = existing.get('border', False)
            init_num_rows = max(1, min(4, len(saved_rows)))
        else:
            saved_rows = []
            init_name = ""
            init_border = False
            init_num_rows = 1

        # Always keep exactly 4 slots internally; trim/pad as needed
        _blank_row = lambda: {"text": "", "color": "1", "size": "3",
                               "h_align": "1", "v_align": "2", "scroll": False, "scroll_speed": 700}
        while len(saved_rows) < 4:
            saved_rows.append(_blank_row())

        text_data    = [r.get('text', '') for r in saved_rows]   # list of 4 strings
        row_settings = saved_rows[:4]                             # list of 4 dicts
        num_rows     = [init_num_rows]   # how many rows the user has added (1-4)
        border_on    = [init_border]
        selected_row = [0]

        color_map = {
            "1": "#ff0000", "2": "#00ff00", "3": "#ffff00", "4": "#0000ff",
            "5": "#ff00ff", "6": "#00ffff", "7": "#ffffff"
        }

        # ── ANIMATION STATE ───────────────────────────────────────────────────
        border_offset     = [0]     # clockwise stripe offset in px
        border_anim_job   = [None]
        _snake_mode         = ['off']        # mirrors snake_var; set after UI built
        _scroll_type        = ['multi']      # 'multi' = snake, 'single' = per-row
        preview_scroll_pos  = [0]            # multi-row snake position
        preview_row_scroll_pos = [0, 0, 0, 0]  # per-row positions for single mode
        preview_scroll_job  = [None]

        # ── HELPERS ───────────────────────────────────────────────────────────
        def draw_chars_evenly(display_text, y, size, h_align, color, font_sz):
            """Draw each character in its own equal-width slot so text fills the full line."""
            limit = CHAR_LIMITS[size]
            slot_w = canvas_width / limit
            n_chars = len(display_text)
            # Starting x depends on alignment
            if h_align == "2":     # right — last char ends at right edge
                x_base = canvas_width - n_chars * slot_w
            elif h_align == "3":   # left — first char at left edge
                x_base = 0.0
            else:                  # center
                x_base = (canvas_width - n_chars * slot_w) / 2
            for ci, ch in enumerate(display_text):
                cx = x_base + ci * slot_w + slot_w / 2
                canvas.create_text(cx, y, text=ch, fill=color,
                                  font=('Arial', font_sz, 'bold'), anchor='center')

        def draw_striped_border(offset=0, bw=4, slen=10):
            """Draw animated clockwise red/green/yellow stripe border."""
            stripe_colors = ['#cc0000', '#00aa00', '#cccc00']
            # Compute total perimeter length
            perimeter = 2 * (canvas_width + canvas_height)
            def color_at(dist):
                idx = ((dist + offset) // slen) % 3
                return stripe_colors[int(idx)]
            # Walk clockwise: top → right → bottom(RTL) → left(BTT)
            segments = []
            d = 0
            # Top: left→right
            x = 0
            while x < canvas_width:
                xe = min(x + slen, canvas_width)
                segments.append(('top', x, xe, d))
                d += xe - x; x = xe
            # Right: top→bottom
            y = 0
            while y < canvas_height:
                ye = min(y + slen, canvas_height)
                segments.append(('right', y, ye, d))
                d += ye - y; y = ye
            # Bottom: right→left
            x = canvas_width
            while x > 0:
                xe = max(x - slen, 0)
                segments.append(('bot', xe, x, d))
                d += x - xe; x = xe
            # Left: bottom→top
            y = canvas_height
            while y > 0:
                ye = max(y - slen, 0)
                segments.append(('left', ye, y, d))
                d += y - ye; y = ye
            for seg in segments:
                c = color_at(seg[3])
                if seg[0] == 'top':
                    canvas.create_rectangle(seg[1], 0, seg[2], bw, fill=c, outline='')
                elif seg[0] == 'right':
                    canvas.create_rectangle(canvas_width - bw, seg[1], canvas_width, seg[2], fill=c, outline='')
                elif seg[0] == 'bot':
                    canvas.create_rectangle(seg[1], canvas_height - bw, seg[2], canvas_height, fill=c, outline='')
                else:
                    canvas.create_rectangle(0, seg[1], bw, seg[2], fill=c, outline='')

        def border_tick():
            try:
                if not canvas.winfo_exists(): return
            except Exception: return
            if not border_on[0]:
                border_anim_job[0] = None; return
            border_offset[0] = (border_offset[0] - 2) % 60
            update_preview()
            border_anim_job[0] = self.root.after(60, border_tick)

        def preview_scroll_tick():
            try:
                if not canvas.winfo_exists(): return
            except Exception: return
            if _snake_mode[0] == 'off':
                preview_scroll_job[0] = None; return
            if _scroll_type[0] == 'single':
                for _j in range(num_rows[0]):
                    preview_row_scroll_pos[_j] += 1
            else:
                preview_scroll_pos[0] += 1
            update_preview()
            speed_map = {"slow": 1200, "med": 900, "fast": 600}
            ms = speed_map.get(_snake_mode[0], 900)
            preview_scroll_job[0] = self.root.after(ms, preview_scroll_tick)

        def start_preview_scroll():
            if preview_scroll_job[0]: return   # already running
            preview_scroll_pos[0] = 0
            preview_scroll_tick()

        def stop_preview_scroll():
            if preview_scroll_job[0]:
                self.root.after_cancel(preview_scroll_job[0])
                preview_scroll_job[0] = None

        def _bypass_print_commands():
            """Print would-be commands to console when in bypass mode."""
            if not (getattr(self, 'bypass_connection', None)
                    and self.bypass_connection.get()):
                return
            prog_base = {1: 7, 2: 9, 3: 11, 4: 13}.get(num_rows[0], 7)
            prog = prog_base + (1 if border_on[0] else 0)
            print(f"[BYPASS] *#1PRGC3{prog},0000")
            if _snake_mode[0] != 'off':
                if _scroll_type[0] == 'single':
                    print(f"[BYPASS]   SINGLE-LINE SCROLL {_snake_mode[0].upper()} — each row scrolls independently")
                else:
                    print(f"[BYPASS]   MULTI-ROW SCROLL {_snake_mode[0].upper()} — all rows scroll together")
                return
            for i in range(num_rows[0]):
                text = text_data[i]; settings = row_settings[i]; ramt = i + 1
                if not text.strip():
                    continue
                if settings.get("scroll", False):
                    sp_k = {500:"slow",700:"med",900:"fast"}.get(settings.get("scroll_speed",700),"med")
                    print(f"[BYPASS]   RAMT{ramt}: [SCROLL {sp_k}] {text}")
                else:
                    cmd = (f"*#1RAMT{ramt},{settings['color']}{settings.get('size','3')}"
                           f"{settings['h_align']}{settings.get('v_align','2')}{text}0000")
                    print(f"[BYPASS]   {cmd}")

        def update_preview():
            canvas.delete("all")
            n = num_rows[0]
            zone_h = canvas_height / n

            # Zone dividers
            for z in range(1, n):
                canvas.create_line(0, z * zone_h, canvas_width, z * zone_h,
                                  fill='#333333', width=1, dash=(4, 4))

            # ── Scroll preview simulation ──────────────────────────────────────
            if _snake_mode[0] != 'off' and any(text_data[i].strip() for i in range(n)):
                prog_base = {1: 7, 2: 9, 3: 11, 4: 13}.get(n, 7)
                prog = prog_base + (1 if border_on[0] else 0)
                print(f"[SCROLL] *#1PRGC3{prog},0000")

                if _scroll_type[0] == 'single':
                    # ── Single-line: each row scrolls its own text independently ──
                    for i in range(n):
                        settings    = row_settings[i]
                        size        = settings.get('size', '3')
                        font_sz     = get_font_size(size)
                        limit       = CHAR_LIMITS[size]
                        color       = color_map.get(settings["color"], "#ffffff")
                        h_align     = settings.get("h_align", "1")
                        v_align     = settings.get("v_align", "2")
                        zone_top    = i * zone_h
                        zone_bottom = (i + 1) * zone_h
                        half = font_sz / 2 + 1
                        min_y = zone_top + half; max_y = zone_bottom - half
                        if v_align == "3": y = max_y
                        elif v_align == "2": y = (zone_top + zone_bottom) / 2
                        else: y = min_y
                        y = max(min_y, min(y, max_y))
                        if i == selected_row[0]:
                            canvas.create_rectangle(0, zone_top+1, canvas_width, zone_bottom-1,
                                                   fill='#1a3a5a', outline='')
                        raw = text_data[i]
                        if raw.strip():
                            padded = raw.strip() + '   '
                            flen   = len(padded)
                            pos    = preview_row_scroll_pos[i] % max(1, flen)
                            doubled = padded * 2
                            window = doubled[pos: pos + limit].ljust(limit)[:limit]
                            draw_chars_evenly(window, y, size, h_align, color, font_sz)
                            ramt = i + 1
                            cmd = (f"*#1RAMT{ramt},{settings['color']}{size}"
                                   f"{h_align}{v_align}{window}0000")
                            print(f"[SCROLL]   {cmd}")
                else:
                    # ── Multi-row snake: all rows share one flowing string ─────
                    parts = [text_data[i].strip() for i in range(n)]
                    joined = '   '.join(p for p in parts if p)
                    total_chars = sum(CHAR_LIMITS[row_settings[i].get('size','3')] for i in range(n))
                    full_str = joined + ' ' * max(4, total_chars - len(joined))
                    doubled  = full_str * 2
                    flen     = len(full_str)
                    pos    = preview_scroll_pos[0] % flen
                    offset = 0
                    for i in range(n):
                        settings    = row_settings[i]
                        size        = settings.get('size', '3')
                        font_sz     = get_font_size(size)
                        limit       = CHAR_LIMITS[size]
                        color       = color_map.get(settings["color"], "#ffffff")
                        h_align     = settings.get("h_align", "1")
                        v_align     = settings.get("v_align", "2")
                        zone_top    = i * zone_h
                        zone_bottom = (i + 1) * zone_h
                        half = font_sz / 2 + 1
                        min_y = zone_top + half; max_y = zone_bottom - half
                        if v_align == "3": y = max_y
                        elif v_align == "2": y = (zone_top + zone_bottom) / 2
                        else: y = min_y
                        y = max(min_y, min(y, max_y))
                        if i == selected_row[0]:
                            canvas.create_rectangle(0, zone_top+1, canvas_width, zone_bottom-1,
                                                   fill='#1a3a5a', outline='')
                        start  = (pos + offset) % flen
                        window = doubled[start: start + limit].ljust(limit)[:limit]
                        draw_chars_evenly(window, y, size, h_align, color, font_sz)
                        ramt = i + 1
                        cmd = (f"*#1RAMT{ramt},{settings['color']}{size}"
                               f"{h_align}{v_align}{window}0000")
                        print(f"[SCROLL]   {cmd}")
                        offset += limit
            else:
                # ── Normal (static) render ────────────────────────────────────
                for i in range(n):
                    text     = text_data[i]
                    settings = row_settings[i]
                    size     = settings.get('size', '3')
                    font_sz  = get_font_size(size)
                    color    = color_map.get(settings["color"], "#ffffff")
                    h_align  = settings.get("h_align", "1")
                    v_align  = settings.get("v_align", "2")
                    zone_top    = i * zone_h
                    zone_bottom = (i + 1) * zone_h
                    half = font_sz / 2 + 1
                    min_y = zone_top + half; max_y = zone_bottom - half
                    if i == selected_row[0]:
                        canvas.create_rectangle(0, zone_top+1, canvas_width, zone_bottom-1,
                                               fill='#1a3a5a', outline='')
                    if v_align == "3": y = max_y
                    elif v_align == "2": y = (zone_top + zone_bottom) / 2
                    else: y = min_y
                    y = max(min_y, min(y, max_y))

                    display_text  = text[:CHAR_LIMITS[size]]
                    display_color = color
                    if i == selected_row[0] and not text:
                        display_text  = '─' * CHAR_LIMITS[size]
                        display_color = "#333333"
                    if display_text:
                        draw_chars_evenly(display_text, y, size, h_align, display_color, font_sz)

            # Striped animated border (drawn last, on top of text)
            if border_on[0]:
                draw_striped_border(border_offset[0])

            # Char counter
            size = row_settings[selected_row[0]].get('size', '3')
            limit = CHAR_LIMITS[size]
            current_len = len(text_data[selected_row[0]])
            remaining = limit - current_len
            if remaining < 0:
                char_label.config(text=f"⚠{abs(remaining)}!", fg='#ff0000')
            elif remaining <= 1:
                char_label.config(text=f"{current_len}/{limit}", fg='#ffaa00')
            else:
                char_label.config(text=f"{current_len}/{limit}", fg='#00ff00')
            # Bypass console output
            _bypass_print_commands()

        def on_key(event):
            size = row_settings[selected_row[0]].get('size', '3')
            limit = CHAR_LIMITS[size]
            current = text_data[selected_row[0]]
            if event.keysym == 'BackSpace':
                if current:
                    text_data[selected_row[0]] = current[:-1]
            elif event.keysym == 'Return':
                if selected_row[0] < num_rows[0] - 1:
                    select_row(selected_row[0] + 1)
                    return
            elif event.keysym == 'Up':
                if selected_row[0] > 0:
                    select_row(selected_row[0] - 1)
                    return
            elif event.keysym == 'Down':
                if selected_row[0] < num_rows[0] - 1:
                    select_row(selected_row[0] + 1)
                    return
            elif len(event.char) == 1 and event.char.isprintable():
                if len(current) < limit:
                    text_data[selected_row[0]] = current + event.char
                else:
                    canvas.config(highlightbackground='#ff0000')
                    self.root.after(100, lambda: canvas.config(highlightbackground='#333333'))
            update_preview()

        def on_click(event):
            n = num_rows[0]
            zone_h = canvas_height / n
            clicked = min(int(event.y / zone_h), n - 1)
            select_row(clicked)
            canvas.focus_set()

        canvas.bind('<Key>', on_key)
        canvas.bind('<Button-1>', on_click)
        canvas.focus_set()

        # ── AD NAME (ad mode only) ────────────────────────────────────────────
        if is_ad:
            name_frame = tk.Frame(controls, bg='#1a1a1a')
            name_frame.pack(fill='x', padx=10, pady=(5, 0))
            tk.Label(name_frame, text="Name:", font=('Helvetica', 8, 'bold'),
                    bg='#1a1a1a', fg='#888888').pack(side='left')
            name_var = tk.StringVar(value=init_name)
            tk.Entry(name_frame, textvariable=name_var, font=('Helvetica', 10),
                    bg='#2a2a2a', fg='white', relief='flat',
                    insertbackground='white').pack(side='left', fill='x', expand=True, padx=(6, 0))
        else:
            name_var = None

        # ── ROW TABS + BORDER TOGGLE ─────────────────────────────────────────
        tabs_border_frame = tk.Frame(controls, bg='#1a1a1a')
        tabs_border_frame.pack(fill='x', padx=10, pady=(8, 0))

        row_tabs_frame = tk.Frame(tabs_border_frame, bg='#1a1a1a')
        row_tabs_frame.pack(side='left')

        border_frame = tk.Frame(tabs_border_frame, bg='#1a1a1a')
        border_frame.pack(side='right')
        tk.Label(border_frame, text="BORDER", font=('Helvetica', 7, 'bold'),
                bg='#1a1a1a', fg='#888888').pack()
        border_var = tk.BooleanVar(value=init_border)

        def on_border_toggle():
            border_on[0] = border_var.get()
            if border_on[0] and not border_anim_job[0]:
                border_tick()
            update_preview()

        bdr_btn_f = tk.Frame(border_frame, bg='#1a1a1a')
        bdr_btn_f.pack()
        for lbl, val in [("Off", False), ("On", True)]:
            tk.Radiobutton(bdr_btn_f, text=lbl, variable=border_var, value=val,
                          font=('Helvetica', 9), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', indicatoron=False, width=4,
                          command=on_border_toggle).pack(side='left', padx=1)

        def rebuild_row_tabs():
            for w in row_tabs_frame.winfo_children():
                w.destroy()
            tk.Label(row_tabs_frame, text="ROWS:", font=('Helvetica', 7, 'bold'),
                    bg='#1a1a1a', fg='#888888').pack(side='left', padx=(0, 4))
            for i in range(num_rows[0]):
                is_sel = (i == selected_row[0])
                tk.Button(row_tabs_frame, text=f" {i + 1} ",
                         font=('Helvetica', 10, 'bold'),
                         bg='#0055cc' if is_sel else '#2a2a2a',
                         fg='white', relief='flat', padx=2,
                         command=lambda idx=i: select_row(idx)).pack(side='left', padx=1)
            # + Add row
            if num_rows[0] < 4:
                tk.Button(row_tabs_frame, text=" + ", font=('Helvetica', 10, 'bold'),
                         bg='#004400', fg='#44ff44', relief='flat',
                         command=add_row).pack(side='left', padx=(4, 1))
            # × Remove last row
            if num_rows[0] > 1:
                tk.Button(row_tabs_frame, text=" × ", font=('Helvetica', 10, 'bold'),
                         bg='#440000', fg='#ff4444', relief='flat',
                         command=remove_last_row).pack(side='left', padx=1)

        def select_row(idx):
            selected_row[0] = idx
            rebuild_row_tabs()
            update_row_ui()
            update_preview()
            canvas.focus_set()

        def add_row():
            if num_rows[0] < 4:
                num_rows[0] += 1
                selected_row[0] = num_rows[0] - 1
                rebuild_row_tabs()
                update_row_ui()
                update_preview()
                canvas.focus_set()

        def remove_last_row():
            if num_rows[0] > 1:
                idx = num_rows[0] - 1
                text_data[idx] = ""
                row_settings[idx] = _blank_row()
                num_rows[0] -= 1
                if selected_row[0] >= num_rows[0]:
                    selected_row[0] = num_rows[0] - 1
                rebuild_row_tabs()
                update_row_ui()
                update_preview()
                canvas.focus_set()

        rebuild_row_tabs()

        # ── DIVIDER ───────────────────────────────────────────────────────────
        tk.Frame(controls, bg='#333333', height=1).pack(fill='x', padx=10, pady=(5, 0))

        # ── SIZE + COLOR ──────────────────────────────────────────────────────
        row1 = tk.Frame(controls, bg='#1a1a1a')
        row1.pack(fill='x', pady=4)

        size_frame = tk.Frame(row1, bg='#1a1a1a')
        size_frame.pack(side='left', padx=(10, 5))
        tk.Label(size_frame, text="SIZE", font=('Helvetica', 8, 'bold'),
                bg='#1a1a1a', fg='#888888').pack()
        size_var = tk.StringVar(value=row_settings[0].get('size', '3'))

        def on_size_change(new_size):
            limit = CHAR_LIMITS[new_size]
            row_settings[selected_row[0]]['size'] = new_size
            if len(text_data[selected_row[0]]) > limit:
                text_data[selected_row[0]] = text_data[selected_row[0]][:limit]
            update_preview()

        size_btns = tk.Frame(size_frame, bg='#1a1a1a')
        size_btns.pack()
        for label, val in [("XL", "4"), ("L", "3"), ("M", "2")]:
            tk.Radiobutton(size_btns, text=label, variable=size_var, value=val,
                          font=('Helvetica', 9, 'bold'), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', indicatoron=False, width=3,
                          command=lambda v=val: on_size_change(v)).pack(side='left', padx=1)

        color_frame = tk.Frame(row1, bg='#1a1a1a')
        color_frame.pack(side='left', padx=5)
        tk.Label(color_frame, text="COLOR", font=('Helvetica', 8, 'bold'),
                bg='#1a1a1a', fg='#888888').pack()
        color_var = tk.StringVar(value=row_settings[0]["color"])

        def on_color_change():
            row_settings[selected_row[0]]["color"] = color_var.get()
            update_preview()

        color_grid = tk.Frame(color_frame, bg='#1a1a1a')
        color_grid.pack()
        colors = [("1", "#ff0000"), ("2", "#00ff00"), ("3", "#ffff00"), ("4", "#0000ff"),
                  ("5", "#ff00ff"), ("6", "#00ffff"), ("7", "#ffffff")]
        for r in range(2):
            rf = tk.Frame(color_grid, bg='#1a1a1a')
            rf.pack()
            start = r * 4
            for val, rgb in colors[start:start + 4]:
                tk.Radiobutton(rf, variable=color_var, value=val, bg=rgb,
                              selectcolor=rgb, indicatoron=False, width=2, height=1,
                              command=on_color_change).pack(side='left', padx=1, pady=1)

        # ── H-ALIGN + V-ALIGN ─────────────────────────────────────────────────
        row2 = tk.Frame(controls, bg='#1a1a1a')
        row2.pack(fill='x', pady=4)

        # H-Align
        h_align_outer = tk.Frame(row2, bg='#1a1a1a')
        h_align_outer.pack(side='left', padx=(10, 4))
        tk.Label(h_align_outer, text="H-ALIGN", font=('Helvetica', 7, 'bold'),
                bg='#1a1a1a', fg='#888888').pack()
        h_align_var = tk.StringVar(value=row_settings[0]["h_align"])

        def on_h_align_change():
            row_settings[selected_row[0]]["h_align"] = h_align_var.get()
            update_preview()

        h_btn_f = tk.Frame(h_align_outer, bg='#1a1a1a')
        h_btn_f.pack()
        for icon, val in [("←", "3"), ("•", "1"), ("→", "2")]:
            tk.Radiobutton(h_btn_f, text=icon, variable=h_align_var, value=val,
                          font=('Helvetica', 12), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', indicatoron=False, width=3,
                          command=on_h_align_change).pack(side='left', padx=1)

        # V-Align
        v_align_outer = tk.Frame(row2, bg='#1a1a1a')
        v_align_outer.pack(side='left', padx=4)
        tk.Label(v_align_outer, text="V-ALIGN", font=('Helvetica', 7, 'bold'),
                bg='#1a1a1a', fg='#888888').pack()
        v_align_var = tk.StringVar(value=row_settings[0].get("v_align", "2"))

        def on_v_align_change():
            row_settings[selected_row[0]]["v_align"] = v_align_var.get()
            update_preview()

        v_btn_f = tk.Frame(v_align_outer, bg='#1a1a1a')
        v_btn_f.pack()
        for icon, val in [("↑", "1"), ("•", "2"), ("↓", "3")]:
            tk.Radiobutton(v_btn_f, text=icon, variable=v_align_var, value=val,
                          font=('Helvetica', 12), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', indicatoron=False, width=3,
                          command=on_v_align_change).pack(side='left', padx=1)

        def update_row_ui():
            """Sync all control widgets to the currently selected row's settings."""
            settings = row_settings[selected_row[0]]
            size_var.set(settings.get('size', '3'))
            color_var.set(settings.get('color', '1'))
            h_align_var.set(settings.get('h_align', '1'))
            v_align_var.set(settings.get('v_align', '2'))

        # ── SCROLL ────────────────────────────────────────────────────────────
        tk.Frame(controls, bg='#333333', height=1).pack(fill='x', padx=10, pady=(4, 0))
        snake_outer = tk.Frame(controls, bg='#1a1a1a')
        snake_outer.pack(fill='x', padx=10, pady=(4, 0))
        tk.Label(snake_outer, text="SCROLL", font=('Helvetica', 7, 'bold'),
                bg='#1a1a1a', fg='#ff8800').pack(side='left', padx=(0, 6))
        snake_var = tk.StringVar(value="off")
        def on_snake_change(v):
            snake_var.set(v)
            _snake_mode[0] = v
            if v == 'off':
                stop_preview_scroll()
                update_preview()
            else:
                start_preview_scroll()

        for lbl, val in [("Off", "off"), ("Slow", "slow"), ("Med", "med"), ("Fast", "fast")]:
            tk.Radiobutton(snake_outer, text=lbl, variable=snake_var, value=val,
                          font=('Helvetica', 8), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', indicatoron=False, width=5,
                          command=lambda v=val: on_snake_change(v)
                          ).pack(side='left', padx=1)

        _single_line_var = tk.BooleanVar(value=False)
        def on_scroll_type_change():
            _scroll_type[0] = 'single' if _single_line_var.get() else 'multi'
            if _snake_mode[0] != 'off':
                stop_preview_scroll()
                for j in range(4): preview_row_scroll_pos[j] = 0
                preview_scroll_pos[0] = 0
                start_preview_scroll()
        tk.Checkbutton(snake_outer, text="Single", variable=_single_line_var,
                      command=on_scroll_type_change,
                      font=('Helvetica', 8), bg='#1a1a1a', fg='#ffcc44',
                      selectcolor='#333333', activebackground='#1a1a1a',
                      activeforeground='#ffcc44').pack(side='left', padx=(6, 1))

        # ── ACTION BUTTONS ────────────────────────────────────────────────────
        btn_frame = tk.Frame(controls, bg='#1a1a1a')
        btn_frame.pack(side='bottom', pady=(5, 8))

        def _apply_rows():
            self.stop_scrolling_text()
            prog_base = {1: 7, 2: 9, 3: 11, 4: 13}.get(num_rows[0], 7)
            prog = prog_base + (1 if border_on[0] else 0)
            active = sum(1 for i in range(num_rows[0]) if text_data[i].strip())
            if active == 0:
                return
            # Snake scroll takes priority over per-row settings
            s_mode = snake_var.get()
            if s_mode != "off":
                speed_map = {"slow": 1200, "med": 900, "fast": 600}
                texts   = [text_data[i] for i in range(num_rows[0])]
                chars   = [CHAR_LIMITS[row_settings[i].get('size', '3')]
                           for i in range(num_rows[0])]
                colors  = [row_settings[i].get('color', '7') for i in range(num_rows[0])]
                sizes   = [row_settings[i].get('size', '3') for i in range(num_rows[0])]
                haligns = [row_settings[i].get('h_align', '1') for i in range(num_rows[0])]
                valigns = [row_settings[i].get('v_align', '2') for i in range(num_rows[0])]
                if _scroll_type[0] == 'single':
                    self.start_single_row_scroll(texts, chars,
                                                 list(range(1, num_rows[0] + 1)),
                                                 colors, sizes, haligns, valigns,
                                                 prog, speed_map[s_mode])
                else:
                    self.start_snake_scroll(texts, chars,
                                            list(range(1, num_rows[0] + 1)),
                                            colors, sizes, valigns,
                                            prog, speed_map[s_mode])
                return
            self.send_udp_command(f"*#1PRGC3{prog},0000")
            for i in range(num_rows[0]):
                text = text_data[i]
                settings = row_settings[i]
                ramt = i + 1
                if not text.strip():
                    continue
                if settings.get("scroll", False):
                    size = settings.get("size", "3")
                    limit = CHAR_LIMITS[size]
                    pad = " " * (limit // 2 + 2)
                    padded = pad + text + pad
                    speed = settings.get("scroll_speed", 700)
                    self.root.after(120 * ramt, lambda t=padded, c=settings["color"],
                                   s=size, sp=speed, r=ramt:
                                   self.start_scrolling_text_row(t, c, s, sp, r))
                else:
                    cmd = (f"*#1RAMT{ramt},{settings['color']}{settings.get('size','3')}"
                           f"{settings['h_align']}{settings.get('v_align','2')}{text}0000")
                    self.send_udp_command(cmd)

        if is_ad:
            def save_ad():
                rows = [{**row_settings[i], 'text': text_data[i]} for i in range(num_rows[0])]
                active = [r for r in rows if r['text'].strip()]
                if not active:
                    messagebox.showwarning("Empty Ad",
                        "Please add some text to your advertisement before saving.",
                        parent=self.root)
                    return
                name = name_var.get().strip() if name_var else ''
                ad = {'name': name or f"Ad {len(self.advertisements) + 1}",
                      'rows': rows, 'border': border_on[0]}
                if edit_index is not None and 0 <= edit_index < len(self.advertisements):
                    self.advertisements[edit_index] = ad
                else:
                    self.advertisements.append(ad)
                self.save_config()
                self.stop_scrolling_text()
                messagebox.showinfo("Saved",
                    f"Advertisement \"{ad['name']}\" saved successfully!",
                    parent=self.root)
                self.show_current_sport_ui()

            tk.Button(btn_frame, text="💾 Save Ad", font=('Helvetica', 11, 'bold'),
                     bg='#00aa00', fg='white', relief='flat', padx=30, pady=6,
                     command=save_ad).pack(pady=2)
            tk.Button(btn_frame, text="▶ Preview", font=('Helvetica', 11, 'bold'),
                     bg='#0066cc', fg='white', relief='flat', padx=30, pady=6,
                     command=_apply_rows).pack(pady=2)
        else:
            def blank():
                self.stop_scrolling_text()
                for i in range(1, 5):
                    self.send_udp_command(f"*#1RAMT{i},1211 0000")

            tk.Button(btn_frame, text="✓ Apply", font=('Helvetica', 11, 'bold'),
                     bg='#00aa00', fg='white', relief='flat', padx=35, pady=6,
                     command=_apply_rows).pack(pady=2)
            tk.Button(btn_frame, text="⊗ Blank", font=('Helvetica', 11, 'bold'),
                     bg='#cc0000', fg='white', relief='flat', padx=35, pady=6,
                     command=blank).pack(pady=2)

        update_row_ui()
        update_preview()
        # Start border animation if loaded with border on
        if border_on[0]:
            border_tick()

    def show_edit_home_text(self):
        """Home screen text editor — delegates to unified show_text_editor."""
        self.show_text_editor(mode='text')


    def _get_all_ads(self):
        """Return all user-saved advertisements."""
        return self.advertisements

    def _ad_label(self, i, ad):
        """Return a display label for an advertisement."""
        name = ad.get('name', '').strip()
        if name:
            return name
        if 'rows' in ad:
            first_text = ad['rows'][0]['text'] if ad['rows'] else ''
        else:
            first_text = ad.get('text', '')
        label = first_text[:25] + ('...' if len(first_text) > 25 else '')
        return f"Ad {i+1}: {label}" if label else f"Ad {i+1}"

    def _play_advertisement(self, ad):
        """Play an advertisement on the display (row format or legacy single-row)."""
        self.send_udp_command("*#1PRGC30,0000")
        if 'rows' in ad:
            rows = ad['rows']
            n = len(rows)
            border = ad.get('border', False)
            prog_base = {1: 7, 2: 9, 3: 11, 4: 13}.get(n, 7)
            prog = prog_base + (1 if border else 0)
            self.root.after(120, lambda: self.send_udp_command(f"*#1PRGC3{prog},0000"))
            for i, row in enumerate(rows, start=1):
                text = row.get('text', '')
                if not text.strip():
                    continue
                color   = row.get('color', '7')
                size    = row.get('size', '3')
                h_align = row.get('h_align', '1')
                v_align = row.get('v_align', '1')
                if row.get('scroll', False):
                    speed = row.get('scroll_speed', 700)
                    self.root.after(120 * i, lambda t=text, c=color, s=size, sp=speed, r=i:
                                    self.start_scrolling_text_row(t, c, s, sp, r))
                else:
                    self.root.after(120 * i, lambda t=text, c=color, s=size, h=h_align, v=v_align, r=i:
                                    self.send_udp_command(f"*#1RAMT{r},{c}{s}{h}{v}{t}0000"))
        else:
            # old single-row format (backward compat)
            color   = ad.get('colour', ad.get('color', '7'))
            size    = ad.get('size', '3')
            h_align = ad.get('h_align', '1')
            v_align = ad.get('v_align', '1')
            text    = ad.get('text', '')
            self.root.after(120, lambda: self.send_udp_command("*#1PRGC37,0000"))
            if ad.get('scroll', False):
                speed = ad.get('scroll_speed', 700)
                self.root.after(240, lambda: self.start_scrolling_text(text, color, size, speed))
            else:
                self.root.after(240, lambda: self.send_udp_command(
                    f"*#1RAMT1,{color}{size}{h_align}{v_align}{text}0000"))

    def start_scrolling_text(self, text, color, size, speed=700):
        """Start scrolling text animation with configurable speed"""
        # Stop any existing scroll
        self.stop_scrolling_text()
        
        # Setup scrolling
        self.scroll_active = True
        self.scroll_text = text + "   "  # Add padding for smooth scrolling
        self.scroll_position = 0
        
        # Store settings
        self.scroll_color = color
        self.scroll_size = size
        self.scroll_speed = speed
        
        # Start scroll loop
        self._scroll_text_step()
    
    def _scroll_text_step(self):
        """Execute one step of scrolling animation"""
        if not self.scroll_active:
            return
        
        # Build the visible window
        full_text = self.scroll_text + self.scroll_text
        window = full_text[self.scroll_position:self.scroll_position + len(self.scroll_text) - 3]
        
        # Send command
        cmd = f"*#1RAMT1,{self.scroll_color}{self.scroll_size}11{window}0000"
        self.send_udp_command(cmd)
        
        # Move to next position
        self.scroll_position = (self.scroll_position + 1) % len(self.scroll_text)
        
        # Schedule next step with configured speed
        self.scroll_timer = self.root.after(self.scroll_speed, self._scroll_text_step)
    
    def stop_scrolling_text(self):
        """Stop all scrolling animation (per-row, snake, and single-row)."""
        self.scroll_active = False
        if self.scroll_timer:
            self.root.after_cancel(self.scroll_timer)
            self.scroll_timer = None
        self.stop_snake_scroll()
        self.stop_single_row_scroll()

    def stop_snake_scroll(self):
        """Stop snake scroll animation."""
        self.snake_active = False
        if getattr(self, 'snake_timer', None):
            self.root.after_cancel(self.snake_timer)
            self.snake_timer = None

    def start_single_row_scroll(self, texts, char_limits, ramt_slots,
                                 colors, sizes, h_aligns, v_aligns, prog, speed):
        """Scroll each row through its own text independently."""
        self.stop_scrolling_text()
        rows = []
        for txt, limit, ramt, color, size, h_align, v_align in zip(
                texts, char_limits, ramt_slots, colors, sizes, h_aligns, v_aligns):
            padded = (txt.strip() + '   ') if txt.strip() else ''
            rows.append({'padded': padded, 'limit': limit, 'ramt': ramt,
                         'color': color, 'size': size, 'h_align': h_align,
                         'v_align': v_align, 'pos': 0})
        self.single_scroll_rows = rows
        self.single_scroll_speed = speed
        self.single_scroll_active = True
        self.send_udp_command(f"*#1PRGC3{prog},0000")
        self.root.after(150, self._single_scroll_step)

    def _single_scroll_step(self):
        """One tick of single-row scroll: each row advances its own position."""
        if not self.single_scroll_active:
            return
        for row in self.single_scroll_rows:
            padded = row['padded']
            if not padded:
                continue
            flen = len(padded)
            doubled = padded * 2
            pos = row['pos'] % flen
            window = doubled[pos: pos + row['limit']].ljust(row['limit'])[:row['limit']]
            cmd = (f"*#1RAMT{row['ramt']},{row['color']}{row['size']}"
                   f"{row['h_align']}{row['v_align']}{window}0000")
            self.send_udp_command(cmd)
            row['pos'] = (row['pos'] + 1) % flen
        self.single_scroll_timer = self.root.after(
            self.single_scroll_speed, self._single_scroll_step)

    def stop_single_row_scroll(self):
        """Stop single-row scroll animation."""
        self.single_scroll_active = False
        if getattr(self, 'single_scroll_timer', None):
            self.root.after_cancel(self.single_scroll_timer)
            self.single_scroll_timer = None

    def start_snake_scroll(self, texts, char_limits, ramt_slots,
                           colors, sizes, v_aligns, prog, speed):
        """Snake-scroll all rows together: text flows continuously across every row
        like a snake, each row showing a successive window into one long string."""
        self.stop_scrolling_text()
        # Build combined string: all non-empty row texts joined with space padding
        parts = [t.strip() for t in texts]
        joined = '   '.join(p for p in parts if p)
        if not joined:
            return
        # Pad total length so it's at least as long as all rows combined
        total_chars = sum(char_limits)
        tail_spaces = max(4, total_chars - len(joined))
        self.snake_full   = joined + ' ' * tail_spaces
        self.snake_position   = 0
        self.snake_speed      = speed
        self.snake_ramt_slots = ramt_slots
        self.snake_char_limits= char_limits
        self.snake_colors     = colors
        self.snake_sizes      = sizes
        self.snake_v_aligns   = v_aligns
        self.snake_active     = True
        self.send_udp_command(f"*#1PRGC3{prog},0000")
        self.root.after(150, self._snake_scroll_step)

    def _snake_scroll_step(self):
        """One tick of snake scroll: send one window per row, offset by row position."""
        if not self.snake_active:
            return
        full = self.snake_full
        flen = len(full)
        doubled = full + full   # enough for any window without modulo inside loop
        pos = self.snake_position
        offset = 0
        for ramt, limit, color, size, v_align in zip(
                self.snake_ramt_slots, self.snake_char_limits,
                self.snake_colors, self.snake_sizes, self.snake_v_aligns):
            start = (pos + offset) % flen
            window = doubled[start: start + limit].ljust(limit)[:limit]
            cmd = f"*#1RAMT{ramt},{color}{size}1{v_align}{window}0000"
            self.send_udp_command(cmd)
            offset += limit
        self.snake_position = (self.snake_position + 1) % flen
        self.snake_timer = self.root.after(self.snake_speed, self._snake_scroll_step)

    def start_scrolling_text_row(self, text, color, size, speed, row):
        """Start scrolling text on a specific RAMT row (used by text editor)"""
        self.stop_scrolling_text()
        self.scroll_active = True
        self.scroll_text = text + "   "
        self.scroll_position = 0
        self.scroll_color = color
        self.scroll_size = size
        self.scroll_speed = speed
        self.scroll_row = row
        self._scroll_text_row_step()

    def _scroll_text_row_step(self):
        """Execute one step of row-specific scrolling"""
        if not self.scroll_active:
            return
        full_text = self.scroll_text + self.scroll_text
        window = full_text[self.scroll_position:self.scroll_position + len(self.scroll_text) - 3]
        cmd = f"*#1RAMT{self.scroll_row},{self.scroll_color}{self.scroll_size}11{window}0000"
        self.send_udp_command(cmd)
        self.scroll_position = (self.scroll_position + 1) % len(self.scroll_text)
        self.scroll_timer = self.root.after(self.scroll_speed, self._scroll_text_row_step)

    # Config management
    def save_config(self):
        """Save configuration to file"""
        config = {
            "display_width": getattr(self, 'display_width', 128),
            "display_height": getattr(self, 'display_height', 80),
            "sport": self.current_sport,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "home_name": self.home_name,
            "away_name": self.away_name,
            "team_settings": self.team_settings,
            "home_screen_settings": self.home_screen_settings,
            "advertisements": self.advertisements,
            "current_ad_index": self.current_ad_index,
            "ad_selections": getattr(self, 'ad_selections', {}),
            # Basketball extras
            "home_timeouts": getattr(self, 'home_timeouts', 0),
            "away_timeouts": getattr(self, 'away_timeouts', 0),
            "home_fouls": getattr(self, 'home_fouls', 0),
            "away_fouls": getattr(self, 'away_fouls', 0),
            # Timer state
            "timer_countdown": getattr(self, 'timer_countdown', False),
            "timer_target_seconds": getattr(self, 'timer_target_seconds', 0),
            "timer_seconds": getattr(self, 'timer_seconds', 0),
            # Timer display style
            "timer_color":          getattr(self, 'timer_color',          '7'),
            "timer_size":           getattr(self, 'timer_size',           '2'),
            "timer_h_align":        getattr(self, 'timer_h_align',        '3'),
            "timer_v_align":        getattr(self, 'timer_v_align',        '1'),
            "timer_offset_afl":     getattr(self, 'timer_offset_afl',     1),
            "timer_offset_default": getattr(self, 'timer_offset_default', 0),
            # Shot clock display style
            "shot_clock_color":   getattr(self, 'shot_clock_color',   '7'),
            "shot_clock_size":    getattr(self, 'shot_clock_size',    '2'),
            "shot_clock_h_align": getattr(self, 'shot_clock_h_align', '1'),
            "shot_clock_v_align": getattr(self, 'shot_clock_v_align', '1'),
            # AFL specific
            "afl_home_goals": getattr(self, 'afl_home_goals', 0),
            "afl_home_points": getattr(self, 'afl_home_points', 0),
            "afl_away_goals": getattr(self, 'afl_away_goals', 0),
            "afl_away_points": getattr(self, 'afl_away_points', 0),
            "afl_home_name": getattr(self, 'afl_home_name', 'HOME'),
            "afl_away_name": getattr(self, 'afl_away_name', 'AWAY'),
            "afl_quarter":         getattr(self, 'afl_quarter',         1),
            "afl_quarter_color":   getattr(self, 'afl_quarter_color',   '7'),
            "afl_quarter_size":    getattr(self, 'afl_quarter_size',    '2'),
            "afl_quarter_h_align": getattr(self, 'afl_quarter_h_align', '1'),
            "afl_quarter_v_align": getattr(self, 'afl_quarter_v_align', '1'),
            # Cricket specific
            "cricket_home_runs": getattr(self, 'cricket_home_runs', 0),
            "cricket_home_wickets": getattr(self, 'cricket_home_wickets', 0),
            "cricket_away_runs": getattr(self, 'cricket_away_runs', 0),
            "cricket_away_wickets": getattr(self, 'cricket_away_wickets', 0),
            "cricket_extras": getattr(self, 'cricket_extras', 0),
            "cricket_overs": getattr(self, 'cricket_overs', 0),
            "cricket_balls": getattr(self, 'cricket_balls', 0),
            "cricket_home_name": getattr(self, 'cricket_home_name', 'HOME'),
            "cricket_away_name": getattr(self, 'cricket_away_name', 'AWAY'),
            # AFL team name display style
            "afl_team_color":   getattr(self, 'afl_team_color',   '1'),
            "afl_team_size":    getattr(self, 'afl_team_size',    '2'),
            "afl_team_h_align": getattr(self, 'afl_team_h_align', '3'),
            "afl_team_v_align": getattr(self, 'afl_team_v_align', '2'),
            # Cricket team name display style
            "cricket_team_color":   getattr(self, 'cricket_team_color',   '1'),
            "cricket_team_size":    getattr(self, 'cricket_team_size',    '2'),
            "cricket_team_h_align": getattr(self, 'cricket_team_h_align', '3'),
            "cricket_team_v_align": getattr(self, 'cricket_team_v_align', '2'),
        }
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"[INFO] Config saved to {CONFIG_FILE}")
        except Exception as e:
            print(f"[ERROR] Failed to save config: {e}")
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                
                self.display_width = config.get("display_width", None)
                self.display_height = config.get("display_height", None)
                
                self.current_sport = config.get("sport")
                self.home_score = config.get("home_score", 0)
                self.away_score = config.get("away_score", 0)
                self.home_name = config.get("home_name", "HOME")
                self.away_name = config.get("away_name", "AWAY")
                self.team_settings = config.get("team_settings", {"color": "1", "size": "2", "h_align": "1", "v_align": "1"})
                self.home_screen_settings = config.get("home_screen_settings", {"color": "7", "size": "2"})
                self.advertisements = config.get("advertisements", [])
                self.current_ad_index = config.get("current_ad_index", 0)
                self.ad_selections = config.get("ad_selections", {})
                self.home_timeouts = config.get("home_timeouts", 0)
                self.away_timeouts = config.get("away_timeouts", 0)
                self.home_fouls = config.get("home_fouls", 0)
                self.away_fouls = config.get("away_fouls", 0)
                self.timer_countdown = config.get("timer_countdown", False)
                self.timer_target_seconds = config.get("timer_target_seconds", 0)
                self.timer_seconds = config.get("timer_seconds", 0)
                # Timer display style
                self.timer_color          = config.get("timer_color",          '7')
                self.timer_size           = config.get("timer_size",           '2')
                self.timer_h_align        = '3'   # always left
                self.timer_v_align        = config.get("timer_v_align",        '1')
                self.timer_offset_afl     = config.get("timer_offset_afl",     1)
                self.timer_offset_default = config.get("timer_offset_default", 0)
                # Shot clock display style
                self.shot_clock_color   = config.get("shot_clock_color",   '7')
                self.shot_clock_size    = config.get("shot_clock_size",    '2')
                self.shot_clock_h_align = '3'   # always left
                self.shot_clock_v_align = config.get("shot_clock_v_align", '1')

                # AFL specific
                self.afl_home_goals = config.get("afl_home_goals", 0)
                self.afl_home_points = config.get("afl_home_points", 0)
                self.afl_away_goals = config.get("afl_away_goals", 0)
                self.afl_away_points = config.get("afl_away_points", 0)
                self.afl_home_name = config.get("afl_home_name", "HOME")
                self.afl_away_name = config.get("afl_away_name", "AWAY")
                self.afl_quarter         = config.get("afl_quarter",         1)
                self.afl_quarter_color   = config.get("afl_quarter_color",   '7')
                self.afl_quarter_size    = config.get("afl_quarter_size",    '2')
                self.afl_quarter_h_align = '3'   # always left
                self.afl_quarter_v_align = config.get("afl_quarter_v_align", '1')

                # Cricket specific
                self.cricket_home_runs = config.get("cricket_home_runs", 0)
                self.cricket_home_wickets = config.get("cricket_home_wickets", 0)
                self.cricket_away_runs = config.get("cricket_away_runs", 0)
                self.cricket_away_wickets = config.get("cricket_away_wickets", 0)
                self.cricket_extras = config.get("cricket_extras", 0)
                self.cricket_overs = config.get("cricket_overs", 0)
                self.cricket_balls = config.get("cricket_balls", 0)
                self.cricket_home_name = config.get("cricket_home_name", "HOME")
                self.cricket_away_name = config.get("cricket_away_name", "AWAY")

                # AFL team name display style
                self.afl_team_color   = config.get("afl_team_color",   '1')
                self.afl_team_size    = config.get("afl_team_size",    '2')
                self.afl_team_h_align = config.get("afl_team_h_align", '3')
                self.afl_team_v_align = config.get("afl_team_v_align", '2')

                # Cricket team name display style
                self.cricket_team_color   = config.get("cricket_team_color",   '1')
                self.cricket_team_size    = config.get("cricket_team_size",    '2')
                self.cricket_team_h_align = config.get("cricket_team_h_align", '3')
                self.cricket_team_v_align = config.get("cricket_team_v_align", '2')

                # Ensure alignment keys exist
                if 'h_align' not in self.team_settings:
                    self.team_settings['h_align'] = '1'
                if 'v_align' not in self.team_settings:
                    self.team_settings['v_align'] = '2'
                
                print(f"[INFO] Config loaded from {CONFIG_FILE}")
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")


    def show_display_setup(self):
        """First-time display configuration screen"""
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Expand window for setup
        self.root.geometry("500x560")

        main = tk.Frame(self.root, bg='#1a1a1a')
        main.pack(fill='both', expand=True, padx=40, pady=20)
        
        tk.Label(main, text="Display Setup", font=('Helvetica', 24, 'bold'),
                bg='#1a1a1a', fg='#00aaff').pack(pady=(0, 10))
        
        tk.Label(main, text="Configure your LED display dimensions",
                font=('Helvetica', 11), bg='#1a1a1a', fg='#888888').pack(pady=(0, 40))
        
        # Width input
        width_frame = tk.Frame(main, bg='#1a1a1a')
        width_frame.pack(pady=15)
        
        tk.Label(width_frame, text="Width (pixels):", font=('Helvetica', 13, 'bold'),
                bg='#1a1a1a', fg='white', width=15, anchor='w').pack(side='left', padx=10)
        
        width_var = tk.StringVar(value=str(getattr(self, 'display_width', 128) or 128))
        width_entry = tk.Entry(width_frame, textvariable=width_var, font=('Helvetica', 14),
                              bg='#333333', fg='white', width=10, relief='flat',
                              insertbackground='white', justify='center')
        width_entry.pack(side='left', padx=10, ipady=8)
        
        # Height input
        height_frame = tk.Frame(main, bg='#1a1a1a')
        height_frame.pack(pady=15)
        
        tk.Label(height_frame, text="Height (pixels):", font=('Helvetica', 13, 'bold'),
                bg='#1a1a1a', fg='white', width=15, anchor='w').pack(side='left', padx=10)
        
        height_var = tk.StringVar(value=str(getattr(self, 'display_height', 80) or 80))
        height_entry = tk.Entry(height_frame, textvariable=height_var, font=('Helvetica', 14),
                               bg='#333333', fg='white', width=10, relief='flat',
                               insertbackground='white', justify='center')
        height_entry.pack(side='left', padx=10, ipady=8)
        
        # Common sizes hint
        tk.Label(main, text="Common: 128×80  •  192×64  •  256×64",
                font=('Helvetica', 9, 'italic'), bg='#1a1a1a', fg='#666666').pack(pady=(30, 5))
        
        def save_and_continue():
            try:
                w = int(width_var.get())
                h = int(height_var.get())
                
                if w < 32 or w > 512 or h < 16 or h > 256:
                    messagebox.showerror("Invalid Size", "Width: 32-512px\nHeight: 16-256px")
                    return
                
                self.display_width = w
                self.display_height = h
                self.save_config()
                
                # Reset window size and create home screen
                self.root.geometry("400x700")
                self.create_home_screen()
                self.root.after(100, self.start_auto_reconnect)
                
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numbers")
        
        # Buttons
        btn_frame = tk.Frame(main, bg='#1a1a1a')
        btn_frame.pack(pady=(40, 0))
        
        tk.Button(btn_frame, text="Apply & Continue", font=('Helvetica', 13, 'bold'),
                 bg='#00aa00', fg='white', relief='flat', padx=40, pady=12,
                 command=save_and_continue).pack()

def main():
    root = tk.Tk()
    app = ScoreboardApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()