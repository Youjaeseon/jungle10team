"""커뮤니티 목록·작성·상세·삭제 SSR 라우트."""

from datetime import datetime, timezone

from bson import ObjectId
from flask import Blueprint, g, redirect, render_template, request, url_for

from auth_util import login_required
from db import db


community_bp = Blueprint("community", __name__)

POSTS_PER_PAGE = 20
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
    return render_template(
        "community/detail.html",
        post=post,
        author=author,
        category_label=CATEGORIES.get(post.get("category"), "기타"),
        is_author=post.get("author_id") == g.user["_id"],
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

    db.posts.delete_one({"_id": post_oid})
    return redirect(url_for("community.post_list"))
