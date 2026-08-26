"""검색 · 거래내역. [진근]

설계 근거: API.md § 1 (GET /search, GET /history) · ARCHITECTURE.md § 3
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
# 거래내역
# GET /history
#

@bp.get("/history")
@login_required
def history():

    seller = g.user["_id"]
    items = list(
        db.items
        .find({"seller_id": seller})
        .sort("created_at", -1)
    )

    return render_template("history.html", selling_itmes=items)

# 설계 근거: API.md:52 (판매 탭 P0 / 구매 탭 P1) · ARCHITECTURE.md:92
# 화면 확정: docs/wireframe/8. History@2x.png
#
# 판매 탭은 rooms 컬렉션을 쓰지 않는다.
# 상태의 주인이 items.status 하나뿐이라, db.items 를 seller_id 로 한 번
# 조회하면 끝난다. 구조는 위 search() 와 같고 조건 하나만 다르다.
# =========================================================

# TODO 2. 함수 정의. 인자는 받지 않는다.
#         로그인한 사용자는 login_required 가 g.user 에 심어 준다
#         (auth_util.py:45). g.user["_id"] 로 꺼내 쓴다.
#         → 7행 import 에 g 를 추가하지 않으면 여기서 NameError 가 난다.
#         쿼리 파라미터가 없으므로 search() 의 24행·28-29행 같은 가드는 없다.

# TODO 3. 내가 올린 글 조회. 베낄 자리는 search() 의 35-39행이다.
#         바뀌는 것은 find() 안의 조건 하나뿐 —
#         title 정규식 대신 seller_id 가 나인 것.
#         · seller_id 에는 ObjectId 가 그대로 들어 있다 (items.py:288 이
#           g.user["_id"] 를 변환 없이 넣는다). 그러니 여기서도 변환하지 않는다.
#         · .sort 키와 list() 로 감싸는 이유는 34행 주석과 같다.

# TODO 4. render_template("history.html", ...) 로 끝낸다.
#         넘기는 이름은 items 가 아니라 selling_items 다.
#         2단계에서 buying_items 가 같은 화면에 들어오기 때문에,
#         지금 items 로 두면 그때 이름을 바꿔야 한다.
