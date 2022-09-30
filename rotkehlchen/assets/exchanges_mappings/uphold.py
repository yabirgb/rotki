from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import strethaddress_to_identifier

WORLD_TO_UPHOLD = COMMON_ASSETS_MAPPINGS | {
    'BTC': 'BTC',
    strethaddress_to_identifier('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9'): 'AAVE',
    'XRP': 'XRP',
    'ETH': 'ETH',
    strethaddress_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF'): 'BAT',
    'ADA': 'ADA',
    'ATOM': 'ATOM',
    'BCH': 'BCH',
    'BTG': 'BTG',  # Bitcoin Gold
    strethaddress_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888'): 'COMP',
    'DASH': 'DASH',
    'DCR': 'DCR',
    'DGB': 'DGB',
    'DOGE': 'DOGE',
    'DOT': 'DOT',
    strethaddress_to_identifier('0xF629cBd94d3791C9250152BD8dfBDF380E2a3B9c'): 'ENJ',
    'EOS': 'EOS',
    'FIL': 'FIL',
    'FLOW': 'FLOW',
    'HBAR': 'HBAR',
    'HNT': 'HNT',
    'IOTA': 'MIOTA',
    strethaddress_to_identifier('0x514910771AF9Ca656af840dff83E8264EcF986CA'): 'LINK',
    'LTC': 'LTC',
    strethaddress_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0'): 'MATIC',
    strethaddress_to_identifier('0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'): 'MKR',
    'NANO': 'NANO',
    'NEO': 'NEO',
    strethaddress_to_identifier('0xd26114cd6EE289AccF82350c8d8487fedB8A0C07'): 'OMG',
    strethaddress_to_identifier('0x4575f41308EC1483f3d399aa9a2826d74Da13Deb'): 'OXT',
    strethaddress_to_identifier('0x408e41876cCCDC0F92210600ef50372656052a38'): 'REN',
    strethaddress_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'): 'SNX',
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0x476c5E26a75bd202a9683ffD34359C0CC15be0fF'): 'SRM',
    strethaddress_to_identifier('0x3883f5e181fccaF8410FA61e12b59BAd963fb645'): 'THETA',
    strethaddress_to_identifier('0xf230b790E05390FC8295F4d3F60332c93BEd42e2'): 'TRX',
    'VET': 'VET',
    strethaddress_to_identifier('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'): 'WBTC',
    strethaddress_to_identifier('0x04Fa0d235C4abf4BcF4787aF4CF447DE572eF828'): 'UMA',
    strethaddress_to_identifier('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984'): 'UNI',
    # 'UPT': 'UPT',
    'XCH': 'XCH',
    'XEM': 'NEM',
    'XLM': 'XLM',
    'XTZ': 'XTZ',
    strethaddress_to_identifier('0x05f4a42e251f2d52b8ed15E9FEdAacFcEF1FAD27'): 'ZIL',
    strethaddress_to_identifier('0xE41d2489571d322189246DaFA5ebDe1F4699F498'): 'ZRX',
}
