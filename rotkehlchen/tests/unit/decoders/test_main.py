def test_decoders_initialization(evm_transaction_decoder):
    """Make sure that all decoders we have created are detected and initialized"""
    assert set(evm_transaction_decoder.decoders.keys()) == {
        'Aavev1',
        'Airdrops',
        'Compound',
        'Curve',
        'Dxdaomesa',
        'Ens',
        'Gitcoin',
        'Kyber',
        'Liquity',
        'Makerdao',
        'Oneinchv1',
        'Oneinchv2',
        'PickleFinance',
        'Sushiswap',
        'Uniswapv1',
        'Uniswapv2',
        'Uniswapv3',
        'Votium',
        'Zksync',
        'Hop',
        'Convex',
    }

    assert evm_transaction_decoder.all_counterparties == {
        'kyber legacy',
        'element-finance',
        'badger',
        'makerdao vault',
        '1inch-v2',
        'uniswap',
        'curve',
        'gnosis-chain',
        'gas',
        'ens',
        'liquity',
        'shapeshift',
        'hop-protocol',
        '1inch',
        'gitcoin',
        'makerdao migration',
        'uniswap-v1',
        'uniswap-v2',
        'uniswap-v3',
        'zksync',
        'frax',
        'makerdao dsr',
        'pickle finance',
        'convex',
        'votium',
        'aave-v1',
        'compound',
        'dxdaomesa',
        '1inch-v1',
        'convex',
        'sushiswap-v2',
    }
