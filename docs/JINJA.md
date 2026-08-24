# Jinja 템플릿 사용법 — 크래프톤 당근

> 각자 맡은 페이지 템플릿을 쓰기 전에 한 번 읽는 문서. 15분이면 충분하다.
> 관련 문서: 디렉토리·담당 배분은 `ARCHITECTURE.md`, 라우트 계약은 `API.md`,
> Bootstrap 클래스는 `BOOTSTRAP.md`.

## 0. 한 줄로

**Jinja는 서버에서 HTML을 조립해 주는 템플릿 엔진이다.** Flask에 기본으로 들어 있어서
따로 설치할 것이 없다. 우리는 이걸로 두 가지를 한다.

1. 파이썬 값(MongoDB에서 꺼낸 데이터)을 HTML 안에 박아 넣는다.
2. 헤더·사이드바 같은 공통 UI를 `base.html` **한 파일**에만 두고 모든 페이지가 물려받는다.

## 1. 무슨 일이 벌어지나

라우트 함수가 템플릿 이름과 데이터를 넘기면, Jinja가 파일을 읽어서 구멍을 메우고,
**완성된 순수 HTML 문자열**을 브라우저로 보낸다.

`routes/items.py`
```python
@bp.get("/")
@login_required
def feed():
    items = list(db.items.find({"status": "selling"}))
    return render_template("feed.html", items=items)   # 변수는 키워드 인자로 넘긴다
```

`templates/feed.html`
```html
{% for item in items %}
  <div class="card"><h5>{{ item.title }}</h5><span>{{ item.price }}원</span></div>
{% endfor %}
```

브라우저가 실제로 받는 것
```html
<div class="card"><h5>선풍기</h5><span>15000원</span></div>
<div class="card"><h5>전공책</h5><span>8000원</span></div>
```

> **중요**: 브라우저는 `{{ }}`나 `{% %}`를 절대 보지 못한다. 치환은 전부 서버 안에서 끝난다.
> 개발자 도구로 페이지 소스를 열어도 Jinja 문법은 한 글자도 안 보인다.
> 우리가 "SSR"이라고 부르는 것이 바로 이것이다.
>
> 따라서 **JS로는 Jinja 변수를 바꿀 수 없다.** 화면이 바뀌어야 하면 페이지를 다시 요청하거나
> (SSR), `/api/`에서 JSON을 받아 JS가 직접 그린다 (Ajax). 경계는 `API.md` § 0.

## 2. 문법은 세 종류뿐

### `{{ ... }}` — 값을 그 자리에 출력한다

중괄호 두 개. 안에 든 파이썬 값이 문자열로 바뀌어 그 자리에 찍힌다.

```html
<h5>{{ item.title }}</h5>              →  <h5>선풍기</h5>
<span>{{ item.price }}원</span>         →  <span>15000원</span>
<img src="{{ url_for('static', filename='js/x.png') }}">   {# 함수 호출도 된다 #}
<a href="/chats/{{ room._id }}">…</a>  {# 속성값 안에서도 쓴다 #}
```

### `{% ... %}` — 실행한다 (반복 · 조건 · 상속). 그 자체는 출력되지 않는다

중괄호 + 퍼센트. 이 태그 자체는 HTML로 나가지 않고, "여기서 반복해라 / 여기서 갈라져라"
하는 지시로만 쓰인다.

```html
{% for item in items %}                 {# items 개수만큼 아래를 반복 #}
  <div>{{ item.title }}</div>
{% endfor %}                            {# ← 반드시 닫는다 #}

{% if item.status == "done" %}          {# 조건이 참일 때만 아래를 출력 #}
  <span class="badge text-bg-success">판매완료</span>
{% endif %}                             {# ← 반드시 닫는다 #}

{% extends "base.html" %}               {# base.html을 물려받는다 (§4) #}
{% block content %}…{% endblock %}      {# base.html의 구멍을 채운다 #}

{% set price_text = item.price ~ "원" %}  {# 템플릿 안에서 변수 하나 만들기 #}
```

> `{% %}`로 연 것은 **반드시 닫는다**: `{% endfor %}` · `{% endif %}` · `{% endblock %}`.
> 파이썬과 달리 들여쓰기로는 안 닫힌다. 안 닫으면 `TemplateSyntaxError`가 난다.

