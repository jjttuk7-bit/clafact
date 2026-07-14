"""ClaFact MVP 데모 서버 — 표준 라이브러리만 사용 (API Key·외부 패키지 불필요).

실행: python scripts/demo_server.py  →  http://localhost:8765
FastAPI 전환은 5주차 서비스화 단계에서 (문서 06). 지금은 "보여주는 것"이 목적.
"""
import json
import sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clafact.kosis import FixtureKosisClient
from clafact.pipeline.retrieve import StatIndex
from clafact.pipeline.run import verify_article

ROOT = Path(__file__).resolve().parents[1]
INDEX = StatIndex(ROOT / "data/samples/kosis/tables_meta.json")
CLIENT = FixtureKosisClient(ROOT / "data/samples/kosis")

SAMPLES = [
    {"title": "과수 농가 고령화 (파생 계산 데모)", "date": "2025-03-14",
     "text": "농가 고령화가 이어지면서 올해 과일 재배면적이 1% 줄었다. 2024년 국내 과수 농가의 65세 이상 비율은 64.2%로 나타났다."},
    {"title": "실업률 왜곡 (불일치 데모)", "date": "2025-06-20",
     "text": "올해 실업률이 10%에 달했다. 전문가들은 경기 둔화의 영향이라고 분석했다. 경제 상황이 크게 악화되었다."},
    {"title": "1인 가구·출생아 (임계·환산 데모)", "date": "2025-06-02",
     "text": "서울의 1인 가구는 150만 가구를 넘어섰다. 지난해 출생아 수는 23만 명으로 역대 최저를 기록했다. 내년 경제성장률은 3%에 이를 전망이다."},
    {"title": "농가 증감률 (방향 검증 데모)", "date": "2025-04-10",
     "text": "지난해 논벼 농가는 전년보다 4.9% 감소했다. 지난해 과수 농가는 2% 감소했다. 지난해 과일 재배면적이 1% 줄었다."},
]

