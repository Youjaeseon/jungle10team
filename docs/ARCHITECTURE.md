# 구조 설계 — 크래프톤 당근

> **[구식 주의 — 2026-08-24 v4 MVP 피벗]** 이 문서는 v3(아고라 구조) 기준으로 작성됨.
> 아고라·판매자 확정·예약중·계좌 modal 관련 절은 무효 — 현재 기준은 `DESIGN.md`(v4).
> 카드 클릭 → 1:1 채팅 자동 개설, 상태 2단계(판매중 → 판매완료).

> 기준: `DESIGN.md` + `API.md` (2026-08-24 스냅샷). 손코딩으로 2박 3일에 완주하는 것이
> 목표라서, 모든 선택의 기준은 "가장 단순하고 배우기 좋은 형태"다.

## 1. 전체 그림

```
브라우저
 │  ① 페이지 이동(링크·폼 제출)          ② 제자리 갱신(fetch)
 │      GET /items/42                       GET /api/items/42/agora (3초 폴링)
 ▼                                          POST /api/items/42/accept …
Flask (app.py + Blueprint 3개)
 │  ① Jinja 템플릿 렌더 → HTML 반환        ② dict 반환 → JSON 반환
 │      render_template("item_detail.html")     jsonify(...)
 ▼
MongoDB (pymongo, 컬렉션 5개)
```

- **SSR 경로**: 브라우저 주소가 바뀌는 모든 이동. Jinja가 `base.html`을 상속한 템플릿을 렌더.
- **Ajax 경로**: 주소가 안 바뀌는 갱신 4종 — 아고라/채팅 폴링, 메시지 전송, 확정, 판매완료. (P1·P2: 뱃지, 찜, 댓글)
- JWT는 httpOnly 쿠키라서 **두 경로 모두 브라우저가 자동으로 토큰을 실어 보낸다.** 프론트에서 토큰을 만질 일이 없다.

## 2. 디렉토리 구조 (제안)

```
jungle10team/
├─ app.py                  # Flask 앱 생성, 설정, Blueprint 등록, 실행
├─ db.py                   # MongoClient 연결 1곳 (모든 라우트가 import)
├─ auth_util.py            # JWT 발급/검증 + @login_required 데코레이터
├─ requirements.txt        # flask, pymongo, pyjwt, (비밀번호 해시는 werkzeug 내장)
├─ routes/
│   ├─ auth.py             # [담당 A] /login /signup /logout, /api/login
│   ├─ items.py            # [담당 B] / /items/* + /api/items/* (아고라·확정·완료)
│   ├─ chat.py             # [담당 C] /chats/* + /api/rooms/*, /history
│   └─ community.py        # [P2] 거래 CRUD를 복사해서 작성
├─ templates/
│   ├─ base.html           # [담당 A] navbar + offcanvas + Bootstrap CDN + {% block %}
│   ├─ login.html  signup.html
│   ├─ feed.html  item_detail.html  item_write.html
│   ├─ chat_list.html  chat_room.html  history.html
│   └─ community/…         # [P2]
└─ static/
    ├─ js/poll.js          # 폴링 유틸 1개 — 아고라·1:1이 공유
    ├─ js/item.js          # 확정·완료·복사·(P1 유형 분기)
    └─ uploads/            # 업로드 사진 (파일명 = ObjectId.jpg)
```

원칙 두 개:
- **파일 수를 늘리지 않는다.** 계층(서비스 레이어, ORM, 클래스)을 추가하지 않는다.
  라우트 함수 안에서 pymongo를 바로 부르는 것이 이 규모의 정답이다.
- **한 사람 = Blueprint 하나.** 충돌 지점이 파일 단위로 격리된다.

## 3. MongoDB 컬렉션 (5개 + P2 1개)

```python
users:          {_id, username(유니크), password_hash, name, cohort, created_at}
items:          {_id, seller_id, title, description,
                 type: "sale"|"free"|"swap",
                 price: int|None,          # sale일 때만
                 want: str|None,           # swap일 때만 ("아무거나"는 None + want_any=True도 가능 — 팀 취향)
                 account: str|None,        # 선택 입력. 상세 페이지에는 안 뿌리고 modal·1:1에만
                 photo: str|None,          # static/uploads 안의 파일명
                 status: "selling"|"reserved"|"done",
                 buyer_id: None|ObjectId,  # accept 시 기록
                 created_at}
agora_messages: {_id, item_id, user_id, text, created_at}
rooms:          {_id, item_id, seller_id, buyer_id, created_at}   # 상태 없음! 상태는 items가 주인
messages:       {_id, room_id, sender_id, text, created_at}
posts (P2):     {_id, author_id, category, title, body,
                 comments: [{user_id, text, created_at}],  # 임베드로 충분
                 created_at}
```

