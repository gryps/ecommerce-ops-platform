from __future__ import annotations

import html
import re
from urllib.parse import urlparse

DOUYIN_HOSTS = {"douyin.com", "iesdouyin.com"}
DOUYIN_MEDIA_HOST_SUFFIXES = (".douyinvod.com", ".idouyinvod.com")
DOUYIN_AUDIO_HOST_SUFFIXES = (".douyinstatic.com", ".byteimg.com")


def _is_douyin_url(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in DOUYIN_HOSTS)


def _extract_shared_url(value: str) -> str:
    match = re.search(r"https?://[^\s<>'\"]+", value.strip())
    return match.group(0).rstrip("，。；;、") if match else value.strip()


def _douyin_video_id(document: str) -> str:
    match = re.search(r"(?:douyin\.com/video/|/video/)(\d{10,})", document)
    return match.group(1) if match else ""


def _douyin_media_urls(document: str) -> list[str]:
    decoded = html.unescape(document).replace(r"\u002F", "/").replace(r"\/", "/")
    candidates = re.findall(
        r'<audio\b[^>]*?\bsrc="(https://[^"]+)"',
        decoded,
        flags=re.IGNORECASE,
    )
    candidates.extend(re.findall(
        r'<(?:video|source)\b[^>]*?\bsrc="(https://[^"]+)"',
        decoded,
        flags=re.IGNORECASE,
    ))
    candidates.extend(re.findall(
        r'https://[^"\s<>]+(?:ies-music|music-play|music/)[^"\s<>]*',
        decoded,
        flags=re.IGNORECASE,
    ))
    candidates.extend(re.findall(r'(?:src|href)="(https://[^"]+)"', decoded))
    trusted: list[str] = []
    for encoded_url in candidates:
        url = html.unescape(encoded_url)
        hostname = (urlparse(url).hostname or "").lower()
        path = urlparse(url).path.lower()
        trusted_video = any(hostname.endswith(suffix) for suffix in DOUYIN_MEDIA_HOST_SUFFIXES)
        trusted_audio = any(hostname.endswith(suffix) for suffix in DOUYIN_AUDIO_HOST_SUFFIXES) and any(
            marker in path for marker in ("ies-music", "music-play", "/music/", "musically-maliva-obj")
        )
        if trusted_video or trusted_audio:
            trusted.append(url)
    return list(dict.fromkeys(trusted))


def _douyin_media_url(document: str) -> str:
    urls = _douyin_media_urls(document)
    return urls[0] if urls else ""
