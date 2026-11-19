#!/usr/bin/env python3
"""感知层输出可视化（演示用）。

一个零依赖的本地 Web 看板：实时读取感知层写入的 JSON 快照，在浏览器里展示
「路口四个方向的车辆排队情况 + 下游占用 + 数据新鲜度」。

用法::

    python scripts/perception_dashboard.py --path /tmp/gd32-traffic/perception.json --port 8090

然后浏览器打开 http://<本机IP>:8090 （本机则 http://127.0.0.1:8090）。
浏览器每 500ms 拉一次 /api/perception 并刷新画面。
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HTML = r"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>感知层输出 · 影子运行</title>
<style>
  :root { --bg:#0f1420; --card:#1a2233; --line:#2a3550; --txt:#e6edf7;
          --dim:#8b98b0; --red:#ff5a5f; --yellow:#ffc53d; --green:#3ddc84; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--txt); font-family:-apple-system,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;
         padding:20px; max-width:920px; margin:0 auto; }
  h1 { font-size:20px; margin-bottom:4px; }
  .sub { color:var(--dim); font-size:13px; margin-bottom:16px; }
  .bar { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:18px; }
  .chip { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 14px; min-width:120px; }
  .chip .k { color:var(--dim); font-size:12px; }
  .chip .v { font-size:22px; font-weight:600; margin-top:2px; }
  .chip .v.ok { color:var(--green); } .chip .v.warn { color:var(--yellow); } .chip .v.bad { color:var(--red); }
  .grid { display:grid; grid-template-columns:1fr 110px 1fr; grid-template-rows:auto 110px auto;
          grid-template-areas:". N ." "W C E" ". S ."; gap:12px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px; }
  .dir-N{grid-area:N} .dir-W{grid-area:W} .dir-E{grid-area:E} .dir-S{grid-area:S}
  .ctr { grid-area:C; display:flex; align-items:center; justify-content:center;
         background:#141b2c; border:2px dashed var(--line); border-radius:12px;
         font-size:13px; color:var(--dim); text-align:center; }
  .dir-name { font-weight:700; font-size:16px; margin-bottom:8px; }
  .lanes { display:flex; flex-direction:column; gap:6px; }
  .lane { display:flex; justify-content:space-between; align-items:center; }
  .lane .mov { color:var(--dim); font-size:13px; }
  .lane .cnt { font-size:18px; font-weight:600; }
  .lane .cnt.z { color:var(--dim); }
  .lane .cnt.n { color:var(--green); }
  .lane .ids { color:var(--dim); font-size:11px; word-break:break-all; margin-top:1px; }
  .down { margin-top:16px; background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px; }
  .down h2 { font-size:14px; margin-bottom:8px; color:var(--dim); }
  .occ { display:flex; gap:8px; flex-wrap:wrap; }
  .occ .o { border:1px solid var(--line); border-radius:8px; padding:6px 10px; font-size:12px; }
  .occ .o .pct { font-weight:700; }
  footer { margin-top:16px; color:var(--dim); font-size:11px; }
  .controls { display:flex; gap:10px; align-items:center; margin-bottom:16px; flex-wrap:wrap; }
  .controls button { background:var(--card); color:var(--txt); border:1px solid var(--line);
                     border-radius:8px; padding:8px 14px; font-size:13px; cursor:pointer; }
  .controls button:hover { border-color:var(--green); }
  #btn-fault:hover { border-color:var(--red); }
  #fault-state { font-size:13px; }
</style>
</head>
<body>
  <h1>🚦 感知层输出 · 车辆排队</h1>
  <div class="sub">实时读取感知 JSON（2 Hz）· 数据由视觉感知层 / 合成感知源写入</div>

  <div class="bar">
    <div class="chip"><div class="k">车辆总数</div><div class="v" id="total">–</div></div>
    <div class="chip"><div class="k">数据新鲜度</div><div class="v" id="fresh">–</div></div>
    <div class="chip"><div class="k">帧时间</div><div class="v" id="ts" style="font-size:14px">–</div></div>
  </div>

  <div class="controls">
    <button id="btn-fault" onclick="setFault(true)">⚠️ 注入故障（感知停发）</button>
    <button id="btn-recover" onclick="setFault(false)">✅ 恢复感知</button>
    <span id="fault-state"></span>
  </div>

  <div class="grid">
    <div class="card dir-N" id="dir-N"></div>
    <div class="card dir-W" id="dir-W"></div>
    <div class="ctr">交叉口</div>
    <div class="card dir-E" id="dir-E"></div>
    <div class="card dir-S" id="dir-S"></div>
  </div>

  <div class="down">
    <h2>下游占用（P1 溢流保护输入）</h2>
    <div class="occ" id="downstream">（无数据 / 未提供）</div>
  </div>

  <footer>lane_id 规范：north/east/south/west + through/left · 绿色=有车排队</footer>

<script>
const LANE_LABELS = {
  north_through:["N 直行","N"], north_left:["N 左转","N"],
  east_through:["E 直行","E"], east_left:["E 左转","E"],
  south_through:["S 直行","S"], south_left:["S 左转","S"],
  west_through:["W 直行","W"], west_left:["W 左转","W"],
};
const DIRS = ["N","E","S","W"];
const DIR_PREFIX = { N:"north", E:"east", S:"south", W:"west" };

function renderDir(elmId, dir){
  const el = document.getElementById(elmId);
  el.innerHTML = `<div class="dir-name">${dir} 方向</div><div class="lanes">
    <div class="lane"><span class="mov">直行</span><span class="cnt" id="${dir}-through">0</span></div>
    <div class="lane ids" id="${dir}-through-ids"></div>
    <div class="lane"><span class="mov">左转</span><span class="cnt" id="${dir}-left">0</span></div>
    <div class="lane ids" id="${dir}-left-ids"></div>
  </div>`;
}

async function poll(){
  try {
    const r = await fetch("/api/perception", {cache:"no-store"});
    const d = await r.json();
    render(d);
  } catch(e) { setFresh(-1, "连接失败"); }
  setTimeout(poll, 500);
}

function render(d){
  const dets = d.detections || [];
  const byLane = {};
  for (const x of dets) (byLane[x.lane_id] = byLane[x.lane_id] || []).push(x.track_id);

  const total = dets.length;
  document.getElementById("total").textContent = total;

  for (const dir of DIRS){
    for (const mov of ["through","left"]){
      const lane = DIR_PREFIX[dir] + "_" + mov;   // north_through / east_left / ...
      const ids = byLane[lane] || [];
      const cntEl = document.getElementById(dir+"-"+mov);
      const idsEl = document.getElementById(dir+"-"+mov+"-ids");
      cntEl.textContent = ids.length;
      cntEl.className = "cnt " + (ids.length ? "n" : "z");
      idsEl.textContent = ids.length ? "track " + [...new Set(ids)].join(", ") : "";
    }
  }

  // 数据新鲜度
  const at = d.observed_at || 0;
  const now = Date.now()/1000;
  const age = now - at;
  const tsEl = document.getElementById("ts");
  tsEl.textContent = at ? new Date(at*1000).toLocaleTimeString() : "无";
  setFresh(age, age < 3 ? "新鲜" : (age < 6 ? "陈旧" : "断流"));

  // 下游占用
  const ds = d.downstream || [];
  const dsEl = document.getElementById("downstream");
  if (!ds.length){ dsEl.innerHTML = "（无数据 / 未提供）"; return; }
  dsEl.innerHTML = ds.map(o => {
    const lbl = (LANE_LABELS[o.lane_id] || [o.lane_id])[0];
    const pct = (o.occupancy==null) ? "未知" : Math.round(o.occupancy*100)+"%";
    return `<span class="o">${lbl}：<span class="pct">${pct}</span></span>`;
  }).join("");
}

function setFresh(age, text){
  const el = document.getElementById("fresh");
  el.textContent = text;
  el.className = "v " + (age < 0 ? "warn" : (age < 3 ? "ok" : (age < 6 ? "warn" : "bad")));
}

async function setFault(on){
  try {
    const r = await fetch("/api/" + (on ? "fault" : "recover"), {method:"POST"});
    const j = await r.json();
    const el = document.getElementById("fault-state");
    el.textContent = j.fault ? "（故障中：感知已停发）" : "（正常）";
    el.style.color = j.fault ? "var(--red)" : "var(--dim)";
  } catch(e){}
}

DIRS.forEach(d => renderDir("dir-"+d, d));
poll();
</script>
</body>
</html>"""