- **상태의 주인은 `items.status` 한 곳.** 피드·상세·채팅방·거래내역의 뱃지가 전부 여기를 읽는다.
- 홈 피드의 아고라 미리보기 = 글마다 `agora_messages`에서 count + 최신 1건 조회.
  글 20개면 쿼리 40번인데 이 규모에서는 전혀 문제없다. `$lookup` 최적화는 하지 않는다.
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
```

데코레이터는 하나만 만들고, 페이지/API 구분은 `request.path.startswith("/api/")`로 나눈다.
**권한 검사는 항상 서버에서**: 🤝 버튼·삭제 버튼을 템플릿에서 `{% if g.user._id == item.seller_id %}`로
숨기는 것과 별개로, accept/done/delete 라우트 안에서도 같은 검사를 반복한다
(버튼 숨김은 UI, 라우트 검사가 보안).

## 5. 폴링 구조 (아고라·1:1 공용)

```js
// static/js/poll.js — 이 함수 하나를 두 화면이 공유
function startPolling(url, targetEl, renderFn) {
  async function tick() {
    const res = await fetch(url);
    if (res.ok) targetEl.innerHTML = renderFn(await res.json());
  }
  tick();
  return setInterval(tick, 3000);
}
```

- 증분 없이 **전체 교체**. 입력 중인 `<input>`은 스레드 영역 밖에 두어 교체에 휩쓸리지 않게 한다.
- 메시지 전송 성공 후에는 3초를 기다리지 말고 즉시 `tick()` 한 번 호출.
- 응답에 `status`가 같이 오므로, 폴링만으로 "다른 브라우저에서 확정됨 → 내 화면에 확정 카드 등장" 시연이 된다.

## 6. 역할 분담과 접점

> ⚠️ **아래 A/B/C 배분은 제안이며 아직 팀 확정 전이다.** 누가 어느 몫을 맡을지는 팀 회의에서
> 정한다. 다만 "한 사람 = Blueprint 하나"로 갈라지는 경계 자체는 배분과 무관하게 유효하다.

| 담당 | 영역 | 산출물 |
|---|---|---|
| **A** | 인증 + 공통 뼈대 + 거래내역 | `base.html`, `auth_util.py`, `routes/auth.py`, `history.html` |
| **B** | 거래 코어 | `routes/items.py`, 피드·상세·작성 템플릿, 계좌 modal, accept/done API |
| **C** | 채팅 + 폴링 | `routes/chat.py`, `poll.js`, 채팅 목록·1:1 템플릿 |

**접점 = 사전 합의가 필요한 계약 2개** (둘 다 이 문서가 그 합의):
1. B의 `POST /api/items/<id>/accept`가 C의 `rooms` 문서를 생성한다 → rooms 스키마(§3) 고정.
2. B가 저장하는 `agora_messages`를 C의 폴링이 읽는다 → 응답 JSON 모양(`API.md` §2) 고정.

**1일차 오전은 A가 크리티컬 패스**: `base.html` + `@login_required`가 나와야 B·C가 자기 페이지를
끼워 넣을 수 있다. 그동안 B·C는 각자 템플릿을 base 없이 목업으로 먼저 만들어도 된다.

## 7. 일정 제안 (P0 완주선)

| 날 | A | B | C |
|---|---|---|---|
| 1일차 | base.html + JWT + 가입/로그인 | 글 작성/삭제 + 피드 | poll.js + 채팅방 템플릿 |
| 2일차 | 거래내역(판매 탭) + 통합 테스트 | 상세 + 아고라 + 계좌 modal | 1:1 채팅 완성 |
| 3일차 | — 합류: accept→방 생성→완료 연쇄 시연 검증, 이후 P1 풀 — | | |

P1·P2는 고정 담당 없이 **자기 P0가 끝난 사람이 가져가는 공용 풀**로 운영.

## 8. 미결 (팀 회의 안건에 추가)

3. **MongoDB 실행 형태 (보류 중)** — 각자 로컬 설치 vs 공용 Atlas 무료 티어 하나. 추천은 Atlas 공용
   (연결 문자열 하나 공유하면 셋의 데이터가 합쳐져서 채팅 시연·통합 테스트가 쉬움)이나 미확정.
4. **사진 저장** — `static/uploads/` 로컬 디스크(추천, 위 구조 기준). S3는 범위 밖.
5. **JWT SECRET 공유 방법** — `.env` 파일로 공유하고 `.gitignore`에 등록 (repo에 올리지 않기).
