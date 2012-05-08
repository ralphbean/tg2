import tg
import random, logging

try:
    from sqlalchemy.orm import Session
except ImportError:
    class Session(object):
        """SQLAlchemy Session"""

log = logging.getLogger(__name__)

class BalancedSession(Session):
    _force_engine = None

    def get_bind(self, mapper=None, clause=None):
        tg_context = tg.request_local.context._current_obj()
        config = tg_context.config
        request = tg_context.request
        app_globals = tg_context.app_globals

        engines = config.get('balanced_engines')
        if not engines:
            log.debug('Balancing disabled, using master')
            return app_globals.sa_engine

        forced_engine = self._force_engine
        if not forced_engine:
            try:
                forced_engine = request._tg_force_sqla_engine
            except TypeError:
                forced_engine = 'master'
            except AttributeError:
                pass

        if forced_engine:
            log.debug('Forced engine: %s', forced_engine)
            return engines['all'][forced_engine]
        elif self._flushing:
            log.debug('Choose engine: master')
            return engines['master']
        else:
            choosen_slave = random.choice(engines['slaves'].keys())
            log.debug('Choose engine: %s', choosen_slave)
            return engines['slaves'][choosen_slave]

    def using_engine(self, engine_name):
        return UsingEngineContext(engine_name, self)

class UsingEngineContext(object):
    def __init__(self, engine_name, DBSession=None):
        self.engine_name = engine_name
        if not DBSession:
            DBSession = tg.config['DBSession']()
        self.session = DBSession
        self.past_engine = self.session._force_engine

    def __enter__(self):
        self.session._force_engine = self.engine_name
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        self.session._force_engine = self.past_engine

def force_request_engine(engine_name):
    tg.request._tg_force_sqla_engine = engine_name