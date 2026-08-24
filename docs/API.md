# API 명세 — 크래프톤 당근

> 기준: `wireframe/wireframe-v3-final.html` + `DESIGN.md` (2026-08-24 스냅샷).
> 원칙: **페이지 이동은 전부 SSR**(Jinja 렌더링), **Ajax는 JSON을 주고받는 `/api/` 경로**에만.
> 우선순위 표기가 없는 것은 전부 P0.

## 0. 공통 규칙

- **인증**: 로그인 성공 시 JWT를 httpOnly 쿠키 `token`으로 발급 (팀 안건 1의 추천안).
  - SSR 페이지에서 인증 실패 → `302 /login` 리다이렉트.
  - `/api/` 경로에서 인증 실패 → `401 {"error": "login_required"}`.
  - 구현: `@login_required` 데코레이터 하나를 만들어 두 동작을 모두 처리.
- **응답 형식**: `/api/`는 항상 JSON. 성공은 `{"ok": true, ...}`, 실패는 `{"error": "<코드>"}` + HTTP 상태 코드.
- **폴링 방식**: 증분(`after` 파라미터) 없이 **전체 조회 → 스레드 영역 innerHTML 전체 교체** (와이어프레임 확정안). 3초 `setInterval`. 데이터가 커지면 그때 증분으로 최적화.
- **시각**: 모든 문서의 `created_at`은 서버가 UTC로 기록, 표시할 때 상대 시간("10분 전")으로 변환.

## 1. 페이지 라우트 (SSR — Jinja가 HTML 반환)

| Method | Path | 인증 | 설명 |
|---|---|---|---|
| GET | `/login` | ✕ | 로그인 폼 |
| GET | `/signup` | ✕ | 회원가입 폼 |
| POST | `/signup` | ✕ | 가입 처리 → 성공 시 `302 /login`. 아이디 중복이면 폼 재렌더+에러 |
| GET | `/logout` | ○ | `token` 쿠키 삭제 → `302 /login` |
| GET | `/` | ○ | 홈 피드. 글 목록 + 글마다 아고라 미리보기(참여자 수, 최근 발언 1건) |
| GET | `/items/new` | ○ | 거래 글 작성 폼 |
| POST | `/items` | ○ | 글 등록(multipart, 사진 1장) → `302 /items/<id>` |
| GET | `/items/<id>` | ○ | 글 상세 + 아고라 스레드 초기 렌더. 판매자 본인이면 🤝 버튼·삭제 버튼 렌더 |
| POST | `/items/<id>/delete` | ○ 판매자만 | 글 삭제 → `302 /` |
| GET | `/chats` | ○ | 내가 참여한 1:1 방 목록 |
| GET | `/chats/<room_id>` | ○ 방 당사자만 | 1:1 채팅방. 상단에 물건 카드 고정 |
| GET | `/history` | ○ | 거래내역. 판매 탭(P0) / 구매 탭(P1) |
| GET/POST | `/items/<id>/edit` | ○ 판매자만 | **P1** 글 수정 |
| GET | `/community` `/community/new` `/community/<id>` | ○ | **P2** 커뮤니티 3종 (거래 CRUD 복사) |

## 2. JSON API (Ajax)

### 인증

**POST `/api/login`**
```json
요청  {"username": "jungler13", "password": "········"}
성공  200 {"ok": true, "redirect": "/"}   ← 응답에 Set-Cookie: token=<JWT>; HttpOnly
실패  401 {"error": "invalid_credentials"}   → 폼 아래 인라인 에러 표시
```

### 아고라 (공개 협상)

**GET `/api/items/<id>/agora`** — 3초 폴링
```json
200 {"ok": true, "status": "selling", "messages": [
      {"id": "...", "user_id": "...", "name": "새벽코딩러", "cohort": "13기",
       "text": "10만 원에 주시면 지금 바로 갑니다", "created_at": "..."}
    ]}
```
- `status`도 함께 내려서, 폴링 중 예약중으로 바뀌면 클라이언트가 확정 카드를 그린다.
- 렌더링: 응답으로 스레드 영역 innerHTML 전체 교체. 🤝 버튼은 **뷰어가 판매자일 때만** 그린다(서버가 `is_seller`를 함께 내려줌).

**POST `/api/items/<id>/agora`**
```json
요청  {"text": "저는 105,000원이요!"}
성공  201 {"ok": true}      ← 클라이언트는 즉시 GET 한 번 더 호출해서 갱신
실패  400 {"error": "empty_text"} / 409 {"error": "item_done"}
```

**POST `/api/items/<id>/accept`** — 🤝 이 사람과 거래 (판매자 전용)
```json
요청  {"buyer_id": "<확정할 상대의 user_id>"}
성공  200 {"ok": true, "room_id": "<생성된 1:1 방 id>"}
실패  403 {"error": "not_seller"} / 409 {"error": "already_reserved"}
```
서버가 한 번에 처리하는 것: ① `items.status → "reserved"`, `items.buyer_id` 기록
② `rooms` 문서 생성(이미 있으면 재사용) ③ room_id 반환 → 클라이언트가 확정 카드 표시.

### 1:1 채팅

**GET `/api/rooms/<room_id>/messages`** — 3초 폴링 (아고라와 같은 폴링 코드 재사용)
```json
200 {"ok": true, "status": "reserved", "messages": [
      {"id": "...", "sender_id": "...", "name": "큰손", "text": "...", "created_at": "..."}
    ]}
```

**POST `/api/rooms/<room_id>/messages>`**
```json
요청  {"text": "좋아요. 계좌 공유드릴게요."}
성공  201 {"ok": true}
실패  403 {"error": "not_member"}
```

### 거래 상태

**POST `/api/items/<id>/done`** — 판매완료 처리 (판매자 단독)
```json
성공  200 {"ok": true, "status": "done"}
실패  403 {"error": "not_seller"} / 409 {"error": "not_reserved"}
```
> 상태의 주인은 `items.status` 한 곳. 방(room)에는 상태를 두지 않는다 —
> 채팅방·피드·상세·거래내역이 모두 items를 읽어서 뱃지를 그린다.

### P1 / P2

| Method | Path | 우선순위 | 설명 |
|---|---|---|---|
| GET | `/api/chats/unread` | P1 | navbar 💬 안 읽음 카운트 (폴링) |
| POST | `/api/items/<id>/like` | P2 | 찜 토글 |
| POST | `/api/community/<id>/comments` | P2 | 댓글 등록 (Ajax, 나머지 커뮤니티는 SSR) |

## 3. 상태 전이 (거래 글)

```
selling(판매중) ──🤝 accept(판매자)──▶ reserved(예약중) ──done(판매자)──▶ done(판매완료)
```
- 역방향 전이 없음 (취소 기능은 범위 밖 — 필요해지면 팀 논의).
- accept는 `selling`에서만, done은 `reserved`에서만 허용. 그 외는 409.
