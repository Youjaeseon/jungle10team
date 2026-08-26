(function (window) {
    "use strict";

    if (
        typeof window.io !== "function" ||
        window.jungleSocket
    ) {
        return;
    }

    // 로그인한 모든 화면에서 하나의 소켓 연결을 함께 사용한다.
    window.jungleSocket = window.io();

    const socket = window.jungleSocket;
    const badge = document.getElementById(
        "chatNotificationBadge"
    );
    const notificationArea = document.getElementById(
        "chatNotificationArea"
    );
    const storageKey = "jungleUnreadChatCount";

    function getUnreadCount() {
        return Number.parseInt(
            window.sessionStorage.getItem(storageKey) || "0",
            10
        );
    }

    function updateBadge(count) {
        if (!badge) {
            return;
        }

        if (count < 1) {
            badge.textContent = "";
            badge.classList.add("d-none");
            return;
        }

        badge.textContent = count > 99 ? "99+" : String(count);
        badge.classList.remove("d-none");
    }

    function saveUnreadCount(count) {
        window.sessionStorage.setItem(storageKey, String(count));
        updateBadge(count);
    }

    function isCurrentChatRoom(roomId) {
        const chatRoom = document.querySelector(".chat-room-page");

        return Boolean(
            chatRoom &&
            String(chatRoom.dataset.roomId) === String(roomId)
        );
    }

    function showNotification(data) {
        if (!notificationArea) {
            return;
        }

        const notice = document.createElement("a");
        const title = document.createElement("strong");
        const message = document.createElement("span");
        const roomId = String(data.room_id || "");

        notice.className = "chat-notification-toast";
        notice.href = roomId ? `/chats/${roomId}` : "/chats";

        title.textContent =
            `${data.sender_name || "상대방"} · ` +
            `${data.item_title || "거래 채팅"}`;
        message.textContent = data.text || "새 메시지가 도착했습니다.";

        notice.append(title, message);
        notificationArea.prepend(notice);

        window.setTimeout(function () {
            notice.remove();
        }, 5000);
    }

    socket.on("chat_notification", function (data) {
        if (isCurrentChatRoom(data.room_id)) {
            return;
        }

        saveUnreadCount(getUnreadCount() + 1);
        showNotification(data);
    });

    document
        .querySelector(".chat-notification-link")
        ?.addEventListener("click", function () {
            saveUnreadCount(0);
        });

    updateBadge(getUnreadCount());
})(window);
