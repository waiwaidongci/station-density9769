import logging
from fastapi import Request
from fastapi.responses import JSONResponse
async def error_boundary(request:Request,call_next):
    try: return await call_next(request)
    except Exception:
        logging.exception('request failed')
        return JSONResponse({'detail':'服务暂时无法处理，请保留输入后重试'},status_code=500)
