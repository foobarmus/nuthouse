function fail(elem) {
    document.getElementById(elem.id + '-label').className = 'failed';
    return false;
}

function pass(elem, valid) {
    document.getElementById(elem.id + '-label').className = '';
    return valid;
}

function focus(elem, focussed) {
    if (!focussed) {
        elem.focus()
    }
    return true;
}

function validate(form) {
    var valid = true;
    var focussed = false;
    var e = form.elements;
    for (i=0;i<e.length;i++) {
        if (e[i].className.indexOf('required')>=0) {
            if ((e[i].type == 'checkbox' && e[i].checked != true) || !e[i].value) {
                valid = fail(e[i]);
                focussed = focus(e[i], focussed);
            } else {
                valid = pass(e[i], valid);
            }
        }
        if (e[i].className.indexOf('alpha-numeric')>=0) {
            var re = new RegExp('^\w*$');
            if (!e[i].value.match(re)) {
                valid = fail(e[i]);
                focussed = focus(e[i], focussed);
            } else {
                valid = pass(e[i], valid);
            }

        }
    }
    return valid;
}
