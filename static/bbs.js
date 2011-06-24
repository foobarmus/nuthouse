document.observe('dom:loaded', function() {

    $('comment_form').observe('click', function(e) {
        if (e.findElement('a')) {
            e.stop();
            new Ajax.Updater('comment_form', '/post_comment_form', {
                method: 'get',
                parameters: {pid: e.findElement('a').id}
            });
        }
    });

});
