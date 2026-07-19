import os

RESOURCES_DIR = os.getenv("RESOURCES_DIR")
YOMU_DEV = os.getenv("YOMU_DEV", "0") == "1"
APP_NAME = "Yomu-Dev" if YOMU_DEV else "Yomu"
