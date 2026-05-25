const state = {
  data: null,
  metric: "revenue",
  staticRecords: null,
};

const staticDataUrl = window.STATIC_SALES_DATA_URL || null;

const palette = {
  blue: "#2f6fed",
  green: "#1d9a6c",
  red: "#d84b55",
  amber: "#e59f28",
  teal: "#159895",
  ink: "#172033",
  muted: "#667085",
  grid: "#d9e2ec",
};

const formatMoney = (value) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);

const formatCompact = (value) =>
  new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);

function pct_change(current, previous) {
  if (!previous || Number.isNaN(previous)) return 0;
  return ((current - previous) / previous) * 100;
}

function trend_label(value) {
  if (value > 2) return "up";
  if (value < -2) return "down";
  return "flat";
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function getCtx(id) {
  const canvas = document.getElementById(id);
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(Number(canvas.getAttribute("height")) * dpr));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { canvas, ctx, width: rect.width, height: Number(canvas.getAttribute("height")) };
}

function clearChart(ctx, width, height) {
  ctx.clearRect(0, 0, width, height);
}

function niceMax(values) {
  const max = Math.max(...values, 1);
  const magnitude = 10 ** Math.floor(Math.log10(max));
  return Math.ceil(max / magnitude) * magnitude;
}

function drawAxes(ctx, width, height, padding) {
  ctx.strokeStyle = palette.grid;
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i <= 4; i += 1) {
    const y = padding.top + ((height - padding.top - padding.bottom) * i) / 4;
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
  }
  ctx.stroke();
}

function drawLineChart(id, labels, values, secondaryValues, metric) {
  const { ctx, width, height } = getCtx(id);
  clearChart(ctx, width, height);
  const padding = { top: 18, right: 18, bottom: 38, left: 54 };
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;
  const max = niceMax([...values, ...(secondaryValues || [])]);
  const min = 0;

  drawAxes(ctx, width, height, padding);

  const points = values.map((value, index) => {
    const x = padding.left + (plotW * index) / Math.max(labels.length - 1, 1);
    const y = padding.top + plotH - ((value - min) / (max - min)) * plotH;
    return { x, y, value };
  });

  if (secondaryValues) {
    const secondary = secondaryValues.map((value, index) => {
      const x = padding.left + (plotW * index) / Math.max(labels.length - 1, 1);
      const y = padding.top + plotH - ((value - min) / (max - min)) * plotH;
      return { x, y };
    });
    ctx.strokeStyle = palette.amber;
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    secondary.forEach((point, index) => {
      if (index === 0) ctx.moveTo(point.x, point.y);
      else ctx.lineTo(point.x, point.y);
    });
    ctx.stroke();
    ctx.setLineDash([]);
  }

  const gradient = ctx.createLinearGradient(0, padding.top, 0, height - padding.bottom);
  gradient.addColorStop(0, "rgba(47,111,237,0.24)");
  gradient.addColorStop(1, "rgba(47,111,237,0.02)");
  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  });
  ctx.lineTo(points[points.length - 1].x, height - padding.bottom);
  ctx.lineTo(points[0].x, height - padding.bottom);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  ctx.strokeStyle = palette.blue;
  ctx.lineWidth = 3;
  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  });
  ctx.stroke();

  points.forEach((point) => {
    ctx.fillStyle = "#ffffff";
    ctx.strokeStyle = palette.blue;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  });

  ctx.fillStyle = palette.muted;
  ctx.font = "11px Inter, system-ui, sans-serif";
  ctx.textAlign = "right";
  for (let i = 0; i <= 4; i += 1) {
    const value = max - (max * i) / 4;
    const y = padding.top + (plotH * i) / 4 + 4;
    ctx.fillText(metric === "revenue" ? formatCompact(value) : Math.round(value).toLocaleString(), padding.left - 10, y);
  }

  ctx.textAlign = "center";
  labels.forEach((label, index) => {
    if (index % Math.ceil(labels.length / 6) !== 0 && index !== labels.length - 1) return;
    const x = padding.left + (plotW * index) / Math.max(labels.length - 1, 1);
    ctx.fillText(label, x, height - 14);
  });
}

