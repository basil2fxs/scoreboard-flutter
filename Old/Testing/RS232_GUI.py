"""
- COM14 @ 57600 baud
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import threading
import time

class TFF6GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TF-F6 LED Display Controller")
        self.root.geometry("1100x750")
        
        # Serial connection
        self.ser = None
        self.port = 'COM14'
        self.baudrate = 57600
        self.connected = False
        
        # Create GUI
        self.create_widgets()
        
        # Auto-connect
        self.connect()
    
    def create_widgets(self):
        """Create all GUI widgets"""
        
        # Connection frame
        conn_frame = ttk.LabelFrame(self.root, text="Connection", padding=10)
        conn_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=0, padx=5)
        self.port_entry = ttk.Entry(conn_frame, width=10)
        self.port_entry.insert(0, self.port)
        self.port_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(conn_frame, text="Baud:").grid(row=0, column=2, padx=5)
        self.baud_entry = ttk.Entry(conn_frame, width=10)
        self.baud_entry.insert(0, str(self.baudrate))
        self.baud_entry.grid(row=0, column=3, padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect)
        self.connect_btn.grid(row=0, column=4, padx=5)
        
        self.disconnect_btn = ttk.Button(conn_frame, text="Disconnect", command=self.disconnect, state='disabled')
        self.disconnect_btn.grid(row=0, column=5, padx=5)
        
        self.status_label = ttk.Label(conn_frame, text="Disconnected", foreground='red')
        self.status_label.grid(row=0, column=6, padx=10)
        
        # Tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Text areas tab
        text_tab = ttk.Frame(notebook)
        notebook.add(text_tab, text="📝 Text Areas")
        self.create_text_tab(text_tab)
        
        # Counters tab
        counter_tab = ttk.Frame(notebook)
        notebook.add(counter_tab, text="🔢 Counters")
        self.create_counter_tab(counter_tab)
    
    def create_text_tab(self, parent):
        """Create text areas tab"""
        
        left = ttk.Frame(parent)
        left.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        
        # Area selector
        area_frame = ttk.LabelFrame(left, text="Select Text Area", padding=10)
        area_frame.pack(fill='x', pady=5)
        
        ttk.Label(area_frame, text="Text Area:").pack(anchor='w', pady=2)
        
        row1 = ttk.Frame(area_frame)
        row1.pack(fill='x', pady=2)
        row2 = ttk.Frame(area_frame)
        row2.pack(fill='x', pady=2)
        
        self.text_area_var = tk.StringVar(value="1")
        for i in range(1, 11):
            frame = row1 if i <= 5 else row2
            ttk.Radiobutton(frame, text=f"RAMT{i}", variable=self.text_area_var, value=str(i),
                          command=self.update_text_preview).pack(side='left', padx=5)
        
        # Text content
        content_frame = ttk.LabelFrame(left, text="Text Content", padding=10)
        content_frame.pack(fill='x', pady=5)
        
        self.text_content = ttk.Entry(content_frame, font=('Arial', 16))
        self.text_content.pack(fill='x', pady=5)
        self.text_content.insert(0, "Test")
        self.text_content.bind('<KeyRelease>', lambda e: self.update_text_preview())
        
        # Color
        color_frame = ttk.LabelFrame(left, text="Color", padding=10)
        color_frame.pack(fill='x', pady=5)
        
        self.color_var = tk.StringVar(value="1")
        colors = [("Red","1"), ("Green","2"), ("Yellow","3"), ("Blue","4"),
                 ("Purple","5"), ("Cyan","6"), ("White","7"), ("Off","8")]
        
        color_grid = ttk.Frame(color_frame)
        color_grid.pack()
        for idx, (name, val) in enumerate(colors):
            ttk.Radiobutton(color_grid, text=name, variable=self.color_var, value=val,
                          command=self.update_text_preview).grid(row=idx//4, column=idx%4, sticky='w', padx=10, pady=2)
        
        # Size
        size_frame = ttk.LabelFrame(left, text="Text Size", padding=10)
        size_frame.pack(fill='x', pady=5)
        
        self.size_var = tk.StringVar(value="2")
        for name, val in [("Very Small","9"), ("Small","1"), ("Medium","2"), ("Large","3"), ("Largest","4")]:
            ttk.Radiobutton(size_frame, text=name, variable=self.size_var, value=val,
                          command=self.update_text_preview).pack(anchor='w', padx=20)
        
        # Alignment
        align_frame = ttk.LabelFrame(left, text="Alignment", padding=10)
        align_frame.pack(fill='x', pady=5)
        
        ttk.Label(align_frame, text="Horizontal:", font=('Arial',10,'bold')).pack(anchor='w')
        self.h_align_var = tk.StringVar(value="1")
        for name, val in [("Center","1"), ("Right","2"), ("Left","3")]:
            ttk.Radiobutton(align_frame, text=name, variable=self.h_align_var, value=val,
                          command=self.update_text_preview).pack(anchor='w', padx=20)
        
        ttk.Label(align_frame, text="Vertical:", font=('Arial',10,'bold')).pack(anchor='w', pady=(5,0))
        self.v_align_var = tk.StringVar(value="1")
        for name, val in [("Center","1"), ("Bottom","2"), ("Top","3")]:
            ttk.Radiobutton(align_frame, text=name, variable=self.v_align_var, value=val,
                          command=self.update_text_preview).pack(anchor='w', padx=20)
        
        # Right side
        right = ttk.Frame(parent)
        right.pack(side='right', fill='both', expand=True, padx=10, pady=10)
        
        # Preview
        prev_frame = ttk.LabelFrame(right, text="Command Preview", padding=10)
        prev_frame.pack(fill='both', expand=True, pady=5)
        
        self.text_preview = scrolledtext.ScrolledText(prev_frame, height=12, wrap='word', font=('Courier',10))
        self.text_preview.pack(fill='both', expand=True)
        
        # Visual preview
        vis_frame = ttk.LabelFrame(right, text="Visual Preview", padding=10)
        vis_frame.pack(fill='x', pady=5)
        
        self.visual_label = tk.Label(vis_frame, text="Test", font=('Arial',20,'bold'),
                                     bg='black', fg='red', height=4, relief='sunken', bd=2)
        self.visual_label.pack(fill='both', pady=10)
        
        # Buttons
        btn_frame = ttk.Frame(right)
        btn_frame.pack(fill='x', pady=10)
        
        ttk.Button(btn_frame, text="📤 Send This Area", command=self.send_text).pack(fill='x', pady=2)
        ttk.Button(btn_frame, text="📤 Send All 10 Areas", command=self.send_all_text).pack(fill='x', pady=2)
        ttk.Button(btn_frame, text="🗑️ Clear This Area", command=self.clear_text).pack(fill='x', pady=2)
        
        self.update_text_preview()
    
    def create_counter_tab(self, parent):
        """Create counters tab"""
        
        left = ttk.Frame(parent)
        left.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        
        # Counter selector
        cnt_frame = ttk.LabelFrame(left, text="Select Counter", padding=10)
        cnt_frame.pack(fill='x', pady=5)
        
        ttk.Label(cnt_frame, text="Counter:").pack(anchor='w', pady=2)
        
        row1 = ttk.Frame(cnt_frame)
        row1.pack(fill='x', pady=2)
        row2 = ttk.Frame(cnt_frame)
        row2.pack(fill='x', pady=2)
        
        self.counter_var = tk.StringVar(value="1")
        for i in range(1, 11):
            frame = row1 if i <= 5 else row2
            ttk.Radiobutton(frame, text=f"CNTS{i}", variable=self.counter_var, value=str(i),
                          command=self.update_counter_preview).pack(side='left', padx=5)
        
        # Value selector (0-9)
        val_frame = ttk.LabelFrame(left, text="Value to Display (0-9)", padding=10)
        val_frame.pack(fill='x', pady=5)
        
        ttk.Label(val_frame, text="Select digit:").pack(anchor='w', pady=2)
        
        val_row = ttk.Frame(val_frame)
        val_row.pack(fill='x', pady=5)
        
        self.value_var = tk.StringVar(value="0")
        for i in range(10):
            ttk.Radiobutton(val_row, text=str(i), variable=self.value_var, value=str(i),
                          command=self.update_counter_preview, width=3).pack(side='left', padx=3)
        
        # Large display
        disp_frame = ttk.Frame(val_frame)
        disp_frame.pack(fill='x', pady=10)
        
        ttk.Label(disp_frame, text="Current:").pack(side='left', padx=5)
        self.value_label = ttk.Label(disp_frame, text="0", font=('Arial',48,'bold'), foreground='red')
        self.value_label.pack(side='left', padx=10)
        
        # +/- buttons
        adj_frame = ttk.LabelFrame(left, text="Adjust Value", padding=10)
        adj_frame.pack(fill='x', pady=5)
        
        btn_row = ttk.Frame(adj_frame)
        btn_row.pack()
        
        ttk.Button(btn_row, text="−", width=8, command=lambda: self.adjust_value(-1)).pack(side='left', padx=5)
        ttk.Button(btn_row, text="+", width=8, command=lambda: self.adjust_value(1)).pack(side='left', padx=5)
        
        # Right side
        right = ttk.Frame(parent)
        right.pack(side='right', fill='both', expand=True, padx=10, pady=10)
        
        # Preview
        prev_frame = ttk.LabelFrame(right, text="Command Preview", padding=10)
        prev_frame.pack(fill='both', expand=True, pady=5)
        
        self.counter_preview = scrolledtext.ScrolledText(prev_frame, height=10, wrap='word', font=('Courier',10))
        self.counter_preview.pack(fill='both', expand=True)
        
        # Explanation
        exp_frame = ttk.LabelFrame(right, text="Format", padding=10)
        exp_frame.pack(fill='x', pady=5)
        
        exp_text = """Command: *#1CNTSx,Sy,0000

