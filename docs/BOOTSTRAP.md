# Bootstrap 컴포넌트 지도 — 크래프톤 당근

> 와이어프레임 v3의 분홍 태그(`navbar`, `offcanvas` …)와 실제 Bootstrap 5 구현의 1:1 대응표.
> 방침(`DESIGN.md`): 기본 파랑 테마 유지, 커스텀 CSS 최소화. CSS와 싸우기 시작하면 2박 3일이 CSS로 샌다.

## 0. 도입 — base.html에 두 줄

```html
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
```

⚠️ 반드시 **`bundle`** 버전 — offcanvas·modal·toast가 의존하는 Popper가 bundle에만 들어 있다.
빌드 도구는 필요 없다.

## 1. 대응표 (난이도 순)

| 와이어프레임 태그 | 쓰이는 곳 | 구현 방식 | 난이도 |
|---|---|---|---|
| `navbar` | 상단 바 | 공식 마크업 복붙 + 내용 교체 | 하 |
| `offcanvas` | 햄버거 사이드바 | data 속성만, **JS 0줄** | 하 |
| `card` | 사이드바 메뉴, 피드 카드 | 클래스만 | 하 |
| `row-cols-1 row-cols-md-3` | 피드 그리드 | 클래스 하나로 3열↔1열 반응형 | 하 |
| `modal` | 계좌이체 안내 | data 속성이면 JS 0줄 | 하 |
| `badge` | 유형·상태 뱃지 | 클래스만 | 하 |
| `form-control` | 모든 입력 폼 | 클래스만 | 하 |
| `nav-pills` / `nav-tabs` | 필터 칩·거래내역 탭 | 탭 전환도 `data-bs-toggle="tab"` 선언만 | 하 |
| `btn-group` (라디오) | 거래 유형·기수 선택 | `btn-check` 패턴 + 필드 분기용 작은 JS | 중 |
| `toast` | 복사 완료 알림 | 유일하게 JS 인스턴스 필요 | 중 |

9개 중 7개가 "HTML에 속성을 쓰면 Bootstrap JS가 알아서 동작"하는 선언형이다.
**우리가 직접 짜는 JS는 사실상 Ajax 계층(폴링·확정·완료)뿐이다.**

## 2. 핵심 스니펫

### offcanvas (햄버거 사이드바) — JS 0줄

```html
<button class="btn" data-bs-toggle="offcanvas" data-bs-target="#sideMenu">☰</button>

<div class="offcanvas offcanvas-start" id="sideMenu">
  <div class="offcanvas-header">
    <h5>메뉴</h5>
    <button class="btn-close" data-bs-dismiss="offcanvas"></button>
  </div>
  <div class="offcanvas-body d-grid gap-2">
    <a href="/" class="card text-decoration-none"><div class="card-body">Home</div></a>
    <a href="/chats" class="card text-decoration-none"><div class="card-body">채팅목록</div></a>
    <a href="/history" class="card text-decoration-none"><div class="card-body">거래내역</div></a>
    <a href="/logout" class="card text-decoration-none"><div class="card-body">로그아웃</div></a>
  </div>
</div>
```

### 피드 그리드 — 반응형이 클래스 하나

```html
<div class="row row-cols-1 row-cols-md-3 g-3">
  {% for item in items %}
  <div class="col"><a href="/items/{{ item._id }}" class="card h-100 …">…</a></div>
  {% endfor %}
</div>
```

### 계좌이체 modal — 열기는 data 속성, JS 0줄

```html
<button class="btn btn-dark" data-bs-toggle="modal" data-bs-target="#buyModal">구매하기</button>

<div class="modal fade" id="buyModal"><div class="modal-dialog"><div class="modal-content">
  <div class="modal-header"><h5>계좌이체 안내</h5>
    <button class="btn-close" data-bs-dismiss="modal"></button></div>
  <div class="modal-body">{{ item.account }} <button id="copy-acct" class="btn btn-sm btn-outline-secondary">복사</button></div>
</div></div></div>
```

### 거래 유형 선택 (btn-check 라디오) + 필드 분기 — 유일하게 JS가 필요한 폼

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
// P1 — 유형에 따라 가격/원하는물건/계좌 필드를 보이고 숨기기
document.querySelectorAll('input[name="type"]').forEach(r =>
  r.addEventListener('change', () => {
    document.getElementById('f-price').hidden = r.value !== 'sale';
    document.getElementById('f-want').hidden  = r.value !== 'swap';
    document.getElementById('f-acct').hidden  = r.value === 'free';
  }));
```
P0는 판매 유형만 완성해도 성립 — 이 분기는 P1에 붙인다.

### toast (복사 알림) — 유일한 JS 인스턴스

```js
document.getElementById('copy-acct').addEventListener('click', async () => {
  await navigator.clipboard.writeText(acctText);
  new bootstrap.Toast(document.getElementById('copied-toast')).show();
});
```

### 상태 뱃지 — Jinja 분기 한 줄

```html
{% set badge = {"selling": ("판매중", "secondary"), "reserved": ("예약중", "warning"),
                "done": ("판매완료", "success")}[item.status] %}
<span class="badge text-bg-{{ badge[1] }}">{{ badge[0] }}</span>
```

## 3. 함정 목록

1. **bundle 아닌 `bootstrap.min.js`를 넣으면** offcanvas·modal이 소리 없이 죽는다. 제일 흔한 삽질.
2. **modal 안에서 폼을 쓸 때** modal이 `<form>` 밖에 있으면 제출이 안 된다. 우리는 modal에 폼이 없어서 해당 없음(안내+복사만).
3. **버튼 숨김 ≠ 권한**: 🤝·삭제·판매완료 버튼은 Jinja `{% if %}`로 판매자에게만 그리되,
   서버 라우트에서도 같은 검사를 반복한다(`ARCHITECTURE.md` §4).
4. **커스텀 CSS는 마지막 날에만.** 색·간격이 마음에 안 들어도 일단 기본 테마로 기능을 완주하고,
   시간이 남으면 CSS 변수(`--bs-primary`)만 바꾼다.
