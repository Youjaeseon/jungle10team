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

from auth_util import login_required
from db import db


items_bp = Blueprint("items", __name__)

ITEMS_PER_PAGE = 20
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


# =========================================================
# 공통 함수
# =========================================================

def _to_object_id(value):
    try:
        return ObjectId(value)
    except Exception:
        return None


def _allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# =========================================================
# 홈 피드
# GET /
# =========================================================

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

    # 존재하지 않는 페이지 요청 시 마지막 페이지로 보정
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

    # -----------------------------------------------------
    # 판매자 정보 한 번에 조회
    # -----------------------------------------------------

    seller_ids = list({
        item["seller_id"]
        for item in items
        if item.get("seller_id")
    })

    sellers = {}

    if seller_ids:
        seller_docs = db.users.find({
            "_id": {
                "$in": seller_ids
            }
        })

        sellers = {
            seller["_id"]: seller
            for seller in seller_docs
        }

    # 각 상품에 판매자 정보 추가
    for item in items:
        item["seller"] = sellers.get(
            item.get("seller_id")
        )

    return render_template(
        "feed.html",
        items=items,
        page=page,
        total_pages=total_pages,
        type=None,
    )


# =========================================================
# 거래 글 작성 화면
# GET /items/new
# =========================================================

@items_bp.route("/items/new")
@login_required
def new_item():
    return render_template("item_write.html")


# =========================================================
# 거래 글 등록
# POST /items
# =========================================================

