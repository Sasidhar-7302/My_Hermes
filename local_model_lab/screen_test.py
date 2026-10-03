# -*- coding: utf-8 -*-
import ctypes
from ctypes import wintypes
import subprocess
import os

def test_screen_grab():
    # Use PowerShell script without escaping issues
    ps_script = """
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bmp.Save("local_model_lab/screen_capture.png", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
Write-Output "SUCCESS: $($bounds.Width)x$($bounds.Height)"
"""
    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
    print("STDOUT:", res.stdout.strip())
    print("STDERR:", res.stderr.strip())
    if os.path.exists("local_model_lab/screen_capture.png"):
        size = os.path.getsize("local_model_lab/screen_capture.png")
        print(f"File created successfully: {size} bytes")

if __name__ == "__main__":
    test_screen_grab()
