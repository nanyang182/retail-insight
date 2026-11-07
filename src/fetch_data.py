# -*- coding: utf-8 -*-
"""
retail-insight · 数据下载
------------------------------------------------
从 UCI 机器学习仓库下载 Online Retail 数据集，转换成流水线要的 csv.gz。

用法：python src/fetch_data.py
说明：只需跑一次。已经存在 data/raw/online_retail.csv.gz 时会自动跳过。
"""
from __future__ import annotations

import io
import sys
import urllib.request
import zipfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
TARGET = RAW_DIR / "online_retail.csv.gz"

URL = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"
UA = "Mozilla/5.0 (retail-insight; educational use)"


def main() -> None:
    if TARGET.exists():
        print(f"已存在，跳过下载：{TARGET.relative_to(ROOT)}")
        return

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"下载 {URL}")
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        blob = resp.read()
    print(f"  收到 {len(blob)/1024/1024:.1f} MB")

    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        name = next(n for n in z.namelist() if n.lower().endswith((".xlsx", ".csv")))
        data = z.read(name)
    print(f"  解出 {name}（{len(data)/1024/1024:.1f} MB）")

    if name.lower().endswith(".xlsx"):
        import pandas as pd

        print("  转换 xlsx -> csv.gz（约 20 秒）…")
        df = pd.read_excel(io.BytesIO(data), engine="openpyxl")
        df.to_csv(TARGET, index=False, compression="gzip")
    else:
        TARGET.write_bytes(data)

    print(f"完成：{TARGET.relative_to(ROOT)}（{TARGET.stat().st_size/1024/1024:.1f} MB）")
    print("下一步：python src/pipeline.py")


if __name__ == "__main__":
    main()
