(() => {
  const body = document.body;
  const menuButton = document.getElementById("menuButton");
  const scrim = document.getElementById("sidebarScrim");
  const closeMenu = () => body.classList.remove("nav-open");
  menuButton?.addEventListener("click", () => body.classList.toggle("nav-open"));
  scrim?.addEventListener("click", closeMenu);

  document.querySelectorAll("[data-table-filter]").forEach((input) => {
    const table = document.getElementById(input.dataset.tableFilter);
    input.addEventListener("input", () => {
      const query = input.value.trim().toLowerCase();
      table?.querySelectorAll("tbody tr").forEach((row) => {
        row.hidden = !row.textContent.toLowerCase().includes(query);
      });
    });
  });

  const canvas = document.getElementById("safetyChart");
  if (!canvas) return;
  const approved = Number(canvas.dataset.approved || 1);
  const blocked = Number(canvas.dataset.blocked || 1);
  const safeSeries = [48, 56, 53, 68, 64, 76, 82].map((v) => v + Math.min(approved, 12));
  const riskSeries = [27, 24, 31, 22, 25, 18, 15].map((v) => Math.max(7, v + blocked));
  const labels = ["周一", "周二", "周三", "周四", "周五", "周六", "今天"];

  function drawChart() {
    const rect = canvas.getBoundingClientRect();
    const scale = window.devicePixelRatio || 1;
    canvas.width = rect.width * scale;
    canvas.height = rect.height * scale;
    const ctx = canvas.getContext("2d");
    ctx.scale(scale, scale);
    const width = rect.width;
    const height = rect.height;
    const pad = { top: 12, right: 10, bottom: 25, left: 7 };
    const chartW = width - pad.left - pad.right;
    const chartH = height - pad.top - pad.bottom;
    ctx.font = '9px "Segoe UI", sans-serif';
    ctx.textAlign = "center";
    labels.forEach((label, index) => {
      const x = pad.left + (chartW * index) / (labels.length - 1);
      ctx.strokeStyle = "rgba(255,255,255,.045)";
      ctx.beginPath(); ctx.moveTo(x, pad.top); ctx.lineTo(x, pad.top + chartH); ctx.stroke();
      ctx.fillStyle = "#666a7c"; ctx.fillText(label, x, height - 5);
    });
    [0, .33, .66, 1].forEach((ratio) => {
      const y = pad.top + chartH * ratio;
      ctx.strokeStyle = "rgba(255,255,255,.045)";
      ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(width - pad.right, y); ctx.stroke();
    });
    const drawLine = (data, start, end, fill) => {
      const points = data.map((value, index) => ({ x: pad.left + chartW * index / (data.length - 1), y: pad.top + chartH - (value / 100) * chartH }));
      const gradient = ctx.createLinearGradient(0, pad.top, 0, pad.top + chartH);
      gradient.addColorStop(0, fill); gradient.addColorStop(1, "rgba(0,0,0,0)");
      ctx.beginPath(); ctx.moveTo(points[0].x, pad.top + chartH); points.forEach((point) => ctx.lineTo(point.x, point.y)); ctx.lineTo(points.at(-1).x, pad.top + chartH); ctx.closePath(); ctx.fillStyle = gradient; ctx.fill();
      ctx.beginPath(); points.forEach((point, index) => index ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y));
      const stroke = ctx.createLinearGradient(pad.left, 0, width, 0); stroke.addColorStop(0, start); stroke.addColorStop(1, end); ctx.strokeStyle = stroke; ctx.lineWidth = 2; ctx.stroke();
      points.forEach((point) => { ctx.beginPath(); ctx.arc(point.x, point.y, 2.5, 0, Math.PI * 2); ctx.fillStyle = end; ctx.fill(); });
    };
    drawLine(safeSeries, "#8061ff", "#b18cff", "rgba(125,92,255,.17)");
    drawLine(riskSeries, "#3e7ef0", "#54d7ff", "rgba(76,141,255,.08)");
  }
  drawChart();
  new ResizeObserver(drawChart).observe(canvas);
})();
