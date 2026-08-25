#!/usr/bin/env bash
# 슬라이드 HTML 한 장을 2560x1520 PNG로 렌더링한다.
#  - --in-process-gpu가 없으면 GPU 프로세스가 붙지 못해 렌더링이 멈추는 경우가 있다.
#  - user-data-dir을 매번 새로 만들어 인스턴스 충돌을 막는다.
#  - wireframe-v4-mvp.html이 Google Fonts를 외부에서 불러온다. 이 환경에서는 그 요청이
#    끝나지 않아 load 이벤트가 늦어지고 렌더링이 멈춘다. host-resolver-rules로 즉시
#    실패시킨다. 폰트는 로컬 Noto Sans CJK KR로 떨어지므로 고딕체가 오히려 일관된다.
#  - virtual-time-budget은 같은 이유로 쓰지 않는다. iframe의 load가 부모의 load보다
#    먼저 오므로, 거기서 화면을 세팅해 두면 기본 screenshot으로 충분하다.
set -u
src=$(realpath "$1")   # 상대 경로를 그대로 넘기면 Chrome이 호스트명으로 해석한다
out=$(realpath -m "$2")
rm -f "$out"
for try in 1 2 3 4; do
tmp=$(mktemp -d)
timeout 120 google-chrome --headless --disable-gpu --in-process-gpu --no-sandbox --hide-scrollbars \
  --allow-file-access-from-files --host-resolver-rules='MAP * ~NOTFOUND' \
  --disable-remote-fonts --user-data-dir="$tmp" \
  --force-device-scale-factor=2 --window-size=1280,760 \
  --screenshot="$out" "file://$src" >/dev/null 2>&1
rc=$?
rm -rf "$tmp"
[ -s "$out" ] && break
done
if [ -s "$out" ]; then echo "ok   $out"; else echo "FAIL $out (rc=$rc)"; exit 1; fi