function drawBarChart(id, labels, values, options = {}) {
  const { ctx, width, height } = getCtx(id);
  clearChart(ctx, width, height);
  const padding = { top: 16, right: 14, bottom: 34, left: 52 };
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;
  const max = niceMax(values);
  const barGap = 10;
  const barW = Math.max(12, (plotW - barGap * (values.length - 1)) / values.length);
  drawAxes(ctx, width, height, padding);

  values.forEach((value, index) => {
    const x = padding.left + index * (barW + barGap);
    const h = (value / max) * plotH;
    const y = padding.top + plotH - h;
    ctx.fillStyle = options.colors?.[index] || palette.teal;
    roundRect(ctx, x, y, barW, h, 6);
    ctx.fill();
  });

  ctx.fillStyle = palette.muted;
  ctx.font = "11px Inter, system-ui, sans-serif";
  ctx.textAlign = "center";
  labels.forEach((label, index) => {
    const x = padding.left + index * (barW + barGap) + barW / 2;
    const short = label.length > 10 ? `${label.slice(0, 9)}.` : label;
    ctx.fillText(short, x, height - 12);
  });
}

function drawHorizontalBarChart(id, labels, values) {
  const { ctx, width, height } = getCtx(id);
  clearChart(ctx, width, height);
  const padding = { top: 14, right: 16, bottom: 12, left: 86 };
  const plotW = width - padding.left - padding.right;
  const rowH = (height - padding.top - padding.bottom) / values.length;
  const max = niceMax(values);

  values.forEach((value, index) => {
    const y = padding.top + index * rowH + 7;
    const barH = Math.max(10, rowH - 14);
    const w = (value / max) * plotW;
    ctx.fillStyle = "#e8eef5";
    roundRect(ctx, padding.left, y, plotW, barH, 6);
    ctx.fill();
    ctx.fillStyle = index === 0 ? palette.blue : palette.teal;
    roundRect(ctx, padding.left, y, w, barH, 6);
    ctx.fill();
    ctx.fillStyle = palette.ink;
    ctx.font = "12px Inter, system-ui, sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(labels[index], padding.left - 10, y + barH - 2);
    ctx.textAlign = "left";
    ctx.fillStyle = palette.muted;
    ctx.fillText(formatCompact(value), padding.left + w + 7, y + barH - 2);
  });
}

function drawMomentumChart(id, labels, values) {
  const { ctx, width, height } = getCtx(id);
  clearChart(ctx, width, height);
  const padding = { top: 18, right: 14, bottom: 34, left: 42 };
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;
  const absMax = Math.max(...values.map((v) => Math.abs(v)), 1);
  const zeroY = padding.top + plotH / 2;
  const barGap = 8;
  const barW = Math.max(8, (plotW - barGap * (values.length - 1)) / values.length);

  ctx.strokeStyle = palette.grid;
  ctx.beginPath();
  ctx.moveTo(padding.left, zeroY);
  ctx.lineTo(width - padding.right, zeroY);
  ctx.stroke();

  values.forEach((value, index) => {
    const x = padding.left + index * (barW + barGap);
    const h = (Math.abs(value) / absMax) * (plotH / 2);
    const y = value >= 0 ? zeroY - h : zeroY;
    ctx.fillStyle = value >= 0 ? palette.green : palette.red;
    roundRect(ctx, x, y, barW, h, 5);
    ctx.fill();
  });

  ctx.fillStyle = palette.muted;
  ctx.font = "11px Inter, system-ui, sans-serif";
  ctx.textAlign = "center";
  labels.forEach((label, index) => {
    if (index % Math.ceil(labels.length / 5) !== 0 && index !== labels.length - 1) return;
    const x = padding.left + index * (barW + barGap) + barW / 2;
    ctx.fillText(label, x, height - 12);
  });
}

