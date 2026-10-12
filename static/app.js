
// last 60 values for the charts
const history = { total: [], allowed: [], syn: [] };

function addValue(list, value) {
  list.push(value);
  if (list.length > 60) list.shift();
}

// Draw simple line charts on a <canvas> (no library needed)
function drawChart(canvasId, lines) {
  const canvas = document.getElementById(canvasId);
  canvas.width = canvas.clientWidth; // match the real size so text isn't stretched
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  // highest value, so every line fits
  let max = 10;
  lines.forEach(line => line.values.forEach(v => { if (v > max) max = v; }));
  max = Math.ceil(max / 100) * 100; // round up so the labels are nice numbers

  // grid lines + labels
  ctx.strokeStyle = "#e9ecef";
  ctx.fillStyle = "#868e96";
  ctx.font = "12px Arial";
  for (let i = 0; i <= 4; i++) {
    const y = h - 20 - (h - 30) * i / 4;
    ctx.beginPath(); ctx.moveTo(40, y); ctx.lineTo(w, y); ctx.stroke();
    ctx.fillText(Math.round(max * i / 4), 0, y + 4);
  }

  // the lines
  lines.forEach(line => {
    ctx.strokeStyle = line.color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    line.values.forEach((v, i) => {
      const x = 40 + (w - 40) * i / 59;
      const y = h - 20 - (h - 30) * v / max;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
  });
}

async function update() {
  const res = await fetch("/api/stats");
  const data = await res.json();

  // big numbers
  document.getElementById("total").textContent = data.total_requests;
  document.getElementById("allowed").textContent = data.allowed_requests;
  document.getElementById("syn").textContent = data.syn_rate;
  document.getElementById("blocked-count").textContent = Object.keys(data.blocked_ips).length;

  const status = document.getElementById("status");
  status.textContent = data.status;
  status.className = data.status === "Normal" ? "status normal" : "status attack";

  // charts
  addValue(history.total, data.total_requests);
  addValue(history.allowed, data.allowed_requests);
  addValue(history.syn, data.syn_rate);
  drawChart("http-chart", [
    { values: history.total, color: "#f76707" },
    { values: history.allowed, color: "#1c7ed6" },
  ]);
  drawChart("syn-chart", [{ values: history.syn, color: "#7048e8" }]);

  let alertsHtml = "";
  for (const a of data.alerts) {
    alertsHtml += `<li><span>${a.time}</span>${a.message}</li>`;
  }
  document.getElementById("alerts").innerHTML = alertsHtml || "<li>No alerts yet</li>";

  // blocked IPs
  let blockedHtml = "";
  for (const [ip, time] of Object.entries(data.blocked_ips)) {
    blockedHtml += `<tr><td>${ip}</td><td>${time}</td>
      <td><button onclick="unblock('${ip}')">Unblock</button></td></tr>`;
  }
  document.getElementById("blocked").innerHTML = blockedHtml || "<tr><td colspan='3'>None</td></tr>";

  // top IPs
  let topHtml = "";
  for (const [ip, rate] of data.top_ips) {
    topHtml += `<tr><td>${ip}</td><td>${rate}</td></tr>`;
  }
  document.getElementById("top-ips").innerHTML = topHtml;
}

// send a POST request with JSON
function post(url, body) {
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function unblock(ip) { post("/api/unblock", { ip: ip }); }
function simulate(attack) { post("/api/simulate", { attack: attack }); }

document.getElementById("block-form").addEventListener("submit", e => {
  e.preventDefault();
  const ip = document.getElementById("ip-input").value.trim();
  if (ip) post("/api/block", { ip: ip });
  e.target.reset();
});

update();
setInterval(update, 1000);
