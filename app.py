"""정글장터 Flask 앱 진입점과 프론트엔드 확인용 임시 데이터.

Blueprint, MongoDB, JWT와 Socket.IO 서버가 합쳐지기 전까지 화면을 확인할 수
있도록 docs/API.md와 docs/ARCHITECTURE.md의 계약과 같은 필드명을 사용한다.
"""
from math import ceil

from flask import Flask, render_template, request

app = Flask(__name__)


SAMPLE_ITEMS = [
    {"_id": "item-1", "seller_id": "user-200", "title": "기계식 키보드",
     "description": "정글에서 사용하던 기계식 키보드입니다.", "type": "sale",
     "price": 20000, "want": None, "photo": "6a8d6d10023a379e199b0415.png",
     "status": "selling", "created_at": "2026-08-26T14:20:00+09:00"},
    {"_id": "item-2", "seller_id": "user-201", "title": "정글 알고리즘 책",
     "description": "필요한 분께 나눔합니다.", "type": "free", "price": None,
     "want": None, "photo": None, "status": "selling",
     "created_at": "2026-08-26T13:10:00+09:00"},
    {"_id": "item-3", "seller_id": "user-202", "title": "무선 마우스",
     "description": "텀블러와 교환하고 싶습니다.", "type": "swap", "price": None,
     "want": "텀블러", "photo": None, "status": "selling",
     "created_at": "2026-08-26T12:00:00+09:00"},
    {"_id": "item-4", "seller_id": "user-203", "title": "27인치 모니터",
     "description": "정상 작동하는 모니터입니다.", "type": "sale", "price": 80000,
     "want": None, "photo": None, "status": "done",
     "created_at": "2026-08-25T20:00:00+09:00"},
    {"_id": "item-5", "seller_id": "user-204", "title": "안 쓰는 연습장",
     "description": "사용하지 않은 연습장을 나눔합니다.", "type": "free", "price": None,
     "want": None, "photo": None, "status": "selling",
     "created_at": "2026-08-25T19:00:00+09:00"},
    {"_id": "item-6", "seller_id": "user-205", "title": "휴대용 선풍기",
     "description": "멀티탭 또는 다른 물품도 제안받습니다.", "type": "swap", "price": None,
     "want": "멀티탭", "photo": None, "status": "selling",
     "created_at": "2026-08-25T18:00:00+09:00"},
]


@app.get("/")
def home():
    """MongoDB 연결 전 SSR 피드와 페이지네이션을 확인한다."""
    page = max(request.args.get("page", default=1, type=int) or 1, 1)
    selected_type = request.args.get("type", default="").strip()
    if selected_type not in {"", "sale", "free", "swap"}:
        selected_type = ""

    filtered_items = SAMPLE_ITEMS
    if selected_type:
        filtered_items = [item for item in SAMPLE_ITEMS if item["type"] == selected_type]

    per_page = 20
    total_pages = max(ceil(len(filtered_items) / per_page), 1)
    page = min(page, total_pages)
    start = (page - 1) * per_page

    return render_template(
        "feed.html",
        items=filtered_items[start:start + per_page],
        page=page,
        total_pages=total_pages,
        selected_type=selected_type,
    )


@app.get("/items/<item_id>")
def item_detail(item_id):
    """백엔드 연동 전 공식 물품·판매자 컨텍스트를 확인한다."""
    sample_item = {
        **SAMPLE_ITEMS[0],
        "_id": item_id,
        "description": (
            "정글에서 사용하던 기계식 키보드입니다.\n"
            "정상적으로 작동하고 사용감이 조금 있습니다.\n"
            "정글 건물 1층에서 직거래를 원합니다."
        ),
    }
    seller = {"_id": "user-200", "name": "13기 스페이드", "lab": "SW-AI LAB"}
    return render_template(
        "item_detail.html", item=sample_item, seller=seller, is_seller=False
    )


@app.get("/items/new")
def item_write():
    """백엔드 연동 전 거래 글 작성 UI를 확인한다."""
    return render_template("item_write.html")


