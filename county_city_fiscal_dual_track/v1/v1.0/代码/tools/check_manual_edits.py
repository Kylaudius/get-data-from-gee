# -*- coding: utf-8 -*-
"""
tools/check_manual_edits.py  检查研究者是否手动修改过本迭代文件

为什么需要：每次开新迭代（例如从 v1.0 到 v1.1）之前，要先确认研究者有没有手动改过
上一版的报告、参数或代码，避免新构建覆盖手动修改。

用法（在 Mac “终端 Terminal” 中，先 cd 到 代码/ 文件夹）：
  # A. 迭代结束时记录指纹（生成 迭代文件夹/manifest.json）
  python tools/check_manual_edits.py --record
  # B. 下一次迭代开始前比对（列出新增、修改、删除的文件）
  python tools/check_manual_edits.py --check

说明：数据/原始、数据/中间、数据/结果 下的大文件默认不纳入比对（它们本来就会被脚本更新）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import VERSION_DIR, atomic_write_json, sha256_of  # noqa: E402

# ---------------------------------------------------------------------------
# 代码块 1：确定需要比对的文件范围
# 目的：只比对研究者可能手动编辑的文件（报告、附录、参数、代码、图表、模板、readme）。
# 结果：返回相对路径 → 文件指纹 的字典。
# ---------------------------------------------------------------------------
EXCLUDE_PARTS = {"原始", "中间", "结果", "__pycache__", ".ipynb_checkpoints"}
MANIFEST = VERSION_DIR / "manifest.json"


def scan() -> dict:
    out = {}
    for p in sorted(VERSION_DIR.rglob("*")):
        if not p.is_file() or p.name in ("manifest.json", ".DS_Store") or p.suffix == ".tmp":
            continue
        rel = p.relative_to(VERSION_DIR)
        if EXCLUDE_PARTS & set(rel.parts):
            continue
        out[str(rel)] = sha256_of(p)
    return out


# ---------------------------------------------------------------------------
# 代码块 2：记录或比对
# 目的：--record 把当前指纹写入 manifest.json；--check 读取旧指纹并与当前文件对比。
# 结果：终端打印“被修改 / 新增 / 删除”的文件清单；没有差异时打印“未发现手动修改”。
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--record", action="store_true", help="记录当前文件指纹")
    g.add_argument("--check", action="store_true", help="与已记录的指纹比对")
    args = ap.parse_args()

    now = scan()
    if args.record:
        atomic_write_json(now, MANIFEST)
        print(f"已记录 {len(now)} 个文件的指纹 → {MANIFEST}")
        return
    if not MANIFEST.exists():
        print("尚无 manifest.json，请先运行 --record。")
        return
    old = json.loads(MANIFEST.read_text(encoding="utf-8"))
    changed = [k for k in now if k in old and now[k] != old[k]]
    added = [k for k in now if k not in old]
    removed = [k for k in old if k not in now]
    if not (changed or added or removed):
        print("未发现手动修改。")
        return
    for title, lst in (("被修改", changed), ("新增", added), ("删除", removed)):
        if lst:
            print(f"\n【{title}】{len(lst)} 个文件：")
            for k in lst:
                print("  -", k)


if __name__ == "__main__":
    main()
