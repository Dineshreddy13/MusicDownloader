import threading
import time
class Spinner:
    def __init__(self):
        self.spinner_chars = ['|', '/', '-', '\\']
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._animate)
        self.thread.start()

    def stop(self):
        
        self.running = False
        if self.thread:
            self.thread.join()  

    def _animate(self):
        while self.running:
            for char in self.spinner_chars:
                print(f"\r{char}", end="", flush=True)
                time.sleep(0.1)
                if not self.running:
                    break
class QuietLogger:
    def debug(self, msg):
        pass  # Suppress debug messages
    def warning(self, msg):
        pass  # Suppress warning messages
    def error(self, msg):
        print(msg)