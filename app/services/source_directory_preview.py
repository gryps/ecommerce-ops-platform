from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from app.media import VIDEO_EXTENSIONS, resolve_source_directory


def _windows_path(path: str) -> str:
    result = subprocess.run(
        ["wslpath", "-w", path],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def _linux_path(path: str) -> str:
    result = subprocess.run(
        ["wslpath", "-u", path],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def select_native_source_files(initial_path: str = "") -> tuple[str, list[Path]]:
    powershell = shutil.which("powershell.exe")
    if not powershell:
        windows_powershell = Path(
            "/mnt/c/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe"
        )
        if windows_powershell.is_file():
            powershell = str(windows_powershell)
    if not powershell:
        raise RuntimeError("当前系统无法调用 Windows 目录选择窗口")
    initial_windows = ""
    if initial_path:
        try:
            initial_windows = _windows_path(
                str(resolve_source_directory(initial_path))
            )
        except (ValueError, OSError, subprocess.SubprocessError):
            initial_windows = ""
    escaped_initial = initial_windows.replace("'", "''")
    script = """
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class DialogForeground {
    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetClassName(IntPtr hWnd, StringBuilder className, int maxCount);

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern bool ShowWindow(IntPtr hWnd, int command);

    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern bool SetWindowPos(
        IntPtr hWnd, IntPtr insertAfter, int x, int y, int width, int height, uint flags
    );

    public static void ForceFileDialogToFront(int processId) {
        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {
            uint ownerProcessId;
            GetWindowThreadProcessId(hWnd, out ownerProcessId);
            if (ownerProcessId != (uint)processId || !IsWindowVisible(hWnd)) {
                return true;
            }
            StringBuilder className = new StringBuilder(64);
            GetClassName(hWnd, className, className.Capacity);
            if (className.ToString() != "#32770") {
                return true;
            }
            ShowWindow(hWnd, 9);
            SetWindowPos(
                hWnd, new IntPtr(-1), 0, 0, 0, 0,
                0x0001 | 0x0002 | 0x0040
            );
            SetForegroundWindow(hWnd);
            return true;
        }, IntPtr.Zero);
    }
}
'@
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = '选择一个或多个要打开的视频素材'
$dialog.Multiselect = $true
$dialog.CheckFileExists = $true
$dialog.RestoreDirectory = $true
$dialog.Filter = '媒体文件|*.mp4;*.mov;*.m4v;*.avi;*.mkv;*.webm;*.wmv;*.flv;*.3gp;*.3g2;*.mts;*.m2ts;*.ts|所有文件|*.*'
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
$owner.ShowInTaskbar = $false
$owner.StartPosition = 'Manual'
$owner.Location = New-Object System.Drawing.Point(-32000, -32000)
$owner.Size = New-Object System.Drawing.Size(1, 1)
$owner.Opacity = 0
$initial = '__INITIAL_PATH__'
if ($initial -and (Test-Path -LiteralPath $initial)) {
    $dialog.InitialDirectory = $initial
}
$owner.Show()
$owner.Activate()
$foregroundTimer = New-Object System.Windows.Forms.Timer
$foregroundTimer.Interval = 120
$foregroundTimer.Add_Tick({
    [DialogForeground]::ForceFileDialogToFront($PID)
})
$foregroundTimer.Start()
$result = $dialog.ShowDialog($owner)
$foregroundTimer.Stop()
$foregroundTimer.Dispose()
$owner.Close()
$owner.Dispose()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $dialog.FileNames | ForEach-Object { Write-Output $_ }
}
""".replace("__INITIAL_PATH__", escaped_initial)
    try:
        result = subprocess.run(
            [powershell, "-NoProfile", "-STA", "-Command", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=900,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("目录选择窗口等待超时") from exc
    except subprocess.CalledProcessError as exc:
        message = (exc.stderr or "").strip()
        raise RuntimeError(f"无法打开系统目录选择窗口：{message or 'PowerShell 执行失败'}") from exc
    selected = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not selected:
        return "", []
    try:
        videos = [resolve_source_video(_linux_path(value)) for value in selected]
        common_parent = Path(
            os.path.commonpath([str(video.parent) for video in videos])
        )
        folder = resolve_source_directory(str(common_parent))
        return str(folder), videos
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"所选视频不可用于素材导入：{exc}") from exc


def resolve_source_video(path: str) -> Path:
    try:
        video = Path(path).expanduser().resolve(strict=True)
    except OSError as exc:
        raise ValueError("预览视频不存在或不可访问") from exc
    if not video.is_file() or video.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError("文件不是支持的视频素材")
    resolve_source_directory(str(video.parent))
    return video
