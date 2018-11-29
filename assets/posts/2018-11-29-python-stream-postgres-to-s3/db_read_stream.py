import csv
import io
from typing import Iterator

from smart_open import smart_open
from sqlalchemy import text as sql_text
from sqlalchemy.engine import Connection, create_engine


class DbReadStream(io.RawIOBase):
    """
    This class is an adaptation of the CustomReadStream
    from the previous example. It has been modified to read
    from a postgres database
    """

    def __init__(self, db: Connection, query: str):
        super().__init__()

        # Configure the DB connection,
        # and the query to execute
        self._db = db
        self._query = query

        # Initialize our iterator
        self._iterator = self._iterate()

        # Create a buffer to hold data
        # that is on-deck to be read
        self._buffer = b""

    def read(self, size=-1):
        """
        Read a chunk of a given size from our stream
        """
        # If size=-1, read the entire data set
        if size < 0:
            return self.readall()

        # If the buffer has less data in it than requested,
        # read data into the buffer, until it is the correct size
        while len(self._buffer) < size:
            try:
                # Read data into the buffer from our iterator
                self._buffer += next(self._iterator)
            except StopIteration:
                # If the iterator is complete, stop reading from it
                break

        # Extract data of the requested size from the buffer
        chunk = self._buffer[:size]
        self._buffer = self._buffer[size:]

        return chunk

    def _iterate(self) -> Iterator[bytes]:
        """
        Execute a query against a postgres DB
        using SQLAlchemy

        See http://docs.sqlalchemy.org/en/latest/_modules/examples/performance/large_resultsets.html
        for SQLAlchemy docs on querying large data sets
        """
        # Execute the query, creating a DB cursor object
        self._db_cursor = self._db \
            .execution_options(stream_results=True) \
            .execute(sql_text(self._query))

        while True:
            # Fetch 1000 records at a time from the DB
            records = self._db_cursor.fetchmany(1000)

            # If there are no more results, we can stop iterating
            if not records:
                yield b""
                break

            # Format results as a CSV
            csv = to_csv(records)
            yield csv.encode('utf8')

    ########
    # These methods must be implemented for the object
    # to properly implement the "file-like" IO interface
    ########

    def readable(self, *args, **kwargs):
        return True

    def writable(self, *args, **kwargs):
        return False

    def getvalue(self):
        return self.readall()

    def close(self):
        self._buffer = b""
        if hasattr(self, '_db_cursor'):
            self._db_cursor.close()


def to_csv(rows) -> str:
    csv_buffer = io.StringIO("")
    csv_writer = csv.writer(csv_buffer, lineterminator='\n')
    csv_writer.writerows(rows)
    return csv_buffer.getvalue()


# Create the DB read stream,
# and configure to execute a query
db_read_stream = DbReadStream(
    db=create_engine('postgres://postgres@localhost:5432'),
    query="SELECT * FROM test_record",
)

# Write results to a file
#write_io = open('dst.csv', 'wb')

# Or, write results to S3
write_io = smart_open('s3://my-s3-bucket/db.csv', 'wb')

# Iterate through the DB records, and write to a file
while True:
    # Read 1 MB at a time
    chunk = db_read_stream.read(1024 * 1024)
    if not chunk:
        break

    write_io.write(chunk)


db_read_stream.close()
write_io.close()
