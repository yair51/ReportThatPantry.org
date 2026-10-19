// Starred ("favorite") pantries, saved per browser in localStorage - no account needed.
// Shared by the dashboard table (status.html) and the pantry page (pantry.html).
var RTPFavorites = (function () {
    var KEY = 'rtp-starred-pantries';

    function read() {
        try {
            var ids = JSON.parse(localStorage.getItem(KEY) || '[]');
            return Array.isArray(ids) ? ids.map(String) : [];
        } catch (e) {
            return [];  // Storage blocked (private mode, etc.) - just behave as if nothing is starred
        }
    }

    function write(ids) {
        try {
            localStorage.setItem(KEY, JSON.stringify(ids));
        } catch (e) {}
    }

    return {
        all: read,
        has: function (id) {
            return read().indexOf(String(id).trim()) !== -1;
        },
        // Returns true if the pantry is starred after the toggle
        toggle: function (id) {
            id = String(id).trim();
            var ids = read();
            var index = ids.indexOf(id);
            if (index === -1) {
                ids.push(id);
            } else {
                ids.splice(index, 1);
            }
            write(ids);
            return index === -1;
        }
    };
})();
