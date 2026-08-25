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
Flask (app.py + Blueprint 여러 개 + WebSocket 핸들러)
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
├─ app.py                  # Flask 앱 생성, 설정, Blueprint 등록, 실행
├─ db.py                   # MongoClient 연결 1곳 (모든 라우트가 import)
├─ auth_util.py            # [A] JWT 발급/검증 + @login_required 데코레이터
├─ requirements.txt        # flask, pymongo, pyjwt + WebSocket 라이브러리(미정)
├─ routes/
│   ├─ auth.py             # [A] /login /signup /logout, /api/login
│   ├─ main.py             # [A] /search /history  (헤더·사이드바에서 이어지는 화면)
│   ├─ community.py        # [A, P2] /community 3종
│   ├─ items.py            # [C] / · /items/new · /items/<id> · /items/<id>/delete
│   │                      #      + /api/items/<id>/status (피드·작성·상세·삭제·토글)
│   └─ chat.py             # [C] /items/<id>/chat · /chats/* · 채팅 초기 로드 API
│                          #      + WebSocket 핸들러 (라이브러리 확정 후 chat.py 안
│                          #        또는 ws.py 분리 — C가 결정)
├─ templates/
│   ├─ base.html           # [A] 헤더(검색·말풍선·햄버거) + offcanvas + Bootstrap CDN + {% block %}
│   ├─ login.html  signup.html  history.html          # [A]
│   ├─ feed.html  item_write.html  item_detail.html   # [B]
│   ├─ chat_list.html  chat_room.html                 # [B]
│   └─ community/…         # [A, P2]
└─ static/
    ├─ js/ws.js            # [B] WebSocket 클라이언트 (연결·이벤트 핸들링·재접속)
    ├─ js/item.js          # [B] 거래완료 토글·(P1 유형 분기)
    └─ uploads/            # 업로드 사진 (파일명 = ObjectId.jpg)