function roundRect(ctx, x, y, width, height, radius) {
  const r = Math.min(radius, Math.abs(height) / 2, width / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r);
  ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r);
  ctx.closePath();
}

async function fetchDashboard() {
  const filters = {
    category: document.getElementById("categoryFilter").value,
    city: document.getElementById("cityFilter").value,
    product: document.getElementById("productFilter").value,
  };

  if (staticDataUrl) {
    if (!state.staticRecords) {
      const staticResponse = await fetch(staticDataUrl);
      state.staticRecords = await staticResponse.json();
    }
    state.data = buildStaticDashboard(state.staticRecords, filters);
  } else {
    const params = new URLSearchParams(filters);
    const response = await fetch(`/api/dashboard?${params.toString()}`);
    state.data = await response.json();
  }
  render();
}

function buildStaticDashboard(records, filters) {
  const rows = records
    .map((row) => ({
      ...row,
      Order_Date: new Date(row.Order_Date),
      Price_USD: Number(row.Price_USD),
      Quantity_Sold: Number(row.Quantity_Sold),
      Total_Sales_USD: Number(row.Total_Sales_USD),
    }))
    .filter((row) => {
      const categoryMatch = !filters.category || filters.category === "all" || row.Category === filters.category;
      const cityMatch = !filters.city || filters.city === "all" || row.Customer_City === filters.city;
      const productMatch = !filters.product || filters.product === "all" || row.Product_Name === filters.product;
      return categoryMatch && cityMatch && productMatch;
    });

  if (!rows.length) return { empty: true };

  const monthlyRows = groupBy(rows, (row) => monthKey(row.Order_Date))
    .map(([month, items]) => {
      const revenue = sum(items, "Total_Sales_USD");
      const units = sum(items, "Quantity_Sold");
      const orders = items.length;
      return {
        month,
        date: new Date(`${month}-01T00:00:00`),
        label: monthLabel(month),
        revenue,
        units,
        orders,
        avg_ticket: orders ? revenue / orders : 0,
      };
    })
    .sort((a, b) => a.date - b.date);

  monthlyRows.forEach((row, index) => {
    const previous = monthlyRows[index - 1];
    row.revenue_mom_pct = previous ? pct_change(row.revenue, previous.revenue) : 0;
    const windowRows = monthlyRows.slice(Math.max(0, index - 2), index + 1);
    row.moving_avg_3m = windowRows.reduce((total, item) => total + item.revenue, 0) / windowRows.length;
  });

  const currentMonth = monthlyRows[monthlyRows.length - 1];
  const previousMonth = monthlyRows[monthlyRows.length - 2] || currentMonth;
  const revenue = sum(rows, "Total_Sales_USD");
  const units = sum(rows, "Quantity_Sold");
  const orders = rows.length;
  const avgTicket = orders ? revenue / orders : 0;
  const avgPrice = units ? revenue / units : 0;

  const products = dimensionStatic(rows, "Product_Name", 8);
  const categories = dimensionStatic(rows, "Category");
  const cities = dimensionStatic(rows, "Customer_City");
  const categoryCity = groupBy(rows, (row) => `${row.Category}|||${row.Customer_City}`).map(([key, items]) => {
    const [category, city] = key.split("|||");
    return { Category: category, Customer_City: city, revenue: sum(items, "Total_Sales_USD") };
  });

  const dates = rows.map((row) => row.Order_Date).sort((a, b) => a - b);

  return {
    empty: false,
    period: {
      start: formatDate(dates[0]),
      end: formatDate(dates[dates.length - 1]),
      orders,
    },
    kpis: [
      { label: "Receita total", value: formatMoney(revenue), delta: pct_change(currentMonth.revenue, previousMonth.revenue), trend: trend_label(pct_change(currentMonth.revenue, previousMonth.revenue)) },
      { label: "Unidades vendidas", value: formatCompact(units), delta: pct_change(currentMonth.units, previousMonth.units), trend: trend_label(pct_change(currentMonth.units, previousMonth.units)) },
      { label: "Pedidos", value: formatCompact(orders), delta: pct_change(currentMonth.orders, previousMonth.orders), trend: trend_label(pct_change(currentMonth.orders, previousMonth.orders)) },
      { label: "Ticket medio", value: formatMoney(avgTicket), delta: pct_change(currentMonth.avg_ticket, previousMonth.avg_ticket), trend: trend_label(pct_change(currentMonth.avg_ticket, previousMonth.avg_ticket)) },
      { label: "Preco medio realizado", value: formatMoney(avgPrice), delta: 0, trend: "flat" },
    ],
    leaders: {
      product: products[0].Product_Name,
      category: categories[0].Category,
      city: cities[0].Customer_City,
    },
    monthly: {
      labels: monthlyRows.map((row) => row.label),
      revenue: monthlyRows.map((row) => Number(row.revenue.toFixed(2))),
      units: monthlyRows.map((row) => Math.round(row.units)),
      orders: monthlyRows.map((row) => row.orders),
      moving_avg: monthlyRows.map((row) => Number(row.moving_avg_3m.toFixed(2))),
      mom: monthlyRows.map((row) => Number(row.revenue_mom_pct.toFixed(2))),
    },
    categories: {
      labels: categories.map((row) => row.Category),
      revenue: categories.map((row) => Number(row.revenue.toFixed(2))),
      units: categories.map((row) => Math.round(row.units)),
      share: categories.map((row) => Number(row.share_pct.toFixed(2))),
    },
    cities: {
      labels: cities.map((row) => row.Customer_City),
      revenue: cities.map((row) => Number(row.revenue.toFixed(2))),
      ticket: cities.map((row) => Number(row.avg_ticket.toFixed(2))),
    },
    top_products: products.map((row) => ({
      Product_Name: row.Product_Name,
      revenue_fmt: formatMoney(row.revenue),
      units_fmt: formatCompact(row.units),
      avg_ticket_fmt: formatMoney(row.avg_ticket),
      share_fmt: `${row.share_pct.toFixed(1)}%`,
      share_pct: row.share_pct,
    })),
    category_city: categoryCity,
  };
}

