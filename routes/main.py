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

@bp.get("/history")
@login_required
def history():

    seller_id = g.user["_id"]
    items = list(
        db.items
        .find({"seller_id": seller_id})
        .sort("created_at", -1)
    )

    return render_template("history.html", selling_items=items)
