'use strict';
const {spawnSync}=require('node:child_process');
const mode=process.argv[2]||'time';
const variants=mode==='time'?[
 ['TurboKnight-5-v54.sb3','v54-reference-time'],
 ['TurboKnight-5-v55.sb3','v55-time'],
 ['build/NNUE-candidate.sb3','v55-nnue-time'],
 ['build/Search-without-heuristics.sb3','v55-no-heuristics-time']
]:[['TurboKnight-5-v55.sb3','v55-depth'],['build/Search-without-heuristics.sb3','v55-no-heuristics-depth']];
for(const [file,name]of variants){
 console.log('BEGIN',name);
 const r=spawnSync(process.execPath,['tests/benchmark.js',file,mode,'benchmarks/'+name+'.json'],{encoding:'utf8',timeout:300000});
 if(r.status!==0){process.stdout.write(r.stdout||'');process.stderr.write(r.stderr||'');throw r.error||Error(name+' failed');}
 console.log(require('../benchmarks/'+name+'.json').summary);
}
