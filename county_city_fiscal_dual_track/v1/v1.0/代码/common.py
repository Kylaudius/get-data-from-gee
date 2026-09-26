# -*- coding: utf-8 -*-
"""
common.py  公共工具模块（被其他脚本 import，不需要单独运行）

作用：
  1. 读取 外部参数/config.yaml，统一管理路径与参数；
  2. 提供日志 (logging)、按 chunk 汇报进度 (ChunkProgress)、断点续跑 (resume) 所需的原子写入与完成标记；
  3. 提供读取中文表格（自动识别 UTF-8 / GBK 编码）、行政区划代码 (adcode) 规范化与单元类型判别等函数。

所有文件读写统一使用 UTF-8（CSV 写出使用 utf-8-sig，方便 Mac/Windows 的 Excel 直接打开不乱码）。
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# 代码块 1：路径常量
# 目的：确定“本迭代文件夹”(v1/v1.0) 的位置。所有相对路径都以它为起点，
#       这样把整个 v1.0 文件夹拷到别处也能直接运行。
# 结果：VERSION_DIR 指向 .../v1/v1.0；CONFIG_PATH 指向 外部参数/config.yaml。
# ---------------------------------------------------------------------------
CODE_DIR = Path(__file__).resolve().parent
# 环境变量 FDT_BASE_DIR 仅供 tests/run_smoke_test.py 使用（把全部读写重定向到临时文件夹）；正常使用无需设置。
VERSION_DIR = Path(os.environ.get("FDT_BASE_DIR", CODE_DIR.parent)).resolve()
CONFIG_PATH = VERSION_DIR / "外部参数" / "config.yaml"


# ---------------------------------------------------------------------------
# 代码块 2：读取配置
# 目的：把 config.yaml 读成 Python 字典；以后改年份、阈值、路径只改 yaml，不改代码。
# 结果：返回 dict；若文件不存在会给出中文报错提示。
# ---------------------------------------------------------------------------
def load_config(path: Path | str = CONFIG_PATH) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"找不到配置文件：{path}。请确认 外部参数/config.yaml 存在。")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve(p: str | Path) -> Path:
    """把 config 里的相对路径解析为以 VERSION_DIR 为起点的绝对路径；绝对路径原样返回。"""
    p = Path(p).expanduser()
    return p if p.is_absolute() else (VERSION_DIR / p).resolve()


# ---------------------------------------------------------------------------
# 代码块 3：日志
# 目的：同时在终端和日志文件里记录运行过程，出错时可以把日志发给合作者排查。
# 结果：返回 logger；日志文件默认写在 数据/中间/logs/ 下。
# ---------------------------------------------------------------------------
def get_logger(name: str, log_dir: Path | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    log_dir = log_dir or (VERSION_DIR / "数据" / "中间" / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_dir / f"{name}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


# ---------------------------------------------------------------------------
# 代码块 4：按 chunk 汇报进度
# 目的：大任务分成若干 chunk（批次）执行，每完成一个 chunk 打印：
#       第几批/共几批、本批耗时、累计完成比例、预计剩余时间 (ETA)。
# 结果：终端与日志中出现类似
#       [chunk 12/58] 完成 25 个单元 | 本批 41.2s | 累计 20.7% | 预计剩余 31.5 min
# ---------------------------------------------------------------------------
class ChunkProgress:
    def __init__(self, total_chunks: int, logger: logging.Logger, label: str = "chunk"):
        self.total = max(int(total_chunks), 1)
        self.logger = logger
        self.label = label
        self.t0 = time.time()
        self.done_count = 0          # 本次运行中实际计算完成的 chunk 数
        self.skipped = 0             # 因断点续跑而跳过的 chunk 数
        self._chunk_t0 = None

    def skip(self, i: int, reason: str = "已存在结果，跳过（断点续跑）"):
        self.skipped += 1
        self.logger.info(f"[{self.label} {i + 1}/{self.total}] {reason}")

    def start(self, i: int, desc: str = ""):
        self._chunk_t0 = time.time()
        self.logger.info(f"[{self.label} {i + 1}/{self.total}] 开始 {desc}")

    def finish(self, i: int, n_items: int | None = None):
        self.done_count += 1
        dt = time.time() - (self._chunk_t0 or time.time())
        finished = self.done_count + self.skipped
        pct = 100.0 * finished / self.total
        elapsed = time.time() - self.t0
        remaining = self.total - finished
        eta = (elapsed / max(self.done_count, 1)) * remaining / 60.0
        items = f"完成 {n_items} 个单元 | " if n_items is not None else ""
        self.logger.info(
            f"[{self.label} {i + 1}/{self.total}] {items}本批 {dt:.1f}s | 累计 {pct:.1f}% | 预计剩余 {eta:.1f} min"
        )

    def summary(self):
        mins = (time.time() - self.t0) / 60.0
        self.logger.info(
            f"全部结束：共 {self.total} 批，本次计算 {self.done_count} 批，跳过 {self.skipped} 批，用时 {mins:.1f} min"
        )


# ---------------------------------------------------------------------------
# 代码块 5：原子写入（断点续跑的基础）
# 目的：先写到临时文件，写完再改名为正式文件名。这样即使中途断电/断网，
#       也不会留下“写了一半”的坏文件；续跑时只要看正式文件是否存在即可判断该批是否完成。
# 结果：path 位置出现完整文件；不会出现半截文件。
# ---------------------------------------------------------------------------
def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def atomic_write_csv(df: pd.DataFrame, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, path)


def atomic_write_json(obj, path: Path) -> None:
    atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# 代码块 6：失败重试（指数退避）
# 目的：网络抖动或 GEE 偶发超时时自动重试，等待时间依次为 base, 2*base, 4*base ...
# 结果：成功则返回函数结果；超过次数仍失败则抛出最后一次的异常，交给上层处理（例如拆小 chunk）。
# ---------------------------------------------------------------------------
def retry(fn: Callable, tries: int = 4, base_delay: float = 5.0,
          logger: logging.Logger | None = None, what: str = "任务"):
    last = None
    for k in range(tries):
        try:
            return fn()
        except KeyboardInterrupt:
            raise
        except Exception as e:  # noqa: BLE001  这里需要捕获所有异常以便重试
            last = e
            wait = base_delay * (2 ** k)
            if logger:
                logger.warning(f"{what} 第 {k + 1}/{tries} 次失败：{str(e)[:300]} ；{wait:.0f}s 后重试")
            if k < tries - 1:
                time.sleep(wait)
    raise last


# ---------------------------------------------------------------------------
# 代码块 7：读取中文表格
# 目的：统计年鉴导出的 CSV 常见 GBK/GB18030 编码，Excel 另存的又常带 BOM。
#       这里依次尝试 utf-8-sig → gb18030，xlsx/xls 直接用 pandas 读取。
#       行政区划代码列统一按字符串读取，避免 "110101" 被当成数字丢掉前导零或变成 110101.0。
# 结果：返回 DataFrame。
# ---------------------------------------------------------------------------
def read_table(path: Path | str, sheet=0, code_cols: Iterable[str] = ("adcode", "unit_id")) -> pd.DataFrame:
    path = Path(path)
    dtype = {c: str for c in code_cols}
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path, sheet_name=sheet, dtype=dtype)
    for enc in ("utf-8-sig", "gb18030"):
        try:
            return pd.read_csv(path, encoding=enc, dtype=dtype)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("read_table", b"", 0, 1, f"无法识别编码：{path}")


# ---------------------------------------------------------------------------
# 代码块 8：行政区划代码规范化
# 目的：把各种写法（110101、"110101"、110101.0、11010100000 的 12 位统计用区划代码）
#       统一成 6 位字符串，作为全部数据合并的主键 (primary key)。
# 结果：返回 6 位字符串；无法识别时返回 None。
# ---------------------------------------------------------------------------
def norm_adcode(x) -> str | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).strip()
    if s == "" or s.lower() == "nan":
        return None
    s = re.sub(r"\.0+$", "", s)
    s = re.sub(r"\D", "", s)
    if len(s) == 12:          # 统计用区划代码（12 位）取前 6 位
        s = s[:6]
    if len(s) != 6:
        return None
    return s


def pref_code(adcode: str) -> str:
    """地级单元代码：前 4 位 + '00'。直辖市（11/12/31/50）返回省级代码 xx0000。"""
    if adcode[:2] in ("11", "12", "31", "50"):
        return adcode[:2] + "0000"
    return adcode[:4] + "00"


# ---------------------------------------------------------------------------
# 代码块 9：县级单元类型判别
# 目的：把每个县级行政区判为 市辖区 / 县级市 / 县（含自治县、旗、自治旗、特区、林区）/
#       不设区地级市（东莞、中山、儋州、嘉峪关等）。
#       规则优先使用名称后缀，其次使用代码规则，最后可由 外部参数/unit_type_overrides.csv 人工覆盖。
#       注意：直辖市和部分新设区的代码不在 01–20 区间（如上海崇明区 310151、重庆铜梁区 500151），
#       所以不能只靠代码判断。
# 结果：返回字符串 'district' / 'county_city' / 'county' / 'pref_city_no_district'。
# ---------------------------------------------------------------------------
def classify_unit(adcode: str, name: str | None, overrides: dict | None = None) -> str:
    if overrides and adcode in overrides:
        return overrides[adcode]
    name = (name or "").strip()
    if adcode[2:] != "0000" and adcode[4:] == "00":
        return "pref_city_no_district"
    if name.endswith(("林区", "特区")):
        return "county"
    if name.endswith("区"):
        return "district"
    if name.endswith("市"):
        return "county_city"
    if name.endswith(("县", "旗")):
        return "county"
    tail = int(adcode[4:])
    if adcode[2:4] == "90":            # 省直辖县级行政单位（如湖北仙桃 429004）
        return "county_city"
    if 1 <= tail <= 20:
        return "district"
    if 81 <= tail <= 99:
        return "county_city"
    return "county"


def load_overrides(path: Path) -> dict:
    """读取人工覆盖表（adcode,unit_type），不存在则返回空字典。"""
    if not Path(path).exists():
        return {}
    df = read_table(path)
    df["adcode"] = df["adcode"].map(norm_adcode)
    return dict(zip(df["adcode"], df["unit_type"]))


# ---------------------------------------------------------------------------
# 代码块 10：文件指纹
# 目的：计算文件的 SHA-256，用于检查“研究者是否手动改过某个文件”，
#       防止新一轮迭代覆盖手动修改（配合 tools/check_manual_edits.py 使用）。
# 结果：返回 64 位十六进制字符串。
# ---------------------------------------------------------------------------
def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()
