"""Mechanically rebuild one book's full-text source layer from a CC0 book page.

This script only processes one already-downloaded book page per invocation.
"""

from argparse import ArgumentParser
from html.parser import HTMLParser
from pathlib import Path
import re


class BookParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_main = False
        self.depth = 0
        self.capture = None
        self.items = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if not self.in_main and tag == "main" and attrs.get("data-render") == "book":
            self.in_main = True
            self.depth = 1
            return
        if not self.in_main:
            return
        if self.depth == 1 and (tag in ("h1", "h2") or (tag == "div" and attrs.get("data-sec") == "p")):
            self.capture = [tag, []]
        if self.capture and tag == "br":
            self.capture[1].append("\n")
        self.depth += 1

    def handle_data(self, data):
        if self.capture:
            self.capture[1].append(data)

    def handle_endtag(self, tag):
        if not self.in_main:
            return
        self.depth -= 1
        if self.capture and tag == self.capture[0] and self.depth == 1:
            text = re.sub(r"[ \t\r\n]+", " ", "".join(self.capture[1])).strip()
            self.items.append((self.capture[0], text))
            self.capture = None
        if tag == "main" and self.depth == 0:
            self.in_main = False


def volume_code(volume, ordinal):
    if volume == "卷上":
        return "V1"
    if volume == "卷下":
        return "V2"
    if volume == "上卷":
        return "V1"
    if volume == "下卷":
        return f"V{max(2, ordinal - 1)}"
    if volume == "中卷":
        return "V2"
    if "序" in volume:
        return "PRE"
    chinese_numbers = {
        "卷一": "V1",
        "卷二": "V2",
        "卷三": "V3",
        "卷四": "V4",
        "卷五": "V5",
        "卷六": "V6",
        "卷七": "V7",
        "卷八": "V8",
        "卷九": "V9",
        "卷十": "V10",
    }
    if volume in chinese_numbers:
        return chinese_numbers[volume]
    return f"H{ordinal}"


def main():
    p = ArgumentParser()
    p.add_argument("--html", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--section-marker", required=True)
    p.add_argument("--append", action="store_true")
    p.add_argument("--heading", required=True)
    p.add_argument("--work-id", required=True)
    p.add_argument("--work-title", required=True)
    p.add_argument("--source-url", required=True)
    p.add_argument("--edition", required=True)
    p.add_argument("--old-status", required=True)
    p.add_argument("--new-status", required=True)
    p.add_argument("--expected-paragraphs", type=int, required=True)
    a = p.parse_args()

    parser = BookParser()
    parser.feed(Path(a.html).read_text(encoding="utf-8"))
    paragraphs = sum(tag == "div" for tag, _ in parser.items)
    if paragraphs != a.expected_paragraphs:
        raise SystemExit(f"paragraph count mismatch: got {paragraphs}, expected {a.expected_paragraphs}")

    output = Path(a.output)
    old = output.read_text(encoding="utf-8")
    if a.old_status not in old:
        raise SystemExit("completion-status row not found")
    old = old.replace(a.old_status, a.new_status, 1)
    if a.append:
        start = len(old)
        end = len(old)
    else:
        start = old.index(a.section_marker)
        end = old.find("\n# 《", start + len(a.section_marker))
        if end < 0:
            end = len(old)

    lines = [
        a.heading,
        "",
        "```yaml",
        f'work_id: "{a.work_id}"',
        f'work_title: "{a.work_title}"',
        'author: "薛己"',
        'dynasty: "明"',
        'published_text_source: "中醫笈成"',
        f'source_url: "{a.source_url}"',
        'rights_status: "CC0（依來源站著作權聲明）；古籍正文為公眾領域"',
        'rights_statement_url: "https://jicheng.tw/tcm/copyright.html"',
        f'source_edition: "{a.edition}"',
        'full_text_transcription_status: "complete_from_public_CC0_transcription"',
        'scan_verification_status: "not_started"',
        f'paragraph_count: {paragraphs}',
        'structuring_rule: "每一公開正文段落保留為不可改寫的 source_paragraph；病例與通論、方藥不強行混同。"',
        '```',
        "",
        "> 本层保留全书篇章、通论、方药和病例段落；`record_kind: source_paragraph` 不等于已完成独立医案切分。",
        "",
        "## 全文",
        "",
    ]

    volume = None
    section = None
    volume_ordinal = 0
    counts = {}
    for tag, value in parser.items:
        if tag == "h1":
            volume = value
            section = None
            volume_ordinal += 1
            counts.setdefault(volume, 0)
            lines.extend([f"### {volume}", ""])
        elif tag == "h2":
            section = value
            lines.extend([f"#### {section}", ""])
        else:
            counts[volume] += 1
            sid = f"{a.work_id}-{volume_code(volume, volume_ordinal)}-P{counts[volume]:03d}"
            lines.extend([
                f"##### {sid}",
                "",
                "```yaml",
                f'source_id: "{sid}"',
                f'work_id: "{a.work_id}"',
                'text_layer: "original_text"',
                'record_kind: "source_paragraph"',
                f'volume: "{volume}"',
                f'section: "{section or ""}"',
                f'source_location: "{volume}・{section or volume}・正文段落{counts[volume]}"',
                f'source_url: "{a.source_url}"',
                'scan_verification_status: "not_started"',
                'rights_status: "CC0_public_transcription"',
                '```',
                "",
                value,
                "",
            ])

    replacement = "\n".join(lines).rstrip() + "\n"
    if a.append:
        output.write_text(old.rstrip() + "\n\n---\n\n" + replacement, encoding="utf-8")
    else:
        remainder = "" if end == len(old) else old[end + 1:]
        output.write_text(old[:start] + replacement + remainder, encoding="utf-8")
    print(f"{a.work_title}: {paragraphs} paragraphs; " + ", ".join(f"{k}={v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
