from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS = {"x": MAIN_NS}


def _column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference)
    result = 0
    for char in letters.group(0) if letters else "A":
        result = result * 26 + ord(char) - 64
    return result - 1


def read_first_sheet(path: Path) -> list[list[str]]:
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("x:si", NS):
                shared.append("".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t")))
        root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        result: list[list[str]] = []
        for row in root.findall(".//x:sheetData/x:row", NS):
            values: dict[int, str] = {}
            for cell in row.findall("x:c", NS):
                column = _column_index(cell.attrib.get("r", "A1"))
                kind = cell.attrib.get("t", "")
                raw = cell.findtext("x:v", default="", namespaces=NS)
                if kind == "s" and raw:
                    value = shared[int(raw)]
                elif kind == "inlineStr":
                    value = "".join(node.text or "" for node in cell.iter(f"{{{MAIN_NS}}}t"))
                else:
                    value = raw
                values[column] = value.strip()
            if values:
                width = max(values) + 1
                result.append([values.get(index, "") for index in range(width)])
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the official Qwen-Audio TTS Plus voice workbook")
    parser.add_argument("source", type=Path)
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = read_first_sheet(args.source)
    if args.inspect or not args.output:
        print(json.dumps({"row_count": len(rows), "first_rows": rows[:5], "last_rows": rows[-3:]}, ensure_ascii=False, indent=2))
    if not args.output:
        return
    expected = ["序号", "名称", "voice参数", "性别", "年龄", "特质", "适用场景", "语种", "预览音频文件名"]
    if rows[0] != expected:
        raise ValueError(f"官方音色表表头已变化：{rows[0]}")
    items = []
    for raw in rows[1:]:
        values = [*raw, *("" for _ in range(len(expected) - len(raw)))]
        items.append({
            "sequence": int(values[0]), "name": values[1], "voice": values[2],
            "gender": values[3], "age": values[4], "trait": values[5],
            "scenario": values[6], "language": values[7], "preview_filename": values[8],
        })
    sequences = [item["sequence"] for item in items]
    voices = [item["voice"] for item in items]
    if sequences != list(range(1, len(items) + 1)):
        raise ValueError("官方音色序号不连续")
    if len(voices) != len(set(voices)):
        raise ValueError("官方音色表存在重复 voice 参数")
    payload = {
        "model": "qwen-audio-3.0-tts-plus",
        "source": "https://help.aliyun.com/zh/model-studio/qwen-audio-tts-voice-list",
        "source_file": args.source.name,
        "count": len(items),
        "items": items,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "count": len(items), "unique_voices": len(set(voices))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
