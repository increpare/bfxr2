var puredata_functions = {};

//for each source file - object of puredata_modules
var puredata_function_names = Object.keys(puredata_modules);

function pd_compile(src){
    //replace all ";" with ""
    src = src.replace(/;/g, "");
    src = src.replace(/\r/g, "");
    var lines = src.split("\n");

    //split each line at space
    lines = lines.map(line => line.split(" "));

    /*
    so we need to parse the lines, then build up the function
    lines look like
        #N canvas 151 188 450 300 12; 
    (can ignore everything starting with #N)

    #X obj 411 291 bp~ 134 90;
    (bp~ 134 90 is the function call with its arguments - important!)
    
    #X connect 5 0 11 0;
    (connect is the connection between the two objects - very important!)
    */

    var function_calls = [];
    var connections = [];
    for (let i = 0; i < lines.length; i++) {
        var toks = lines[i];
        switch (toks[1]) {
            case "obj":
                function_calls.push(toks.slice(4));
                break;
            case "msg":
                //basically the same as sig~
                function_calls.push(["sig~",toks[4]]);
                break;
            case "connect":
                var connection = {
                    from_ob: parseInt(toks[2]),
                    from_slot: parseInt(toks[3]),
                    to_ob: parseInt(toks[4]),
                    to_slot: parseInt(toks[5])
                };
                connections.push(connection);
                break;
        }
    }

    var function_body = "";
    var output_node_idx = function_calls.findIndex(call => call[0] === "outlet~");

    var function_tree = build_function_tree(function_calls, connections,output_node_idx);
    var function_body = build_function_body(function_tree);
    console.log(function_body);
    var fn = new Function("envelope_signal", function_body);
    return fn;
}

var function_info = {
    "outlet~":{
        input_slots:1,
        parameter_indices:[],      
        js_name:"outlet~"
    },
    "inlet~":{
        input_slots:0,
        parameter_indices:[],   
        js_name:"inlet~"
    },
    "*~":{
        input_slots:2,
        parameter_indices:[1],
        js_name:"pd_mul"
    },
    "/~":{
        input_slots:2,
        parameter_indices:[1],
        js_name:"pd_div"
    },
    "+~":{
        input_slots:2,
        parameter_indices:[1],
        js_name:"pd_add"
    },
    "sig~":{
        input_slots:1,
        parameter_indices:[0],
        js_name:"pd_c"
    },
    "vcf~":{
        input_slots:3,
        parameter_indices:[2],
        js_name:"pd_vcf"
    },
    "hip~":{
        input_slots:2,
        parameter_indices:[1],
        js_name:"pd_hip"
    },
    "lop~":{
        input_slots:2,
        parameter_indices:[1],
        js_name:"pd_lop"
    },
    "noise~":{
        input_slots:0,
        parameter_indices:[],
        js_name:"pd_noise"
    },
    "clip~":{
        input_slots:3,
        parameter_indices:[1,2],
        js_name:"pd_clip"
    },
    "osc~":{
        input_slots:1,
        parameter_indices:[0],
        js_name:"pd_osc"
    },
    "bp~":{
        input_slots:3,
        parameter_indices:[1,2],
        js_name:"pd_bp"
    },
    "sqrt~":{
        input_slots:1,
        parameter_indices:[0],
        js_name:"pd_sqrt"
    }
    
}

function build_function_tree(function_calls, connections, cur_node_idx){
    var function_call = function_calls[cur_node_idx];
    var node_name = function_call[0];
    var constructor_arguments = function_call.slice(1);
    if (!function_info.hasOwnProperty(node_name)){
        console.error("Unknown function: " + node_name);
    }
    var fn_info = function_info[node_name];
    var node_input_slots = fn_info.input_slots;
    
    // Fix: Create unique arrays for each slot instead of references to the same array
    var input_connection_array = Array(node_input_slots).fill().map(() => []);

    //all functions that connect to the current node
    var input_connections = connections.filter(connection => connection.to_ob === cur_node_idx);    
    for (let i = 0; i < input_connections.length; i++) {
        var connection = input_connections[i];
        // this would be more complicated if any of our functions had multiple outputs,
        // but in practice this, happily, never happens!
        var connection_data = build_function_tree(function_calls, connections, connection.from_ob);
        input_connection_array[connection.to_slot].push(connection_data);
    }
    var call_data = {
        node_name: node_name,
        inputs: input_connection_array,
        constructor_arguments: constructor_arguments,
        node_id: cur_node_idx
    }
    return call_data;
}