x = Counter (1-10)
y = Value to display (0-9)
0000 = Always 0000

Example: *#1CNTS2,S3,0000
  Counter 2 displays "3"
"""
        ttk.Label(exp_frame, text=exp_text, font=('Courier',9), justify='left').pack()
        
        # Buttons
        btn_frame = ttk.Frame(right)
        btn_frame.pack(fill='x', pady=10)
        
        ttk.Button(btn_frame, text="📤 Send to Display", command=self.send_counter).pack(fill='x', pady=2)
        ttk.Button(btn_frame, text="🔢 Count 0-9", command=self.count_sequence).pack(fill='x', pady=2)
        ttk.Button(btn_frame, text="🗑️ Reset to 0", command=self.reset_counter).pack(fill='x', pady=2)
        ttk.Button(btn_frame, text="🗑️ Reset All Counters", command=self.reset_all).pack(fill='x', pady=2)
        
        self.update_counter_preview()
    
    # Text functions
    def update_text_preview(self):
        """Update text preview"""
        area = self.text_area_var.get()
        color = self.color_var.get()
        size = self.size_var.get()
        h = self.h_align_var.get()
        v = self.v_align_var.get()
        text = self.text_content.get()
        
        cmd = f"*#1RAMT{area},{color}{size}{h}{v}{text}0000"
        
        self.text_preview.delete('1.0', tk.END)
        self.text_preview.insert('1.0', f"Command:\n{cmd}\n\n")
        self.text_preview.insert(tk.END, f"*#1RAMT{area} = Text Area {area}\n")
        self.text_preview.insert(tk.END, f"{color} = Color\n")
        self.text_preview.insert(tk.END, f"{size} = Size\n")
        self.text_preview.insert(tk.END, f"{h} = Horizontal align\n")
        self.text_preview.insert(tk.END, f"{v} = Vertical align\n")
        self.text_preview.insert(tk.END, f"{text} = Text\n")
        self.text_preview.insert(tk.END, f"0000 = Padding\n")
        
        # Visual
        colors = {"1":"red","2":"green","3":"yellow","4":"blue","5":"purple","6":"cyan","7":"white","8":"black"}
        sizes = {"1":12,"2":16,"3":20,"4":24,"9":10}
        self.visual_label.config(text=text, fg=colors.get(color,"red"), font=('Arial',sizes.get(size,16),'bold'))
    
    def send_text(self):
        """Send text area"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first!")
            return
        
        area = self.text_area_var.get()
        color = self.color_var.get()
        size = self.size_var.get()
        h = self.h_align_var.get()
        v = self.v_align_var.get()
        text = self.text_content.get()
        
        cmd = f"*#1RAMT{area},{color}{size}{h}{v}{text}0000"
        self.ser.write(cmd.encode('ascii'))
        print(f"Sent: {cmd}")
        messagebox.showinfo("Success", f"Text sent to RAMT{area}!")
    
    def send_all_text(self):
        """Send to all 10 areas"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first!")
            return
        
        color = self.color_var.get()
        size = self.size_var.get()
        h = self.h_align_var.get()
        v = self.v_align_var.get()
        text = self.text_content.get()
        
        for area in range(1, 11):
            cmd = f"*#1RAMT{area},{color}{size}{h}{v}{text}0000"
            self.ser.write(cmd.encode('ascii'))
            print(f"Sent: {cmd}")
            time.sleep(0.1)
        
        messagebox.showinfo("Success", "Text sent to all 10 areas!")
    
    def clear_text(self):
        """Clear text area"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first!")
            return
        
        area = self.text_area_var.get()
        cmd = f"*#1RAMT{area},1211 0000"
        self.ser.write(cmd.encode('ascii'))
        print(f"Sent: {cmd}")
        messagebox.showinfo("Success", f"RAMT{area} cleared!")
    
    # Counter functions
    def update_counter_preview(self):
        """Update counter preview"""
        counter = self.counter_var.get()
        value = self.value_var.get()
        
        cmd = f"*#1CNTS{counter},S{value},0000"
        
        self.counter_preview.delete('1.0', tk.END)
        self.counter_preview.insert('1.0', f"Command:\n{cmd}\n\n")
        self.counter_preview.insert(tk.END, f"*#1CNTS{counter} = Counter {counter}\n")
        self.counter_preview.insert(tk.END, f"S{value} = Display digit {value}\n")
        self.counter_preview.insert(tk.END, f"0000 = Always 0000\n\n")
        self.counter_preview.insert(tk.END, f"Counter {counter} will display: {value}\n")
        
        self.value_label.config(text=value)
    
    def adjust_value(self, delta):
        """Adjust counter value"""
        current = int(self.value_var.get())
        new = (current + delta) % 10
        self.value_var.set(str(new))
        self.update_counter_preview()
    
    def send_counter(self):
        """Send counter value"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first!")
            return
        
        counter = self.counter_var.get()
        value = self.value_var.get()
        
        cmd = f"*#1CNTS{counter},S{value},0000"
        self.ser.write(cmd.encode('ascii'))
        print(f"Sent: {cmd}")
        messagebox.showinfo("Success", f"Counter {counter} = {value}!")
    
    def count_sequence(self):
        """Count 0-9"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first!")
            return
        
        counter = self.counter_var.get()
        
        def run():
            for i in range(10):
                cmd = f"*#1CNTS{counter},S{i},0000"
                self.ser.write(cmd.encode('ascii'))
                print(f"Sent: {cmd}")
                self.value_var.set(str(i))
                self.update_counter_preview()
                time.sleep(0.5)
            messagebox.showinfo("Complete", f"Counted 0-9 on Counter {counter}!")
        
        threading.Thread(target=run, daemon=True).start()
    
    def reset_counter(self):
        """Reset counter to 0"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first!")
            return
        
        counter = self.counter_var.get()
        cmd = f"*#1CNTS{counter},S0,0000"
        self.ser.write(cmd.encode('ascii'))
        print(f"Sent: {cmd}")
        self.value_var.set("0")
        self.update_counter_preview()
        messagebox.showinfo("Success", f"Counter {counter} reset!")
    
    def reset_all(self):
        """Reset all counters"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first!")
            return
        
        for counter in range(1, 11):
            cmd = f"*#1CNTS{counter},S0,0000"
            self.ser.write(cmd.encode('ascii'))
            print(f"Sent: {cmd}")
            time.sleep(0.05)
        
        self.value_var.set("0")
        self.update_counter_preview()
        messagebox.showinfo("Success", "All counters reset!")
    
    # Connection functions
    def connect(self):
        """Connect to serial"""
        try:
            self.port = self.port_entry.get()
            self.baudrate = int(self.baud_entry.get())
            
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            
            self.connected = True
            self.status_label.config(text=f"Connected {self.port}@{self.baudrate}", foreground='green')
            self.connect_btn.config(state='disabled')
            self.disconnect_btn.config(state='normal')
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed:\n{e}")
            self.status_label.config(text="Connection Failed", foreground='red')
    
    def disconnect(self):
        """Disconnect"""
        if self.ser and self.ser.is_open:
            self.ser.close()
        
        self.connected = False
        self.status_label.config(text="Disconnected", foreground='red')
        self.connect_btn.config(state='normal')
        self.disconnect_btn.config(state='disabled')
    
    def on_close(self):
        """Handle close"""
        self.disconnect()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = TFF6GUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()