"""크래프톤 당근 — Flask 앱 진입점.

지금은 화면 확인용 최소본이다. Blueprint 등록·DB 연결·JWT는
각자 담당 파일이 나오는 대로 여기에 붙인다 (ARCHITECTURE.md § 2).
"""
from flask import Flask, render_template

app = Flask(__name__)


@app.get("/")
def home():
    # TODO: [담당 B] routes/items.py 의 Blueprint 로 옮긴다
    return render_template("feed.html")


if __name__ == "__main__":
    # debug=True → .py 저장 시 서버 자동 재시작 + 템플릿은 새로고침만으로 반영.
    # 배포할 때는 반드시 끈다 (에러 페이지에 소스가 노출됨).
    app.run(debug=True, port=5000)