function assign_variable_names(syntax_tree_branch,idx,name_dictionary){
    if (name_dictionary.hasOwnProperty(syntax_tree_branch.node_id)){
        if (name_dictionary[syntax_tree_branch.node_id]<idx){
            name_dictionary[syntax_tree_branch.node_id] = idx;
        }
    } else {
        name_dictionary[syntax_tree_branch.node_id] = idx;
    }
    idx++;
    for (let i = 0; i < syntax_tree_branch.inputs.length; i++) {
        for (let j = 0; j < syntax_tree_branch.inputs[i].length; j++) {
            idx = assign_variable_names(syntax_tree_branch.inputs[i][j],idx,name_dictionary);
        }
    }
    return idx;
}


function reslot_constructor_arguments(fn_name,args){
    var fn_info = function_info[fn_name];
    var input_slots = fn_info.input_slots;
    var parameter_indices = fn_info.parameter_indices;
    //this args[i] should go to args[parameter_indices[i]]
    var reslot_args = Array(input_slots).fill(-1);
    for (let i = 0; i < input_slots; i++) {
        reslot_args[parameter_indices[i]] = args[i];
    }
    return reslot_args;
}

function flatten_syntax_tree(syntax_tree_branch, result,name_dictionary){
    //replace the node_name with the variable name
    var flattened_node = {
        node_name: syntax_tree_branch.node_name,
        node_id: syntax_tree_branch.node_id,
        node_idx: name_dictionary[syntax_tree_branch.node_id],
        constructor_arguments: reslot_constructor_arguments(syntax_tree_branch.node_name,syntax_tree_branch.constructor_arguments),
        inputs:[]
    };
    for (let i = 0; i < syntax_tree_branch.inputs.length; i++) {
        var branch_input_slot = syntax_tree_branch.inputs[i];
        var slot_input=[];        
        for (let j = 0; j < branch_input_slot.length; j++) {
            var slot_entry = branch_input_slot[j];
            var var_idx = name_dictionary[slot_entry.node_id];
            slot_input.push(var_idx);
            flatten_syntax_tree(slot_entry, result,name_dictionary);
        }
        flattened_node.inputs.push(slot_input);
    }
    result.push(flattened_node);
}

function strip_duplicate_nodes(flattened_tree){
    var visited_ids = [];
    for (let i = 0; i < flattened_tree.length; i++) {
        var node = flattened_tree[i];
        if (visited_ids.includes(node.node_id)){
            flattened_tree.splice(i,1);
            i--;
        }
        visited_ids.push(node.node_id);
    }
}
function build_function_body(function_tree){
    var name_dictionary ={};
    assign_variable_names(function_tree,0,name_dictionary);
    console.log(function_tree);
    var flattened_tree=[];
    flatten_syntax_tree(function_tree,flattened_tree,name_dictionary);
    strip_duplicate_nodes(flattened_tree);
    //sort by node_idx, big to small
    flattened_tree.sort((a,b) => b.node_idx - a.node_idx);
    console.log(flattened_tree);
    
    var function_body = "";
    for (let i = 0; i < flattened_tree.length; i++) {
        var node = flattened_tree[i];
        //inputs is a array of arrays - we need to have the slots like just s_1 if it's one input, or summing if it's multiple, like
        // pd_polyadd(s_1,s_2,s_3)
        var args = "";
        for (let j = 0; j < node.inputs.length; j++) {
            if (j>0){
                args += ",";
            }
            var slot_input = node.inputs[j];
            if (slot_input.length === 0){
                if (node.constructor_arguments[j]===-1){
                    args += "NULL";
                } else {
                    args += `pd_c(${node.constructor_arguments[j]})`;
                }
            } else if (slot_input.length === 1){
                args += `s_${slot_input[0]}`;
            } else {
                args += `pd_polyadd(${slot_input.map(input => `s_${input}`).join(",")})`;
            }
        }
        
        // Fix: Convert PureData function names to valid JavaScript function names
        var js_funcname = node.node_name;
        if (js_funcname==="inlet~"){
            function_body += `const s_${node.node_idx} = envelope_signal;\n`;
        } else if (js_funcname==="outlet~"){
            function_body += `const s_${node.node_idx} = ${args};\n`;
        } else {
            if (function_info.hasOwnProperty(node.node_name)){
                js_funcname = function_info[node.node_name].js_name;
            } else {
                console.error("Unknown function: " + node.node_name);
            }
            function_body += `const s_${node.node_idx} = ${js_funcname}(${args});\n`;
        }
    }
    function_body += `return s_0;\n`;
    return function_body;
}

for (let i = 0; i < puredata_function_names.length; i++) {
    var function_name = puredata_function_names[i];
    var pd_source = puredata_modules[function_name];
    console.log("loading "+function_name);
    var pd_compiled = pd_compile(pd_source);
    puredata_functions[function_name] = pd_compiled;
}
