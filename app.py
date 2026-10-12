"""
DDoS Monitor - dashboard prototype for the monitoring & control server.

For now the traffic numbers are FAKE (random), so we can show the dashboard
before the lab servers are ready. Later we replace get_traffic() and
get_syn_rate() with real data from the Nginx reverse proxy.

Run:
    pip install flask
    python app.py
Then open http://localhost:5000
"""
import random
import time

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# ---------- settings ----------
HTTP_LIMIT = 100    # requests per second from ONE IP before we block it
SYN_LIMIT = 1000    # SYN packets per second before we raise an alert

# ---------- state (kept in memory, resets when the app restarts) ----------
blocked_ips = {}    # ip -> time it was blocked
alerts = []         # newest first
simulation = {"http_flood": False, "syn_flood": False}
syn_alert_sent = False


def now():
    return time.strftime("%H:%M:%S")


def add_alert(message):
    alerts.insert(0, {"time": now(), "message": message})
    del alerts[50:]  # keep the last 50


def block_ip(ip, reason):
    blocked_ips[ip] = now()
    add_alert(f"Blocked {ip}: {reason}")


def get_traffic():
    """Requests per second for each IP. FAKE for now.
    Later: count lines per IP in the Nginx access log for the last second."""
    traffic = {
        "192.168.10.41": random.randint(3, 10),  # normal users (traffic generator)
        "192.168.10.42": random.randint(3, 10),
        "192.168.10.43": random.randint(3, 10),
        "192.168.10.50": random.randint(1, 3),   # laptop = real user
    }
    if simulation["http_flood"]:
        traffic["192.168.10.100"] = random.randint(800, 1200)
        traffic["192.168.10.101"] = random.randint(800, 1200)
    return traffic


def get_syn_rate():
    """SYN packets per second. FAKE for now.
    Later: read it on the proxy (e.g. count SYN_RECV connections with `ss`)."""
    if simulation["syn_flood"]:
        return random.randint(4000, 6000)
    return random.randint(10, 30)


# ---------- pages ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def stats():
    global syn_alert_sent
    traffic = get_traffic()
    syn_rate = get_syn_rate()

    # 1) HTTP flood: block any IP that sends more than HTTP_LIMIT
    for ip, rate in traffic.items():
        if rate > HTTP_LIMIT and ip not in blocked_ips:
            block_ip(ip, f"HTTP flood ({rate} req/s)")

    # 2) SYN flood: source IPs are usually fake, so we only alert once
    if syn_rate > SYN_LIMIT and not syn_alert_sent:
        add_alert(f"SYN flood detected ({syn_rate} SYN/s)")
        syn_alert_sent = True
    if syn_rate <= SYN_LIMIT:
        syn_alert_sent = False

    total = sum(traffic.values())
    allowed = sum(rate for ip, rate in traffic.items() if ip not in blocked_ips)
    under_attack = total > 500 or syn_rate > SYN_LIMIT

    return jsonify({
        "time": now(),
        "status": "Under attack" if under_attack else "Normal",
        "total_requests": total,
        "allowed_requests": allowed,
        "syn_rate": syn_rate,
        "top_ips": sorted(traffic.items(), key=lambda x: x[1], reverse=True)[:5],
        "blocked_ips": blocked_ips,
        "alerts": alerts[:10],
    })


@app.route("/api/block", methods=["POST"])
def block():
    block_ip(request.json["ip"], "blocked by hand")
    return jsonify(ok=True)


@app.route("/api/unblock", methods=["POST"])
def unblock():
    ip = request.json["ip"]
    blocked_ips.pop(ip, None)
    add_alert(f"Unblocked {ip}")
    return jsonify(ok=True)


@app.route("/api/simulate", methods=["POST"])
def simulate():
    """Prototype only: turn fake attacks on and off."""
    attack = request.json["attack"]  # "http_flood", "syn_flood" or "stop"
    if attack == "stop":
        simulation["http_flood"] = False
        simulation["syn_flood"] = False
    else:
        simulation[attack] = True
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
