"""정글장터 — Flask 앱 진입점.

헤더 UI 확인을 위해 만들었습니다. Blueprint 등록·DB 연결·JWT 등의 내용은
각자 담당 파일이 나오는 대로 여기에 붙이시면 됩니다(ARCHITECTURE.md § 2).
"""
from flask import Flask, render_template

from auth_util import login_required
from routes.auth import bp as auth_bp

app = Flask(__name__)
app.register_blueprint(auth_bp)   # [진근] /signup /login /logout


@app.get("/")
@login_required
def home():
    # TODO: [재성] routes/items.py 의 Blueprint 로 옮긴다
    return render_template("feed.html")

if __name__ == "__main__":
    # debug=True → .py 저장 시 서버 자동 재시작 + 템플릿은 새로고침만으로 반영.
    # 로컬에서 requirements.txt 깔고, venv 상태에서 app.py 보시면서 진행.
    # 배포할 때는 반드시 끄기
    app.run(debug=True, port=5000)
