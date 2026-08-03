from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Product Video Automation MVP"
    workbench_database_url: str = ""
    workspace_dir: Path = Path("storage/workspace")
    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"
    mount_roots: list[Path] = [
        Path("/mnt"),
        Path("/media"),
        Path("/run/media"),
        Path("storage"),
    ]
    auth_session_hours: int = 24
    media_probe_timeout_seconds: int = 60

    model_config = ConfigDict(env_file=".env", env_prefix="PVA_", extra="ignore")


settings = Settings()