HTML = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<title>ClaFact — 뉴스 수치 검증 MVP</title>
<style>
 body{font-family:'Malgun Gothic',sans-serif;max-width:860px;margin:24px auto;padding:0 16px;color:#262626;background:#fafbfd}
 h1{color:#1F3864;margin-bottom:2px} .sub{color:#44546A;font-style:italic;margin-top:0}
 textarea{width:100%;height:110px;padding:10px;border:1px solid #BFC9D9;border-radius:8px;font-size:14px;box-sizing:border-box}
 input[type=date]{padding:8px;border:1px solid #BFC9D9;border-radius:8px}
 button{background:#1F3864;color:#fff;border:0;padding:10px 22px;border-radius:8px;font-size:15px;cursor:pointer;font-weight:bold}
 button:hover{background:#2E4A7A} .samples button{background:#EAF1F8;color:#1F3864;font-weight:normal;padding:6px 12px;font-size:13px;margin-right:6px}
 .card{border:1px solid #DDE5EF;border-left:6px solid #999;border-radius:10px;background:#fff;padding:14px 16px;margin:12px 0;box-shadow:0 1px 3px rgba(31,56,100,.06)}
 .card.match{border-left-color:#2E8B57}.card.mismatch{border-left-color:#C0392B}.card.unverifiable{border-left-color:#8A8F98}.card.not_claim{opacity:.55}
 .badge{display:inline-block;padding:3px 12px;border-radius:99px;color:#fff;font-size:13px;font-weight:bold;margin-right:8px}
 .b-match{background:#2E8B57}.b-mismatch{background:#C0392B}.b-unverifiable{background:#8A8F98}.b-not_claim{background:#C5CBD4}
 .chip{display:inline-block;padding:2px 10px;border-radius:99px;background:#EAF1F8;color:#1F3864;font-size:12px;margin-right:6px}
 .chip.low{background:#FDF3E7;color:#C55A11;font-weight:bold}
 .sent{font-size:15px;margin:8px 0 6px;font-weight:bold}
 .expl{font-size:13px;color:#44546A;background:#F6F8FB;border-radius:8px;padding:10px;margin-top:8px;line-height:1.6}
 .meta{font-size:12.5px;color:#5A6B85}
 .foot{margin-top:28px;font-size:12px;color:#8A8F98;text-align:center}
 .stat{background:#EAF1F8;border-radius:8px;padding:8px 14px;display:inline-block;margin-top:10px;font-size:13px;color:#1F3864}
</style></head><body>
<h1>ClaFact <span style="font-size:16px;color:#C55A11">MVP DEMO</span></h1>
<p class="sub">뉴스 속 수치 주장을 공식 통계로 검증합니다 — 오프라인 데모 (API Key 불필요, 판정은 결정적 로직)</p>
<div class="samples" id="samples"><b style="font-size:13px">샘플: </b></div><br>
<textarea id="text" placeholder="기사 본문을 붙여넣으세요..."></textarea><br><br>
<label>기사 작성일 <input type="date" id="date" value="2025-07-13"></label>
&nbsp;<button onclick="verify()">검증하기</button>
<div id="out"></div>
<p class="foot">ClaBi × AIFFELTHON | 근거 없으면 판정하지 않습니다 (판단불가 우선) | 최종 판단은 검증자 리뷰로 확정</p>
<script>
const SAMPLES = __SAMPLES__;
const sdiv = document.getElementById('samples');
SAMPLES.forEach((s,i)=>{const b=document.createElement('button');b.textContent=s.title;
 b.onclick=()=>{document.getElementById('text').value=s.text;document.getElementById('date').value=s.date;verify();};sdiv.appendChild(b);});
const KO={match:'일치',mismatch:'불일치',unverifiable:'판단불가',not_claim:'주장 아님'};
async function verify(){
 const text=document.getElementById('text').value, date=document.getElementById('date').value;
 if(!text.trim())return;
 const out=document.getElementById('out'); out.innerHTML='<p>검증 중...</p>';
 const res=await fetch('/api/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,date})});
 const data=await res.json();
 const claims=data.results.filter(r=>r.label!=='not_claim');
 let html=`<div class="stat">문장 ${data.results.length}개 · 검증 대상 주장 ${claims.length}개 · 일치 ${claims.filter(r=>r.label==='match').length} · 불일치 ${claims.filter(r=>r.label==='mismatch').length} · 판단불가 ${claims.filter(r=>r.label==='unverifiable').length}</div>`;
 for(const r of data.results){
  if(r.label==='not_claim') continue;
  html+=`<div class="card ${r.label}">
   <span class="badge b-${r.label}">${KO[r.label]}</span>`;
  if(r.confidence) html+=`<span class="chip ${r.confidence==='low'?'low':''}">신뢰도 ${r.confidence}${r.confidence==='low'?' — 리뷰 최우선':''}</span>`;
  if(r.period) html+=`<span class="chip">시점 ${r.period}</span>`;
  if(r.quantity) html+=`<span class="chip">주장 수치 ${r.quantity}</span>`;
  html+=`<div class="sent">${r.sentence}</div>`;
  if(r.evidence && r.evidence.tbl) html+=`<div class="meta">근거: ${r.evidence.tbl} → <b>${r.evidence.value}</b></div>`;
  html+=`<div class="expl">${r.explanation}</div>`;
  if(r.notes && r.notes.length) html+=`<div class="meta" style="margin-top:6px">⚠ ${r.notes.join(' / ')}</div>`;
  html+=`</div>`;
 }
 out.innerHTML=html;
}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # 조용한 로그
        print(f"[demo] {args[0] if args else ''}")

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        page = HTML.replace("__SAMPLES__", json.dumps(SAMPLES, ensure_ascii=False))
        self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")

    def do_POST(self):
        if self.path != "/api/verify":
            self._send(404, b"{}", "application/json")
            return
        length = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(length).decode("utf-8"))
        results = verify_article(req.get("text", ""), req.get("date", "2025-07-13"), INDEX, CLIENT)
        payload = {"results": [r.__dict__ for r in results]}
        self._send(200, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")


if __name__ == "__main__":
    import os
    # 클라우드 배포(Render/HF Spaces 등)는 PORT 환경변수 + 0.0.0.0 바인딩 필요
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8765))
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    print(f"ClaFact MVP demo → http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
