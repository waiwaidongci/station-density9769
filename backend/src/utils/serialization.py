from datetime import datetime,timezone
def now(): return datetime.now(timezone.utc).isoformat()
def row(obj): return {c.name:getattr(obj,c.name) for c in obj.__table__.columns}
