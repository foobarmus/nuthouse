function goo_blur(q) {
    if (q.value == '') {
        q.style.background = 'white url(/static/google_custom_search_watermark.gif) left no-repeat';
    }
};
function goo_focus(q) {
    q.style.background = 'white';
};
