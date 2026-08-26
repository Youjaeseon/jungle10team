"""정글장터 — Flask 앱 진입점.

Blueprint 를 등록하는 일만 한다. 라우트의 본체는 각 담당자의 routes/*.py
안에 있다 (ARCHITECTURE.md § 2).
"""
from os import environ
from flask import Flask, request

from routes.auth import bp as auth_bp
from routes.chat import chat_bp, socketio
from routes.community import community_bp
from routes.items import items_bp
from routes.main import bp as main_bp

app = Flask(__name__)

# flash() 는 메시지를 Flask session 에 담고, session 은 이 키로 서명한 쿠키에 실린다.
# 키가 없으면 routes/items.py 의 입력 검증이 flash 를 부르는 순간 500 이 난다.
# 정상 경로에서는 터지지 않아서, 값을 빠뜨리면 발표 도중에야 드러난다.
#
# 환경변수는 auth_util.py 의 load_dotenv() 가 올린다. 위 import 블록이
# routes.auth → auth_util 을 먼저 끌어오기 때문에 이 줄에서는 이미 읽을 수 있다.
# import 순서에 기댄 구조이므로, 순서를 바꿀 때는 여기가 먼저 깨진다.
app.secret_key = environ["FLASK_SECRET"]

app.register_blueprint(auth_bp)    # [진근] /signup /login /logout /api/login
app.register_blueprint(items_bp)   # [재성] / /items /items/<id> ...
app.register_blueprint(chat_bp)    # [재성] /chats /chats/<id> ...
app.register_blueprint(main_bp)
app.register_blueprint(community_bp)  # /community /community/new /community/<id>
socketio.init_app(app)

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
    # host="0.0.0.0" — 기본값 127.0.0.1 은 EC2 인스턴스 바깥에서 닿지 않는다.
    #
    # debug 는 .env 의 FLASK_DEBUG 로 가른다. 켜면 .py 저장 시 자동 재시작이
    # 되지만, 예외가 났을 때 에러 화면에 소스가 그대로 나온다. 그래서 로컬
    # .env 에만 FLASK_DEBUG=1 을 두고 배포 서버 .env 에는 넣지 않는다.
    #
    # allow_unsafe_werkzeug — Flask-SocketIO 는 내장 개발 서버가 운영처럼
    # 도는 것을 막는데, 이 플래그가 그 차단을 푼다.
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=environ.get("FLASK_DEBUG") == "1",
        allow_unsafe_werkzeug=True,
    )
