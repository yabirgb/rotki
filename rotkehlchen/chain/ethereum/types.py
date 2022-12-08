from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    # This is a list of all ethereum contracts that are guaranteed to be returned
    # by EthereumContracts as they are stored in the file/DB
    ETHEREUM_KNOWN_CONTRACTS = Literal[
        'AAVE_V1_LENDING_POOL',
        'AAVE_V2_LENDING_POOL',
        'CONVEX_BOOSTER',
        'CURVEFI_3POOLSWAP',
        'CURVEFI_A3CRVSWAP',
        'CURVEFI_BUSDSWAP',
        'CURVEFI_GUSDC3CRVSWAP',
        'CURVEFI_PAXSWAP',
        'CURVEFI_RENSWAP',
        'CURVEFI_SRENSWAP',
        'CURVEFI_SUSDV2SWAP',
        'CURVEFI_YSWAP',
        'CURVE_ADDRESS_PROVIDER',
        'DS_PROXY_REGISTRY',
        'ENS_PUBLIC_RESOLVER_2',
        'ENS_REVERSE_RECORDS',
        'ENS_REVERSE_RESOLVER',
        'MULTICALL2',
        'BALANCE_SCAN',
        'LIQUITY_STABILITY_POOL',
        'LIQUITY_TROVE_MANAGER',
        'MAKERDAO_AAVE_A_JOIN',
        'MAKERDAO_BAL_A_JOIN',
        'MAKERDAO_BAT_A_JOIN',
        'MAKERDAO_CAT',
        'MAKERDAO_CDP_MANAGER',
        'MAKERDAO_COMP_A_JOIN',
        'MAKERDAO_DAI_JOIN',
        'MAKERDAO_ETH_A_JOIN',
        'MAKERDAO_ETH_B_JOIN',
        'MAKERDAO_ETH_C_JOIN',
        'MAKERDAO_GET_CDPS',
        'MAKERDAO_GUSD_A_JOIN',
        'MAKERDAO_JUG',
        'MAKERDAO_KNC_A_JOIN',
        'MAKERDAO_LINK_A_JOIN',
        'MAKERDAO_LRC_A_JOIN',
        'MAKERDAO_MANA_A_JOIN',
        'MAKERDAO_MATIC_A_JOIN',
        'MAKERDAO_PAXUSD_A_JOIN',
        'MAKERDAO_POT',
        'MAKERDAO_RENBTC_A_JOIN',
        'MAKERDAO_SPOT',
        'MAKERDAO_TUSD_A_JOIN',
        'MAKERDAO_UNI_A_JOIN',
        'MAKERDAO_USDC_A_JOIN',
        'MAKERDAO_USDC_B_JOIN',
        'MAKERDAO_USDT_A_JOIN',
        'MAKERDAO_VAT',
        'MAKERDAO_WBTC_A_JOIN',
        'MAKERDAO_WBTC_B_JOIN',
        'MAKERDAO_WBTC_C_JOIN',
        'MAKERDAO_YFI_A_JOIN',
        'MAKERDAO_ZRX_A_JOIN',
        'PICKLE_DILL',
        'PICKLE_DILL_REWARDS',
        'SADDLE_ALETH_POOL',
        'UNISWAP_V2_FACTORY',
        'UNISWAP_V3_FACTORY',
        'UNISWAP_V3_NFT_MANAGER',
        'YEARN_3CRV_VAULT',
        'YEARN_A3CRV_VAULT',
        'YEARN_ALINK_VAULT',
        'YEARN_ASUSD_VAULT',
        'YEARN_BBTC_SBTC_VAULT',
        'YEARN_BCURVE_VAULT',
        'YEARN_CDAI_CUSDC_VAULT',
        'YEARN_DAI_VAULT',
        'YEARN_DUSD_3CRV_VAULT',
        'YEARN_ETH_ANKER_VAULT',
        'YEARN_EURS_VAULT',
        'YEARN_GUSD_3CRV_VAULT',
        'YEARN_GUSD_VAULT',
        'YEARN_HBTC_WBTC_VAULT',
        'YEARN_HUSD_3CRV_VAULT',
        'YEARN_MUSD_3CRV_VAULT',
        'YEARN_MUSD_VAULT',
        'YEARN_OBTC_SBTC_VAULT',
        'YEARN_PSLP_VAULT',
        'YEARN_RENBTC_WBTC_VAULT',
        'YEARN_SRENCURVE_VAULT',
        'YEARN_SUSD_3CRV_VAULT',
        'YEARN_TBTC_SBTC_VAULT',
        'YEARN_TUSD_VAULT',
        'YEARN_USDC_VAULT',
        'YEARN_USDN_3CRV_VAULT',
        'YEARN_USDP_3CRV_VAULT',
        'YEARN_USDT_VAULT',
        'YEARN_UST_3CRV_VAULT',
        'YEARN_WETH_VAULT',
        'YEARN_YCRV_VAULT',
        'YEARN_YFI_VAULT',
    ]
    # This is a list of all ethereum abi that are guaranteed to be returned
    # by EthereumContracts as they are stored in the file/DB
    ETHEREUM_KNOWN_ABI = Literal[
        'ATOKEN',
        'ATOKEN_V2',
        'CONVEX_LP_TOKEN',
        'CTOKEN',
        'CURVE_METAPOOL_FACTORY',
        'CURVE_POOL',
        'CURVE_REGISTRY',
        'ERC20_TOKEN',
        'ERC721_TOKEN',
        'FARM_ASSET',
        'UNISWAP_V2_LP',
        'UNISWAP_V3_POOL',
        'UNIV1_LP',
        'YEARN_VAULT_V2',
        'ZERION_ADAPTER',
    ]
