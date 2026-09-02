// App bar auto-hide controller

(function () {
    const dock = document.querySelector('.app-bar');
    if (!dock) {
        return;
    }

    const hotZone = document.getElementById('dock-hot-zone');
    const handle = document.getElementById('dock-handle');
    const idleDelayMs = 120000;
    let hideTimer = null;
    let isHoveringDock = false;
    let activityThrottle = null;

    function showDock() {
        document.body.classList.remove('dock-hidden');
        scheduleHide();
    }

    function hideDock() {
        if (isHoveringDock) {
            return;
        }
        document.body.classList.add('dock-hidden');
    }

    function scheduleHide() {
        if (hideTimer) {
            clearTimeout(hideTimer);
        }
        hideTimer = setTimeout(() => {
            hideDock();
        }, idleDelayMs);
    }

    function handleActivity() {
        if (activityThrottle) {
            return;
        }
        activityThrottle = setTimeout(() => {
            activityThrottle = null;
        }, 2000);

        showDock();
    }

    dock.addEventListener('mouseenter', () => {
        isHoveringDock = true;
        showDock();
    });

    dock.addEventListener('mouseleave', () => {
        isHoveringDock = false;
        scheduleHide();
    });

    if (hotZone) {
        hotZone.addEventListener('mouseenter', showDock);
    }

    if (handle) {
        handle.addEventListener('mouseenter', showDock);
    }

    document.addEventListener('mousemove', handleActivity, { passive: true });
    document.addEventListener('mousedown', handleActivity, { passive: true });
    document.addEventListener('click', handleActivity, { passive: true });
    document.addEventListener('wheel', handleActivity, { passive: true });
    document.addEventListener('touchstart', handleActivity, { passive: true });
    document.addEventListener('keydown', () => {
        showDock();
    });

    scheduleHide();
})();
