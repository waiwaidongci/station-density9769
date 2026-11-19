import {domain} from '../constants/domain.js';import {research} from '../stores/research.js';import {session} from '../stores/session.js';import {retestApi} from '../api/research.js';import {runOptions} from '../components/common/business.js';import {status} from '../components/common/status.js';import {table} from '../components/common/table.js';import {esc,fmt,formObject,localTime} from '../utils/format.js';import {action,toast,bind} from '../hooks/actions.js';

const pval=value=>typeof value!=='number'?esc(value):value<0.0001?'< 0.0001':fmt(value);
const leaseExpired=study=>study.state==='running'&&study.heartbeat_at&&Date.now()-new Date(study.heartbeat_at).getTime()>120000;
const pairTable=(result,kind,columns)=>{
  const rows=result?.pairing?.[kind]||[];
  if(!rows.length)return '<p class="fine">无</p>';
  return table(rows,columns,{limit:50});
};

function studyLedger(){
  if(!research.retests.length)return '<div class="empty">还没有复测研究。先完成一份早期密度研究，再冻结两期复测。</div>';
  return '<div class="ledger retest-ledger">'+research.retests.map(s=>'<a href="#retest" data-retest="'+s.id+'"><small>#'+s.id+'</small><strong>'+esc(s.name)+'</strong>'+status(s.state)+(s.priority_zones?.length?'<span class="status approved">优先 '+s.priority_zones.length+' 区</span>':'')+'<time title="北京时间 · Asia/Shanghai">'+esc(localTime(s.created_at))+'</time></a>').join('')+'</div>';
}

export async function retestPage(){
  const study=research.retestId?await retestApi.get(research.retestId):null;
  research.activeRetest=study;
  const result=study?.result;
  const verification=study?.verification;
  const zones=result?.zones||[];
  const priority=result?.priority_zones||[];
  return '<section class="page-heading"><p class="eyebrow">06 / PAIRED RETEST</p><h1>两期复测，按站号对上，再校正全局。</h1><p>站号取样本编号末尾数字（编号不含数字时以编号本身为准）；分区与标准化尺度沿用早期密度研究。每区取三项标准化平均变化的最大绝对值，同站三项一起换期，每次换期取全区最大统计量校正 p 值。</p></section>'
    +'<div class="split"><section><label class="compact">复测研究<select id="retest-select">'+research.retests.map(s=>'<option value="'+s.id+'" '+(s.id==research.retestId?'selected':'')+'>'+esc(s.name)+' · #'+s.id+'</option>').join('')+'</select></label>'
    +(!study?'<div class="empty">先选择或新建一份复测研究。</div>':study.state==='failed'?'<div class="failure"><h2>试算或核对未通过</h2><p>'+esc(study.error||'未知错误')+'</p>'+(study.verification?'<h3>核对明细</h3>'+table(study.verification.checks.map(c=>({...c,ok:c.ok?'通过':'未通过'})),[{key:'name',label:'核对项'},{key:'ok',label:'通过'},{key:'detail',label:'细节'}],{limit:50}):'')+(session.writable&&!(study.error||'').startsWith('结果核对未通过')?'<button id="retest-retry">按同一冻结算式重新试算</button>':'')+'<p class="fine">已完成的置换批次会保留，恢复时不会重复计入；核对未通过的记录需先排查快照与算法口径。</p></div>'
      :study.state==='queued'||study.state==='running'?'<div class="pending"><span class="spinner"></span><h2>独立 worker 正在分批试算</h2><p>已完成 '+esc(String(study.progress?.batches_done||0))+' / '+esc(String(study.progress?.batches||'?'))+' 批；中断后可从已完成批次恢复，不会重复计入。</p>'+(session.writable?'<button id="retest-retry" class="secondary">中断则按已完成批次恢复</button>':'')+'</div>'
      :'<div class="run-title"><h2>'+esc(study.name)+'</h2>'+status(study.state)+'<small>#'+study.id+' · 早期任务 #'+study.early_run_id+' · 两期来源 #'+study.period1_source_id+' / #'+study.period2_source_id+'</small>'+(report(study,priority))+'</div>'
        +'<p class="fine">'+(result?.permutation.mode==='full_enumeration'?'配对数不足 '+result.permutation.threshold+'，全枚举 ':'固定种子 '+result?.permutation.seed+'，抽取 ')+fmt(result?.permutation.total)+' 次 · 配对站 '+result?.pairing.paired+' 个 · α = '+result?.alpha+'</p>'
        +priorityBlock(priority)
        +'<h2>各区校正结果</h2>'+table(zones.map(z=>({zone:z.zone,n:z.n,max_abs:z.max_abs,max_feature:domain.column_labels[z.max_feature]||z.max_feature,p_value:z.p_value,priority:z.priority?'优先复访':'—'})),[{key:'zone',label:'早期分区'},{key:'n',label:'配对站数'},{key:'max_abs',label:'三项最大标准化变化'},{key:'max_feature',label:'最大项'},{key:'p_value',label:'校正 p 值'},{key:'priority',label:'结论'}],{limit:zones.length})
        +'<p class="fine">观测均值（原始量纲）：'+zones.map(z=>'区'+z.zone+' '+domain.fields.map(f=>esc(f[1])+' '+fmt(z.means_raw[f[0]])).join(' / ')).join('；')+'</p>'
        +(result?.excluded_zones?.length?'<h2>配对不足、未纳入检验的分区</h2>'+table(result.excluded_zones.map(z=>({...z,stations:z.stations.join('、')})),[{key:'zone',label:'早期分区'},{key:'n',label:'配对站数'},{key:'stations',label:'站号'}],{limit:50}):'')
        +'<h2>配对依据核对</h2><div class="pair-lists"><section><h3>缺配站号</h3>'+pairTable(result,'unmatched',[{key:'station',label:'站号'},{key:'period1',label:'第一期编号'},{key:'period2',label:'第二期编号'},{key:'reason',label:'说明'}])+'</section><section><h3>无分区站（单列）</h3>'+pairTable(result,'unzoned',[{key:'station',label:'站号'},{key:'reference',label:'样本编号'},{key:'early_reference',label:'早期编号'},{key:'reason',label:'说明'}])+'</section><section><h3>字段缺失、无法代入</h3>'+pairTable(result,'invalid',[{key:'station',label:'站号'},{key:'reference1',label:'第一期编号'},{key:'reference2',label:'第二期编号'},{key:'reason',label:'说明'}])+'</section></div>'
        +(result?.pairing?.conflicts?.length?'<h3>站号冲突</h3>'+table(result.pairing.conflicts,[{key:'period',label:'期次'},{key:'reference',label:'样本编号'},{key:'reason',label:'说明'}],{limit:50}):'')
        +'<h2>发布前核对</h2>'+(verification?table(verification.checks.map(c=>({...c,ok:c.ok?'通过':'未通过',detail:c.detail.length>120?c.detail.slice(0,117)+'…':c.detail})),[{key:'name',label:'核对项'},{key:'ok',label:'通过'},{key:'detail',label:'细节'}],{limit:50})+'<p class="fine">'+esc(verification.summary)+'</p>':'<p class="fine">试算未齐全，核对未生成。</p>')
    )
    +'</section><aside class="entry-sheet">'
    +(session.writable?'<h2>新建复测研究</h2><form id="retest-form"><label>复测名称<input name="name" required value="十一月两期复测"></label><label>早期密度研究<select name="early_run_id">'+runOptions(research.runs,research.runId,true)+'</select></label><label>第一期复测来源<select name="period1_source_id">'+sourcePick(research.period1_source_id)+'</select></label><label>第二期复测来源<select name="period2_source_id">'+sourcePick(research.period2_source_id,true)+'</select></label><p class="fine">提交即冻结早期分区、标准化尺度与两期全部样本。缺配、重复与无分区站在结果中单独列出。</p><button type="submit">冻结并试算 →</button></form>':'<h2>只读</h2><p>复测由分析师或负责人创建；阅读者可查看已发布研究的优先复访分区。</p>')
    +'<h2>最近复测</h2>'+studyLedger()+'</aside></div>';
}

