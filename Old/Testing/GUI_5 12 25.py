#!/usr/bin/env python3
"""
Professional Sports Scoreboard Controller GUI
Optimized for mobile-friendly interface
Controls LED displays via UDP (TF-F6 controller)
"""

import tkinter as tk
from tkinter import ttk, messagebox
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
    
    def auto_reconnect(self):
        """Try to reconnect every second if not connected"""
        if not self.connected:
            self.test_connection()
        
        # Schedule next reconnection attempt
        self.reconnect_timer = self.root.after(1000, self.auto_reconnect)
    
    def test_connection(self):
        """Test connection to controller"""
        try:
            # Try to send a test packet (bypass queue for connection test)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            test_cmd = "*#1PRGC30,0000"
            sock.sendto(test_cmd.encode("ascii"), (CONTROLLER_IP, CONTROLLER_PORT))
            sock.close()
            
            self.connected = True
            self.status_label.config(text=f"● Connected to {CONTROLLER_IP}", fg='#00ff00')
            self.connect_btn.config(state='disabled')
            self.enable_sport_buttons()
            print(f"[INFO] Connected to {CONTROLLER_IP}:{CONTROLLER_PORT}")
            
        except Exception as e:
            self.connected = False
            self.status_label.config(text=f"● Not Connected", fg='#ff3333')
            self.connect_btn.config(state='normal')
            print(f"[ERROR] Connection failed: {e}")
    
    def create_home_screen(self):
        """Create main home screen"""
        # Clear any existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Main container
        main_frame = tk.Frame(self.root, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title = tk.Label(main_frame, text="Sports Scoreboard", 
                        font=('Helvetica', 28, 'bold'),
                        bg='#1a1a1a', fg='white')
        title.pack(pady=(0, 10))
        
        # Status indicator
        self.status_label = tk.Label(main_frame, text="● Connecting...", 
                                     font=('Helvetica', 12),
                                     bg='#1a1a1a', fg='#ffaa00')
        self.status_label.pack(pady=(0, 5))
        
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
        
        # Connect button
        self.connect_btn = tk.Button(main_frame, text="Connect",
                                     font=('Helvetica', 18, 'bold'),
                                     bg='#00aa00', fg='white',
                                     activebackground='#00dd00',
                                     activeforeground='white',
                                     relief='flat', bd=0,
                                     padx=40, pady=15,
                                     command=self.test_connection)
        self.connect_btn.pack(pady=10, fill='x')
        
        # Select Sport button
        self.select_sport_btn = tk.Button(main_frame, text="Select Sport",
                                         font=('Helvetica', 18, 'bold'),
                                         bg='#555555', fg='white',
                                         activebackground='#0066cc',
                                         activeforeground='white',
                                         relief='flat', bd=0,
                                         padx=40, pady=15,
                                         state='disabled',
                                         command=self.show_sport_selection)
        self.select_sport_btn.pack(pady=10, fill='x')
        
        # Manage Scores button
        self.manage_scores_btn = tk.Button(main_frame, text="Manage Scores",
                                          font=('Helvetica', 18, 'bold'),
                                          bg='#555555', fg='white',
                                          activebackground='#0066cc',
                                          activeforeground='white',
                                          relief='flat', bd=0,
                                          padx=40, pady=15,
                                          state='disabled',
                                          command=self.show_manage_scores)
        self.manage_scores_btn.pack(pady=10, fill='x')
        
        # Spacer
        tk.Frame(main_frame, bg='#1a1a1a', height=50).pack(fill='x')
        
        # Edit Home Screen Text button (bottom right)
        edit_btn = tk.Button(main_frame, text="Edit Screen\nText",
                            font=('Helvetica', 10),
                            bg='#333333', fg='white',
                            activebackground='#555555',
                            activeforeground='white',
                            relief='flat', bd=0,
                            padx=10, pady=8,
                            command=self.show_edit_home_text)
        edit_btn.pack(side='right', anchor='se')
    
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
        
        tk.Button(top_bar, text="← Menu", font=('Helvetica', 12, 'bold'),
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
        
        # Back to menu button (top left)
        tk.Button(top_bar, text="← Menu", font=('Helvetica', 12, 'bold'),
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
    
    def show_coming_soon(self):
        """Show coming soon screen for sports not yet implemented"""
        for widget in self.root.winfo_children():
            widget.destroy()
        
        main_frame = tk.Frame(self.root, bg='#1a1a1a')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Top bar with back button
        top_bar = tk.Frame(main_frame, bg='#1a1a1a')
        top_bar.pack(fill='x', pady=(0, 30))
        
        tk.Button(top_bar, text="← Menu", font=('Helvetica', 12, 'bold'),
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
        """Update team name"""
        if team == 'home':
            new_name = self.home_name_entry.get().strip()
            if new_name:
                self.home_name = new_name
                color = self.team_settings['color']
                size = self.team_settings['size']
                h_align = self.team_settings.get('h_align', '1')
                v_align = self.team_settings.get('v_align', '1')
                self.send_udp_command(f"*#1RAMT1,{color}{size}{h_align}{v_align}{self.home_name}0000")
                self.save_config()
                print(f"[INFO] Home team updated to: {self.home_name}")
        else:
            new_name = self.away_name_entry.get().strip()
            if new_name:
                self.away_name = new_name
                color = self.team_settings['color']
                size = self.team_settings['size']
                h_align = self.team_settings.get('h_align', '1')
                v_align = self.team_settings.get('v_align', '1')
                self.send_udp_command(f"*#1RAMT2,{color}{size}{h_align}{v_align}{self.away_name}0000")
                self.save_config()
                print(f"[INFO] Away team updated to: {self.away_name}")
    
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
                                     "Reset all scores to 0?",
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
        
        text_var = tk.StringVar(value=self.halftime_screen_settings.get('text', f"Half Time - {self.home_name} {self.home_score} - {self.away_score} {self.away_name}"))
        
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
                      activeforeground='white').pack(anchor='w', pady=(5, 10), padx=10)
        
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
                      activeforeground='white').pack(anchor='w', pady=(5, 10), padx=10)
        
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
        
        # Send command to return to page 0 (home screen)
        self.send_udp_command("*#1PRGC30,0000")
        
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
                self.update_team_name('home')
                self.update_team_name('away')
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
                self.update_team_name('home')
                self.update_team_name('away')
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
                self.update_team_name('home')
                self.update_team_name('away')
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
                self.update_team_name('home')
                self.update_team_name('away')
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
        
        tk.Button(top_bar, text="← Menu", font=('Helvetica', 12, 'bold'),
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
        
        # Scrolling checkbox
        scroll_var = tk.BooleanVar(value=False)
        
        scroll_frame = tk.Frame(main, bg='#2a2a2a', relief='ridge', bd=1)
        scroll_frame.pack(fill='x', pady=(15, 5), ipady=10)
        
        tk.Checkbutton(scroll_frame, text="Enable Scrolling Text", variable=scroll_var,
                      font=('Helvetica', 11, 'bold'), bg='#2a2a2a', fg='white',
                      selectcolor='#333333', activebackground='#2a2a2a',
                      activeforeground='white').pack(padx=10, pady=(5, 10))
        
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
            
            if scroll_var.get():
                # Start scrolling text with selected speed
                speed = speed_var.get()
                self.start_scrolling_text(text, color, size, speed)
            else:
                # Stop any existing scroll
                self.stop_scrolling_text()
                # Send static text
                self.send_udp_command(f"*#1RAMT1,{color}{size}11{text}0000")
            
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
            "current_ad_index": self.current_ad_index
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