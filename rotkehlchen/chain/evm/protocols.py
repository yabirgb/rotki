"""EVM protocol constants and mappings.

This module contains all protocol constants and their mappings to avoid circular imports.
"""
from typing import Final

# Protocol identifiers
UNISWAP_PROTOCOL: Final = 'UNI-V2'
UNISWAPV3_PROTOCOL: Final = 'UNI-V3'
SUSHISWAP_PROTOCOL: Final = 'SLP'
YEARN_VAULTS_V1_PROTOCOL: Final = 'yearn_vaults_v1'
YEARN_VAULTS_V2_PROTOCOL: Final = 'yearn_vaults_v2'
YEARN_VAULTS_V3_PROTOCOL: Final = 'yearn_vaults_v3'
YEARN_STAKING_PROTOCOL: Final = 'yearn_staking'
CURVE_POOL_PROTOCOL: Final = 'curve_pool'
VELODROME_POOL_PROTOCOL: Final = 'velodrome_pool'
AERODROME_POOL_PROTOCOL: Final = 'aerodrome_pool'
PICKLE_JAR_PROTOCOL: Final = 'pickle_jar'
SPAM_PROTOCOL: Final = 'spam'
GEARBOX_PROTOCOL: Final = 'gearbox'
HOP_PROTOCOL_LP: Final = 'hop_lp'
MORPHO_VAULT_PROTOCOL: Final = 'morpho_vaults'
CURVE_LENDING_VAULTS_PROTOCOL: Final = 'curve_lending_vaults'
PENDLE_PROTOCOL: Final = 'pendle'

# Import CPT constants from their respective modules
from rotkehlchen.chain.ethereum.modules.pickle_finance.constants import CPT_PICKLE
from rotkehlchen.chain.ethereum.modules.sushiswap.constants import CPT_SUSHISWAP_V2
from rotkehlchen.chain.ethereum.modules.yearn.constants import (
    CPT_YEARN_V1,
    CPT_YEARN_V2,
    CPT_YEARN_V3,
)
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.hop.constants import CPT_HOP
from rotkehlchen.chain.evm.decoding.morpho.constants import CPT_MORPHO
from rotkehlchen.chain.evm.decoding.pendle.constants import CPT_PENDLE
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V2, CPT_UNISWAP_V3
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_AERODROME, CPT_VELODROME

# Protocol to counterparty mapping
PROTOCOL_TO_COUNTERPARTY: Final[dict[str, str | None]] = {
    SPAM_PROTOCOL: None,
    AERODROME_POOL_PROTOCOL: CPT_AERODROME,
    VELODROME_POOL_PROTOCOL: CPT_VELODROME,
    PICKLE_JAR_PROTOCOL: CPT_PICKLE,
    SUSHISWAP_PROTOCOL: CPT_SUSHISWAP_V2,
    UNISWAP_PROTOCOL: CPT_UNISWAP_V2,
    UNISWAPV3_PROTOCOL: CPT_UNISWAP_V3,
    YEARN_VAULTS_V1_PROTOCOL: CPT_YEARN_V1,
    YEARN_VAULTS_V2_PROTOCOL: CPT_YEARN_V2,
    YEARN_VAULTS_V3_PROTOCOL: CPT_YEARN_V3,
    CURVE_POOL_PROTOCOL: CPT_CURVE,
    CURVE_LENDING_VAULTS_PROTOCOL: CPT_CURVE,
    PENDLE_PROTOCOL: CPT_PENDLE,
    HOP_PROTOCOL_LP: CPT_HOP,
    MORPHO_VAULT_PROTOCOL: CPT_MORPHO,
}

# The protocols for which we know how to calculate their prices
ProtocolsWithPriceLogic = (
    UNISWAP_PROTOCOL,
    YEARN_VAULTS_V2_PROTOCOL,
    CURVE_POOL_PROTOCOL,
    VELODROME_POOL_PROTOCOL,
    HOP_PROTOCOL_LP,
    UNISWAPV3_PROTOCOL,
    AERODROME_POOL_PROTOCOL,
    PENDLE_PROTOCOL,
)

# In these protocols the LP token of a pool and the pool itself are the same contract
LP_TOKEN_AS_POOL_PROTOCOLS = (
    UNISWAP_PROTOCOL,
    VELODROME_POOL_PROTOCOL,
    AERODROME_POOL_PROTOCOL,
)


def get_token_counterparty_protocol(token_protocol: str) -> str | None:
    """Converts a token's protocol identifier to the corresponding counterparty type.

    Returns None for spam tokens, otherwise maps known protocols to their CPT constants.
    If the protocol is not in the mapping, returns the protocol itself.
    """
    return PROTOCOL_TO_COUNTERPARTY.get(token_protocol, token_protocol)