function sourcePick(selected,second=false){
  const first=research.sources[0]?.id;
  return research.sources.map((s,i)=>'<option value="'+s.id+'" '+((selected?selected===s.id:(second?i===1:first===s.id))?'selected':'')+'>'+esc(s.name)+' · '+s.record_count+'条</option>').join('');
}

function priorityBlock(priority){
  if(!priority.length)return '<div class="method-sheet retest-priority"><p class="eyebrow">PRIORITY / 校正后 α &lt; 0.05</p><p>没有校正后 p 值低于 0.05 的分区；两期变化不足以支持优先复访。</p></div>';
  return '<div class="method-sheet retest-priority"><p class="eyebrow">PRIORITY / 校正后 α &lt; 0.05</p><h2>优先复访分区</h2><ol>'+priority.map(z=>'<li><b>区 '+z.zone+'</b> · '+z.n+' 站 · 最大变化 '+esc(domain.column_labels[z.max_feature]||z.max_feature)+' '+fmt(z.max_abs)+'σ · p = '+pval(z.p_value)+'</li>').join('')+'</ol><p class="fine">p 值已在全区最大统计量下校正；优先顺序按校正后 p 值从小到大。</p></div>';
}

function report(study,priority){
  if(study.state==='published')return '<span class="status approved">已发布 · 优先 '+priority.length+' 区</span>';
  if(study.state==='verified'&&session.user.role==='admin')return '<button id="retest-publish">发布复测结论 ✓</button>';
  return '';
}

export function bindRetest(refresh){
  bind('#retest-select','change',async e=>{research.retestId=Number(e.target.value);await refresh()});
  for(const a of document.querySelectorAll('[data-retest]'))a.addEventListener('click',async event=>{event.preventDefault();research.retestId=Number(a.dataset.retest);await refresh()});
  action('#retest-form',async form=>{const data=formObject(form);const s=await retestApi.create({name:data.name,early_run_id:Number(data.early_run_id),period1_source_id:Number(data.period1_source_id),period2_source_id:Number(data.period2_source_id)});research.retestId=s.id;await refresh();toast('复测研究已冻结，worker 分批试算中')});
  bind('#retest-retry','click',async()=>{try{await retestApi.retry(research.retestId);await refresh();toast('已按同一冻结算式恢复试算')}catch(e){toast(e.message,true)}});
  bind('#retest-publish','click',async()=>{try{await retestApi.publish(research.retestId);await refresh();toast('复测结论已发布，研究页面可见优先复访分区')}catch(e){toast(e.message,true)}});
}
