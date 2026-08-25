"""JWT 발급과 검증. [진근]

로그인에 성공하면 토큰을 만들고(create_token), 이후 모든 요청에서는 쿠키에 실려 온
토큰을 검사한다(@login_required). 검사를 통과하면 g.user 에 사용자 문서가 담긴다.
설계 근거: ARCHITECTURE.md § 4
"""
import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from bson import ObjectId
from dotenv import load_dotenv
from flask import g, jsonify, redirect, request

from db import db

# .env 를 이 파일에서 읽는다. auth_util 을 import 하는 쪽(ex> auth.py)이 순서를 신경 쓰지 않아도 되게.
load_dotenv()

SECRET = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"
TOKEN_TTL = timedelta(hours=24)


def create_token(user_id):
    """user_id(ObjectId)를 담은 JWT 문자열을 만든다. 로그인 성공 시 호출."""
    payload = {
        "user_id": str(user_id),  # ObjectId 는 JSON 이 아니라서 문자열로 바꿔 담는다
        "exp": datetime.now(timezone.utc) + TOKEN_TTL,
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def login_required(view):
    """로그인 검사 데코레이터. 통과 → g.user 에 사용자 문서, 실패 → 401 또는 /login."""

    @wraps(view)  # 없으면 Flask 가 엔드포인트 이름 충돌로 죽는다
    def wrapper(*args, **kwargs):
        user = _user_from_cookie()
        if user is None:
            if request.path.startswith("/api/"):
                return jsonify({"error": "login_required"}), 401
            return redirect("/login")
        g.user = user
        return view(*args, **kwargs)

    return wrapper


def _user_from_cookie():
    """쿠키의 토큰을 검증하고 사용자 문서를 돌려준다. 하나라도 어긋나면 None."""
    token = request.cookies.get("token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:  # 만료 · 서명 불일치 · 형식 오류를 한 번에 받는다
        return None
    return db.users.find_one({"_id": ObjectId(payload["user_id"])})
