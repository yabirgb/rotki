# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import sql_service_pb2 as sql__service__pb2


class SQLServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.ExecuteQuery = channel.unary_unary(
                '/sql_service.SQLService/ExecuteQuery',
                request_serializer=sql__service__pb2.QueryRequest.SerializeToString,
                response_deserializer=sql__service__pb2.QueryResponse.FromString,
                )


class SQLServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def ExecuteQuery(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_SQLServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'ExecuteQuery': grpc.unary_unary_rpc_method_handler(
                    servicer.ExecuteQuery,
                    request_deserializer=sql__service__pb2.QueryRequest.FromString,
                    response_serializer=sql__service__pb2.QueryResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'sql_service.SQLService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class SQLService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def ExecuteQuery(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/sql_service.SQLService/ExecuteQuery',
            sql__service__pb2.QueryRequest.SerializeToString,
            sql__service__pb2.QueryResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
