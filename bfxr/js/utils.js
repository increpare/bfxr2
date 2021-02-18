function prettify_param_name(s) {
    return s.replace(/_/g, ' ');
}

function variablize_param_name(s) {
    s = s.replace(/ /g, '_');
    s = s.replace(/-/g, '_');
    s = s.replace(/\'/g, ' ');
    return s;
}