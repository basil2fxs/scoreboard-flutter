"""
TF-F6 LED Display Controller GUI
Control multiple counters with custom values

Protocol Format:
*#1CNTSx,Sy,0000
  x = counter number (1-9) - which counter to update
  y = the actual VALUE to display (0-9)
  0000 = always sent as 0000 (static)

Example: *#1CNTS2,S5,0000 displays "5" on Counter 2
"""

import serial
import time
import tkinter as tk
from tkinter import ttk, messagebox

class TFF6ControllerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TF-F6 LED Display Controller")
        self.root.geometry("800x600")
        
        # Serial connection
        self.ser = None
        self.port = "COM14"
        self.baudrate = 57600
        
        # Setup GUI
        self.create_widgets()
        
        # Auto-connect on startup
        self.connect()
    
    def create_widgets(self):
        # Connection Frame
        conn_frame = ttk.LabelFrame(self.root, text="Connection", padding=10)
        conn_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=0, sticky="w")
        self.port_entry = ttk.Entry(conn_frame, width=10)
        self.port_entry.insert(0, "COM14")
        self.port_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(conn_frame, text="Baud:").grid(row=0, column=2, sticky="w", padx=(20,0))
        self.baud_entry = ttk.Entry(conn_frame, width=10)
        self.baud_entry.insert(0, "57600")
        self.baud_entry.grid(row=0, column=3, padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect)
        self.connect_btn.grid(row=0, column=4, padx=10)
        
        self.status_label = ttk.Label(conn_frame, text="Not Connected", foreground="red")
        self.status_label.grid(row=0, column=5, padx=10)
        
        # Main Control Frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create counter controls (Counters 1-9)
        self.counter_controls = []
        
        # Header row
        ttk.Label(main_frame, text="Counter", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(main_frame, text="Value to Display", font=('Arial', 10, 'bold')).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(main_frame, text="", font=('Arial', 10, 'bold')).grid(row=0, column=2, padx=5, pady=5)
        
        for i in range(1, 10):
            row = i
            
            # Counter label
            ttk.Label(main_frame, text=f"Counter {i}:").grid(row=row, column=0, sticky="e", padx=5, pady=3)
            
            # Value selector (0-9) - this is what displays
            value_var = tk.StringVar(value="0")
            value_spinbox = ttk.Spinbox(main_frame, from_=0, to=9, width=10, textvariable=value_var)
            value_spinbox.grid(row=row, column=1, padx=5, pady=3)
            
            # Send button
            send_btn = ttk.Button(
                main_frame, 
                text="Send",
                command=lambda c=i, v=value_var: self.send_counter(c, v)
            )
            send_btn.grid(row=row, column=2, padx=5, pady=3)
            
            self.counter_controls.append({
                'counter': i,
                'value': value_var,
                'button': send_btn
            })
        
        # Quick Actions Frame
        quick_frame = ttk.LabelFrame(self.root, text="Quick Actions", padding=10)
        quick_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(quick_frame, text="Reset All to 0", command=self.reset_all).pack(side="left", padx=5)
        ttk.Button(quick_frame, text="Test Sequence", command=self.test_sequence).pack(side="left", padx=5)
        
        # Custom Command Frame
        custom_frame = ttk.LabelFrame(self.root, text="Custom Command", padding=10)
        custom_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(custom_frame, text="Raw Command:").pack(side="left", padx=5)
        self.custom_cmd = ttk.Entry(custom_frame, width=40)
        self.custom_cmd.insert(0, "*#1CNTS1,S0,0000")
        self.custom_cmd.pack(side="left", padx=5)
        ttk.Button(custom_frame, text="Send", command=self.send_custom).pack(side="left", padx=5)
        
        # Log Frame
        log_frame = ttk.LabelFrame(self.root, text="Activity Log", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=8, width=80, state='disabled')
        self.log_text.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)
    
    def log(self, message):
        """Add message to log"""
        self.log_text.config(state='normal')
        self.log_text.insert('end', f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see('end')
        self.log_text.config(state='disabled')
    
    def connect(self):
        """Connect to serial port"""
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            
            port = self.port_entry.get()
            baudrate = int(self.baud_entry.get())
            
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            
            self.status_label.config(text=f"Connected to {port} @ {baudrate}", foreground="green")
            self.log(f"✓ Connected to {port} @ {baudrate} baud")
            
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", foreground="red")
            self.log(f"✗ Connection error: {str(e)}")
            messagebox.showerror("Connection Error", str(e))
    
    def send_counter(self, counter_num, value_var):
        """Send counter command"""
        if not self.ser or not self.ser.is_open:
            messagebox.showerror("Error", "Not connected to serial port!")
            return
        
        try:
            value = int(value_var.get())
            
            # Format: *#1CNTSx,Sy,0000
            # x = counter number (1-9)
            # y = the VALUE to display (0-9)
            # 0000 = always sent as 0000
            
            command = f"*#1CNTS{counter_num},S{value},0000"
            
            self.ser.write(command.encode('ascii'))
            self.log(f"Sent: {command} → Counter {counter_num} displays '{value}'")
            
        except ValueError:
            messagebox.showerror("Error", "Value must be a number!")
        except Exception as e:
            self.log(f"✗ Error: {str(e)}")
            messagebox.showerror("Error", str(e))
    
    def send_custom(self):
        """Send custom command"""
        if not self.ser or not self.ser.is_open:
            messagebox.showerror("Error", "Not connected to serial port!")
            return
        
        try:
            command = self.custom_cmd.get()
            self.ser.write(command.encode('ascii'))
            self.log(f"Sent custom: {command}")
        except Exception as e:
            self.log(f"✗ Error: {str(e)}")
            messagebox.showerror("Error", str(e))
    
    def reset_all(self):
        """Reset all counters to 0"""
        if not self.ser or not self.ser.is_open:
            messagebox.showerror("Error", "Not connected to serial port!")
            return
        
        self.log("Resetting all counters to 0...")
        
        for i in range(1, 10):
            command = f"*#1CNTS{i},S0,0000"
            self.ser.write(command.encode('ascii'))
            time.sleep(0.1)
        
        self.log("✓ All counters reset to 0")
    
    def test_sequence(self):
        """Run a test sequence"""
        if not self.ser or not self.ser.is_open:
            messagebox.showerror("Error", "Not connected to serial port!")
            return
        
        self.log("Running test sequence (Counter 2: 0→5)...")
        
        # Test Counter 2 counting from 0 to 5 (like your working example)
        for value in range(0, 6):
            command = f"*#1CNTS2,S{value},0000"
            self.ser.write(command.encode('ascii'))
            self.log(f"Test: {command} → displays '{value}'")
            time.sleep(0.5)
        
        self.log("✓ Test sequence complete")
    
    def on_closing(self):
        """Handle window close"""
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TFF6ControllerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()