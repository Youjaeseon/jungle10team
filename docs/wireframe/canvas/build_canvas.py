# -*- coding: utf-8 -*-
"""발표용 아트보드 빌더.

`_style.css` 한 벌과 `bodies/<이름>.html` 조각을 합쳐 `<이름>.dc.html`을 만든다.
CSS가 8개 파일에 그대로 복제되는 구조라서, 한 곳만 고치면 전부 따라오도록 나눠 두었다.
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

# (파일 이름, 캔버스에 붙일 제목)
BOARDS = [
    ("Main",         "1 · 로그인 → 회원가입"),
    ("HomeFeed",     "2 · 홈 피드"),
    ("BuyerFlow",    "3 · 구매자 — 피드 → 상세 → 채팅"),
    ("SellerFlow",   "4 · 판매자 — 내 글 → 상세 → 챗룸"),
    ("WriteForm",    "5 · 글 작성"),
    ("Sidebar",      "6 · 사이드바 (offcanvas)"),
    ("ChatList",     "7 · 사이드바 → 채팅목록"),
    ("History",      "8 · 사이드바 → 거래내역"),
    ("Logout",       "9 · 사이드바 → 로그아웃"),
    ("Community",    "10 · 커뮤니티 (P2)"),
    ("Architecture", "11 · 아키텍처"),
]

TPL = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&amp;display=swap">
  <style>
%s
</style>
</helmet>
%s
</x-dc>
</body>
</html>
"""

# 정적 렌더 검증용 — support.js와 <x-dc>를 걷어낸 단독 HTML
PROBE = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>%s</title><style>
@font-face{font-family:'Noto Sans KR';src:local('Noto Sans CJK KR')}
%s
</style></head><body>
%s
</body></html>
"""


def build():
    css = io.open(os.path.join(HERE, "_style.css"), encoding="utf-8").read().rstrip()
    probe_dir = os.path.join(HERE, "_probe")
    if not os.path.isdir(probe_dir):
        os.makedirs(probe_dir)
    boards = []
    for i, (name, title) in enumerate(BOARDS):
        body = io.open(os.path.join(HERE, "bodies", name + ".html"),
                       encoding="utf-8").read().rstrip()
        io.open(os.path.join(HERE, name + ".dc.html"), "w", encoding="utf-8").write(TPL % (css, body))
        io.open(os.path.join(probe_dir, name + ".html"), "w", encoding="utf-8").write(PROBE % (title, css, body))
        boards.append({
            "file": name + ".dc.html",
            "x": 1400 * (i % 2),
            "y": 920 * (i // 2),
            "w": 1280,
            "h": 760,
            "title": title,
        })
        print("wrote", name + ".dc.html")
    io.open(os.path.join(HERE, "canvas.json"), "w", encoding="utf-8").write(
        json.dumps({"artboards": boards,
                    "launch": {"view": "canvas"}},
                   ensure_ascii=False, indent=2) + "\n")
    print("wrote canvas.json")


if __name__ == "__main__":
    build()