### `{# ... #}` — 주석. HTML로도 나가지 않는다

```html
{# 이 줄은 브라우저에 전혀 전달되지 않는다. 팀원끼리 남기는 메모용 #}
<!-- 이건 HTML 주석이라 브라우저 소스보기에 그대로 보인다. 비밀은 쓰지 말 것 -->
```

## 3. 공통 UI가 뭐냐 — navbar와 offcanvas

`base.html`이 들고 있는 공통 UI는 딱 두 덩어리다. 둘 다 Bootstrap 컴포넌트 이름이다.

```
┌──────────────────────────────────────────┐
│ ☰   🥕 크래프톤 당근   홈        ⌕  💬②  │ ← navbar (화면 맨 위 가로 막대)
├──────────────────────────────────────────┤
│                                          │
│   {% block content %} ← 여기가 각자 담당   │
│                                          │
└──────────────────────────────────────────┘
```

- **navbar = 헤더.** 모든 페이지 맨 위에 항상 붙어 있는 가로 막대.
  왼쪽부터 햄버거 버튼(☰) · 서비스 이름 · 현재 페이지 이름, 오른쪽 끝에 검색(P2)과
  채팅 뱃지(P1).
- **offcanvas = 사이드바.** 이름 그대로 "화면(canvas) 바깥(off)에 숨어 있다가 밀려 들어오는 판".
  ☰ 를 누르면 왼쪽에서 슬라이드해서 나오고, 뒤 본문은 어두워지며, 바깥을 클릭하면 닫힌다.
  모바일 앱의 서랍 메뉴와 같은 물건이다. 메뉴 5항목이 들어간다
  (Home · Community · 채팅목록 · 거래내역 · 로그아웃).

**우리가 여닫는 JS를 짤 일은 없다.** 아래처럼 속성 두 개만 적으면 Bootstrap이 열고 닫고
배경 어둡게 하고 바깥 클릭 처리까지 전부 해 준다. (`BOOTSTRAP.md` § 2에 전체 스니펫)

```html
<!-- navbar 안의 햄버거 버튼: "sideMenu라는 offcanvas를 토글해라" -->
<button class="btn" data-bs-toggle="offcanvas" data-bs-target="#sideMenu">☰</button>

<!-- 평소엔 화면 밖에 숨어 있는 판. id가 위의 target과 짝이다 -->
<div class="offcanvas offcanvas-start" id="sideMenu"> … 메뉴 5개 … </div>
```

⚠️ 단, `bootstrap.bundle.min.js`(bundle 버전)를 넣어야 동작한다. bundle이 아닌 파일을 넣으면
offcanvas가 **에러 없이 조용히 안 열린다.** 제일 흔한 삽질이다.

> **이 두 덩어리는 `base.html`에 딱 한 번만 등장한다.** B·C는 navbar도 offcanvas도
> 자기 파일에 쓰지 않는다. 물려받으면 저절로 화면에 있다.

## 4. base.html 상속 — 우리 팀의 계약 (여기가 제일 중요)

`base.html`(담당 A)이 `<html>` · `<head>` · navbar · offcanvas · Bootstrap CDN을 전부 들고
있고, 그 안에 **구멍(block)** 세 개를 뚫어 둔다. 나머지 템플릿은 그 구멍만 채운다.

### 규칙 3줄

1. 모든 템플릿은 `{% extends "base.html" %}`로 **첫 줄을** 시작한다.
2. 쓸 수 있는 block은 **`title` · `content` · `scripts` 세 개뿐**이며, **이름은 고정**이다.
   이름을 바꾸거나 새로 만들면 다른 사람 파일이 같이 깨진다. 필요하면 A에게 말한다.
3. **커스텀 CSS를 쓰지 않는다.** Bootstrap 유틸리티 클래스만 쓴다.
   CSS의 유일한 주인은 `base.html`이다 (`BOOTSTRAP.md` § 3).

### 복붙용 시작 골격

```html
{% extends "base.html" %}

{% block title %}홈{% endblock %}

{% block content %}
  <!-- 여기부터 내 페이지. <html>·<head>·navbar는 절대 쓰지 않는다 -->
  <h4 class="mb-3">최근 올라온 물건</h4>
  <div class="row row-cols-1 row-cols-md-3 g-3">…</div>
{% endblock %}

{% block scripts %}
  <!-- 이 페이지에서만 필요한 JS. 없으면 이 블록 자체를 지운다 -->
  <script src="{{ url_for('static', filename='js/item.js') }}"></script>
{% endblock %}
```

