import os #JWT 인증
import jwt

from collections import defaultdict
from flask import Blueprint, flash, g, jsonify, redirect, render_template, request
from bson import ObjectId
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime, timezone
from db import db
from auth_util import login_required

chat_bp = Blueprint('chat', __name__)

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