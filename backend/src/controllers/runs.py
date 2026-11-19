from ..services import runs
from ..utils.serialization import row
class RunsController:
    list=staticmethod(runs.list_runs)
    create=staticmethod(runs.create_run)
    @staticmethod
    def get(db,id):return row(runs.get_run(db,id))
