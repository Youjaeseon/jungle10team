# -*- coding: utf-8 -*-
"""와이어프레임 슬라이드 생성기.

화면 자체는 ../wireframe-v4-mvp.html 을 iframe으로 그대로 실어 온다.
그 파일이 이미 고딕체(IBM Plex Sans KR)를 쓰므로 화면을 다시 그릴 필요가 없고,
문구가 바뀌면 슬라이드가 자동으로 따라온다.
"""
import html, io, os

FH = 800        # iframe 원본 높이
CONTENT_W = 1184  # 슬라이드 안쪽 폭 (1280 - 좌우 여백 48*2)
STAGE_H = 551     # 프레임이 쓸 수 있는 최대 높이 (머리말·꼬리말 제외)
NOTES_W = 240

# (파일명, 제목, 부제, [ (화면 id, 캡션, 강조색, 버거 열기) ], [ (색, 메모) ])
SLIDES = [
    ("1_Main", "와이어프레임 — 로그인 · 회원가입",
     "가입은 페이지 이동, 로그인은 제자리 요청이다",
     [("login", "GET /login", "ssr", False),
      ("signup", "GET /signup", "ssr", False)],
     [("ssr", "회원가입 버튼은 페이지 이동이다. 주소가 <span class='mono'>/signup</span>으로 바뀐다."),
      ("ajax", "로그인 성공 → JWT 발급 → httpOnly 쿠키 저장 → 홈으로."),
      ("ajax", "기수는 칩 선택이고 검증이 없다. 신뢰 표시용 데이터일 뿐이다."),
      ("gray", "아이디 중복 확인은 등록 시 서버에서 한 번만 한다.")]),

    ("2_HomeFeed", "와이어프레임 — 홈 거래 피드",
     "카드 한 장이 곧 물건 상세 입구다",
     [("home", "GET /", "ssr", False)],
     [("ssr", "카드 클릭 = 물건 상세 화면으로 이동한다. 이 단계에서는 방을 만들지 않는다."),
      ("ssr", "본인 글 카드도 똑같이 상세로 간다. 화면 템플릿은 구매자와 하나다."),
      ("gray", "내 글을 모아 보는 자리는 사이드바의 거래내역(판매 탭)이다."),
      ("gray", "그리드는 <span class='mono'>row-cols-1 row-cols-md-3</span> 한 줄이다. 3열↔1열 반응형이 여기서 끝난다."),
      ("gray", "검색 · 필터 · 찜은 P2다. P0 시연에는 없어도 된다.")]),

    ("3_Sidebar", "와이어프레임 — 사이드바 (offcanvas)",
     "하단 탭 대신 웹 문법의 햄버거 메뉴",
     [("home", "햄버거 → offcanvas 5항목", "ssr", True)],
     [("ssr", "Bootstrap <span class='mono'>offcanvas</span> 컴포넌트를 그대로 쓴다. JS 번들이 필요하다."),
      ("ssr", "항목 5개로 고정한다 — Home · Community · 채팅목록 · 거래내역 · 로그아웃."),
      ("gray", "마이페이지는 만들지 않는다. 2박 3일 안에 쓸 화면이 아니다."),
      ("gray", "로그아웃은 JWT 쿠키를 지우는 것이 전부다.")]),

    ("4_ItemChat", "와이어프레임 — 물건 상세 → 1:1 채팅",
     "v5에서 상세와 채팅을 갈랐다",
     [("itemdetail", "GET /items/42", "ssr", False),
      ("chat", "GET /items/42/chat → 302 /chats/&lt;id&gt;", "ssr", False)],
     [("ssr", "상세는 사진 · 가격 · 상태 · 판매자를 보여주는 화면이다. 방을 만들지 않는다."),
      ("ssr", "'채팅 바로가기'가 방을 찾거나 만든다. 방은 (글, 구매자) 조합당 하나다."),
      ("ssr", "판매자가 누르면 그 글의 첫 방으로 간다. 채팅 하단 페이지네이션으로 구매자별 방을 오간다."),
      ("ajax", "폴링은 <span class='mono'>setInterval</span> 3초. 메시지 영역을 <span class='mono'>innerHTML</span>로 통째 교체한다."),
      ("ajax", "판매완료 처리는 판매자에게만 보인다. 버튼 숨김은 UI이고, 라우트 안의 검사가 보안이다.")]),

    ("5_WriteForm", "와이어프레임 — 거래 글 작성",
     "사진 1장 고정 · 유형 칩으로 필드가 갈린다",
     [("write", "GET /items/new → POST /items", "ssr", False)],
     [("ssr", "작성 → 등록 → 피드로 리다이렉트. 전부 SSR이다."),
      ("gray", "사진은 1장으로 고정한다. 다중 업로드를 빼면 난이도가 크게 떨어진다."),
      ("gray", "저장 위치는 <span class='mono'>static/uploads/</span>이고 파일명은 <span class='mono'>ObjectId.jpg</span>다."),
      ("ajax", "P0는 판매 유형만 만든다. 나눔 · 교환 필드 분기는 P1이다."),
      ("gray", "계좌번호 입력란은 없앴다. 개인 금융정보를 화면에 두지 않는다.")]),

    ("6_Community", "와이어프레임 — 커뮤니티 (P2)",
     "거래 CRUD를 한 번 더 베껴 쓰는 반복 연습",
     [("community", "GET /community", "ssr", False),
      ("post", "GET /community/7", "ssr", False)],
     [("ssr", "목록 → 글 → 작성 이동은 전부 SSR이다."),
      ("ajax", "댓글 등록만 AJAX다. 나머지는 페이지를 새로 받는다."),
      ("gray", "말머리는 질문 · 정보공유 두 개뿐이다."),
      ("gray", "P2라서 P0가 끝난 사람이 가져간다. 고정 담당이 없다.")]),
]

