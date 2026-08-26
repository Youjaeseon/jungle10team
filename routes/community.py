"""커뮤니티 목록·작성·상세·삭제 SSR 라우트 + 댓글 JSON API.

댓글은 0.5초 AJAX 폴링으로 갱신한다. WebSocket 을 쓰지 않는다.
거래 채팅(routes/chat.py, 재성)의 SocketIO 계층은 건드리지 않는다.

댓글 저장: db.post_comments (게시글 문서의 comments 배열이 아니다)
  { _id, post_id: ObjectId, author_id: ObjectId, text: str,
    created_at: datetime(UTC), updated_at: datetime(UTC) }

API 경로가 /api/ 로 시작해야 하는 이유:
auth_util.py:42 의 login_required 는 경로가 /api/ 로 시작할 때만 401 JSON 을
돌려주고, 그렇지 않으면 /login 으로 302 리다이렉트한다. 폴링이 그 리다이렉트를
받으면 로그인 페이지 HTML 을 JSON 으로 파싱하려다 터진다.
"""

from datetime import datetime, timezone

from bson import ObjectId
from flask import (
    Blueprint,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from auth_util import login_required
from db import db
from routes.chat import _to_kst


community_bp = Blueprint("community", __name__)

POSTS_PER_PAGE = 20
COMMENT_MAX_LENGTH = 500
CATEGORIES = {
    "question": "질문",
    "info": "정보공유",
    "group_buy": "공동 구매",
    "free": "자유",
}


def _to_object_id(value):
    """URL 문자열을 MongoDB ObjectId로 바꾸고, 잘못된 값은 None으로 돌려준다."""
    try:
        return ObjectId(value)
    except Exception:
        return None


def _post_form_values():
    """작성 폼 값을 공백을 정리한 문자열로 읽는다."""
    return {
        "category": request.form.get("category", "").strip(),
        "title": request.form.get("title", "").strip(),
        "body": request.form.get("body", "").strip(),
    }


def _validate_post(values):
    if values["category"] not in CATEGORIES:
        return "카테고리를 선택해 주세요."
    if not values["title"]:
        return "제목을 입력해 주세요."
    if len(values["title"]) > 80:
        return "제목은 80자 이내로 입력해 주세요."
    if not values["body"]:
        return "내용을 입력해 주세요."
    if len(values["body"]) > 3000:
        return "내용은 3,000자 이내로 입력해 주세요."
    return None


def _validate_comment(text):
    """댓글 본문을 서버에서 검사한다.

    템플릿의 maxlength 는 브라우저에게 하는 부탁이지 약속이 아니다.
    fetch 는 그 입력창을 거치지 않고도 이 엔드포인트를 부를 수 있다.
    """
    if not text:
        return "empty_text"
    if len(text) > COMMENT_MAX_LENGTH:
        return "too_long"
    return None


def _comment_time(value):
    """UTC 로 저장된 시각을 게시판 표기(08-27 09:12)로 바꾼다.

    routes/chat.py 의 _display_time 은 "오후 9:50" 형태라 채팅용이다.
    게시판은 며칠 전 글에도 날짜가 필요하므로 여기서 따로 만든다.
    UTC 로 저장하고 표시할 때만 KST 로 바꾸는 원칙은 같다.
    """
    kst = _to_kst(value)
    if kst is None:
        return ""
    return kst.strftime("%m-%d %H:%M")


def _serialize_comment(comment, author=None):
    """댓글 문서를 화면·JSON 이 함께 쓰는 dict 로 바꾼다.

    ObjectId 와 datetime 은 JSON 으로 나가지 못하므로 str / isoformat 으로 바꾼다.
    author_id 를 문자열로 내보내는 것은, JS 가 String(c.author_id) === currentUserId
    로 본인 댓글을 판정하기 때문이다. 여기가 어긋나면 남의 댓글에 수정 버튼이 뜬다.

    is_mine 은 넣지 않는다. 템플릿과 JS 가 각자 current_user_id 와 비교하므로
    판정 기준이 "문자열끼리 비교" 한 가지로 유지된다.
    """
    if author is None:
        author = db.users.find_one({"_id": comment["author_id"]})

    created_at = comment["created_at"]
    updated_at = comment.get("updated_at", created_at)

    return {
        "id": str(comment["_id"]),
        "author_id": str(comment["author_id"]),
        "name": author.get("name", "알 수 없음") if author else "알 수 없음",
        "lab": author.get("lab", "") if author else "",
        "text": comment["text"],
        "created_at": created_at.isoformat(),
        "display_time": _comment_time(created_at),
        # 클라이언트가 "내가 그린 것 중 가장 늦은 수정 시각"을 계산해서 서버의
        # stamp 와 대조한다. 그래야 남이 새 댓글을 쓴 것과 기존 댓글을 고친
        # 것이 구분된다. 이 칸이 없으면 새 댓글마다 전체를 다시 받게 된다.
        "updated_at": updated_at.isoformat(),
        # 저장하지 않고 계산한다. 저장한 값과 실제가 어긋날 여지를 없앤다.
        "edited": updated_at != created_at,
    }


def _load_comments(post_oid, since_oid=None):
    """한 게시글의 댓글을 오래된 순으로 읽어 직렬화한다.

    since_oid 가 있으면 그 id 뒤에 달린 것만 돌려준다. ObjectId 는 생성 시각
    순으로 증가하므로 _id 비교만으로 "그 뒤에 생긴 것"이 정확히 갈린다.
    시각으로 자르는 방식과 달리 같은 밀리초에 두 개가 들어와도 새지 않는다.
    """
    query = {"post_id": post_oid}
    if since_oid is not None:
        query["_id"] = {"$gt": since_oid}

    comments = list(
        db.post_comments.find(query).sort("_id", 1)
    )
    if not comments:
        return []

    # 댓글마다 users 를 조회하면 20개일 때 20번 왕복한다. post_list 가
    # 작성자를 $in 으로 한 번에 읽는 것과 같은 방식으로 한 번에 읽는다.
    author_ids = list({comment["author_id"] for comment in comments})
    authors = {
        user["_id"]: user
        for user in db.users.find({"_id": {"$in": author_ids}})
    }

    return [
        _serialize_comment(comment, author=authors.get(comment["author_id"]))
        for comment in comments
    ]


def _comment_signal(post_oid):
    """폴링이 수정·삭제를 알아채기 위한 대조 신호 두 개를 한 번에 구한다.

    since 방식은 "마지막 id 뒤에 생긴 것"만 볼 수 있어서, 남이 댓글을 고치거나
    지운 것은 구조적으로 관측되지 않는다. 그래서 값싼 신호를 함께 내려보낸다.

      total — 전체 댓글 수. 누가 지우면 화면에 그린 개수와 어긋난다.
      stamp — 가장 늦은 updated_at. 누가 고치면 값이 바뀐다.

    클라이언트는 이 둘이 자기 상태와 어긋날 때만 전체를 다시 받는다.
    평상시에는 빈 배열만 오가므로 화면이 깜빡이지 않는다.
    """
    rows = list(db.post_comments.aggregate([
        {"$match": {"post_id": post_oid}},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "stamp": {"$max": "$updated_at"},
        }},
    ]))

    if not rows:
        return 0, ""

    stamp = rows[0].get("stamp")
    return rows[0]["total"], stamp.isoformat() if stamp else ""


