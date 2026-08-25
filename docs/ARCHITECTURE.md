# 구조 설계 — 크래프톤 당근

> 기준: 2026-08-25 팀 회의 (v6) + `API.md` v6. 손코딩으로 완주하는 것이 목표라서,
> 모든 선택의 기준은 "가장 단순하고 배우기 좋은 형태"다.

## 1. 전체 그림

```
브라우저
 │ ① 페이지 이동(링크·폼 제출)   ② 제자리 갱신(fetch)          ③ 실시간(WebSocket)
 │    GET /items/42                 POST /api/items/<id>/status    채팅방마다 연결 1개
 │    GET /?page=2                  POST /api/login                message / presence / status
 ▼    GET /search?q=키보드
Flask + Flask-SocketIO (app.py + Blueprint 여러 개 + 이벤트 핸들러)
 │ ① Jinja 렌더 → HTML             ② dict → JSON                 ③ 이벤트 브로드캐스트
 ▼
MongoDB (pymongo, 컬렉션 4개)
```

- **SSR 경로**: 브라우저 주소가 바뀌는 모든 이동. Jinja가 `base.html`을 상속한 템플릿을 렌더.
- **Ajax 경로**: 주소가 안 바뀌는 갱신 — 로그인, 거래완료 토글. (P1·P2: 뱃지, 찜, 댓글)
- **WebSocket 경로** (v6 신설): 채팅 송수신 + 상대 입장 여부(presence) + 상태 변경 알림.
  3초 폴링은 폐기됐다. 이벤트 계약은 `API.md` §3.
- JWT는 httpOnly 쿠키라서 **세 경로 모두 브라우저가 자동으로 토큰을 실어 보낸다.**
  프론트에서 토큰을 만질 일이 없다.

## 2. 디렉토리 구조 (제안 — 파일 경계는 §6과 함께 팀 확정 대상)

```
jungle10team/
├─ app.py                  # [진근] 앱 생성·Blueprint 등록·SocketIO 초기화·socketio.run
│                          #      셋 다 필요한 파일 — 수정 요청은 진근에게, 커밋은 진근만
├─ db.py                   # MongoClient 연결 1곳 (모든 라우트가 import)
├─ auth_util.py            # [진근] JWT 발급/검증 + @login_required 데코레이터
├─ requirements.txt        # [진근] flask, pymongo, pyjwt, flask-socketio
│                          #      의존성 추가도 진근 경유 (app.py와 같은 이유)
├─ routes/
│   ├─ auth.py             # [진근] /login /signup /logout, /api/login
│   ├─ main.py             # [진근] /search /history  (헤더·사이드바에서 이어지는 화면)
│   ├─ community.py        # [진근, P2] /community 3종
│   ├─ items.py            # [재성] / · /items/new · /items/<id> · /items/<id>/delete
│   │                      #      + /api/items/<id>/status (피드·작성·상세·삭제·토글)
│   └─ chat.py             # [재성] /items/<id>/chat · /chats/* · 채팅 초기 로드 API
│                          #      + SocketIO 이벤트 핸들러 (chat.py 안 또는
│                          #        ws.py 분리 — 재성이 결정)
├─ templates/
│   ├─ base.html           # [진근] 헤더(검색·말풍선·햄버거) + offcanvas + Bootstrap CDN + {% block %}
│   ├─ login.html  signup.html  history.html  search.html   # [진근]
│   ├─ _item_card.html     # [래혁] 피드 카드 partial — feed.html과 search.html(진근)이
│   │                      #        {% include %}로 공유 (제안: 카드 마크업 중복 방지)
│   ├─ feed.html  item_write.html  item_detail.html   # [래혁]
│   ├─ chat_list.html  chat_room.html                 # [래혁]
│   └─ community/…         # [진근, P2]
└─ static/
    ├─ js/ws.js            # [래혁] SocketIO 클라이언트 (연결·이벤트 핸들링·재접속)
    ├─ js/item.js          # [래혁] 거래완료 토글·(P1 유형 분기)
    └─ uploads/            # 업로드 사진 (파일명 = ObjectId.jpg)
```

원칙 두 개 (유지):
- **파일 수를 늘리지 않는다.** 계층(서비스 레이어, ORM, 클래스)을 추가하지 않는다.
  라우트 함수 안에서 pymongo를 바로 부르는 것이 이 규모의 정답이다.
