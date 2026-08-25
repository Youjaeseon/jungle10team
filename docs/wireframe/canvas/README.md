# 발표용 아트보드 (Claude Design 캔버스)

아티팩트: https://claude.ai/code/artifact/eda93a62-914b-4ee8-ba31-3e2c4a1f41f9

## 무엇이 원본인가

| 파일 | 역할 |
|---|---|
| `_style.css` | 아트보드 8장이 공유하는 스타일 한 벌. 고딕(Noto Sans KR) · 본문 최소 20px |
| `bodies/<이름>.html` | 아트보드 한 장의 본문. **여기를 고친다** |
| `build_canvas.py` | 위 둘을 합쳐 `<이름>.dc.html`과 `canvas.json`을 만든다 |
| `<이름>.dc.html` | 생성물. 손으로 고치지 않는다 |
| `_probe/` | 검증용 단독 HTML. 생성물이고 git에 올리지 않는다 |

CSS가 8개 파일에 그대로 복제되는 구조라서, 한 곳만 고치면 전부 따라오도록 나눠 두었다.

## 고치는 순서

```bash
# 1. bodies/ 또는 _style.css 를 고친다
python3 build_canvas.py          # 2. .dc.html · canvas.json · _probe/ 재생성
bash ../src/shot.sh _probe/BuyerFlow.html /tmp/x.png   # 3. 넘침 확인 (1280x760)
```

`shot.sh`는 원격 폰트를 끊고 로컬 Noto Sans CJK KR로 떨어뜨린다. 실제 고딕 폭에서
글자가 잘리는지를 그대로 볼 수 있다.

## 다시 발행하기

`design` 스킬의 `seed-canvas.mjs`로 페이로드를 새로 만든 뒤, **기존 URL을 `url`로 넘겨서**
같은 링크에 덮어쓴다. 새 링크를 만들면 이미 공유한 주소가 죽는다.

## 아트보드 11장

| # | 파일 | 내용 |
|---|---|---|
| 1 | `Main` | 로그인 → 회원가입 |
| 2 | `HomeFeed` | 홈 거래 피드 |
| 3 | `BuyerFlow` | 구매자 — 피드 → 상세 → 채팅 (3단) |
| 4 | `SellerFlow` | 판매자 — 내 글 → 상세 → 챗룸 (3단 + 페이지네이션) |
| 5 | `WriteForm` | 거래 글 작성 |
| 6 | `Sidebar` | 햄버거 → offcanvas |
| 7 | `ChatList` | 사이드바 → 채팅목록 |
| 8 | `History` | 사이드바 → 거래내역 |
| 9 | `Logout` | 사이드바 → 로그아웃 |
| 10 | `Community` | 커뮤니티 (P2) |
| 11 | `Architecture` | 아키텍처 |

6~9번이 사이드바와 그 자식 화면들이다. 세 장 모두 왼쪽에 offcanvas가 열린 사이드바,
오른쪽에 목적지 화면을 빨간 테두리로 두고, 그 사이를 빨간 연결선이 잇는다.

## 흐름선 규칙

두 화면 이상인 보드에는 반드시 빨간 연결선(`.zl`)과 라벨(`.zlab`)을 둔다. 라벨은
**두 창 사이의 틈 안에** 가둔다 — 창 위로 넘치면 화면 안의 버튼을 가려 버린다.
한 화면짜리 보드(HomeFeed · WriteForm)에는 나가는 지점에 빨간 강조(`.mark`)를 준다.

## 기본 프로필 아이콘

회원가입에서 사진을 받지 않으므로 `.avatar` 하나가 모든 사용자를 대신한다.
`_style.css`의 `.avatar`에 data URI SVG로 박혀 있고, `.avatar.lg`는 목록용 큰 크기다.

## 글자 크기 규칙

플레이스홀더 두 자리만 20px 미만이다 — `.input`(입력란 안내 문구) 17px, `.url`(주소창) 16px.
그 밖에 20px 미만이 생기면 규칙 위반이다:

```bash
grep -n 'font-size:1[0-9]px' _style.css bodies/*.html
```
