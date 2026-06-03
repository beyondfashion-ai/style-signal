from pathlib import Path
import shutil
import subprocess
from typing import Optional


class FetcherNotInstalled(RuntimeError):
    pass


def _candidate_bins() -> list[Path]:
    home = Path.home()
    return [
        home / "Library" / "Python" / "3.11" / "bin" / "scrapling",
        home / "Library" / "Python" / "3.12" / "bin" / "scrapling",
        home / "Library" / "Python" / "3.13" / "bin" / "scrapling",
        home / ".local" / "bin" / "scrapling",
    ]


def find_scrapling(scrapling_bin: Optional[str] = None) -> str:
    if scrapling_bin:
        return scrapling_bin

    path_bin = shutil.which("scrapling")
    if path_bin:
        return path_bin

    for candidate in _candidate_bins():
        if candidate.is_file():
            return str(candidate)

    raise FetcherNotInstalled("scrapling binary not found")


def stealthy_fetch(
    url: str,
    output_path: str,
    timeout_ms: int = 40000,
    wait_ms: int = 5000,
    real_chrome: bool = False,
    scrapling_bin: Optional[str] = None,
) -> tuple[bool, int, str]:
    """Return (success, file_size, raw_text_or_empty)."""
    binary = find_scrapling(scrapling_bin)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        binary,
        "extract",
        "stealthy-fetch",
        url,
        str(output),
        "--network-idle",
        "--timeout",
        str(timeout_ms),
        "--wait",
        str(wait_ms),
    ]
    if real_chrome:
        cmd.append("--real-chrome")

    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if not output.exists():
        return False, 0, ""

    raw_text = output.read_text(encoding="utf-8", errors="replace")
    file_size = output.stat().st_size
    return completed.returncode == 0, file_size, raw_text
