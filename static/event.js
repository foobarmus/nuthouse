document.observe('dom:loaded', function() {

    $('wrap-up').observe('click', function(e) {
        if (e.findElement('a')) {
            e.stop();
            new Ajax.Updater('frap', '/wrapup', {
                method: 'get',
                onSuccess: function () { $('wrap-up').style.display = 'none'; }
            });
        }
    });

});
