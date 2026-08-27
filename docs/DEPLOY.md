# 배포 런북 — AWS EC2

> 작성: 2026-08-26. 갱신: 2026-08-27, 기준 `origin/main` @ 85fcb7e (PR #5 병합본).
> 아직 인스턴스를 만들지 않은 상태에서 쓴 문서다. 값(퍼블릭 IP, 키페어 이름)은
> 프로비저닝한 뒤에 채운다. 코드가 진실이므로, 이 문서와 코드가 어긋나면 코드를 믿는다.
>
> § 2 부터 § 7 까지의 절차는 `deploy/bootstrap.sh` 한 번으로 끝난다. 아래 본문은
> 그 스크립트가 무엇을 왜 하는지를 설명하는 것이고, 손으로 따라 할 수도 있다.

목표는 발표 당일에 진근의 노트북 브라우저에서 `http://<퍼블릭IP>:5000` 을 열어
정글장터가 그대로 돌아가는 것이다. 홈 피드 페이지네이션, 물품 상세, 채팅,
채팅목록, 내 거래글, 검색을 보여준다.

---

## 0. 인스턴스를 만들기 전에 정한 것

| 항목 | 선택 | 이유 |
|---|---|---|
| AMI | Ubuntu 24.04 LTS | 기본 파이썬이 3.12 라서 `requirements.txt` 의 고정 버전이 그대로 설치된다. Amazon Linux 2023 은 3.9 라서 Flask 3.1.3 설치가 깨질 수 있다. |
| 인스턴스 타입 | t3.small | 메모리 2GB. MongoDB 와 Flask 를 한 인스턴스에서 돌린다. t2.micro(1GB) 는 발표 도중 OOM 으로 죽을 여지가 있고, 쓴다면 swap 2GB 를 반드시 잡는다. |
| 리전 | ap-northeast-2 (서울) | 발표 때 응답 지연이 가장 짧다. |
| 포트 | 5000 을 그대로 연다 | nginx 를 두지 않는다. 80 포트나 HTTPS 가 필요해지면 그때 넣는다. |
| 웹서버 | Flask 내장 서버 | 데모 한 번을 위한 것이다. gunicorn 은 Flask-SocketIO 와 함께 쓰려면 worker class 설정이 따로 필요해서, 이번 규모에서는 얻는 것보다 잃는 것이 많다. |

프리티어 t2.micro 를 쓰기로 바꾼다면 swap 을 먼저 잡는다.

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 1. AWS 콘솔에서 하는 일

1. EC2 → 인스턴스 시작 → Ubuntu 24.04 LTS, t3.small 을 고른다.
2. 키페어를 새로 만들고 `.pem` 파일을 내려받는다. 이 파일은 다시 받을 수 없다.
   로컬에서 `chmod 400 <키>.pem` 을 해 두지 않으면 SSH 가 키를 거부한다.
3. 보안 그룹의 인바운드 규칙에 두 줄을 넣는다.
   - SSH, TCP 22, 소스는 내 IP
   - 사용자 지정 TCP, **5000**, 소스는 `0.0.0.0/0`
4. 퍼블릭 IPv4 주소를 적어 둔다. 인스턴스를 껐다 켜면 이 주소가 바뀐다.
   발표 전날에 중지할 계획이라면 탄력적 IP 를 붙여 두는 편이 안전하다.

접속:

```bash
ssh -i <키>.pem ubuntu@<퍼블릭IP>
```

---

## 2. 인스턴스 기본 준비

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip git
```

---

## 3. MongoDB 설치

데이터베이스 이름은 `jungle` 이다. 팀원 셋이 모두 같은 이름을 쓴다는 것이 이미 정해진
사실이고, `db.py` 가 `mongodb://localhost:27017` 을 하드코딩하고 있어서 앱과 DB 가
같은 인스턴스에 있어야 한다.

```bash
curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc \
  | sudo gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/8.0 multiverse" \
  | sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list
sudo apt update && sudo apt install -y mongodb-org
sudo systemctl enable --now mongod
```

확인한다. `active (running)` 이 나와야 한다.

```bash
systemctl status mongod --no-pager
mongosh --eval 'db.runCommand({ping:1})'
```

데이터베이스를 미리 만들 필요는 없다. MongoDB 는 첫 삽입 때 만든다.

---

## 4. 코드 배치

```bash
git clone <repo URL> ~/jungle10team
cd ~/jungle10team
git checkout main          # 최종 머지 브랜치
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

여기서 설치가 깨지면 파이썬 버전을 먼저 의심한다. `python3 -V` 가 3.12 인지 확인한다.

---

## 5. 잊기 쉬운 두 가지

이 두 항목이 실제로 사고를 낸다. 특히 두 번째는 조용히 실패해서 발표 도중에 발견된다.

### 5-1. `.env` 만들기

`.env` 는 `.gitignore` 에 있어서 clone 으로 따라오지 않는다. 채워야 하는 값은
두 개이고, 빠뜨렸을 때 터지는 자리가 서로 다르다.

| 변수 | 읽는 곳 | 없으면 |
|---|---|---|
| `JWT_SECRET` | `auth_util.py` | 앱이 뜨는 순간 `KeyError` 로 죽는다. 즉시 드러난다. |
| `FLASK_SECRET` | `app.py` 의 `app.secret_key` | 앱이 뜨는 순간 `KeyError` 로 죽는다. 이 줄이 없던 시절에는 `flash()` 를 부르는 요청에서만 500 이 나서, 물품 등록에 제목을 비운 채 제출해야 드러났다. |

`deploy/bootstrap.sh` 가 `.env` 를 자동으로 만든다. 손으로 만든다면 이렇게 한다.

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # 두 번 실행해 따로 넣는다
```

두 값은 서명 주체가 다른 별개의 신뢰 체계다. `JWT_SECRET` 은 PyJWT 가 HS256 으로,
`FLASK_SECRET` 은 Flask 내부의 itsdangerous 가 session 쿠키를 서명하는 데 쓴다.
한 값을 돌려 쓰면 한쪽이 유출됐을 때 양쪽이 함께 뚫린다.

**배포 서버의 `JWT_SECRET` 은 팀원 로컬과 같을 필요가 없다.** 도메인이 달라 쿠키가
넘어가지 않기 때문이다. 대신 한 번 정한 값을 고정한다. 재시작마다 바뀌면 그때까지
발급된 토큰이 전부 서명 불일치로 거부되어 접속자 전원이 로그인 화면으로 튕긴다.
셋이 같은 값을 맞추는 규칙은 **팀원끼리 로컬에서 계정을 공유할 때** 필요한 것이다.

`FLASK_DEBUG` 는 배포 서버에서 **비워 둔다.** 켜면 예외 화면에 소스가 그대로 나온다.

### 5-2. `static/uploads/` 채우기

`.gitignore` 가 `static/uploads/*` 를 제외하고 `.gitkeep` 만 남겨서, clone 직후
업로드 폴더는 비어 있다. 페이지는 정상으로 뜨고 사진 자리만 깨진다.

```bash
mkdir -p static/uploads
scp -i <키>.pem static/uploads/*.jpg static/uploads/*.png ubuntu@<퍼블릭IP>:~/jungle10team/static/uploads/
```

시드 스크립트를 쓴다면 스크립트가 참조하는 파일 이름과 실제로 올린 파일 이름이
같은지 확인한다.

---

## 6. 데모 데이터 심기

피드는 한 페이지에 20개다. 3페이지를 보여주려면 41개 이상이 필요하다.
사진 50장이 아니라 **물품 50개**가 목표이고, 실제 사진 10~15장을 여러 물품이
나눠 쓰면 데모에서는 충분하다. 다만 제목과 사진이 어긋나면(맥북 카드에 풍경 사진)
망가진 화면으로 읽히므로, 사진에 맞춰 제목을 짓는다.

채팅목록과 내 거래글은 사진이 아니라 다른 것을 필요로 한다.

- 채팅목록: `rooms` 와 `messages` 문서, 그리고 **두 번째 계정**이 있어야 한다.
- 내 거래글: `seller_id` 하나로 거른다 (구매 탭은 2026-08-27 제거). 데모 계정이
  물품의 판매자여야 목록이 채워진다. 정렬이 거래완료를 앞에 놓으므로, **완료 상태인
  물품을 최소 두어 개 섞어 두어야** 그 규칙이 화면에서 보인다.

UI 로 손수 등록하는 것은 현실적이지 않다. 시드 스크립트를 로컬에서 만들어 두고
인스턴스에서 한 번 돌린다.

---

## 7. 실행

`app.py` 의 실행 블록은 이미 배포를 견디는 값으로 되어 있다. 서버에서 코드를
고칠 필요가 없다.

- `host="0.0.0.0"` — 기본값 `127.0.0.1` 은 인스턴스 바깥에서 닿지 않는다.
- `debug` — `.env` 의 `FLASK_DEBUG` 로 가른다. 배포 서버에는 넣지 않으므로 꺼진다.
- `allow_unsafe_werkzeug=True` — Flask-SocketIO 가 내장 개발 서버 위에서
  운영 모드로 도는 것을 막는데, 이 플래그가 그 차단을 푼다.

`nohup` 대신 systemd 로 띄운다. 재부팅해도 살아나고, 실행 디렉터리가 고정되어
`.env` 를 못 찾는 사고가 함께 막힌다. `load_dotenv()` 는 **현재 작업 디렉터리**
기준으로 `.env` 를 찾기 때문에, 엉뚱한 곳에서 실행하면 `KeyError` 로 죽는다.

`deploy/bootstrap.sh` 가 `deploy/jungle10team.service` 를 실제 경로로 바꿔서
설치한다. 손으로 한다면 그 파일의 `User` · `WorkingDirectory` · `ExecStart`
세 줄을 확인하고 복사한다.

```bash
sudo cp deploy/jungle10team.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jungle10team
```

상태와 로그는 이렇게 본다.

```bash
systemctl status jungle10team --no-pager
journalctl -u jungle10team -f          # 예전의 tail -f ~/app.log 를 대신한다
sudo systemctl restart jungle10team    # 코드를 갱신한 뒤
```

브라우저에서 `http://<퍼블릭IP>:5000` 을 연다.

---

## 8. 배포 전에 반드시 풀어야 하는 것

| 항목 | 상태 | 막고 있는 것 |
|---|---|---|
| `socketio` 가 앱에 묶여 있지 않다 | **해결 (8a80ee3)** | `app.py` 가 `socketio.init_app(app)` 을 부른다. `ARCHITECTURE.md:31` 이 지정한 대로 초기화가 `app.py` 에 있다. |
| `app.secret_key` 가 없다 | **해결 (feature/deploy)** | `flash()` 를 부르는 요청마다 500 이 나던 문제. `app.py` 가 `FLASK_SECRET` 을 읽고, `templates/base.html` 이 메시지를 그린다. |
| `templates/history.html` | 완료 | 단일 목록('내 거래글'). 탭 없음. `routes/main.py` 가 `/history` 를 200 으로 응답한다. |
| `JWT_SECRET` 합의 | 배포와 무관 | 셋이 같은 값을 쓰는 것은 **로컬끼리** 계정을 공유할 때 필요하다. EC2 는 도메인이 달라 쿠키가 넘어가지 않으므로 별도 값을 쓴다. |
| 데모 시드 데이터 | 미해결 | § 6 이 요구하는 물품 50개와 사진이 없다. 시드 스크립트도 아직 없다. 배포를 먼저 성공시키고 별도로 진행한다. |
| 데모 사진 무게 | 미조치 | 현재 업로드가 장당 평균 425KB, 최대 1.0MB. `/static/` 은 `no-store` 에서 제외되어 있어서(`app.py`) 한 번만 받지만, 첫 로딩은 그만큼 느리다. |

남은 것은 데모 데이터와 사진 무게뿐이고, 둘 다 인스턴스 없이 로컬에서 확인할 수
있다. 서버에서 처음 돌려 보는 상황을 만들지 않는 것이 이 문서의 목적이다.