function groupBy(rows, keyFn) {
  const grouped = new Map();
  rows.forEach((row) => {
    const key = keyFn(row);
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(row);
  });
  return Array.from(grouped.entries());
}

function dimensionStatic(rows, dimension, limit = null) {
  const grouped = groupBy(rows, (row) => row[dimension]).map(([label, items]) => {
    const revenue = sum(items, "Total_Sales_USD");
    const units = sum(items, "Quantity_Sold");
    const orders = items.length;
    return {
      [dimension]: label,
      revenue,
      units,
      orders,
      avg_price: average(items, "Price_USD"),
      avg_ticket: orders ? revenue / orders : 0,
    };
  });
  grouped.sort((a, b) => b.revenue - a.revenue);
  const total = grouped.reduce((acc, row) => acc + row.revenue, 0);
  grouped.forEach((row) => {
    row.share_pct = total ? (row.revenue / total) * 100 : 0;
  });
  return limit ? grouped.slice(0, limit) : grouped;
}

function sum(rows, field) {
  return rows.reduce((total, row) => total + Number(row[field] || 0), 0);
}

function average(rows, field) {
  return rows.length ? sum(rows, field) / rows.length : 0;
}

function monthKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(month) {
  const [year, monthNumber] = month.split("-").map(Number);
  return new Date(year, monthNumber - 1, 1).toLocaleDateString("en-US", { month: "short", year: "numeric" }).replace(" ", "/");
}

function formatDate(date) {
  return date.toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" });
}

function renderKpis(kpis) {
  const grid = document.getElementById("kpiGrid");
  grid.innerHTML = kpis
    .map((kpi) => {
      const sign = kpi.delta > 0 ? "+" : "";
      const icon = kpi.trend === "up" ? "UP" : kpi.trend === "down" ? "DOWN" : "FLAT";
      return `
        <article class="kpi-card">
          <span>${kpi.label}</span>
          <strong>${kpi.value}</strong>
          <div class="delta ${kpi.trend}">${icon} ${sign}${kpi.delta.toFixed(1)}% MoM</div>
        </article>
      `;
    })
    .join("");
}

