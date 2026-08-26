/* 커뮤니티 댓글 — 0.5초 AJAX 폴링 클라이언트.
 *
 * WebSocket 을 쓰지 않는다. 거래 채팅(static/js/ws.js)과는 아무 관계가 없고,
 * 두 파일이 같은 페이지에서 함께 도는 일도 없다.
 *
 * 서버와의 약속 (routes/community.py):
 *   GET  /api/community/<post_id>/comments?since=<id>
 *        -> { ok, comments: [...], total, stamp }
 *   POST /api/community/<post_id>/comments             { text }
 *   POST /api/community/comments/<comment_id>/edit     { text }
 *   POST /api/community/comments/<comment_id>/delete
 *
 * 폴링의 어려운 지점 하나:
 * since 방식은 "마지막 id 뒤에 생긴 것"만 볼 수 있어서, 남이 댓글을 고치거나
 * 지운 것은 구조적으로 관측되지 않는다. 그래서 서버가 대조 신호 두 개를 함께
 * 준다 — total(전체 개수)과 stamp(가장 늦은 수정 시각). 화면에 그려 둔 값과
 * 어긋날 때만 전체를 다시 받는다. 평상시에는 빈 배열만 오가므로 화면이
 * 깜빡이지 않고 스크롤도 튀지 않는다.
 */

$(function () {
    const $box = $(".comment-box");

    if ($box.length === 0) {
        return;
    }

    const postId = String($box.data("postId"));
    const currentUserId = String($box.data("currentUserId"));

    const $list = $("#commentList");
    const $count = $("#commentCount");
    const $form = $("#commentForm");
    const $input = $("#commentInput");
    const $submit = $("#commentSubmit");
    const $status = $("#commentStatus");

    const POLL_BASE_DELAY = 500;
    const POLL_MAX_DELAY = 5000;
    const MAX_LENGTH = 500;

    // ── 상태 ────────────────────────────────────────────────
    // 넷 다 SSR 이 그려 준 초기 화면에서 읽어 시작한다.
    let lastCommentId = $list.find(".comment-row").last().data("commentId");
    let renderedCount = $list.find(".comment-row").length;
    let renderedStamp = String($box.data("commentStamp") || "");

    let pollTimer = null;
    let pollDelay = POLL_BASE_DELAY;
    // 예약된 틱끼리는 setTimeout 재귀가 겹침을 막아 준다. 이 플래그는 그
    // 바깥에서 오는 요청(탭 복귀 직후, 작성·수정·삭제 직후)을 위한 것이다.
    let inFlight = false;
    // 401 처럼 다시 시도해도 소용없는 상태. 타이머를 다시 걸지 않는다.
    let stopped = false;
    // 인라인 수정 중인 댓글 id. 같은 계정을 두 탭에서 열어 두면 폴링이
    // 편집 중인 칸을 통째로 뜯어 갈 수 있어서, 그 동안 전체 갱신을 미룬다.
    let editingId = null;

    lastCommentId = lastCommentId ? String(lastCommentId) : "";

    function announce(message) {
        $status.text(message);
    }

    // 화면에 그려 둔 것 중 가장 늦은 수정 시각을 유지한다. 서버의 stamp 와
    // 이 값을 대조해서 "남이 기존 댓글을 고쳤다"를 알아챈다. ISO 문자열은
    // 자릿수가 고정이라 문자열 비교만으로 시각 순서가 그대로 나온다.
    function bumpStamp(comment) {
        const value = String(comment.updated_at || "");

        if (value > renderedStamp) {
            renderedStamp = value;
        }
    }

    function isMine(authorId) {
        return String(authorId) === currentUserId;
    }

    function updateCount() {
        renderedCount = $list.find(".comment-row").length;
        $count.text(renderedCount);
    }

    // ── 행 그리기 ───────────────────────────────────────────
    // 사용자가 보낸 값은 전부 .text() 로 넣는다. .html() 을 쓰면 댓글에 담긴
    // <script> 가 실제로 실행된다(XSS). Jinja 는 자동으로 escape 해 주지만
    // JS 는 해 주지 않는다.
    function renderRow(comment) {
        const $row = $("<li>")
            .addClass("comment-row")
            .attr("data-comment-id", comment.id)
            .attr("data-author-id", comment.author_id);

        const $author = $("<span>")
            .addClass("comment-author")
            .text(comment.name);

        if (comment.lab) {
            $author.append($("<small>").text(comment.lab));
        }

        const $text = $("<span>")
            .addClass("comment-text")
            .text(comment.text);

        const $time = $("<time>")
            .addClass("comment-time")
            .attr("datetime", comment.created_at || "")
            .text(
                comment.edited
                    ? `${comment.display_time} (수정됨)`
                    : comment.display_time
            );

        $row.append($author, $text, $time);

        if (isMine(comment.author_id)) {
            const $actions = $("<span>")
                .addClass("comment-actions")
                .append(
                    $("<button>")
                        .attr("type", "button")
                        .addClass("comment-edit-button")
                        .text("수정"),
                    $("<button>")
                        .attr("type", "button")
                        .addClass("comment-delete-button")
                        .text("삭제")
                );

            $row.append($actions);
        }

        return $row;
    }

    function isScrolledToBottom() {
        const el = $list.get(0);

        if (!el) {
            return true;
        }

        return el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    }

    function scrollToBottom() {
        const el = $list.get(0);

        if (!el) {
            return;
        }

        requestAnimationFrame(function () {
            el.scrollTop = el.scrollHeight;
        });
    }

    // 새로 달린 댓글만 끝에 붙인다. 이미 있는 행은 건드리지 않으므로
    // 글자 선택이 풀리지 않고 스크롤도 그대로다.
    function appendComments(comments) {
        if (comments.length === 0) {
            return;
        }

        const wasAtBottom = isScrolledToBottom();

        $("#commentEmpty").remove();

        comments.forEach(function (comment) {
            // 작성 직후의 즉시 폴링과 예약된 틱이 같은 댓글을 두 번 가져올 수
            // 있다. id 로 한 번 더 거른다.
            if ($list.find(`[data-comment-id="${comment.id}"]`).length > 0) {
                return;
            }

            $list.append(renderRow(comment));
            lastCommentId = comment.id;
            bumpStamp(comment);
        });

        updateCount();

        if (wasAtBottom) {
            scrollToBottom();
        }
    }

    // 수정·삭제가 반영되지 않은 것을 알아챘을 때만 부른다. 목록을 통째로
    // 다시 그리므로 비싸고, 그래서 평상시에는 절대 부르지 않는다.
    function redrawAll(comments) {
        const wasAtBottom = isScrolledToBottom();

        // 삭제로 최댓값이 내려갈 수 있으므로 누적하지 않고 처음부터 다시 센다.
        renderedStamp = "";
        $list.empty();

        if (comments.length === 0) {
            $list.append(
                $("<li>")
                    .addClass("comment-empty")
                    .attr("id", "commentEmpty")
                    .text("첫 댓글을 남겨 보세요.")
            );
            lastCommentId = "";
        } else {
            comments.forEach(function (comment) {
                $list.append(renderRow(comment));
                bumpStamp(comment);
            });
            lastCommentId = comments[comments.length - 1].id;
        }

        updateCount();

        if (wasAtBottom) {
            scrollToBottom();
        }
    }

    // ── 통신 ────────────────────────────────────────────────
    function requestJson(url, options) {
        return fetch(url, options).then(function (response) {
            if (response.status === 401) {
                stopped = true;
                announce("다시 로그인해 주세요.");
                throw new Error("login_required");
            }

            return response.json().then(function (data) {
                if (!response.ok) {
                    throw new Error(data.error || "request_failed");
                }

                return data;
            });
        });
    }

    function fetchComments(since) {
        const query = since
            ? `?since=${encodeURIComponent(since)}`
            : "";

        return requestJson(
            `/api/community/${postId}/comments${query}`,
            { credentials: "same-origin" }
        );
    }

    function postJson(url, body) {
        return requestJson(url, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body || {})
        });
    }

    // ── 폴링 ────────────────────────────────────────────────
    // setInterval 을 쓰지 않는다. 응답이 0.5초보다 늦게 오면 setInterval 은
    // 요청을 쌓고, 겹친 응답의 순서가 뒤집히면 오래된 것이 새 것을 덮어쓴다.
    // 응답을 처리한 뒤에 다음 setTimeout 을 걸면 겹칠 수가 없다.
    function schedule() {
        if (stopped || document.hidden) {
            return;
        }

        clearTimeout(pollTimer);
        pollTimer = setTimeout(tick, pollDelay);
    }

    function tick() {
        if (stopped || inFlight || document.hidden) {
            schedule();
            return;
        }

        inFlight = true;

        fetchComments(lastCommentId)
            .then(function (data) {
                appendComments(data.comments || []);

                const total = data.total;
                const stamp = String(data.stamp || "");
                const changed =
                    total !== renderedCount || stamp !== renderedStamp;

                // 수정 중인 행이 있으면 전체 갱신을 미룬다. 편집 칸이 통째로
                // 사라지는 것보다 반영이 몇 초 늦는 편이 낫다.
                if (changed && editingId === null) {
                    return fetchComments("").then(function (full) {
                        redrawAll(full.comments || []);
                    });
                }

                return null;
            })
            .then(function () {
                pollDelay = POLL_BASE_DELAY;
            })
            .catch(function () {
                // 서버가 잠깐 멈췄을 때 열린 탭마다 초당 2회로 두들기지
                // 않도록 간격을 늘렸다가, 성공하면 위에서 다시 줄인다.
                pollDelay = Math.min(pollDelay * 2, POLL_MAX_DELAY);
            })
            .then(function () {
                inFlight = false;
                schedule();
            });
    }

    document.addEventListener("visibilitychange", function () {
        if (document.hidden) {
            clearTimeout(pollTimer);
            pollTimer = null;
            return;
        }

        clearTimeout(pollTimer);
        pollDelay = POLL_BASE_DELAY;
        tick();
    });

    // ── 작성 ────────────────────────────────────────────────
    function updateSubmitButton() {
        const text = String($input.val() || "").trim();

        $submit.prop(
            "disabled",
            text.length === 0 || text.length > MAX_LENGTH
        );
    }

    $input.on("input", updateSubmitButton);

    $form.on("submit", function (event) {
        // 막지 않으면 페이지가 새로고침된다.
        event.preventDefault();

        const text = String($input.val() || "").trim();

        if (!text) {
            return;
        }

        $submit.prop("disabled", true);

        postJson(`/api/community/${postId}/comments`, { text: text })
            .then(function (data) {
                $input.val("");
                // 서버가 확정한 댓글만 그린다. 저장에 실패한 글이 내 화면에만
                // 남는 일이 없다.
                appendComments([data.comment]);
                renderedStamp = String(data.stamp || renderedStamp);
                announce("댓글을 등록했어요.");
            })
            .catch(function (error) {
                announce(
                    error.message === "too_long"
                        ? "댓글은 500자 이내로 입력해 주세요."
                        : "댓글을 등록하지 못했어요."
                );
            })
            .then(function () {
                updateSubmitButton();
                $input.trigger("focus");
            });
    });

    // ── 삭제 ────────────────────────────────────────────────
    // 브라우저 기본 confirm() 대신 부트스트랩 모달을 쓴다. 글 삭제와 같은
    // 생김새라, 확인 창이 대상마다 달라 보이지 않는다.
    //
    // 모달은 화면에 하나뿐이고 모든 댓글이 돌려 쓴다. 그래서 "지금 어느
    // 댓글을 지우려는 중인가"를 기억해 둘 자리가 필요하다.
    let pendingDeleteId = null;

    const $deleteModal = $("#deleteCommentModal");
    const $deleteTarget = $("#deleteCommentTarget");
    const $deleteConfirm = $("#deleteCommentConfirm");

    function deleteModalInstance() {
        const el = $deleteModal.get(0);

        if (!el || typeof bootstrap === "undefined") {
            return null;
        }

        return bootstrap.Modal.getOrCreateInstance(el);
    }

    $list.on("click", ".comment-delete-button", function () {
        const $row = $(this).closest(".comment-row");

        pendingDeleteId = String($row.data("commentId"));

        // 지울 댓글의 본문을 모달에 보여 준다. .text() 로 넣는다 —
        // 여기서 .html() 을 쓰면 남이 쓴 댓글의 태그가 살아난다.
        $deleteTarget.text($row.find(".comment-text").text());

        const modal = deleteModalInstance();

        if (modal) {
            modal.show();
            return;
        }

        // 부트스트랩이 없는 상황(CDN 실패 등)에서도 삭제 자체는 되어야 한다.
        if (window.confirm("이 댓글을 삭제할까요?")) {
            $deleteConfirm.trigger("click");
        }
    });

    $deleteConfirm.on("click", function () {
        if (pendingDeleteId === null) {
            return;
        }

        const commentId = pendingDeleteId;
        const $row = $list.find(`[data-comment-id="${commentId}"]`);

        pendingDeleteId = null;
        $deleteConfirm.prop("disabled", true);

        postJson(`/api/community/comments/${commentId}/delete`)
            .then(function (data) {
                $row.remove();
                updateCount();

                if (renderedCount === 0) {
                    $list.append(
                        $("<li>")
                            .addClass("comment-empty")
                            .attr("id", "commentEmpty")
                            .text("첫 댓글을 남겨 보세요.")
                    );
                }

                renderedStamp = String(data.stamp || "");
                announce("댓글을 삭제했어요.");
            })
            .catch(function () {
                announce("댓글을 삭제하지 못했어요.");
            })
            .then(function () {
                $deleteConfirm.prop("disabled", false);

                const modal = deleteModalInstance();

                if (modal) {
                    modal.hide();
                }
            });
    });

    // 취소하거나 바깥을 눌러 닫았을 때 남은 대상을 지운다. 이게 없으면
    // 다음에 모달을 열 때 이전 대상이 그대로 남아 엉뚱한 댓글이 지워진다.
    $deleteModal.on("hidden.bs.modal", function () {
        pendingDeleteId = null;
        $deleteTarget.text("");
    });

    // ── 수정 ────────────────────────────────────────────────
    function closeEditForm($row) {
        $row.find(".comment-edit-form").remove();
        $row.find(".comment-text, .comment-actions").show();
        editingId = null;
    }

    $list.on("click", ".comment-edit-button", function () {
        const $row = $(this).closest(".comment-row");
        const commentId = String($row.data("commentId"));

        // 다른 행을 수정 중이었다면 그쪽을 먼저 닫는다.
        if (editingId !== null) {
            closeEditForm($list.find(`[data-comment-id="${editingId}"]`));
        }

        editingId = commentId;

        const $editForm = $("<form>")
            .addClass("comment-edit-form")
            .append(
                $("<input>")
                    .attr("type", "text")
                    .attr("maxlength", MAX_LENGTH)
                    .val($row.find(".comment-text").text()),
                $("<button>").attr("type", "submit").text("저장"),
                $("<button>")
                    .attr("type", "button")
                    .addClass("comment-edit-cancel")
                    .text("취소")
            );

        $row.find(".comment-text, .comment-actions").hide();
        $row.append($editForm);
        $editForm.find("input").trigger("focus");
    });

    $list.on("click", ".comment-edit-cancel", function () {
        closeEditForm($(this).closest(".comment-row"));
    });

    $list.on("submit", ".comment-edit-form", function (event) {
        event.preventDefault();

        const $row = $(this).closest(".comment-row");
        const commentId = String($row.data("commentId"));
        const text = String($(this).find("input").val() || "").trim();

        if (!text) {
            announce("빈 댓글로 수정할 수 없어요.");
            return;
        }

        postJson(`/api/community/comments/${commentId}/edit`, { text: text })
            .then(function (data) {
                editingId = null;
                $row.replaceWith(renderRow(data.comment));
                // 내가 고쳤으므로 서버의 stamp 가 바뀌었다. 응답이 준 새 값을
                // 그대로 받아 두지 않으면, 다음 틱이 이것을 "남이 고친 것"으로
                // 오해해서 목록을 통째로 다시 받는다.
                renderedStamp = String(data.stamp || renderedStamp);
                announce("댓글을 수정했어요.");
            })
            .catch(function (error) {
                announce(
                    error.message === "too_long"
                        ? "댓글은 500자 이내로 입력해 주세요."
                        : "댓글을 수정하지 못했어요."
                );
            });
    });

    // ── 시작 ────────────────────────────────────────────────
    updateSubmitButton();
    updateCount();
    scrollToBottom();
    schedule();
});
