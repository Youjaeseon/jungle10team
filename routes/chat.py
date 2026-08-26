import os
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import jwt
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
from flask_socketio import SocketIO, emit, join_room, leave_room

from auth_util import login_required
from db import db

chat_bp = Blueprint('chat', __name__)

socketio = SocketIO()

#========================================================================
#시간zone 설정
#========================================================================
KST = ZoneInfo("Asia/Seoul")

# =========================================================
# SocketIO 접속 상태
# =========================================================

# sid -> {"room_id": ObjectId, "user_id": ObjectId}
_socket_connections = {}

# (room_id, user_id) -> 연결 개수
# 같은 사용자가 탭을 여러 개 열었을 때를 고려
_presence_counts = defaultdict(int)


#========================================================================
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

#판매자,구매자 구별
def _is_room_member(room, user_id):
    return user_id in (
        room["seller_id"],
        room["buyer_id"],
    )

#소켓룸 이름
def _socket_room_name(room_id):
    return f"room:{room_id}"

#한국 시간 변환
def _to_kst(value):
    if not value:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(KST)

#시간 문자열
def _display_time(value):
    local_time = _to_kst(value)

    if not local_time:
        return ""

    hour = local_time.hour

    if hour < 12:
        period = "오전"
        display_hour = hour if hour != 0 else 12
    else:
        period = "오후"
        display_hour = hour - 12 if hour > 12 else 12

    return f"{period} {display_hour:02d}:{local_time.minute:02d}"

#채팅 날짜
def _date_label(value):
    local_time = _to_kst(value)

    if not local_time:
        return None

    return (
        f"{local_time.year}년 "
        f"{local_time.month}월 "
        f"{local_time.day}일"
    )

#html형식에 맞게 변환
def _partner_data(user):
    if not user:
        return {
            "_id": None,
            "name": "알 수 없음",
            "lab": "",
            "initial": "?",
        }

    name = user.get("name") or "알 수 없음"

    return {
        "_id": user["_id"],
        "name": name,
        "lab": user.get("lab") or "",
        "initial": name[0] if name else "?",
    }

#DB형식에 맞게 변환
def _serialize_message(message, sender=None, date_label=None):
    if sender is None:
        sender = db.users.find_one({
            "_id": message["sender_id"]
        })

    created_at = message["created_at"]

    return {
        # HTML에서는 message._id 사용
        "_id": message["_id"],

        # WebSocket/API에서는 id 사용
        "id": str(message["_id"]),

        "sender_id": str(message["sender_id"]),
        "name": (
            sender.get("name", "알 수 없음")
            if sender
            else "알 수 없음"
        ),
        "lab": (
            sender.get("lab", "")
            if sender
            else ""
        ),
        "text": message["text"],
        "created_at": created_at.isoformat(),
        "display_time": _display_time(created_at),
        "date_label": date_label,
    }

#날짜별로 메세지 구분선 표시
def _load_messages(room_id):
    raw_messages = list(
        db.messages
        .find({"room_id": room_id})
        .sort("created_at", 1)
    )

    result = []
    previous_date = None

    for message in raw_messages:

        created_at_kst = _to_kst(
            message["created_at"]
        )

        current_date = (
            created_at_kst.date()
            if created_at_kst
            else None
        )

        # 날짜가 달라졌을 때만 날짜 구분선 출력
        if current_date != previous_date:
            label = _date_label(
                message["created_at"]
            )
        else:
            label = None

        sender = db.users.find_one({
            "_id": message["sender_id"]
        })

        result.append(
            _serialize_message(
                message,
                sender=sender,
                date_label=label,
            )
        )

        previous_date = current_date

    return result

