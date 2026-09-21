#!/usr/bin/env python3
"""为单个文件或目录生成确定性的 SHA-256 清单（只读）。"""
from __future__ import annotations
import argparse, hashlib
from pathlib import Path

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024): digest.update(block)
    return digest.hexdigest()

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("path", type=Path, help="待计算哈希的文件或目录")
args = parser.parse_args()
root = args.path.resolve()
if root.is_file():
    print(f"{sha256(root)}  {root.name}  {root.stat().st_size}")
elif root.is_dir():
    for path in sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink()):
        print(f"{sha256(path)}  {path.relative_to(root).as_posix()}  {path.stat().st_size}")
else:
    parser.error(f"不是文件或目录：{root}")