@app.get("/chats")
def chat_list():
    """조인 결과를 템플릿용 뷰 모델로 가공한 채팅 목록 예시."""
    sample_chat_rooms = [
        {"_id": "room-1", "role": "buyer",
         "partner": {"_id": "user-201", "name": "13기 스페이드",
                     "lab": "SW-AI LAB", "initial": "스"},
         "item": {"_id": "item-1", "title": "기계식 키보드",
                  "type": "sale", "status": "selling"},
         "last_message": {"text": "오늘 저녁에 거래 가능하신가요?",
                          "created_at": "2026-08-26T14:30:00+09:00",
                          "display_time": "오후 2:30"}},
        {"_id": "room-2", "role": "seller",
         "partner": {"_id": "user-202", "name": "13기 클로버",
                     "lab": "GAME LAB", "initial": "클"},
         "item": {"_id": "item-2", "title": "정글 알고리즘 책",
                  "type": "free", "status": "selling"},
         "last_message": {"text": "네, 1층에서 만나요!",
                          "created_at": "2026-08-25T18:00:00+09:00",
                          "display_time": "어제"}},
        {"_id": "room-3", "role": "seller",
         "partner": {"_id": "user-203", "name": "13기 하트",
                     "lab": "GAME TECH LAB", "initial": "하"},
         "item": {"_id": "item-4", "title": "27인치 모니터",
                  "type": "sale", "status": "done"},
         "last_message": {"text": "좋은 거래 감사합니다.",
                          "created_at": "2026-08-24T16:00:00+09:00",
                          "display_time": "8월 24일"}},
    ]
    return render_template("chat_list.html", chat_rooms=sample_chat_rooms)


@app.get("/chats/<room_id>")
def chat_room(room_id):
    """공식 room·message 계약으로 1:1 채팅 UI를 확인한다."""
    sample_room = {
        "_id": room_id,
        "item_id": "item-1",
        "seller_id": "user-200",
        "buyer_id": "user-100",
        "partner": {"_id": "user-201", "name": "13기 스페이드",
                    "lab": "SW-AI LAB", "initial": "스"},
        "item": {"_id": "item-1", "title": "기계식 키보드",
                 "photo": "6a8d6d10023a379e199b0415.png", "type": "sale",
                 "status": "selling", "price": 20000, "want": None},
    }
    sample_messages = [
        {"_id": "message-1", "room_id": room_id, "sender_id": "user-201",
         "name": "13기 스페이드", "lab": "SW-AI LAB",
         "text": "안녕하세요! 키보드 아직 판매 중인가요?",
         "created_at": "2026-08-26T14:25:00+09:00", "display_time": "오후 2:25",
         "date_label": "2026년 8월 26일"},
        {"_id": "message-2", "room_id": room_id, "sender_id": "user-100",
         "name": "나", "lab": "SW-AI LAB", "text": "네, 아직 판매 중입니다.",
         "created_at": "2026-08-26T14:27:00+09:00", "display_time": "오후 2:27",
         "date_label": ""},
        {"_id": "message-3", "room_id": room_id, "sender_id": "user-201",
         "name": "13기 스페이드", "lab": "SW-AI LAB",
         "text": "오늘 저녁에 거래 가능하신가요?",
         "created_at": "2026-08-26T14:30:00+09:00", "display_time": "오후 2:30",
         "date_label": ""},
        {"_id": "message-4", "room_id": room_id, "sender_id": "user-100",
         "name": "나", "lab": "SW-AI LAB",
         "text": "네! 저녁 7시에 정글 건물 1층에서 가능합니다.",
         "created_at": "2026-08-26T14:31:00+09:00", "display_time": "오후 2:31",
         "date_label": ""},
    ]
    return render_template(
        "chat_room.html",
        room=sample_room,
        messages=sample_messages,
        current_user_id="user-100",
        is_seller=False,
        sibling_rooms=[],
        socket_enabled=False,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
