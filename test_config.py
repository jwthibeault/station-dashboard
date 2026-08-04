from station_dashboard.config import Config

cfg = Config()

print(f"Rotation: {cfg.rotation_seconds} seconds")

print()

for page in cfg.pages:
    print(page["name"])
    print(page["url"])
    print()
