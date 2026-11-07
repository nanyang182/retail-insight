# -*- coding: utf-8 -*-
"""
retail-insight · 数据流水线
------------------------------------------------
原始交易明细  ->  清洗  ->  指标计算  ->  dashboard/data.js

运行：python src/pipeline.py
依赖：pandas（requirements.txt）

设计原则
1. 所有口径写在代码里、输出里也写一遍，避免"数字对不上"。
2. 清洗规则逐条注释，任何一条都能在报告里解释。
3. 结论文字由数据生成，换数据后结论自动更新，不会说假话。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:  # Windows 控制台默认 GBK，直接输出 £ 会崩
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "online_retail.csv.gz"
OUT = ROOT / "dashboard" / "data.js"

# 商品编码规则：5 位数字，可带 0~2 位字母后缀（如 85123A）
PRODUCT_CODE = r"^\d{5}[A-Z]{0,2}$"

# 订单金额分档（英镑）
PRICE_BANDS = [
    (0, 100, "< £100"),
    (100, 250, "£100–250"),
    (250, 500, "£250–500"),
    (500, 1000, "£500–1k"),
    (1000, 2500, "£1k–2.5k"),
    (2500, float("inf"), "> £2.5k"),
]

# 观察窗口：全周期 / 2011 上半年 / 2011 下半年
PERIODS = [
    ("all", "全周期", None, None),
    ("h1", "2011 H1", "2011-01-01", "2011-06-30"),
    ("h2", "2011 H2", "2011-07-01", "2011-12-31"),
]


# ---------------------------------------------------------------- 读取与清洗
def load_raw() -> pd.DataFrame:
    df = pd.read_csv(
        RAW,
        parse_dates=["InvoiceDate"],
        dtype={
            "InvoiceNo": "string",
            "StockCode": "string",
            "Description": "string",
            "Country": "string",
        },
    )
    return df


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """返回 (全量清洗结果, 有效销售明细, 退货明细)"""
    df = df.drop_duplicates()  # 5268 行完全重复的记录
    df["InvoiceNo"] = df["InvoiceNo"].str.strip()
    df["StockCode"] = df["StockCode"].str.strip().str.upper()
    df["Country"] = df["Country"].fillna("Unknown")
    df["Description"] = df["Description"].fillna("未命名商品").str.strip()

    # 取消单：InvoiceNo 以 C 开头
    df["is_cancel"] = df["InvoiceNo"].str.startswith("C", na=False)
    # 商品行：排除 POST / DOT / M / BANK CHARGES 等费用与手工调整行
    df["is_product"] = df["StockCode"].str.match(PRODUCT_CODE, na=False)
    df["revenue"] = df["Quantity"] * df["UnitPrice"]

    sales = df[
        (~df["is_cancel"])
        & df["is_product"]
        & (df["Quantity"] > 0)
        & (df["UnitPrice"] > 0)
    ].copy()

    returns = df[df["is_cancel"] & df["is_product"]].copy()
    returns["revenue"] = returns["revenue"].abs()
    return df, sales, returns


# ---------------------------------------------------------------- 指标计算
def _score(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """按分位数打 1~5 分，避免 qcut 在重复值上切不动"""
    r = series.rank(pct=True, method="average")
    s = np.ceil(r * 5).clip(1, 5).astype(int)
    return s if higher_is_better else (6 - s)


def rfm_segments(sales: pd.DataFrame) -> pd.DataFrame:
    s = sales.dropna(subset=["CustomerID"]).copy()
    s["CustomerID"] = s["CustomerID"].astype("int64")
    snapshot = s["InvoiceDate"].max() + pd.Timedelta(days=1)

    g = s.groupby("CustomerID").agg(
        last_order=("InvoiceDate", "max"),
        orders=("InvoiceNo", "nunique"),
        monetary=("revenue", "sum"),
    )
    g["recency"] = (snapshot - g["last_order"]).dt.days
    g["R"] = _score(g["recency"], higher_is_better=False)
    g["F"] = _score(g["orders"])
    g["M"] = _score(g["monetary"])

    def label(row) -> str:
        r, f, m = row["R"], row["F"], row["M"]
        if r >= 4 and f >= 4:
            return "核心客户"
        if r >= 4 and m >= 4:
            return "高价值新客"
        if r >= 4:
            return "新客 / 低频"
        if f >= 4 or m >= 4:
            return "沉睡高价值"
        return "低价值流失"

    g["segment"] = g.apply(label, axis=1)
    return g


def lorenz_curve(g: pd.DataFrame, step: int = 5) -> list[dict]:
    rev = g["monetary"].sort_values(ascending=False).to_numpy()
    cum = np.cumsum(rev) / rev.sum() * 100
    xs = np.arange(1, len(rev) + 1) / len(rev) * 100
    pts = [{"x": 0.0, "y": 0.0}]
    for p in range(step, 101, step):
        idx = min(int(np.searchsorted(xs, p)), len(cum) - 1)
        pts.append({"x": float(p), "y": round(float(cum[idx]), 1)})
    return pts


def build_period(sales: pd.DataFrame, returns: pd.DataFrame, pkey: str, label: str,
                 span: str, df_all: pd.DataFrame) -> dict:
    gross = float(sales["revenue"].sum())
    ret = float(returns["revenue"].sum())
    net = gross - ret

    orders = int(sales["InvoiceNo"].nunique())
    inv_totals = sales.groupby("InvoiceNo")["revenue"].sum()

    rfm = rfm_segments(sales)
    cust_orders = sales.dropna(subset=["CustomerID"]).groupby("CustomerID")["InvoiceNo"].nunique()
    repeat_rate = float((cust_orders >= 2).mean() * 100) if len(cust_orders) else 0.0

    # 月度：收入 / 退货 / 退货率
    m_sales = sales.set_index("InvoiceDate")["revenue"].resample("MS").sum()
    m_ret = returns.set_index("InvoiceDate")["revenue"].resample("MS").sum().reindex(m_sales.index, fill_value=0.0)
    data_end = sales["InvoiceDate"].max()
    monthly = []
    for idx, v, rv in zip(m_sales.index, m_sales.values, m_ret.values):
        # 首尾月份可能被数据边界截断，标记出来，避免把"不完整月"当趋势
        partial = (idx + pd.offsets.MonthEnd(0)) > data_end
        monthly.append(
            {
                "month": idx.strftime("%Y-%m"),
                "label": f"{idx.month}月",
                "revenue": round(float(v), 0),
                "returns": round(float(rv), 0),
                "return_rate": round(float(rv / v * 100) if v else 0.0, 2),
                "partial": bool(partial),
            }
        )

    seg = (
        rfm.groupby("segment")
        .agg(customers=("monetary", "size"), revenue=("monetary", "sum"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    seg["share"] = seg["revenue"] / seg["revenue"].sum() * 100
    seg["cust_share"] = seg["customers"] / seg["customers"].sum() * 100
    rfm_out = [
        {
            "segment": r["segment"],
            "customers": int(r["customers"]),
            "revenue": round(float(r["revenue"]), 0),
            "share": round(float(r["share"]), 1),
            "cust_share": round(float(r["cust_share"]), 1),
        }
        for _, r in seg.iterrows()
    ]

    # 订单金额分档
    price = []
    for lo, hi, name in PRICE_BANDS:
        cnt = int(((inv_totals >= lo) & (inv_totals < hi)).sum())
        price.append({"band": name, "orders": cnt, "share": round(cnt / len(inv_totals) * 100, 1)})

    # Top 商品
    prod = (
        sales.groupby("StockCode")
        .agg(desc=("Description", "first"), revenue=("revenue", "sum"), qty=("Quantity", "sum"))
        .sort_values("revenue", ascending=False)
        .head(10)
        .reset_index()
    )
    products = [
        {
            "code": r["StockCode"],
            "name": str(r["desc"])[:34],
            "revenue": round(float(r["revenue"]), 0),
            "qty": int(r["qty"]),
        }
        for _, r in prod.iterrows()
    ]

    # 市场分布（英国单列）
    by_country = sales.groupby("Country")["revenue"].sum().sort_values(ascending=False)
    uk_share = float(by_country.get("United Kingdom", 0.0) / gross * 100)
    countries = [
        {"name": k, "revenue": round(float(v), 0), "share": round(float(v / gross * 100), 1)}
        for k, v in by_country.drop(labels=["United Kingdom"], errors="ignore").head(8).items()
    ]

    # 商品集中度（ABC 分级用）
    sku_rev = sales.groupby("StockCode")["revenue"].sum().sort_values(ascending=False)
    n_sku = int(len(sku_rev))
    top20_n = max(1, int(np.ceil(n_sku * 0.2)))
    sku = {
        "count": n_sku,
        "top20_share": round(float(sku_rev.head(top20_n).sum() / gross * 100), 1) if gross else 0.0,
        "top10_share": round(float(sku_rev.head(10).sum() / gross * 100), 1) if gross else 0.0,
    }

    lorenz = lorenz_curve(rfm)

    return {
        "key": pkey,
        "label": label,
        "span": span,
        "kpi": {
            "net": round(net, 0),
            "gross": round(gross, 0),
            "returns": round(ret, 0),
            "orders": orders,
            "customers": int(sales["CustomerID"].nunique()),
            "aov": round(gross / orders, 1) if orders else 0,
            "return_rate": round(ret / gross * 100, 2) if gross else 0,
            "repeat_rate": round(repeat_rate, 1),
            "missing_id_share": round(float(sales["CustomerID"].isna().mean() * 100), 1),
            "uk_share": round(uk_share, 1),
        },
        "monthly": monthly,
        "rfm": rfm_out,
        "lorenz": lorenz,
        "price": price,
        "products": products,
        "countries": countries,
        "sku": sku,
        "rows_clean": int(len(sales)),
    }


def make_insights(allp: dict) -> list[dict]:
    kpi = allp["kpi"]
    # 前 20% 客户贡献
    pt = {p["x"]: p["y"] for p in allp["lorenz"]}
    top20 = pt.get(20.0, 0.0)

    core = next((s for s in allp["rfm"] if s["segment"] == "核心客户"), None)
    core_cust = core["cust_share"] if core else 0
    core_rev = core["share"] if core else 0

    monthly = sorted(allp["monthly"], key=lambda m: m["revenue"], reverse=True)
    peak, low = monthly[0], monthly[-1]
    ratio = peak["revenue"] / low["revenue"] if low["revenue"] else 0

    top10_share = sum(p["revenue"] for p in allp["products"]) / kpi["gross"] * 100
    sku = allp["sku"]

    return [
        {
            "tag": "客户结构",
            "metric": f"{top20:.0f}%",
            "metric_label": "收入来自前 20% 客户",
            "title": f"前 20% 客户贡献 {top20:.0f}% 收入，客户结构高度集中",
            "body": (
                f"仅 {core_cust:.0f}% 的客户（约 {core['customers'] if core else 0} 人）贡献了 "
                f"{core_rev:.0f}% 的收入。这类客户一旦流失，收入缺口无法靠拉新补上。"
                f"建议设立分层服务：核心客户配专属跟单与新品尝鲜权，而非继续做全量打折。"
            ),
        },
        {
            "tag": "季节节奏",
            "metric": f"{ratio:.1f}×",
            "metric_label": "旺季 / 淡季收入比",
            "title": f"{peak['label']} 收入是 {low['label']} 的 {ratio:.1f} 倍，备货与人力应按季节排",
            "body": (
                f"峰值月 {peak['month']} 收入 £{peak['revenue']:,.0f}，谷值月 {low['month']} 仅 "
                f"£{low['revenue']:,.0f}。旺季前 4~6 周应锁定库存与客服排班，"
                f"淡季把预算转向老客唤醒而不是投广告。"
            ),
        },
        {
            "tag": "商品效率",
            "metric": f"{sku['top10_share']:.0f}%",
            "metric_label": "Top 10 SKU 收入占比",
            "title": f"{sku['count']:,} 个 SKU，Top 10 只占 {sku['top10_share']:.0f}% 收入",
            "body": (
                f"前 20% 的 SKU 贡献 {sku['top20_share']:.0f}% 收入，收入分散在长尾上："
                f"不依赖单一爆款是好事，但库存单位多、管理成本高。建议按 ABC 分级——"
                f"A 类保供并扩陈列，C 类设清仓阈值，把采购精力从长尾收回来。"
            ),
        },
    ]


def main() -> None:
    if not RAW.exists():
        sys.exit(f"找不到原始数据：{RAW}\n请先运行 python src/fetch_data.py")

    raw = load_raw()
    df, sales, returns = clean(raw)
    print(f"原始 {len(raw):,} 行 -> 去重后 {len(df):,} 行")
    print(f"有效销售 {len(sales):,} 行 / 订单 {sales['InvoiceNo'].nunique():,} 笔")
    print(f"退货 {len(returns):,} 行 / 金额 £{returns['revenue'].sum():,.0f}")

    whole = df  # 仅用于取时间范围
    tmin, tmax = whole["InvoiceDate"].min(), whole["InvoiceDate"].max()

    periods = []
    for key, label, start, end in PERIODS:
        s, r = sales, returns
        if start:
            lo, hi = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
            s = sales[(sales["InvoiceDate"] >= lo) & (sales["InvoiceDate"] < hi)]
            r = returns[(returns["InvoiceDate"] >= lo) & (returns["InvoiceDate"] < hi)]
        span = (
            f"{s['InvoiceDate'].min():%Y.%m} – {s['InvoiceDate'].max():%Y.%m}"
            if len(s)
            else "-"
        )
        periods.append(build_period(s, r, key, label, span, df))
        print(f"  [{label}] 收入 £{periods[-1]['kpi']['gross']:,.0f} / 订单 {periods[-1]['kpi']['orders']:,}")

    payload = {
        "meta": {
            "source": "UCI Machine Learning Repository · Online Retail",
            "source_url": "https://archive.ics.uci.edu/dataset/352/online+retail",
            "license": "CC BY 4.0",
            "range": f"{tmin:%Y.%m.%d} – {tmax:%Y.%m.%d}",
            "rows_raw": int(len(raw)),
            "rows_clean": int(len(sales)),
            "orders": int(sales["InvoiceNo"].nunique()),
            "currency": "GBP",
            "generated": pd.Timestamp.now().strftime("%Y-%m-%d"),
        },
        "periods": periods,
        "insights": make_insights(periods[0]),
        "notes": {
            "unit": "金额单位：英镑（£），收入为含税销售额",
            "clean": "剔除完全重复行、非商品行（邮费/手续费/调整）、数量或单价 ≤ 0 的异常行",
            "return": "取消单（InvoiceNo 以 C 开头）计为退货，按金额绝对值统计",
            "rfm": "R=最近购买距今天数，F=订单数，M=消费金额；按分位数打 1~5 分",
            "segment": "核心客户 R≥4 且 F≥4；高价值新客 R≥4 且 M≥4；沉睡高价值 F≥4 或 M≥4",
            "anomaly": f"约 {periods[0]['kpi']['missing_id_share']:.1f}% 的销售行没有客户 ID，故复购与 RFM 仅覆盖可识别客户",
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text(
        "/* 由 src/pipeline.py 自动生成，请勿手工修改 */\n"
        f"window.__RETAIL_DATA__ = {body};\n",
        encoding="utf-8",
    )
    print(f"\n已生成 {OUT.relative_to(ROOT)}  ({OUT.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
