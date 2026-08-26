"""정글장터 — Flask 앱 진입점.

Blueprint 를 등록하는 일만 한다. 라우트의 본체는 각 담당자의 routes/*.py
안에 있다 (ARCHITECTURE.md § 2).
"""
from flask import Flask, request

from routes.auth import bp as auth_bp
from routes.chat import chat_bp
from routes.community import community_bp
from routes.items import items_bp
from routes.main import bp as main_bp

app = Flask(__name__)

app.register_blueprint(auth_bp)    # [진근] /signup /login /logout /api/login
app.register_blueprint(items_bp)   # [재성] / /items /items/<id> ...
app.register_blueprint(chat_bp)    # [재성] /chats /chats/<id> ...
app.register_blueprint(main_bp)
app.register_blueprint(community_bp)  # /community /community/new /community/<id>


# 뒤로가기로 돌아온 페이지가 옛 화면을 보여주던 문제.
# 브라우저가 캐시에서 꺼내 쓰느라 서버에 묻지 않아서, 거래완료 토글이
# 피드·검색 결과에 반영되지 않았다. no-store 는 그 캐시를 아예 막는다.
#
# /static/ 은 제외한다. 업로드 사진이 장당 수백 KB 라서, 배포 뒤에는
# 페이지를 옮길 때마다 그것까지 다시 받으면 눈에 띄게 느려진다.
# 되살아나서 문제가 되는 것은 HTML 쪽이므로 목적은 그대로 달성된다.
@app.after_request
def no_store(response):
    if not request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"

    return response


if __name__ == "__main__":
    # debug=True → .py 저장 시 서버 자동 재시작 + 템플릿은 새로고침만으로 반영.
    # 배포할 때는 반드시 끄기
    app.run(debug=True, port=5000)