- **한 사람 = 파일 하나.** 셋이 각자 브랜치에서 작업 중이므로, 같은 파일을 두 사람이
  건드리지 않는 것이 머지 충돌을 막는 유일한 구조적 방어다. v5의 "한 사람 = Blueprint
  하나"가 v6 역할 재편(래혁 프론트 / 재성 백엔드)으로 "라우트 파일은 재성, 템플릿·JS
  파일은 래혁"으로
  바뀌었다 — 경계가 Blueprint에서 **파일 확장자**로 이동했을 뿐, 원칙은 같다.
  예외는 셋 다 필요로 하는 `app.py`·`requirements.txt` 둘 — 주인을 진근 하나로 두고,
  래혁·재성은 필요한 변경(Blueprint 등록, 의존성 추가)을 요청만 한다.

## 3. MongoDB 컬렉션 (4개 + P2 1개)

```python
users:     {_id, username(유니크), password_hash, name,
            lab: "SW-AI LAB"|"GAME LAB"|"GAME TECH LAB"|"코치 및 운영진",  # v6: 기수 → 소속
            created_at}
items:     {_id, seller_id, title, description,
            type: "sale"|"free"|"swap",
            price: int|None,          # sale일 때만
            want: str|None,           # swap일 때만 (None = "아무거나")
            photo: str|None,          # static/uploads 안의 파일명
            status: "selling"|"done", # v6: 양방향 토글
            created_at}
rooms:     {_id, item_id, seller_id, buyer_id, created_at}
            # (item_id, buyer_id) 조합당 1개 — 재요청 시 재사용. 상태 없음! 상태는 items가 주인
            # 판매자 페이지네이션 = 같은 item_id의 방들을 created_at 순으로 나열한 것
messages:  {_id, room_id, sender_id, text, created_at}
posts (P2): {_id, author_id, category, title, body,
            comments: [{user_id, text, created_at}],  # 임베드로 충분
            created_at}
```

- **상태의 주인은 `items.status` 한 곳.** 피드·채팅 화면·거래내역의 뱃지가 전부 여기를 읽는다.
- v6: `users.cohort`(기수)가 `users.lab`(소속 4종)으로 대체됐다. 채팅·상세에서
  이름 옆에 소속을 표시한다.
- 검색(`/search`)은 `items.title` 부분일치(`$regex`)로 시작한다. 데이터가 수십 건인
  MVP에서는 인덱스 없이 충분하고, 필요해지면 그때 text index를 건다 (add on failure).
- 홈 피드 페이지네이션은 `skip/limit`으로 시작한다: `page N → skip((N-1)*20).limit(20)`.
- 인덱스는 `users.username` 유니크 하나만 걸면 시작할 수 있다.

## 4. JWT 인증 흐름

```
POST /api/login
  → 아이디로 users 조회 → check_password_hash
  → jwt.encode({user_id, exp: 24h}, SECRET)
  → Set-Cookie: token=<JWT>; HttpOnly   (배포 시 Secure 추가)

이후 모든 요청
  → @login_required: request.cookies["token"] → jwt.decode
  → 성공: g.user에 사용자 문서를 담고 라우트 실행
  → 실패: 페이지 요청이면 302 /login, /api/면 401 JSON
WebSocket 연결 수립
  → 같은 쿠키를 검증하고, 방 당사자가 아니면 연결 거부
```

데코레이터는 하나만 만들고, 페이지/API 구분은 `request.path.startswith("/api/")`로 나눈다.
**권한 검사는 항상 서버에서**: 거래완료 토글·삭제 버튼을 템플릿에서
`{% if g.user._id == item.seller_id %}`로 숨기는 것과 별개로, status/delete 라우트
안에서도 같은 검사를 반복한다 (버튼 숨김은 UI, 라우트 검사가 보안).

## 5. 방 찾기/생성 + 실시간 구조

**방 입장 (`GET /items/<id>/chat`)** — v5 확정안 유지:

```python
if g.user["_id"] == item["seller_id"]:
    # 판매자 — 방을 만들지 않고 이 글의 첫 방으로 보낸다
    room = db.rooms.find_one({"item_id": item_id}, sort=[("created_at", 1)])
    if not room:
        return redirect(f"/items/{item_id}")        # 아직 문의가 없다
else:
    # 구매자 — (글, 나) 방을 찾거나 만든다
    room = db.rooms.find_one({"item_id": item_id, "buyer_id": g.user["_id"]})
    if not room:
        room = 새로 insert  # (item_id, seller_id, buyer_id)
return redirect(f"/chats/{room['_id']}")
```

