from typing import TYPE_CHECKING

import pytest

from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr
@pytest.mark.parametrize(('address', 'expected_active'), [
    ('0xdfc24b077bc1425AD1DEA75bCB6f8158E10Df303', True),  # HLP vault
    ('0x2Ba553d9F990a3B66b03b2dC0D030dfC1c061036', True),  # regular user
    ('0x7a3F1c9e5b2d48a6c0E1f39B8d4A52c7E6b10f93', False),  # never seen by hyperliquid core
])
def test_has_core_activity(address: ChecksumEvmAddress, expected_active: bool) -> None:
    assert HyperliquidAPI().has_core_activity(address=address) is expected_active
