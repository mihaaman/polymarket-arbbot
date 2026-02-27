import http.server
import socketserver
import json
import time
import threading
import requests
from urllib.parse import urlparse, parse_qs
from collections import deque

WATCHER_URL = "http://localhost:8000/api/data"
PORT = 7070 
STARTING_BALANCE = 50.0    


-İ HAVE DELETED THİS PART BECAUSE İT USES MY OWN STRATTEGY-



        self.is_running = False
        self.balance = STARTING_BALANCE
        self.net_profit = 0.0
        self.shares_per_trade = 25
        self.active_trades = {}      
        self.pending_settlements = [] 
        self.price_history = {}      
        self.history = []            
        self.trade_logs = []         
        self.profit_history = []     
        self.last_sync_ok = False
        self.current_market_id = None
        self.last_clear_ts = 0       
        self.lock = threading.Lock()

state = BotState()

def process_logic():
    while True:
        if state.is_running:
            try:
                response = requests.get(WATCHER_URL, timeout=1)
                if response.status_code == 200:
                    state.last_sync_ok = True
                    markets = response.json()
                    
                    if markets:
                        m_exp = str(markets[0].get('time_left', '15:00')).strip() 
                        m_time = markets[0].get('last_update', '00:00:00')
                        now_ts = int(time.time())
                        new_market_id = str((now_ts // 900) * 900)

                        is_last_minute = m_exp.startswith("00:")

                        with state.lock:
                            market_expired = (state.current_market_id and new_market_id != state.current_market_id)
                            timer_is_ending = (m_exp == "00:01" or m_exp == "00:00")

                            if market_expired or timer_is_ending:
                                state.last_clear_ts = time.time() 
                                if state.pending_settlements:
                                    for p in state.pending_settlements:
                                        state.balance += p['profit']
                                        state.net_profit += p['profit']
                                        state.profit_history.append({'ts': time.time(), 'pnl': p['profit']})
                                        state.history.append({"msg": f"WIN: {p['coin']}", "val": p['profit'], "type": "win"})
                                        state.trade_logs.append(f"[{m_time}] [SETTLED] {p['coin']} +${p['profit']:.2f}")
                                    state.pending_settlements = [] 

                                for coin, t in list(state.active_trades.items()):
                                    loss = t['price1'] * t['shares']
                                    state.balance -= loss
                                    state.net_profit -= loss
                                    state.trade_logs.append(f"[{m_time}] [EXPIRED] {coin} -${loss:.2f}")
                                state.active_trades = {}
                                state.current_market_id = new_market_id
                            
                            if not state.current_market_id:
                                state.current_market_id = new_market_id

                            for m in markets:
                                coin = m['title']
                                up_p, down_p = m['up'], m['down']

                                if coin not in state.price_history:
                                    state.price_history[coin] = {"up": deque(maxlen=MAX_HISTORY_TICKS), "down": deque(maxlen=MAX_HISTORY_TICKS)}
                                state.price_history[coin]["up"].append(up_p)
                                state.price_history[coin]["down"].append(down_p)

                                if coin in state.active_trades:
                                    t = state.active_trades[coin]
                                    elapsed = time.time() - t['ts']
                                    side2_price = down_p if t['side1'] == "UP" else up_p
                                    total_sum = t['price1'] + side2_price


                                    
-ALSO İ HAVE DELETED SOME PART FROM THERE BECAUSE İT USES MY OWN STRATTEGY-


                      
                                    if free_balance >= (state.shares_per_trade * 2.0):
                                        # UP DIP ENTRY
                                        if up_p <= 0.30 or up_p >= 0.70: 
                                            hist_up = state.price_history[coin]["up"]
                                            if len(hist_up) > 10:
                                                if up_p <= max(hist_up) * (1 - DIP_THRESHOLD) and up_p > 0.01:
                                                    fee = get_fee(up_p, state.shares_per_trade)
                                                    state.balance -= fee
                                                    state.net_profit -= fee
                                                    state.active_trades[coin] = {"side1": "UP", "price1": up_p, "ts": time.time(), "shares": state.shares_per_trade}
                                                    state.trade_logs.append(f"[{m_time}] [ENTRY] {coin} UP @ {up_p}¢")
                                                    continue 
                                        
                                        # DOWN DIP ENTRY
                                        if down_p <= 0.30 or down_p >= 0.70: 
                                            hist_down = state.price_history[coin]["down"]
                                            if len(hist_down) > 10:
                                                if down_p <= max(hist_down) * (1 - DIP_THRESHOLD) and down_p > 0.01:
                                                    fee = get_fee(down_p, state.shares_per_trade)
                                                    state.balance -= fee
                                                    state.net_profit -= fee
                                                    state.active_trades[coin] = {"side1": "DOWN", "price1": down_p, "ts": time.time(), "shares": state.shares_per_trade}
                                                    state.trade_logs.append(f"[{m_time}] [ENTRY] {coin} DOWN @ {down_p}¢")

                else: state.last_sync_ok = False
            except Exception as e:
                state.last_sync_ok = False
        time.sleep(0.1)

class BotHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/status':
            self.send_response(200); self.send_header('Content-type', 'application/json'); self.end_headers()
            with state.lock:
                now = time.time()
                state.profit_history = [p for p in state.profit_history if now - p['ts'] <= 86400]
                profit_24h = sum(p['pnl'] for p in state.profit_history)
                locked_active = sum(t['shares'] * 1.0 for t in state.active_trades.values())
                locked_pending = sum(p['shares'] * 1.0 for p in state.pending_settlements)
                data = {
                    "running": state.is_running, "sync": state.last_sync_ok, 
                    "balance": round(state.balance, 2), "free_balance": round(state.balance - (locked_active + locked_pending), 2),
                    "profit": round(state.net_profit, 2), "profit_24h": round(profit_24h, 2),
                    "active": [{"coin": c, "side": t['side1'], "price": t['price1'], "elapsed": int(time.time()-t['ts'])} for c,t in state.active_trades.items()],
                    "pending": state.pending_settlements, "history": state.history[-20:], "logs": state.trade_logs[-20:], "shares": state.shares_per_trade
                }
                self.wfile.write(json.dumps(data).encode())
        elif parsed.path == '/api/toggle':
            state.is_running = not state.is_running
            self.send_response(200); self.end_headers()
        elif parsed.path == '/api/settings':
            q = parse_qs(parsed.query)
            if 'shares' in q: state.shares_per_trade = int(q['shares'][0])
            self.send_response(200); self.end_headers()
        else:
            self.send_response(200); self.end_headers()
            self.wfile.write(self.get_html().encode())

    def get_html(self):
        return """
        <!DOCTYPE html><html><head><meta charset="UTF-8"><title>MATRIX ARB V3.1 DYNAMIC-FEES</title>
        <style>
            body { margin: 0; background: #000; color: #00FF41; font-family: 'Courier New', monospace; overflow: hidden; }
            canvas { position: fixed; top: 0; left: 0; z-index: -1; opacity: 0.15; }
            .wrapper { position: relative; z-index: 1; padding: 15px; max-width: 1400px; margin: 0 auto; }
            .status-bar { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #00FF41; padding-bottom: 10px; margin-bottom: 15px; font-size: 0.9em; }
            .grid { display: grid; grid-template-columns: 1fr 1fr 1.2fr; gap: 15px; }
            .box { background: rgba(0, 15, 0, 0.95); border: 1px solid #00FF41; padding: 12px; height: 500px; overflow-y: auto; scrollbar-width: thin; scrollbar-color: #00FF41 #000; }
            .stat-box { background: rgba(0, 40, 0, 0.6); border: 1px solid #00FF41; padding: 8px; text-align: center; font-size: 0.9em; }
            .win { color: #00FF41; } .loss { color: #FF3131; } .wait { color: #3498db; }
            .btn { background: #000; border: 1px solid #00FF41; color: #00FF41; padding: 8px 15px; cursor: pointer; font-family: inherit; font-weight: bold; }
            .btn:hover { background: #00FF41; color: #000; }
            input { background: #000; border: 1px solid #00FF41; color: #00FF41; width: 50px; padding: 4px; text-align: center; }
            hr { border: 0; border-top: 1px solid #004400; margin: 10px 0; }
            .log-item { font-size: 0.85em; margin-bottom: 4px; border-bottom: 1px solid #002200; padding-bottom: 2px; }
        </style></head>
        <body><canvas id="matrix"></canvas><div class="wrapper">
            <div class="status-bar">
                <div>WATCHER: <span id="sync">...</span> | PORT: 7070 | SHARES: <span id="currSh" style="color:#fff">25</span> | <input type="number" id="shIn" value="25"> <button class="btn" onclick="save()">SET</button></div>
                <button class="btn" onclick="fetch('/api/toggle')">START/STOP SYSTEM</button>
            </div>
            <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                <div class="stat-box" style="flex: 1.5;">FREE: <span id="fbal" style="color:#fff;">$0.00</span> / <span id="bal">$0.00</span></div>
                <div class="stat-box" style="flex: 1;">TOTAL PNL: <span id="prof">$0.00</span></div>
                <div class="stat-box" style="flex: 1;">24H PNL: <span id="prof24" style="color:#fff;">$0.00</span></div>
            </div>
            <div class="grid">
                <div class="box"><div style="color:#008F11; font-weight:bold; margin-bottom:10px;">[1] HUNTING LEG 2 (ACTIVE)</div><div id="activePos"></div></div>
                <div class="box"><div style="color:#008F11; font-weight:bold; margin-bottom:10px;">[2] PENDING SETTLEMENT</div><div id="waitPos"></div></div>
                <div class="box"><div style="color:#008F11; font-weight:bold; margin-bottom:10px;">[3] FULL TRADE LOGS</div><div id="history"></div></div>
            </div>
        </div><script>
            const canvas = document.getElementById('matrix'); const ctx = canvas.getContext('2d');
            canvas.width = window.innerWidth; canvas.height = window.innerHeight;
            const drops = Array(Math.floor(canvas.width/20)).fill(1);
            function draw() {
                ctx.fillStyle = "rgba(0,0,0,0.05)"; ctx.fillRect(0,0,canvas.width,canvas.height);
                ctx.fillStyle = "#00FF41"; drops.forEach((y, i) => {
                    ctx.fillText(Math.random()>0.5?"0":"1", i*20, y*20);
                    if(y*20 > canvas.height && Math.random()>0.975) drops[i]=0; drops[i]++;
                });
            }
            setInterval(draw, 50);
            function save(){ fetch('/api/settings?shares=' + document.getElementById('shIn').value); }
            setInterval(async () => {
                try {
                    const r = await fetch('/api/status'); const d = await r.json();
                    document.getElementById('bal').innerText = '$'+d.balance.toFixed(2);
                    document.getElementById('fbal').innerText = '$'+d.free_balance.toFixed(2);
                    document.getElementById('prof').innerText = '$'+d.profit.toFixed(2);
                    document.getElementById('prof24').innerText = '$'+d.profit_24h.toFixed(2);
                    document.getElementById('currSh').innerText = d.shares;
                    document.getElementById('sync').innerText = d.sync ? 'ULTRA-FAST' : 'OFFLINE';
                    document.getElementById('activePos').innerHTML = d.active.map(t => `<div class="log-item">> ${t.coin} ${t.side} @ ${t.price}¢ (${t.elapsed}s)</div>`).join('');
                    document.getElementById('waitPos').innerHTML = d.pending.map(p => `<div class="wait log-item">> ${p.coin}: Locked $${p.profit.toFixed(2)}</div>`).join('');
                    let combined = d.history.map(h => `<div class="${h.type} log-item">> ${h.msg}</div>`);
                    combined.push('<hr>');
                    combined.push(...d.logs.map(l => `<div class="log-item" style="color:#888">> ${l}</div>`));
                    document.getElementById('history').innerHTML = combined.reverse().join('');
                } catch(e) {}
            }, 500);
        </script></body></html>
        """

if __name__ == "__main__":
    threading.Thread(target=process_logic, daemon=True).start()
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), BotHandler) as httpd:
        print(f"🚀 BOT V3.1 RUNNING ON PORT {PORT}")
        httpd.serve_forever()