물건을 보기만 하는 사람에게는 방이 생기지 않는다. 방을 만드는 자리는
`/items/<id>/chat` 한 곳뿐이다.

**실시간 (v6 — 폴링 폐기, WebSocket)**:

```
채팅방 화면 로드
  → 과거 메시지: SSR 렌더 또는 초기 로드 API 1회
  → ws.js가 이 방의 WebSocket에 연결 (서버는 쿠키 검증 + 당사자 확인)

메시지 전송:   클라 message → 서버 DB 저장 → 방 전체에 message 브로드캐스트
               (보낸 본인 화면도 이 브로드캐스트로 추가 — 코드 경로가 하나로 통일)
presence:      연결 수립 = 입장, 연결 종료 = 이탈. 서버가 상대에게 presence 이벤트
거래완료 토글: POST /api/items/<id>/status 성공 시, 서버가 그 글의 열린 방들에 status 이벤트
연결 끊김:     ws.js가 재연결 후 초기 로드를 한 번 더 → 놓친 메시지를 메운다
```

- **Flask-SocketIO로 확정 (2026-08-25).** 방 join/leave와 브로드캐스트가 내장이라
  presence 구현이 짧다. `API.md` §3의 이벤트 이름을 SocketIO 이벤트명으로 그대로 쓴다.
- 서버 실행이 `app.run()`에서 `socketio.run(app)`으로 바뀐다 — `app.py`는 진근의
  파일이므로 진근이 고친다.

**판매자 페이지네이션 (`chat_room.html`)** — 라우트를 새로 만들지 않는다 (v5 유지):

```python
# GET /chats/<room_id> 안에서, 뷰어가 판매자일 때만
sibling_rooms = list(db.rooms.find({"item_id": room["item_id"]}).sort("created_at", 1))
```

## 6. 역할 분담과 접점 (v6 — 회의 확정)

역할의 축이 바뀌었다: v5는 "기능 덩어리별"(인증/거래/채팅), v6는 **진근만 영역 풀스택,
래혁·재성은 메인 기능을 프론트/백으로 수평 분할**이다.
(표기: A=진근 · B=래혁 · C=재성. 이전 커밋과 문서의 A/B/C는 이 대응으로 읽는다.)

| 담당 | 축 | 영역 |
|---|---|---|
| **진근** (A) | 영역 풀스택 | 로그인·회원가입(JWT 발급·쿠키 저장, 소속 4종 선택)·로그아웃 · **헤더**(검색 UI + DB 연동 검색 기능, 말풍선 아이콘, 햄버거) · **사이드바**(offcanvas + 카드 메뉴) · 사이드바에서 이어지는 **거래내역 · 로그아웃 · 커뮤니티**의 화면과 엔드포인트 전부 |
| **래혁** (B) | 프론트엔드 | 메인 기능(홈 피드 · 글 작성 · 물품 상세 · 채팅방 · 채팅목록)의 템플릿·CSS·JS — 페이지네이션 UI, 완료 카드 흑백 처리, ws.js, 토글 버튼 |
| **재성** (C) | 백엔드 | 같은 메인 기능의 라우트·DB 질의·WebSocket 서버 — items/chat 라우트, 방 찾기/생성, 브로드캐스트, status 토글 API |

> **파일 단위 경계는 아직 미확정.** §2의 담당 태그가 내 제안이다: 라우트 `.py`는 재성,
> `templates/`의 메인 화면과 `static/js/`는 래혁, 진근은 자기 영역의 `.py`와 템플릿을 모두.
> 셋이 각자 브랜치라서 "같은 파일을 두 사람이 안 건드리는" 경계가 머지 충돌 방어선이다.
> 팀에서 확정하면 이 표와 §2를 같이 고친다.

**접점 = 사전 합의가 필요한 계약** (이 문서와 `API.md`가 그 합의):
1. **재성의 라우트 ↔ 래혁의 템플릿**: `render_template()`에 넘기는 컨텍스트 변수 이름이 곧
   인터페이스다. 최소 계약 — `feed.html`: `items`, `page`, `total_pages`, `type` ·
   `item_detail.html`: `item`, `is_seller` · `chat_room.html`: `room`, `item`,
   `messages`, `is_seller`, `sibling_rooms` · `chat_list.html`: `buying_rooms`,
   `selling_rooms` (구매/판매 구분 표시 — 회의록).
   바꾸려면 둘이 합의하고 이 줄을 고친다.
