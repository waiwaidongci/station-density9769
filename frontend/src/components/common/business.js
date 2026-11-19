import {esc,fmt,localTime} from '../../utils/format.js';import {status} from './status.js';
export function sourceOptions(sources,id){return sources.map(s=>'<option value="'+s.id+'" '+(s.id==id?'selected':'')+'>'+esc(s.name)+' · '+s.record_count+'条</option>').join('')}
export function runOptions(runs,id,completedOnly=false){return runs.filter(r=>!completedOnly||r.state==='completed').map(r=>'<option value="'+r.id+'" '+(r.id==id?'selected':'')+'>'+esc(r.name)+' · #'+r.id+'</option>').join('')}
export function metrics(items){return '<dl class="metrics">'+items.map(x=>'<div><dt>'+esc(x.label)+'</dt><dd>'+fmt(x.value)+'</dd></div>').join('')+'</dl>'}
export function runLedger(runs){return '<div class="ledger">'+runs.slice(0,8).map(r=>'<a href="#results" data-run="'+r.id+'"><small>#'+r.id+'</small><strong>'+esc(r.name)+'</strong>'+status(r.state)+'<time title="北京时间 · Asia/Shanghai">'+esc(localTime(r.created_at))+'</time></a>').join('')+'</div>'}
