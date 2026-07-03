"""Local drag-and-drop interface — the easiest way to run a file through.

No web framework: Python's standard-library http.server only. Start it with

    python recover_npis.py --serve

and a browser opens at http://127.0.0.1:8765. Drag a claims file onto the page,
watch the live pipeline, download the finished workbook. Same engine as the CLI.

Upload is a raw-body POST (the page sends the file bytes with an X-Filename
header), so there is no multipart parsing and no dependency surface.
"""

import os
import html
import json
import threading
import time
import traceback
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import run_pipeline, write_report

JOBS = {}          # job_id -> dict(frac, msg, done, error, out_path, name, stats)
WORKDIR = Path("/tmp/claimscrub_web")
WORKDIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------- the page ----
PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Claims Intake</title>
<style>
  :root{
    --ink:#11201c; --ink-soft:#4a5d57; --line:#d2ddd7; --line-soft:#e7eeea;
    --panel:#fbfdfc; --paper:#f3f7f5; --teal:#0c7c66; --teal-deep:#075a4a;
    --amber:#b06a00; --good:#0c7c66; --bad:#a8331f; --shadow:rgba(17,32,28,.08);
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%}
  body{
    background:var(--paper); color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    font-size:15px; line-height:1.5; -webkit-font-smoothing:antialiased;
    display:flex; align-items:flex-start; justify-content:center; padding:40px 20px;
  }
  .mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}
  .wrap{width:100%; max-width:680px}
  header{display:flex; align-items:baseline; justify-content:space-between; margin-bottom:22px}
  .title{font-size:20px; font-weight:680; letter-spacing:-.01em}
  .title b{color:var(--teal-deep)}
  .sub{font-size:12.5px; color:var(--ink-soft)}
  .card{background:var(--panel); border:1px solid var(--line); border-radius:14px;
        box-shadow:0 1px 0 var(--shadow); overflow:hidden}
  /* intake tray */
  .tray{position:relative; margin:0; padding:38px 28px; text-align:center;
        border-bottom:1px solid var(--line-soft); transition:background .15s,border-color .15s}
  .tray .slot{border:1.5px dashed var(--line); border-radius:12px; padding:34px 18px;
        transition:border-color .15s, background .15s; cursor:pointer; background:var(--paper)}
  .tray.drag .slot{border-color:var(--teal); background:#ecf5f2}
  .slot h2{margin:0 0 4px; font-size:16px; font-weight:640}
  .slot p{margin:0; font-size:12.5px; color:var(--ink-soft)}
  .slot .fname{margin-top:10px; font-size:13px; color:var(--teal-deep)}
  .pick{color:var(--teal-deep); text-decoration:underline; text-underline-offset:2px}
  input[type=file]{display:none}
  /* options row */
  .opts{display:flex; flex-wrap:wrap; gap:14px 22px; padding:16px 28px; align-items:center;
        border-bottom:1px solid var(--line-soft); font-size:13px}
  .opt{display:flex; align-items:center; gap:7px; color:var(--ink-soft)}
  .opt label{color:var(--ink)}
  select,input[type=number]{font:inherit; font-size:13px; padding:4px 7px; border:1px solid var(--line);
        border-radius:7px; background:var(--panel); color:var(--ink)}
  input[type=number]{width:62px}
  .seg{display:inline-flex; border:1px solid var(--line); border-radius:8px; overflow:hidden}
  .seg button{font:inherit; font-size:12.5px; padding:4px 11px; border:0; background:var(--panel);
        color:var(--ink-soft); cursor:pointer}
  .seg button.on{background:var(--teal); color:#fff}
  .check{display:inline-flex; align-items:center; gap:6px; cursor:pointer}
  .check input{accent-color:var(--teal)}
  /* action */
  .act{padding:18px 28px; display:flex; align-items:center; gap:14px}
  .run{font:inherit; font-weight:640; font-size:14px; color:#fff; background:var(--teal);
       border:0; border-radius:9px; padding:11px 20px; cursor:pointer; transition:background .15s}
  .run:hover{background:var(--teal-deep)}
  .run:disabled{background:#9bb7af; cursor:not-allowed}
  .hint{font-size:12px; color:var(--ink-soft)}
  /* pipeline tracker (the signature) */
  .run-panel{display:none; padding:6px 28px 24px}
  .run-panel.show{display:block}
  .bar{height:6px; background:var(--line-soft); border-radius:6px; overflow:hidden; margin:14px 0 18px}
  .bar > i{display:block; height:100%; width:0; background:var(--teal); transition:width .35s ease}
  .stage{display:flex; align-items:center; gap:12px; padding:7px 0; font-size:13.5px; color:var(--ink-soft)}
  .stage .dot{width:9px; height:9px; border-radius:50%; background:var(--line); flex:none;
        box-shadow:0 0 0 0 rgba(12,124,102,.0)}
  .stage.active{color:var(--ink)}
  .stage.active .dot{background:var(--amber); box-shadow:0 0 0 4px rgba(176,106,0,.14)}
  .stage.done{color:var(--ink)}
  .stage.done .dot{background:var(--good)}
  .stage .lbl{flex:1}
  .stage .num{font-size:11px; color:var(--ink-soft)}
  .live{margin-top:8px; font-size:12.5px; color:var(--ink-soft); min-height:1.2em}
  /* results */
  .result{display:none; padding:8px 28px 26px}
  .result.show{display:block}
  .grid{display:grid; grid-template-columns:1fr 1fr; gap:1px; background:var(--line-soft);
        border:1px solid var(--line-soft); border-radius:10px; overflow:hidden; margin:8px 0 18px}
  .cell{background:var(--panel); padding:12px 14px}
  .cell .k{font-size:11.5px; color:var(--ink-soft); text-transform:uppercase; letter-spacing:.04em}
  .cell .v{font-size:20px; font-weight:680; margin-top:3px}
  .cell .v small{font-size:12px; font-weight:500; color:var(--ink-soft)}
  .dl{display:inline-flex; align-items:center; gap:9px; font:inherit; font-weight:640; font-size:14px;
      color:#fff; background:var(--teal); border:0; border-radius:9px; padding:11px 20px;
      text-decoration:none; cursor:pointer}
  .dl:hover{background:var(--teal-deep)}
  .err{display:none; margin:6px 28px 24px; padding:13px 15px; border:1px solid #e6c4bc;
       background:#fbeeeb; border-radius:10px; color:#7c2718; font-size:13.5px}
  .err.show{display:block}
  footer{margin-top:16px; font-size:11.5px; color:var(--ink-soft); text-align:center; line-height:1.6}
  @media (max-width:520px){ .grid{grid-template-columns:1fr} .opts{gap:12px} }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="title">Claims&nbsp;<b>Intake</b></div>
    <div class="sub mono">CMS + NPPES · live</div>
  </header>

  <div class="card">
    <!-- intake tray -->
    <div class="tray" id="tray">
      <div class="slot" id="slot">
        <h2>Drop a claims file</h2>
        <p>.xlsx, .xls, .csv or .tsv — or <span class="pick">choose a file</span></p>
        <div class="fname mono" id="fname"></div>
      </div>
      <input type="file" id="file" accept=".xlsx,.xls,.csv,.tsv">
    </div>

    <!-- options -->
    <div class="opts">
      <div class="opt">
        <label>CMS pulls</label>
        <span class="seg" id="scale">
          <button data-v="auto" class="on">Auto</button>
          <button data-v="national">National</button>
          <button data-v="regional">Regional</button>
        </span>
      </div>
      <div class="opt"><label>Top codes</label>
        <input type="number" id="top" value="40" min="0" step="10" title="Cap CMS work to the N highest-blank-dollar HCPCS (0 = no cap)">
      </div>
      <label class="check"><input type="checkbox" id="enrich" checked> Enrich</label>
      <label class="check"><input type="checkbox" id="b340" checked> 340B</label>
      <label class="check"><input type="checkbox" id="entity" checked> Operators</label>
    </div>

    <!-- v42: selectable single-purpose data-quality fixes -->
    <div class="opt" style="margin-top:6px">
      <label style="cursor:pointer"><input type="checkbox" id="fixmode"> Quick fixes mode (run only the checks you pick, one pass, no full pipeline)</label>
    </div>
    <div id="fixpanel" style="display:none;border:1px solid var(--line);border-radius:10px;padding:12px;margin-top:8px">
      <div id="fixlist" style="display:grid;grid-template-columns:1fr 1fr;gap:6px 18px"></div>
      <div style="margin-top:10px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        <button class="run" id="preview" style="background:transparent;color:var(--teal-deep);border:1px solid var(--line)">Check fixability</button>
        <button class="run" id="runfix">Run selected fixes</button>
        <span class="hint" id="fixhint"></span>
      </div>
      <div id="fixout" class="mono" style="margin-top:10px;font-size:13px;white-space:pre-wrap"></div>
    </div>

    <!-- action -->
    <div class="act">
      <button class="run" id="run" disabled>Recover &amp; enrich</button>
      <span class="hint" id="hint">Everything runs locally on your machine.</span>
    </div>

    <!-- live pipeline -->
    <div class="run-panel" id="runPanel">
      <div class="bar"><i id="fill"></i></div>
      <div class="stage" data-lo="0"    data-hi="0.10"><span class="dot"></span><span class="lbl">Read &amp; repair fields</span><span class="num mono">01</span></div>
      <div class="stage" data-lo="0.10" data-hi="0.35"><span class="dot"></span><span class="lbl">Route drugs &amp; pull live CMS pools</span><span class="num mono">02</span></div>
      <div class="stage" data-lo="0.35" data-hi="0.66"><span class="dot"></span><span class="lbl">Recover missing billing NPIs</span><span class="num mono">03</span></div>
      <div class="stage" data-lo="0.66" data-hi="0.88"><span class="dot"></span><span class="lbl">Enrich — NPPES directory &amp; drug reference</span><span class="num mono">04</span></div>
      <div class="stage" data-lo="0.88" data-hi="0.93"><span class="dot"></span><span class="lbl">Resolve 340B &amp; size gross-up</span><span class="num mono">05</span></div>
      <div class="stage" data-lo="0.93" data-hi="1.00"><span class="dot"></span><span class="lbl">Write workbook</span><span class="num mono">06</span></div>
      <div class="live mono" id="live"></div>
    </div>

    <!-- error -->
    <div class="err" id="err"></div>

    <!-- result -->
    <div class="result" id="result">
      <div class="grid" id="stats"></div>
      <a class="dl" id="dl" download>Download workbook</a>
      <button class="run" id="again" style="background:transparent;color:var(--teal-deep);border:1px solid var(--line);margin-left:10px">Process another file</button>
    </div>
  </div>

  <footer>
    Medicare reimbursement is sized, not guessed — read the Caveats tab.<br>
    Files never leave this machine.
  </footer>
</div>

<script>
const $ = s => document.querySelector(s);
let file = null, scale = "auto", jobId = null, poll = null;

const tray=$("#tray"), slot=$("#slot"), input=$("#file");
slot.addEventListener("click", ()=> input.click());
input.addEventListener("change", e => setFile(e.target.files[0]));
["dragenter","dragover"].forEach(ev=> tray.addEventListener(ev, e=>{e.preventDefault(); tray.classList.add("drag");}));
["dragleave","drop"].forEach(ev=> tray.addEventListener(ev, e=>{e.preventDefault(); if(ev==="drop"||e.target===tray) tray.classList.remove("drag");}));
tray.addEventListener("drop", e => { if(e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); });

function setFile(f){
  if(!f) return;
  file = f;
  $("#fname").textContent = f.name + "  ·  " + (f.size/1024).toFixed(0) + " KB";
  $("#run").disabled = false;
  $("#result").classList.remove("show"); $("#err").classList.remove("show");
}

document.querySelectorAll("#scale button").forEach(b=>{
  b.addEventListener("click", ()=>{
    document.querySelectorAll("#scale button").forEach(x=>x.classList.remove("on"));
    b.classList.add("on"); scale = b.dataset.v;
  });
});

$("#run").addEventListener("click", start);
$("#again").addEventListener("click", reset);

function start(){
  if(!file) return;
  $("#run").disabled = true; $("#hint").textContent = "Working — this can take a minute on a large file.";
  $("#runPanel").classList.add("show"); $("#result").classList.remove("show"); $("#err").classList.remove("show");
  resetStages();
  const qs = new URLSearchParams({
    scale, top: $("#top").value || "0",
    enrich: $("#enrich").checked?1:0, b340: $("#b340").checked?1:0, entity: $("#entity").checked?1:0
  });
  fetch("/upload?"+qs.toString(), {
    method:"POST", headers:{"X-Filename": file.name}, body: file
  }).then(r=>r.json()).then(j=>{
    jobId = j.job_id;
    poll = setInterval(check, 600);
  }).catch(e=> fail("Could not start: "+e));
}

function check(){
  fetch("/progress/"+jobId).then(r=>r.json()).then(j=>{
    setProgress(j.frac, j.msg);
    if(j.error){ clearInterval(poll); fail(j.error); }
    else if(j.done){ clearInterval(poll); finish(j); }
  }).catch(()=>{});
}

function setProgress(frac, msg){
  $("#fill").style.width = Math.max(2, frac*100) + "%";
  $("#live").textContent = msg || "";
  document.querySelectorAll(".stage").forEach(s=>{
    const lo=+s.dataset.lo, hi=+s.dataset.hi;
    s.classList.toggle("done", frac>=hi-0.0001);
    s.classList.toggle("active", frac>=lo && frac<hi-0.0001);
  });
}
function resetStages(){ setProgress(0,""); document.querySelectorAll(".stage").forEach(s=>s.classList.remove("done","active")); }

function finish(j){
  setProgress(1, "Done");
  $("#hint").textContent = "Done.";
  const s = j.stats || {};
  if (s.note){
    $("#err").textContent = s.note; $("#err").classList.add("show");
  }
  const cells = [
    ["Rows", fmt(s.rows_total)],
    ["Repaired", fmt(s.rows_with_repairs)+`<small> / ${fmt(s.field_repairs_total)} fixes</small>`],
    ["Blanks recovered", fmt(s.rows_recovered)+`<small> / ${fmt(s.rows_blank_billing)} (${s.pct_blanks_recovered??0}%)</small>`],
    ["Point attribution", fmt(s.rows_point_attribution)],
    ["Providers enriched", fmt(s.providers_enriched)+`<small> / ${fmt(s.providers_found_in_nppes)} in NPPES</small>`],
    ["Medicare-enrolled", fmt(s.providers_medicare_enrolled)+`<small> PECOS-verified</small>`],
    ["Referrers verified", fmt(s.referring_npis_verified)+`<small> Order &amp; Referring</small>`],
    ["340B signal", fmt(s.providers_340b_signal)+`<small> sig · ${fmt(s.providers_340b_registered)} reg</small>`],
    ["Honest top-1", (s.honest_top1!=null? (s.honest_top1*100).toFixed(1)+"%":"—")],
    ["Gross-up rows", fmt(s.rows_grossup)],
  ];
  $("#stats").innerHTML = cells.map(c=>`<div class="cell"><div class="k">${c[0]}</div><div class="v mono">${c[1]}</div></div>`).join("");
  const a=$("#dl"); a.href="/download/"+jobId; a.setAttribute("download", j.out_name||"recovered.xlsx");
  $("#result").classList.add("show");
  $("#run").disabled = false;
}

function reset(){
  file = null; jobId = null;
  $("#file").value = "";
  $("#fname").textContent = "";
  $("#run").disabled = true;
  $("#hint").textContent = "Everything runs locally on your machine.";
  $("#runPanel").classList.remove("show");
  $("#result").classList.remove("show");
  $("#err").classList.remove("show");
  resetStages();
}

function fail(m){
  $("#err").textContent = m; $("#err").classList.add("show");
  $("#hint").textContent = "Stopped."; $("#run").disabled = false;
  $("#runPanel").classList.remove("show");
}
function fmt(n){ return (n==null)?"—":Number(n).toLocaleString(); }

// v42: Quick fixes panel
$("#fixmode").addEventListener("change", e=>{
  $("#fixpanel").style.display = e.target.checked ? "block" : "none";
  $("#run").style.display = e.target.checked ? "none" : "";
  if(e.target.checked && !window._fixLoaded){ loadFixCatalog(); window._fixLoaded = true; }
});
function loadFixCatalog(){
  fetch("/fixes").then(r=>r.json()).then(j=>{
    const el = $("#fixlist"); el.innerHTML = "";
    j.catalog.forEach(g=>{
      const h = document.createElement("div");
      h.style.cssText = "grid-column:1/-1;font-weight:600;color:var(--teal-deep);margin-top:6px";
      h.textContent = g.group_label; el.appendChild(h);
      g.fixes.forEach(fx=>{
        const lab = document.createElement("label");
        lab.style.cssText = "display:flex;gap:6px;align-items:flex-start;font-size:13px";
        lab.innerHTML = '<input type="checkbox" class="fixchk" value="'+fx.key+'"><span><b>'+fx.label+'</b><br><span style="color:#667">'+fx.touches+'</span></span>';
        el.appendChild(lab);
      });
    });
  });
}
function pickedFixes(){ return [...document.querySelectorAll(".fixchk:checked")].map(c=>c.value); }
$("#preview").addEventListener("click", ()=>{
  if(!file){ $("#fixhint").textContent = "Choose a file first."; return; }
  $("#fixhint").textContent = "Profiling…"; $("#fixout").textContent = "";
  fetch("/fixability", {method:"POST", headers:{"X-Filename":file.name}, body:file})
    .then(r=>r.json()).then(j=>{
      $("#fixhint").textContent = j.note || "";
      $("#fixout").textContent = j.rows.map(r=>"  "+r.status.padEnd(12)+" "+r.fix).join("\n");
    }).catch(e=> $("#fixhint").textContent = "Error: "+e);
});
$("#runfix").addEventListener("click", ()=>{
  const keys = pickedFixes();
  if(!file){ $("#fixhint").textContent = "Choose a file first."; return; }
  if(!keys.length){ $("#fixhint").textContent = "Check at least one fix."; return; }
  $("#fixhint").textContent = "Running "+keys.length+" fix(es)…"; $("#fixout").textContent = "";
  fetch("/runfixes?fix="+keys.join(","), {method:"POST", headers:{"X-Filename":file.name}, body:file})
    .then(r=>r.json()).then(j=>{
      $("#fixhint").innerHTML = 'Done. <a href="'+j.download+'" style="color:var(--teal-deep)">Download '+j.out_name+'</a>';
      $("#fixout").textContent = j.summary.map(s=>"  "+s.key+": "+s.rows+" rows  "+s.note).join("\n");
    }).catch(e=> $("#fixhint").textContent = "Error: "+e);
});
</script>
</body>
</html>"""


# -------------------------------------------------------------- the server ----
def _run_job(job_id, src_path, opts):
    job = JOBS[job_id]

    def cb(msg, frac):
        job["msg"] = msg
        job["frac"] = float(frac)

    try:
        national = {"auto": None, "national": True, "regional": False}.get(opts.get("scale"), None)
        top = int(opts.get("top") or 0) or None
        result = run_pipeline(
            str(src_path), top_hcpcs=top, national=national,
            do_enrich=opts.get("enrich", True), do_340b=opts.get("b340", True),
            do_entity=opts.get("entity", True), progress=cb)
        out_name = Path(src_path).stem.replace(" ", "_") + "_recovered.xlsx"
        out_path = WORKDIR / f"{job_id}_{out_name}"
        write_report(result, str(out_path))
        job["out_path"] = str(out_path)
        job["out_name"] = out_name
        job["stats"] = result.stats
        job["frac"] = 1.0
        job["msg"] = "Done"
        job["done"] = True
    except Exception as e:
        traceback.print_exc()
        job["error"] = f"{type(e).__name__}: {e}"
        job["done"] = True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # quiet

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if path == "/fixes":
            # v42: the selectable-fix catalog, for a checkbox UI
            from npi_recovery import registry as R
            cat = []
            for grp in R.GROUP_ORDER:
                items = [{"key": m.key, "label": m.label, "kahn": m.kahn,
                          "requires": list(m.requires), "optional": list(m.optional),
                          "touches": m.touches, "repairs": m.fixes}
                         for m in R.REGISTRY if m.group == grp]
                cat.append({"group": grp, "group_label": R.GROUP_LABELS[grp], "fixes": items})
            return self._send(200, json.dumps({"catalog": cat}))
        if path.startswith("/progress/"):
            job = JOBS.get(path.rsplit("/", 1)[-1])
            if not job:
                return self._send(404, json.dumps({"error": "unknown job"}))
            return self._send(200, json.dumps({
                "frac": job["frac"], "msg": job["msg"], "done": job["done"],
                "error": job.get("error"), "stats": job.get("stats"),
                "out_name": job.get("out_name")}))
        if path.startswith("/download/"):
            job = JOBS.get(path.rsplit("/", 1)[-1])
            if not job or not job.get("out_path"):
                return self._send(404, "not ready", "text/plain")
            data = Path(job["out_path"]).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type",
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition",
                             f'attachment; filename="{job.get("out_name","recovered.xlsx")}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        return self._send(404, "not found", "text/plain")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/fixability", "/runfixes"):
            return self._handle_fixes(parsed)
        if parsed.path != "/upload":
            return self._send(404, "not found", "text/plain")
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return self._send(400, json.dumps({"error": "empty upload"}))
        name = self.headers.get("X-Filename", "claims.xlsx")
        safe = "".join(c for c in name if c.isalnum() or c in "._- ").strip() or "claims.xlsx"
        q = parse_qs(parsed.query)
        opts = {
            "scale": (q.get("scale", ["auto"])[0]),
            "top": (q.get("top", ["40"])[0]),
            "enrich": q.get("enrich", ["1"])[0] == "1",
            "b340": q.get("b340", ["1"])[0] == "1",
            "entity": q.get("entity", ["1"])[0] == "1",
        }
        job_id = uuid.uuid4().hex[:12]
        src = WORKDIR / f"{job_id}_{safe}"
        src.write_bytes(raw)
        JOBS[job_id] = {"frac": 0.0, "msg": "Queued", "done": False, "error": None,
                        "name": safe}
        threading.Thread(target=_run_job, args=(job_id, src, opts), daemon=True).start()
        return self._send(200, json.dumps({"job_id": job_id}))

    def _handle_fixes(self, parsed):
        """v42: /fixability profiles an upload and returns the manifest; /runfixes
        runs the selected fix keys and returns a downloadable focused workbook.
        Both read the raw upload body (same convention as /upload)."""
        from npi_recovery import registry as R, schema, focused_report
        import pandas as pd
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return self._send(400, json.dumps({"error": "empty upload"}))
        name = self.headers.get("X-Filename", "claims.xlsx")
        safe = "".join(c for c in name if c.isalnum() or c in "._- ").strip() or "claims.xlsx"
        job_id = uuid.uuid4().hex[:12]
        src = WORKDIR / f"{job_id}_{safe}"
        src.write_bytes(raw)
        # read + standardize (schema-adaptive)
        suffix = Path(safe).suffix.lower()
        if suffix in (".xlsx", ".xlsm", ".xls"):
            df = pd.read_excel(str(src), dtype=str)
        elif suffix == ".parquet":
            df = pd.read_parquet(str(src))
        else:
            from npi_recovery import preflight
            res = preflight.robust_read(str(src))
            df = res[1] if isinstance(res, tuple) else res
        mapping, _rep = schema.detect_columns(df)
        std = schema.standardize(df, mapping)
        mapping = {k: k for k, v in mapping.items() if v is not None and k in std.columns}
        manifest = R.fixability(std, mapping)
        coverage = R.field_coverage(std, mapping)
        man_rows = manifest[["key", "fix", "group", "kahn_category", "status",
                             "missing_required", "missing_for_verdict"]].to_dict("records")
        if parsed.path == "/fixability":
            return self._send(200, json.dumps({
                "rows": man_rows, "note": manifest.attrs.get("note", ""),
                "input_rows": len(std),
                "fields_delivered": int(coverage["delivered"].sum()),
                "fields_total": len(coverage)}))
        # /runfixes
        q = parse_qs(parsed.query)
        keys = [k for k in q.get("fix", [""])[0].split(",") if k]
        ctx = {"ref_dir": os.path.join(os.path.dirname(schema.__file__), "reference"),
               "mapping": mapping}
        results = R.run_selected(std, keys, ctx)
        out_path = WORKDIR / f"{job_id}_fixes.xlsx"
        focused_report.write_focused(str(out_path), std, manifest, results, safe, coverage=coverage)
        summary = []
        for k in keys:
            r = results.get(k, pd.DataFrame())
            note = (r.attrs.get("note") if hasattr(r, "attrs") and r.attrs.get("note")
                    else (r["note"].iloc[0] if "note" in getattr(r, "columns", []) and len(r) else ""))
            summary.append({"key": k, "rows": len(r), "note": note})
        JOBS[job_id] = {"out_path": str(out_path), "out_name": f"{Path(safe).stem}_fixes.xlsx",
                        "done": True}
        return self._send(200, json.dumps({
            "job_id": job_id, "summary": summary,
            "download": f"/download/{job_id}", "out_name": f"{Path(safe).stem}_fixes.xlsx"}))


def serve(port=8765, open_browser=True):
    addr = ("127.0.0.1", port)
    httpd = ThreadingHTTPServer(addr, Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"\n  Claims Intake is running at  {url}")
    print("  Drag a claims file onto the page. Press Ctrl+C to stop.\n")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
        httpd.shutdown()
