from ..services import retest


class RetestController:
    list = staticmethod(retest.list_studies)
    create = staticmethod(retest.create_study)
    get = staticmethod(retest.get_study)
    retry = staticmethod(retest.retry)
    publish = staticmethod(retest.publish)
