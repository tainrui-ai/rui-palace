document.addEventListener("DOMContentLoaded", function() {
    const modal = document.getElementById("cookie-consent");
    const acceptBtn = document.getElementById("accept-btn");
    const rejectBtn = document.getElementById("reject-btn");

    // 检查缓存，若已同意，直接隐藏
    if (localStorage.getItem("cookieConsent") === "true") {
        modal.style.display = "none";
    }

    // 点击后直接消失
    function dismiss() {
        modal.style.opacity = "0";
        setTimeout(() => {
            modal.style.display = "none";
        }, 500);
    }

    acceptBtn.onclick = function() {
        localStorage.setItem("cookieConsent", "true");
        dismiss();
    };

    rejectBtn.onclick = function() {
        dismiss();
    };
});