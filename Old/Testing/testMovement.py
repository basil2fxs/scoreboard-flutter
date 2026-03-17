import serial
import time

# Serial Setup
port = serial.Serial(
    port="COM14",
    baudrate=57600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=0
)

print("Opened", port.portstr)

# The text to scroll
text = "Hello World"
# Add padding for smooth scrolling
scroll_text = text + "   "

# Infinite scroll loop
while True:
    for i in range(len(scroll_text)):
        # Build the visible window (same length as text)
        window = (scroll_text + scroll_text)[i:i+len(text)]

        # EXACT PowerLED command
        cmd = f"*#1RAMT1,2211{window}0000"

        # Send out raw ASCII like your PowerShell example
        port.write(cmd.encode('ascii'))

        print("Sent:", cmd)

        # The protocol recommends >=100ms gap
        time.sleep(0.7)