@community_bp.get("/community")
@login_required
def post_list():
    """최신 커뮤니티 글을 카테고리 필터와 페이지 단위로 보여준다."""
    page = max(request.args.get("page", default=1, type=int) or 1, 1)
    selected_category = request.args.get("category", "").strip()

    query = {}
    if selected_category in CATEGORIES:
        query["category"] = selected_category
    else:
        selected_category = None

    total_posts = db.posts.count_documents(query)
    total_pages = max(1, (total_posts + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE)
    page = min(page, total_pages)

    posts = list(
        db.posts.find(query)
        .sort("created_at", -1)
        .skip((page - 1) * POSTS_PER_PAGE)
        .limit(POSTS_PER_PAGE)
    )

    author_ids = list({post.get("author_id") for post in posts if post.get("author_id")})
    authors = {
        user["_id"]: user
        for user in db.users.find({"_id": {"$in": author_ids}})
    } if author_ids else {}

    for post in posts:
        post["author"] = authors.get(post.get("author_id"))

    # 목록의 "댓글 N". 글마다 count_documents 를 부르면 20번 왕복한다.
    # 작성자를 $in 으로 한 번에 읽은 바로 위와 같은 방식으로 한 번에 센다.
    # 카운터 필드를 글 문서에 두지 않는 이유: 실제 개수와 어긋날 수 있고,
    # 이 변경 이전에 만들어진 글에는 그 필드가 없어 마이그레이션이 필요해진다.
    comment_counts = {
        row["_id"]: row["n"]
        for row in db.post_comments.aggregate([
            {"$match": {"post_id": {"$in": [post["_id"] for post in posts]}}},
            {"$group": {"_id": "$post_id", "n": {"$sum": 1}}},
        ])
    } if posts else {}

    for post in posts:
        post["comment_count"] = comment_counts.get(post["_id"], 0)

    return render_template(
        "community/list.html",
        posts=posts,
        categories=CATEGORIES,
        selected_category=selected_category,
        page=page,
        total_pages=total_pages,
    )


@community_bp.get("/community/new")
@login_required
def new_post():
    return render_template(
        "community/new.html",
        categories=CATEGORIES,
        form_values={"category": "question", "title": "", "body": ""},
        error=None,
    )


@community_bp.post("/community")
@login_required
def create_post():
    values = _post_form_values()
    error = _validate_post(values)

    if error:
        return render_template(
            "community/new.html",
            categories=CATEGORIES,
            form_values=values,
            error=error,
        ), 400

    post = {
        "author_id": g.user["_id"],
        "category": values["category"],
        "title": values["title"],
        "body": values["body"],
        "comments": [],
        "created_at": datetime.now(timezone.utc),
    }
    result = db.posts.insert_one(post)
    return redirect(url_for("community.post_detail", post_id=result.inserted_id))


@community_bp.get("/community/<post_id>")
@login_required
def post_detail(post_id):
    post_oid = _to_object_id(post_id)
    if post_oid is None:
        return "존재하지 않는 커뮤니티 글입니다.", 404

    post = db.posts.find_one({"_id": post_oid})
    if post is None:
        return "존재하지 않는 커뮤니티 글입니다.", 404

    author = db.users.find_one({"_id": post.get("author_id")})

    # 이미 쌓인 댓글은 SSR 이 그린다. 폴링은 "이 페이지를 연 뒤의 변화"만 나른다.
    # current_user_id 는 템플릿이 "내 댓글인가"를 가르는 기준이고, 비교는
    # 반드시 문자열끼리 해야 한다(ObjectId 와 str 을 비교하면 언제나 거짓이다).
    return render_template(
        "community/detail.html",
        post=post,
        author=author,
        category_label=CATEGORIES.get(post.get("category"), "기타"),
        is_author=post.get("author_id") == g.user["_id"],
        comments=_load_comments(post_oid),
        current_user_id=str(g.user["_id"]),
        # 초기 stamp 를 함께 넘긴다. 이것이 없으면 클라이언트가 첫 틱에서
        # "내가 아는 stamp 가 없다"는 이유로 전체를 한 번 더 받게 되고,
        # 방금 SSR 로 그린 목록을 곧바로 다시 그리는 낭비가 생긴다.
        comment_stamp=_comment_signal(post_oid)[1],
    )


@community_bp.post("/community/<post_id>/delete")
@login_required
def delete_post(post_id):
    post_oid = _to_object_id(post_id)
    if post_oid is None:
        return "존재하지 않는 커뮤니티 글입니다.", 404

    post = db.posts.find_one({"_id": post_oid})
    if post is None:
        return "존재하지 않는 커뮤니티 글입니다.", 404
    if post.get("author_id") != g.user["_id"]:
        return "삭제 권한이 없습니다.", 403

    # 글이 사라지면 그 아래 댓글도 함께 사라진다.
    # 글을 먼저 지우면 중간에 실패했을 때 주인 없는 댓글이 남는다. 댓글 먼저.
    db.post_comments.delete_many({"post_id": post_oid})
    db.posts.delete_one({"_id": post_oid})
    return redirect(url_for("community.post_list"))


# =========================================================
# 댓글 JSON API
# =========================================================
#
# 성공은 {"ok": true, ...}, 실패는 {"error": "<코드>"} + 4xx.
# routes/items.py:483 의 toggle_item_status 와 같은 모양이다.
#
# 메서드는 저장소 관례를 따른다. 이미 POST /community/<post_id>/delete 가
# 있으므로 파괴적 동작도 POST + 동사 경로로 통일한다. PATCH/DELETE 를
# 새로 들이지 않는다.


def _post_or_error(post_id):
    """게시글을 찾고, 없으면 (None, JSON 응답)을 돌려준다.

    네 엔드포인트가 전부 같은 두 관문을 지난다. 앞은 "글자 모양이 ObjectId 인가"
    (DB 를 보지 않는다), 뒤는 "그 글이 실제로 있는가". 순서가 바뀌면 잘못된
    문자열이 find_one 까지 흘러가 500 이 난다.
    """
    post_oid = _to_object_id(post_id)
    if post_oid is None:
        return None, (jsonify({"error": "post_not_found"}), 404)

    post = db.posts.find_one({"_id": post_oid})
    if post is None:
        return None, (jsonify({"error": "post_not_found"}), 404)

    return post_oid, None


def _owned_comment_or_error(comment_id):
    """댓글을 찾고 본인 것인지 확인한다.

    화면에서 버튼을 숨기는 것은 보안이 아니다. 버튼이 안 보여도 이 경로를
    직접 부르는 것은 누구나 할 수 있다. 진짜 방어선은 여기다.
    """
    comment_oid = _to_object_id(comment_id)
    if comment_oid is None:
        return None, (jsonify({"error": "comment_not_found"}), 404)

    comment = db.post_comments.find_one({"_id": comment_oid})
    if comment is None:
        return None, (jsonify({"error": "comment_not_found"}), 404)

    if comment["author_id"] != g.user["_id"]:
        return None, (jsonify({"error": "not_author"}), 403)

    return comment, None


@community_bp.get("/api/community/<post_id>/comments")
@login_required
def list_comments(post_id):
    """댓글 목록. since 가 있으면 그 뒤에 달린 것만 돌려준다.

    total 과 stamp 는 since 여부와 무관하게 항상 전체 기준으로 계산한다.
    클라이언트가 이 둘을 자기 상태와 대조해서 수정·삭제를 알아챈다.
    """
    post_oid, error = _post_or_error(post_id)
    if error:
        return error

    since_oid = _to_object_id(request.args.get("since", ""))
    total, stamp = _comment_signal(post_oid)

    return jsonify({
        "ok": True,
        "comments": _load_comments(post_oid, since_oid=since_oid),
        "total": total,
        "stamp": stamp,
    })


@community_bp.post("/api/community/<post_id>/comments")
@login_required
def create_comment(post_id):
    post_oid, error = _post_or_error(post_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", "")).strip()

    invalid = _validate_comment(text)
    if invalid:
        return jsonify({"error": invalid}), 400

    # created_at 과 updated_at 을 같은 값으로 넣는다. 두 번 now() 를 부르면
    # 미세하게 달라져서, 방금 쓴 댓글이 "수정됨"으로 표시된다.
    now = datetime.now(timezone.utc)
    result = db.post_comments.insert_one({
        "post_id": post_oid,
        "author_id": g.user["_id"],
        "text": text,
        "created_at": now,
        "updated_at": now,
    })

    comment = db.post_comments.find_one({"_id": result.inserted_id})
    total, stamp = _comment_signal(post_oid)

    return jsonify({
        "ok": True,
        "comment": _serialize_comment(comment, author=g.user),
        "total": total,
        "stamp": stamp,
    })


@community_bp.post("/api/community/comments/<comment_id>/edit")
@login_required
def edit_comment(comment_id):
    comment, error = _owned_comment_or_error(comment_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", "")).strip()

    invalid = _validate_comment(text)
    if invalid:
        return jsonify({"error": invalid}), 400

    # updated_at 만 갱신한다. created_at 은 그대로 두어야 "언제 쓴 글인가"가
    # 남고, 둘이 달라졌다는 사실이 곧 "수정됨" 표시의 근거가 된다.
    db.post_comments.update_one(
        {"_id": comment["_id"]},
        {"$set": {"text": text, "updated_at": datetime.now(timezone.utc)}},
    )

    updated = db.post_comments.find_one({"_id": comment["_id"]})
    total, stamp = _comment_signal(comment["post_id"])

    return jsonify({
        "ok": True,
        "comment": _serialize_comment(updated, author=g.user),
        "total": total,
        "stamp": stamp,
    })


@community_bp.post("/api/community/comments/<comment_id>/delete")
@login_required
def delete_comment(comment_id):
    comment, error = _owned_comment_or_error(comment_id)
    if error:
        return error

    db.post_comments.delete_one({"_id": comment["_id"]})
    total, stamp = _comment_signal(comment["post_id"])

    return jsonify({
        "ok": True,
        "id": str(comment["_id"]),
        "total": total,
        "stamp": stamp,
    })
