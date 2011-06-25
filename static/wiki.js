document.observe('dom:loaded', function() {

    $('advanced').observe('click', function(e) {
        if (e.findElement('a')) {
            e.stop();
            new Ajax.Updater('advanced', '/wiki_form_advanced_options', {
                method: 'get',
                parameters: {
                    name: $('name').value,
                    crumbstring: $('crumbs').value
                }
            });
        }
    });

});
