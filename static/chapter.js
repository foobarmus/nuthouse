document.observe('dom:loaded', function() {

    $('event_form').observe('click', function(e) {
        if (e.findElement('a')) {
            e.stop();
            new Ajax.Updater('event_form', '/event', {
                method: 'get',
                parameters: {chapter: $('chapter_id').innerHTML}
            });
        }
    });

});
