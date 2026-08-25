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
_socket_connections = {}

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

#채팅방 메세지 조회
def _get_room_messages(room_id):
    return f"chat: {room_id}"

#==========================================================================
# 채팅목록 (GET)
#==========================================================================
@chat_bp.route("/chats")
@login_required
def chat_list():
   user_id = g.user["_id"]

   rooms = list(
   db.rooms.find({
     "$or": [
         {"seller_id": user_id},
         {"buyer_id": user_id}
     ] 
   }).sort("created_at", -1)
   )

   buying_rooms = []
   selling_rooms = []

   for room in rooms:
      item = db.items.find_one({"_id": room["item_id"]})

      # 없으면 제외
      if not item:
         continue

      #상대방 찾기
      if user_id == room["seller_id"]:
         peer_id = room["buyer_id"]
         room_type = "selling"
      else:
            peer_id = room["seller_id"]
            room_type = "buying"

      peer = db.users.find_one({"_id": peer_id})

      #마지막 메세지
      last_message = db.message.find_one({"room_id": room["_id"]}, sort=[("created_at", -1)])

      room_data = {
         "room" : room,
         "item" : item,
         "peer" : peer,
         "last_message" : last_message,
      }

      if room_type == "selling":
            selling_rooms.append(room_data)
      else:
            buying_rooms.append(room_data)
            """
            구매와 판매 채팅을 각각 넘긴다.
            """
      return render_template("chat_list.html", selling_rooms=selling_rooms, buying_rooms=buying_rooms)

# =========================================================
# 채팅 입구(GET)
# 구매자:
#   (상품, 구매자) 조합의 기존 방 조회
#   없으면 새 방 생성
# 판매자:
#   해당 상품의 가장 오래된 첫 번째 방으로 이동
#   방이 하나도 없으면 상품 상세로 복귀
# =========================================================
@chat_bp.route("/chat/<item_id>/chat")
@login_required
def enter_chat(item_id):

   item_oid = _to_object_id(item_id)

   if not item_oid:
      return "존재하지 않거나 삭제된 상품입니다.",404

   item = db.items.find_one({"_id": item_oid})

   if not item:
      return "존재하지 않거나 삭제된 상품입니다.",404

   user_id = g.user["_id"]

   #판매자 본인이 누를 경우
   if item["seller_id"] == user_id:

      room = db.rooms.find_one({"item_id": item_oid}, sort=[("created_at", 1)])

      if not room:
         flash("아직 문의가 없습니다.")
         return redirect(f"/item/{item_id}")

      return redirect(f"/chats/{room['_id']}")

   #구매자
   room = db.rooms.find_one({"item_id": item_oid, "buyer_id": user_id})

   #없으면 생성
   if not room:
      result = db.rooms.insert_one({
         "item_id": item_oid,
         "buyer_id": user_id,
         "seller_id": item["seller_id"],
         "created_at": datetime.now(timezone.utc),
      })

      room_id = result.inserted_id

   else:
      room_id = room["_id"]

   return redirect(f"/chats/{room_id}")

# =========================================================
# 채팅방 페이지(GET)
# =========================================================
@chat_bp.route("/chats/<room_id>")
@login_required
def chat_room(room_id):
   room_oid = _to_object_id(room_id)

   if not room_oid:
      return "존재하지 않는 채팅방입니다.",404

   room = db.rooms.find_one({"_id": room_oid})

   if not room:
      return "존재하지 않는 채팅방입니다.",404

   user_id = g.user["_id"]

   #