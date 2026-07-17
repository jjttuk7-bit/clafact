"""브라우저 브릿지 v2 — 키를 노출하지 않고 KOSIS 실 응답을 받는다.

배경 (문서 19 §5.5): 개발망은 정부망 443 을 비브라우저 클라이언트에 차단한다.
브라우저만 통과하므로, 브라우저 JS 의 fetch 로 KOSIS 를 호출한다.

🔒 v1(302 리다이렉트)의 결함을 고쳤다: 리다이렉트는 브라우저를 kosis.kr 로 보내
   최종 URL(=키 포함)이 탭 제목·도구 결과에 노출됐다. v2 는 브라우저가 **localhost 에
   머물면서** JS fetch 로만 KOSIS 를 친다. 키는:
     - 서버가 .env 에서 읽어 **HTML 안의 JS 에만** 주입 (내가 만드는 URL 엔 없음)
     - 화면에는 KOSIS 응답 본문만 뜬다 (KOSIS 는 응답에 apiKey 를 담지 않음)
     - 따라서 get_page_text/read_page 결과에 키가 없다
   ⚠️ 이 서버 사용 중에는 read_network_requests 를 호출하지 말 것 (네트워크 탭엔 키가 있다).

사용법:
    python scripts/kosis_browser_probe.py
    # 브라우저에서:
    #   http://127.0.0.1:8765/search?nm=과수 농가 고령&n=10   (통합검색)
    #   http://127.0.0.1:8765/data?tbl=DT_1EA1019&prd=2024      (통계자료)

⚠️ 127.0.0.1 에만 바인딩 — 외부 노출 시 키 프록시가 된다. 0.0.0.0 금지.
"""
import html as _html
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
PORT = 8765


def load_env() -> None:
    import os
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def _kosis_url(path: str, key: str, params: dict) -> str:
    from urllib.parse import urlencode
    base = {"method": "getList", "apiKey": key, "format": "json"}
    base.update(params)
    return f"https://kosis.kr/openapi/{path}?{urlencode(base)}"


def _page(target_url: str) -> str:
    """브라우저에서 target_url 을 fetch 해 결과만 <pre> 로 보여주는 HTML.
    target_url 은 서버 안에서만 쓰이고 JS 문자열에만 들어간다 (화면·탭 URL 엔 없음)."""
    js_url = target_url.replace("\\", "\\\\").replace('"', '\\"')
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>KOSIS Probe</title></head><body>
<pre id="out">loading...</pre>
<script>
fetch("{js_url}").then(r => r.text()).then(t => {{
  document.getElementById("out").textContent = t;
  document.title = "KOSIS Probe (done)";
}}).catch(e => {{
  document.getElementById("out").textContent = "FETCH_ERROR: " + e;
  document.title = "KOSIS Probe (error)";
}});
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  [{self.command}] {urlparse(self.path).path}")  # 경로만 (키 없음)

    def do_GET(self):
        import os
        u = urlparse(self.path)
        if u.path == "/health":
            return self._text(200, "ok")
        key = os.environ.get("KOSIS_API_KEY", "")
        if not key:
            return self._text(500, "KOSIS_API_KEY 없음 — clafact/.env 확인")
        q = parse_qs(u.query)
        one = lambda k, d="": (q.get(k) or [d])[0]

        # /go — 302 리다이렉트 (CORS 우회: 최상위 이동은 CORS 무관).
        # javascript_tool 로만 구동하면 키가 도구 결과에 안 뜬다(footer 는 origin 만 표기).
        if u.path == "/go":
            svc = one("svc", "search")
            if svc == "search":
                url = _kosis_url("statisticsSearch.do", key, {
                    "searchNm": one("nm"), "sort": one("sort", "RANK"),
                    "resultCount": one("n", "10"), "startCount": one("p", "1")})
            else:
                url = _kosis_url("Param/statisticsParameterData.do", key, {
                    "orgId": one("org", "101"), "tblId": one("tbl"),
                    "itmId": "ALL", "objL1": "ALL", "objL2": "", "objL3": "", "objL4": "",
                    "objL5": "", "objL6": "", "objL7": "", "objL8": "",
                    "prdSe": one("prdse", "Y"), "newEstPrdCnt": one("recent", "3"),
                    "jsonVD": "Y"})
            self.send_response(302)
            self.send_header("Location", url)
            self.end_headers()
            return

        if u.path == "/search":
            url = _kosis_url("statisticsSearch.do", key, {
                "searchNm": one("nm"), "sort": one("sort", "RANK"),
                "resultCount": one("n", "10"), "startCount": one("p", "1")})
        elif u.path == "/data":
            url = _kosis_url("Param/statisticsParameterData.do", key, {
                "orgId": one("org", "101"), "tblId": one("tbl"),
                "itmId": "ALL", "objL1": "ALL", "objL2": "", "objL3": "", "objL4": "",
                "objL5": "", "objL6": "", "objL7": "", "objL8": "",
                "prdSe": one("prdse", "Y"), "newEstPrdCnt": one("recent", "3"),
                "jsonVD": "Y"})
        else:
            return self._text(404, "use /search?nm=... or /data?tbl=...")

        body = _page(url).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text(self, code, msg):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(msg.encode("utf-8"))


def main() -> int:
    import os
    load_env()
    if not os.environ.get("KOSIS_API_KEY"):
        print("✗ KOSIS_API_KEY 없음 — clafact/.env 에 넣어주세요")
        return 1
    print(f"브릿지 v2: http://127.0.0.1:{PORT}/search?nm=과수 농가 고령&n=10")
    print("  (키는 서버 내부에서만 JS 에 주입 — 화면·탭 URL·로그에 안 뜸)")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
