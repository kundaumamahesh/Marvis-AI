import json
import os


class MemoryManager:

    def __init__(self):

        self.file = "memory/conversation.json"

        os.makedirs("memory", exist_ok=True)

        if not os.path.exists(self.file):

            with open(self.file, "w", encoding="utf-8") as f:
                json.dump([], f)

    def load(self):

        try:

            with open(
                self.file,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)

        except:

            return []

    def save(self, data):

        with open(
            self.file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=2,
                ensure_ascii=False
            )

    def add(self, role, content):

        history = self.load()

        history.append({
            "role": role,
            "content": content
        })

        history = history[-30:]

        self.save(history)

    def get(self):

        return self.load()