function validate(form) {
    var valid = true;
    var focussed = false;
    var e = form.elements;
    for (i=0;i<e.length;i++) {
        if (e[i].className.indexOf('required')>=0) {
            if ((e[i].type == 'checkbox' && e[i].checked != true) || !e[i].value) {
                document.getElementById(e[i].id + '-label').className = 'failed';
                valid = false;
                if (!focussed) {
                    e[i].focus()
                    focussed = true;
                }
            } else {
                document.getElementById(e[i].id + '-label').className = '';
            }
        }
    }
    return valid;
}
