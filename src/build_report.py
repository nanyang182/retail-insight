# -*- coding: utf-8 -*-
"""
retail-insight · 生成 Word 版项目报告
------------------------------------------------
把 docs/项目报告.md 的内容排成可以直接提交的 A4 文档。

运行：python src/build_report.py
输出：docs/Retail_Insight_项目报告.docx
"""
from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "Retail_Insight_项目报告.docx"

INK = RGBColor(0x0A, 0x1B, 0x2E)
BLUE = RGBColor(0x1E, 0x63, 0xD8)
MUTED = RGBColor(0x5B, 0x72, 0x85)
LIGHT = RGBColor(0x8F, 0xA3, 0xB8)
FONT = "微软雅黑"


def set_font(run, size=10.5, bold=False, color=INK, spacing=None):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), FONT)
    rfonts.set(qn("w:ascii"), FONT)
    rfonts.set(qn("w:hAnsi"), FONT)
    if spacing is not None:
        run._element.get_or_add_rPr().append(_spacing_el(spacing))


def _spacing_el(twips):
    el = OxmlElement("w:spacing")
    el.set(qn("w:val"), str(twips))
    return el


def bottom_border(paragraph, color="DCE6F2", size=6):
    ppr = paragraph._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "6")
    bottom.set(qn("w:color"), color)
    pbdr.append(bottom)
    ppr.append(pbdr)


def shade(cell, hexcolor):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcpr.append(shd)


def no_borders(table):
    tbl = table._tbl
    tblpr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "none")
        borders.append(el)
    tblpr.append(borders)


def body(doc, text, size=10.5, color=INK, space_after=5, indent=0, bold=False, line=1.5):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = line
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    run = p.add_run(text)
    set_font(run, size=size, color=color, bold=bold)
    return p


def heading(doc, num, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(13)
    p.paragraph_format.space_after = Pt(7)
    r1 = p.add_run(f"{num}  ")
    set_font(r1, size=13, bold=True, color=BLUE)
    r2 = p.add_run(text)
    set_font(r2, size=13, bold=True, color=INK)
    bottom_border(p)
    return p


def bullet(doc, text, size=10.5):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.6)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.5
    r = p.add_run("· ")
    set_font(r, size=size, bold=True, color=BLUE)
    r2 = p.add_run(text)
    set_font(r2, size=size, color=INK)
    return p


def kpi_strip(doc, items):
    table = doc.add_table(rows=1, cols=len(items))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    no_borders(table)
    for i, (value, label) in enumerate(items):
        cell = table.rows[0].cells[i]
        shade(cell, "F4F8FD")
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        cell.paragraphs[0].paragraph_format.space_before = Pt(10)
        cell.paragraphs[0].paragraph_format.space_after = Pt(1)
        r = cell.paragraphs[0].add_run(value)
        set_font(r, size=15, bold=True, color=BLUE)

        p2 = cell.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_after = Pt(9)
        r2 = p2.add_run(label)
        set_font(r2, size=8.5, color=MUTED)
    return table


def simple_table(doc, headers, rows, widths, font_size=9):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        shade(hdr[i], "0A1B2E")
        p = hdr[i].paragraphs[0]
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(h)
        set_font(r, size=font_size, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
    for row in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)
            r = p.add_run(val)
            set_font(r, size=font_size, color=INK)
    for row in table.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
        # 行内不跨页
        trpr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trpr.append(cant)
    # 跨页时重复表头
    trpr = table.rows[0]._tr.get_or_add_trPr()
    hdr = OxmlElement("w:tblHeader")
    hdr.set(qn("w:val"), "true")
    trpr.append(hdr)
    return table


def add_page_number(paragraph):
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_end)
    set_font(run, size=8.5, color=LIGHT)


