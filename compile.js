const fs = require('fs');
var UglifyJS = require("uglify-js");
var CleanCSS = require('clean-css');
const { exec, execSync } = require('child_process');

//bring the templates up to date
var output = execSync("node insert_templates.js");
//print stdout of output
console.log(output.toString());

//load index.html
var index = fs.readFileSync('index.html', 'utf8');
console.log("processing index.html...");

//all the scripts are contained between <!--SCRIPT_INCLUDES_START--> and <!--SCRIPT_INCLUDES_END-->
var script_start_tag = '<!--SCRIPT_INCLUDES_START-->';
var script_end_tag = '<!--SCRIPT_INCLUDES_END-->';
const script_start = index.indexOf(script_start_tag);
const script_end = index.indexOf(script_end_tag);
const scripts = index.substring(script_start, script_end+script_end_tag.length);

//all the css is contained between <!--CSS_INCLUDES_START--> and <!--CSS_INCLUDES_END-->
var css_start_tag = '<!--CSS_INCLUDES_START-->';
var css_end_tag = '<!--CSS_INCLUDES_END-->';
const css_start = index.indexOf(css_start_tag);
const css_end = index.indexOf(css_end_tag);
var css = index.substring(css_start, css_end+css_end_tag.length);

//extract those sections
const css_includes = css.split('\n');
const script_includes = scripts.split('\n');

// console.log(css_includes);
// console.log(script_includes);


//construct css file list
var css_files = [];
for (var i = 0; i < css_includes.length; i++) {
    const line = css_includes[i];
    var match = line.match(/<link rel="stylesheet" href="(.+?)"/);
    if (match){
        var css_file = match[1];
        if (css_file.endsWith('.css')){
            css_files.push(css_file);
        }
    }
}
// console.log(css_files);


//construct js file list
var js_files = [];
for (var i = 0; i < script_includes.length; i++) {
    const line = script_includes[i];
    var match = line.match(/<script src="(.+?)"/);
    if (match){
        var js_file = match[1];
        if (js_file.endsWith('.js')){
            js_files.push(js_file);
        }
    }
}

// console.log(js_files);

//concatenate all css files
var css_content = '';
for (var i = 0; i < css_files.length; i++) {
    const css_file = css_files[i];
    const css_file_content = fs.readFileSync(css_file, 'utf8');
    css_content += "\n"+css_file_content;
}

//concatenate all js files
var js_content = '';
for (var i = 0; i < js_files.length; i++) {
    const js_file = js_files[i];
    const js_file_content = fs.readFileSync(js_file, 'utf8');
    js_content += "\n"+js_file_content;
}

//uglify js content
var uglified_js_content = UglifyJS.minify(js_content).code;

//clean css content
var options = { 
    
    level: {
        1: {
            all: true
        },
        2: {
            all: true
        },
    }
 };

var cleaned_css_content = new CleanCSS(options).minify(css_content);

//if bin directory exists, remove it
if (fs.existsSync('bin')){
    fs.rmSync('bin', {recursive: true});
}

//create bin directory  
fs.mkdirSync('bin');

// fs.writeFileSync('bin/style.css', cleaned_css_content.styles);
// fs.writeFileSync('bin/bfxr.js', uglified_js_content);
// var js_include_line = '<script src="bfxr.js" defer></script>';
// var css_include_line = '<link rel="stylesheet" href="style.css">';

var js_include_line = '<script>'+uglified_js_content+'</script>';
var css_include_line = '<style>'+cleaned_css_content.styles+'</style>';

//replace the old includes with the new ones
index = index.replace( scripts, js_include_line);
index = index.replace( css, css_include_line);

//write the new index.html
fs.writeFileSync('bin/index.html', index);

console.log("crushing images...");
fs.mkdirSync('bin/img');
fs.readdirSync('img').forEach(file => {
    // First copy the file to bin/img
    fs.copyFileSync(`img/${file}`, `bin/img/${file}`);
    var command = `pngcrush -rem allb -brute -reduce -ow ./bin/img/${file}`;
    exec(command);
});

//run ./gzipper perl script
exec("perl gzipper");

//move favicon.icon and favicon.png to bin
fs.copyFileSync('favicon.ico', 'bin/favicon.ico');
fs.copyFileSync('favicon.png', 'bin/favicon.png');