TPL = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>{title}</title>
<link rel="stylesheet" href="_slide.css">
<style>
.stage{{flex:1;display:flex;gap:26px;margin-top:18px;min-height:0}}
.frames{{flex:1;display:flex;gap:22px;align-items:flex-start;justify-content:center}}
.frame{{display:flex;flex-direction:column;align-items:center;gap:7px}}
.shell{{width:{fw}px;height:{fh}px;overflow:hidden;position:relative}}
.shell iframe{{width:{iw}px;height:{ih}px;border:0;position:absolute;top:0;left:0;
              transform:scale({scale});transform-origin:0 0}}
.frame .cap{{font-size:11.5px;color:var(--ink-2);font-family:"D2Coding","Noto Sans Mono CJK KR",monospace}}
.link{{align-self:center;width:34px;height:0;border-top:3px solid var(--ssr);margin-top:-24px}}

.notes{{width:240px;flex:none;display:flex;flex-direction:column;gap:12px;padding-top:2px}}
.notes h2{{font-size:11.5px;font-weight:700;letter-spacing:.08em;color:var(--ink-3)}}
.note{{display:flex;gap:9px;font-size:12.5px;line-height:1.5}}
.note .dot{{flex:none;width:8px;height:8px;border-radius:50%;margin-top:5px}}
.note.ssr .dot{{background:var(--ssr)}}
.note.ajax .dot{{background:var(--ajax)}}
.note.gray .dot{{background:var(--ink-3)}}
.note .tx{{color:var(--ink)}}
.note.gray .tx{{color:var(--ink-2)}}
.foot{{flex:none;margin-top:14px;border-top:1.5px dashed var(--soft);padding-top:10px;
      font-size:11.5px;color:var(--ink-3)}}
