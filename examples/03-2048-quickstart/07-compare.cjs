const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");

const root = process.argv[2];
if (!root) throw Error("Usage: node 07-compare.cjs /path/to/2048");
const modules = ["tile","grid","local_storage_manager","game_manager"];
const sources = modules.map(name => fs.readFileSync(path.join(root,"js",name+".js"),"utf8"));
const digest = crypto.createHash("sha256").update(sources.join("\n")).digest("hex");
const cases = [
  ["start","F01",[],[]],
  ["pair","F02",[[2,2]],["left"]],
  ["once","F02",[[2,2,4]],["left"]],
  ["two-pairs","F02",[[2,2,2,2]],["right"]],
  ["blocked","F02",[[2]],["left"]],
  ["persist","F03",[[2,2]],["left","reload"]],
  ["restart","F03",[[2,2]],["left","restart"]],
  ["win-hold","F04",[[1024,1024]],["left","right"]],
  ["continue-reload","F04",[[1024,1024]],["left","continue","reload"]],
  ["continue-move","F04",[[1024,1024]],["left","continue","down","reload"]],
  ["loss","F05",[[0,4,2,4],[2,4,2,4],[4,2,4,2],[2,4,2,4]],["left","reload"]]
];
function run(rows, actions) {
  const values = new Map();
  const events = [];
  const storage = {
    setItem(k,v) {values.set(k,String(v)); if(k!=="test") events.push("set:"+k);},
    getItem(k) {return values.get(k) ?? null;},
    removeItem(k) {values.delete(k); if(k!=="test") events.push("remove:"+k);}
  };
  const context = vm.createContext({window:{localStorage:storage}});
  vm.runInContext("Math.random = () => 0", context);
  for (const source of sources) vm.runInContext(source, context);
  if(rows.length) {
    const cells = Array.from({length:4},(_,x)=>Array.from({length:4},(_,y)=>
      rows[y]?.[x] ? {position:{x,y},value:rows[y][x]} : null));
    values.set("gameState", JSON.stringify({grid:{size:4,cells},score:0,won:false,over:false,keepPlaying:false}));
  }
  let handlers, lastView;
  class Input {constructor(){handlers={};} on(name,fn){handlers[name]=fn;}}
  class View {
    actuate(grid,meta) {events.push("view"); lastView=JSON.parse(JSON.stringify({cells:grid.serialize().cells,...meta}));}
    continueGame() {events.push("clearOverlay");}
  }
  function boot(){new context.GameManager(4,Input,View,context.LocalStorageManager);}
  function capture(action) {
    return {action, events:events.splice(0), lastView, saved:JSON.parse(storage.getItem("gameState")), best:storage.getItem("bestScore")};
  }
  boot();
  const trace=[capture("boot")];
  for(const action of actions){
    if(action==="reload") boot();
    else if(action==="restart") handlers.restart();
    else if(action==="continue") handlers.keepPlaying();
    else handlers.move(["up","right","down","left"].indexOf(action));
    trace.push(capture(action));
  }
  return trace;
}
const file = path.join(__dirname,"06-engine.jsonl");
if(process.argv.includes("--record")) {
  const records=cases.map(([id,feature,rows,actions])=>({id,feature,sourceSHA256:digest,rows,actions,trace:run(rows,actions)}));
  fs.writeFileSync(file,records.map(r=>JSON.stringify(r)).join("\n")+"\n",{flag:"wx"});
} else {
  for(const row of fs.readFileSync(file,"utf8").trim().split("\n").map(JSON.parse)){
    assert.deepEqual(run(row.rows,row.actions),row.trace,row.id);
    console.log("PASS",row.id);
  }
}
