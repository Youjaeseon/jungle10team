# Bootstrap 컴포넌트 지도 — 정글장터

> 기준: 2026-08-25 팀 회의 (v6). 와이어프레임의 분홍 태그(`navbar`, `offcanvas` …)와
> 실제 Bootstrap 5 구현의 1:1 대응표.
> 방침(`DESIGN.md`): 기본 파랑 테마 유지, 커스텀 CSS 최소화. CSS와 싸우기 시작하면 일정이 CSS로 샌다.
> 2026-08-26 보강: §1-1(`data-bs-*` 동작 원리) · §2의 활동내역 탭 스니펫 · §3 함정 5·6.
> 2026-08-27: 활동내역이 '내 거래글' 로 재개명되고 구매 탭이 제거되면서 **탭 바가 그
> 화면에서 사라졌다.** §2 의 탭 스니펫은 그 화면의 것이 아니라, 남은 유일한 예정 용례인
> P2 유형 필터를 위한 일반 참고 자료로 남긴다.

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
| `nav-pills` / `nav-tabs` | 유형 필터 칩(P2) | 탭 전환도 `data-bs-toggle="tab"` 선언만 | 래혁 | 하 |
| `pagination` | **홈 피드 하단** + 판매자 방 번호 | 클래스만 (Jinja 반복) | 래혁 | 하 |
| `btn-check` (라디오) | 거래 유형·**소속 4종** 선택 | 패턴 복붙 + (유형만) 필드 분기 JS | B / A | 중 |
| 완료 카드 흑백 | 피드·내 거래글의 done 글 | CSS `filter: grayscale(1)` 한 줄 | 래혁 | 하 |

**우리가 직접 짜는 JS는 ws.js(SocketIO 클라이언트) · 거래완료 토글 · 유형 필드 분기(P1)뿐이다.**
나머지는 전부 "HTML에 속성을 쓰면 Bootstrap JS가 알아서 동작"하는 선언형이다.
SocketIO 클라이언트 라이브러리는 CDN 한 줄 — `chat_room.html`의 `scripts` block에 넣는다:
`<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>`

## 1-1. `data-bs-*` 속성이 동작하는 원리

Bootstrap 번들 JS는 페이지가 열릴 때 문서를 한 번 훑으면서 `data-bs-` 로 시작하는
속성을 찾는다. 찾으면 그 요소에 해당 동작을 붙여 준다. **우리가 `addEventListener` 를
쓰지 않는 이유가 이것이다** (§1 아래 "선언형" 의 실체).

| 속성 | 값을 정하는 주체 | 역할 |
|---|---|---|
| `data-bs-toggle` | Bootstrap — 고정 어휘 | 이 요소가 어떤 부품인지 선언한다. `tab` `offcanvas` `modal` `collapse` `dropdown` `tooltip` |
| `data-bs-target` | 우리 — 자유로운 이름 | 조작할 대상을 `#id` 로 지목한다 |
| `data-bs-dismiss` | Bootstrap — 고정 어휘 | 닫기 버튼. 대상을 적지 않으면 자기가 속한 부품을 닫는다 (`base.html:59`) |

`toggle` 은 어휘를 고르는 자리이고 `target` 은 이름을 짓는 자리다. 성격이 반대다.

### id 짝 맞추기

`target` 의 값과 대상의 `id` 는 글자까지 같아야 한다. 가리키는 쪽에만 `#` 을 쓰고,
`id` 속성 자체에는 `#` 을 붙이지 않는다.

```
<button data-bs-target="#sideMenu">  ──지목──▶  <div id="sideMenu">
        base.html:22                            base.html:53
```

이름 자체에 의미는 없다. 양쪽만 같으면 무엇으로 지어도 동작한다.

### 클래스 값은 공백으로 나눈다

`.nav-link.active` 같은 점 표기는 **CSS 선택자 문법**이고, 설명문이나 스타일시트에서만
쓴다. HTML 의 `class` 속성 값에는 공백으로 나열한다.

```
class="nav-link.active"    ✗  그런 이름의 클래스 하나로 읽혀 스타일이 전부 실종된다
class="nav-link active"    ✓  클래스 두 개
```

