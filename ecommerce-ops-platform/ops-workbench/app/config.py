from pathlib import Path

from pydantic import ConfigDict
from pydantic import model_validator
from pydantic_settings import BaseSettings


APP_DIR = Path(__file__).resolve().parents[1]
PLATFORM_DIR = APP_DIR.parent
DEFAULT_RUNTIME_DIR = PLATFORM_DIR / "ops-workbench-runtime"


def _resolve_local_path(value: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve(strict=False)
    return (APP_DIR / path).resolve(strict=False)


class Settings(BaseSettings):
    app_name: str = "Product Video Automation MVP"
    workbench_database_url: str = ""
    runtime_dir: Path = DEFAULT_RUNTIME_DIR
    workspace_dir: Path | None = None
    static_dir: Path | None = None
    operations_runtime_dir: Path | None = None
    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"
    mount_roots: list[Path] | None = None
    auth_session_hours: int = 24
    media_probe_timeout_seconds: int = 60
    comfyui_base_url: str = "http://127.0.0.1:8188"

    @model_validator(mode="after")
    def normalize_runtime_paths(self) -> "Settings":
        self.runtime_dir = _resolve_local_path(self.runtime_dir)
        if self.workspace_dir is None:
            self.workspace_dir = self.runtime_dir / "workspace"
        else:
            self.workspace_dir = _resolve_local_path(self.workspace_dir)
        if self.static_dir is None:
            self.static_dir = self.runtime_dir / "static-workbench"
        else:
            self.static_dir = _resolve_local_path(self.static_dir)
        if self.operations_runtime_dir is None:
            self.operations_runtime_dir = self.runtime_dir / "operations"
        else:
            self.operations_runtime_dir = _resolve_local_path(self.operations_runtime_dir)
        if self.mount_roots is None:
            self.mount_roots = [
                Path("/mnt"),
                Path("/media"),
                Path("/run/media"),
                self.runtime_dir,
                self.operations_runtime_dir,
            ]
        else:
            self.mount_roots = [_resolve_local_path(path) for path in self.mount_roots]
        return self

    model_config = ConfigDict(
        env_file=DEFAULT_RUNTIME_DIR / ".env",
        env_prefix="PVA_",
        extra="ignore",
    )


settings = Settings()

