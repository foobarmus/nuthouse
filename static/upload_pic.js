document.observe('dom:loaded', function() {

    $('add-pics').observe('click', function(e) {
        if (e.findElement('a')) {
            e.stop();
            new Ajax.Updater('add-pics', '/upload_pic', {
                method: 'get',
                onSuccess: function () { $('add-pics').style.background = 'none'; }
            });
        }
    });

});
