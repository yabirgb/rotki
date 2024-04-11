import logging
from typing import TYPE_CHECKING
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_DECODING_OUTPUT
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.decoding.weth.decoder import WethDecoder as EthBaseWethDecoder
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext, DecodingOutput


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class WethDecoder(EthBaseWethDecoder):
    def _decode_deposit_event(self, context: 'DecoderContext') -> 'DecodingOutput':
        depositor = hex_or_bytes_to_address(context.tx_log.topics[1])
        deposited_amount_raw = hex_or_bytes_to_int(context.tx_log.data[:32])
        deposited_amount = asset_normalized_value(
            amount=deposited_amount_raw,
            asset=self.base_asset,
        )

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.address in (self.wrapped_token.evm_address, depositor) and
                event.balance.amount == deposited_amount and
                event.asset == self.base_asset
            ):
                if event.address == depositor:
                    return DEFAULT_DECODING_OUTPUT

                event.counterparty = self.counterparty
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Wrap {deposited_amount} {self.base_asset.symbol} in {self.wrapped_token.symbol}'  # noqa: E501
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.balance.amount == deposited_amount and
                event.asset == self.wrapped_token
            ):  # scroll WETH does emit an event on transfer so we can edit the event instead of creating a new one  # noqa: E501
                event.notes = f'Receive {deposited_amount} {self.wrapped_token.symbol}'
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = self.counterparty
                event.location_label = depositor
                event.address = context.transaction.to_address

        return DEFAULT_DECODING_OUTPUT

    def _decode_withdrawal_event(self, context: 'DecoderContext') -> 'DecodingOutput':
        withdrawer = hex_or_bytes_to_address(context.tx_log.topics[1])
        withdrawn_amount_raw = hex_or_bytes_to_int(context.tx_log.data[:32])
        withdrawn_amount = asset_normalized_value(
            amount=withdrawn_amount_raw,
            asset=self.base_asset,
        )
        in_event = out_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.address in (self.wrapped_token.evm_address, withdrawer) and
                event.balance.amount == withdrawn_amount and
                event.asset == self.base_asset
            ):
                if event.address == withdrawer:
                    return DEFAULT_DECODING_OUTPUT

                in_event = event
                event.notes = f'Receive {withdrawn_amount} {self.base_asset.symbol}'
                event.counterparty = self.counterparty
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.balance.amount == withdrawn_amount and
                event.asset == self.wrapped_token
            ):  # scroll WETH does emit an event on transfer so we can edit the event instead of creating a new one  # noqa: E501
                event.notes = f'Unwrap {withdrawn_amount} {self.wrapped_token.symbol}'
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = self.counterparty
                event.location_label = withdrawer
                event.address = context.transaction.to_address
                out_event = event

        if in_event is None or out_event is None:
            log.error(f'Could not find the corresponding events when decoding weth withdrawal {context.transaction.tx_hash.hex()}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT
