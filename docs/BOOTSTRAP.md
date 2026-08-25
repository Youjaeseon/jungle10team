# Bootstrap 컴포넌트 지도 — 정글장터

> 기준: 2026-08-25 팀 회의 (v6). 와이어프레임의 분홍 태그(`navbar`, `offcanvas` …)와
> 실제 Bootstrap 5 구현의 1:1 대응표.
> 방침(`DESIGN.md`): 기본 파랑 테마 유지, 커스텀 CSS 최소화. CSS와 싸우기 시작하면 일정이 CSS로 샌다.

## 0. 도입 — base.html에 두 줄

```html
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
```

⚠️ 반드시 **`bundle`** 버전 — offcanvas가 의존하는 Popper가 bundle에만 들어 있다.
빌드 도구는 필요 없다.

## 1. 대응표 (난이도 순)

| 와이어프레임 요소 | 쓰이는 곳 | 구현 방식 | 담당 | 난이도 |
|---|---|---|---|---|
| `navbar` + 검색 폼 | 헤더 (햄버거·로고·검색·말풍선) | 공식 마크업 + `<form action="/search">` | 진근 | 하 |
| `offcanvas` | 햄버거 사이드바 | data 속성만, **JS 0줄** | 진근 | 하 |
| `card` | 사이드바 메뉴, 피드 카드 | 클래스만 | 진근 / 래혁 | 하 |
| `row-cols-1 row-cols-md-3` | 피드 그리드 | 클래스 하나로 3열↔1열 반응형 | 래혁 | 하 |
| `badge` | 유형·상태 뱃지 ('완료' 포함) | 클래스만 | 래혁 | 하 |
| `alert` | "로그아웃되었어요" 안내 | 클래스만 | 진근 | 하 |
| `form-control` | 모든 입력 폼 | 클래스만 | 전원 | 하 |
| `nav-pills` / `nav-tabs` | 필터 칩(P2)·거래내역 탭 | 탭 전환도 `data-bs-toggle="tab"` 선언만 | 래혁 / 진근 | 하 |
| `pagination` | **홈 피드 하단** + 판매자 방 번호 | 클래스만 (Jinja 반복) | 래혁 | 하 |
| `btn-check` (라디오) | 거래 유형·**소속 4종** 선택 | 패턴 복붙 + (유형만) 필드 분기 JS | B / A | 중 |
| 완료 카드 흑백 | 피드·거래내역의 done 글 | CSS `filter: grayscale(1)` 한 줄 | 래혁 | 하 |

**우리가 직접 짜는 JS는 ws.js(SocketIO 클라이언트) · 거래완료 토글 · 유형 필드 분기(P1)뿐이다.**
나머지는 전부 "HTML에 속성을 쓰면 Bootstrap JS가 알아서 동작"하는 선언형이다.
SocketIO 클라이언트 라이브러리는 CDN 한 줄 — `chat_room.html`의 `scripts` block에 넣는다:
`<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>`

## 2. 핵심 스니펫

### 헤더 (navbar + 검색 + 말풍선 + 햄버거) — [진근]

```html
<nav class="navbar bg-body-tertiary sticky-top">
  <div class="container-fluid">
    <button class="btn" data-bs-toggle="offcanvas" data-bs-target="#sideMenu">☰</button>
    <a class="navbar-brand me-auto" href="/">정글장터</a>
    <form class="d-flex" role="search" action="/search" method="get">
      <input class="form-control form-control-sm" type="search" name="q" placeholder="물품 검색">
    </form>
    <a href="/chats" class="btn">💬</a>
  </div>
</nav>
```
검색은 폼 제출 = SSR 이동(`GET /search?q=…`)이라 JS가 없다.

### offcanvas (햄버거 사이드바) — [진근], JS 0줄

```html
<div class="offcanvas offcanvas-start" id="sideMenu">
  <div class="offcanvas-header">
    <h5>메뉴</h5>
    <button class="btn-close" data-bs-dismiss="offcanvas"></button>
  </div>
  <div class="offcanvas-body d-grid gap-2">
    <a href="/" class="card text-decoration-none"><div class="card-body">Home</div></a>
    <a href="/community" class="card text-decoration-none"><div class="card-body">Community</div></a>
    <a href="/chats" class="card text-decoration-none"><div class="card-body">채팅목록</div></a>
    <a href="/history" class="card text-decoration-none"><div class="card-body">거래내역</div></a>
    <a href="/logout" class="card text-decoration-none"><div class="card-body">로그아웃</div></a>
  </div>
</div>
```

### 회원가입 소속 선택 (btn-check 라디오) — [진근]

```html
<div class="btn-group" role="group">
  {% for lab in ["SW-AI LAB", "GAME LAB", "GAME TECH LAB", "코치 및 운영진"] %}
  <input type="radio" class="btn-check" name="lab" id="lab-{{ loop.index }}"
         value="{{ lab }}" {{ "checked" if loop.first }}>
  <label class="btn btn-outline-primary" for="lab-{{ loop.index }}">{{ lab }}</label>
  {% endfor %}
</div>
```
분기 JS가 없다 — 값을 그대로 `users.lab`에 저장할 뿐이다.

### 피드 그리드 + 완료 흑백 — [래혁]

```html
<div class="row row-cols-1 row-cols-md-3 g-3">
  {% for item in items %}
  <div class="col">
    <a href="/items/{{ item._id }}" class="card h-100 text-decoration-none
              {{ 'card-done' if item.status == 'done' }}">…</a>
  </div>
  {% endfor %}
</div>
```
```css
/* 예외 한 줄 — Bootstrap에 흑백 유틸리티가 없다. CSS의 주인은 base.html 하나이므로
   이 줄도 base.html에만 둔다: 래혁이 요청하고 진근이 추가한다 (JINJA.md §4 규칙 3) */
.card-done img { filter: grayscale(1); }
```

### 홈 피드 페이지네이션 — [래혁], 페이지당 20개

```html
<nav>
  <ul class="pagination justify-content-center">
    {% for p in range(1, total_pages + 1) %}
    <li class="page-item {{ 'active' if p == page }}">
      <a class="page-link" href="/?page={{ p }}{{ '&type=' + type if type }}">{{ p }}</a>
    </li>
    {% endfor %}
  </ul>
</nav>
```
백엔드(C)는 `skip((page-1)*20).limit(20)`과 `total_pages`를 넘긴다
(컨텍스트 계약: `ARCHITECTURE.md` §6).

### 판매자 방 페이지네이션 (채팅 화면) — [래혁], 같은 컴포넌트

```html
{% if is_seller %}
<nav>
  <ul class="pagination pagination-sm justify-content-center">
    {% for r in sibling_rooms %}
    <li class="page-item {{ 'active' if r._id == room._id }}">
      <a class="page-link" href="/chats/{{ r._id }}">{{ loop.index }}</a>
    </li>
    {% endfor %}
  </ul>
</nav>
{% endif %}
```
번호 하나가 구매자 한 명의 방이다. 구매자에게는 이 블록 자체를 그리지 않는다.

### 거래완료 토글 + 삭제 (물품 상세, 판매자만) — 버튼은 [래혁], API는 [재성]

```html
{% if is_seller %}
<form action="/items/{{ item._id }}/delete" method="post" class="d-inline">
  <button class="btn btn-danger">삭제</button>
</form>
<button id="toggle-done" class="btn btn-outline-warning">
  {{ "거래완료 해제" if item.status == "done" else "거래완료 처리" }}
</button>
{% endif %}
```
```js
// item.js — 토글: 응답의 status로 버튼·뱃지를 다시 그린다
document.getElementById('toggle-done')?.addEventListener('click', async () => {
  const res = await fetch(`/api/items/${itemId}/status`, {method: 'POST'});
  if (res.ok) updateStatusUI((await res.json()).status);   // "selling" | "done"
});
```

### 상태 뱃지 — Jinja 분기 한 줄 — [래혁]

```html
{% set badge = {"selling": ("판매중", "secondary"),
                "done": ("완료", "dark")}[item.status] %}
<span class="badge text-bg-{{ badge[1] }}">{{ badge[0] }}</span>
```

### 거래 유형 선택 (btn-check) + 필드 분기 — [래혁], 분기는 P1

```html
<div class="btn-group" role="group">
  <input type="radio" class="btn-check" name="type" id="t-sale" value="sale" checked>
  <label class="btn btn-outline-primary" for="t-sale">판매</label>
  <input type="radio" class="btn-check" name="type" id="t-free" value="free">
  <label class="btn btn-outline-primary" for="t-free">나눔</label>
  <input type="radio" class="btn-check" name="type" id="t-swap" value="swap">
  <label class="btn btn-outline-primary" for="t-swap">교환</label>
</div>
```
```js
// P1 — 유형에 따라 가격/원하는물건 필드를 보이고 숨기기
document.querySelectorAll('input[name="type"]').forEach(r =>
  r.addEventListener('change', () => {
    document.getElementById('f-price').hidden = r.value !== 'sale';
    document.getElementById('f-want').hidden  = r.value !== 'swap';
  }));
```
P0는 판매 유형만 완성해도 성립 — 이 분기는 P1에 붙인다.

### presence 표시 (채팅 화면) — [래혁], 데이터는 ws.js의 presence 이벤트

```html
<span id="peer-presence" class="badge text-bg-success" hidden>상대방이 보고 있어요</span>
```
```js
// ws.js — SocketIO 이벤트 구독
socket.on('presence', ({online}) =>
  document.getElementById('peer-presence').hidden = !online);
```

## 3. 함정 목록

1. **bundle 아닌 `bootstrap.min.js`를 넣으면** offcanvas가 소리 없이 죽는다. 제일 흔한 삽질.
2. **버튼 숨김 ≠ 권한**: 삭제·거래완료 버튼은 Jinja `{% if %}`로 판매자에게만 그리되,
   서버 라우트에서도 같은 검사를 반복한다 (`ARCHITECTURE.md` §4).
3. **커스텀 CSS는 마지막 날에만.** 유일한 예외가 위의 `.card-done` 흑백 한 줄이다.
   색·간격이 마음에 안 들어도 일단 기본 테마로 기능을 완주하고, 시간이 남으면
   CSS 변수(`--bs-primary`)만 바꾼다.
4. **base.html·app.py·requirements.txt는 진근의 파일이다.** 래혁·재성은 고치고 싶으면
   진근에게 말한다 — 세 브랜치가 같은 파일을 건드리는 순간 머지 충돌이 시작된다.
