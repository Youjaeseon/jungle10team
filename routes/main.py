"""검색 · 내 거래글. [진근]

설계 근거: API.md § 1 (GET /search, GET /history) · ARCHITECTURE.md § 3

--------------------------------------------------------------------
2026-08-27 · /history 구매 탭 철회와 '활동내역 → 내 거래글' 재개명 [로테 작성]

  하루 전에 넣은 구매 탭을 도로 걷어냈다. 그때의 BEFORE/AFTER 는
  docs/review-history-buy-tab/ 에 그대로 남아 있고, README 머리에 철회 표시를
  붙여 두었다 — 현재 코드가 아니라 그 시점의 판단 기록으로 읽어야 한다.
  지금의 계약은 API.md:52 행과 그 아래 각주다.

  왜 걷어냈나:
    items 에 구매자를 가리키는 필드가 없어서, 구매 탭은 rooms.buyer_id
    ('내가 채팅방을 연 물건')를 근사값으로 썼다. 그러면 문의만 하고 사지 않은
    것까지 '구매' 로 불리게 되어 라벨이 내용보다 넓어진다. 근사를 정확하게
    만들려면 거래완료 토글에서 구매자를 고르게 해야 하는데, 그것은 P0 범위
    밖이다 (DESIGN.md § 잘라낸 것). 탭이 하나만 남으면서 탭 바도 함께 사라졌다.

  이 파일에서 바뀐 것:
    1) rooms 를 더 이상 읽지 않는다. distinct 와 $in 두 단계 조회가 통째로 빠졌다.
    2) selling_items → my_items. 목록에 교환·나눔 글도 들어가므로 selling 이라는
       이름이 내용을 좁게 말한다.
    3) 정렬이 두 단계가 됐다. 거래완료가 먼저, 같은 그룹 안에서는 최신순.

  같은 작업에서 함께 바뀐 파일: templates/history.html · templates/base.html:76 ·
  docs/{DESIGN,API,ARCHITECTURE,JINJA,BOOTSTRAP,DEPLOY}.md · CLAUDE.md
--------------------------------------------------------------------
"""
import re

from flask import Blueprint, redirect, render_template, request, g

from auth_util import login_required
from db import db

bp = Blueprint("main", __name__)


# =========================================================
# 검색 결과
# GET /search?q=<검색어>
# =========================================================

@bp.get("/search")
@login_required
def search():
    # ?q= 에 붙어 온 값. 없으면 "" 이므로 아래 .strip() 이 안전하다.
    keyword = request.args.get("q", "").strip()

    # 빈 검색어로 조회하면 빈 패턴이 전부에 걸려서 목록이 통째로 나온다.
    # 그건 검색이 아니므로 DB 를 두드리지 않고 홈으로 돌려보낸다.
    if not keyword:
        return redirect("/")

    # re.escape 로 "(" 나 "|" 를 평범한 글자로 강등시킨다.
    # 안 하면 "(" 하나에 OperationFailure 로 500, "|" 하나에 엉뚱한 OR 검색이 된다.
    # "$options": "i" 는 대소문자 무시. iPhone / QHD 같은 영문 제목 때문에 붙인다.
    # find 는 커서를 주고 커서는 한 번만 흐르므로, 템플릿에서 두 번 훑도록 list() 로 받는다.
    items = list(
        db.items
        .find({"title": {"$regex": re.escape(keyword), "$options": "i"}})
        .sort("created_at", -1)
    )

    # items 라는 이름은 feed.html 과 맞춘 것이다.
    # 나중에 _item_card.html 을 그대로 include 할 수 있다.
    # keyword 는 검색창에 되살릴 값이다.
    return render_template("search.html", items=items, keyword=keyword)

# =========================================================
# 내 거래글 (구 활동내역 · 구 거래내역)
# GET /history
#
# 설계 근거: API.md:52 와 그 아래 각주 · ARCHITECTURE.md:92
#            (상태의 주인은 items.status 하나)
#
# 내 글은 items 에 seller_id 로 박혀 있으므로 한 번 조회하면 끝난다. rooms 는
# 쓰지 않는다. type 으로도 거르지 않는다 — 판매도 교환도 나눔도 전부 '내가 올린
# 글' 이고, 어느 종류인지는 카드의 뱃지가 이미 보여준다.
#
# 정렬은 거래완료가 먼저다. 이 화면은 '지금 팔 것' 을 고르는 자리가 아니라
# '내가 무엇을 올렸는지' 를 훑는 자리라서, 끝난 거래를 아래로 밀어낼 이유가 없다.
# =========================================================

@bp.get("/history")
@login_required
def history():
    me = g.user["_id"]

    # 내가 올린 글.
    # list() 가 여기서는 필수다. find() 가 돌려주는 Cursor 에도 .sort() 가 있지만
    # 그건 몽고에 정렬을 시키는 다른 함수라서, 아래의 key= 를 넘기면 그대로 터진다.
    # 파이썬 리스트로 받아야 파이썬 정렬을 걸 수 있다.
    my_items = list(
        db.items
        .find({"seller_id": me})
        .sort("created_at", -1)
    )

    # 거래완료를 맨 앞으로 올린다.
    # status 가 "selling" / "done" 문자열이라서 몽고의 sort 하나로는 못 한다.
    # 사전순으로는 selling 이 앞서기 때문에 -1 을 걸어도 원하는 순서가 안 나온다.
    #
    # 파이썬 정렬은 stable 이라, 키가 같은 원소끼리는 원래 순서를 유지한다.
    # 위에서 이미 최신순으로 받아 왔으므로 그룹 안의 최신순은 저절로 살아남는다.
    # False < True 이므로, 완료일 때 False 가 되는 키를 오름차순으로 정렬하면
    # 완료 글이 앞에 온다. reverse=True 는 키의 뜻이 뒤집혀 읽기 어려우니 안 쓴다.
    # .get 의 기본값은 status 필드가 없는 초기 데이터 때문이다
    # (items.py:516-519 가 같은 이유로 같은 기본값을 쓴다).
    my_items.sort(key=lambda item: item.get("status", "selling") != "done")

    return render_template("history.html", my_items=my_items)
