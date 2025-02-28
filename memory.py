import os
import pickle


class Memory:
    filename = "memory.pkl"

    def __init__(self):
        if os.path.exists(self.filename):
            with open(self.filename, "rb") as f:
                self.data: dict = pickle.load(f)
        else:
            self.data: dict = {}

    def has_crawled(self, url):
        return self.data.get(url, False) is True

    def started(self, url):
        self.data[url] = False

    def crawled(self, url):
        self.data[url] = True

    def get_last_url(self):
        if self.data:
            return list(self.data.keys())[-1]
        else:
            return

    def save(self):
        # Sauvegarder les données mises à jour avec pickle
        with open(self.filename, "wb") as f:
            pickle.dump(self.data, f)
