# API 명세 — 정글장터

> 기준: 2026-08-25 팀 회의 (v6). 이전 판: `wireframe/wireframe-v4-mvp.html` + `DESIGN.md` (2026-08-24 v5).
> 원칙: **페이지 이동은 전부 SSR**(Jinja 렌더링), **Ajax는 JSON을 주고받는 `/api/` 경로**에만,
> **채팅은 WebSocket**(방마다 실시간 연결 + presence).
> 우선순위 표기가 없는 것은 전부 P0.

## v6에서 바뀐 것 (회의 확정)

1. **폴링 폐기 → WebSocket.** 채팅방마다 실시간 연결을 맺고, 같은 연결로 상대가
   방에 들어와 있는지(presence)도 표시한다. 라이브러리는 **Flask-SocketIO로 확정**
   (2026-08-25). 이벤트 계약은 §3.
2. **홈 피드 페이지네이션.** 페이지당 최대 20개, 하단 페이지 번호. 이미지 로딩 부담을 줄이기 위함.
3. **거래완료 = ON/OFF 토글.** `selling ⇄ done` 양방향 전이 허용. 409(already_done) 규칙 삭제.
   완료 글은 피드에서 '완료' 뱃지 + 사진 흑백 필터로 표시한다.
4. **물품 상세에 삭제 버튼.** 판매자 본인 글에만 그린다 (라우트는 v5부터 있던
   `POST /items/<id>/delete` 그대로).
5. **회원가입 소속 선택.** 기수(12·13·14기) 대신 소속 4종:
   `SW-AI LAB` · `GAME LAB` · `GAME TECH LAB` · `코치 및 운영진`.
6. **헤더 검색.** 물품 제목을 DB에서 검색하는 자체 검색 기능. (판매자 검색 등
   상세 범위는 미정 — §1의 `/search` 참고.)
7. **역할 재편.** 진근(A) = 인증·헤더·사이드바 영역 풀스택, 래혁(B) = 메인 기능
   프론트엔드, 재성(C) = 메인 기능 백엔드. 상세는 `ARCHITECTURE.md` §6.

## 0. 공통 규칙

- **인증**: 로그인 성공 시 JWT를 httpOnly 쿠키 `token`으로 발급.
  - SSR 페이지에서 인증 실패 → `302 /login` 리다이렉트.
  - `/api/` 경로에서 인증 실패 → `401 {"error": "login_required"}`.
  - WebSocket 연결 수립 시에도 같은 쿠키로 인증한다 (실패 시 연결 거부).
  - 구현: `@login_required` 데코레이터 하나를 만들어 페이지/API 동작을 모두 처리.
- **응답 형식**: `/api/`는 항상 JSON. 성공은 `{"ok": true, ...}`, 실패는 `{"error": "<코드>"}` + HTTP 상태 코드.
- **시각**: 모든 문서의 `created_at`은 서버가 UTC로 기록, 표시할 때 상대 시간("10분 전")으로 변환.

## 1. 페이지 라우트 (SSR — Jinja가 HTML 반환)

