#!/usr/bin/env python3
"""
Professional Scoreboard Control
Supports Soccer, AFL, Cricket and more
Controls LED displays via UDP (TF-F6 controller)
Optimized for mobile-friendly interface
"""

import tkinter as tk
from tkinter import ttk, messagebox
import socket
import json
import os
import sys
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
        self.root.geometry("450x700")
        self.root.configure(bg='#1a1a1a')
        
        # Disable window resize for consistency
        self.root.resizable(False, False)

        # macOS colour consistency — apply globally so no individual widgets need changing
        if sys.platform == 'darwin':
            style = ttk.Style()
            style.theme_use('default')  # avoid native Aqua theme overriding custom colours
            style.configure('TCombobox',
                            fieldbackground='#333333',
                            background='#444444',
                            foreground='white',
                            selectbackground='#555555',
                            selectforeground='white')
            self.root.option_add('*Button.highlightThickness', 0)
            self.root.option_add('*Checkbutton.highlightThickness', 0)

        # Connection state
        self.connected = False
        self.connection_tried = False
        self.reconnect_timer = None
        
        # Sport settings
        self.current_sport = None
        self.sport_programs = {
            "AFL (Count-Up)": "1",
            "AFL (Count-Down)": "2",
            "Soccer": "3",
            "Cricket": "4"
        }
        
        # Score data
        self.home_score = 0
        self.away_score = 0
        self.home_name = "HOME"
        self.away_name = "AWAY"
        self.timer_running = False
        self.current_half = "1st HALF"
        
        # AFL-specific score tracking
        self.home_goals = 0
        self.home_points = 0
        self.away_goals = 0
        self.away_points = 0
        self.current_quarter = "Q1"
        self.quarter_settings = {"color": "1", "size": "1", "h_align": "1", "v_align": "1"}  # RAMT3 for quarters
        
        # Text settings for different areas
        self.half_settings = {"color": "1", "size": "1", "h_align": "1", "v_align": "1"}  # RAMT3
        self.team_settings = {"color": "1", "size": "3", "h_align": "1", "v_align": "1"}  # RAMT1
        self.home_screen_settings = {"color": "7", "size": "2"}  # RAMT1 for home screen
        self.halftime_screen_settings = {"color": "7", "size": "2"}  # For halftime/fulltime screens
        
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
        
        # Advertisement management
        self.advertisements = []  # List of saved advertisements
        self.current_ad_index = 0  # Currently selected advertisement
        
        # Load saved config
        self.load_config()
        
        # Create UI
        self.create_home_screen()
        
        # Auto-connect on startup
        self.root.after(100, self.start_auto_reconnect)
    
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
        if not self.connected:
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
                    if hasattr(self, 'status_label'):
                        self.status_label.config(text=f"● Connected to {CONTROLLER_IP}", fg='#00ff00', bg='#2a2a2a')
                    self.connect_btn.config(state='disabled')
                    self.enable_sport_buttons()
                    print(f"[INFO] ✓✓✓ Connection VERIFIED - Controller is responding!")
                else:
                    raise Exception(f"Response from wrong address: {addr} (expected {CONTROLLER_IP}:{CONTROLLER_PORT})")
                    
            except socket.timeout:
                raise Exception(f"Controller not responding - no reply after 1 second (is controller at {CONTROLLER_IP}:{CONTROLLER_PORT}?)")
            
            sock.close()
            
        except Exception as e:
            self.connected = False
            if hasattr(self, 'status_label'):
                self.status_label.config(text=f"● Disconnected", fg='#ff3333', bg='#2a2a2a')
            self.connect_btn.config(state='normal')
            self.select_sport_btn.config(bg='#555555', state='disabled')
            self.manage_scores_btn.config(bg='#555555', state='disabled')
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
        main_frame.pack(fill='both', expand=True)
        
        # Top section - Title and Status
        top_section = tk.Frame(main_frame, bg='#1a1a1a')
        top_section.pack(fill='x', padx=20, pady=(20, 10))
        
        # Title
        title = tk.Label(top_section, text="Scoreboard Control", 
                        font=('Helvetica', 24, 'bold'),
                        bg='#1a1a1a', fg='#00aaff')
        title.pack()
        
        # Subtitle
        subtitle = tk.Label(top_section, text="Professional LED Display Management", 
                           font=('Helvetica', 9),
                           bg='#1a1a1a', fg='#888888')
        subtitle.pack(pady=(2, 10))
        
        # Status indicator (compact)
        self.status_label = tk.Label(top_section, text="● Testing connection...", 
                                     font=('Helvetica', 10, 'bold'),
                                     bg='#2a2a2a', fg='#ffaa00', 
                                     padx=15, pady=6, relief='solid', bd=1)
        self.status_label.pack()
        
        # Current sport indicator (compact)
        if self.current_sport:
            sport_label = tk.Label(top_section, text=f"Sport: {self.current_sport}",
                                  font=('Helvetica', 11, 'bold'),
                                  bg='#1a1a1a', fg='#00aaff')
            sport_label.pack(pady=(8, 0))
        
        # Middle section - Action Buttons
        action_section = tk.Frame(main_frame, bg='#1a1a1a')
        action_section.pack(fill='x', padx=20, pady=(15, 10))
        
        # Connect button
        self.connect_btn = tk.Button(action_section, text="🔌 Connect to Controller",
                                     font=('Helvetica', 15, 'bold'),
                                     bg='#00aa00', fg='white',
                                     activebackground='#00dd00',
                                     activeforeground='white',
                                     relief='flat', bd=0,
                                     padx=30, pady=12,
                                     cursor='hand2',
                                     state='disabled',
                                     command=self.test_connection)
        self.connect_btn.pack(fill='x', pady=(0, 8))
        
        # Select Sport button
        self.select_sport_btn = tk.Button(action_section, text="🏆 Select Sport",
                                         font=('Helvetica', 15, 'bold'),
                                         bg='#555555', fg='white',
                                         activebackground='#0088ff',
                                         activeforeground='white',
                                         relief='flat', bd=0,
                                         padx=30, pady=12,
                                         cursor='hand2',
                                         state='disabled',
                                         command=self.show_sport_selection)
        self.select_sport_btn.pack(fill='x', pady=8)
        
        # Manage Scores button
        self.manage_scores_btn = tk.Button(action_section, text="⚽ Manage Scores",
                                          font=('Helvetica', 15, 'bold'),
                                          bg='#555555', fg='white',
                                          activebackground='#ff8800',
                                          activeforeground='white',
                                          relief='flat', bd=0,
                                          padx=30, pady=12,
                                          cursor='hand2',
                                          state='disabled',
                                          command=self.show_manage_scores)
        self.manage_scores_btn.pack(fill='x', pady=8)
        
        # WiFi Connection Instructions (compact)
        instruction_frame = tk.Frame(action_section, bg='#2a2a2a', relief='solid', bd=1)
        instruction_frame.pack(fill='x', pady=(15, 0))
        
        tk.Label(instruction_frame, text="📡 Connect to scoreboard WiFi network to manage scores",
                font=('Helvetica', 9, 'italic'),
                bg='#2a2a2a', fg='#ffaa00',
                padx=10, pady=8).pack()
        
        # Bottom section - Controls and Footer
        bottom_section = tk.Frame(main_frame, bg='#1a1a1a')
        bottom_section.pack(side='bottom', fill='x', padx=20, pady=(10, 15))
        
        # Bottom controls row
        controls_row = tk.Frame(bottom_section, bg='#1a1a1a')
        controls_row.pack(fill='x', pady=(0, 10))
        
        # Bypass connection toggle (left)
        self.bypass_connection = tk.BooleanVar(value=False)
        bypass_check = tk.Checkbutton(controls_row, text="Bypass Connection", 
                                      variable=self.bypass_connection,
                                      font=('Helvetica', 8),
                                      bg='#1a1a1a', fg='#888888',
                                      selectcolor='#333333',
                                      activebackground='#1a1a1a',
                                      activeforeground='#ffaa00',
                                      command=self.toggle_bypass)
        bypass_check.pack(side='left')
        
        # Edit Home Screen Text button (right)
        edit_btn = tk.Button(controls_row, text="✏️ Edit Screen Text",
                            font=('Helvetica', 9, 'bold'),
                            bg='#444444', fg='white',
                            activebackground='#666666',
                            activeforeground='white',
                            relief='flat', bd=0,
                            padx=12, pady=6,
                            cursor='hand2',
                            command=self.show_edit_home_text)
        edit_btn.pack(side='right')
        
        # Professional footer
        footer_text = tk.Label(bottom_section, 
                              text=f"Controller: {CONTROLLER_IP}:{CONTROLLER_PORT} • v1.0",
                              font=('Helvetica', 8),
                              bg='#1a1a1a', fg='#666666')
        footer_text.pack()
        
        # Auto-attempt connection when returning to home screen
        self.root.after(100, self.test_connection)
    
    def toggle_bypass(self):
        """Toggle bypass connection mode"""
        if self.bypass_connection.get():
            # Bypass enabled - allow all functions
            self.connected = True
            if hasattr(self, 'status_label'):
                self.status_label.config(text=f"● Bypass Mode (No Connection)", fg='#ffaa00', bg='#2a2a2a')
            self.connect_btn.config(state='disabled')
            self.enable_sport_buttons()
            print("[INFO] Bypass mode enabled - sending commands without connection check")
        else:
            # Bypass disabled - test real connection
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
        # Sport selected, no popup needed
        print(f"[INFO] Sport selected: {sport_name}")
    
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
        
        # Send team names
        color = self.team_settings['color']
        size = self.team_settings['size']
        h_align = self.team_settings.get('h_align', '1')
        v_align = self.team_settings.get('v_align', '1')
        self.send_udp_command(f"*#1RAMT1,{color}{size}{h_align}{v_align}{self.home_name}0000")
        self.send_udp_command(f"*#1RAMT2,{color}{size}{h_align}{v_align}{self.away_name}0000")
        
        # Send default half
        half_color = self.half_settings['color']
        half_size = self.half_settings['size']
        half_h_align = self.half_settings.get('h_align', '1')
        half_v_align = self.half_settings.get('v_align', '1')
        self.send_udp_command(f"*#1RAMT3,{half_color}{half_size}{half_h_align}{half_v_align}1st HALF0000")
        self.current_half = "1st HALF"
        
        # Show appropriate UI
        if self.current_sport == "Soccer":
            self.show_soccer_ui()
        elif self.current_sport in ["AFL (Count-Up)", "AFL (Count-Down)"]:
            self.show_afl_ui()
        elif self.current_sport == "Cricket":
            self.show_cricket_ui()
        else:
            # For other sports, show "Coming Soon"
            self.show_coming_soon()
    
    def show_soccer_ui(self):
        """Show soccer score management UI"""
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
        
        # Timer controls
        timer_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        timer_frame.pack(fill='x', pady=(0, 15), padx=5, ipady=10)
        
        tk.Label(timer_frame, text="Timer Controls", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(pady=(5, 10))
        
        timer_btns = tk.Frame(timer_frame, bg='#2a2a2a')
        timer_btns.pack()
        
        tk.Button(timer_btns, text="▶ Start", font=('Helvetica', 12), bg='#00aa00', fg='white',
                 relief='flat', padx=15, pady=8, command=self.start_timer).pack(side='left', padx=5)
        tk.Button(timer_btns, text="⏸ Pause", font=('Helvetica', 12), bg='#ffaa00', fg='white',
                 relief='flat', padx=15, pady=8, command=self.pause_timer).pack(side='left', padx=5)
        tk.Button(timer_btns, text="↻ Reset", font=('Helvetica', 12), bg='#ff3333', fg='white',
                 relief='flat', padx=15, pady=8, command=self.reset_timer).pack(side='left', padx=5)
        
        # Half selection
        half_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        half_frame.pack(fill='x', pady=(0, 15), padx=5, ipady=10)
        
        half_header = tk.Frame(half_frame, bg='#2a2a2a')
        half_header.pack(fill='x', padx=10, pady=5)
        
        tk.Label(half_header, text="HALF", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left')
        
        tk.Button(half_header, text="⚙", font=('Helvetica', 10), bg='#555555', fg='white',
                 relief='flat', padx=8, pady=2, command=lambda: self.show_text_settings("half")).pack(side='right')
        
        half_btns = tk.Frame(half_frame, bg='#2a2a2a')
        half_btns.pack(pady=(0, 5))
        
        tk.Button(half_btns, text="1st HALF", font=('Helvetica', 14, 'bold'), bg='#0066cc', fg='white',
                 relief='flat', padx=25, pady=10, command=self.set_first_half).pack(side='left', padx=5)
        tk.Button(half_btns, text="2nd HALF", font=('Helvetica', 14, 'bold'), bg='#0066cc', fg='white',
                 relief='flat', padx=25, pady=10, command=self.set_second_half).pack(side='left', padx=5)
        
        # Team names
        team_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        team_frame.pack(fill='x', pady=(0, 15), padx=5, ipady=10)
        
        team_header = tk.Frame(team_frame, bg='#2a2a2a')
        team_header.pack(fill='x', padx=10, pady=5)
        
        tk.Label(team_header, text="Team Names", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left')
        
        tk.Button(team_header, text="⚙", font=('Helvetica', 10), bg='#555555', fg='white',
                 relief='flat', padx=8, pady=2, command=lambda: self.show_text_settings("team")).pack(side='right')
        
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
        
        tk.Label(home_score_frame, text="HOME", font=('Helvetica', 11),
                bg='#2a2a2a', fg='#00ff00', width=8).pack(side='left', padx=5)
        
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
        
        tk.Label(away_score_frame, text="AWAY", font=('Helvetica', 11),
                bg='#2a2a2a', fg='#ffaa00', width=8).pack(side='left', padx=5)
        
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
        
        # Action buttons
        action_frame = tk.Frame(main_frame, bg='#1a1a1a')
        action_frame.pack(fill='x', pady=15)
        
        # Half Time Screen with settings button
        halftime_btn_frame = tk.Frame(action_frame, bg='#1a1a1a')
        halftime_btn_frame.pack(fill='x', pady=5)
        
        tk.Button(halftime_btn_frame, text="Half Time Screen", font=('Helvetica', 13, 'bold'),
                 bg='#ff8800', fg='white', relief='flat', padx=15, pady=12,
                 command=self.show_halftime_screen).pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        tk.Button(halftime_btn_frame, text="⚙", font=('Helvetica', 14, 'bold'),
                 bg='#555555', fg='white', relief='flat', width=4, pady=12,
                 command=self.show_halftime_settings).pack(side='right')
        
        tk.Button(action_frame, text="Return to Scores", font=('Helvetica', 13, 'bold'),
                 bg='#0088ff', fg='white', relief='flat', padx=15, pady=12,
                 command=self.return_to_scores).pack(fill='x', pady=5)
        
        # Advertisements section
        ads_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        ads_frame.pack(fill='x', pady=(15, 5), padx=5, ipady=10)
        
        tk.Label(ads_frame, text="Advertisements", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(pady=(5, 10))
        
        # Dropdown for selecting advertisement
        if len(self.advertisements) == 0:
            ad_choices = ["No advertisements"]
            current_index = 0
        else:
            ad_choices = [f"Ad {i+1}: {ad['text'][:25]}..." if len(ad['text']) > 25 else f"Ad {i+1}: {ad['text']}" 
                         for i, ad in enumerate(self.advertisements)]
            # Ensure current_ad_index is valid
            if self.current_ad_index >= len(self.advertisements):
                self.current_ad_index = 0
            current_index = self.current_ad_index
        
        selected_ad = tk.StringVar(value=ad_choices[current_index])
        
        dropdown = ttk.Combobox(ads_frame, textvariable=selected_ad, 
                               values=ad_choices, state='readonly',
                               font=('Helvetica', 10), width=28)
        dropdown.pack(pady=(0, 10))
        dropdown.current(current_index)  # Set to saved selection
        
        def on_ad_select(event):
            if len(self.advertisements) > 0:
                self.current_ad_index = dropdown.current()
                self.save_config()
        
        dropdown.bind('<<ComboboxSelected>>', on_ad_select)
        
        # Start Advertisement button
        def start_advertisement():
            if len(self.advertisements) > 0:
                ad = self.advertisements[self.current_ad_index]
                self.send_udp_command("*#1PRGC30,0000")
                
                color = ad.get('colour', ad.get('color', '7'))
                size = ad['size']
                h_align = ad.get('h_align', '1')
                v_align = ad.get('v_align', '1')
                text = ad['text']
                
                if ad.get('scroll', False):
                    speed = ad.get('scroll_speed', 700)
                    self.root.after(120, lambda: self.start_scrolling_text(text, color, size, speed))
                else:
                    self.root.after(120, lambda: self.send_udp_command(f"*#1RAMT1,{color}{size}{h_align}{v_align}{text}0000"))
        
        tk.Button(ads_frame, text="Start Advertisement", font=('Helvetica', 11, 'bold'),
                 bg='#00aa00', fg='white', relief='flat', padx=15, pady=8,
                 command=start_advertisement).pack(fill='x', padx=10, pady=(0, 5))
        
        # Return to Scores button
        tk.Button(ads_frame, text="Return to Scores", font=('Helvetica', 11, 'bold'),
                 bg='#0088ff', fg='white', relief='flat', padx=15, pady=8,
                 command=self.return_to_scores).pack(fill='x', padx=10, pady=(0, 10))
        
        # Manage buttons
        manage_btns = tk.Frame(ads_frame, bg='#2a2a2a')
        manage_btns.pack(pady=(5, 10))
        
        tk.Button(manage_btns, text="+ Add", font=('Helvetica', 11, 'bold'),
                 bg='#6600cc', fg='white', relief='flat', padx=15, pady=8,
                 command=self.show_add_advertisement).pack(side='left', padx=3)
        
        tk.Button(manage_btns, text="✎ Edit", font=('Helvetica', 11, 'bold'),
                 bg='#0066cc', fg='white', relief='flat', padx=15, pady=8,
                 command=self.show_edit_advertisement).pack(side='left', padx=3)
        
        tk.Button(manage_btns, text="− Remove", font=('Helvetica', 11, 'bold'),
                 bg='#cc0000', fg='white', relief='flat', padx=12, pady=8,
                 command=self.show_remove_advertisements).pack(side='left', padx=3)
        
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
        # Initialize AFL-specific scores if not exists
        if not hasattr(self, 'afl_home_goals'):
            self.afl_home_goals = 0
            self.afl_home_points = 0
            self.afl_away_goals = 0
            self.afl_away_points = 0
            self.current_quarter = "Q1"
        
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
        
        # Timer controls
        timer_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        timer_frame.pack(fill='x', pady=(0, 15), padx=5, ipady=10)
        
        tk.Label(timer_frame, text="Timer Controls", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(pady=(5, 10))
        
        timer_btns = tk.Frame(timer_frame, bg='#2a2a2a')
        timer_btns.pack(pady=(0, 5))
        
        tk.Button(timer_btns, text="▶ Start", font=('Helvetica', 13, 'bold'),
                 bg='#00aa00', fg='white', relief='flat', padx=20, pady=10,
                 command=lambda: self.send_udp_command("*#1TIMS1,0000")).pack(side='left', padx=5)
        tk.Button(timer_btns, text="⏸ Pause", font=('Helvetica', 13, 'bold'),
                 bg='#ffaa00', fg='white', relief='flat', padx=20, pady=10,
                 command=lambda: self.send_udp_command("*#1TIMP1,0000")).pack(side='left', padx=5)
        tk.Button(timer_btns, text="↻ Reset", font=('Helvetica', 13, 'bold'),
                 bg='#cc0000', fg='white', relief='flat', padx=20, pady=10,
                 command=lambda: self.send_udp_command("*#1TIMR1,0000")).pack(side='left', padx=5)
        
        # Quarter selection with settings
        quarter_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        quarter_frame.pack(fill='x', pady=(0, 15), padx=5, ipady=10)
        
        quarter_header = tk.Frame(quarter_frame, bg='#2a2a2a')
        quarter_header.pack(fill='x', padx=10, pady=(5, 0))
        
        tk.Label(quarter_header, text="QUARTER", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left')
        
        tk.Button(quarter_header, text="⚙", font=('Helvetica', 11),
                 bg='#444444', fg='white', relief='flat', width=3,
                 command=self.show_afl_quarter_settings).pack(side='right')
        
        quarter_btns = tk.Frame(quarter_frame, bg='#2a2a2a')
        quarter_btns.pack(pady=(10, 5))
        
        for q in ["Q1", "Q2", "Q3", "Q4"]:
            tk.Button(quarter_btns, text=q, font=('Helvetica', 14, 'bold'),
                     bg='#0066cc', fg='white', relief='flat', width=5, pady=10,
                     command=lambda quarter=q: self.set_afl_quarter(quarter)).pack(side='left', padx=3)
        
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
        
        # HOME TEAM SCORES
        home_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        home_frame.pack(fill='x', pady=(0, 10), padx=5, ipady=10)
        
        home_header = tk.Frame(home_frame, bg='#2a2a2a')
        home_header.pack(fill='x', padx=10, pady=(5, 0))
        
        self.afl_home_label = tk.Label(home_header, text=self.afl_home_name, font=('Helvetica', 13, 'bold'),
                bg='#2a2a2a', fg='#00aaff')
        self.afl_home_label.pack(side='left')
        
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
        
        self.afl_away_label = tk.Label(away_header, text=self.afl_away_name, font=('Helvetica', 13, 'bold'),
                bg='#2a2a2a', fg='#ff6600')
        self.afl_away_label.pack(side='left')
        
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
        
        # Break screens with settings
        break_frame = tk.Frame(main_frame, bg='#1a1a1a')
        break_frame.pack(fill='x', pady=15)
        
        # Quarter Time
        qt_frame = tk.Frame(break_frame, bg='#1a1a1a')
        qt_frame.pack(fill='x', pady=3)
        
        tk.Button(qt_frame, text="Quarter Time", font=('Helvetica', 12, 'bold'),
                 bg='#ff8800', fg='white', relief='flat', padx=15, pady=10,
                 command=lambda: self.show_afl_break("Quarter Time")).pack(side='left', fill='x', expand=True)
        
        tk.Button(qt_frame, text="⚙", font=('Helvetica', 11),
                 bg='#444444', fg='white', relief='flat', width=4, pady=10,
                 command=lambda: self.show_afl_break_settings("Quarter Time")).pack(side='right', padx=(5, 0))
        
        # Half Time
        ht_frame = tk.Frame(break_frame, bg='#1a1a1a')
        ht_frame.pack(fill='x', pady=3)
        
        tk.Button(ht_frame, text="Half Time", font=('Helvetica', 12, 'bold'),
                 bg='#ff8800', fg='white', relief='flat', padx=15, pady=10,
                 command=lambda: self.show_afl_break("Half Time")).pack(side='left', fill='x', expand=True)
        
        tk.Button(ht_frame, text="⚙", font=('Helvetica', 11),
                 bg='#444444', fg='white', relief='flat', width=4, pady=10,
                 command=lambda: self.show_afl_break_settings("Half Time")).pack(side='right', padx=(5, 0))
        
        # 3/4 Time
        tqt_frame = tk.Frame(break_frame, bg='#1a1a1a')
        tqt_frame.pack(fill='x', pady=3)
        
        tk.Button(tqt_frame, text="3/4 Time", font=('Helvetica', 12, 'bold'),
                 bg='#ff8800', fg='white', relief='flat', padx=15, pady=10,
                 command=lambda: self.show_afl_break("3/4 Time")).pack(side='left', fill='x', expand=True)
        
        tk.Button(tqt_frame, text="⚙", font=('Helvetica', 11),
                 bg='#444444', fg='white', relief='flat', width=4, pady=10,
                 command=lambda: self.show_afl_break_settings("3/4 Time")).pack(side='right', padx=(5, 0))
        
        tk.Button(break_frame, text="Return to Scores", font=('Helvetica', 12, 'bold'),
                 bg='#0088ff', fg='white', relief='flat', padx=15, pady=10,
                 command=self.return_to_afl_scores).pack(fill='x', pady=3)
        
        # Advertisements
        ads_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        ads_frame.pack(fill='x', pady=(15, 5), padx=5, ipady=10)
        
        tk.Label(ads_frame, text="Advertisements", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(pady=(5, 10))
        
        # Advertisement dropdown and controls (similar to soccer)
        if len(self.advertisements) > 0:
            ad_choices = [f"Ad {i+1}: {ad['text'][:25]}..." if len(ad['text']) > 25 else f"Ad {i+1}: {ad['text']}" 
                         for i, ad in enumerate(self.advertisements)]
            current_index = min(self.current_ad_index, len(self.advertisements)-1)
        else:
            ad_choices = ["No advertisements"]
            current_index = 0
        
        selected_ad = tk.StringVar(value=ad_choices[current_index])
        dropdown = ttk.Combobox(ads_frame, textvariable=selected_ad, values=ad_choices,
                               state='readonly', font=('Helvetica', 10), width=28)
        dropdown.pack(pady=(0, 10))
        dropdown.current(current_index)
        dropdown.bind('<<ComboboxSelected>>', lambda e: setattr(self, 'current_ad_index', dropdown.current()))
        
        tk.Button(ads_frame, text="Start Advertisement", font=('Helvetica', 11, 'bold'),
                 bg='#00aa00', fg='white', relief='flat', padx=15, pady=8,
                 command=self.start_advertisement_from_afl).pack(fill='x', padx=10, pady=(0, 5))
        
        tk.Button(ads_frame, text="Return to Scores", font=('Helvetica', 11, 'bold'),
                 bg='#0088ff', fg='white', relief='flat', padx=15, pady=8,
                 command=self.return_to_afl_scores).pack(fill='x', padx=10, pady=(0, 10))
        
        manage_btns = tk.Frame(ads_frame, bg='#2a2a2a')
        manage_btns.pack(pady=(5, 10))
        
        tk.Button(manage_btns, text="+ Add", font=('Helvetica', 11, 'bold'),
                 bg='#6600cc', fg='white', relief='flat', padx=15, pady=8,
                 command=self.show_add_advertisement).pack(side='left', padx=3)
        
        tk.Button(manage_btns, text="✎ Edit", font=('Helvetica', 11, 'bold'),
                 bg='#0066cc', fg='white', relief='flat', padx=15, pady=8,
                 command=self.show_edit_advertisement).pack(side='left', padx=3)
        
        tk.Button(manage_btns, text="− Remove", font=('Helvetica', 11, 'bold'),
                 bg='#cc0000', fg='white', relief='flat', padx=12, pady=8,
                 command=self.show_remove_advertisements).pack(side='left', padx=3)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Send initial data
        self.update_afl_display()
    
    def set_afl_quarter(self, quarter):
        """Set AFL quarter"""
        self.current_quarter = quarter
        self.send_udp_command(f"*#1RAMT3,1211{quarter}0000")
        print(f"[AFL] Quarter set to {quarter}")
    
    def update_afl_team_name(self, team):
        """Update AFL team name"""
        if team == 'home':
            name = self.afl_home_name_entry.get().strip()
            if name:
                self.afl_home_name = name
                if hasattr(self, 'afl_home_label'):
                    self.afl_home_label.config(text=name)
                self.send_udp_command(f"*#1RAMT1,1311{name}0000")
        else:
            name = self.afl_away_name_entry.get().strip()
            if name:
                self.afl_away_name = name
                if hasattr(self, 'afl_away_label'):
                    self.afl_away_label.config(text=name)
                self.send_udp_command(f"*#1RAMT2,1311{name}0000")
    
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
    
    def show_afl_break(self, break_name):
        """Show AFL break screen with custom settings"""
        if not hasattr(self, 'afl_break_settings'):
            self.afl_break_settings = {
                'Quarter Time': {'color': '7', 'size': '2', 'h_align': '1', 'v_align': '1', 'text': '', 'scroll': False, 'scroll_speed': 700},
                'Half Time': {'color': '7', 'size': '2', 'h_align': '1', 'v_align': '1', 'text': '', 'scroll': False, 'scroll_speed': 700},
                '3/4 Time': {'color': '7', 'size': '2', 'h_align': '1', 'v_align': '1', 'text': '', 'scroll': False, 'scroll_speed': 700}
            }
        
        self.send_udp_command("*#1PRGC30,0000")
        
        settings = self.afl_break_settings[break_name]
        
        # Get text (custom or default)
        if settings.get('text'):
            text = settings['text']
        else:
            home_total = (getattr(self, 'afl_home_goals', 0) * 6) + getattr(self, 'afl_home_points', 0)
            away_total = (getattr(self, 'afl_away_goals', 0) * 6) + getattr(self, 'afl_away_points', 0)
            home_name = getattr(self, 'afl_home_name', 'HOME')
            away_name = getattr(self, 'afl_away_name', 'AWAY')
            text = f"{break_name}   {home_name} {home_total} - {away_total} {away_name}"
        
        color = settings['color']
        size = settings['size']
        h_align = settings.get('h_align', '1')
        v_align = settings.get('v_align', '1')
        
        # Check if scrolling
        if settings.get('scroll', False):
            speed = settings.get('scroll_speed', 700)
            self.root.after(120, lambda: self.start_scrolling_text(text, color, size, speed))
        else:
            self.root.after(120, lambda: self.send_udp_command(f"*#1RAMT1,{color}{size}{h_align}{v_align}{text}0000"))
        
        print(f"[AFL] {break_name} screen displayed")
    
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
        
        # Set team names
        home_name = getattr(self, 'afl_home_name', 'HOME')
        away_name = getattr(self, 'afl_away_name', 'AWAY')
        self.send_udp_command(f"*#1RAMT1,1311{home_name}0000")
        self.send_udp_command(f"*#1RAMT2,1311{away_name}0000")
        
        # Set quarter
        self.send_udp_command(f"*#1RAMT3,1211{self.current_quarter}0000")
    
    def start_advertisement_from_afl(self):
        """Start advertisement from AFL screen"""
        if len(self.advertisements) > 0:
            ad = self.advertisements[self.current_ad_index]
            self.send_udp_command("*#1PRGC30,0000")
            
            color = ad.get('colour', ad.get('color', '7'))
            size = ad['size']
            h_align = ad.get('h_align', '1')
            v_align = ad.get('v_align', '1')
            text = ad['text']
            
            if ad.get('scroll', False):
                speed = ad.get('scroll_speed', 700)
                self.root.after(120, lambda: self.start_scrolling_text(text, color, size, speed))
            else:
                self.root.after(120, lambda: self.send_udp_command(f"*#1RAMT1,{color}{size}{h_align}{v_align}{text}0000"))
    
    def reset_afl_scores(self, team):
        """Reset AFL scores for a team with confirmation"""
        team_name = self.afl_home_name if team == 'home' else self.afl_away_name
        
        if not messagebox.askyesno("Confirm Reset", f"Reset all scores for {team_name}?"):
            return
        
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
    
    def show_afl_quarter_settings(self):
        """Show AFL quarter text settings page"""
        # Initialize settings if not exists
        if not hasattr(self, 'afl_quarter_settings'):
            self.afl_quarter_settings = {'color': '1', 'size': '2', 'h_align': '1', 'v_align': '1'}
        
        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create scrollable frame
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
        top_bar.pack(fill='x', pady=(0, 10))
        
        tk.Button(top_bar, text="← Back", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 command=self.show_afl_ui).pack(side='left')
        
        tk.Label(main_frame, text="Quarter Display Settings", font=('Helvetica', 18, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=(0, 20))
        
        current = self.afl_quarter_settings
        
        # Colour and Size side by side
        cs_frame = tk.Frame(main_frame, bg='#1a1a1a')
        cs_frame.pack(fill='x', pady=(10, 5))
        
        # Colour (left)
        colour_section = tk.Frame(cs_frame, bg='#1a1a1a')
        colour_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(colour_section, text="Colour:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        color_var = tk.StringVar(value=current['color'])
        colors = [("Red", "1"), ("Green", "2"), ("Yellow", "3"), ("Blue", "4"),
                 ("Purple", "5"), ("Cyan", "6"), ("White", "7")]
        
        def on_color_change():
            self.afl_quarter_settings['color'] = color_var.get()
            self.send_udp_command(f"*#1RAMT3,{color_var.get()}{current['size']}{current['h_align']}{current['v_align']}{self.current_quarter}0000")
            self.save_config()
        
        for name, val in colors:
            tk.Radiobutton(colour_section, text=name, variable=color_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_color_change).pack(anchor='w', padx=10, pady=3)
        
        # Size (right)
        size_section = tk.Frame(cs_frame, bg='#1a1a1a')
        size_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(size_section, text="Size:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        size_var = tk.StringVar(value=current['size'])
        sizes = [("Very Small", "9"), ("Small", "1"), ("Medium", "2"), ("Large", "3"), ("Extra Large", "4")]
        
        def on_size_change():
            self.afl_quarter_settings['size'] = size_var.get()
            self.send_udp_command(f"*#1RAMT3,{current['color']}{size_var.get()}{current['h_align']}{current['v_align']}{self.current_quarter}0000")
            self.save_config()
        
        for name, val in sizes:
            tk.Radiobutton(size_section, text=name, variable=size_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_size_change).pack(anchor='w', padx=10, pady=3)
        
        # Horizontal and Vertical side by side
        align_frame = tk.Frame(main_frame, bg='#1a1a1a')
        align_frame.pack(fill='x', pady=(15, 5))
        
        # Horizontal (left)
        h_section = tk.Frame(align_frame, bg='#1a1a1a')
        h_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(h_section, text="Horizontal:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        h_align_var = tk.StringVar(value=current['h_align'])
        h_aligns = [("Center", "1"), ("Right", "2"), ("Left", "3")]
        
        def on_h_align_change():
            self.afl_quarter_settings['h_align'] = h_align_var.get()
            self.send_udp_command(f"*#1RAMT3,{current['color']}{current['size']}{h_align_var.get()}{current['v_align']}{self.current_quarter}0000")
            self.save_config()
        
        for name, val in h_aligns:
            tk.Radiobutton(h_section, text=name, variable=h_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_h_align_change).pack(anchor='w', padx=10, pady=3)
        
        # Vertical (right)
        v_section = tk.Frame(align_frame, bg='#1a1a1a')
        v_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(v_section, text="Vertical:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        v_align_var = tk.StringVar(value=current['v_align'])
        v_aligns = [("Center", "1"), ("Bottom", "2"), ("Top", "3")]
        
        def on_v_align_change():
            self.afl_quarter_settings['v_align'] = v_align_var.get()
            self.send_udp_command(f"*#1RAMT3,{current['color']}{current['size']}{current['h_align']}{v_align_var.get()}{self.current_quarter}0000")
            self.save_config()
        
        for name, val in v_aligns:
            tk.Radiobutton(v_section, text=name, variable=v_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_v_align_change).pack(anchor='w', padx=10, pady=3)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def show_afl_team_settings(self):
        """Show AFL team name settings page"""
        if not hasattr(self, 'afl_team_settings'):
            self.afl_team_settings = {'color': '1', 'size': '3', 'h_align': '1', 'v_align': '1'}
        
        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        canvas = tk.Canvas(self.root, bg='#1a1a1a', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#1a1a1a')
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        main_frame = tk.Frame(scrollable_frame, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Top bar
        top_bar = tk.Frame(main_frame, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 10))
        
        tk.Button(top_bar, text="← Back", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 command=self.show_afl_ui).pack(side='left')
        
        tk.Label(main_frame, text="AFL Team Names Settings", font=('Helvetica', 18, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=(0, 20))
        
        current = self.afl_team_settings
        
        # Colour and Size side by side
        cs_frame = tk.Frame(main_frame, bg='#1a1a1a')
        cs_frame.pack(fill='x', pady=(10, 5))
        
        # Colour (left)
        colour_section = tk.Frame(cs_frame, bg='#1a1a1a')
        colour_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(colour_section, text="Colour:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        color_var = tk.StringVar(value=current['color'])
        colors = [("Red", "1"), ("Green", "2"), ("Yellow", "3"), ("Blue", "4"),
                 ("Purple", "5"), ("Cyan", "6"), ("White", "7")]
        
        def on_color_change():
            self.afl_team_settings['color'] = color_var.get()
            c = color_var.get()
            s = current['size']
            h = current['h_align']
            v = current['v_align']
            self.send_udp_command(f"*#1RAMT1,{c}{s}{h}{v}{self.afl_home_name}0000")
            self.send_udp_command(f"*#1RAMT2,{c}{s}{h}{v}{self.afl_away_name}0000")
            self.save_config()
        
        for name, val in colors:
            tk.Radiobutton(colour_section, text=name, variable=color_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_color_change).pack(anchor='w', padx=10, pady=3)
        
        # Size (right)
        size_section = tk.Frame(cs_frame, bg='#1a1a1a')
        size_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(size_section, text="Size:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        size_var = tk.StringVar(value=current['size'])
        sizes = [("Very Small", "9"), ("Small", "1"), ("Medium", "2"), ("Large", "3"), ("Extra Large", "4")]
        
        def on_size_change():
            self.afl_team_settings['size'] = size_var.get()
            c = current['color']
            s = size_var.get()
            h = current['h_align']
            v = current['v_align']
            self.send_udp_command(f"*#1RAMT1,{c}{s}{h}{v}{self.afl_home_name}0000")
            self.send_udp_command(f"*#1RAMT2,{c}{s}{h}{v}{self.afl_away_name}0000")
            self.save_config()
        
        for name, val in sizes:
            tk.Radiobutton(size_section, text=name, variable=size_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_size_change).pack(anchor='w', padx=10, pady=3)
        
        # Horizontal and Vertical side by side
        align_frame = tk.Frame(main_frame, bg='#1a1a1a')
        align_frame.pack(fill='x', pady=(15, 5))
        
        # Horizontal (left)
        h_section = tk.Frame(align_frame, bg='#1a1a1a')
        h_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(h_section, text="Horizontal:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        h_align_var = tk.StringVar(value=current['h_align'])
        h_aligns = [("Center", "1"), ("Right", "2"), ("Left", "3")]
        
        def on_h_align_change():
            self.afl_team_settings['h_align'] = h_align_var.get()
            c = current['color']
            s = current['size']
            h = h_align_var.get()
            v = current['v_align']
            self.send_udp_command(f"*#1RAMT1,{c}{s}{h}{v}{self.afl_home_name}0000")
            self.send_udp_command(f"*#1RAMT2,{c}{s}{h}{v}{self.afl_away_name}0000")
            self.save_config()
        
        for name, val in h_aligns:
            tk.Radiobutton(h_section, text=name, variable=h_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_h_align_change).pack(anchor='w', padx=10, pady=3)
        
        # Vertical (right)
        v_section = tk.Frame(align_frame, bg='#1a1a1a')
        v_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(v_section, text="Vertical:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        v_align_var = tk.StringVar(value=current['v_align'])
        v_aligns = [("Center", "1"), ("Bottom", "2"), ("Top", "3")]
        
        def on_v_align_change():
            self.afl_team_settings['v_align'] = v_align_var.get()
            c = current['color']
            s = current['size']
            h = current['h_align']
            v = v_align_var.get()
            self.send_udp_command(f"*#1RAMT1,{c}{s}{h}{v}{self.afl_home_name}0000")
            self.send_udp_command(f"*#1RAMT2,{c}{s}{h}{v}{self.afl_away_name}0000")
            self.save_config()
        
        for name, val in v_aligns:
            tk.Radiobutton(v_section, text=name, variable=v_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_v_align_change).pack(anchor='w', padx=10, pady=3)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def show_afl_break_settings(self, break_name):
        """Show AFL break screen settings with full customization like Soccer halftime"""
        if not hasattr(self, 'afl_break_settings'):
            self.afl_break_settings = {
                'Quarter Time': {'color': '7', 'size': '2', 'h_align': '1', 'v_align': '1', 'text': '', 'scroll': False, 'scroll_speed': 700},
                'Half Time': {'color': '7', 'size': '2', 'h_align': '1', 'v_align': '1', 'text': '', 'scroll': False, 'scroll_speed': 700},
                '3/4 Time': {'color': '7', 'size': '2', 'h_align': '1', 'v_align': '1', 'text': '', 'scroll': False, 'scroll_speed': 700}
            }
        
        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        canvas = tk.Canvas(self.root, bg='#1a1a1a', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#1a1a1a')
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        main_frame = tk.Frame(scrollable_frame, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Top bar
        top_bar = tk.Frame(main_frame, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 10))
        
        tk.Button(top_bar, text="← Return", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 command=self.show_afl_ui).pack(side='left')
        
        tk.Label(main_frame, text=f"{break_name} Screen Settings", font=('Helvetica', 18, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=(0, 20))
        
        current = self.afl_break_settings[break_name]
        
        # Custom text input
        tk.Label(main_frame, text="Custom Text:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(10, 5))
        
        home_total = (getattr(self, 'afl_home_goals', 0) * 6) + getattr(self, 'afl_home_points', 0)
        away_total = (getattr(self, 'afl_away_goals', 0) * 6) + getattr(self, 'afl_away_points', 0)
        home_name = getattr(self, 'afl_home_name', 'HOME')
        away_name = getattr(self, 'afl_away_name', 'AWAY')
        
        default_text = f"{break_name}   {home_name} {home_total} - {away_total} {away_name}"
        text_var = tk.StringVar(value=current.get('text', default_text))
        
        text_entry = tk.Entry(main_frame, textvariable=text_var, font=('Helvetica', 14),
                             bg='#333333', fg='white', relief='flat', insertbackground='white')
        text_entry.pack(fill='x', pady=5, ipady=8)
        
        # Colour and Size side by side
        cs_frame = tk.Frame(main_frame, bg='#1a1a1a')
        cs_frame.pack(fill='x', pady=(15, 5))
        
        # Colour (left)
        colour_section = tk.Frame(cs_frame, bg='#1a1a1a')
        colour_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(colour_section, text="Colour:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        color_var = tk.StringVar(value=current['color'])
        colors = [("Red", "1"), ("Green", "2"), ("Yellow", "3"), ("Blue", "4"),
                 ("Purple", "5"), ("Cyan", "6"), ("White", "7")]
        
        for name, val in colors:
            tk.Radiobutton(colour_section, text=name, variable=color_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=3)
        
        # Size (right)
        size_section = tk.Frame(cs_frame, bg='#1a1a1a')
        size_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(size_section, text="Size:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        size_var = tk.StringVar(value=current['size'])
        sizes = [("Very Small", "9"), ("Small", "1"), ("Medium", "2"), ("Large", "3"), ("Extra Large", "4")]
        
        for name, val in sizes:
            tk.Radiobutton(size_section, text=name, variable=size_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=3)
        
        # Horizontal and Vertical side by side
        align_frame = tk.Frame(main_frame, bg='#1a1a1a')
        align_frame.pack(fill='x', pady=(15, 5))
        
        # Horizontal (left)
        h_section = tk.Frame(align_frame, bg='#1a1a1a')
        h_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(h_section, text="Horizontal:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        h_align_var = tk.StringVar(value=current.get('h_align', '1'))
        
        for name, val in [("Center", "1"), ("Right", "2"), ("Left", "3")]:
            tk.Radiobutton(h_section, text=name, variable=h_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=3)
        
        # Vertical (right)
        v_section = tk.Frame(align_frame, bg='#1a1a1a')
        v_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(v_section, text="Vertical:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        v_align_var = tk.StringVar(value=current.get('v_align', '1'))
        
        for name, val in [("Center", "1"), ("Bottom", "2"), ("Top", "3")]:
            tk.Radiobutton(v_section, text=name, variable=v_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=3)
        
        # Scrolling section
        scroll_var = tk.BooleanVar(value=current.get('scroll', False))
        scroll_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=1)
        scroll_frame.pack(fill='x', pady=(15, 5), ipady=10)
        
        tk.Checkbutton(scroll_frame, text="Enable Scrolling Text", variable=scroll_var,
                      font=('Helvetica', 12, 'bold'), bg='#2a2a2a', fg='white',
                      selectcolor='#333333', activebackground='#2a2a2a',
                      activeforeground='white').pack(anchor='w', padx=10, pady=5)
        
        tk.Label(scroll_frame, text="Scroll Speed:", font=('Helvetica', 11, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', padx=10, pady=(10, 5))
        
        speed_var = tk.IntVar(value=current.get('scroll_speed', 700))
        speed_slider = tk.Scale(scroll_frame, from_=200, to=1200, orient='horizontal',
                               variable=speed_var, font=('Helvetica', 10),
                               bg='#2a2a2a', fg='white', highlightthickness=0,
                               troughcolor='#444444', activebackground='#00aaff',
                               length=300, showvalue=True, label="ms delay")
        speed_slider.pack(padx=10, pady=(0, 10))
        
        tk.Label(scroll_frame, text="Lower = Faster  •  Higher = Slower",
                font=('Helvetica', 9, 'italic'), bg='#2a2a2a', fg='#888888').pack(pady=(0, 5))
        
        # Save and apply button
        def save_and_apply():
            self.afl_break_settings[break_name]['text'] = text_var.get()
            self.afl_break_settings[break_name]['color'] = color_var.get()
            self.afl_break_settings[break_name]['size'] = size_var.get()
            self.afl_break_settings[break_name]['h_align'] = h_align_var.get()
            self.afl_break_settings[break_name]['v_align'] = v_align_var.get()
            self.afl_break_settings[break_name]['scroll'] = scroll_var.get()
            self.afl_break_settings[break_name]['scroll_speed'] = speed_var.get()
            self.save_config()
            
            # Show the break screen
            self.show_afl_break(break_name)
            
            # Return to AFL screen
            self.show_afl_ui()
        
        tk.Button(main_frame, text="Save & Apply", font=('Helvetica', 14, 'bold'),
                 bg='#ff8800', fg='white', relief='flat', padx=30, pady=12,
                 command=save_and_apply).pack(pady=30)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def show_cricket_ui(self):
        """Show Cricket score management UI"""
        # Initialize Cricket-specific scores if not exists
        if not hasattr(self, 'cricket_home_runs'):
            self.cricket_home_runs = 0
            self.cricket_home_wickets = 0
            self.cricket_away_runs = 0
            self.cricket_away_wickets = 0
            self.cricket_extras = 0
            self.cricket_overs = 0
            self.cricket_balls = 0
            self.current_innings = "INN1"
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
        
        # Timer controls
        timer_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        timer_frame.pack(fill='x', pady=(0, 15), ipady=10)
        
        tk.Label(timer_frame, text="Timer Controls", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(pady=(5, 10))
        
        timer_btns = tk.Frame(timer_frame, bg='#2a2a2a')
        timer_btns.pack(pady=(0, 5))
        
        tk.Button(timer_btns, text="▶ Start", font=('Helvetica', 13, 'bold'),
                 bg='#00aa00', fg='white', relief='flat', padx=20, pady=10,
                 command=lambda: self.send_udp_command("*#1TIMS1,0000")).pack(side='left', padx=5)
        tk.Button(timer_btns, text="⏸ Pause", font=('Helvetica', 13, 'bold'),
                 bg='#ffaa00', fg='white', relief='flat', padx=20, pady=10,
                 command=lambda: self.send_udp_command("*#1TIMP1,0000")).pack(side='left', padx=5)
        tk.Button(timer_btns, text="↻ Reset", font=('Helvetica', 13, 'bold'),
                 bg='#cc0000', fg='white', relief='flat', padx=20, pady=10,
                 command=lambda: self.send_udp_command("*#1TIMR1,0000")).pack(side='left', padx=5)
        
        # Innings selection
        innings_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        innings_frame.pack(fill='x', pady=(0, 15), ipady=10)
        
        innings_header = tk.Frame(innings_frame, bg='#2a2a2a')
        innings_header.pack(fill='x', padx=10, pady=(5, 0))
        
        tk.Label(innings_header, text="INNINGS", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left')
        
        tk.Button(innings_header, text="⚙", font=('Helvetica', 11),
                 bg='#444444', fg='white', relief='flat', width=3,
                 command=self.show_cricket_innings_settings).pack(side='right')
        
        innings_btns = tk.Frame(innings_frame, bg='#2a2a2a')
        innings_btns.pack(pady=(10, 5))
        
        tk.Button(innings_btns, text="INN1", font=('Helvetica', 14, 'bold'),
                 bg='#0066cc', fg='white', relief='flat', width=8, pady=10,
                 command=lambda: self.set_cricket_innings("INN1")).pack(side='left', padx=5)
        tk.Button(innings_btns, text="INN2", font=('Helvetica', 14, 'bold'),
                 bg='#0066cc', fg='white', relief='flat', width=8, pady=10,
                 command=lambda: self.set_cricket_innings("INN2")).pack(side='left', padx=5)
        
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
        
        self.cricket_home_label = tk.Label(home_header, text=f"{self.cricket_home_name} BATTING", font=('Helvetica', 13, 'bold'),
                bg='#2a2a2a', fg='#00aaff')
        self.cricket_home_label.pack(side='left')
        
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
        
        self.cricket_home_runs_entry = tk.Entry(home_runs_frame, font=('Helvetica', 14),
                                                bg='#333333', fg='white', width=5,
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
        
        self.cricket_away_label = tk.Label(away_header, text=f"{self.cricket_away_name} BATTING", font=('Helvetica', 13, 'bold'),
                bg='#2a2a2a', fg='#ff6600')
        self.cricket_away_label.pack(side='left')
        
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
        
        self.cricket_away_runs_entry = tk.Entry(away_runs_frame, font=('Helvetica', 14),
                                                bg='#333333', fg='white', width=5,
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
        
        # EXTRAS AND OVERS - Prominent section for scorers
        extras_overs_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        extras_overs_frame.pack(fill='x', pady=(0, 10), ipady=10)
        
        # Header with reset button
        progress_header = tk.Frame(extras_overs_frame, bg='#2a2a2a')
        progress_header.pack(fill='x', padx=10, pady=(5, 0))
        
        tk.Label(progress_header, text="MATCH PROGRESS", font=('Helvetica', 13, 'bold'),
                bg='#2a2a2a', fg='#ffaa00').pack(side='left')
        
        tk.Button(progress_header, text="↻", font=('Helvetica', 12),
                 bg='#cc0000', fg='white', relief='flat', width=3,
                 command=self.reset_cricket_progress).pack(side='right', padx=2)
        
        tk.Label(extras_overs_frame, text="", bg='#2a2a2a').pack(pady=5)  # Spacer
        
        # Overs (C6) and Balls (C7) - Most important for scorers
        overs_frame = tk.Frame(extras_overs_frame, bg='#2a2a2a')
        overs_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(overs_frame, text="Overs:", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white', width=6, anchor='w').pack(side='left')
        
        # Overs before decimal
        tk.Button(overs_frame, text="−", font=('Helvetica', 14, 'bold'),
                 bg='#cc0000', fg='white', width=2, relief='flat',
                 command=lambda: self.adjust_cricket_overs(-1)).pack(side='left', padx=2)
        
        self.cricket_overs_entry = tk.Entry(overs_frame, font=('Helvetica', 16, 'bold'),
                                           bg='#333333', fg='#00ff00', width=3,
                                           relief='flat', insertbackground='white',
                                           justify='center')
        self.cricket_overs_entry.pack(side='left', padx=3)
        self.cricket_overs_entry.insert(0, str(self.cricket_overs))
        self.cricket_overs_entry.bind('<KeyRelease>', lambda e: self.manual_cricket_overs())
        
        tk.Button(overs_frame, text="+", font=('Helvetica', 14, 'bold'),
                 bg='#00aa00', fg='white', width=2, relief='flat',
                 command=lambda: self.adjust_cricket_overs(1)).pack(side='left', padx=2)
        
        tk.Label(overs_frame, text=".", font=('Helvetica', 20, 'bold'),
                bg='#2a2a2a', fg='white').pack(side='left', padx=3)
        
        # Balls after decimal (0-5 range)
        tk.Button(overs_frame, text="−", font=('Helvetica', 14, 'bold'),
                 bg='#cc0000', fg='white', width=2, relief='flat',
                 command=lambda: self.adjust_cricket_balls(-1)).pack(side='left', padx=2)
        
        self.cricket_balls_entry = tk.Entry(overs_frame, font=('Helvetica', 16, 'bold'),
                                           bg='#333333', fg='#00ff00', width=3,
                                           relief='flat', insertbackground='white',
                                           justify='center')
        self.cricket_balls_entry.pack(side='left', padx=3)
        self.cricket_balls_entry.insert(0, str(self.cricket_balls))
        self.cricket_balls_entry.bind('<KeyRelease>', lambda e: self.manual_cricket_balls())
        
        tk.Button(overs_frame, text="+", font=('Helvetica', 14, 'bold'),
                 bg='#00aa00', fg='white', width=2, relief='flat',
                 command=lambda: self.adjust_cricket_balls(1)).pack(side='left', padx=2)
        
        # Helper text
        tk.Label(extras_overs_frame, text="Balls auto-increment to next over at 6",
                font=('Helvetica', 9, 'italic'), bg='#2a2a2a', fg='#888888').pack(pady=(0, 5))
        
        # Extras (C5)
        extras_frame = tk.Frame(extras_overs_frame, bg='#2a2a2a')
        extras_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(extras_frame, text="Extras:", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white', width=6, anchor='w').pack(side='left')
        
        tk.Button(extras_frame, text="−", font=('Helvetica', 14, 'bold'),
                 bg='#cc0000', fg='white', width=2, relief='flat',
                 command=lambda: self.adjust_cricket_extras(-1)).pack(side='left', padx=2)
        
        self.cricket_extras_entry = tk.Entry(extras_frame, font=('Helvetica', 16, 'bold'),
                                            bg='#333333', fg='#ffaa00', width=4,
                                            relief='flat', insertbackground='white',
                                            justify='center')
        self.cricket_extras_entry.pack(side='left', padx=3)
        self.cricket_extras_entry.insert(0, str(self.cricket_extras))
        self.cricket_extras_entry.bind('<KeyRelease>', lambda e: self.manual_cricket_extras())
        
        tk.Button(extras_frame, text="+", font=('Helvetica', 14, 'bold'),
                 bg='#00aa00', fg='white', width=2, relief='flat',
                 command=lambda: self.adjust_cricket_extras(1)).pack(side='left', padx=2)
        
        tk.Label(extras_frame, text="(Wide, No-ball, Bye, Leg-bye)",
                font=('Helvetica', 9, 'italic'), bg='#2a2a2a', fg='#888888').pack(side='left', padx=10)
        
        # Break screen
        break_frame = tk.Frame(main_frame, bg='#1a1a1a')
        break_frame.pack(fill='x', pady=15)
        
        break_btn_frame = tk.Frame(break_frame, bg='#1a1a1a')
        break_btn_frame.pack(fill='x', pady=3)
        
        tk.Button(break_btn_frame, text="Break", font=('Helvetica', 12, 'bold'),
                 bg='#ff8800', fg='white', relief='flat', padx=15, pady=10,
                 command=self.show_cricket_break).pack(side='left', fill='x', expand=True)
        
        tk.Button(break_btn_frame, text="⚙", font=('Helvetica', 11),
                 bg='#444444', fg='white', relief='flat', width=4, pady=10,
                 command=self.show_cricket_break_settings).pack(side='right', padx=(5, 0))
        
        tk.Button(break_frame, text="Return to Scores", font=('Helvetica', 11, 'bold'),
                 bg='#0088ff', fg='white', relief='flat', padx=15, pady=8,
                 command=self.return_to_cricket_scores).pack(fill='x', pady=3)
        
        # Advertisements
        ads_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
        ads_frame.pack(fill='x', pady=(15, 5), ipady=10)
        
        tk.Label(ads_frame, text="Advertisements", font=('Helvetica', 12, 'bold'),
                bg='#2a2a2a', fg='white').pack(pady=(5, 10))
        
        if len(self.advertisements) > 0:
            ad_choices = [f"Ad {i+1}: {ad['text'][:25]}..." if len(ad['text']) > 25 else f"Ad {i+1}: {ad['text']}" 
                         for i, ad in enumerate(self.advertisements)]
            current_index = min(self.current_ad_index, len(self.advertisements)-1)
        else:
            ad_choices = ["No advertisements"]
            current_index = 0
        
        selected_ad = tk.StringVar(value=ad_choices[current_index])
        dropdown = ttk.Combobox(ads_frame, textvariable=selected_ad, values=ad_choices,
                               state='readonly', font=('Helvetica', 10), width=28)
        dropdown.pack(pady=(0, 10))
        dropdown.current(current_index)
        dropdown.bind('<<ComboboxSelected>>', lambda e: setattr(self, 'current_ad_index', dropdown.current()))
        
        tk.Button(ads_frame, text="Start Advertisement", font=('Helvetica', 11, 'bold'),
                 bg='#00aa00', fg='white', relief='flat', padx=15, pady=8,
                 command=self.start_advertisement_from_cricket).pack(fill='x', padx=10, pady=(0, 5))
        
        tk.Button(ads_frame, text="Return to Scores", font=('Helvetica', 11, 'bold'),
                 bg='#0088ff', fg='white', relief='flat', padx=15, pady=8,
                 command=self.return_to_cricket_scores).pack(fill='x', padx=10, pady=(0, 10))
        
        manage_btns = tk.Frame(ads_frame, bg='#2a2a2a')
        manage_btns.pack(pady=(5, 10))
        
        tk.Button(manage_btns, text="+ Add", font=('Helvetica', 11, 'bold'),
                 bg='#6600cc', fg='white', relief='flat', padx=15, pady=8,
                 command=self.show_add_advertisement).pack(side='left', padx=3)
        
        tk.Button(manage_btns, text="✎ Edit", font=('Helvetica', 11, 'bold'),
                 bg='#0066cc', fg='white', relief='flat', padx=15, pady=8,
                 command=self.show_edit_advertisement).pack(side='left', padx=3)
        
        tk.Button(manage_btns, text="− Remove", font=('Helvetica', 11, 'bold'),
                 bg='#cc0000', fg='white', relief='flat', padx=12, pady=8,
                 command=self.show_remove_advertisements).pack(side='left', padx=3)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Send initial data
        self.update_cricket_display()
    
    # Cricket supporting functions
    def set_cricket_innings(self, innings):
        """Set Cricket innings"""
        self.current_innings = innings
        self.send_udp_command(f"*#1RAMT3,1211{innings}0000")
        print(f"[CRICKET] Innings set to {innings}")
        self.save_config()
    
    def update_cricket_team_name(self, team):
        """Update Cricket team name"""
        if team == 'home':
            name = self.cricket_home_name_entry.get().strip()
            if name:
                self.cricket_home_name = name
                if hasattr(self, 'cricket_home_label'):
                    self.cricket_home_label.config(text=f"{name} BATTING")
                self.send_udp_command(f"*#1RAMT1,1311{name}0000")
        else:
            name = self.cricket_away_name_entry.get().strip()
            if name:
                self.cricket_away_name = name
                if hasattr(self, 'cricket_away_label'):
                    self.cricket_away_label.config(text=f"{name} BATTING")
                self.send_udp_command(f"*#1RAMT2,1311{name}0000")
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
        """Reset Cricket scores for a team with confirmation"""
        team_name = self.cricket_home_name if team == 'home' else self.cricket_away_name
        
        if not messagebox.askyesno("Confirm Reset", f"Reset all scores for {team_name}?"):
            return
        
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
    
    def reset_cricket_progress(self):
        """Reset Cricket overs and extras with confirmation"""
        if not messagebox.askyesno("Confirm Reset", "Reset Overs and Extras?"):
            return
        
        self.cricket_overs = 0
        self.cricket_balls = 0
        self.cricket_extras = 0
        
        self.cricket_overs_entry.delete(0, tk.END)
        self.cricket_overs_entry.insert(0, "0")
        self.cricket_balls_entry.delete(0, tk.END)
        self.cricket_balls_entry.insert(0, "0")
        self.cricket_extras_entry.delete(0, tk.END)
        self.cricket_extras_entry.insert(0, "0")
        
        self.send_udp_command("*#1CNTS5,S0,0000")  # Extras
        self.send_udp_command("*#1CNTS6,S0,0000")  # Overs
        self.send_udp_command("*#1CNTS7,S0,0000")  # Balls
        
        self.save_config()
        print("[CRICKET] Match progress reset")
    
    def show_cricket_team_settings(self):
        """Show Cricket team name settings page - full interactive like AFL"""
        if not hasattr(self, 'cricket_team_settings'):
            self.cricket_team_settings = {'color': '1', 'size': '3', 'h_align': '1', 'v_align': '1'}
        
        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        canvas = tk.Canvas(self.root, bg='#1a1a1a', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#1a1a1a')
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        main_frame = tk.Frame(scrollable_frame, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Top bar
        top_bar = tk.Frame(main_frame, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 10))
        
        tk.Button(top_bar, text="← Back", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 command=self.show_cricket_ui).pack(side='left')
        
        tk.Label(main_frame, text="Cricket Team Names Settings", font=('Helvetica', 18, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=(0, 20))
        
        current = self.cricket_team_settings
        
        # Colour and Size side by side
        cs_frame = tk.Frame(main_frame, bg='#1a1a1a')
        cs_frame.pack(fill='x', pady=(10, 5))
        
        # Colour (left)
        colour_section = tk.Frame(cs_frame, bg='#1a1a1a')
        colour_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(colour_section, text="Colour:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        color_var = tk.StringVar(value=current['color'])
        colors = [("Red", "1"), ("Green", "2"), ("Yellow", "3"), ("Blue", "4"),
                 ("Purple", "5"), ("Cyan", "6"), ("White", "7")]
        
        def on_color_change():
            self.cricket_team_settings['color'] = color_var.get()
            c = color_var.get()
            s = current['size']
            h = current['h_align']
            v = current['v_align']
            self.send_udp_command(f"*#1RAMT1,{c}{s}{h}{v}{self.cricket_home_name}0000")
            self.send_udp_command(f"*#1RAMT2,{c}{s}{h}{v}{self.cricket_away_name}0000")
            self.save_config()
        
        for name, val in colors:
            tk.Radiobutton(colour_section, text=name, variable=color_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_color_change).pack(anchor='w', padx=10, pady=3)
        
        # Size (right)
        size_section = tk.Frame(cs_frame, bg='#1a1a1a')
        size_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(size_section, text="Size:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        size_var = tk.StringVar(value=current['size'])
        sizes = [("Very Small", "9"), ("Small", "1"), ("Medium", "2"), ("Large", "3"), ("Extra Large", "4")]
        
        def on_size_change():
            self.cricket_team_settings['size'] = size_var.get()
            c = current['color']
            s = size_var.get()
            h = current['h_align']
            v = current['v_align']
            self.send_udp_command(f"*#1RAMT1,{c}{s}{h}{v}{self.cricket_home_name}0000")
            self.send_udp_command(f"*#1RAMT2,{c}{s}{h}{v}{self.cricket_away_name}0000")
            self.save_config()
        
        for name, val in sizes:
            tk.Radiobutton(size_section, text=name, variable=size_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_size_change).pack(anchor='w', padx=10, pady=3)
        
        # Horizontal and Vertical side by side
        align_frame = tk.Frame(main_frame, bg='#1a1a1a')
        align_frame.pack(fill='x', pady=(15, 5))
        
        # Horizontal (left)
        h_section = tk.Frame(align_frame, bg='#1a1a1a')
        h_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(h_section, text="Horizontal:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        h_align_var = tk.StringVar(value=current.get('h_align', '1'))
        
        def on_h_align_change():
            self.cricket_team_settings['h_align'] = h_align_var.get()
            c = current['color']
            s = current['size']
            h = h_align_var.get()
            v = current['v_align']
            self.send_udp_command(f"*#1RAMT1,{c}{s}{h}{v}{self.cricket_home_name}0000")
            self.send_udp_command(f"*#1RAMT2,{c}{s}{h}{v}{self.cricket_away_name}0000")
            self.save_config()
        
        for name, val in [("Center", "1"), ("Right", "2"), ("Left", "3")]:
            tk.Radiobutton(h_section, text=name, variable=h_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_h_align_change).pack(anchor='w', padx=10, pady=3)
        
        # Vertical (right)
        v_section = tk.Frame(align_frame, bg='#1a1a1a')
        v_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(v_section, text="Vertical:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        v_align_var = tk.StringVar(value=current.get('v_align', '1'))
        
        def on_v_align_change():
            self.cricket_team_settings['v_align'] = v_align_var.get()
            c = current['color']
            s = current['size']
            h = current['h_align']
            v = v_align_var.get()
            self.send_udp_command(f"*#1RAMT1,{c}{s}{h}{v}{self.cricket_home_name}0000")
            self.send_udp_command(f"*#1RAMT2,{c}{s}{h}{v}{self.cricket_away_name}0000")
            self.save_config()
        
        for name, val in [("Center", "1"), ("Bottom", "2"), ("Top", "3")]:
            tk.Radiobutton(v_section, text=name, variable=v_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_v_align_change).pack(anchor='w', padx=10, pady=3)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
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
        
        # Set team names
        self.send_udp_command(f"*#1RAMT1,1311{self.cricket_home_name}0000")
        self.send_udp_command(f"*#1RAMT2,1311{self.cricket_away_name}0000")
        
        # Set innings
        self.send_udp_command(f"*#1RAMT3,1211{self.current_innings}0000")
    
    def start_advertisement_from_cricket(self):
        """Start advertisement from Cricket screen"""
        if len(self.advertisements) > 0:
            ad = self.advertisements[self.current_ad_index]
            self.send_udp_command("*#1PRGC30,0000")
            
            color = ad.get('colour', ad.get('color', '7'))
            size = ad['size']
            h_align = ad.get('h_align', '1')
            v_align = ad.get('v_align', '1')
            text = ad['text']
            
            if ad.get('scroll', False):
                speed = ad.get('scroll_speed', 700)
                self.root.after(120, lambda: self.start_scrolling_text(text, color, size, speed))
            else:
                self.root.after(120, lambda: self.send_udp_command(f"*#1RAMT1,{color}{size}{h_align}{v_align}{text}0000"))
    
    def show_cricket_break(self):
        """Show Cricket break screen with custom settings"""
        if not hasattr(self, 'cricket_break_settings'):
            self.cricket_break_settings = {'color': '7', 'size': '2', 'h_align': '1', 'v_align': '1', 'text': '', 'scroll': False, 'scroll_speed': 700}
        
        self.send_udp_command("*#1PRGC30,0000")
        
        settings = self.cricket_break_settings
        
        # Get text (custom or default)
        if settings.get('text'):
            text = settings['text']
        else:
            home_score = f"{self.cricket_home_runs}/{self.cricket_home_wickets}"
            away_score = f"{self.cricket_away_runs}/{self.cricket_away_wickets}"
            text = f"Break   {self.cricket_home_name} {home_score} - {self.cricket_away_name} {away_score}"
        
        color = settings['color']
        size = settings['size']
        h_align = settings.get('h_align', '1')
        v_align = settings.get('v_align', '1')
        
        # Check if scrolling
        if settings.get('scroll', False):
            speed = settings.get('scroll_speed', 700)
            self.root.after(120, lambda: self.start_scrolling_text(text, color, size, speed))
        else:
            self.root.after(120, lambda: self.send_udp_command(f"*#1RAMT1,{color}{size}{h_align}{v_align}{text}0000"))
        
        print("[CRICKET] Break screen displayed")
    
    def show_cricket_break_settings(self):
        """Show Cricket break screen settings with full customization"""
        if not hasattr(self, 'cricket_break_settings'):
            self.cricket_break_settings = {'color': '7', 'size': '2', 'h_align': '1', 'v_align': '1', 'text': '', 'scroll': False, 'scroll_speed': 700}
        
        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        canvas = tk.Canvas(self.root, bg='#1a1a1a', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#1a1a1a')
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        main_frame = tk.Frame(scrollable_frame, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Top bar
        top_bar = tk.Frame(main_frame, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 10))
        
        tk.Button(top_bar, text="← Return", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 command=self.show_cricket_ui).pack(side='left')
        
        tk.Label(main_frame, text="Break Screen Settings", font=('Helvetica', 18, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=(0, 20))
        
        current = self.cricket_break_settings
        
        # Custom text input
        tk.Label(main_frame, text="Custom Text:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(10, 5))
        
        home_score = f"{self.cricket_home_runs}/{self.cricket_home_wickets}"
        away_score = f"{self.cricket_away_runs}/{self.cricket_away_wickets}"
        default_text = f"Break   {self.cricket_home_name} {home_score} - {self.cricket_away_name} {away_score}"
        text_var = tk.StringVar(value=current.get('text', default_text))
        
        text_entry = tk.Entry(main_frame, textvariable=text_var, font=('Helvetica', 14),
                             bg='#333333', fg='white', relief='flat', insertbackground='white')
        text_entry.pack(fill='x', pady=5, ipady=8)
        
        # Colour and Size side by side
        cs_frame = tk.Frame(main_frame, bg='#1a1a1a')
        cs_frame.pack(fill='x', pady=(15, 5))
        
        # Colour (left)
        colour_section = tk.Frame(cs_frame, bg='#1a1a1a')
        colour_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(colour_section, text="Colour:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        color_var = tk.StringVar(value=current['color'])
        colors = [("Red", "1"), ("Green", "2"), ("Yellow", "3"), ("Blue", "4"),
                 ("Purple", "5"), ("Cyan", "6"), ("White", "7")]
        
        for name, val in colors:
            tk.Radiobutton(colour_section, text=name, variable=color_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=3)
        
        # Size (right)
        size_section = tk.Frame(cs_frame, bg='#1a1a1a')
        size_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(size_section, text="Size:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        size_var = tk.StringVar(value=current['size'])
        sizes = [("Very Small", "9"), ("Small", "1"), ("Medium", "2"), ("Large", "3"), ("Extra Large", "4")]
        
        for name, val in sizes:
            tk.Radiobutton(size_section, text=name, variable=size_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=3)
        
        # Horizontal and Vertical side by side
        align_frame = tk.Frame(main_frame, bg='#1a1a1a')
        align_frame.pack(fill='x', pady=(15, 5))
        
        # Horizontal (left)
        h_section = tk.Frame(align_frame, bg='#1a1a1a')
        h_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(h_section, text="Horizontal:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        h_align_var = tk.StringVar(value=current.get('h_align', '1'))
        
        for name, val in [("Center", "1"), ("Right", "2"), ("Left", "3")]:
            tk.Radiobutton(h_section, text=name, variable=h_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=3)
        
        # Vertical (right)
        v_section = tk.Frame(align_frame, bg='#1a1a1a')
        v_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(v_section, text="Vertical:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        v_align_var = tk.StringVar(value=current.get('v_align', '1'))
        
        for name, val in [("Center", "1"), ("Bottom", "2"), ("Top", "3")]:
            tk.Radiobutton(v_section, text=name, variable=v_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=3)
        
        # Scrolling section
        scroll_var = tk.BooleanVar(value=current.get('scroll', False))
        scroll_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=1)
        scroll_frame.pack(fill='x', pady=(15, 5), ipady=10)
        
        tk.Checkbutton(scroll_frame, text="Enable Scrolling Text", variable=scroll_var,
                      font=('Helvetica', 12, 'bold'), bg='#2a2a2a', fg='white',
                      selectcolor='#333333', activebackground='#2a2a2a',
                      activeforeground='white').pack(anchor='w', padx=10, pady=5)
        
        tk.Label(scroll_frame, text="Scroll Speed:", font=('Helvetica', 11, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', padx=10, pady=(10, 5))
        
        speed_var = tk.IntVar(value=current.get('scroll_speed', 700))
        speed_slider = tk.Scale(scroll_frame, from_=200, to=1200, orient='horizontal',
                               variable=speed_var, font=('Helvetica', 10),
                               bg='#2a2a2a', fg='white', highlightthickness=0,
                               troughcolor='#444444', activebackground='#00aaff',
                               length=300, showvalue=True, label="ms delay")
        speed_slider.pack(padx=10, pady=(0, 10))
        
        tk.Label(scroll_frame, text="Lower = Faster  •  Higher = Slower",
                font=('Helvetica', 9, 'italic'), bg='#2a2a2a', fg='#888888').pack(pady=(0, 5))
        
        # Save and apply button
        def save_and_apply():
            self.cricket_break_settings['text'] = text_var.get()
            self.cricket_break_settings['color'] = color_var.get()
            self.cricket_break_settings['size'] = size_var.get()
            self.cricket_break_settings['h_align'] = h_align_var.get()
            self.cricket_break_settings['v_align'] = v_align_var.get()
            self.cricket_break_settings['scroll'] = scroll_var.get()
            self.cricket_break_settings['scroll_speed'] = speed_var.get()
            self.save_config()
            
            # Show the break screen
            self.show_cricket_break()
            
            # Return to Cricket screen
            self.show_cricket_ui()
        
        tk.Button(main_frame, text="Save & Apply", font=('Helvetica', 14, 'bold'),
                 bg='#ff8800', fg='white', relief='flat', padx=30, pady=12,
                 command=save_and_apply).pack(pady=30)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def show_cricket_innings_settings(self):
        """Show Cricket innings text settings page - like Soccer Half settings"""
        if not hasattr(self, 'cricket_innings_settings'):
            self.cricket_innings_settings = {'color': '1', 'size': '2', 'h_align': '1', 'v_align': '1'}
        
        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        canvas = tk.Canvas(self.root, bg='#1a1a1a', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#1a1a1a')
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        main_frame = tk.Frame(scrollable_frame, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Top bar
        top_bar = tk.Frame(main_frame, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 10))
        
        tk.Button(top_bar, text="← Return", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 command=self.show_cricket_ui).pack(side='left')
        
        tk.Label(main_frame, text="Innings Display Settings", font=('Helvetica', 18, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=(0, 20))
        
        current = self.cricket_innings_settings
        
        # Colour and Size side by side
        cs_frame = tk.Frame(main_frame, bg='#1a1a1a')
        cs_frame.pack(fill='x', pady=(10, 5))
        
        # Colour (left)
        colour_section = tk.Frame(cs_frame, bg='#1a1a1a')
        colour_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(colour_section, text="Colour:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        color_var = tk.StringVar(value=current['color'])
        colors = [("Red", "1"), ("Green", "2"), ("Yellow", "3"), ("Blue", "4"),
                 ("Purple", "5"), ("Cyan", "6"), ("White", "7")]
        
        def on_color_change():
            self.cricket_innings_settings['color'] = color_var.get()
            self.send_udp_command(f"*#1RAMT3,{color_var.get()}{current['size']}{current['h_align']}{current['v_align']}{self.current_innings}0000")
            self.save_config()
        
        for name, val in colors:
            tk.Radiobutton(colour_section, text=name, variable=color_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_color_change).pack(anchor='w', padx=10, pady=3)
        
        # Size (right)
        size_section = tk.Frame(cs_frame, bg='#1a1a1a')
        size_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(size_section, text="Size:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        size_var = tk.StringVar(value=current['size'])
        sizes = [("Very Small", "9"), ("Small", "1"), ("Medium", "2"), ("Large", "3"), ("Extra Large", "4")]
        
        def on_size_change():
            self.cricket_innings_settings['size'] = size_var.get()
            self.send_udp_command(f"*#1RAMT3,{current['color']}{size_var.get()}{current['h_align']}{current['v_align']}{self.current_innings}0000")
            self.save_config()
        
        for name, val in sizes:
            tk.Radiobutton(size_section, text=name, variable=size_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_size_change).pack(anchor='w', padx=10, pady=3)
        
        # Horizontal and Vertical side by side
        align_frame = tk.Frame(main_frame, bg='#1a1a1a')
        align_frame.pack(fill='x', pady=(15, 5))
        
        # Horizontal (left)
        h_section = tk.Frame(align_frame, bg='#1a1a1a')
        h_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(h_section, text="Horizontal:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        h_align_var = tk.StringVar(value=current.get('h_align', '1'))
        
        def on_h_align_change():
            self.cricket_innings_settings['h_align'] = h_align_var.get()
            self.send_udp_command(f"*#1RAMT3,{current['color']}{current['size']}{h_align_var.get()}{current['v_align']}{self.current_innings}0000")
            self.save_config()
        
        for name, val in [("Center", "1"), ("Right", "2"), ("Left", "3")]:
            tk.Radiobutton(h_section, text=name, variable=h_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_h_align_change).pack(anchor='w', padx=10, pady=3)
        
        # Vertical (right)
        v_section = tk.Frame(align_frame, bg='#1a1a1a')
        v_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(v_section, text="Vertical:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        v_align_var = tk.StringVar(value=current.get('v_align', '1'))
        
        def on_v_align_change():
            self.cricket_innings_settings['v_align'] = v_align_var.get()
            self.send_udp_command(f"*#1RAMT3,{current['color']}{current['size']}{current['h_align']}{v_align_var.get()}{self.current_innings}0000")
            self.save_config()
        
        for name, val in [("Center", "1"), ("Bottom", "2"), ("Top", "3")]:
            tk.Radiobutton(v_section, text=name, variable=v_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', command=on_v_align_change).pack(anchor='w', padx=10, pady=3)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
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
    
    # Timer functions
    def start_timer(self):
        """Start timer"""
        self.send_udp_command("*#1TIMS1,0000")
        self.timer_running = True
        print("[INFO] Timer started")
    
    def pause_timer(self):
        """Pause timer"""
        self.send_udp_command("*#1TIMP1,0000")
        self.timer_running = False
        print("[INFO] Timer paused")
    
    def reset_timer(self):
        """Reset timer"""
        self.send_udp_command("*#1TIMR1,0000")
        self.timer_running = False
        print("[INFO] Timer reset")
    
    # Half functions
    def set_first_half(self):
        """Set to 1st half"""
        color = self.half_settings['color']
        size = self.half_settings['size']
        h_align = self.half_settings.get('h_align', '1')
        v_align = self.half_settings.get('v_align', '1')
        self.send_udp_command(f"*#1RAMT3,{color}{size}{h_align}{v_align}1st HALF0000")
        self.current_half = "1st HALF"
        self.save_config()
        print("[INFO] Set to 1st HALF")
    
    def set_second_half(self):
        """Set to 2nd half"""
        color = self.half_settings['color']
        size = self.half_settings['size']
        h_align = self.half_settings.get('h_align', '1')
        v_align = self.half_settings.get('v_align', '1')
        self.send_udp_command(f"*#1RAMT3,{color}{size}{h_align}{v_align}2nd HALF0000")
        self.current_half = "2nd HALF"
        self.save_config()
        print("[INFO] Set to 2nd HALF")
    
    # Team name functions
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
                self.save_config()
                print(f"[INFO] Home team updated to: {self.home_name}")
        else:
            new_name = self.away_name_entry.get().strip()
            if new_name:
                self.away_name = new_name
                self.send_team_name_update('away')
                self.save_config()
                print(f"[INFO] Away team updated to: {self.away_name}")
    
    def send_team_name_update(self, team):
        """Send team name update using stored values (doesn't access entry widgets)"""
        color = self.team_settings['color']
        size = self.team_settings['size']
        h_align = self.team_settings.get('h_align', '1')
        v_align = self.team_settings.get('v_align', '1')
        
        if team == 'home':
            self.send_udp_command(f"*#1RAMT1,{color}{size}{h_align}{v_align}{self.home_name}0000")
        else:
            self.send_udp_command(f"*#1RAMT2,{color}{size}{h_align}{v_align}{self.away_name}0000")
    
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
                self.send_udp_command("*#1CNTS1,A1,0000")
            else:
                self.send_udp_command("*#1CNTS1,D1,0000")
            
            print(f"[INFO] Home score: {self.home_score}")
        else:
            self.away_score = max(0, self.away_score + delta)
            self.away_score_entry.delete(0, tk.END)
            self.away_score_entry.insert(0, str(self.away_score))
            
            if delta > 0:
                self.send_udp_command("*#1CNTS2,A1,0000")
            else:
                self.send_udp_command("*#1CNTS2,D1,0000")
            
            print(f"[INFO] Away score: {self.away_score}")
        
        self.save_config()
    
    def reset_scores(self):
        """Reset all scores to 0"""
        result = messagebox.askyesno("Confirm Reset", 
                                     f"Reset scores for {self.home_name} and {self.away_name}?",
                                     icon='warning')
        if result:
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
    
    # Screen functions
    def show_halftime_settings(self):
        """Show halftime screen settings page with custom text and alignments"""
        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create scrollable frame
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
        
        # Top bar with back button
        top_bar = tk.Frame(main_frame, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 10))
        
        tk.Button(top_bar, text="← Return", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 activebackground='#555555', activeforeground='white',
                 command=self.show_soccer_ui).pack(side='left', anchor='w')
        
        tk.Label(main_frame, text="Half Time Screen Settings", font=('Helvetica', 18, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=(0, 20))
        
        # Custom text input
        tk.Label(main_frame, text="Custom Text:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(10, 5))
        
        # Default format: "Half Time   Home: X - Y Away:"
        default_text = f"Half Time   {self.home_name}: {self.home_score} - {self.away_score} {self.away_name}"
        text_var = tk.StringVar(value=self.halftime_screen_settings.get('text', default_text))
        
        text_entry = tk.Entry(main_frame, textvariable=text_var, font=('Helvetica', 14), 
                             bg='#333333', fg='white', relief='flat', insertbackground='white')
        text_entry.pack(fill='x', pady=5, ipady=8)
        
        # Colour and Size side by side
        cs_frame = tk.Frame(main_frame, bg='#1a1a1a')
        cs_frame.pack(fill='x', pady=(15, 5))
        
        # Colour (left side)
        colour_section = tk.Frame(cs_frame, bg='#1a1a1a')
        colour_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(colour_section, text="Colour:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        color_var = tk.StringVar(value=self.halftime_screen_settings['color'])
        colors = [("Red", "1"), ("Green", "2"), ("Yellow", "3"), ("Blue", "4"),
                 ("Purple", "5"), ("Cyan", "6"), ("White", "7")]
        
        for name, val in colors:
            tk.Radiobutton(colour_section, text=name, variable=color_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=3)
        
        # Size (right side)
        size_section = tk.Frame(cs_frame, bg='#1a1a1a')
        size_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(size_section, text="Size:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        size_var = tk.StringVar(value=self.halftime_screen_settings['size'])
        sizes = [("Very Small", "9"), ("Small", "1"), ("Medium", "2"), ("Large", "3"), ("Extra Large", "4")]
        
        for name, val in sizes:
            tk.Radiobutton(size_section, text=name, variable=size_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=3)
        
        # Horizontal and Vertical side by side
        align_frame = tk.Frame(main_frame, bg='#1a1a1a')
        align_frame.pack(fill='x', pady=(15, 5))
        
        # Horizontal (left side)
        h_section = tk.Frame(align_frame, bg='#1a1a1a')
        h_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(h_section, text="Horizontal:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        h_align_var = tk.StringVar(value=self.halftime_screen_settings.get('h_align', '1'))
        
        for name, val in [("Center", "1"), ("Right", "2"), ("Left", "3")]:
            tk.Radiobutton(h_section, text=name, variable=h_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=3)
        
        # Vertical (right side)
        v_section = tk.Frame(align_frame, bg='#1a1a1a')
        v_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(v_section, text="Vertical:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        v_align_var = tk.StringVar(value=self.halftime_screen_settings.get('v_align', '1'))
        
        for name, val in [("Center", "1"), ("Bottom", "2"), ("Top", "3")]:
            tk.Radiobutton(v_section, text=name, variable=v_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=3)
        
        # Save and show button
        def save_and_apply():
            # Save settings
            self.halftime_screen_settings['text'] = text_var.get()
            self.halftime_screen_settings['color'] = color_var.get()
            self.halftime_screen_settings['size'] = size_var.get()
            self.halftime_screen_settings['h_align'] = h_align_var.get()
            self.halftime_screen_settings['v_align'] = v_align_var.get()
            self.save_config()
            
            # Show halftime screen
            self.show_halftime_screen()
            
            # Return to match screen
            self.show_soccer_ui()
        
        tk.Button(main_frame, text="Save & Apply", font=('Helvetica', 14, 'bold'),
                 bg='#ff8800', fg='white', relief='flat', padx=30, pady=12,
                 command=save_and_apply).pack(pady=30)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def show_halftime_screen(self):
        """Show half time screen with custom settings"""
        self.send_udp_command("*#1PRGC30,0000")
        
        # Get settings
        text = self.halftime_screen_settings.get('text', f"Half Time - {self.home_name} {self.home_score} - {self.away_score} {self.away_name}")
        color = self.halftime_screen_settings['color']
        size = self.halftime_screen_settings['size']
        h_align = self.halftime_screen_settings.get('h_align', '1')
        v_align = self.halftime_screen_settings.get('v_align', '1')
        
        self.root.after(120, lambda: self.send_udp_command(f"*#1RAMT1,{color}{size}{h_align}{v_align}{text}0000"))
        print("[INFO] Half Time screen displayed")
    
    def show_add_advertisement(self):
        """Show add advertisement screen"""
        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create scrollable frame
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
        top_bar.pack(fill='x', pady=(0, 10))
        
        tk.Button(top_bar, text="← Back to Scores", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 command=self.show_soccer_ui).pack(side='left')
        
        tk.Label(main_frame, text="Add Advertisement", font=('Helvetica', 18, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=(0, 20))
        
        # Text input
        tk.Label(main_frame, text="Advertisement Text:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(10, 5))
        
        text_var = tk.StringVar(value="")
        text_entry = tk.Entry(main_frame, textvariable=text_var, font=('Helvetica', 14),
                             bg='#333333', fg='white', relief='flat', insertbackground='white')
        text_entry.pack(fill='x', pady=5, ipady=8)
        
        # Color and Size side by side
        cs_frame = tk.Frame(main_frame, bg='#1a1a1a')
        cs_frame.pack(fill='x', pady=(15, 5))
        
        # Color (left side)
        colour_section = tk.Frame(cs_frame, bg='#1a1a1a')
        colour_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(colour_section, text="Colour:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        color_var = tk.StringVar(value="7")
        colors = [("Red", "1"), ("Green", "2"), ("Yellow", "3"), ("Blue", "4"),
                 ("Purple", "5"), ("Cyan", "6"), ("White", "7")]
        
        for name, val in colors:
            tk.Radiobutton(colour_section, text=name, variable=color_var, value=val,
                          font=('Helvetica', 10), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=2)
        
        # Size (right side)
        size_section = tk.Frame(cs_frame, bg='#1a1a1a')
        size_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(size_section, text="Size:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        size_var = tk.StringVar(value="2")
        sizes = [("Very Small", "9"), ("Small", "1"), ("Medium", "2"), ("Large", "3"), ("Extra Large", "4")]
        
        for name, val in sizes:
            tk.Radiobutton(size_section, text=name, variable=size_var, value=val,
                          font=('Helvetica', 10), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=2)
        
        # Horizontal and Vertical side by side
        align_frame = tk.Frame(main_frame, bg='#1a1a1a')
        align_frame.pack(fill='x', pady=(15, 5))
        
        # Horizontal (left side)
        h_section = tk.Frame(align_frame, bg='#1a1a1a')
        h_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(h_section, text="Horizontal:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        h_align_var = tk.StringVar(value="1")
        for name, val in [("Center", "1"), ("Right", "2"), ("Left", "3")]:
            tk.Radiobutton(h_section, text=name, variable=h_align_var, value=val,
                          font=('Helvetica', 10), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=2)
        
        # Vertical (right side)
        v_section = tk.Frame(align_frame, bg='#1a1a1a')
        v_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(v_section, text="Vertical:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        v_align_var = tk.StringVar(value="1")
        for name, val in [("Center", "1"), ("Bottom", "2"), ("Top", "3")]:
            tk.Radiobutton(v_section, text=name, variable=v_align_var, value=val,
                          font=('Helvetica', 10), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=2)
        
        # Scrolling
        scroll_var = tk.BooleanVar(value=False)
        scroll_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=1)
        scroll_frame.pack(fill='x', pady=(15, 5), ipady=10)
        
        tk.Checkbutton(scroll_frame, text="Enable Scrolling", variable=scroll_var,
                      font=('Helvetica', 11, 'bold'), bg='#2a2a2a', fg='white',
                      selectcolor='#333333', activebackground='#2a2a2a',
                      activeforeground='white').pack(anchor='w', pady=(5, 5), padx=10)
        
        # Scrolling tip
        tip_label = tk.Label(scroll_frame, 
                            text="💡 Tip: Add spaces before/after text to scroll across entire screen",
                            font=('Helvetica', 9, 'italic'), bg='#2a2a2a', fg='#ffaa00',
                            wraplength=350, justify='left')
        tip_label.pack(padx=10, pady=(0, 10))
        
        # Scroll speed
        tk.Label(scroll_frame, text="Scroll Speed:", font=('Helvetica', 10, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', padx=10, pady=(0, 5))
        
        speed_var = tk.IntVar(value=700)
        
        speed_options = [
            ("Very Slow", 1000),
            ("Slow", 800),
            ("Normal", 700),
            ("Fast", 500),
            ("Very Fast", 300)
        ]
        
        for name, val in speed_options:
            tk.Radiobutton(scroll_frame, text=name, variable=speed_var, value=val,
                          font=('Helvetica', 10), bg='#2a2a2a', fg='white',
                          selectcolor='#333333', activebackground='#2a2a2a',
                          activeforeground='white').pack(anchor='w', padx=20, pady=2)
        
        # Preview and Save buttons
        button_frame = tk.Frame(main_frame, bg='#1a1a1a')
        button_frame.pack(pady=20)
        
        def preview_ad():
            text = text_var.get()
            if not text:
                return
            
            self.send_udp_command("*#1PRGC30,0000")
            color = color_var.get()
            size = size_var.get()
            h_align = h_align_var.get()
            v_align = v_align_var.get()
            
            if scroll_var.get():
                speed = speed_var.get()
                self.root.after(120, lambda: self.start_scrolling_text(text, color, size, speed))
            else:
                self.root.after(120, lambda: self.send_udp_command(f"*#1RAMT1,{color}{size}{h_align}{v_align}{text}0000"))
        
        def save_ad():
            text = text_var.get()
            if not text:
                return
            
            ad = {
                'text': text,
                'colour': color_var.get(),
                'size': size_var.get(),
                'h_align': h_align_var.get(),
                'v_align': v_align_var.get(),
                'scroll': scroll_var.get(),
                'scroll_speed': speed_var.get()
            }
            
            self.advertisements.append(ad)
            self.save_config()
            
            # Stop scrolling and return to scores with refresh
            self.stop_scrolling_text()
            self.return_to_scores()
        
        tk.Button(button_frame, text="Preview", font=('Helvetica', 13, 'bold'),
                 bg='#0066cc', fg='white', relief='flat', padx=25, pady=10,
                 command=preview_ad).pack(side='left', padx=5)
        
        tk.Button(button_frame, text="Save", font=('Helvetica', 13, 'bold'),
                 bg='#00aa00', fg='white', relief='flat', padx=30, pady=10,
                 command=save_ad).pack(side='left', padx=5)
        
        # Pack canvas
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def show_edit_advertisement(self):
        """Show edit advertisement screen"""
        if len(self.advertisements) == 0:
            return
        
        # Get current advertisement to edit
        ad = self.advertisements[self.current_ad_index]
        
        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create scrollable frame
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
        top_bar.pack(fill='x', pady=(0, 10))
        
        tk.Button(top_bar, text="← Back to Scores", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 command=self.show_soccer_ui).pack(side='left')
        
        tk.Label(main_frame, text="Edit Advertisement", 
                font=('Helvetica', 18, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=(0, 15))
        
        # Advertisement selector dropdown
        tk.Label(main_frame, text="Select Advertisement to Edit:", font=('Helvetica', 11, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(5, 5))
        
        if len(self.advertisements) == 0:
            ad_choices = ["No advertisements"]
        else:
            ad_choices = [f"Ad {i+1}: {ad['text'][:30]}..." if len(ad['text']) > 30 else f"Ad {i+1}: {ad['text']}" 
                         for i, ad in enumerate(self.advertisements)]
        
        selected_ad_var = tk.StringVar(value=ad_choices[self.current_ad_index])
        
        ad_dropdown = ttk.Combobox(main_frame, textvariable=selected_ad_var, 
                                   values=ad_choices, state='readonly',
                                   font=('Helvetica', 11), width=35)
        ad_dropdown.pack(pady=(0, 15))
        ad_dropdown.current(self.current_ad_index)
        
        def on_ad_change(event):
            self.current_ad_index = ad_dropdown.current()
            self.save_config()
            # Reload the edit page with new selection
            self.show_edit_advertisement()
        
        ad_dropdown.bind('<<ComboboxSelected>>', on_ad_change)
        
        # Text input
        tk.Label(main_frame, text="Advertisement Text:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(10, 5))
        
        text_var = tk.StringVar(value=ad['text'])
        text_entry = tk.Entry(main_frame, textvariable=text_var, font=('Helvetica', 14),
                             bg='#333333', fg='white', relief='flat', insertbackground='white')
        text_entry.pack(fill='x', pady=5, ipady=8)
        
        # Color and Size side by side
        cs_frame = tk.Frame(main_frame, bg='#1a1a1a')
        cs_frame.pack(fill='x', pady=(15, 5))
        
        # Color (left side)
        colour_section = tk.Frame(cs_frame, bg='#1a1a1a')
        colour_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(colour_section, text="Colour:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        color_var = tk.StringVar(value=ad.get('colour', ad.get('color', '7')))
        colors = [("Red", "1"), ("Green", "2"), ("Yellow", "3"), ("Blue", "4"),
                 ("Purple", "5"), ("Cyan", "6"), ("White", "7")]
        
        for name, val in colors:
            tk.Radiobutton(colour_section, text=name, variable=color_var, value=val,
                          font=('Helvetica', 10), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=2)
        
        # Size (right side)
        size_section = tk.Frame(cs_frame, bg='#1a1a1a')
        size_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(size_section, text="Size:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        size_var = tk.StringVar(value=ad['size'])
        sizes = [("Very Small", "9"), ("Small", "1"), ("Medium", "2"), ("Large", "3"), ("Extra Large", "4")]
        
        for name, val in sizes:
            tk.Radiobutton(size_section, text=name, variable=size_var, value=val,
                          font=('Helvetica', 10), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=2)
        
        # Horizontal and Vertical side by side
        align_frame = tk.Frame(main_frame, bg='#1a1a1a')
        align_frame.pack(fill='x', pady=(15, 5))
        
        # Horizontal (left side)
        h_section = tk.Frame(align_frame, bg='#1a1a1a')
        h_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(h_section, text="Horizontal:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        h_align_var = tk.StringVar(value=ad.get('h_align', '1'))
        for name, val in [("Center", "1"), ("Right", "2"), ("Left", "3")]:
            tk.Radiobutton(h_section, text=name, variable=h_align_var, value=val,
                          font=('Helvetica', 10), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=2)
        
        # Vertical (right side)
        v_section = tk.Frame(align_frame, bg='#1a1a1a')
        v_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(v_section, text="Vertical:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        v_align_var = tk.StringVar(value=ad.get('v_align', '1'))
        for name, val in [("Center", "1"), ("Bottom", "2"), ("Top", "3")]:
            tk.Radiobutton(v_section, text=name, variable=v_align_var, value=val,
                          font=('Helvetica', 10), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=2)
        
        # Scrolling
        scroll_var = tk.BooleanVar(value=ad.get('scroll', False))
        scroll_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=1)
        scroll_frame.pack(fill='x', pady=(15, 5), ipady=10)
        
        tk.Checkbutton(scroll_frame, text="Enable Scrolling", variable=scroll_var,
                      font=('Helvetica', 11, 'bold'), bg='#2a2a2a', fg='white',
                      selectcolor='#333333', activebackground='#2a2a2a',
                      activeforeground='white').pack(anchor='w', pady=(5, 5), padx=10)
        
        # Scrolling tip
        tip_label = tk.Label(scroll_frame, 
                            text="💡 Tip: Add spaces before/after text to scroll across entire screen",
                            font=('Helvetica', 9, 'italic'), bg='#2a2a2a', fg='#ffaa00',
                            wraplength=350, justify='left')
        tip_label.pack(padx=10, pady=(0, 10))
        
        # Scroll speed
        tk.Label(scroll_frame, text="Scroll Speed:", font=('Helvetica', 10, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', padx=10, pady=(0, 5))
        
        speed_var = tk.IntVar(value=ad.get('scroll_speed', 700))
        
        speed_options = [
            ("Very Slow", 1000),
            ("Slow", 800),
            ("Normal", 700),
            ("Fast", 500),
            ("Very Fast", 300)
        ]
        
        for name, val in speed_options:
            tk.Radiobutton(scroll_frame, text=name, variable=speed_var, value=val,
                          font=('Helvetica', 10), bg='#2a2a2a', fg='white',
                          selectcolor='#333333', activebackground='#2a2a2a',
                          activeforeground='white').pack(anchor='w', padx=20, pady=2)
        
        # Preview and Save buttons
        button_frame = tk.Frame(main_frame, bg='#1a1a1a')
        button_frame.pack(pady=20)
        
        def preview_ad():
            text = text_var.get()
            if not text:
                return
            
            self.send_udp_command("*#1PRGC30,0000")
            color = color_var.get()
            size = size_var.get()
            h_align = h_align_var.get()
            v_align = v_align_var.get()
            
            if scroll_var.get():
                speed = speed_var.get()
                self.root.after(120, lambda: self.start_scrolling_text(text, color, size, speed))
            else:
                self.root.after(120, lambda: self.send_udp_command(f"*#1RAMT1,{color}{size}{h_align}{v_align}{text}0000"))
        
        def save_ad():
            text = text_var.get()
            if not text:
                return
            
            # Update the advertisement at current index
            self.advertisements[self.current_ad_index] = {
                'text': text,
                'colour': color_var.get(),
                'size': size_var.get(),
                'h_align': h_align_var.get(),
                'v_align': v_align_var.get(),
                'scroll': scroll_var.get(),
                'scroll_speed': speed_var.get()
            }
            
            self.save_config()
            
            # Stop scrolling and return to scores with refresh
            self.stop_scrolling_text()
            self.return_to_scores()
        
        tk.Button(button_frame, text="Preview", font=('Helvetica', 13, 'bold'),
                 bg='#0066cc', fg='white', relief='flat', padx=25, pady=10,
                 command=preview_ad).pack(side='left', padx=5)
        
        tk.Button(button_frame, text="Save", font=('Helvetica', 13, 'bold'),
                 bg='#00aa00', fg='white', relief='flat', padx=30, pady=10,
                 command=save_ad).pack(side='left', padx=5)
        
        # Pack canvas
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def show_remove_advertisements(self):
        """Show remove advertisements screen"""
        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        main_frame = tk.Frame(self.root, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Top bar
        top_bar = tk.Frame(main_frame, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 10))
        
        tk.Button(top_bar, text="← Back to Scores", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 command=self.show_soccer_ui).pack(side='left')
        
        tk.Label(main_frame, text="Remove Advertisements", font=('Helvetica', 18, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=(0, 20))
        
        if len(self.advertisements) == 0:
            tk.Label(main_frame, text="No advertisements to remove", 
                    font=('Helvetica', 14), bg='#1a1a1a', fg='#888888').pack(pady=50)
        else:
            # List advertisements
            for i, ad in enumerate(self.advertisements):
                ad_frame = tk.Frame(main_frame, bg='#2a2a2a', relief='ridge', bd=2)
                ad_frame.pack(fill='x', pady=5)
                
                text_display = ad['text'][:50] + "..." if len(ad['text']) > 50 else ad['text']
                
                tk.Label(ad_frame, text=f"Ad {i+1}: {text_display}",
                        font=('Helvetica', 11), bg='#2a2a2a', fg='white',
                        anchor='w').pack(side='left', padx=10, pady=10, fill='x', expand=True)
                
                tk.Button(ad_frame, text="✕", font=('Helvetica', 14, 'bold'),
                         bg='#cc0000', fg='white', relief='flat', width=4,
                         command=lambda idx=i: self.remove_advertisement(idx)).pack(side='right', padx=10, pady=5)
    
    def remove_advertisement(self, index):
        """Remove advertisement at index"""
        if 0 <= index < len(self.advertisements):
            self.advertisements.pop(index)
            if self.current_ad_index >= len(self.advertisements):
                self.current_ad_index = max(0, len(self.advertisements) - 1)
            self.save_config()
            self.show_remove_advertisements()  # Refresh the screen
        """Show full time screen"""
        self.send_udp_command("*#1PRGC30,0000")
        self.root.after(100, lambda: self.send_udp_command("*#1RAMT1,1211Full Time0000"))
        print("[INFO] Full Time screen displayed")
    
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
        
        # Send team names
        color = self.team_settings['color']
        size = self.team_settings['size']
        h_align = self.team_settings.get('h_align', '1')
        v_align = self.team_settings.get('v_align', '1')
        self.send_udp_command(f"*#1RAMT1,{color}{size}{h_align}{v_align}{self.home_name}0000")
        self.send_udp_command(f"*#1RAMT2,{color}{size}{h_align}{v_align}{self.away_name}0000")
        
        # Send half
        half_color = self.half_settings['color']
        half_size = self.half_settings['size']
        half_h_align = self.half_settings.get('h_align', '1')
        half_v_align = self.half_settings.get('v_align', '1')
        if self.current_half == "1st HALF":
            self.send_udp_command(f"*#1RAMT3,{half_color}{half_size}{half_h_align}{half_v_align}1st HALF0000")
        else:
            self.send_udp_command(f"*#1RAMT3,{half_color}{half_size}{half_h_align}{half_v_align}2nd HALF0000")
    
    def back_to_home(self):
        """Return to home screen"""
        self.save_config()
        
        # Stop any scrolling
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
    
    # Text settings
    def show_text_settings(self, text_type):
        """Show text settings as a full page with scrolling"""
        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create scrollable frame
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
        
        # Top bar with back button
        top_bar = tk.Frame(main_frame, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 10))
        
        tk.Button(top_bar, text="← Return", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 activebackground='#555555', activeforeground='white',
                 command=self.show_soccer_ui).pack(side='left', anchor='w')
        
        # Get current settings
        if text_type == "half":
            current = self.half_settings
            title_text = "HALF Text Settings"
        else:
            current = self.team_settings
            title_text = "Team Names Settings"
        
        tk.Label(main_frame, text=title_text, font=('Helvetica', 18, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=(0, 20))
        
        # Colour and Size side by side
        cs_frame = tk.Frame(main_frame, bg='#1a1a1a')
        cs_frame.pack(fill='x', pady=(10, 5))
        
        # Colour (left side)
        colour_section = tk.Frame(cs_frame, bg='#1a1a1a')
        colour_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(colour_section, text="Colour:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        color_var = tk.StringVar(value=current['color'])
        
        colors = [
            ("Red", "1"), ("Green", "2"), ("Yellow", "3"), ("Blue", "4"),
            ("Purple", "5"), ("Cyan", "6"), ("White", "7")
        ]
        
        def on_color_change():
            """Apply colour change instantly"""
            if text_type == "half":
                self.half_settings['color'] = color_var.get()
                if self.current_half == "1st HALF":
                    self.set_first_half()
                else:
                    self.set_second_half()
            else:
                self.team_settings['color'] = color_var.get()
                # Send the stored team names, not from entry widgets
                self.send_team_name_update('home')
                self.send_team_name_update('away')
            self.save_config()
        
        for name, val in colors:
            tk.Radiobutton(colour_section, text=name, variable=color_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', activebackground='#1a1a1a',
                          activeforeground='white', 
                          command=on_color_change).pack(anchor='w', padx=10, pady=3)
        
        # Size (right side)
        size_section = tk.Frame(cs_frame, bg='#1a1a1a')
        size_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(size_section, text="Size:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        size_var = tk.StringVar(value=current['size'])
        
        sizes = [("Very Small", "9"), ("Small", "1"), ("Medium", "2"), ("Large", "3"), ("Extra Large", "4")]
        
        def on_size_change():
            """Apply size change instantly"""
            if text_type == "half":
                self.half_settings['size'] = size_var.get()
                if self.current_half == "1st HALF":
                    self.set_first_half()
                else:
                    self.set_second_half()
            else:
                self.team_settings['size'] = size_var.get()
                # Send the stored team names, not from entry widgets
                self.send_team_name_update('home')
                self.send_team_name_update('away')
            self.save_config()
        
        for name, val in sizes:
            tk.Radiobutton(size_section, text=name, variable=size_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', activebackground='#1a1a1a',
                          activeforeground='white',
                          command=on_size_change).pack(anchor='w', padx=10, pady=3)
        
        # Horizontal and Vertical side by side
        align_frame = tk.Frame(main_frame, bg='#1a1a1a')
        align_frame.pack(fill='x', pady=(15, 5))
        
        # Horizontal (left side)
        h_section = tk.Frame(align_frame, bg='#1a1a1a')
        h_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(h_section, text="Horizontal:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        h_align_var = tk.StringVar(value=current.get('h_align', '1'))
        
        h_aligns = [("Center", "1"), ("Right", "2"), ("Left", "3")]
        
        def on_h_align_change():
            """Apply horizontal alignment change instantly"""
            if text_type == "half":
                self.half_settings['h_align'] = h_align_var.get()
                if self.current_half == "1st HALF":
                    self.set_first_half()
                else:
                    self.set_second_half()
            else:
                self.team_settings['h_align'] = h_align_var.get()
                # Send the stored team names, not from entry widgets
                self.send_team_name_update('home')
                self.send_team_name_update('away')
            self.save_config()
        
        for name, val in h_aligns:
            tk.Radiobutton(h_section, text=name, variable=h_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', activebackground='#1a1a1a',
                          activeforeground='white',
                          command=on_h_align_change).pack(anchor='w', padx=10, pady=3)
        
        # Vertical (right side)
        v_section = tk.Frame(align_frame, bg='#1a1a1a')
        v_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(v_section, text="Vertical:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        v_align_var = tk.StringVar(value=current.get('v_align', '1'))
        
        v_aligns = [("Center", "1"), ("Bottom", "2"), ("Top", "3")]
        
        def on_v_align_change():
            """Apply vertical alignment change instantly"""
            if text_type == "half":
                self.half_settings['v_align'] = v_align_var.get()
                if self.current_half == "1st HALF":
                    self.set_first_half()
                else:
                    self.set_second_half()
            else:
                self.team_settings['v_align'] = v_align_var.get()
                # Send the stored team names, not from entry widgets
                self.send_team_name_update('home')
                self.send_team_name_update('away')
            self.save_config()
        
        for name, val in v_aligns:
            tk.Radiobutton(v_section, text=name, variable=v_align_var, value=val,
                          font=('Helvetica', 11), bg='#1a1a1a', fg='white',
                          selectcolor='#333333', activebackground='#1a1a1a',
                          activeforeground='white',
                          command=on_v_align_change).pack(anchor='w', padx=10, pady=3)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def show_edit_home_text(self):
        """Show edit screen text as a full page instead of popup"""
        # Clear screen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create scrollable frame
        canvas = tk.Canvas(self.root, bg='#1a1a1a', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#1a1a1a')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        main = tk.Frame(scrollable_frame, bg='#1a1a1a')
        main.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Top bar with back button
        top_bar = tk.Frame(main, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 10))
        
        tk.Button(top_bar, text="← Controller", font=('Helvetica', 12, 'bold'),
                 bg='#333333', fg='white', relief='flat', padx=15, pady=8,
                 activebackground='#555555', activeforeground='white',
                 command=self.create_home_screen).pack(side='left', anchor='w')
        
        tk.Label(main, text="Edit Screen Text", font=('Helvetica', 18, 'bold'),
                bg='#1a1a1a', fg='white').pack(pady=(0, 20))
        
        # Text input
        tk.Label(main, text="Text to display:", font=('Helvetica', 12),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(10, 5))
        
        text_entry = tk.Entry(main, font=('Helvetica', 14), bg='#333333',
                             fg='white', relief='flat', insertbackground='white')
        text_entry.pack(fill='x', pady=5, ipady=8)
        text_entry.insert(0, "Welcome")
        
        # Colour and Size side by side
        cs_frame = tk.Frame(main, bg='#1a1a1a')
        cs_frame.pack(fill='x', pady=(15, 5))
        
        # Colour (left side)
        colour_section = tk.Frame(cs_frame, bg='#1a1a1a')
        colour_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(colour_section, text="Colour:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        color_var = tk.StringVar(value=self.home_screen_settings['color'])
        colors = [("Red", "1"), ("Green", "2"), ("Yellow", "3"), ("Blue", "4"),
                 ("Purple", "5"), ("Cyan", "6"), ("White", "7")]
        
        for name, val in colors:
            tk.Radiobutton(colour_section, text=name, variable=color_var, value=val,
                          font=('Helvetica', 10), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=2)
        
        # Size (right side)
        size_section = tk.Frame(cs_frame, bg='#1a1a1a')
        size_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(size_section, text="Size:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        size_var = tk.StringVar(value=self.home_screen_settings['size'])
        sizes = [("Very Small", "9"), ("Small", "1"), ("Medium", "2"), ("Large", "3"), ("Extra Large", "4")]
        
        for name, val in sizes:
            tk.Radiobutton(size_section, text=name, variable=size_var, value=val,
                          font=('Helvetica', 10), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=2)
        
        # Horizontal and Vertical side by side
        align_frame = tk.Frame(main, bg='#1a1a1a')
        align_frame.pack(fill='x', pady=(15, 5))
        
        # Horizontal (left side)
        h_section = tk.Frame(align_frame, bg='#1a1a1a')
        h_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(h_section, text="Horizontal:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        h_align_var = tk.StringVar(value="1")
        for name, val in [("Center", "1"), ("Right", "2"), ("Left", "3")]:
            tk.Radiobutton(h_section, text=name, variable=h_align_var, value=val,
                          font=('Helvetica', 10), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=2)
        
        # Vertical (right side)
        v_section = tk.Frame(align_frame, bg='#1a1a1a')
        v_section.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(v_section, text="Vertical:", font=('Helvetica', 12, 'bold'),
                bg='#1a1a1a', fg='white').pack(anchor='w', pady=(0, 5))
        
        v_align_var = tk.StringVar(value="1")
        for name, val in [("Center", "1"), ("Bottom", "2"), ("Top", "3")]:
            tk.Radiobutton(v_section, text=name, variable=v_align_var, value=val,
                          font=('Helvetica', 10), bg='#1a1a1a', fg='white',
                          selectcolor='#333333').pack(anchor='w', padx=10, pady=2)
        
        # Scrolling checkbox
        scroll_var = tk.BooleanVar(value=False)
        
        scroll_frame = tk.Frame(main, bg='#2a2a2a', relief='ridge', bd=1)
        scroll_frame.pack(fill='x', pady=(15, 5), ipady=10)
        
        tk.Checkbutton(scroll_frame, text="Enable Scrolling Text", variable=scroll_var,
                      font=('Helvetica', 11, 'bold'), bg='#2a2a2a', fg='white',
                      selectcolor='#333333', activebackground='#2a2a2a',
                      activeforeground='white').pack(padx=10, pady=(5, 5))
        
        # Scrolling tip
        tip_label = tk.Label(scroll_frame, 
                            text="💡 Tip: Add spaces before/after text to scroll across entire screen",
                            font=('Helvetica', 9, 'italic'), bg='#2a2a2a', fg='#ffaa00',
                            wraplength=350, justify='left')
        tip_label.pack(padx=10, pady=(0, 10))
        
        # Scroll speed options
        tk.Label(scroll_frame, text="Scroll Speed:", font=('Helvetica', 10, 'bold'),
                bg='#2a2a2a', fg='white').pack(anchor='w', padx=10, pady=(0, 5))
        
        speed_var = tk.IntVar(value=700)
        
        speed_options = [
            ("Very Slow", 1000),
            ("Slow", 800),
            ("Normal", 700),
            ("Fast", 500),
            ("Very Fast", 300)
        ]
        
        for name, val in speed_options:
            tk.Radiobutton(scroll_frame, text=name, variable=speed_var, value=val,
                          font=('Helvetica', 10), bg='#2a2a2a', fg='white',
                          selectcolor='#333333', activebackground='#2a2a2a',
                          activeforeground='white').pack(anchor='w', padx=20, pady=2)
        
        # Buttons
        def send_home_text():
            text = text_entry.get().strip()
            if not text:
                return
            
            # Save settings
            self.home_screen_settings['color'] = color_var.get()
            self.home_screen_settings['size'] = size_var.get()
            self.save_config()
            
            color = color_var.get()
            size = size_var.get()
            h_align = h_align_var.get()
            v_align = v_align_var.get()
            
            if scroll_var.get():
                # Start scrolling text with selected speed
                speed = speed_var.get()
                self.start_scrolling_text(text, color, size, speed)
            else:
                # Stop any existing scroll
                self.stop_scrolling_text()
                # Send static text with alignment
                self.send_udp_command(f"*#1RAMT1,{color}{size}{h_align}{v_align}{text}0000")
            
            # Stay on page - don't return to home
        
        def send_blank_screen():
            # Stop any scrolling
            self.stop_scrolling_text()
            # Send blank text
            self.send_udp_command("*#1RAMT1,1211 0000")
            # Stay on page - don't return to home
        
        button_frame = tk.Frame(main, bg='#1a1a1a')
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Send Text", font=('Helvetica', 13, 'bold'),
                 bg='#0066cc', fg='white', relief='flat', padx=25, pady=10,
                 command=send_home_text).pack(side='left', padx=5)
        
        tk.Button(button_frame, text="Blank Screen", font=('Helvetica', 13, 'bold'),
                 bg='#cc0000', fg='white', relief='flat', padx=20, pady=10,
                 command=send_blank_screen).pack(side='left', padx=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
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
        """Stop scrolling text animation"""
        self.scroll_active = False
        if self.scroll_timer:
            self.root.after_cancel(self.scroll_timer)
            self.scroll_timer = None
    
    # Config management
    def save_config(self):
        """Save configuration to file"""
        config = {
            "sport": self.current_sport,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "home_name": self.home_name,
            "away_name": self.away_name,
            "current_half": self.current_half,
            "half_settings": self.half_settings,
            "team_settings": self.team_settings,
            "home_screen_settings": self.home_screen_settings,
            "halftime_screen_settings": self.halftime_screen_settings,
            "advertisements": self.advertisements,
            "current_ad_index": self.current_ad_index,
            # AFL specific
            "afl_home_goals": getattr(self, 'afl_home_goals', 0),
            "afl_home_points": getattr(self, 'afl_home_points', 0),
            "afl_away_goals": getattr(self, 'afl_away_goals', 0),
            "afl_away_points": getattr(self, 'afl_away_points', 0),
            "afl_home_name": getattr(self, 'afl_home_name', 'HOME'),
            "afl_away_name": getattr(self, 'afl_away_name', 'AWAY'),
            "current_quarter": getattr(self, 'current_quarter', 'Q1'),
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
            "current_innings": getattr(self, 'current_innings', 'INN1'),
            # UI state
            "bypass_connection": self.bypass_connection.get()
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
                
                self.current_sport = config.get("sport")
                self.home_score = config.get("home_score", 0)
                self.away_score = config.get("away_score", 0)
                self.home_name = config.get("home_name", "HOME")
                self.away_name = config.get("away_name", "AWAY")
                self.current_half = config.get("current_half", "1st HALF")
                self.half_settings = config.get("half_settings", {"color": "1", "size": "1", "h_align": "1", "v_align": "1"})
                self.team_settings = config.get("team_settings", {"color": "1", "size": "3", "h_align": "1", "v_align": "1"})
                self.home_screen_settings = config.get("home_screen_settings", {"color": "7", "size": "2"})
                self.halftime_screen_settings = config.get("halftime_screen_settings", {"color": "7", "size": "2"})
                self.advertisements = config.get("advertisements", [])
                self.current_ad_index = config.get("current_ad_index", 0)
                
                # AFL specific
                self.afl_home_goals = config.get("afl_home_goals", 0)
                self.afl_home_points = config.get("afl_home_points", 0)
                self.afl_away_goals = config.get("afl_away_goals", 0)
                self.afl_away_points = config.get("afl_away_points", 0)
                self.afl_home_name = config.get("afl_home_name", "HOME")
                self.afl_away_name = config.get("afl_away_name", "AWAY")
                self.current_quarter = config.get("current_quarter", "Q1")
                
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
                self.current_innings = config.get("current_innings", "INN1")
                
                # UI state - bypass is saved but ALWAYS reset to False on boot
                # User requested: "reset to unchecked on program boot"
                saved_bypass = config.get("bypass_connection", False)
                # Don't apply saved state on boot - always start unchecked
                
                # Ensure alignment keys exist
                if 'h_align' not in self.half_settings:
                    self.half_settings['h_align'] = '1'
                if 'v_align' not in self.half_settings:
                    self.half_settings['v_align'] = '1'
                if 'h_align' not in self.team_settings:
                    self.team_settings['h_align'] = '1'
                if 'v_align' not in self.team_settings:
                    self.team_settings['v_align'] = '1'
                if 'h_align' not in self.halftime_screen_settings:
                    self.halftime_screen_settings['h_align'] = '1'
                if 'v_align' not in self.halftime_screen_settings:
                    self.halftime_screen_settings['v_align'] = '1'
                
                print(f"[INFO] Config loaded from {CONFIG_FILE}")
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")

def main():
    root = tk.Tk()
    app = ScoreboardApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()