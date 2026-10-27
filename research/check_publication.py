#!/usr/bin/env python3
"""Check tracked text for non-research metadata and private local identifiers.

Findings report only paths and line numbers, never the matched content.
Literary first-person expressions in the historical sources are preserved.
"""
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DISALLOWED=re.compile(
    r'\u5e08\u5f1f|\u5e2b\u5f1f|\u804a\u5929|\u5bf9\u8bdd|\u5c0d\u8a71|'
    r'chatgpt[-]conversation:/{2}|[/]Users[/]|[/]home[/]|'
    r'\u7528\u6237.{0,6}(?:\u660e\u786e|\u8981\u6c42|\u63d0\u4f9b|\u540c\u610f|\u91cd\u8ff0)|'
    r'\u7528\u6236\u63d0\u4f9b'
)


def main():
    files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    checked=0
    findings=[]
    for name in files:
        if not name:continue
        try:text=(ROOT/name).read_text(encoding='utf-8')
        except UnicodeDecodeError:continue
        checked+=1
        for line,content in enumerate(text.splitlines(),1):
            if DISALLOWED.search(content):findings.append(f'{name}:{line}')
    if findings:
        raise SystemExit('Publication metadata findings: '+', '.join(findings))
    print(f'PASS: {checked} tracked text files; restricted metadata findings=0')


if __name__=='__main__':main()