@items_bp.route("/items", methods=["POST"])
@login_required
def create_item():

    # -----------------------------------------------------
    # form 데이터
    # -----------------------------------------------------

    title = request.form.get(
        "title",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    item_type = request.form.get(
        "item_type",
        ""
    ).strip()

    price_raw = request.form.get(
        "price",
        ""
    ).strip()

    want_raw = request.form.get(
        "want",
        ""
    ).strip()

    photo_file = request.files.get("photo")

    # -----------------------------------------------------
    # 필수 입력 검증
    # -----------------------------------------------------

    if not title:
        flash("제목을 입력해주세요.")
        return redirect("/items/new")

    if not description:
        flash("설명을 입력해주세요.")
        return redirect("/items/new")

    if item_type not in {
        "sale",
        "swap",
        "free",
    }:
        flash("올바른 거래 유형을 선택해주세요.")
        return redirect("/items/new")

    # -----------------------------------------------------
    # 거래 유형별 데이터 처리
    # -----------------------------------------------------

    price = None
    want = None

    # 판매
    if item_type == "sale":

        if not price_raw:
            flash("판매 가격을 입력해주세요.")
            return redirect("/items/new")

        try:
            price = int(price_raw)

        except ValueError:
            flash("가격은 숫자로 입력해주세요.")
            return redirect("/items/new")

        if price < 0:
            flash("가격은 0원 이상이어야 합니다.")
            return redirect("/items/new")

    # 교환
    elif item_type == "swap":

        # 비어 있으면 '아무거나' 의미
        want = want_raw if want_raw else None

    # free는 price, want 둘 다 None

    # -----------------------------------------------------
    # 상품 ID 미리 생성
    # 이미지 파일명에도 사용
    # -----------------------------------------------------

    item_id = ObjectId()

    photo_filename = None

    # -----------------------------------------------------
    # 사진 저장
    # -----------------------------------------------------

    if photo_file and photo_file.filename:

        if not _allowed_file(photo_file.filename):
            flash("이미지 파일만 업로드할 수 있습니다.")
            return redirect("/items/new")

        # _allowed_file에서 이미 '.' 존재 여부를 검사했기 때문에
        # 여기서는 안전하게 확장자 추출 가능
        extension = (
            photo_file.filename
            .rsplit(".", 1)[1]
            .lower()
        )

        # 원본 파일명이 아닌 상품 ObjectId로 저장
        photo_filename = (
            f"{item_id}.{extension}"
        )

        upload_dir = os.path.join(
            current_app.root_path,
            "static",
            "uploads",
        )

        os.makedirs(
            upload_dir,
            exist_ok=True,
        )

        photo_path = os.path.join(
            upload_dir,
            photo_filename,
        )

        photo_file.save(photo_path)

    # -----------------------------------------------------
    # MongoDB 저장
    # -----------------------------------------------------

    item = {
        "_id": item_id,

        # JWT 인증 후 login_required에서 설정한 사용자
        "seller_id": g.user["_id"],

        "title": title,
        "description": description,
        "type": item_type,

        "price": price,
        "want": want,

        "photo": photo_filename,

        "status": "selling",

        "created_at": datetime.now(
            timezone.utc
        ),
    }

    db.items.insert_one(item)

    return redirect(
        f"/items/{item_id}"
    )


# =========================================================
# 물품 상세
# GET /items/<item_id>
# =========================================================

@items_bp.route("/items/<item_id>")
@login_required
def item_detail(item_id):

    item_oid = _to_object_id(item_id)

    if not item_oid:
        return (
            "존재하지 않는 상품입니다.",
            404,
        )

    item = db.items.find_one({
        "_id": item_oid
    })

    if not item:
        return (
            "존재하지 않는 상품입니다.",
            404,
        )

    # -----------------------------------------------------
    # 판매자 정보
    # -----------------------------------------------------

    seller = db.users.find_one({
        "_id": item["seller_id"]
    })

    item["seller"] = seller

    # -----------------------------------------------------
    # 현재 사용자가 판매자인지
    # -----------------------------------------------------

    is_seller = (
        item["seller_id"]
        == g.user["_id"]
    )

    return render_template(
        "item_detail.html",
        item=item,
        is_seller=is_seller,
    )


# =========================================================
# 물품 삭제
# POST /items/<item_id>/delete
# 판매자만 가능
# =========================================================

@items_bp.route(
    "/items/<item_id>/delete",
    methods=["POST"],
)
@login_required
def delete_item(item_id):

    item_oid = _to_object_id(item_id)

    if not item_oid:
        return (
            "존재하지 않는 상품입니다.",
            404,
        )

    item = db.items.find_one({
        "_id": item_oid
    })

    if not item:
        return (
            "존재하지 않는 상품입니다.",
            404,
        )

    # -----------------------------------------------------
    # 판매자 권한 검증
    # -----------------------------------------------------

    if item["seller_id"] != g.user["_id"]:
        return (
            "삭제 권한이 없습니다.",
            403,
        )

    # -----------------------------------------------------
    # 이미지 파일 삭제
    # -----------------------------------------------------

    if item.get("photo"):

        photo_path = os.path.join(
            current_app.root_path,
            "static",
            "uploads",
            item["photo"],
        )

        if os.path.exists(photo_path):

            try:
                os.remove(photo_path)

            except OSError:
                # 이미지 삭제 실패가
                # 상품 삭제 전체 실패로 이어지지는 않게 함
                pass

    # -----------------------------------------------------
    # 해당 상품의 채팅방 조회
    # -----------------------------------------------------

    room_ids = [
        room["_id"]
        for room in db.rooms.find(
            {
                "item_id": item_oid
            },
            {
                "_id": 1
            },
        )
    ]

    # -----------------------------------------------------
    # 상품 관련 채팅 데이터 삭제
    # -----------------------------------------------------

    if room_ids:

        db.messages.delete_many({
            "room_id": {
                "$in": room_ids
            }
        })

        db.rooms.delete_many({
            "_id": {
                "$in": room_ids
            }
        })

    # -----------------------------------------------------
    # 상품 삭제
    # -----------------------------------------------------

    db.items.delete_one({
        "_id": item_oid
    })

    return redirect("/")


# =========================================================
# 거래 상태 변경
# POST /api/items/<item_id>/status
#
# selling -> done
# done    -> selling
# =========================================================

@items_bp.route(
    "/api/items/<item_id>/status",
    methods=["POST"],
)
@login_required
def toggle_item_status(item_id):

    item_oid = _to_object_id(item_id)

    if not item_oid:
        return jsonify({
            "error": "item_not_found"
        }), 404

    item = db.items.find_one({
        "_id": item_oid
    })

    if not item:
        return jsonify({
            "error": "item_not_found"
        }), 404

    # -----------------------------------------------------
    # 판매자만 상태 변경 가능
    # -----------------------------------------------------

    if item["seller_id"] != g.user["_id"]:

        return jsonify({
            "error": "not_seller"
        }), 403

    current_status = item.get(
        "status",
        "selling",
    )

    if current_status == "selling":
        new_status = "done"

    else:
        new_status = "selling"

    # -----------------------------------------------------
    # MongoDB 상태 변경
    # -----------------------------------------------------

    db.items.update_one(
        {
            "_id": item_oid
        },
        {
            "$set": {
                "status": new_status
            }
        }
    )

    # -----------------------------------------------------
    # WebSocket 상태 브로드캐스트
    # -----------------------------------------------------

    try:
        # 순환 import 방지를 위해 함수 내부 import
        from routes.chat import socketio

        rooms = db.rooms.find(
            {
                "item_id": item_oid
            },
            {
                "_id": 1
            },
        )

        for room in rooms:

            socketio.emit(
                "status",
                {
                    "item_id": str(
                        item_oid
                    ),
                    "status": new_status,
                },
                to=f"room:{room['_id']}",
            )

    except Exception:
        # DB 상태 변경은 이미 성공했으므로
        # WebSocket 오류 때문에 API 전체를
        # 실패시키지 않는다.
        pass

    return jsonify({
        "ok": True,
        "status": new_status,
    })