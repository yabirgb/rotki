import random

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
)

CONVEX_ADDR = '0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF'


@pytest.mark.parametrize('ethereum_accounts', [[CONVEX_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['convex']])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_pickle_dill(
        rotkehlchen_api_server,
        inquirer,  # pylint: disable=unused-argument
):
    """Test that we can get the status of the trove and the staked lqty"""
    async_query = random.choice([False, True])
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'convexbalancesresource',
    ), json={'async_query': async_query})
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    print(result)
    assert CONVEX_ADDR in result
    data = result[CONVEX_ADDR]
    assert 'locked_amount' in data
    assert 'locked_until' in data
    assert 'pending_rewards' in data