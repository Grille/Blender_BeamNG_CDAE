import time

class Stopwatch:

    def __init__(self):
        self.now = time.time()
        self.items: list[tuple[str, float]] = []


    def log(self, name: str):
        delta = time.time()-self.now
        self.now = time.time()
        self.items.append((name, delta))


    def print(self):
        for name, delta in self.items:
            print(f"{name}: {delta}")
