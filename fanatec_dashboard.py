#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fanatec Wheelbase Dashboard — Web-Board für die ftec_tuning-Sysfs-Attribute
des gotzl/hid-fanatecff-Treibers (CSL DD & Co).

Nur Python-Stdlib. GET /  -> Board, GET /api/values, POST /api/set.
"""
import json, glob, os, re, sys, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8088

META = {
    "SEN":   ("Lenkwinkel (°)",      90, 2530, 10),
    "FF":    ("FFB-Stärke",           0,  100,  1),
    "SHO":   ("Shock",                0,  100,  1),
    "DPR":   ("Dämpfung",             0,  100,  1),
    "FOR":   ("Force",                0,  100,  1),
    "SPR":   ("Spring",               0,  100,  1),
    "INT":   ("Intensität",           0,  100,  1),
    "NDP":   ("Natural Damping",      0,  100,  1),
    "NFR":   ("Natural Friction",     0,  100,  1),
    "NIN":   ("Natural Inertia",      0,  100,  1),
    "FFS":   ("FFB-Sensitivity",      0,  100,  1),
    "ACP":   ("Auto-Centering Pull",  0,  100,  1),
    "BLI":   ("Brake-Lock-Indicator", 0,  110,  1),
    "brF":   ("brF",                  0,  100,  1),
    "FEI":   ("FEI",                  0,  100,  1),
    "SLOT":  ("Tuning-Slot",          0,   10,  1),
    "FUL":   ("FullForce",            0,    1,  1),
    "advanced_mode": ("Advanced Mode", 0, 1, 1),
}
TOGGLES = {"FUL", "advanced_mode"}
WRITE_ONLY = {"RESET"}
SKIP = {"uevent"}


def tuning_dir():
    for d in sorted(glob.glob("/sys/class/ftec_tuning/*")):
        if os.path.isdir(d) and os.path.exists(os.path.join(d, "SEN")):
            return d
    return None


def read_attrs(d):
    out = {}
    try:
        names = sorted(os.listdir(d))
    except OSError:
        return out
    for f in names:
        if f in SKIP or f in WRITE_ONLY:
            continue
        p = os.path.join(d, f)
        if not os.path.isfile(p):
            continue
        try:
            with open(p) as fh:
                v = fh.read().strip()
        except OSError:
            continue
        try:
            out[f] = int(v)
        except ValueError:
            out[f] = v
    return out


def ensure_tuning_values(d, tries=3):
    """Der Treiber blockiert Schreibzugriffe, bis die Tuning-Werte einmal vom
    Gerät gelesen wurden (SLOT == 0 => noch nicht gelesen). Ein Schreibzugriff
    auf RESET fordert die aktuellen Werte vom Gerät an (kein Werks-Reset,
    trotz des Namens)."""
    for _ in range(tries):
        vals = read_attrs(d)
        if vals.get("SLOT", 0) != 0:
            return vals
        try:
            with open(os.path.join(d, "RESET"), "w") as fh:
                fh.write("1")
        except OSError:
            return vals
        time.sleep(0.5)
    return read_attrs(d)


PAGE = """<!DOCTYPE html>
<html lang="de"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fanatec Control — CSL DD</title>
<style>
:root { --bg:#0b0d12; --card:#141821; --line:#232a38; --txt:#e8ebf2; --dim:#8b94a7; --acc:#e10600; --ok:#39d98a; }
* { box-sizing:border-box; margin:0; }
body { background:var(--bg); color:var(--txt); font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif; padding:24px 16px 60px; max-width:860px; margin:0 auto; }
header { display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; flex-wrap:wrap; gap:8px; }
h1 { font-size:1.35rem; letter-spacing:.5px; }
h1 span { color:var(--acc); }
#status { font-size:.85rem; color:var(--dim); }
#status .dot { display:inline-block; width:9px; height:9px; border-radius:50%; background:var(--ok); margin-right:6px; }
#status.off .dot { background:var(--acc); }
.banner { background:#2a1215; border:1px solid #5c1a1a; color:#ffb3b0; padding:12px 16px; border-radius:10px; margin-bottom:16px; display:none; }
.card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 18px; margin-bottom:12px; }
.card h2 { font-size:.8rem; text-transform:uppercase; letter-spacing:1.2px; color:var(--dim); margin-bottom:12px; }
.row { display:flex; align-items:center; gap:12px; padding:7px 0; }
.row label { flex:0 0 190px; font-size:.92rem; }
.row .val { flex:0 0 76px; text-align:right; font-variant-numeric:tabular-nums; font-weight:600; }
.row .badge { flex:0 0 46px; text-align:center; font-size:.72rem; color:var(--dim); }
input[type=range] { flex:1; accent-color:var(--acc); height:4px; }
input[type=number] { width:74px; background:#0e1118; border:1px solid var(--line); color:var(--txt); border-radius:8px; padding:6px 8px; font-size:.9rem; }
.tgl { appearance:none; width:46px; height:26px; background:#2a3140; border-radius:14px; position:relative; cursor:pointer; transition:.2s; flex:0 0 46px; }
.tgl:checked { background:var(--acc); }
.tgl::after { content:''; position:absolute; top:3px; left:3px; width:20px; height:20px; border-radius:50%; background:#fff; transition:.2s; }
.tgl:checked::after { left:23px; }
button { background:var(--acc); color:#fff; border:0; padding:9px 18px; border-radius:10px; font-weight:600; cursor:pointer; font-size:.9rem; }
button.ghost { background:transparent; border:1px solid var(--line); color:var(--dim); }
.presets { display:flex; gap:8px; flex-wrap:wrap; padding:4px 0 10px; }
.presets button { background:#1b2230; border:1px solid var(--line); padding:6px 12px; font-size:.8rem; }
.flash { animation:fl .6s; } @keyframes fl { 0%{background:#3a1518} 100%{background:var(--card)} }
.hint { font-size:.78rem; color:var(--dim); margin-top:4px; }
.group2 { border-left:3px solid var(--acc); padding-left:12px; }
</style></head>
<body>
<header>
  <h1>🏎 <span>Fanatec</span> Control</h1>
  <div id="status"><span class="dot"></span><span id="stTxt">verbinde…</span></div>
</header>
<div class="banner" id="banner">Wheelbase nicht verbunden — USB prüfen, dann aktualisiert sich diese Seite automatisch.</div>
<main id="panel"></main>
<p class="hint">Änderungen werden sofort an die Wheelbase gesendet (Tuning-Menü der CSL DD). SEN „1270" = Auto-Modus der Base — sobald du den Regler bewegst, wird ein fester Winkel gesetzt. RESET setzt alle Tuning-Werte zurück.</p>
<script>
const META = __META__;
const TOGGLES = new Json_Toggles;
let rendered = false, dragging = null;

async function api(path, body) {
  const opt = body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {};
  const r = await fetch(path, opt);
  return r.json();
}

function render(vals) {
  const p = document.getElementById('panel');
  p.innerHTML = '';
  const order = ['SEN','FF','DPR','SHO','SPR','FOR','INT','NDP','NFR','NIN','FFS','ACP','BLI','brF','FEI','SLOT','FUL','advanced_mode'];
  const groups = [
    {title:'Lenkung', items:['SEN'], presets:true},
    {title:'Force Feedback', items:['FF','DPR','SHO','SPR','FOR','INT'], main:true},
    {title:'Fein-Hub (Natural)', items:['NDP','NFR','NIN']},
    {title:'Sonstiges', items:['FFS','ACP','BLI','brF','FEI','SLOT','FUL','advanced_mode']},
  ];
  for (const g of groups) {
    const card = document.createElement('div'); card.className = 'card';
    card.innerHTML = '<h2>'+g.title+'</h2>';
    if (g.presets) {
      const pr = document.createElement('div'); pr.className = 'presets';
      for (const deg of [360,540,720,900,1080]) {
        const b = document.createElement('button'); b.textContent = deg+'°';
        b.onclick = () => setAttr('SEN', deg);
        pr.appendChild(b);
      }
      card.appendChild(pr);
    }
    for (const k of g.items) {
      if (!(k in vals)) continue;
      const meta = META[k] || [k,0,100,1];
      const [label, mn, mx, st] = meta;
      const v = vals[k];
      const row = document.createElement('div'); row.className = 'row';
      const lab = document.createElement('label'); lab.textContent = label;
      row.appendChild(lab);
      if (TOGGLES.has(k)) {
        const t = document.createElement('input'); t.type='checkbox'; t.className='tgl'; t.checked = !!v;
        t.onchange = () => setAttr(k, t.checked?1:0);
        row.appendChild(t);
      } else {
        const slider = document.createElement('input'); slider.type='range';
        slider.min = mn; slider.max = Math.max(mx, Math.ceil(v/10)*10); slider.step = st; slider.value = v;
        slider.dataset.k = k;
        slider.addEventListener('pointerdown', () => dragging = k);
        slider.addEventListener('pointerup',   () => { if (dragging===k) dragging=null; });
        slider.addEventListener('input',  () => { num.value = slider.value; badge.textContent = slider.value; });
        slider.addEventListener('change', () => setAttr(k, parseInt(slider.value)));
        row.appendChild(slider);
        const num = document.createElement('input'); num.type='number'; num.min=mn; num.value=v; num.dataset.k=k;
        num.onchange = () => { if (num.value!=='') setAttr(k, parseInt(num.value)); };
        row.appendChild(num);
        const badge = document.createElement('span'); badge.className='badge'; badge.id='badge-'+k; badge.textContent = v;
        row.appendChild(badge);
        row._els = {num, badge};
        row.dataset.k = k;
      }
      card.appendChild(row);
      card._rows = card._rows || {}; card._rows[k] = row;
    }
    if (g.main) {
      const rst = document.createElement('button'); rst.className='ghost'; rst.textContent='Tuning zurücksetzen (RESET)';
      rst.onclick = () => { if (confirm('Alle Tuning-Werte der Wheelbase auf Werkseinstellung zurücksetzen?')) setAttr('RESET', 1); };
      card.appendChild(rst);
    }
    p.appendChild(card);
  }
  rendered = true;
}

function update(vals) {
  for (const k in vals) {
    const row = document.querySelector('.row[data-k="'+k+'"]');
    if (!row) continue;
    const badge = row.querySelector('.badge'); const num = row.querySelector('input[type=number]');
    const tgl = row.querySelector('.tgl'); const slider = row.querySelector('input[type=range]');
    const v = vals[k];
    if (badge && dragging !== k) badge.textContent = v;
    if (num && document.activeElement !== num) num.value = v;
    if (slider && dragging !== k) { slider.max = Math.max(parseInt(slider.max), Math.ceil(v/10)*10); if (dragging!==k) slider.value = v; }
    if (tgl) tgl.checked = !!v;
  }
}

async function setAttr(k, v) {
  const res = await api('/api/set', {attr:k, value:v});
  const card = document.querySelector('.row[data-k="'+k+'"]');
  if (res.ok) { if (card) { card.classList.remove('flash'); void card.offsetWidth; card.classList.add('flash'); } }
  else { alert('Fehler: ' + (res.error || res.statusText || JSON.stringify(res))); refresh(); }
}

async function refresh() {
  const d = await api('/api/values');
  const st = document.getElementById('status');
  const banner = document.getElementById('banner');
  if (!d.connected) { st.classList.add('off'); document.getElementById('stTxt').textContent = 'Wheelbase nicht verbunden';
    banner.style.display='block'; return; }
  st.classList.remove('off'); document.getElementById('stTxt').textContent = 'verbunden · ' + (d.path||'').split('/').pop();
  banner.style.display='none';
  if (!rendered) render(d.values); else update(d.values);
}
refresh(); setInterval(refresh, 4000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _html(self):
        body = PAGE.replace("__META__", json.dumps(META)).replace("new Json_Toggles", "new Set(" + json.dumps(sorted(TOGGLES)) + ")").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._html()
        elif self.path.startswith("/api/values"):
            d = tuning_dir()
            if not d:
                self._json(200, {"connected": False})
            else:
                self._json(200, {"connected": True, "path": d, "values": ensure_tuning_values(d)})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self.path.startswith("/api/set"):
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._json(400, {"error": "bad json"})
            return
        attr = str(req.get("attr", ""))
        value = req.get("value")
        if not re.match(r"^[A-Za-z_][A-Za-z_0-9]*$", attr) or attr in SKIP:
            self._json(400, {"error": "ungültiges Attribut"})
            return
        d = tuning_dir()
        if not d:
            self._json(409, {"error": "Wheelbase nicht verbunden"})
            return
        path = os.path.join(d, attr)
        if not os.path.exists(path):
            self._json(400, {"error": "Attribut unbekannt"})
            return
        try:
            with open(path, "w") as fh:
                fh.write(str(value))
        except OSError as e:
            self._json(500, {"error": "schreiben fehlgeschlagen: %s" % e})
            return
        self._json(200, {"ok": True, "attr": attr, "value": value})


def main():
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("Fanatec Dashboard auf Port %d — Tuning: %s" % (PORT, tuning_dir() or "(wartet auf Wheelbase)"))
    srv.serve_forever()


if __name__ == "__main__":
    main()