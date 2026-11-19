const key='research-session-'+location.port;
export const session={token:localStorage.getItem(key)||'',user:null,set(data){this.token=data.token;this.user=data.user;localStorage.setItem(key,this.token)},logout(){this.token='';this.user=null;localStorage.removeItem(key)},get writable(){return this.user&&this.user.role!=='viewer'}};
