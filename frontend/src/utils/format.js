export const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const fmt=value=>typeof value==='number'?(Number.isInteger(value)?String(value):value.toLocaleString('zh-CN',{maximumFractionDigits:4})):esc(value);
export const formObject=form=>Object.fromEntries(new FormData(form));

export const localTime=value=>new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(value));
