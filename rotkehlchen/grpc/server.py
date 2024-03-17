import sqlite3
import grpc
import google.protobuf.wrappers_pb2 as wrappers
import sql_service_pb2
import sql_service_pb2_grpc
from concurrent import futures

class SQLService(sql_service_pb2_grpc.SQLServiceServicer):
    def ExecuteQuery(self, request, context):
        conn = sqlite3.connect("/Users/yabirgb/work/rotki/rotkehlchen/data/global.db")
        cursor = conn.cursor()

        # Execute the query
        cursor.execute(request.query)

        # Fetch rows and convert them to the Value format
        rows = [
            [
                sql_service_pb2.Value(value=wrappers.StringValue(string_value=str(cell)) if cell is not None else sql_service_pb2.Value(value=sql_service_pb2.NullValue(value="NULL")))
                for cell in row
            ]
            for row in cursor.fetchall()
        ]

        return sql_service_pb2.QueryResponse(rows=rows)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    sql_service_pb2_grpc.add_SQLServiceServicer_to_server(SQLService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()