function renderProductTable(rows) {
  const tbody = document.getElementById("productTable");
  tbody.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td>${row.Product_Name}</td>
          <td>${row.revenue_fmt}</td>
          <td>${row.units_fmt}</td>
          <td>${row.avg_ticket_fmt}</td>
          <td>
            <div class="share-bar">
              <span>${row.share_fmt}</span>
              <div class="share-track"><div class="share-fill" style="width:${Math.min(row.share_pct, 100)}%"></div></div>
            </div>
          </td>
        </tr>
      `
    )
    .join("");
}

function renderHeatmap(rows) {
  const heatmap = document.getElementById("heatmap");
  const sorted = [...rows].sort((a, b) => b.revenue - a.revenue).slice(0, 10);
  const max = Math.max(...sorted.map((row) => row.revenue), 1);
  heatmap.innerHTML = sorted
    .map((row) => {
      const intensity = 0.35 + (row.revenue / max) * 0.65;
      return `
        <div class="heat-cell" style="background: rgba(47, 111, 237, ${intensity.toFixed(2)})">
          <span>${row.Category} - ${row.Customer_City}</span>
          <strong>${formatMoney(row.revenue)}</strong>
        </div>
      `;
    })
    .join("");
}

function renderCharts() {
  const data = state.data;
  const metric = state.metric;
  const metricValues = data.monthly[metric];
  drawLineChart("trendChart", data.monthly.labels, metricValues, metric === "revenue" ? data.monthly.moving_avg : null, metric);
  drawMomentumChart("momentumChart", data.monthly.labels, data.monthly.mom);
  drawBarChart("categoryChart", data.categories.labels, data.categories.revenue, {
    colors: data.categories.labels.map((_, index) => [palette.blue, palette.teal, palette.green, palette.amber, palette.red][index % 5]),
  });
  drawHorizontalBarChart("cityChart", data.cities.labels, data.cities.revenue);
}

function render() {
  if (!state.data || state.data.empty) {
    document.getElementById("emptyState").hidden = false;
    document.getElementById("periodLabel").textContent = "Sem dados para os filtros";
    document.getElementById("kpiGrid").innerHTML = "";
    document.getElementById("productTable").innerHTML = "";
    document.getElementById("heatmap").innerHTML = "";
    document.getElementById("leaderProduct").textContent = "-";
    document.getElementById("leaderCategory").textContent = "-";
    document.getElementById("leaderCity").textContent = "-";
    ["trendChart", "momentumChart", "categoryChart", "cityChart"].forEach((id) => {
      const { ctx, width, height } = getCtx(id);
      clearChart(ctx, width, height);
    });
    return;
  }

  document.getElementById("emptyState").hidden = true;
  document.getElementById("periodLabel").textContent = `${state.data.period.start} - ${state.data.period.end}`;
  document.getElementById("leaderProduct").textContent = state.data.leaders.product;
  document.getElementById("leaderCategory").textContent = state.data.leaders.category;
  document.getElementById("leaderCity").textContent = state.data.leaders.city;
  renderKpis(state.data.kpis);
  renderProductTable(state.data.top_products);
  renderHeatmap(state.data.category_city);
  renderCharts();
}

function bindEvents() {
  ["categoryFilter", "cityFilter", "productFilter"].forEach((id) => {
    document.getElementById(id).addEventListener("change", fetchDashboard);
  });
  document.getElementById("resetFilters").addEventListener("click", () => {
    document.getElementById("categoryFilter").value = "all";
    document.getElementById("cityFilter").value = "all";
    document.getElementById("productFilter").value = "all";
    fetchDashboard();
  });
  document.querySelectorAll("[data-timeseries]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-timeseries]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state.metric = button.dataset.timeseries;
      renderCharts();
    });
  });
  window.addEventListener("resize", () => {
    if (state.data) renderCharts();
  });
}

bindEvents();
fetchDashboard();