</style></head><body>
<div class="slide">
  <div class="slide-head">
    <h1>{title}</h1>
    <div class="sub">{sub}</div>
    <div style="margin-left:auto;display:flex;gap:16px;font-size:12px;color:var(--ink-2);align-items:center">
      <span><i style="display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--ssr);margin-right:6px"></i>화면 전환 (SSR)</span>
      <span><i style="display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--ajax);margin-right:6px"></i>제자리 갱신 (AJAX)</span>
    </div>
  </div>

  <div class="stage">
    <div class="frames">{frames}</div>
    <div class="notes">
      <h2>구현 메모</h2>
      {notes}
    </div>
  </div>

  <div class="foot">화면은 <span class="mono">docs/wireframe/wireframe-v4-mvp.html</span>을 그대로 실어 온 것이다 — 그 파일을 고치면 이 슬라이드도 따라 바뀐다.</div>
</div>
<script>
var CFG = {cfg};
document.querySelectorAll('iframe').forEach(function(f, i){{
  f.addEventListener('load', function(){{
    var d = f.contentDocument;
    var st = d.createElement('style');
    st.textContent = ".wrap{{display:block !important;padding:0 !important}}"
      + ".sidepanel,.caption,.vwtoggle{{display:none !important}}"
      + ".stagecol{{gap:0 !important}}"
      + ".browser{{max-width:none !important;width:100% !important;margin:0 !important}}"
      + ".anno,.notes li{{font-family:'Noto Sans CJK KR','NanumSquare Neo',sans-serif !important;"
      + "font-size:.8rem !important;line-height:1.45 !important}}";
    d.head.appendChild(st);
    // 헤드리스 환경에 이모지 폰트가 없어 두부 글자가 나온다. SVG 아이콘으로 갈아 끼운다.
    var brand = d.querySelector('.navbar .brandname');
    if (brand) brand.innerHTML =
      '<svg width="13" height="13" viewBox="0 0 16 16" style="vertical-align:-1px;margin-right:3px">'
      + '<path d="M4 12 L11 5 L13 7 L6 14 Z" fill="#e8792b"/>'
      + '<path d="M11 5 L12 2 M12 4 L15 3" stroke="#3a8a3a" stroke-width="1.4" fill="none"/></svg>'
      + '크래프톤 당근';
    var chat = d.querySelector('[aria-label="채팅"] span');
    if (chat) chat.innerHTML =
      '<svg width="15" height="15" viewBox="0 0 16 16"><path d="M2 3h12v8H7l-3.5 3V11H2z"'
      + ' fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>';

    var go = d.querySelector('[data-go=\\"' + CFG[i].id + '\\"]');
    if (go) go.click();
    if (CFG[i].burger) d.getElementById('burger').click();
  }});
}});
</script>
</body></html>
"""

def build():
    here = os.path.dirname(os.path.abspath(__file__))
    for name, title, sub, screens, notes in SLIDES:
        two = len(screens) > 1
        iw = 620 if two else 1180
        ih = FH
        if two:
            avail = (CONTENT_W - 26 - NOTES_W - 22 - 34 - 22) / 2.0
        else:
            avail = CONTENT_W - 26 - NOTES_W
        scale = min(avail / iw, STAGE_H / float(ih))
        fw = round(iw * scale)
        fh = round(ih * scale)
        parts = []
        for n, (sid, cap, color, burger) in enumerate(screens):
            if n:
                parts.append('<div class="link"></div>')
            parts.append(
                '<div class="frame"><div class="shell">'
                '<iframe src="../wireframe-v4-mvp.html" scrolling="no"></iframe>'
                '</div><div class="cap">%s</div></div>' % cap)
        note_html = "\n      ".join(
            '<div class="note %s"><span class="dot"></span><span class="tx">%s</span></div>' % (c, t)
            for c, t in notes)
        cfg = "[" + ",".join(
            '{id:"%s",burger:%s}' % (s[0], "true" if s[3] else "false") for s in screens) + "]"
        out = TPL.format(title=html.escape(title), sub=html.escape(sub),
                         frames="".join(parts), notes=note_html,
                         iw=iw, ih=ih, fw=fw, fh=fh, scale=round(scale, 4), cfg=cfg)
        with io.open(os.path.join(here, name + ".html"), "w", encoding="utf-8") as f:
            f.write(out)
        print("wrote", name + ".html")

if __name__ == "__main__":
    build()
