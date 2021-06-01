import epsagon.wrappers.python_function
import epsagon.runners.python_function
import epsagon.constants
import mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


DB_NAME = 'db'
HOST_NAME = 'host'
ENGINE = create_engine('postgresql://user:password@{}/{}'.format(HOST_NAME, DB_NAME))


@mock.patch('epsagon.events.sqlalchemy.SqlAlchemyEvent')
def test_sanity(sqlalchemy_event_mock):
    retval = 'success'

    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function():
        session = sessionmaker(bind=ENGINE)()
        session.close()
        return retval

    assert wrapped_function() == retval
    init_instrumentation, close_instrumentation = [
        call.args for call in sqlalchemy_event_mock.call_args_list
    ]

    assert init_instrumentation[-1] =='initialize'
    assert close_instrumentation[-1] == 'close'

    init_instrumentation[1].bind.url.database = DB_NAME
    init_instrumentation[1].bind.url.host = HOST_NAME
    close_instrumentation[1].bind.url.database = DB_NAME
    close_instrumentation[1].bind.url.host = HOST_NAME