#소켓 사용자 확인
def _get_socket_user():
    token = request.cookies.get("token")

    if not token:
        return None

    secret = (
        current_app.config.get("JWT_SECRET")
        or os.getenv("JWT_SECRET")
        or current_app.config.get("SECRET_KEY")
    )

    if not secret:
        return None

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
        )

    except jwt.PyJWTError:
        return None

    user_id = payload.get("user_id")

    user_oid = _to_object_id(user_id)

    if not user_oid:
        return None

    return db.users.find_one({
        "_id": user_oid
    })


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
   })
   )

   chat_rooms = []

   for room in rooms:
      item = db.items.find_one({"_id": room["item_id"]})

      # 없으면 제외
      if not item:
         continue

      #상대방 찾기
      if user_id == room["seller_id"]:

         role = "seller"
         partner_id = room["buyer_id"]
      else:
         role = "buyer"
         partner_id = room["seller_id"]

      partner = db.users.find_one({"_id": partner_id})

      #마지막 메세지
      last_message_doc = db.messages.find_one(
            {
                "room_id": room["_id"]
            },
            sort=[
                ("created_at", -1)
            ],
        )

      if last_message_doc:

            last_message = {
                "text": last_message_doc["text"],
                "created_at": (
                    last_message_doc[
                        "created_at"
                    ].isoformat()
                ),
                "display_time": _display_time(
                    last_message_doc[
                        "created_at"
                    ]
                ),
            }

            sort_time = last_message_doc[
                "created_at"
            ]

      else:

            last_message = {
                "text": "아직 메시지가 없습니다.",
                "created_at": "",
                "display_time": "",
            }

            sort_time = room.get(
                "created_at",
                datetime.min.replace(
                    tzinfo=timezone.utc
                ),
            )

        #-------------------------------------------------
        # 변환
        # -------------------------------------------------

      chat_rooms.append({
            "_id": room["_id"],
            "item_id": room["item_id"],
            "seller_id": room["seller_id"],
            "buyer_id": room["buyer_id"],
            "created_at": room.get(
                "created_at"
            ),

            "partner": _partner_data(
                partner
            ),

            "item": item,

            "last_message": last_message,

            "role": role,

            # 화면에는 사용하지 않고 정렬용
            "_sort_time": sort_time,
        })

    # 마지막 대화가 최신인 방부터 표시
      chat_rooms.sort(
        key=lambda room: room["_sort_time"],
        reverse=True,
    )

    # 템플릿에서 필요 없는 정렬용 값 제거
      for room in chat_rooms:
        room.pop("_sort_time", None)

      return render_template(
        "chat_list.html",
        chat_rooms=chat_rooms,
    )

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

   # 방 당사자가 아니면 접근 금지
   if not _is_room_member(room, user_id):
        return "접근 권한이 없습니다.", 403

   item = db.items.find_one({"_id": room["item_id"]})

   if not item:
        return "존재하지 않는 상품입니다.", 404

   is_seller = user_id == room["seller_id"]

    # -----------------------------------------------------
    # 상대방
    # -----------------------------------------------------

   if is_seller:
        partner_id = room["buyer_id"]
   else:
        partner_id = room["seller_id"]

   partner = db.users.find_one({
        "_id": partner_id
    })

    # -----------------------------------------------------
    # MongoDB room 복사본에 화면용 값 추가
    # -----------------------------------------------------

   room_view = dict(room)

   room_view["partner"] = (
        _partner_data(partner)
    )

   room_view["item"] = item

    # -----------------------------------------------------
    # 기존 메시지
    # -----------------------------------------------------

   messages = _load_messages(
        room_oid
    )

    # -----------------------------------------------------
    # 판매자라면 같은 상품의 모든 구매자 방 조회
    # -----------------------------------------------------

   sibling_rooms = []

   if is_seller:

        sibling_rooms = list(
            db.rooms
            .find({
                "item_id": room["item_id"]
            })
            .sort(
                "created_at",
                1,
            )
        )

   return render_template(
        "chat_room.html",

        room=room_view,

        messages=messages,

        current_user_id=str(
            user_id
        ),

        socket_enabled=True,

        is_seller=is_seller,

        sibling_rooms=sibling_rooms,
    )

#=========================================================
#과거 메세지(GET)
#=========================================================
@chat_bp.route(
    "/api/rooms/<room_id>/messages",
    methods=["GET"],
)
@login_required
def get_messages(room_id):

    room_oid = _to_object_id(room_id)

    if not room_oid:
        return jsonify({
            "error": "room_not_found"
        }), 404

    room = db.rooms.find_one({
        "_id": room_oid
    })

    if not room:
        return jsonify({
            "error": "room_not_found"
        }), 404

    user_id = g.user["_id"]

    if not _is_room_member(
        room,
        user_id,
    ):
        return jsonify({
            "error": "not_member"
        }), 403

    item = db.items.find_one({
        "_id": room["item_id"]
    })

    if not item:
        return jsonify({
            "error": "item_not_found"
        }), 404

    messages = _load_messages(
        room_oid
    )

    return jsonify({
        "ok": True,

        "status": item.get(
            "status",
            "selling",
        ),

        "is_seller": (
            user_id
            == room["seller_id"]
        ),

        "messages": messages,
    })
#=========================================================
#SocketIo 연걸
#=========================================================
@socketio.on("connect")
def socket_connet(auth=None):

    user = _get_socket_user()
    #연결 거부
    if not user:
        return False

    return True
#=========================================================
# Socket 방 참가
# =========================================================
@socketio.on("join")
def socket_join(data):

   user = _get_socket_user()

   if not user:
       emit(
           "error",
           {"error": "login_required"},
       )
       return

   if not isinstance(data, dict):
         emit(
            "error",
            {"error": "room_not_found"},
         )
         return

   room_oid = _to_object_id(
       data.get("room_id")
   )

   if not room_oid:

         emit(
            "error",
            {"error": "room_not_found"},
         )
         return

   room = db.rooms.find_one({
         "_id": room_oid
      })
   
   if not room:
         emit(
            "error",
            {"error": "room_not_found"},
         )
         return

   user_id = user["_id"]

   if not _is_room_member(
         room,
         user_id,
   ):
         emit(
            "error",
            {"error": "not_member"},
         )
         return

   #기존방이 다른 방에 join되어 있으면 정리
   previous = _socket_connections.get(
         request.sid
   )

   if previous:

       old_room_id = previous["room_id"]

       old_user_id = previous["user_id"]

       old_room_name = (_socket_room_name(
            old_room_id
        ))

       old_key = (str(old_room_id), str(old_user_id))

       leave_room(old_room_name)

       if _presence_counts[old_key] > 0:
           _presence_counts[old_key] -= 1

       if _presence_counts[old_key] == 0:
            _presence_counts.pop(old_key, None)

            emit(
                "presence",
                {
                    "user_id": str(old_user_id),
                    "online": False,
                },
                to=old_room_name,
                include_self=False,
            )