### 조용히 실패한다

`toggle` 값의 철자가 틀리면 아무 동작도 붙지 않고, `target` 이 없는 id 를 가리키면
눌러도 아무 일이 일어나지 않는다. **콘솔에 에러가 찍히지 않는다.** 안 눌릴 때의 첫
점검은 언제나 이 두 글자의 대조다.

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
    <a href="/history" class="card text-decoration-none"><div class="card-body">내 거래글</div></a>
    <a href="/logout" class="card text-decoration-none"><div class="card-body">로그아웃</div></a>
  </div>
</div>
```

### 탭 (nav-pills + tab-pane) — JS 0줄

> **이 스니펫을 쓰는 화면은 지금 없다.** 원래 활동내역(진근)의 판매/구매 탭이었는데,
> 2026-08-27 에 구매 탭이 제거되면서 탭이 하나만 남았고, 탭 하나짜리 탭 바는 존재
> 이유가 없어서 함께 걷어냈다 (`DESIGN.md` § 잘라낸 것). 남은 예정 용례는 P2 유형
> 필터(래혁)뿐이므로, 그때를 위한 일반 참고 자료로 이 절을 남긴다.

버튼 쪽(`ul.nav`)과 내용물 쪽(`div.tab-content`) 두 덩어리다. `active` 는 지금 눌린
탭과 지금 보이는 내용물, **양쪽에 하나씩 짝으로** 붙는다.

```html
<ul class="nav nav-pills mb-4" role="tablist">
  <li class="nav-item" role="presentation">
    <button class="nav-link active" type="button" role="tab"
            data-bs-toggle="tab" data-bs-target="#tab-a"
            aria-selected="true">첫째 탭</button>
  </li>
  <li class="nav-item" role="presentation">
    <button class="nav-link" type="button" disabled>둘째 탭 (아직 안 열림)</button>
  </li>
</ul>

<div class="tab-content">
  <div class="tab-pane fade show active" id="tab-a">
    {# 카드 목록: row g-4 → col-12 col-sm-6 col-lg-4 → include "_item_card.html" #}
  </div>
</div>
```

- `tab-pane` 은 기본이 **숨김**이다. 처음 보일 하나에만 `show active` 를 더한다.
  이걸 빠뜨리면 탭 바만 뜨고 아래가 텅 빈다.
- `<button>` 은 `disabled` **속성** 하나로 눌림이 막힌다. `disabled` 클래스가 따로
  필요한 것은 `<a>` 로 탭을 만들 때다.
- `type="button"` — `<button>` 의 기본 타입이 `submit` 이라, 폼 안에 놓이면 클릭이
  폼 제출로 샌다.
- 아직 안 여는 탭은 `disabled` 로 막아 두고, 열 때 `disabled` 를 떼고 `data-bs-*`
  두 개를 붙인다. 빈 pane 을 미리 만들어 두지 않는다.
- **탭이 하나뿐이면 탭을 쓰지 않는다.** 탭 바는 "여러 갈래 중 지금 이것" 을 말하는
  장치라, 갈래가 하나면 아무 정보도 전하지 못하면서 클릭 대상만 늘린다. 내 거래글이
  2026-08-27 에 탭을 걷어낸 이유가 이것이다.
- `nav-pills` 의 선택된 탭 색은 기본 파랑이다. 초록으로 바꾸려면 `layout.css` 에
  `--bs-nav-pills-link-active-bg` 를 재선언한다 (§3 함정 3이 허용하는 방식).

같은 컴포넌트를 P2 의 필터 칩(래혁)에도 쓴다.

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
5. **`class` 값에 점을 찍지 않는다.** `class="nav-link.active"` 는 존재하지 않는
   클래스 이름 하나로 읽혀 스타일이 통째로 사라진다. 점 표기는 CSS 선택자 문법이다 (§1-1).
6. **`data-bs-*` 오타는 에러를 내지 않는다.** 부품이 안 움직이면 `data-bs-toggle` 의
   철자와 `data-bs-target` ↔ `id` 의 대조부터 본다 (§1-1).