| block | 들어가는 것 | 비고 |
|---|---|---|
| `title` | 브라우저 탭 제목 | 생략하면 base의 기본값("크래프톤 당근")이 쓰인다 |
| `content` | 페이지 본문 전체 | `<main class="container">` 안쪽이라 컨테이너를 또 만들 필요 없다 |
| `scripts` | 이 페이지 전용 `<script>` | `</body>` 직전 + Bootstrap JS **뒤**에 놓인다 |

`scripts` block이 있는 이유: `poll.js`는 `chat_room.html`에만, `item.js`는 작성 페이지에만
필요하다. 이 구멍이 없으면 각자 `base.html`을 열어서 `<script>` 줄을 추가하게 되고,
"한 사람 = 파일 하나"라는 충돌 격리가 그 순간 깨진다.

> **`base.html`은 A만 수정한다.** 헤더·사이드바·전역 CSS에 손댈 일이 생기면 직접 고치지 말고
> A에게 말한다. 셋이 같은 파일을 고치면 merge 충돌이 난다.

## 5. 자주 쓰게 될 패턴 6개

> 각 패턴 제목 옆의 **[A][B][C]** 는 주로 누가 쓰게 되는지다. 표시가 없는 사람도
> 읽어는 두자. 남의 코드를 볼 일이 생긴다.

### 5-1. 반복 — 목록을 화면에 뿌린다 **[A][B][C] 전원**

MongoDB에서 꺼낸 리스트를 카드 여러 장으로 펼치는, 가장 많이 쓸 패턴이다.
B는 피드 카드, C는 채팅 메시지 목록, A는 거래내역 목록에 쓴다.

```html
{# items는 라우트에서 render_template("feed.html", items=items)로 넘겨준 리스트 #}
{% for item in items %}
  {# 이 안에서 item은 리스트의 원소 하나(=MongoDB 문서 하나)를 가리킨다.
     리스트에 물건이 8개면 이 <div>가 8번 찍힌다. #}
  <div class="col">
    <a href="/items/{{ item._id }}" class="card h-100">{{ item.title }}</a>
    {#         ↑ 카드마다 링크 주소가 달라진다. 이게 "카드 = 채팅 입구"의 구현이다 #}
  </div>

{% else %}
  {# ↑ for에 붙는 else. 리스트가 "비어 있을 때만" 실행된다.
     if의 else가 아니라 for의 else다. Jinja의 편의 기능이고, 파이썬에도 있는 문법이다.
     빈 화면에 아무것도 안 나오면 사용자가 고장인 줄 알기 때문에 항상 넣어 준다. #}
  <p class="text-muted">아직 올라온 물건이 없어요.</p>

{% endfor %}
```

### 5-2. 조건 — 사람에 따라 버튼을 보이거나 감춘다 **[C] 주로, [A][B] 일부**

C의 `chat_room.html`에서 "판매완료 처리" 버튼은 판매자에게만 보여야 한다.
B는 삭제 버튼, A는 로그인 여부에 따른 navbar 아이콘에 같은 패턴을 쓴다.

```html
{# g.user는 @login_required 데코레이터가 넣어 준 "지금 로그인한 사람" 문서다
   (ARCHITECTURE.md § 4). 어느 템플릿에서든 그냥 g.user로 쓸 수 있다. #}
{% if item.seller_id == g.user._id %}
  {# 지금 이 화면을 보는 사람 == 이 물건을 올린 사람 → 판매자다 #}
  <button id="btn-done" class="btn btn-success">판매완료 처리</button>
{% else %}
  {# 그 외 = 구매자다. 구매자에게는 이 버튼을 아예 안 그린다 #}
  <span class="text-muted small">판매자가 완료 처리하면 상태가 바뀌어요</span>
{% endif %}
```

> ⚠️ **버튼 숨김은 UI이지 보안이 아니다.** 버튼이 안 보여도 구매자가 개발자 도구로
> `POST /api/items/<id>/done`을 직접 쏘면 그만이다. 그래서 **라우트 함수 안에서도**
> 같은 검사를 반복하고 아니면 `403 {"error": "not_seller"}`를 돌려준다
> (`ARCHITECTURE.md` § 4, `API.md` § 2). 시연에서 지적당하기 딱 좋은 지점이다.

