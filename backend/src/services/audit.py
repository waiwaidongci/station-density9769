from ..models.audit import Audit
from ..utils.serialization import now
def log(db,user,action,target,detail=''):
    db.add(Audit(actor=user.email if hasattr(user,'email') else str(user),action=action,target=str(target),detail=detail,created_at=now()))
