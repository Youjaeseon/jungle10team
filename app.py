"""정글장터 — Flask 앱 진입점.

Blueprint 를 등록하는 일만 한다. 라우트의 본체는 각 담당자의 routes/*.py
안에 있다 (ARCHITECTURE.md § 2).
"""
from flask import Flask

from routes.auth import bp as auth_bp
from routes.chat import chat_bp
from routes.items import items_bp
from routes.main import bp as main_bp

app = Flask(__name__)

app.register_blueprint(auth_bp)    # [진근] /signup /login /logout /api/login
app.register_blueprint(items_bp)   # [재성] / /items /items/<id> ...
app.register_blueprint(chat_bp)    # [재성] /chats /chats/<id> ...
app.register_blueprint(main_bp)

if __name__ == "__main__":
    # debug=True → .py 저장 시 서버 자동 재시작 + 템플릿은 새로고침만으로 반영.
    # 배포할 때는 반드시 끄기
    app.run(debug=True, port=5000)
