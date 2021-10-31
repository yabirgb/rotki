from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, List

from rotkehlchen.typing import ChecksumEthAddress


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class ConvexExtraReward:
    contract: ChecksumEthAddress
    token: ChecksumEthAddress
    name: str


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class ConvexPool:
    """Represent a convex pool"""
    lp: ChecksumEthAddress
    token: ChecksumEthAddress
    gauge: ChecksumEthAddress
    crv_rewards: ChecksumEthAddress
    name: str
    extras: List[ConvexExtraReward]
    id: int


def get_convex_pools() -> Dict[int, ConvexPool]:
    """Get pools in a CurvePool structure from information file"""
    pools = {}
    dir_path = Path(__file__).resolve().parent.parent.parent.parent
    with open(dir_path / 'data' / 'convex_data.json', 'r') as f:
        data = json.loads(f.read())
        for pool_info in data:
            lp = pool_info['id']
            extras = []
            if 'extras' in pool_info:
                for extra_info in pool_info['extras']:
                    extras.append(
                        ConvexExtraReward(
                            contract=extra_info['contract'],
                            token=extra_info['token'],
                            name=extra_info['name'],
                        )
                    )
            pools[lp] = ConvexPool(
                lp=pool_info['lptoken'],
                token=pool_info['token'],
                gauge=pool_info['gauge'],
                crv_rewards=pool_info['crvRewards'],
                name=pool_info['name'],
                extras=extras,
                id=pool_info['id']
            )
    return pools