2. **진근의 base.html ↔ 래혁의 템플릿**: `{% block content %}` 이름과 헤더가 차지하는
   마크업 구조. 래혁의 화면은 전부 `base.html`을 상속한다.
3. **진근의 헤더 ↔ 메인 기능**: 검색 폼은 `GET /search`(진근)로, 말풍선 아이콘은
   `/chats`(재성 라우트)로, 햄버거 메뉴의 Home은 `/`(재성 라우트)로 링크만 건다 —
   진근이 남의 라우트를 부르는 지점은 전부 링크라서 코드 결합이 없다.
   ⚠️ 말풍선 → `/chats` 링크는 회의록의 "헤더에서 채팅 목록이 나타나는 기능"을
   **페이지 이동으로 해석**한 것이다. 헤더 안 드롭다운이 맞다면 진근 몫으로 재배분 (§8).
4. **재성의 SocketIO 서버 ↔ 래혁의 ws.js**: `API.md` §3 이벤트 계약.
5. **래혁의 `_item_card.html` ↔ 진근의 `search.html`**: 카드 partial의 include 변수
   (`item` 하나). §2의 partial 제안이 승인되면 확정.

**계약을 바꾸는 변경은 양쪽 파일을 한 커밋으로.** 컨텍스트 변수나 이벤트 페이로드가
바뀌면 재성의 라우트와 래혁의 템플릿(또는 ws.js)이 같이 바뀌어야 페이지가 산다. 같은
파일을 안 건드려도 두 브랜치가 어긋나면 git 충돌 없이 화면이 깨진다 — 머지 충돌보다
발견이 늦다. 그래서 계약 변경은 둘이 합의한 뒤, 한 사람의 브랜치에서 라우트와 템플릿을
같이 고쳐 한 커밋으로 만든다. 소유권은 파일 단위지만, 파손 단위는 기능 단위다.

**1일차 오전은 진근이 크리티컬 패스** (유지): `base.html` + `@login_required`가 나와야
래혁·재성이 자기 화면을 끼워 넣을 수 있다. 그동안 래혁은 템플릿을 base 없이 목업으로,
재성은 라우트를 더미 데이터로 먼저 만들어도 된다.

## 7. 일정 (v6 기준으로 다시)

| 날 | 진근 | 래혁 | 재성 |
|---|---|---|---|
| 1일차 | base.html(헤더·사이드바) + JWT + 가입(소속 선택)/로그인/로그아웃 | 피드·작성·상세 템플릿 (목업 → base 상속) | items 라우트(작성·피드·상세·삭제) + 페이지네이션 질의 |
| 2일차 | 검색(/search) + 거래내역(판매 탭) | ws.js + 채팅 화면 + 완료 흑백·토글 UI | 방 찾기/생성 + SocketIO 서버(메시지·presence) + status 토글 API |
| 3일차 | — 합류: 검색→카드→방 생성→대화(실시간)→완료 토글 연쇄 시연 검증, 이후 P1 풀 — | | |

P1·P2 중 **커뮤니티는 진근 고정**(회의 확정), 나머지(글 수정, 안 읽음, 찜)는
자기 P0가 끝난 사람이 가져가는 공용 풀.

## 8. 미결 (팀 회의 안건)

1. **래혁/재성 파일 단위 경계 확정** — §2·§6의 제안(라우트=재성, 템플릿·JS=래혁,
   `_item_card.html` partial 포함)을 팀이 승인할지.
2. **채팅목록 진입 방식** — 말풍선 아이콘을 `/chats` 페이지 링크로 해석했다(§6 접점 3).
   헤더 안 드롭다운이 맞다면 진근 몫으로 재배분.
3. **검색 상세 범위** — 물품 제목만(P0)인지, 판매자 이름 검색까지인지. 진근이 조율.
4. **커뮤니티 우선순위** — 담당은 진근으로 확정됐으나 P2(시간 남으면) 유지인지 격상인지.
5. **사진 저장** — `static/uploads/` 로컬 디스크(추천, 위 구조 기준). S3는 범위 밖.
6. **JWT SECRET 공유 방법** — `.env` 파일로 공유하고 `.gitignore`에 등록 (repo에 올리지 않기).

확정된 것: MongoDB는 각자 로컬 설치(Atlas 기각) · DB 이름은 `jungle` ·
WebSocket 라이브러리는 **Flask-SocketIO** (2026-08-25).
