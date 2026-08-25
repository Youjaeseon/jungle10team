"""회원가입 · 로그인 · 로그아웃. [진근]

설계 근거: API.md § 1(페이지 라우트) · § 2(POST /api/login) · ARCHITECTURE.md § 4
"""
from datetime import datetime, timezone
from functools import total_ordering

from flask import Blueprint, jsonify, make_response, redirect, render_template, request
from werkzeug.security import check_password_hash, generate_password_hash

from auth_util import TOKEN_TTL, create_token, login_required
from db import db

# 첫 인자 "auth" 는 엔드포인트 이름표. url_for("auth.signup_form") 처럼 쓰인다.
bp = Blueprint("auth", __name__)

# 소속 4종 (v6 회의 확정). 템플릿의 <select> 와 서버 검사가 이 하나를 함께 본다.
LABS = ("SW-AI LAB", "GAME LAB", "GAME TECH LAB", "코치 및 운영진")


@bp.get("/signup")
def signup_form():
    return render_template("signup.html", labs=LABS)


@bp.post("/signup")
def signup():
    # request.form 은 <input name="..."> 를 담은 딕셔너리. 없는 키는 KeyError 대신
    # 빈 문자열로 받으려고 .get 을 쓴다. strip() 으로 앞뒤 공백을 떼어 낸다.
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")   # 비밀번호는 공백도 문자니까 strip 안 함
    name = request.form.get("name", "").strip()
    lab = request.form.get("lab", "")

    if not (username and password and name) or lab not in LABS:
        return _error("빈 칸이 있거나 소속이 올바르지 않아요.", username, name)

    if db.users.find_one({"username": username}):
        return _error("이미 쓰는 아이디예요.", username, name)

    db.users.insert_one({
        "username": username,
        # 원문 비밀번호는 어디에도 저장하지 않는다. 해시는 되돌릴 수 없고,
        # 로그인 때는 같은 방식으로 다시 해싱해 비교(check_password_hash)한다.
        "password_hash": generate_password_hash(password),
        "name": name,
        "lab": lab,
        "created_at": datetime.now(timezone.utc),
    })
    return redirect("/login")


def _error(message, username, name):
    """폼을 다시 그린다. 입력하던 값은 되살리고, 비밀번호만 비운다."""
    return render_template(
        "signup.html", labs=LABS, error=message, username=username, name=name
    )


@bp.get("/login")
def login_form():
    return render_template("login.html")


@bp.post("/api/login")
def api_login():
    """아이디·비밀번호를 받아 JWT 를 쿠키로 심는다. 화면 갱신은 브라우저가 한다."""
    # 폼 제출이 아니라 fetch 가 보낸 JSON 이라서 request.form 이 아니라 get_json 을 쓴다.
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = db.users.find_one({"username": username})
    # 아이디가 없을 때와 비밀번호가 틀릴 때를 한 문구로 합친다 (아이디 존재 여부를 숨긴다).
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "invalid_credentials"}), 401

    response = make_response(jsonify({"ok": True, "redirect": "/"}))
    response.set_cookie(
        "token",
        create_token(user["_id"]),
        httponly=True,                        # 자바스크립트가 못 읽는다 (토큰 탈취 방어)
        max_age=int(TOKEN_TTL.total_seconds()),  # 토큰 수명과 쿠키 수명을 같은 값에서 뽑는다
    )
    return response


@bp.get("/logout")
@login_required
def logout():
    response = redirect("/login")
    response.delete_cookie("token")
    return response
