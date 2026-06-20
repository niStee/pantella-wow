import tkinter as tk
import threading
import time

class TkinterOverlay:
    """Transparent overlay for AI companion text. Runs in daemon thread."""
    
    def __init__(self, title="Aether", width=400, height=120):
        self.title = title
        self.width = width
        self.height = height
        self.text = "Initializing..."
        self.root = None
        self.label = None
        self._thread = None
        self._running = False
        
    def start(self):
        """Launch overlay in a background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        time.sleep(0.5)  # Wait for window init
        
    def _run(self):
        """Tkinter main loop."""
        self.root = tk.Tk()
        self.root.overrideredirect(True)       # No borders
        self.root.attributes('-alpha', 0.85)   # 85% transparent
        self.root.attributes('-topmost', True) # Always on top
        self.root.attributes('-transparentcolor', 'black')
        
        # Position: bottom-right of screen
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = screen_w - self.width - 20
        y = screen_h - self.height - 100
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        
        # Background frame
        frame = tk.Frame(self.root, bg='black', bd=2, relief='ridge')
        frame.pack(fill='both', expand=True)
        
        # Title label
        title_label = tk.Label(frame, text=self.title, 
                              font=("Arial", 10, "bold"),
                              bg='black', fg='#FFD700')  # Gold
        title_label.pack(fill='x', padx=5, pady=2)
        
        # Text label
        self.label = tk.Label(frame, text=self.text,
                             font=("Arial", 11), 
                             bg='black', fg='white',
                             wraplength=self.width - 20,
                             justify='left')
        self.label.pack(fill='both', expand=True, padx=10, pady=5)
        
        self._running = True
        self.root.mainloop()
        
    def update_text(self, text, color='white'):
        """Update overlay text. Thread-safe."""
        self.text = text
        if self.root and self.label:
            try:
                self.root.after(0, lambda: self.label.config(text=text, fg=color))
            except Exception:
                pass
                
    def update_title(self, title):
        """Update companion name in title."""
        self.title = title
        # Would need to store title_label reference for this
        
    def stop(self):
        """Shutdown overlay."""
        self._running = False
        if self.root:
            self.root.after(0, self.root.destroy)
