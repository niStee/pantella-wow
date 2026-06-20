import tkinter as tk
import threading
import queue
import time

class TkinterOverlay:
    """Thread-safe transparent overlay for AI companion text."""
    
    def __init__(self, title="Companion", width=400, height=120):
        self.title = title
        self.width = width
        self.height = height
        self.msg_queue = queue.Queue()
        self._thread = None
        self._running = False
        
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        time.sleep(0.5)
        
    def _run(self):
        """Tkinter main loop - runs in its own thread."""
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-alpha', 0.85)
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', 'black')
        
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = screen_w - self.width - 20
        y = screen_h - self.height - 100
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        
        frame = tk.Frame(self.root, bg='black', bd=2, relief='ridge')
        frame.pack(fill='both', expand=True)
        
        self.title_label = tk.Label(frame, text=self.title,
                                    font=("Arial", 10, "bold"),
                                    bg='black', fg='#FFD700')
        self.title_label.pack(fill='x', padx=5, pady=2)
        
        self.text_label = tk.Label(frame, text="Initializing...",
                                   font=("Arial", 11), 
                                   bg='black', fg='white',
                                   wraplength=self.width - 20,
                                   justify='left')
        self.text_label.pack(fill='both', expand=True, padx=10, pady=5)
        
        self._running = True
        self._check_queue()  # Start polling loop
        self.root.mainloop()
        
    def _check_queue(self):
        """Poll message queue every 100ms - thread-safe."""
        try:
            while True:
                item = self.msg_queue.get_nowait()
                if item[0].startswith('_title_'):
                    self.title_label.config(text=item[0][7:])
                else:
                    msg, color = item
                    self.text_label.config(text=msg, fg=color)
                    # Auto-resize height if text is long
                    lines = msg.count('\n') + 1
                    new_height = max(120, min(300, lines * 20 + 40))
                    if new_height != self.height:
                        self.height = new_height
                        self.root.geometry(f"{self.width}x{self.height}")
        except queue.Empty:
            pass
        if self._running:
            self.root.after(100, self._check_queue)
            
    def update_text(self, text, color='white'):
        """Thread-safe: just puts item into queue."""
        self.msg_queue.put((text, color))
        
    def update_title(self, title):
        self.title = title
        if hasattr(self, 'title_label'):
            self.msg_queue.put(('_title_' + title, ''))
        
    def stop(self):
        self._running = False
        if hasattr(self, 'root'):
            self.root.after(0, self.root.destroy)