def main() -> None:
    doc = Document()

    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)

    # 页脚
    footer_p = section.footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = footer_p.add_run("Retail Insight · 王勇恒 · 2026.11    ")
    set_font(r, size=8.5, color=LIGHT)
    add_page_number(footer_p)

    # ---------------- 标题区
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("RETAIL INSIGHT")
    set_font(r, size=9, bold=True, color=BLUE)
    r.font.element.rPr.find(qn("w:rFonts")).set(qn("w:ascii"), "Arial")

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run("电商交易洞察看板")
    set_font(r, size=24, bold=True, color=INK)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run("用 54 万条真实交易明细，回答四个运营问题：收入从哪来、客户会不会走、商品结构健不健康、下一步做什么")
    set_font(r, size=10.5, color=MUTED)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(14)
    r = p.add_run("王勇恒　|　产品经理方向　|　独立完成　|　周期 2 天")
    set_font(r, size=9, color=LIGHT)
    bottom_border(p, color="1E63D8", size=12)

    kpi_strip(doc, [
        ("£9.77M", "净收入"),
        ("19,773", "有效订单"),
        ("4,334", "可识别客户"),
        ("74.6%", "收入来自前 20% 客户"),
    ])

    # ---------------- 一
    heading(doc, "01", "为什么做这个项目")
    body(doc, "产品岗的日常绕不开三个问题：这个功能值不值得做、做了有没有效果、数据能不能支撑判断。"
              "我之前的经历里缺一块「用真实数据完整走一遍」的证据，所以选了一个体量够大、脏数据够多、"
              "又没有标准答案的公开数据集，逼自己从原始流水一路做到结论。")
    body(doc, "选它还有两个现实原因：数据真实（不是造出来的），以及可复现——任何人下载同一份数据，"
              "跑同一份代码，都能得到同样的数字。")

    # ---------------- 二
    heading(doc, "02", "怎么做的")
    simple_table(
        doc,
        ["步骤", "做了什么", "关键判断"],
        [
            ["取数", "UCI Online Retail，541,909 行，2010.12–2011.12", "单表、无成本列，注定只能做收入视角"],
            ["清洗", "去重 5,268 行；剔除邮费/调整行；取消单归为退货", "规则写进代码并输出到页面，数字可回溯"],
            ["建模", "6 个核心指标 + RFM 分层 + 洛伦兹曲线 + ABC", "口径先定死，再画图"],
            ["交付", "零依赖静态看板（手写 SVG）+ 可复跑流水线", "离线可演示、体积极小、样式可控"],
        ],
        widths=[1.8, 8.4, 6.4],
    )
    body(doc, "最终口径：有效销售 £10.25M，退货 £47.6 万（4.6%），净收入 £977 万；"
              "客单价 £518，复购率 65.3%，英国市场占 85.1%。", space_after=10)

    # 产出清单（同时把首页版面填满，避免出现半页空白）
    body(doc, "产出：dashboard/index.html（零依赖看板，双击即开）· src/pipeline.py（清洗与指标流水线）"
              "· 本文档（方法与边界）。", size=9.5, color=MUTED, space_after=4)


    # ---------------- 三
    heading(doc, "03", "三个发现")

    body(doc, "发现 1　收入高度依赖少数客户", bold=True, space_after=3)
    body(doc, "前 20% 的客户贡献了 74.6% 的收入；其中「核心客户」只占客户数的 23.4%（1,014 人），"
              "却贡献了 64.6% 的收入。这类生意拉新的边际收益远低于留客——丢 10 个核心客户，"
              "相当于丢几百个散客。", indent=0.4)

    body(doc, "发现 2　季节性极强，旺季很集中", bold=True, space_after=3)
    body(doc, "11 月收入 £145 万，是 2 月（£50.8 万）的 2.9 倍；9–11 三个月贡献了全年 35% 的收入。"
              "库存、客服排班、投放预算如果按月平均分配，旺季一定掉链子、淡季一定浪费。", indent=0.4)

    body(doc, "发现 3　商品极度长尾，10 个爆款撑不起盘子", bold=True, space_after=3)
    body(doc, "3,791 个 SKU 里，Top 10 只占 10% 收入，前 20% 的 SKU 贡献 78%。不依赖单品的另一面是"
              "管理成本高——长尾 SKU 占用采购精力与库存，但边际贡献很低。", indent=0.4)

    # ---------------- 四
    heading(doc, "04", "三条建议（按优先级）")
    simple_table(
        doc,
        ["优先级", "建议", "依据", "怎么衡量"],
        [
            ["P0", "为核心客户建分层服务：专属跟单、新品尝鲜、账期支持，替代全量打折", "1,014 人贡献 64.6% 收入", "90 天复购率、流失率"],
            ["P1", "按季节排产：旺季前 4–6 周锁库存与人力，淡季预算转向老客唤醒", "9–11 月占全年 35%", "旺季缺货率、履约时效"],
            ["P2", "SKU 做 ABC 分级：A 类保供扩陈列，C 类设清仓阈值", "Top 10 仅占 10%", "C 类 SKU 数、周转天数"],
            ["P3", "补客户 ID 采集：25.1% 的销售行没有客户 ID", "数据质量", "有 ID 订单占比"],
        ],
        widths=[1.5, 7.2, 4.2, 3.7],
        font_size=8.5,
    )
    body(doc, "P3 看起来最不像业务建议，但它是前三条能不能持续做的前提——没有 ID，分层维护就无从谈起。",
         size=9.5, color=MUTED, space_after=8)

    # ---------------- 五
    heading(doc, "05", "复盘：这份分析的边界")
    body(doc, "一个诚实的项目报告，应该主动说清楚自己不能证明什么：", space_after=4)
    bullet(doc, "没有成本数据，只能谈收入结构，不能谈利润结构。真实决策里，「高收入低毛利」的客户可能恰恰该放弃。")
    bullet(doc, "25% 的订单没有客户 ID，复购率与 RFM 只覆盖约 75% 的交易额，会系统性高估客户质量。")
    bullet(doc, "2011 年 12 月只有 9 天数据，趋势图已用浅色标出并跳过该月退货率，但读者仍容易误读。")
    bullet(doc, "单商家、单国家、13 个月，季节性结论不能直接套到别的品类或市场。")
    bullet(doc, "只有相关性，没有因果：说「核心客户贡献 64.6%」没问题，说「维护核心客户就能提升收入」是推断，需要实验验证。")

    body(doc, "如果重做，我会加两件事：一是引入成本列算毛利分层；二是做 cohort 留存，看不同首购月份的客户"
              "在后续月份的留存曲线——那比一个静态复购率有用得多。", space_after=8)

    # ---------------- 六
    heading(doc, "06", "可复现说明")
    body(doc, "同一份数据、同一份代码，任何人都能跑出同样的数字。",
         space_after=5)
    code = doc.add_paragraph()
    code.paragraph_format.left_indent = Cm(0.5)
    code.paragraph_format.space_after = Pt(10)
    code.paragraph_format.line_spacing = 1.4
    code.paragraph_format.keep_together = True
    shade_par = OxmlElement("w:shd")
    shade_par.set(qn("w:val"), "clear")
    shade_par.set(qn("w:fill"), "F4F8FD")
    code._p.get_or_add_pPr().append(shade_par)
    for line in ["pip install -r requirements.txt", "python src/fetch_data.py", "python src/pipeline.py"]:
        r = code.add_run(line + "\n")
        set_font(r, size=9, color=RGBColor(0x35, 0x50, 0x6A))
        r.font.name = "Consolas"
        r._element.get_or_add_rPr().find(qn("w:rFonts")).set(qn("w:ascii"), "Consolas")

    # ---------------- 附图
    shot = ROOT / "docs" / "shots" / "fig-dashboard.png"
    if shot.exists():
        heading(doc, "附", "看板主视图")
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(str(shot), width=Cm(16.2))
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(6)
        r = cap.add_run("KPI 区 + 月度收入与退货率 + 客户分层（可在全周期 / 上半年 / 下半年之间切换）")
        set_font(r, size=8.5, color=LIGHT)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT))
    print(f"已生成 {OUT.relative_to(ROOT)}  ({OUT.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()






