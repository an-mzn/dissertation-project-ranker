"""Display the active notebook ranker in a local browser window."""

import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dissertation Project Ranker</title>
<style>
:root{color-scheme:light dark;--background:#f5f5f5;--text:#222;--surface:#fff;
--border:#ccc;--divider:#ddd;--choice:#222;--choice-text:#fff;--focus:#555}
@media(prefers-color-scheme:dark){:root{--background:#0a0a0a;--text:#ddd;
--surface:#000;--border:#333;--divider:#222;--choice:#ddd;--choice-text:#000;--focus:#aaa}}
*{box-sizing:border-box}body{margin:0;background:var(--background);color:var(--text);
font:16px/1.5 system-ui,sans-serif}main{width:100%;height:100dvh;
padding:clamp(12px,2vw,24px);display:flex;flex-direction:column;gap:12px;overflow:hidden}
header{flex-shrink:0;background:var(--background);padding:12px 0;
border-bottom:1px solid var(--divider)}h1{font-size:24px;margin:0 0 8px}
nav{display:flex;gap:10px;flex-wrap:wrap}button{font:inherit;padding:10px 20px;
border:1px solid var(--border);border-radius:8px;cursor:pointer;
background:var(--surface);color:var(--text)}
.top-controls{align-items:center;justify-content:space-between}
.bottom-controls{flex-shrink:0;display:flex;justify-content:center;align-items:center;gap:10px}
.bottom-controls .arrow{font-size:24px;line-height:1;padding:10px 18px}
button.choice{background:var(--choice);color:var(--choice-text);border-color:var(--choice);
transition:background-color 220ms ease,color 220ms ease}
button.choice:hover:not(:disabled){background:var(--surface);color:var(--text)}
button:disabled{opacity:.45;cursor:default}button:focus-visible{outline:3px solid var(--focus)}
section{background:var(--surface)}#error{color:var(--text);font-weight:600}
#options{flex:1;min-height:0}
#options>div{height:100%;margin-top:0!important;flex-wrap:nowrap!important}
#options section{display:flex;flex-direction:column;min-height:0;height:100%;overflow:hidden}
#options section[role="button"]{cursor:pointer;transition:box-shadow 220ms ease}
#options section[role="button"]:hover:not([aria-disabled="true"]),
#options section[role="button"]:focus-visible{box-shadow:inset 0 0 0 2px var(--choice);outline:none}
#options section[aria-disabled="true"]{cursor:default}
#options section>[aria-label="Project description"]{flex:1;min-height:0;max-height:none!important}
#options section>div:not([aria-label]),#options section>h3,#options section>p{flex-shrink:0}
#ranking:empty{display:none}#ranking{flex-shrink:0;max-height:25dvh;overflow-y:auto}
footer{flex-shrink:0;display:flex;justify-content:space-between;align-items:baseline;
gap:12px;flex-wrap:wrap;font-size:13px}
footer p{margin:0}#save-status{margin-left:auto;text-align:right}
#save-status p{font-size:inherit!important;margin:0!important}
@media(max-width:700px){#options>div{flex-direction:column}
#options section{flex:1 1 0!important}#options section h3{font-size:16px!important;margin:4px 0!important}
#options section{padding:12px!important}}
@media(prefers-reduced-motion:reduce){button.choice,#options section{transition:none}}
</style></head><body><main>
<header><h1>Dissertation Project Ranker</h1><div id="status"></div>
<nav class="top-controls">
<button data-action="rank">Show top 20</button>
<button data-action="stop">Stop</button></nav><div id="error" role="alert"></div>
</header><div id="options"></div><div id="ranking"></div>
<nav class="bottom-controls" aria-label="Comparison controls">
<button class="arrow" data-action="back" aria-label="Back: undo last choice" title="Back: undo last choice">←</button>
<button class="choice" data-action="both">Both</button>
<button class="arrow" data-action="skip" aria-label="Skip this comparison" title="Skip this comparison">→</button>
</nav>
<footer><p>Keep the notebook kernel running. Closing this window does not reset your scores.</p>
<div id="save-status" role="status"></div></footer>
</main><script>
let busy=false, stopped=true, pointerStart=null;
const options=document.getElementById('options');
function decorateCards(){
  options.querySelectorAll('section').forEach((card,index)=>{
    card.dataset.action=index===0?'a':'b';
    card.setAttribute('role','button');
    card.tabIndex=stopped?-1:0;
    const title=card.querySelector('h3');
    card.setAttribute('aria-label','Choose '+(index===0?'A':'B')+': '+title.textContent);
    card.setAttribute('aria-disabled',String(stopped||busy));
  });
}
options.addEventListener('pointerdown',event=>{
  pointerStart={x:event.clientX,y:event.clientY};
});
options.addEventListener('click',event=>{
  const card=event.target.closest('section[data-action]');
  if(!card||busy||stopped||event.detail>1)return;
  if(event.target.closest('a,button,input,textarea,select,summary'))return;
  const selection=window.getSelection();
  if(selection&&!selection.isCollapsed)return;
  if(pointerStart&&Math.hypot(event.clientX-pointerStart.x,event.clientY-pointerStart.y)>8)return;
  const description=event.target.closest('[aria-label="Project description"]');
  if(description){
    const bounds=description.getBoundingClientRect();
    if(event.clientX>=bounds.left+description.clientWidth)return;
  }
  update(card.dataset.action);
});
options.addEventListener('keydown',event=>{
  const card=event.target.closest('section[data-action]');
  if(card&&event.target===card&&!busy&&!stopped&&(event.key==='Enter'||event.key===' ')){
    event.preventDefault();
    if(!event.repeat)update(card.dataset.action);
  }
});
async function update(action){
  if(busy)return;busy=true;
  const buttons=[...document.querySelectorAll('button')];
  buttons.forEach(b=>b.disabled=true);
  try{
    const response=await fetch(location.pathname+(action?'action':'state'),{
      method:action?'POST':'GET',
      headers:action?{'Content-Type':'application/json'}:{},
      body:action?JSON.stringify({action}):undefined
    });
    if(!response.ok)throw Error('The notebook connection failed.');
    const state=await response.json();
    stopped=state.stopped;
    for(const key of ['status','options','ranking'])document.getElementById(key).innerHTML=state[key];
    document.getElementById('save-status').innerHTML=state.save_status;
    document.querySelector('[data-action="rank"]').textContent=state.ranking?'Hide top 20':'Show top 20';
    document.querySelector('[data-action="stop"]').textContent=state.stopped?'Resume':'Stop';
    buttons.forEach(b=>b.disabled=b.dataset.action==='back'?!state.can_back:
      b.dataset.action==='stop'?state.complete:
      state.stopped&&b.dataset.action!=='rank');
    document.getElementById('error').textContent='';
  }catch(error){
    document.getElementById('error').textContent=error.message+' Keep the kernel running and reopen the window from the notebook.';
    buttons.forEach(b=>b.disabled=false);
  }finally{busy=false;decorateCards();}
}
document.querySelectorAll('button').forEach(b=>b.onclick=()=>update(b.dataset.action));
update();
</script></body></html>"""


class RankerWindow:
    def __init__(self, ranker):
        self.ranker = ranker
        self.lock = threading.Lock()
        self.prefix = f"/{secrets.token_urlsafe(24)}/"
        window = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def respond(self, status, body, content_type):
                payload = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):
                if self.path == window.prefix:
                    self.respond(200, PAGE, "text/html; charset=utf-8")
                elif self.path == window.prefix + "state":
                    with window.lock:
                        state = window.state()
                    self.respond(200, json.dumps(state), "application/json")
                else:
                    self.respond(404, "Not found", "text/plain")

            def do_POST(self):
                if self.path != window.prefix + "action":
                    self.respond(404, "Not found", "text/plain")
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 1024:
                        raise ValueError("Invalid request size")
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload, dict):
                        raise ValueError("Invalid action payload")
                    action = payload["action"]
                    with window.lock:
                        if action == "a":
                            window.ranker.choose(0)
                        elif action == "b":
                            window.ranker.choose(1)
                        elif action == "both":
                            window.ranker.choose(2)
                        elif action == "back":
                            window.ranker.back()
                        elif action == "skip":
                            window.ranker.skip()
                        elif action == "rank":
                            window.ranker.toggle_ranking()
                        elif action == "stop":
                            window.ranker.toggle_stopped()
                        else:
                            raise ValueError("Unknown action")
                        state = window.state()
                except (ValueError, KeyError, TypeError):
                    self.respond(400, "Invalid action", "text/plain")
                    return
                self.respond(200, json.dumps(state), "application/json")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}{self.prefix}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def state(self):
        return {
            "status": self.ranker.status.value,
            "save_status": self.ranker.save_status.value,
            "options": self.ranker.options.value,
            "ranking": self.ranker.ranking.value,
            "stopped": self.ranker.choose_a.disabled,
            "can_back": bool(getattr(self.ranker, "history", [])),
            "complete": self.ranker.position >= len(self.ranker.comparisons),
        }

    def open(self):
        webbrowser.open(self.url, new=1)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