def read_perception(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"observed_at": 0, "detections": [], "downstream": []}


class Handler(BaseHTTPRequestHandler):
    perception_path = Path("/tmp/gd32-traffic/perception.json")
    fault_flag = Path("/tmp/gd32-traffic/fault.flag")

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._serve_bytes(HTML.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/api/perception":
            body = json.dumps(read_perception(self.perception_path)).encode("utf-8")
            self._serve_bytes(body, "application/json; charset=utf-8")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        """故障注入：/api/fault 建立标志文件（感知源停发）；/api/recover 清除。"""
        if self.path == "/api/fault":
            try:
                self.fault_flag.parent.mkdir(parents=True, exist_ok=True)
                self.fault_flag.touch()
            except OSError:
                pass
            self._serve_bytes(b'{"fault": true}', "application/json; charset=utf-8")
        elif self.path == "/api/recover":
            try:
                self.fault_flag.unlink(missing_ok=True)
            except OSError:
                pass
            self._serve_bytes(b'{"fault": false}', "application/json; charset=utf-8")
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_bytes(self, body: bytes, ctype: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # 静默访问日志，避免刷屏
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="感知层输出可视化看板")
    ap.add_argument("--path", default="/tmp/gd32-traffic/perception.json",
                    help="感知 JSON 路径（与 shadow.yaml 的 perception.input_path 一致）")
    ap.add_argument("--fault-flag", default="/tmp/gd32-traffic/fault.flag",
                    help="故障注入标志文件（与 simulate_perception.py 的 --fault-flag 一致）")
    ap.add_argument("--host", default="0.0.0.0", help="监听地址")
    ap.add_argument("--port", type=int, default=8090, help="端口")
    args = ap.parse_args()

    Handler.perception_path = Path(args.path)
    Handler.fault_flag = Path(args.fault_flag)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"感知看板已启动： http://127.0.0.1:{args.port}  （本机）", flush=True)
    print(f"局域网访问：      http://<本机IP>:{args.port}", flush=True)
    print(f"读取感知文件：    {args.path}", flush=True)
    print(f"故障标志文件：    {args.fault_flag}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