### 5-3. 정적 파일 경로 — JS와 업로드 사진을 불러온다 **[B][C]**

`static/` 폴더 안의 파일(내가 쓴 JS, 사용자가 올린 사진)을 가리킬 때 쓴다.
B는 `item.js`와 업로드 사진, C는 `poll.js`에 필요하다.

```html
{# url_for는 Flask가 제공하는 함수다. "static 폴더의 js/poll.js를 가리키는 주소를 만들어라"
   라는 뜻이고, 결과는 /static/js/poll.js 라는 문자열이 된다. #}
<script src="{{ url_for('static', filename='js/poll.js') }}"></script>

{# 사진은 파일명이 물건마다 다르므로 문자열을 이어 붙여야 한다.
   ~ 는 Jinja에서 문자열을 잇는 연산자다. 파이썬의 + 자리라고 보면 된다.
   item.photo가 "68a3f1.jpg"라면 결과는 /static/uploads/68a3f1.jpg 가 된다. #}
<img src="{{ url_for('static', filename='uploads/' ~ item.photo) }}" class="card-img-top">
```

`/static/js/poll.js`라고 직접 써도 지금은 동작한다. 다만 `url_for`가 Flask 표준이고
나중에 경로가 바뀌어도 안 깨지므로 이걸로 통일한다.

### 5-4. 값이 없을 수 있는 필드 — 화면에 `None`이 찍히는 것을 막는다 **[B][C] 필수**

`items` 스키마에서 `price` · `want` · `account` · `photo`는 **`None`일 수 있다**
(`ARCHITECTURE.md` § 3). 나눔 글에는 가격이 없고, 판매 글에는 원하는 물건이 없기 때문이다.
아무 처리 없이 출력하면 화면에 글자 그대로 **`None`** 이 찍힌다.

B는 작성 폼과 피드에서, C는 `chat_room.html` 상단 물건 카드에서 **같은 필드를 읽으므로**
둘 다 이 처리가 필요하다.

```html
{# 방법 1 — 삼항 조건. "price가 있으면 그 값, 없으면 '나눔'" #}
{{ item.price if item.price else '나눔' }}

{# 방법 2 — or. 앞이 None이나 빈 문자열이면 뒤엣것을 쓴다. 제일 짧다.
   want가 None이면 "아무거나" (v4 설계상 None = 아무거나) #}
{{ item.want or '아무거나' }}

{# 방법 3 — default 필터. | 는 "왼쪽 값을 오른쪽 필터에 통과시켜라"는 뜻이다 #}
{{ item.description|default('설명 없음') }}

{# 사진처럼 태그 전체를 그릴지 말지 갈라야 하면 if로 감싼다.
   photo가 None인데 <img>를 그리면 깨진 이미지 아이콘이 뜬다 #}
{% if item.photo %}
  <img src="{{ url_for('static', filename='uploads/' ~ item.photo) }}">
{% else %}
  <div class="bg-light text-center py-5 text-muted">사진 없음</div>
{% endif %}
```

### 5-5. 폼 재렌더 — 실패했을 때 입력값을 되살린다 **[A] 주로, [B] 일부**

A의 가입 폼에서 아이디가 중복이면 `API.md` § 1대로 폼을 다시 그린다. 이때 아무 처리도
안 하면 사용자가 적은 내용이 전부 날아가서, 처음부터 다시 타이핑하게 된다.

라우트 쪽:
```python
if db.users.find_one({"username": username}):
    # 폼을 다시 그리되, 방금 입력한 값과 에러 메시지를 같이 넘긴다
    return render_template("signup.html", username=username, error="이미 있는 아이디예요")
```

템플릿 쪽:
```html
{# value에 넘겨받은 값을 도로 넣어 준다. 첫 방문에는 username 변수 자체가 없으므로
   default('')로 빈 문자열을 대신 쓴다. 이게 없으면 첫 방문 때 에러가 난다. #}
<input name="username" class="form-control" value="{{ username|default('') }}">

{# error가 넘어온 경우에만 빨간 글씨를 그린다. 첫 방문에는 error가 없어서 조건이 거짓이 된다 #}
{% if error %}<div class="text-danger small">{{ error }}</div>{% endif %}
```

