from __future__ import annotations

from pathlib import Path

import cv2


SOURCE = Path("/mnt/d/报销凭据")
OUTPUT = Path("/mnt/e/codexwork/vision_images")
MAX_SIDE = 2400


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    count = 0
    for source in sorted(SOURCE.glob("IMG_*.JPG")):
        target = OUTPUT / source.name
        if target.exists():
            count += 1
            continue
        image = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"无法读取：{source}")
        height, width = image.shape[:2]
        if max(width, height) > MAX_SIDE:
            ratio = MAX_SIDE / max(width, height)
            image = cv2.resize(
                image,
                (round(width * ratio), round(height * ratio)),
                interpolation=cv2.INTER_AREA,
            )
        if not cv2.imwrite(
            str(target),
            image,
            [cv2.IMWRITE_JPEG_QUALITY, 88, cv2.IMWRITE_JPEG_PROGRESSIVE, 1],
        ):
            raise RuntimeError(f"无法写入：{target}")
        count += 1
    print(f"prepared={count}")


if __name__ == "__main__":
    main()
