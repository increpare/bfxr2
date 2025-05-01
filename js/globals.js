Math.clamp = function(value, min, max){
    return Math.max(min, Math.min(value, max));
}

// shallow copy
function copy_obj(obj){
    return Object.assign({}, obj);
}

function step(n){
    return function(x){
        if (x<=0 || x>=1) return 0;
        return ((x*x*x)*n-x*n)*(1-x)*(-1.5);
    }
}

function resize_fn(fn,a1,a2,b1,b2){
    return function(y){
        return fn( (y-b1)/(b2-b1) * (a2-a1) + a1 );
    }      
}

function add_fns( ...fns ){
    return function(x){                
        return fns.reduce((acc,fn) => acc + fn(x), 0);
    }
}

function isVisible (ele, container) {
    const eleTop = ele.offsetTop;
    const eleBottom = eleTop + ele.clientHeight;

    const containerTop = container.scrollTop;
    const containerBottom = containerTop + container.clientHeight;

    // The element is fully visible in the container
    return (
        (eleTop >= containerTop && eleBottom <= containerBottom) ||
        // Some part of the element is visible in the container
        (eleTop < containerTop && containerTop < eleBottom) ||
        (eleTop < containerBottom && containerBottom < eleBottom)
    );
};

function setVisible (ele, container) {
    if (isVisible(ele, container)){
        return;
    }
    //if above
    if (ele.offsetTop < container.scrollTop){
        container.scrollTop = ele.offsetTop;
    }
    //if below
    else if (ele.offsetTop + ele.offsetHeight > container.scrollTop + container.offsetHeight){
        container.scrollTop = ele.offsetTop - container.offsetHeight + ele.offsetHeight;
    }
}

function lerp(a, b, t){
    return a + t * (b - a);
}
