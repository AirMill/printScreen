import tkinter as tk
from tkinter import filedialog
import pyautogui
import os

class ScreenshotApp:
    def __init__(self, root):
        self.root = root
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        self.root.attributes('-alpha', 0.5)  # Transparency
        self.root.geometry("100x160+100+100")  # Adjusted for extra button
        
        self.save_folder = os.getcwd()  # Default save location

        self.exit_btn = tk.Button(root, text="Exit", bg='blue', fg='white', width=10, height=2, command=self.exit_app)
        self.exit_btn.pack(pady=2)
        
        self.capture_btn = tk.Button(root, text="Capture", bg='red', width=10, height=5, command=self.capture_screen)
        self.capture_btn.pack(pady=5)
        
        self.settings_btn = tk.Button(root, text="Settings", bg='yellow', width=8, height=2, command=self.select_folder)
        self.settings_btn.pack()
        
        self.root.bind('<B1-Motion>', self.drag_window)
    
    def drag_window(self, event):
        x = self.root.winfo_pointerx() - 50
        y = self.root.winfo_pointery() - 10
        self.root.geometry(f"100x160+{x}+{y}")
    
    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_folder = folder
    
    def capture_screen(self):
        self.root.withdraw()  # Hide window before capture
        
        # Find next available filename
        index = 1
        while os.path.exists(os.path.join(self.save_folder, f"screenshot_{index}.jpg")):
            index += 1
        
        filepath = os.path.join(self.save_folder, f"screenshot_{index}.jpg")
        screenshot = pyautogui.screenshot()
        screenshot = screenshot.convert("RGB")  # Convert to RGB for JPG format
        screenshot.save(filepath, "JPEG")
        
        self.root.deiconify()  # Show window again
        print(f"Screenshot saved to {filepath}")
    
    def exit_app(self):
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenshotApp(root)
    root.mainloop()
