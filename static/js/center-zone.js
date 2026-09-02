// Center Zone helpers

function cancelCenterZoneTimer(timerId) {
    if (!timerId) {
        return;
    }
    fetch(`/api/timers/${timerId}`, {
        method: 'DELETE'
    })
        .then((response) => {
            if (!response.ok) {
                throw new Error('Failed to cancel timer.');
            }
            if (window.htmx) {
                htmx.ajax('GET', '/partials/center-zone', '#center-zone');
            }
        })
        .catch((error) => {
            console.error('Center Zone timer cancel failed:', error);
        });
}
