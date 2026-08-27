#!/usr/bin/env bash
#
# 정글장터 — EC2 인스턴스 초기 설치 스크립트.
#
# Ubuntu 24.04 LTS 인스턴스에 SSH 로 들어간 뒤 한 번 실행한다.
#   curl -fsSL https://raw.githubusercontent.com/Youjaeseon/jungle10team/main/deploy/bootstrap.sh -o bootstrap.sh
#   bash bootstrap.sh
#
# 다시 실행해도 안전하다. 이미 끝난 단계는 건너뛴다.
# 코드를 갱신하고 재시작만 하고 싶다면 그냥 다시 돌리면 된다.
#
# 이 스크립트가 하지 않는 것: 인스턴스 생성, 보안 그룹 설정, 데모 데이터 심기.
# 앞의 둘은 AWS 콘솔에서 하고(docs/DEPLOY.md § 1), 마지막은 별도 작업이다.

set -euo pipefail

# main 에 병합되기 전에 시험해 본다면 BRANCH 를 넘긴다.
#   BRANCH=feature/deploy bash bootstrap.sh
REPO_URL="${REPO_URL:-https://github.com/Youjaeseon/jungle10team.git}"
BRANCH="${BRANCH:-main}"
APP_DIR="${APP_DIR:-${HOME}/jungle10team}"
SERVICE_NAME="jungle10team"
PORT=5000

step() { printf '\n\033[1;36m== %s\033[0m\n' "$1"; }
info() { printf '   %s\n' "$1"; }

# ---------------------------------------------------------------
step "1/7  기본 패키지"
# ---------------------------------------------------------------
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv python3-pip git curl gnupg

# ---------------------------------------------------------------
step "2/7  MongoDB 8.0"
# ---------------------------------------------------------------
# 데이터베이스 이름은 jungle 이다. db.py 가 mongodb://localhost:27017 을
# 하드코딩하고 있어서 앱과 DB 가 같은 인스턴스에 있어야 한다.
if ! command -v mongod >/dev/null 2>&1; then
    curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc \
        | sudo gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg --dearmor --yes
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/8.0 multiverse" \
        | sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list >/dev/null
    sudo apt-get update -qq
    sudo apt-get install -y -qq mongodb-org
else
    info "이미 설치되어 있다. 건너뛴다."
fi
sudo systemctl enable --now mongod

# 설치 직후에는 기동에 몇 초 걸린다. 여기서 실패하면 앱은 뜨지만 모든
# 페이지가 DB 접속 오류로 죽으므로, 다음 단계로 넘어가지 않고 멈춘다.
for _ in $(seq 1 30); do
    if mongosh --quiet --eval 'db.runCommand({ping:1}).ok' 2>/dev/null | grep -q 1; then
        info "mongod 응답 확인."
        break
    fi
    sleep 1
done
mongosh --quiet --eval 'db.runCommand({ping:1}).ok' | grep -q 1

# ---------------------------------------------------------------
step "3/7  소스 내려받기"
# ---------------------------------------------------------------
if [ -d "${APP_DIR}/.git" ]; then
    git -C "${APP_DIR}" fetch origin
    git -C "${APP_DIR}" checkout "${BRANCH}"
    git -C "${APP_DIR}" pull --ff-only
else
    git clone --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
fi
info "$(git -C "${APP_DIR}" log --oneline -1)"

# ---------------------------------------------------------------
step "4/7  venv 와 의존성"
# ---------------------------------------------------------------
if [ ! -x "${APP_DIR}/venv/bin/python" ]; then
    python3 -m venv "${APP_DIR}/venv"
fi
"${APP_DIR}/venv/bin/pip" install -q --upgrade pip
"${APP_DIR}/venv/bin/pip" install -q -r "${APP_DIR}/requirements.txt"

# ---------------------------------------------------------------
step "5/7  .env"
# ---------------------------------------------------------------
# 이미 있으면 절대 덮어쓰지 않는다. JWT_SECRET 이 바뀌면 발급해 둔 토큰이
# 전부 서명 불일치로 거부되어, 접속자 전원이 로그인 화면으로 튕긴다.
if [ -f "${APP_DIR}/.env" ]; then
    info ".env 가 이미 있다. 그대로 둔다."
else
    # 두 값은 서명 주체가 다른 별개의 신뢰 체계다. 따로 뽑는다.
    JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
    FLASK_SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
    cat > "${APP_DIR}/.env" <<ENVEOF
# bootstrap.sh 가 생성했다. 이 값을 바꾸면 기존 로그인이 모두 끊긴다.
# 배포 서버는 팀원 로컬과 도메인이 달라 쿠키가 넘어가지 않으므로,
# JWT_SECRET 이 팀원 값과 달라도 된다. 대신 여기서는 고정한다.
JWT_SECRET=${JWT_SECRET}
FLASK_SECRET=${FLASK_SECRET}
# FLASK_DEBUG 는 넣지 않는다. 켜면 에러 화면에 소스가 그대로 노출된다.
ENVEOF
    chmod 600 "${APP_DIR}/.env"
    info ".env 를 새로 만들었다."
fi

# ---------------------------------------------------------------
step "6/7  systemd 서비스"
# ---------------------------------------------------------------
# 유닛 템플릿의 계정과 경로를 이 인스턴스의 실제 값으로 바꿔서 설치한다.
sed -e "s|^User=.*|User=$(id -un)|" \
    -e "s|^WorkingDirectory=.*|WorkingDirectory=${APP_DIR}|" \
    -e "s|^ExecStart=.*|ExecStart=${APP_DIR}/venv/bin/python app.py|" \
    "${APP_DIR}/deploy/${SERVICE_NAME}.service" \
    | sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

# ---------------------------------------------------------------
step "7/7  확인"
# ---------------------------------------------------------------
# 기동에 잠깐 걸린다. 응답이 올 때까지 최대 20초 기다린다.
code=""
for _ in $(seq 1 20); do
    code="$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT}/login" || true)"
    [ "${code}" = "200" ] && break
    sleep 1
done

sudo systemctl status "${SERVICE_NAME}" --no-pager --lines=0 || true

if [ "${code}" = "200" ]; then
    printf '\n\033[1;32m성공. /login 이 200 을 돌려준다.\033[0m\n'
    printf '브라우저에서 http://<퍼블릭IP>:%s 를 연다.\n' "${PORT}"
    printf '보안 그룹 인바운드에 TCP %s 가 열려 있어야 바깥에서 닿는다.\n' "${PORT}"
else
    printf '\n\033[1;31m실패. /login 응답이 "%s" 다.\033[0m\n' "${code}"
    printf '로그를 본다:  journalctl -u %s -n 50 --no-pager\n' "${SERVICE_NAME}"
    exit 1
fi
