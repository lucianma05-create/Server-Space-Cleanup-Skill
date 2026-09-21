#!/usr/bin/env python3
"""只读盘点目录空间，并按便于审查的类别汇总。"""
from __future__ import annotations
import argparse, os
from collections import defaultdict
from pathlib import Path

MODEL = {".pt", ".pth", ".bin", ".safetensors", ".ckpt"}
DATA = {".json", ".jsonl", ".csv", ".tsv", ".parquet", ".arrow", ".tar", ".zip", ".gz"}

def readable(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024 or unit == "TiB": return f"{n:.1f} {unit}"
        n /= 1024
    return str(n)

def category(relative: Path) -> str:
    parts, name = {x.lower() for x in relative.parts}, relative.name.lower()
    if "checkpoint" in name or "checkpoint" in parts: return "checkpoint"
    if relative.suffix.lower() in MODEL or "model" in parts or "models" in parts: return "模型或权重"
    if relative.suffix.lower() in DATA or "dataset" in parts or "data" in parts: return "数据集或压缩包"
    if ".cache" in parts or "cache" in parts: return "缓存"
    if "conda" in parts or "envs" in parts: return "虚拟环境"
    if relative.suffix.lower() in {".log", ".out", ".err"}: return "日志"
    return "其他"

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("root", type=Path, help="待盘点的个人目录")
parser.add_argument("--min-size-gib", type=float, default=1, help="仅列出不小于该大小（GiB）的文件")
parser.add_argument("--limit", type=int, default=50, help="最多列出多少个大文件")
args = parser.parse_args()
root = args.root.resolve()
if not root.is_dir(): parser.error(f"不是目录：{root}")
minimum, totals, large = int(args.min_size_gib * 1024**3), defaultdict(int), []
for current, dirs, files in os.walk(root, onerror=lambda _: None):
    dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(current, d))]
    for name in files:
        path = Path(current, name)
        try: stat = path.stat()
        except OSError: continue
        if not path.is_file(): continue
        kind = category(path.relative_to(root))
        totals[kind] += stat.st_size
        if stat.st_size >= minimum: large.append((stat.st_size, path, kind))
print(f"目录：{root}\n分类汇总：")
for kind, size in sorted(totals.items(), key=lambda x: x[1], reverse=True):
    print(f"  {kind:20} {readable(size):>10}")
print(f"大文件（>= {readable(minimum)}）：")
for size, path, kind in sorted(large, reverse=True)[:args.limit]:
    print(f"  {readable(size):>10}  {kind:20}  {path}")
