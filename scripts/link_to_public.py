#!/usr/bin/env python3
"""验证个人副本和公共副本等价后，在原路径建立指向公共副本的绝对软链接。"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            hasher.update(block)
    return hasher.hexdigest()


def manifest(root: Path) -> list[tuple[str, str, int | str]]:
    if root.is_symlink():
        return [(".", "link", os.readlink(root))]
    if root.is_file():
        return [(root.name, "file", f"{root.stat().st_size}:{sha256(root)}")]
    records: list[tuple[str, str, int | str]] = []
    for item in sorted(root.rglob("*")):
        relative = item.relative_to(root).as_posix()
        if item.is_symlink():
            records.append((relative, "link", os.readlink(item)))
        elif item.is_dir():
            records.append((relative, "dir", 0))
        elif item.is_file():
            records.append((relative, "file", f"{item.stat().st_size}:{sha256(item)}"))
        else:
            records.append((relative, "other", 0))
    return records


def inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def fail(message: str) -> None:
    print(f"错误：{message}", file=sys.stderr)
    raise SystemExit(2)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("local_path", type=Path, help="将被替换为软链接的个人文件或目录")
parser.add_argument("public_path", type=Path, help="已校验的公共文件或目录")
parser.add_argument(
    "--personal-root",
    type=Path,
    default=Path("/data") / getpass.getuser(),
    help="个人目录根路径；默认 /data/<当前用户名>",
)
parser.add_argument(
    "--public-root", type=Path, default=Path("/publicdata"),
    help="本次确认的公共目录根路径；默认 /publicdata",
)
parser.add_argument("--verify", action="store_true", help="执行完整 SHA-256 内容校验")
parser.add_argument("--apply", action="store_true", help="完成备份与软链接切换；必须同时提供 --verify")
args = parser.parse_args()

local = args.local_path.absolute()
public = args.public_path.resolve(strict=False)
personal_root = args.personal_root.resolve(strict=False)
public_root = args.public_root.resolve(strict=False)

if not local.exists() and not local.is_symlink():
    fail(f"个人路径不存在：{local}")
if local.is_symlink():
    fail(f"个人路径已经是符号链接，不会覆盖：{local}")
if not public.exists():
    fail(f"公共路径不存在：{public}")
if not inside(local, personal_root) or local == personal_root:
    fail(f"个人路径必须位于个人目录内且不能是目录根：{personal_root}")
if not inside(public, public_root):
    fail(f"公共路径必须位于已确认公共根目录内：{public_root}")
if local.is_dir() != public.is_dir() or local.is_file() != public.is_file():
    fail("个人路径与公共路径的对象类型不一致")
if args.apply and not args.verify:
    fail("--apply 必须同时提供 --verify")

print(f"个人路径：{local}")
print(f"公共路径：{public}")
print(f"个人根目录：{personal_root}")
print(f"公共根目录：{public_root}")

if not args.verify:
    print("仅显示计划；使用 --verify 执行完整内容校验。")
    raise SystemExit(0)

print("正在计算完整内容清单与 SHA-256，请耐心等待……")
if manifest(local) != manifest(public):
    fail("内容校验不一致，未创建链接")
print("内容校验通过。")

if not args.apply:
    print("仅校验完成；如需切换，请在明确确认后增加 --apply。")
    raise SystemExit(0)

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = local.with_name(f"{local.name}.pre-public-link-backup-{stamp}")
if backup.exists() or backup.is_symlink():
    fail(f"备份路径已存在：{backup}")

try:
    os.rename(local, backup)
    os.symlink(str(public), str(local), target_is_directory=public.is_dir())
    if local.resolve(strict=True) != public.resolve(strict=True):
        raise RuntimeError("新链接未解析到预期公共路径")
except Exception as error:
    if local.is_symlink() or local.exists():
        try:
            if local.is_dir() and not local.is_symlink():
                os.rmdir(local)
            else:
                local.unlink()
        except OSError:
            pass
    if backup.exists() or backup.is_symlink():
        os.rename(backup, local)
    fail(f"切换失败，已尝试恢复个人路径：{error}")

print(f"路径交接成功：{local} -> {public}")
print(f"个人备份仍保留：{backup}")
print("请先验证原有代码可正常读取该路径；删除备份必须另行明确确认。")