| Method | Path | 인증 | 담당 | 설명 |
|---|---|---|---|---|
| GET | `/login` | ✕ | 진근 | 로그인 폼 |
| GET | `/signup` | ✕ | 진근 | 회원가입 폼. 아이디·비밀번호·이름 + **소속 4종 선택** |
| POST | `/signup` | ✕ | 진근 | 가입 처리 → 성공 시 `302 /login`. 아이디 중복이면 폼 재렌더+에러 |
| GET | `/logout` | ○ | 진근 | `token` 쿠키 삭제 → `302 /login` (+"로그아웃되었어요" 안내) |
| GET | `/` | ○ | 래혁/재성 | 홈 피드. **`?page=N` — 페이지당 최대 20개, 페이지 안은 스크롤 + 하단 페이지 번호.** 완료 글은 '완료' 뱃지 + 사진 흑백. 유형 필터 칩은 P2 — 그때 `?type=` 파라미터를 붙인다 |
| GET | `/search` | ○ | 진근 | **검색 결과.** `?q=<검색어>`로 items 제목을 부분일치 검색, 피드와 같은 카드로 렌더. (판매자 이름 검색 등 확장 범위는 미정) |
| GET | `/items/new` | ○ | 래혁/재성 | 거래 글 작성 폼 |
| POST | `/items` | ○ | 래혁/재성 | 글 등록(multipart, 사진 1장) → `302 /` |
| GET | `/items/<id>` | ○ | 래혁/재성 | **물품 상세.** 사진 · 제목 · 가격 · 유형 뱃지 · 상태 뱃지 · 판매자(이름·소속) · 설명. 판매자 본인이면 **삭제 버튼 + 거래완료 토글**이 추가로 그려진다 |
| GET | `/items/<id>/chat` | ○ | 래혁/재성 | **채팅 입구.** 구매자면 (글, 나) 방을 찾거나 생성 → `302 /chats/<room_id>`. 판매자면 그 글의 첫 번째 방으로 `302`. 방이 없으면 `302 /items/<id>` + "아직 문의가 없어요" |
| POST | `/items/<id>/delete` | ○ 판매자만 | 래혁/재성 | 글 삭제 → `302 /` |
| GET | `/chats` | ○ | 래혁/재성 | 내가 참여한 1:1 방 목록 — **구매 중인 방과 판매 중인 방을 구분**해 보여준다(회의록). 헤더 말풍선 아이콘의 목적지 — 진입 방식 해석은 아래 주석 |
| GET | `/chats/<room_id>` | ○ 방 당사자만 | 래혁/재성 | 1:1 채팅. 상단에 물건 요약 한 줄. 입장하면 WebSocket 연결(§3). 뷰어가 판매자면 하단에 같은 글의 방 페이지네이션 |
| GET | `/history` | ○ | 진근 | **내 거래글**(구 활동내역 · 구 거래내역). `items.seller_id` 가 나인 글 전부를 한 목록으로 — 판매·교환·나눔을 가리지 않는다. 탭 없음. 정렬은 **거래완료 먼저, 같은 그룹 안에서는 `created_at` 내림차순** |
| GET/POST | `/items/<id>/edit` | ○ 판매자만 | 공용 풀 | **P1** 글 수정 |
| GET | `/community` `/community/new` `/community/<id>` | ○ | 진근 | **P2** 커뮤니티 3종 (거래 CRUD 복사). 엔드포인트 설계·구현은 진근 |

> **`/history` 의 구매 탭은 2026-08-27 에 제거됐다.** `items` 에 구매자 필드가 없고
> 결제도 구매 확정도 없어서(§4 · `DESIGN.md`) "누가 샀는지" 는 어디에도 남지 않는다.
> 그래서 구매 탭은 **내가 채팅방을 연 물건**(`rooms.buyer_id`)을 근사값으로 썼는데,
> 문의만 하고 사지 않은 것까지 '구매' 라고 부르게 되어 라벨이 실제보다 넓었다. 탭을
> 걷어내고 페이지를 '내가 올린 글' 하나로 좁혔다. **이 라우트는 이제 `rooms` 를 읽지
> 않는다.** 정확한 구매 기록이 필요해지면 거래완료 토글에서 구매자를 고르게 하고
> `items` 에 기록해야 하며, 그것은 팀 회의 안건이다.
>
> **정렬 규칙.** `status` 가 `"selling"` / `"done"` 문자열이라서 몽고의 `sort` 하나로는
> 완료를 앞에 놓을 수 없다 — 사전순으로는 `selling` 이 앞선다. `created_at` 내림차순으로
> 받아 온 뒤 완료 여부로 한 번 더 정렬한다. 파이썬 정렬이 stable 이라 그룹 안의 최신순은
> 그대로 남는다.
>
> 래혁/재성이 함께 적힌 행: 재성이 라우트(백엔드), 래혁이 그 화면의 템플릿·JS(프론트엔드)를
> 맡는다. 파일 단위 경계는 미확정 — 제안은 `ARCHITECTURE.md` §6.
>
> 회의록의 "말풍선 아이콘을 누르면 채팅 목록이 나타나는 기능은 헤더 역할(진근)의 일부"를
> 이 문서는 **아이콘 → `/chats` 페이지 링크**로 해석했다. 헤더 안 드롭다운으로 해석하면
> 진근의 몫이 늘어난다 — 팀 확인 필요 (`ARCHITECTURE.md` §8).
>
> `/items/<id>/chat`이 GET인데도 방을 만든다. 엄밀히는 POST가 맞지만, 재요청해도
> 기존 방을 재사용하므로 결과는 같다 (v5 판단 유지).
>
> 판매자 방 페이지네이션에는 라우트를 새로 만들지 않는다. `/chats/<room_id>` 템플릿
> 안에서 같은 글의 방 목록을 뽑아 번호를 그린다 (v5 판단 유지).

