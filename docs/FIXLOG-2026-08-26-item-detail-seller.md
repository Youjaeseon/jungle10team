# item_detail 판매자 정보 누락 수정 — 재성님께

- 작성: 2026-08-26, 진근
- 대상 파일: `routes/items.py` (재성님 파일)
- 발견한 브랜치: `merge/full-stack` (`feature/auth` + `feature/team-rebuild` + `feature/chat`)
- 수정 범위: 1줄 추가

`app.py`에 남아 있던 래혁님의 임시 라우트를 걷어내고 `items_bp`·`chat_bp`를
등록한 뒤, 실제 화면을 열어 보는 과정에서 발견했습니다. 재성님 파일이라
원칙적으로는 제가 건드릴 자리가 아니지만, 브라우저 확인이 이 지점에서 막혀서
한 줄만 고치고 이 문서를 남깁니다. 마음에 안 드시면 되돌리셔도 됩니다.

---

## 증상

로그인한 상태로 `GET /items/<id>`를 열면 500이 났습니다. items 컬렉션에 있는
4건 전부 동일했습니다.

```
jinja2.exceptions.UndefinedError: 'seller' is undefined
  File "templates/item_detail.html", line 90, in block 'content'
    {{ seller.name[0] }}
```

## 원인

판매자 조회는 이미 정상이었습니다. `item_detail()`이 `db.users.find_one()`으로
판매자 문서를 제대로 가져오고 있었습니다. 문제는 **그 결과를 템플릿에 전달하는
경로**였습니다.

| | 위치 | 형태 |
|---|---|---|
| 라우트가 담은 곳 | `routes/items.py` | `item["seller"]` (item 딕셔너리 안) |
| 템플릿이 찾는 곳 | `templates/item_detail.html` 85~99행 | `seller` (최상위 변수) |

`render_template`에 `item`과 `is_seller`는 넘기는데 `seller`는 넘기지 않아서,
Jinja가 `seller`를 `Undefined`로 만들었습니다. 그 상태에서 `.name`에 접근하는
순간 `UndefinedError`가 납니다.

래혁님이 `app.py`에 만들어 두셨던 임시 라우트는 `seller`를 최상위로 넘기고
있었습니다. 그래서 임시 라우트로 화면을 볼 때는 정상이었고, 실제 백엔드로
교체하는 순간 드러났습니다. 두 분 사이의 계약 불일치입니다.

## 수정 내용

`routes/items.py`, `item_detail()`의 `render_template` 호출에 한 줄 추가했습니다.

```python
    return render_template(
        "item_detail.html",
        item=item,
        seller=seller,      # ← 이 줄만 추가
        is_seller=is_seller,
    )
```

`seller` 지역변수는 바로 위에서 이미 만들어 두신 것을 그대로 씁니다. 조회를
새로 하지 않습니다.

## 확인

```
GET /items/6a8dd1243dede93941b25754   200
GET /items/6a8dd1243dede93941b25755   200
GET /items/6a8dd1243dede93941b25756   200
GET /items/6a8dd1243dede93941b25757   200
```

판매자 블록도 실제로 그려집니다.

```html
<div class="seller-profile">
    <div class="seller-avatar" aria-hidden="true">조</div>
```

템플릿이 쓰는 필드는 `seller.name`과 `seller.lab` 둘뿐이고, `users` 문서에
모두 있습니다(`_id`, `username`, `name`, `lab`, `password_hash`,
`created_at`). 현재 items 4건의 `seller_id`는 전부 `users`에 실재하는
사용자를 가리킵니다.

---

## 재성님께서 판단하실 것

**1. `item["seller"] = seller` 줄을 남길지**

이 줄은 지금 아무 데서도 쓰이지 않습니다. `_item_card.html`과 `feed.html`은
`seller`를 참조하지 않고, `item_detail.html`은 최상위 `seller`만 씁니다.
의도하신 용도가 따로 있으면 그대로 두시고, 없으면 지우셔도 됩니다. 저는
건드리지 않았습니다.

**2. 판매자가 없는 경우**

`seller`가 `None`이면 템플릿 90행에서 같은 예외가 다시 납니다. 지금 데이터에는
해당하는 항목이 없어서 방어 코드를 넣지 않았습니다. 탈퇴 기능을 만드실 때
같이 정하시면 될 것 같습니다.

---

## 같은 확인 과정에서 발견한 다른 항목 (수정하지 않았습니다)

전달만 드립니다. 제가 손대지 않았습니다.

| 위치 | 증상 | 담당 |
|---|---|---|
| `routes/chat.py` `chat_list()` | `return`이 없어 `/chats`가 500. `TypeError: ... did not return a valid response` | 재성 |
| `routes/chat.py` 151행 | `@chat_bp.route("/chat/<item_id>/chat")` — `docs/API.md` §1과 `item_detail.html` 142행은 `/items/<id>/chat`을 가리킵니다. 현재 그 링크는 404 | 재성 |
| `routes/items.py` `feed()` | `?type=` 을 읽지 않아 유형 필터가 동작하지 않고, 템플릿이 쓰는 이름은 `selected_type`인데 `type=None`으로 넘어갑니다. API.md 기준 P2라 급하지 않습니다 | 재성 + 래혁 |
| `templates/feed.html` 36·43·50·57·88행 | `url_for('home', ...)` — 이제 엔드포인트가 `items.feed`라 `BuildError`로 `/`가 500 | 래혁 |

`routes/chat.py`에는 `@socketio.on` 핸들러가 아직 없어서, `app.py`에서
`socketio.init_app` / `socketio.run` 배선은 하지 않았습니다. 핸들러를
올리시면 그때 붙이겠습니다. 말씀 주세요.
