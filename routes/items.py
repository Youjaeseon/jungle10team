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
from werkzeug.utils import secure_filename

from auth_util import login_required
from db import db

items_bp = Blueprint("items", __name__)

ITEMS_PER_PAGE = 20
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif","webp"}

#==========================================================================
#공통함수
#==========================================================================

def to_active_id(value):
    try:
        return ObjectId(value)
    except Exception:
        return None

    # 파일 확장자 확인
def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS