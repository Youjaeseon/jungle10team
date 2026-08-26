$(function () {
    const $chatRoom = $(".chat-room-page");

    if ($chatRoom.length === 0) {
        return;
    }

    const roomId = String($chatRoom.data("roomId"));
    const currentUserId = String(
        $chatRoom.data("currentUserId")
    );
    const socketEnabled =
        String($chatRoom.data("socketEnabled")) === "true";
    const $messageList = $("#messageList");
    const $messageForm = $("#chatMessageForm");
    const $messageInput = $("#chatMessageInput");
    const $sendButton = $("#chatSendButton");
    const $statusMessage = $("#chatStatusMessage");
    const $peerPresence = $("#peerPresence");
    const $itemStatus = $("#chatItemStatus");

    let socket = null;
    let hasConnectedBefore = false;

    function getMessageText() {
        return $messageInput.val().trim();
    }

    function updateSendButton() {
        $sendButton.prop(
            "disabled",
            getMessageText().length === 0
        );
    }

    function formatMessageTime(createdAt) {
        const date = createdAt
            ? new Date(createdAt)
            : new Date();

        return new Intl.DateTimeFormat(
            "ko-KR",
            {
                hour: "numeric",
                minute: "2-digit",
                hour12: true
            }
        ).format(date);
    }

    function scrollToLatestMessage() {
        const messageList = $messageList.get(0);

        if (!messageList) {
            return;
        }

        requestAnimationFrame(function () {
            messageList.scrollTop =
                messageList.scrollHeight;
        });
    }

    function createMessageElement(message) {
        const senderId = String(message.sender_id);
        const isMine = senderId === currentUserId;
        const messageId =
            message.id ||
            message._id ||
            `local-${Date.now()}`;
        const displayTime = formatMessageTime(
            message.created_at
        );
        const $row = $("<li>")
            .addClass("chat-message-row")
            .addClass(
                isMine
                    ? "chat-message-row-mine"
                    : "chat-message-row-partner"
            )
            .attr("data-message-id", messageId);
        const $time = $("<time>")
            .addClass("chat-message-time")
            .attr(
                "datetime",
                message.created_at || ""
            )
            .text(displayTime);
        const $bubble = $("<div>")
            .addClass("chat-message-bubble")
            .addClass(
                isMine
                    ? "chat-message-bubble-mine"
                    : "chat-message-bubble-partner"
            )
            .text(message.text);

        if (isMine) {
            const $wrapper = $("<div>")
                .addClass("chat-message-mine")
                .append($time, $bubble);

            return $row.append($wrapper);
        }

        const senderName = message.name || "상대방";
        const $avatar = $("<div>")
            .addClass("chat-message-avatar")
            .attr("aria-hidden", "true")
            .text(senderName.slice(0, 1));
        const $sender = $("<div>")
            .addClass("chat-message-sender")
            .text(
                message.lab
                    ? `${senderName} · ${message.lab}`
                    : senderName
            );
        const $partnerMessage = $("<div>")
            .addClass("chat-message-partner")
            .append($bubble, $time);
        const $content = $("<div>")
            .append($sender, $partnerMessage);

        return $row.append($avatar, $content);
    }

    function appendMessage(message) {
        const messageId = message.id || message._id;

        if (
            messageId &&
            $messageList.find(
                `[data-message-id="${messageId}"]`
            ).length > 0
        ) {
            return;
        }

        $("#emptyMessageState").remove();
        $messageList.append(
            createMessageElement(message)
        );
        scrollToLatestMessage();
    }

    function clearMessageInput() {
        $messageInput.val("");
        updateSendButton();
        $messageInput.trigger("focus");
    }

    function updateStatusUI(status) {
        const isDone = status === "done";

        $itemStatus
            .toggleClass(
                "chat-status-completed",
                isDone
            )
            .toggleClass(
                "chat-status-available",
                !isDone
            )
            .text(isDone ? "거래 완료" : "판매 중");
    }

    async function loadMissedMessages() {
        try {
            const response = await fetch(
                `/api/rooms/${roomId}/messages`
            );
            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.error || "messages_load_failed"
                );
            }

            data.messages.forEach(appendMessage);
            updateStatusUI(data.status);
        } catch (error) {
            console.error(
                "놓친 메시지를 불러오지 못했습니다.",
                error
            );
        }
    }

    function initializeSocket() {
        if (
            !socketEnabled ||
            typeof window.io !== "function"
        ) {
            return;
        }

        socket = window.jungleSocket || window.io();

        socket.on("connect", function () {
            socket.emit(
                "join",
                {
                    room_id: roomId
                }
            );

            if (hasConnectedBefore) {
                loadMissedMessages();
            }

            hasConnectedBefore = true;
        });

        socket.on("message", function (message) {
            appendMessage(message);
            $statusMessage.text(
                "새 메시지가 도착했습니다."
            );
        });

        socket.on("presence", function (data) {
            $peerPresence.toggleClass(
                "d-none",
                !data.online
            );
        });

        socket.on("status", function (data) {
            updateStatusUI(data.status);
        });

        socket.on("error", function (data) {
            $statusMessage.text(
                data.error || "메시지 전송에 실패했습니다."
            );
            console.error("Socket.IO 오류", data);
        });

        socket.on("disconnect", function () {
            $peerPresence.addClass("d-none");
        });
    }

    $messageInput.on("input", updateSendButton);

    $messageForm.on("submit", function (event) {
        event.preventDefault();

        const text = getMessageText();

        if (!text) {
            updateSendButton();
            return;
        }

        if (socket) {
            socket.emit(
                "message",
                {
                    text: text
                }
            );
        } else {
            appendMessage({
                id: `local-${Date.now()}`,
                sender_id: currentUserId,
                name: "나",
                lab: "",
                text: text,
                created_at: new Date().toISOString()
            });
        }

        clearMessageInput();
        $statusMessage.text(
            socket
                ? "메시지를 전송하고 있습니다."
                : "로컬 메시지를 표시했습니다."
        );
    });

    initializeSocket();
    updateSendButton();
    scrollToLatestMessage();
});