> 비밀번호 입력칸에는 이 처리를 하지 않는다. 비밀번호를 HTML에 되돌려 심는 것은 안 좋다.

### 5-6. 상태 뱃지 — 세 화면이 똑같은 코드를 쓴다 **[A][B][C] 전원**

`items.status`("selling" 또는 "done")를 색깔 있는 뱃지로 그린다. 피드(B) · 채팅 화면(C) ·
거래내역(A) 세 곳에 전부 나오는데, **같은 모양으로 보여야 하므로 코드를 그대로 복사해 쓴다.**

```html
{# set = 템플릿 안에서 임시 변수를 만든다.
   { } 안은 파이썬 딕셔너리이고, 뒤의 [item.status]로 값 하나를 꺼낸다.
   status가 "selling"이면 badge = ("판매중", "secondary") 라는 짝이 된다. #}
{% set badge = {"selling": ("판매중", "secondary"),
                "done":    ("판매완료", "success")}[item.status] %}

{# badge[0]은 표시할 글자, badge[1]은 Bootstrap 색 이름이다.
   결과: <span class="badge text-bg-secondary">판매중</span> #}
<span class="badge text-bg-{{ badge[1] }}">{{ badge[0] }}</span>
```

`{% if %}` 두 번으로 써도 되지만, 세 사람이 각자 if를 쓰면 글자나 색이 미묘하게 어긋난다.
이 세 줄을 그대로 복사하는 편이 안전하다.

> 상태의 주인은 `items.status` **한 곳뿐**이다. rooms에는 상태를 두지 않는다
> (`ARCHITECTURE.md` § 3).

## 6. 함정 목록

1. **Jinja는 파이썬이 아니다.** 템플릿 안에서 `db.items.find(...)`를 부르거나 로직을 짜지 않는다.
   데이터 준비는 전부 라우트 함수에서 끝내고, 템플릿에는 완성된 값만 넘긴다.
   `.append()` 같은 메서드도 대부분 안 된다.
2. **닫는 태그를 빼먹는다.** `{% endfor %}` · `{% endif %}` · `{% endblock %}`. 제일 흔한 에러다.
3. **`{% extends %}`는 반드시 첫 줄.** 위에 HTML 주석 한 줄이라도 있으면 안 된다.
4. **`{% block %}` 바깥에 쓴 내용은 사라진다.** 자식 템플릿에서 block 밖에 쓴 HTML은 렌더되지
   않는다. 화면에 아무것도 안 나오면 이걸 먼저 의심한다.
5. **`bootstrap.bundle.min.js`가 아니면 offcanvas가 조용히 죽는다.** 에러도 안 난다 (§ 3).
6. **딕셔너리는 `item.title`과 `item['title']` 둘 다 된다.** pymongo 문서는 dict라서
   점 표기가 편하다. MongoDB 문서의 id 키는 `_id`이므로 `item._id`가 맞다.
7. **JS 안에서 Jinja 변수를 쓸 때는 따옴표를 잊지 않는다.**
   `const roomId = "{{ room._id }}";` — 따옴표를 빼면 JS 문법 에러가 난다.
8. **템플릿 이름은 `templates/` 기준 상대 경로다.** `render_template("feed.html")`,
   커뮤니티는 `render_template("community/list.html")`.

## 7. 담당별 첫 파일

| 담당 | 만들 템플릿 | 비고 |
|---|---|---|
| **A** | `base.html` → `login.html` `signup.html` `history.html` | base.html이 1일차 오전 크리티컬 패스. navbar·offcanvas의 유일한 주인 |
| **B** | `feed.html` `item_write.html` | 5-1 반복 · 5-3 사진 · 5-4 None 처리가 핵심. `scripts` block에 `item.js` |
| **C** | `chat_list.html` `chat_room.html` | 5-2 조건(판매자 판별)이 핵심. `scripts` block에 `poll.js`. 상단 물건 카드는 B의 items 스키마를 그대로 읽는다 |

`base.html`이 나오기 전이라도 B·C는 `{% block content %}` 안쪽 마크업을 먼저 짜 두면 된다.
나중에 위아래 세 줄만 붙이면 그대로 붙는다.
