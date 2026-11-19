import time
from collections import defaultdict,deque
from fastapi.responses import JSONResponse
buckets=defaultdict(deque)
async def rate_limit(request,call_next):
    if request.method in ('POST','PUT','DELETE'):
        key=(request.client.host,request.url.path); t=time.monotonic();q=buckets[key]
        while q and t-q[0]>60:q.popleft()
        if len(q)>=90:return JSONResponse({'detail':'一分钟内操作过多，请稍后重试'},status_code=429)
        q.append(t)
    return await call_next(request)
