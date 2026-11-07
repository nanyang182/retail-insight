/* ============================================================
   Retail Insight · 看板渲染
   零依赖：原生 SVG 绘制，不引任何图表库，双击 index.html 即可打开
   ============================================================ */
(function () {
  "use strict";

  const DATA = window.__RETAIL_DATA__;
  if (!DATA) {
    document.body.innerHTML =
      '<p style="padding:40px;font-family:sans-serif">data.js 未加载，请先运行 python src/pipeline.py</p>';
    return;
  }

  const NS = "http://www.w3.org/2000/svg";
  const C = {
    blue: "#1E63D8",
    cyan: "#27C7DB",
    violet: "#8B5CF6",
    slate: "#94A3B8",
    teal: "#5BA7C9",
    red: "#E5484D",
    ink: "#0A1B2E",
    muted: "#8FA3B8",
    grid: "#EDF3FA",
    axis: "#CBD9E7",
    label: "#5B7285",
  };

  const SEG_COLOR = {
    "核心客户": C.blue,
    "沉睡高价值": C.violet,
    "低价值流失": C.slate,
    "高价值新客": C.cyan,
    "新客 / 低频": C.teal,
  };

  /* ------------------------------------------------------------ 工具 */
  function el(tag, attrs, parent) {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  function text(parent, x, y, str, attrs) {
    const t = el("text", Object.assign({ x: x, y: y }, attrs || {}), parent);
    t.textContent = str;
    return t;
  }

  const int = (v) => Math.round(v).toLocaleString("en-US");

  function money(v) {
    const a = Math.abs(v);
    if (a >= 1e6) return "£" + (v / 1e6).toFixed(2) + "M";
    if (a >= 1e3) return "£" + (v / 1e3).toFixed(a >= 1e5 ? 0 : 1) + "K";
    return "£" + v.toFixed(0);
  }

  function axisMoney(v) {
    if (v === 0) return "0";
    if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(v % 1e6 === 0 ? 0 : 1) + "M";
    if (Math.abs(v) >= 1e3) return Math.round(v / 1e3) + "K";
    return String(Math.round(v));
  }

  const measureCtx = document.createElement("canvas").getContext("2d");
  function clip(str, maxPx, font) {
    measureCtx.font = font || "11px 'Segoe UI', sans-serif";
    if (measureCtx.measureText(str).width <= maxPx) return str;
    let s = str;
    while (s.length > 1 && measureCtx.measureText(s + "…").width > maxPx) s = s.slice(0, -1);
    return s + "…";
  }

  // 让坐标刻度落在 1/1.5/2/2.5/3/4/5/6/8 × 10^n 上，避免出现 842K 这种数
  function niceStep(raw) {
    const exp = Math.floor(Math.log10(raw));
    const base = Math.pow(10, exp);
    const f = raw / base;
    const set = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10];
    const n = set.find((s) => s >= f - 1e-9) || 10;
    return n * base;
  }

  /* ------------------------------------------------------------ 提示框 */
  const tip = document.getElementById("tip");
  function showTip(ev, html) {
    tip.innerHTML = html;
    const x = Math.min(Math.max(ev.clientX, 150), window.innerWidth - 150);
    tip.style.left = x + "px";
    tip.style.top = ev.clientY + "px";
    tip.style.opacity = "1";
  }
  function hideTip() {
    tip.style.opacity = "0";
  }

  /* ------------------------------------------------------------ 折线 + 柱 */
  function renderTrend(host, period) {
    host.innerHTML = "";
    const W = host.clientWidth || 820;
    const H = host.clientHeight || 296;
    const m = { l: 52, r: 46, t: 20, b: 42 };
    const iw = W - m.l - m.r;
    const ih = H - m.t - m.b;
    const data = period.monthly;
    const n = data.length;

    const peak = Math.max.apply(null, data.map((d) => d.revenue));
    const step = niceStep((peak * 1.06) / 4);
    const maxRev = step * 4;
    const rates = data.filter((d) => !d.partial).map((d) => d.return_rate);
    const maxRate = Math.max(8, Math.ceil((Math.max.apply(null, rates) * 1.5) / 4) * 4);

    const svg = el("svg", { width: W, height: H, role: "img" }, host);
    const band = iw / n;
    const bw = Math.min(44, band * 0.5);
    const xc = (i) => m.l + band * (i + 0.5);
    const yRev = (v) => m.t + ih - (v / maxRev) * ih;
    const yRate = (v) => m.t + ih - (v / maxRate) * ih;

    // 网格 + 左轴
    for (let i = 0; i <= 4; i++) {
      const y = m.t + (ih * i) / 4;
      el("line", { x1: m.l, y1: y, x2: m.l + iw, y2: y, stroke: C.grid, "stroke-width": 1 }, svg);
      text(svg, m.l - 9, y + 4, axisMoney(maxRev * (1 - i / 4)), {
        "text-anchor": "end", "font-size": 10.5, fill: C.muted,
      });
    }

    // 柱：收入
    data.forEach((d, i) => {
      const y = yRev(d.revenue);
      const h = Math.max(1, m.t + ih - y);
      const rect = el("rect", {
        x: xc(i) - bw / 2,
        y: y,
        width: bw,
        height: h,
        rx: 3,
        fill: d.partial ? "#C3D5E8" : C.blue,
        opacity: d.partial ? 0.85 : 1,
      }, svg);

      // 命中区（整列）
      const hit = el("rect", {
        x: m.l + band * i, y: m.t, width: band, height: ih, fill: "transparent",
      }, svg);
      hit.style.cursor = "default";
      hit.addEventListener("mousemove", (ev) => {
        showTip(
          ev,
          `<b>${d.month}</b>${d.partial ? " <span class='t-dim'>（截至 9 日）</span>" : ""}<br>` +
            `<span class='t-dim'>销售额</span> ${money(d.revenue)}<br>` +
            `<span class='t-dim'>退货</span> ${money(d.returns)}<br>` +
            `<span class='t-dim'>退货率</span> ${d.return_rate.toFixed(2)}%`
        );
        rect.setAttribute("opacity", "0.82");
      });
      hit.addEventListener("mouseleave", () => {
        hideTip();
        rect.setAttribute("opacity", d.partial ? "0.85" : "1");
      });
    });

    // 折线：退货率
    const linePts = [];
    data.forEach((d, i) => {
      if (d.partial) return;
      linePts.push([xc(i), yRate(d.return_rate)]);
    });
    if (linePts.length > 1) {
      el("polyline", {
        points: linePts.map((p) => p[0] + "," + p[1]).join(" "),
        fill: "none",
        stroke: C.red,
        "stroke-width": 1.8,
        "stroke-linejoin": "round",
        opacity: 0.85,
      }, svg);
      linePts.forEach((p) => {
        el("circle", { cx: p[0], cy: p[1], r: 3, fill: "#fff", stroke: C.red, "stroke-width": 1.8 }, svg);
      });
    }

    // 右轴（退货率）
    for (let i = 0; i <= 2; i++) {
      const y = m.t + (ih * i) / 2;
      text(svg, m.l + iw + 9, y + 4, (maxRate * (1 - i / 2)).toFixed(0) + "%", {
        "font-size": 10.5, fill: C.red, opacity: 0.75,
      });
    }

    // x 轴标签 + 年份分隔（避免 12 月出现两次分不清）
    data.forEach((d, i) => {
      text(svg, xc(i), m.t + ih + 19, d.label, {
        "text-anchor": "middle", "font-size": 10.5, fill: d.partial ? "#B9C9D8" : C.muted,
      });
      const isYearStart = i === 0 || d.month.slice(5) === "01";
      if (isYearStart) {
        text(svg, xc(i), m.t + ih + 33, d.month.slice(0, 4), {
          "text-anchor": "middle", "font-size": 9.5, fill: "#A6B8C8", "letter-spacing": "0.04em",
        });
        if (i > 0) {
          el("line", {
            x1: m.l + band * i, y1: m.t, x2: m.l + band * i, y2: m.t + ih,
            stroke: "#E9F0F8", "stroke-width": 1, "stroke-dasharray": "3 5",
          }, svg);
        }
      }
    });
  }

  /* ------------------------------------------------------------ 环形图 */
  function renderDonut(host, period, legendHost) {
    host.innerHTML = "";
    const W = host.clientWidth || 360;
    const H = host.clientHeight || 244;
    const cx = W / 2;
    const cy = H / 2 - 4;
    const r = Math.min(W, H) / 2 - 30;
    const sw = 21;
    const circ = 2 * Math.PI * r;

    const svg = el("svg", { width: W, height: H }, host);
    const g = el("g", { transform: `rotate(-90 ${cx} ${cy})` }, svg);

    let acc = 0;
    period.rfm.forEach((s) => {
      const frac = s.cust_share / 100;
      const len = Math.max(0, circ * frac - 2.5);
      const arc = el("circle", {
        cx: cx, cy: cy, r: r,
        fill: "none",
        stroke: SEG_COLOR[s.segment] || C.slate,
        "stroke-width": sw,
        "stroke-dasharray": `${len} ${circ - len}`,
        "stroke-dashoffset": -acc,
        "stroke-linecap": "butt",
      }, g);
      arc.style.transition = "opacity .15s";
      arc.addEventListener("mousemove", (ev) => {
        showTip(
          ev,
          `<b>${s.segment}</b><br>` +
            `<span class='t-dim'>客户</span> ${int(s.customers)} 人 · ${s.cust_share.toFixed(1)}%<br>` +
            `<span class='t-dim'>贡献收入</span> ${s.share.toFixed(1)}%`
        );
        arc.setAttribute("opacity", "0.75");
      });
      arc.addEventListener("mouseleave", () => {
        hideTip();
        arc.setAttribute("opacity", "1");
      });
      acc += circ * frac;
    });

    const total = period.rfm.reduce((a, b) => a + b.customers, 0);
    text(svg, cx, cy - 2, int(total), {
      "text-anchor": "middle", "font-size": 22, "font-weight": 700, fill: C.ink,
    });
    text(svg, cx, cy + 16, "位可识别客户", {
      "text-anchor": "middle", "font-size": 10.5, fill: C.muted,
    });

    legendHost.innerHTML =
      `<li class="legend-head"><i></i><span>分层</span><span>客户数</span><span>收入占比</span></li>` +
      period.rfm
        .map(
          (s) =>
            `<li><i style="background:${SEG_COLOR[s.segment] || C.slate}"></i>` +
            `<span class="n">${s.segment}</span>` +
            `<span class="c">${int(s.customers)} 人</span>` +
            `<span class="p">${s.share.toFixed(1)}%</span></li>`
        )
        .join("");
  }

  /* ------------------------------------------------------------ 洛伦兹曲线 */
  function renderLorenz(host, period) {
    host.innerHTML = "";
    const W = host.clientWidth || 600;
    const H = host.clientHeight || 244;
    const m = { l: 44, r: 18, t: 18, b: 34 };
    const iw = W - m.l - m.r;
    const ih = H - m.t - m.b;
    const pts = period.lorenz;

    const svg = el("svg", { width: W, height: H }, host);
    const X = (v) => m.l + (v / 100) * iw;
    const Y = (v) => m.t + ih - (v / 100) * ih;

    for (let i = 0; i <= 4; i++) {
      const y = m.t + (ih * i) / 4;
      const x = m.l + (iw * i) / 4;
      el("line", { x1: m.l, y1: y, x2: m.l + iw, y2: y, stroke: C.grid }, svg);
      text(svg, m.l - 8, y + 4, 100 - i * 25 + "%", { "text-anchor": "end", "font-size": 10.5, fill: C.muted }, svg);
      text(svg, x, m.t + ih + 18, i * 25 + "%", { "text-anchor": "middle", "font-size": 10.5, fill: C.muted }, svg);
    }

    // 绝对平均线
    el("line", {
      x1: X(0), y1: Y(0), x2: X(100), y2: Y(100),
      stroke: C.axis, "stroke-width": 1.2, "stroke-dasharray": "5 4",
    }, svg);

    const d = pts.map((p, i) => (i ? "L" : "M") + X(p.x) + "," + Y(p.y)).join(" ");
    el("path", {
      d: d + ` L${X(100)},${Y(0)} L${X(0)},${Y(0)} Z`,
      fill: "url(#lz)", opacity: 0.9,
    }, svg);

    const defs = el("defs", {}, svg);
    const grad = el("linearGradient", { id: "lz", x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
    el("stop", { offset: "0%", "stop-color": C.blue, "stop-opacity": 0.26 }, grad);
    el("stop", { offset: "100%", "stop-color": C.blue, "stop-opacity": 0.02 }, grad);

    el("path", { d: d, fill: "none", stroke: C.blue, "stroke-width": 2.2, "stroke-linejoin": "round" }, svg);

    // 20% 标注
    const mark = pts.find((p) => p.x === 20);
    if (mark) {
      el("line", {
        x1: X(20), y1: Y(mark.y), x2: X(20), y2: Y(0),
        stroke: C.blue, "stroke-width": 1, "stroke-dasharray": "4 4", opacity: 0.45,
      }, svg);
      el("circle", { cx: X(20), cy: Y(mark.y), r: 4.5, fill: "#fff", stroke: C.blue, "stroke-width": 2 }, svg);
      text(svg, X(20) + 9, Y(mark.y) - 13, `前 20% 客户 → ${mark.y.toFixed(0)}% 收入`, {
        "font-size": 11, "font-weight": 700, fill: C.blue,
        stroke: "#FFFFFF", "stroke-width": 3.5, "paint-order": "stroke",
      }, svg);
    }

    text(svg, m.l + iw, m.t + ih + 18, "客户累计占比", {
      "text-anchor": "end", "font-size": 10, fill: "#A6B8C8",
    }, svg);
  }

  /* ------------------------------------------------------------ 竖柱 */
  function renderBars(host, items, opts) {
    host.innerHTML = "";
    const W = host.clientWidth || 600;
    const H = host.clientHeight || 244;
    const m = { l: 12, r: 12, t: 26, b: 34 };
    const iw = W - m.l - m.r;
    const ih = H - m.t - m.b;
    const max = Math.max.apply(null, items.map((d) => d.value)) * 1.1;
    const n = items.length;
    const band = iw / n;
    const bw = Math.min(46, band * 0.5);

    const svg = el("svg", { width: W, height: H }, host);

    for (let i = 0; i <= 3; i++) {
      const y = m.t + (ih * i) / 3;
      el("line", { x1: m.l, y1: y, x2: m.l + iw, y2: y, stroke: C.grid }, svg);
    }

    items.forEach((d, i) => {
      const x = m.l + band * (i + 0.5);
      const h = Math.max(2, (d.value / max) * ih);
      const y = m.t + ih - h;
      const rect = el("rect", {
        x: x - bw / 2, y: y, width: bw, height: h, rx: 4,
        fill: opts.color || C.blue, opacity: 0.92,
      }, svg);

      text(svg, x, y - 8, d.label, {
        "text-anchor": "middle", "font-size": 11.5, "font-weight": 700, fill: C.ink,
      }, svg);
      text(svg, x, m.t + ih + 19, d.band, {
        "text-anchor": "middle", "font-size": 10.5, fill: C.muted,
      }, svg);

      rect.addEventListener("mousemove", (ev) => showTip(ev, d.tip));
      rect.addEventListener("mouseleave", hideTip);
    });
  }

  /* ------------------------------------------------------------ 横条 */
  function renderHBars(host, items, opts) {
    host.innerHTML = "";
    const W = host.clientWidth || 600;
    const H = host.clientHeight || 296;
    const labelW = Math.min(178, W * 0.36);
    const valueW = 62;
    const m = { l: 2, r: 2, t: 6, b: 6 };
    const barX = labelW + 12;
    const barW = W - barX - valueW - m.r;
    const n = items.length;
    const rowH = (H - m.t - m.b) / n;
    const bh = Math.min(13, rowH * 0.46);
    const max = Math.max.apply(null, items.map((d) => d.value));

    const svg = el("svg", { width: W, height: H }, host);

    items.forEach((d, i) => {
      const y = m.t + rowH * i + rowH / 2;
      const len = Math.max(3, (d.value / max) * barW);

      const name = text(svg, m.l, y + 3.5, clip(d.name, labelW - 6), {
        "font-size": 11, fill: C.label,
      });
      name.setAttribute("title", d.name);

      el("rect", {
        x: barX, y: y - bh / 2, width: barW, height: bh, rx: bh / 2, fill: "#F1F6FC",
      }, svg);

      const bar = el("rect", {
        x: barX, y: y - bh / 2, width: len, height: bh, rx: bh / 2,
        fill: opts.color || C.blue, opacity: 0.9,
      }, svg);

      text(svg, barX + barW + 8, y + 3.5, d.label, {
        "font-size": 11, "font-weight": 700, fill: C.ink, "font-variant-numeric": "tabular-nums",
      }, svg);

      bar.addEventListener("mousemove", (ev) => showTip(ev, d.tip));
      bar.addEventListener("mouseleave", hideTip);
    });
  }

  /* ------------------------------------------------------------ KPI */
  const KPIS = [
    {
      k: "净收入",
      v: (p) => money(p.kpi.net),
      s: (p) => `已扣除退货 ${money(p.kpi.returns)}`,
    },
    {
      k: "订单数",
      v: (p) => int(p.kpi.orders),
      s: (p) => `单笔均值 ${money(p.kpi.aov)}`,
    },
    {
      k: "可识别客户",
      v: (p) => int(p.kpi.customers),
      s: (p) => `${p.kpi.missing_id_share.toFixed(1)}% 的销售行无客户 ID`,
    },
    {
      k: "客单价",
      v: (p) => money(p.kpi.aov),
      s: () => "单笔订单平均金额",
    },
    {
      k: "退货率",
      v: (p) => p.kpi.return_rate.toFixed(1) + "<small>%</small>",
      s: (p) => `退货金额 ${money(p.kpi.returns)}`,
    },
    {
      k: "复购率",
      v: (p) => p.kpi.repeat_rate.toFixed(1) + "<small>%</small>",
      s: () => "购买 ≥2 次的客户占比",
    },
  ];

  function renderKPIs(period) {
    document.getElementById("kpis").innerHTML = KPIS.map(
      (k) =>
        `<div class="kpi"><div class="k">${k.k}</div>` +
        `<div class="v">${k.v(period)}</div><div class="s">${k.s(period)}</div></div>`
    ).join("");
  }

  /* ------------------------------------------------------------ 建议 */
  function renderInsights() {
    document.getElementById("insights").innerHTML = DATA.insights
      .map(
        (it) =>
          `<article class="insight"><div class="tag">${it.tag}</div>` +
          `<div class="metric">${it.metric}</div>` +
          `<div class="mlabel">${it.metric_label}</div>` +
          `<h3>${it.title}</h3><p>${it.body}</p></article>`
      )
      .join("");
  }

  /* ------------------------------------------------------------ 页脚口径 */
  function renderNotes() {
    const n = DATA.notes;
    const rows = [
      ["数据源", `${DATA.meta.source}（${DATA.meta.license}）`],
      ["覆盖区间", `${DATA.meta.range}，共 ${int(DATA.meta.rows_raw)} 行原始记录`],
      ["金额口径", n.unit],
      ["清洗规则", n.clean],
      ["退货口径", n.return],
      ["RFM 口径", n.rfm + "；" + n.segment],
      ["已知偏差", n.anomaly],
    ];
    document.getElementById("notes").innerHTML = rows
      .map((r) => `<dt>${r[0]}</dt><dd>${r[1]}</dd>`)
      .join("");
  }

  /* ------------------------------------------------------------ 周期切换 */
  function buildSwitch(onChange) {
    const host = document.getElementById("period-switch");
    host.innerHTML = DATA.periods
      .map(
        (p) =>
          `<button role="tab" data-key="${p.key}" class="${p.key === current ? "on" : ""}">${p.label}</button>`
      )
      .join("");
    host.querySelectorAll("button").forEach((b) => {
      b.addEventListener("click", () => {
        host.querySelectorAll("button").forEach((x) => x.classList.remove("on"));
        b.classList.add("on");
        onChange(b.dataset.key);
      });
    });
  }

  /* ------------------------------------------------------------ 主流程 */
  let current = DATA.periods[0].key;
  const initial = (location.hash || "").replace("#", "");
  if (DATA.periods.some((p) => p.key === initial)) current = initial;

  function period() {
    return DATA.periods.find((p) => p.key === current) || DATA.periods[0];
  }

  function renderCharts() {
    const p = period();
    renderTrend(document.getElementById("chart-trend"), p);
    renderDonut(document.getElementById("chart-rfm"), p, document.getElementById("legend-rfm"));
    renderLorenz(document.getElementById("chart-lorenz"), p);

    renderBars(
      document.getElementById("chart-price"),
      p.price.map((d) => ({
        band: d.band,
        value: d.orders,
        label: d.share.toFixed(1) + "%",
        tip: `<b>${d.band}</b><br><span class='t-dim'>订单</span> ${int(d.orders)} 笔 · 占 ${d.share.toFixed(1)}%`,
      })),
      { color: C.cyan }
    );

    renderHBars(
      document.getElementById("chart-products"),
      p.products.map((d) => ({
        name: d.name,
        value: d.revenue,
        label: money(d.revenue),
        tip:
          `<b>${d.name}</b><br><span class='t-dim'>销售额</span> ${money(d.revenue)}<br>` +
          `<span class='t-dim'>销量</span> ${int(d.qty)} 件 · SKU ${d.code}`,
      })),
      { color: C.blue }
    );

    renderHBars(
      document.getElementById("chart-countries"),
      p.countries.map((d) => ({
        name: d.name,
        value: d.revenue,
        label: d.share.toFixed(1) + "%",
        tip: `<b>${d.name}</b><br><span class='t-dim'>销售额</span> ${money(d.revenue)} · 占 ${d.share.toFixed(1)}%`,
      })),
      { color: C.violet }
    );

    // 部分月份提示
    const partial = p.monthly.filter((d) => d.partial);
    document.getElementById("trend-note").textContent = partial.length
      ? `浅色柱为数据截止月（${partial[0].month} 仅含 1–9 日），退货率折线跳过该月，避免把不完整月当趋势。`
      : "";
  }

  function renderAll() {
    renderCharts();
    renderKPIs(period());
  }

  /* ------------------------------------------------------------ 初始化 */
  document.getElementById("meta-source").textContent = DATA.meta.source;
  document.getElementById("meta-range").textContent = DATA.meta.range;
  document.getElementById("meta-date").textContent = DATA.meta.generated;

  document.getElementById("hero-facts").innerHTML =
    `<b>${int(DATA.meta.rows_raw)}</b> 行原始交易 · ` +
    `<b>${int(DATA.periods[0].kpi.orders)}</b> 笔有效订单 · ` +
    `<b>${int(DATA.periods[0].kpi.customers)}</b> 位可识别客户 · ` +
    `<b>${DATA.periods[0].monthly.length}</b> 个月`;

  renderInsights();
  renderNotes();
  buildSwitch((key) => {
    current = key;
    try {
      history.replaceState(null, "", "#" + key);
    } catch (e) {
      /* file:// 下可能不允许，忽略即可 */
    }
    renderAll();
  });
  renderAll();

  let t = null;
  window.addEventListener("resize", () => {
    clearTimeout(t);
    t = setTimeout(renderCharts, 160);
  });
})();