## 2. JSON API (Ajax)

### 인증

**POST `/api/login`**
```json
요청  {"username": "jungler13", "password": "········"}
성공  200 {"ok": true, "redirect": "/"}   ← 응답에 Set-Cookie: token=<JWT>; HttpOnly
실패  401 {"error": "invalid_credentials"}   → 폼 아래 인라인 에러 표시
```

### 거래 상태 — 토글

**POST `/api/items/<id>/status`** — 거래완료 ON/OFF (판매자 단독)
```json
성공  200 {"ok": true, "status": "done"}      ← selling이었으면 done으로
성공  200 {"ok": true, "status": "selling"}   ← done이었으면 selling으로
실패  403 {"error": "not_seller"}
```
> v5의 `POST /api/items/<id>/done`을 대체한다. 409(already_done)는 삭제 —
> 양방향 토글이므로 "이미 완료"가 에러가 아니다.
> 상태의 주인은 `items.status` 한 곳 (v5 판단 유지). 상태가 바뀌면 서버가
> 그 글의 열려 있는 채팅방들에 `status` 이벤트를 브로드캐스트한다(§3).

### 채팅 초기 로드

**GET `/api/rooms/<room_id>/messages`** — **방 입장 시 1회만** (폴링 아님)
```json
200 {"ok": true, "status": "selling", "is_seller": false, "messages": [
      {"id": "...", "sender_id": "...", "name": "조진근", "lab": "SW-AI LAB",
       "text": "110,000원까지는 맞춰드릴게요.", "created_at": "..."}
    ]}
실패  403 {"error": "not_member"}
```
- 과거 메시지는 이 REST 한 번으로 받고, 이후의 새 메시지는 전부 WebSocket으로 받는다.
- SSR 렌더 시점에 Jinja로 과거 메시지를 그려도 된다면 이 엔드포인트는 생략 가능 —
  구현하며 재성이 결정한다.

### P1 / P2

| Method | Path | 우선순위 | 설명 |
|---|---|---|---|
| GET | `/api/chats/unread` | P1 | navbar 💬 안 읽음 카운트 (WebSocket 활용 여부 미정) |
| POST | `/api/items/<id>/like` | P2 | 찜 토글 |

### 2.x 커뮤니티 댓글 (구현 완료, 2026-08-27 · 진근)

거래 채팅과 달리 **WebSocket을 쓰지 않는다.** 0.5초 AJAX 폴링이다. 커뮤니티는
동시 인원이 적고 즉각성 요구가 낮아, 소켓의 네임스페이스·룸·재연결 처리를
들이는 것보다 폴링이 단순하다고 판단했다. `routes/chat.py`의 SocketIO 계층은
건드리지 않는다.

경로가 `/api/`로 시작해야 하는 이유: `auth_util.py`의 `login_required`는 그때만
401 JSON을 돌려주고, 아니면 `/login`으로 302 리다이렉트한다. 폴링이 그것을
받으면 로그인 페이지 HTML을 JSON으로 파싱하려다 터진다.

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/community/<post_id>/comments?since=<id>` | 목록. `since`가 있으면 그 id 뒤에 달린 것만 |
| POST | `/api/community/<post_id>/comments` | 등록. body `{"text": "..."}` |
| POST | `/api/community/comments/<comment_id>/edit` | 본인 댓글 수정. body `{"text": "..."}` |
| POST | `/api/community/comments/<comment_id>/delete` | 본인 댓글 삭제 |

```
GET  /api/community/<post_id>/comments?since=<id>
성공  200 {"ok": true,
           "comments": [
             {"id": "...", "author_id": "...", "name": "조진근", "lab": "SW-AI LAB",
              "text": "저요저요", "created_at": "...", "updated_at": "...",
              "display_time": "08-27 09:12", "edited": false}
           ],
           "total": 12,
           "stamp": "2026-08-27T00:12:33.123456"}