```

원칙 두 개 (유지):
- **파일 수를 늘리지 않는다.** 계층(서비스 레이어, ORM, 클래스)을 추가하지 않는다.
  라우트 함수 안에서 pymongo를 바로 부르는 것이 이 규모의 정답이다.
- **한 사람 = 파일 하나.** 셋이 각자 브랜치에서 작업 중이므로, 같은 파일을 두 사람이
  건드리지 않는 것이 머지 충돌을 막는 유일한 구조적 방어다. v5의 "한 사람 = Blueprint
  하나"가 v6 역할 재편(B 프론트 / C 백엔드)으로 "라우트 파일은 C, 템플릿·JS 파일은 B"로
  바뀌었다 — 경계가 Blueprint에서 **파일 확장자**로 이동했을 뿐, 원칙은 같다.

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

- **라이브러리 미정.** 후보: Flask-SocketIO(방 join/leave·브로드캐스트 내장이라
  presence 구현이 짧다 — 내 추천) vs flask-sock(더 가볍지만 방 관리를 직접 짠다).
  결정은 C와 팀의 몫. 어느 쪽이든 `API.md` §3의 이벤트 계약은 그대로 유효하다.
- 서버 실행 방식이 라이브러리에 따라 바뀔 수 있다(예: Flask-SocketIO는
  `socketio.run(app)`). 결정되는 날 `app.py`와 이 문서를 같이 고친다.

**판매자 페이지네이션 (`chat_room.html`)** — 라우트를 새로 만들지 않는다 (v5 유지):

```python
# GET /chats/<room_id> 안에서, 뷰어가 판매자일 때만
sibling_rooms = list(db.rooms.find({"item_id": room["item_id"]}).sort("created_at", 1))
```

## 6. 역할 분담과 접점 (v6 — 회의 확정)

역할의 축이 바뀌었다: v5는 "기능 덩어리별"(인증/거래/채팅), v6는 **A만 영역 풀스택,
B·C는 메인 기능을 프론트/백으로 수평 분할**이다.

| 담당 | 축 | 영역 |
|---|---|---|
| **A** | 영역 풀스택 | 로그인·회원가입(JWT 발급·쿠키 저장, 소속 4종 선택)·로그아웃 · **헤더**(검색 UI + DB 연동 검색 기능, 말풍선 아이콘, 햄버거) · **사이드바**(offcanvas + 카드 메뉴) · 사이드바에서 이어지는 **거래내역 · 로그아웃 · 커뮤니티**의 화면과 엔드포인트 전부 |
| **B** | 프론트엔드 | 메인 기능(홈 피드 · 글 작성 · 물품 상세 · 채팅방 · 채팅목록)의 템플릿·CSS·JS — 페이지네이션 UI, 완료 카드 흑백 처리, ws.js, 토글 버튼 |
| **C** | 백엔드 | 같은 메인 기능의 라우트·DB 질의·WebSocket 서버 — items/chat 라우트, 방 찾기/생성, 브로드캐스트, status 토글 API |

> **파일 단위 경계는 아직 미확정.** §2의 담당 태그가 내 제안이다: 라우트 `.py`는 C,
> `templates/`의 메인 화면과 `static/js/`는 B, A는 자기 영역의 `.py`와 템플릿을 모두.
> 셋이 각자 브랜치라서 "같은 파일을 두 사람이 안 건드리는" 경계가 머지 충돌 방어선이다.
> 팀에서 확정하면 이 표와 §2를 같이 고친다.

**접점 = 사전 합의가 필요한 계약** (이 문서와 `API.md`가 그 합의):
1. **C의 라우트 ↔ B의 템플릿**: `render_template()`에 넘기는 컨텍스트 변수 이름이 곧
   인터페이스다. 최소 계약 — `feed.html`: `items`, `page`, `total_pages`, `type` ·
   `item_detail.html`: `item`, `is_seller` · `chat_room.html`: `room`, `item`,
   `messages`, `is_seller`, `sibling_rooms` · `chat_list.html`: `rooms`.
   바꾸려면 둘이 합의하고 이 줄을 고친다.
2. **A의 base.html ↔ B의 템플릿**: `{% block content %}` 이름과 헤더가 차지하는
   마크업 구조. B의 화면은 전부 `base.html`을 상속한다.
3. **A의 헤더 ↔ 메인 기능**: 검색 폼은 `GET /search`(A)로, 말풍선 아이콘은
   `/chats`(C 라우트)로, 햄버거 메뉴의 Home은 `/`(C 라우트)로 링크만 건다 —
   A가 남의 라우트를 부르는 지점은 전부 링크라서 코드 결합이 없다.
4. **C의 WebSocket ↔ B의 ws.js**: `API.md` §3 이벤트 계약.

**1일차 오전은 A가 크리티컬 패스** (유지): `base.html` + `@login_required`가 나와야
B·C가 자기 화면을 끼워 넣을 수 있다. 그동안 B는 템플릿을 base 없이 목업으로,
C는 라우트를 더미 데이터로 먼저 만들어도 된다.

## 7. 일정 (v6 기준으로 다시)

| 날 | A | B | C |
|---|---|---|---|
| 1일차 | base.html(헤더·사이드바) + JWT + 가입(소속 선택)/로그인/로그아웃 | 피드·작성·상세 템플릿 (목업 → base 상속) | items 라우트(작성·피드·상세·삭제) + 페이지네이션 질의 |
| 2일차 | 검색(/search) + 거래내역(판매 탭) | ws.js + 채팅 화면 + 완료 흑백·토글 UI | 방 찾기/생성 + WebSocket 서버(메시지·presence) + status 토글 API |
| 3일차 | — 합류: 검색→카드→방 생성→대화(실시간)→완료 토글 연쇄 시연 검증, 이후 P1 풀 — | | |

P1·P2 중 **커뮤니티는 A 고정**(회의 확정), 나머지(글 수정, 안 읽음, 찜)는
자기 P0가 끝난 사람이 가져가는 공용 풀.

## 8. 미결 (팀 회의 안건)

1. **WebSocket 라이브러리** — Flask-SocketIO vs flask-sock. §5 참고. 실행 방식과
   requirements.txt가 이 결정에 걸려 있다.
2. **B/C 파일 단위 경계 확정** — §2·§6의 제안(라우트=C, 템플릿·JS=B)을 팀이 승인할지.
3. **검색 상세 범위** — 물품 제목만(P0)인지, 판매자 이름 검색까지인지. A가 조율.
4. **커뮤니티 우선순위** — 담당은 A로 확정됐으나 P2(시간 남으면) 유지인지 격상인지.
5. **사진 저장** — `static/uploads/` 로컬 디스크(추천, 위 구조 기준). S3는 범위 밖.
6. **JWT SECRET 공유 방법** — `.env` 파일로 공유하고 `.gitignore`에 등록 (repo에 올리지 않기).

확정된 것: MongoDB는 각자 로컬 설치(Atlas 기각), DB 이름은 `jungle`.
