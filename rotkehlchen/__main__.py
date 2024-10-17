from gevent import monkey

monkey.patch_all()  # isort:skip

import logging
import sys
import traceback

# import grequests to ensure that it doesn't get imported after requests
import grequests  # noqa: F401
import requests  # noqa: F401

from rotkehlchen.errors.misc import DBSchemaError, SystemPermissionError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.server import RotkehlchenServer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def main() -> None:
    try:
        rotkehlchen_server = RotkehlchenServer()
    except (SystemPermissionError, DBSchemaError) as e:
        print(f'ERROR at initialization: {e!s}')
        sys.exit(1)
    except SystemExit as e:
        if e.code is None or e.code in (0, 2):
            # exit_code 2 is for invalid arguments
            exit_code = 0 if e.code is None else e.code
            sys.exit(exit_code)
        else:
            tb = traceback.format_exc()
            logging.critical(tb)
            print(f'Failed to start rotki backend:\n{tb}')
            sys.exit(1)
    except:  # noqa: B001, E722, RUF100  # pylint: disable=bare-except
        tb = traceback.format_exc()
        logging.critical(tb)
        print(f'Failed to start rotki backend:\n{tb}')
        sys.exit(1)

    rotkehlchen_server.main()


if __name__ == '__main__':
    main()
