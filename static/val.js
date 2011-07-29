var focussed = false;

function doTest(label, elem, failTest, valid) {
    if (failTest) {
        document.getElementById(label).className = 'failed';
        if (!focussed) {
            elem.focus();
            focussed = true;
        }
        valid = false;
    } else {
        document.getElementById(label).className = (label.indexOf('-help')>=0) ? 'grey' : '';
    }
    return valid;
}

function validate(form) {
    var valid = true;
    var label;
    var failTest;
    var e = form.elements;
    for (i=0;i<e.length;i++) {
        if (e[i].className.indexOf('required')>=0) {
            label = e[i].id + '-label';
            failTest = ((e[i].type == 'checkbox' && e[i].checked != true) || !e[i].value);
            valid = doTest(label, e[i], failTest, valid);
        }
        if (e[i].className.indexOf('alpha-numeric')>=0) {
            var re = new RegExp('^\\w*$');
            label = e[i].id + '-help';
            failTest = (!e[i].value.match(re));
            valid = doTest(label, e[i], failTest, valid);
        }
    }
    return valid;
}
