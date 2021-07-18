from rotkehlchen.constants.assets import A_USD

QUERY_USER_EVENTS = (
    """
	addLiquidityEvents(where:{{block_gte: $from_block, block_lte: $to_block, provider: $address }}){{
        pool{{
        id
        lpToken {{
            id
            decimals
        }}
        underlyingCoins {{
            index
            token {{
                id
            }}
            balance
        }}
        virtualPrice
        name
        }}
        tokenAmounts
        fees
        tokenSupply
        timestamp
        transaction
        block
    }}
	removeLiquidityEvents(where:{{block_gte: $from_block, block_lte: $to_block, provider: $address }}){{
        pool{{
        id
        lpToken {{
            id
            decimals
        }}
        underlyingCoins {{
            index
            token {{
                id
            }}
            balance
        }}
        virtualPrice
            name
        }}
        tokenAmounts
        fees
        tokenSupply
        timestamp
        transaction
        block
    }}
    """
)

def _price_calculation(
    virtual_price: int,
    tokens: List[EthereumToken],
    balances: List[int],
    timestamp: Timestamp,
    decimals: int,
) -> Price:
    """
    May raise:
    - NoPriceForGivenTimestamp if there is no price for any token on the pool
    at the given timestamp
    """
    if len(tokens) != len(balances):
        return FVal(ZERO)

    values = []
    token_prices = []
    for token_pos, token in enumerate(tokens):
        token_price = PriceHistorian().query_historical_price(token, A_USD, timestamp)
        token_prices.append(token_price)
        values.append(token_price * balances[token_pos])
    total_pool_price = sum(values)
    weights = [value/total_pool_price for value in values]
    assets_price = FVal(sum(map(operator.mul, weights, token_prices)))
    return Price((assets_price * FVal(virtual_price)) / (10 ** decimals))

class CurveFiGraph:
    """Reads Yearn vaults v2 information from the graph"""

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.premium = premium
        self.graph = Graph('https://api.thegraph.com/subgraphs/name/curvefi/curve')  # noqa: E501


    def _process_event(
        self,
        events: List[Dict[str, Any]],
        event_type: Literal['add', 'remove'],
    ) -> List[CurveFiEvent]:
        result = []
        for entry in events:
            try:
                assets = [EthereumToken(token['token']['id']) for token in entry['pool']['underlyingCoins']]
            except KeyError:
                continue
            except UnknownAsset:
                continue

            try:
                share_price = _price_calculation(
                    virtual_price=entry['virtualPrice'],
                    tokens=assets,
                    balances=[coin['balance'] for coin in entry['pool']['underlyingCoins']],
                    timestamp=entry['timestamp'],
                    decimals=entry['pool']['lpToken']['decimals'],
                )
            except NoPriceForGivenTimestamp:
                continue

            result.append(
                CurveFiEvent(
                    event_type=event_type,
                    block_number=entry['block'],
                    timestamp=entry['timestamp'],
                    lp_token=EthereumToken(entry['pool']['lpToken']['id']),
                    tx_hash=entry['id'],
                    value=
                )
            )