import os #JWT 인증
from dns import message
import jwt

from collections import defaultdict
from flask import Blueprint, flash, g, jsonify, redirect, render_template, request
from bson import ObjectId
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime, timezone
from db import db
from auth_util import login_required

chat_bp = Blueprint('chat', __name__)

socketio = SocketIO()

# Socket 접속 상태 관리
# 브라우저 탭/재접속 고려
# ex) 같은 사용자가 같은 방에 여러개의 연결을 하는것을 방지하기 위해 연결 개수를 따로 센다.

_socket_connetions = {}

# 현재 연결 갯수 ex) 2개의 탭을 사용할 경우 하나만 껐을때 2->0이 아니라 2->1
_presence_counts = defaultdict(int)

#공통함수
# ==========================================================================

#문자열 ObjectId를 변환
def _to_object_id(value):
    try:
        return ObjectId(value)
    except Exception:
        return None

#프론트 전달을 json으로 변환
def _serialize_message(message, sender=None):
    """
    sender을 전달하지 않으면 DB에서 조회하여 가져옴.
    이미 채팅방이 존재하는 경우에는 sender를 전달하지 않아도 됨.
    """
    if sender is None:
      sender = db.users.find_one({"_id": message["sender_id"]})

    return {
        "id": str(message["_id"]),
        "sender_id": str(message["sender_id"]),
        "name": sender["name"] if sender else "알 수 없음",
        "lab": sender.get("lab") if sender else None,
        "text": message["text"],
        "created_at": message["created_at"].isoformat(),
    }

#SocketIo에서 token쿠키에서 로그인 사용자를 가져오는 함수
def _get_socket_user():
    token = request.cookies.get("token")

    if not token:
       return None

    secret = os.getenv("JWT_SECRET")

    if not secret:
      return None

    try:
      payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError:
      return None

    user_id = payload.get("user_id")

    if not user_id:
      return None

    user_oid = _to_object_id(user_id)

    if not user_oid:
      return None

    return db.users.find_one({"_id": user_oid})



   

@chat_bp.route('/items/<item_id>')
@login_required
def item_chat(item_id):
    try:
        item_oid = ObjectId(item_id)
    except Exception:
        return "존재하지 않는 상품입니다.", 404

    item = db.items.find_one({"_id": item_oid})

    if not item:
        return "존재하지 않는 상품입니다.", 404

    # 내 상품일 경우
    if item["seller_id"] == g.user[""]

@chat_bp.route('/chats/<room_id>')
def chat_room(room_id):
    try:
     room_oid = ObjectId(room_id)
    except Exception:
     return "존재하지 않는 채팅방입니다.", 404

room = db.rooms.find_one({"_id": room_oid})
if not room: 
    return "존재하지 않는 채팅방입니다.", 404

user_id = g.user["_id"]

   

@chat_bp.route("/api/rooms/<room_id>/messages", methods=["GET"])

@chat_bp.route("/api/rooms/<room_id>/messages", methods=["POST"])