실패  404 {"error": "post_not_found"} · 401 {"error": "login_required"}
```

**`total`과 `stamp`가 왜 필요한가.** `since` 방식은 "마지막 id 뒤에 생긴 것"만
볼 수 있어서, 남이 댓글을 수정하거나 삭제한 것은 구조적으로 관측되지 않는다.
그래서 두 값을 함께 내려보낸다 — `total`은 전체 개수(삭제를 잡는다), `stamp`는
가장 늦은 `updated_at`(수정을 잡는다). 클라이언트는 화면에 그려 둔 값과 이
둘이 어긋날 때만 전체를 다시 받는다. 평상시에는 빈 배열만 오간다.

`total`과 `stamp`는 `since` 여부와 무관하게 **항상 전체 기준**이며, 작성·수정·
삭제 응답에도 같이 실린다(그래야 자기 동작 직후 불필요한 전체 재요청이 없다).

저장은 `db.post_comments` 컬렉션이다. 게시글 문서의 `comments` 배열이 아니다.
목록 페이지의 "댓글 N"은 `post_list()`가 집계 한 번으로 센다.

에러 코드: `post_not_found` `comment_not_found` `not_author`(403)
`empty_text`(400) `too_long`(400, 500자 초과) `login_required`(401)

## 3. WebSocket 이벤트 계약 (Flask-SocketIO)

**연결**: 채팅방 화면(`/chats/<room_id>`)에 들어오면 클라이언트가 그 방의 WebSocket에
연결한다. 인증은 `token` 쿠키. 방 당사자가 아니면 서버가 연결을 거부한다.

| 방향 | 이벤트 | 페이로드 | 설명 |
|---|---|---|---|
| 클라 → 서버 | `message` | `{"text": "..."}` | 메시지 전송. 서버가 DB 저장 후 방 전체에 브로드캐스트 |
| 서버 → 클라 | `message` | `{"id", "sender_id", "name", "lab", "text", "created_at"}` | 새 메시지 (보낸 본인 포함 — 화면 추가는 이 이벤트 하나로 통일) |
| 서버 → 클라 | `presence` | `{"user_id": "...", "online": true|false}` | 상대의 방 입장/이탈. "상대방이 보고 있어요" 표시용 |
| 서버 → 클라 | `status` | `{"status": "selling"|"done"}` | 판매자가 거래완료를 토글했을 때. 뱃지·완료 표시 갱신 |
| 서버 → 클라 | `error` | `{"error": "empty_text" 등}` | 전송 실패 사유 |

- **확정**: Flask-SocketIO (2026-08-25). 클라이언트는 `io()` 연결 후 `join`을 emit해서
  방에 참가하고, 표의 이벤트 이름을 SocketIO 이벤트명으로 그대로 쓴다.
  서버 실행은 `socketio.run(app)` (`ARCHITECTURE.md` §5).
- 재접속: 연결이 끊기면 클라이언트가 재연결하고, 초기 로드 API를 다시 한 번 불러
  놓친 메시지를 메운다. (이 단순한 방식이 2박 3일의 정답 — 오프셋 동기화는 범위 밖)

## 4. 상태 전이 (거래 글)

```
selling(판매중) ⇄ done(거래완료)     — 판매자 단독, ON/OFF 토글
```
- **양방향** (v6 변경). 완료를 실수로 눌러도 다시 끄면 된다.
- 표시 규칙: 피드·내 거래글·상세·채팅 어디서든 `items.status` 하나를 읽어
  done이면 '완료' 뱃지 + 사진 흑백 필터.
