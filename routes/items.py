import os
from datetime import datetime, timezone

from bson import ObjectId
from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
)
from werkzeug.utils import secure_filename

from auth_util import login_required
from db import db

items_bp = Blueprint("items", __name__)

ITEMS_PER_PAGE = 20
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif","webp"}

#==========================================================================
#공통함수
#==========================================================================

def to_active_id(value):
    try:
        return ObjectId(value)
    except Exception:
        return None

    # 파일 확장자 확인
def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

#==========================================================================
#Home Feed
#==========================================================================
@items_bp.route("/")
@login_required
def feed():
    page = request.args.get("page", 1, type=int)

    if page < 1:
        page = 1

    query = {}

    total_items = db.items.count_documents(query)

    total_pages = max(
        1,
        (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    )

    # 존재하지 않는 페이지가 들어오면 마지막 페이지로 보정
    if page > total_pages:
        page = total_pages

    skip = (page - 1) * ITEMS_PER_PAGE

    items = list(
        db.items
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(ITEMS_PER_PAGE)
    )

    # 피드에서 판매자 이름/소속을 사용하도록
    seller_ids = list({
        item["seller_id"]
        for item in items
        if item.get("seller_id")
    })

    sellers = {}

    if seller_ids:
        seller_docs = db.users.find({
            "_id": {"$in": seller_ids}
        })

        sellers = {
            seller["_id"]: seller
            for seller in seller_docs
        }

    for item in items:
        seller = sellers.get(item.get("seller_id"))

        item["seller"] = seller

    return render_template(
        "feed.html",
        items=items,
        page=page,
        total_pages=total_pages,
        type=None,
    )

#==========================================================================
#거래 글 작성 화면(GET)
#==========================================================================
@items_bp.route("/items/new")
@login_required
def new_item():
    return render_template("item_write.html")

#=========================================================================
#거래 글 등록(POST)
#=========================================================================
@items_bp.route("/items", methods=["POST"])
@login_required
def create_item():
    title = request.form.get("title", "").strip() #strip()로 공백 제거
    description = request.form.get("description", "").strip()
    item_type = request.form.get("item_type", "").strip()
    price = request.form.get("price", "").strip()
    want_raw = request.form.get("want", "").strip()
    phone_file = request.files.get("phone")

    #필수 입력 확인
    if not title:
        flash("제목을 입력해주세요.")
        return redirect("/items/new")

    if not description:
        flash("설명을 입력해주세요.")
        return redirect("/items/new")
