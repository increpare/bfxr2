Math.clamp = function(value, min, max){
    return Math.max(min, Math.min(value, max));
}

// shallow copy
copy_obj = function(obj){
    return Object.assign({}, obj);
}

