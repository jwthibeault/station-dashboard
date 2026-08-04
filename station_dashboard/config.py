import json
from pathlib import Path


class Config:
    def __init__(self):
        base_dir = Path(__file__).resolve().parent.parent

        with open(base_dir / "config.json", "r") as f:
            self.config = json.load(f)

        with open(base_dir / "credentials.json", "r") as f:
            self.credentials = json.load(f)

    @property
    def pages(self):
        return self.config["pages"]

    @property
    def rotation_seconds(self):
        return self.config["dashboard"]["rotation_seconds"]
