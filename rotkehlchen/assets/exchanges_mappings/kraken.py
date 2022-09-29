from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind


WORLD_TO_KRAKEN = COMMON_ASSETS_MAPPINGS | {
    'ATOM': 'ATOM',
    'ALGO': 'ALGO',
    'AUD': 'ZAUD',
    strethaddress_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888'): 'COMP',
    'DOT': 'DOT',
    'KAVA': 'KAVA',
    strethaddress_to_identifier('0xdd974D5C2e2928deA5F71b9825b8b646686BD200'): 'KNC',
    'BSV': 'BSV',
    'ETC': 'XETC',
    'ETH': 'XETH',
    'LTC': 'XLTC',
    # REP V1
    strethaddress_to_identifier('0x1985365e9f78359a9B6AD760e32412f4a445E862'): 'XREP',
    'BTC': 'XXBT',
    'XMR': 'XXMR',
    'XRP': 'XXRP',
    'ZEC': 'XZEC',
    'EUR': 'ZEUR',
    'USD': 'ZUSD',
    'GBP': 'ZGBP',
    'CAD': 'ZCAD',
    'JPY': 'ZJPY',
    'CHF': 'CHF',
    'KRW': 'ZKRW',
    'AED': 'AED',
    # REP V2
    strethaddress_to_identifier('0x221657776846890989a759BA2973e427DfF5C9bB'): 'REPV2',
    'DAO': 'XDAO',
    strethaddress_to_identifier('0xec67005c4E498Ec7f55E092bd1d35cbC47C91892'): 'XMLN',
    'ICN': 'XICN',
    strethaddress_to_identifier('0x6810e776880C02933D47DB1b9fc05908e5386b96'): 'GNO',
    'BCH': 'BCH',
    'XLM': 'XXLM',
    'DASH': 'DASH',
    'EOS': 'EOS',
    strethaddress_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7'): 'USDT',
    'KFEE': 'KFEE',
    'ADA': 'ADA',
    'QTUM': 'QTUM',
    'NMC': 'XNMC',
    'VEN': 'XXVN',
    'DOGE': 'XXDG',
    'XTZ': 'XTZ',
    'WAVES': 'WAVES',
    'ICX': 'ICX',
    'NANO': 'NANO',
    'OMG': 'OMG',
    'SC': 'SC',
    'PAXG': 'PAXG',
    'LSK': 'LSK',
    'TRX': 'TRX',
    'OXT': 'OXT',
    'STORJ': 'STORJ',
    strethaddress_to_identifier('0xba100000625a3754423978a60c9317c58a424e3D'): 'BAL',
    'KSM': 'KSM',
    strethaddress_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52'): 'CRV',
    strethaddress_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'): 'SNX',
    'FIL': 'FIL',
    strethaddress_to_identifier('0xa117000000f279D81A1D3cc75430fAA017FA5A2e'): 'ANT',
    'KEEP': 'KEEP',
    'TBTC': 'TBTC',
    'ETH2': 'ETH2',
    strethaddress_to_identifier('0x0F5D2fB29fb7d3CFeE444a200298f468908cC942'): 'MANA',
    strethaddress_to_identifier('0xc944E90C64B2c07662A292be6244BDf05Cda44a7'): 'GRT',
    'FLOW': 'FLOW',
    'OCEAN': 'OCEAN',
    'EWT': 'EWT',
    strethaddress_to_identifier('0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'): 'MKR',
    strethaddress_to_identifier('0xFca59Cd816aB1eaD66534D82bc21E7515cE441CF'): 'RARI',
    'REN': 'REN',
    strethaddress_to_identifier('0xE41d2489571d322189246DaFA5ebDe1F4699F498'): 'ZRX',
    strethaddress_to_identifier('0x3F382DbD960E3a9bbCeaE22651E88158d2791550'): 'GHST',
    strethaddress_to_identifier('0x8290333ceF9e6D528dD5618Fb97a76f268f3EDD4'): 'ANKR',
    strethaddress_to_identifier('0x58b6A8A3302369DAEc383334672404Ee733aB239'): 'LPT',
    strethaddress_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0'): 'SAND',
    strethaddress_to_identifier('0x1F573D6Fb3F13d689FF844B4cE37794d79a7FF1C'): 'BNT',
    strethaddress_to_identifier('0xF629cBd94d3791C9250152BD8dfBDF380E2a3B9c'): 'ENJ',
    'MINA': 'MINA',
    'SRM': 'SRM',
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0x3506424F91fD33084466F402d5D97f05F8e3b4AF'): 'CHZ',
    strethaddress_to_identifier('0x8207c1FfC5B6804F6024322CcF34F29c3541Ae26'): 'OGN',
    strethaddress_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447'): 'PERP',
    strethaddress_to_identifier('0xD417144312DbF50465b1C641d016962017Ef6240'): 'CQT',
    strethaddress_to_identifier('0xF5D669627376EBd411E34b98F19C868c8ABA5ADA'): 'AXS',
    strethaddress_to_identifier('0x491604c0FDF08347Dd1fa4Ee062a822A5DD06B5D'): 'CTSI',
    strethaddress_to_identifier('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD'): 'LRC',
    'KAR': 'KAR',
    strethaddress_to_identifier('0x3472A5A71965499acd81997a54BBA8D852C6E53d'): 'BADGER',
    strethaddress_to_identifier('0x09a3EcAFa817268f77BE1283176B946C4ff2E608'): 'MIR',
    strethaddress_to_identifier('0xBA11D00c5f74255f56a5E366F4F77f5A186d7f55'): 'BAND',
    strethaddress_to_identifier('0xe28b3B32B6c345A34Ff64674606124Dd5Aceca30'): 'INJ',
    'MOVR': 'MOVR',
    'SDN': 'SDN',
    strethaddress_to_identifier('0x92D6C1e31e14520e676a687F0a93788B716BEff5'): 'DYDX',
    'OXY': 'OXY',
    'RAY': 'RAY',
    strethaddress_to_identifier('0x6c5bA91642F10282b576d91922Ae6448C9d52f4E'): 'PHA',
    'BNC': 'BNC',
    strethaddress_to_identifier('0xd2877702675e6cEb975b4A1dFf9fb7BAF4C91ea9'): 'LUNA',
    strethaddress_to_identifier('0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE'): 'SHIB',
    'AVAX': 'AVAX',
    'KILT': 'KILT',
    'STEP': 'STEP',
    'UST': 'UST',
    'MNGO': 'MNGO',
    'ORCA': 'ORCA',
    'KINT': 'KINT',
    'GLMR': 'GLMR',
    'ATLAS': 'ATLAS',
    'ACA': 'ACA',
    'AIR': 'AIR',
    'POLIS': 'POLIS',
    'KIN': 'KIN',
    'FIDA': 'FIDA',
    'ASTR': 'ASTR',
    'AKT': 'AKT',
    'SGB': 'SGB',
    'SBR': 'SBR',
    strethaddress_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0'): 'FXS',
    strethaddress_to_identifier('0xc7283b66Eb1EB5FB86327f08e1B5816b0720212B'): 'TRIBE',
    strethaddress_to_identifier('0x090185f2135308BaD17527004364eBcC2D37e5F6'): 'SPELL',
    strethaddress_to_identifier('0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B'): 'CVX',
    strethaddress_to_identifier('0xdBdb4d16EdA451D0503b854CF79D55697F90c8DF'): 'ALCX',
    strethaddress_to_identifier('0xC18360217D8F7Ab5e7c516566761Ea12Ce7F9D72'): 'ENS',
    strethaddress_to_identifier('0x1cEB5cB57C4D4E2b2433641b95Dd330A33185A44'): 'KP3R',
    strethaddress_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF'): 'IMX',
    strethaddress_to_identifier('0x25f8087EAD173b73D6e8B84329989A8eEA16CF73'): 'YGG',
    strethaddress_to_identifier('0xba5BDe662c17e2aDFF1075610382B9B691296350'): 'RARE',
    'ICP': 'ICP',
    strethaddress_to_identifier('0x0391D2021f89DC339F60Fff84546EA23E337750f'): 'BOND',
    strethaddress_to_identifier('0xAC51066d7bEC65Dc4589368da368b212745d63E8'): 'ALICE',
    strethaddress_to_identifier('0x7dE91B204C1C737bcEe6F000AAA6569Cf7061cb7'): 'XRT',
    strethaddress_to_identifier('0x18aAA7115705e8be94bfFEBDE57Af9BFc265B998'): 'AUDIO',
    strethaddress_to_identifier('0x4691937a7508860F876c9c0a2a617E7d9E945D4B'): 'WOO',
    strethaddress_to_identifier('0x7420B4b9a0110cdC71fB720908340C03F9Bc03EC'): 'JASMY',
    strethaddress_to_identifier('0x0996bFb5D057faa237640E2506BE7B4f9C46de0B'): 'RNDR',
    strethaddress_to_identifier('0x4a220E6096B25EADb88358cb44068A3248254675'): 'QNT',
    strethaddress_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA'): 'GALA',
    strethaddress_to_identifier('0xfB5c6815cA3AC72Ce9F5006869AE67f18bF77006'): 'PSTAKE',
    strethaddress_to_identifier('0x4d224452801ACEd8B2F0aebE155379bb5D594381'): 'APE',
    strethaddress_to_identifier('0x69af81e73A73B40adF4f3d4223Cd9b1ECE623074'): 'MASK',
    strethaddress_to_identifier('0x595832F8FC6BF59c85C527fEC3740A1b7a361269'): 'POWR',
    'SCRT': 'SCRT',
    strethaddress_to_identifier('0x04Fa0d235C4abf4BcF4787aF4CF447DE572eF828'): 'UMA',
    strethaddress_to_identifier('0x2e9d63788249371f1DFC918a52f8d799F4a38C94'): 'TOKE',
    strethaddress_to_identifier('0x65Ef703f5594D2573eb71Aaf55BC0CB548492df4'): 'MULTI',
    strethaddress_to_identifier('0xA4EED63db85311E22dF4473f87CcfC3DaDCFA3E3'): 'RBC',
    strethaddress_to_identifier('0x3a4f40631a4f906c2BaD353Ed06De7A5D3fCb430'): 'PLA',
    strethaddress_to_identifier('0xF17e65822b568B3903685a7c9F496CF7656Cc6C2'): 'BICO',
    strethaddress_to_identifier('0x949D48EcA67b17269629c7194F4b727d4Ef9E5d6'): 'MC',
    'MSOL': 'MSOL',
    'SAMO': 'SAMO',
    'GARI': 'GARI',
    'GST-2': 'GST',
    'GMT': 'GMT',
    'CFG': 'CFG',
    strethaddress_to_identifier('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'): 'WETH',
    strethaddress_to_identifier('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'): 'LDO',
    strethaddress_to_identifier('0x0b38210ea11411557c13457D4dA7dC6ea731B88a'): 'API3',
    'RUNE': 'RUNE',
    strethaddress_to_identifier('0x607F4C5BB672230e8672085532f7e901544a7375'): 'RLC',
    strethaddress_to_identifier('0xCdF7028ceAB81fA0C6971208e83fa7872994beE5'): 'T',
    strethaddress_to_identifier('0x32353A6C91143bfd6C7d363B546e62a9A2489A20'): 'AGLD',
    strethaddress_to_identifier('0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85'): 'FET',
    strethaddress_to_identifier('0x525A8F6F3Ba4752868cde25164382BfbaE3990e1'): 'NYM',
    strethaddress_to_identifier('0x1776e1F26f98b1A5dF9cD347953a26dd3Cb46671'): 'NMR',
    strethaddress_to_identifier('0xfA5047c9c78B8877af97BDcb85Db743fD7313d4a'): 'ROOK',
    strethaddress_to_identifier('0x41e5560054824eA6B0732E656E3Ad64E20e94E45'): 'CVC',
    strethaddress_to_identifier('0xe53EC727dbDEB9E2d5456c3be40cFF031AB40A55'): 'SUPER',
    strethaddress_to_identifier('0x31c8EAcBFFdD875c74b94b077895Bd78CF1E64A3'): 'RAD',
    'NEAR': 'NEAR',
    strethaddress_to_identifier('0x8CE9137d39326AD0cD6491fb5CC0CbA0e089b6A9'): 'SXP',
    'LUNA-3': 'LUNA2',
    strethaddress_to_identifier('0x888888848B652B3E3a0f34c96E00EEC0F3a23F72'): 'TLM',
    strethaddress_to_identifier('0x3597bfD533a99c9aa083587B074434E61Eb0A258'): 'DENT',
    strethaddress_to_identifier('0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'): 'GTC',
    strethaddress_to_identifier('0xADE00C28244d5CE17D72E40330B1c318cD12B7c3'): 'ADX',
    strethaddress_to_identifier('0x037A54AaB062628C9Bbae1FDB1583c195585fe41'): 'LCX',
    strethaddress_to_identifier('0xd084B83C305daFD76AE3E1b4E1F1fe2eCcCb3988'): 'TVK',
    strethaddress_to_identifier('0x4E15361FD6b4BB609Fa63C81A2be19d873717870'): 'FTM',
    strethaddress_to_identifier('0xB705268213D593B8FD88d3FDEFF93AFF5CbDcfAE'): 'IDEX',
    'BTT': 'BTT',
    strethaddress_to_identifier('0x8f8221aFbB33998d8584A2B05749bA73c37a938a'): 'REQ',
    strethaddress_to_identifier('0x915044526758533dfB918ecEb6e44bc21632060D'): 'CHR',
    strethaddress_to_identifier('0x77FbA179C79De5B7653F68b5039Af940AdA60ce0'): 'FORTH',
    strethaddress_to_identifier('0xef3A930e1FfFFAcd2fc13434aC81bD278B0ecC8d'): 'FIS',
    strethaddress_to_identifier('0x5Ca381bBfb58f0092df149bD3D243b08B9a8386e'): 'MXC',
    strethaddress_to_identifier('0xa0246c9032bC3A600820415aE600c6388619A14D'): 'FARM',
    strethaddress_to_identifier('0xEd04915c23f00A313a544955524EB7DBD823143d'): 'ACH',
    'MV': 'MV',
    'EGLD': 'EGLD',
    'UNFI': 'UNFI',
    'COTI': 'COTI',
    strethaddress_to_identifier('0x4CC19356f2D37338b9802aa8E8fc58B0373296E7'): 'KEY',
    strethaddress_to_identifier('0x1A4b46696b2bB4794Eb3D4c26f1c55F9170fa4C5'): 'BIT',
    'INTR': 'INTR',
    'TEER': 'TEER',
    evm_address_to_identifier('0xAE12C5930881c53715B369ceC7606B70d8EB229f', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'C98',  # noqa: E501
    evm_address_to_identifier('0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'STG',  # noqa: E501
    evm_address_to_identifier('0xB4EFd85c19999D84251304bDA99E90B92300Bd93', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RPL',  # noqa: E501
    'ETHW': 'ETHW',
    evm_address_to_identifier('0x42bBFa2e77757C645eeaAd1655E0911a7553Efbc', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BOBA',  # noqa: E501
    evm_address_to_identifier('0x2620638eda99f9e7e902ea24a285456ee9438861', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CSM',  # noqa: E501
    evm_address_to_identifier('0x5fAa989Af96Af85384b8a938c2EdE4A7378D9875', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GAL',  # noqa: E501
    evm_address_to_identifier('0xabEDe05598760E399ed7EB24900b30C51788f00F', ChainID.MATIC, EvmTokenKind.ERC20): 'SWP',  # noqa: E501
    evm_address_to_identifier('0xA2cd3D43c775978A96BdBf12d733D5A1ED94fb18', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'XCN',  # noqa: E501
    evm_address_to_identifier('0xBA50933C268F567BDC86E1aC131BE072C6B0b71a', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ARPA',  # noqa: E501
    evm_address_to_identifier('0x0f2D719407FdBeFF09D87557AbB7232601FD9F29', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SYN',  # noqa: E501
    evm_address_to_identifier('0x4C19596f5aAfF459fA38B0f7eD92F11AE6543784', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TRU',  # noqa: E501
    evm_address_to_identifier('0xa1faa113cbE53436Df28FF0aEe54275c13B40975', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALPHA',  # noqa: E501
    evm_address_to_identifier('0x57B946008913B82E4dF85f501cbAeD910e58D26C', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'POND',  # noqa: E501
    evm_address_to_identifier('0x5732046A883704404F284Ce41FfADd5b007FD668', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BLZ',  # noqa: E501
    evm_address_to_identifier('0x4F9254C83EB525f9FCf346490bbb3ed28a81C667', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CELR',  # noqa: E501
    evm_address_to_identifier('0x83e6f1E41cdd28eAcEB20Cb649155049Fac3D5Aa', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'POLS',  # noqa: E501
    'JUNO': 'JUNO',
    'NODL': 'NODL',
    'BSX': 'BSX',
}
