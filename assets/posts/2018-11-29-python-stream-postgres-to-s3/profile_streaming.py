from memory_profiler import profile
from smart_open import smart_open
from sqlalchemy import create_engine
from time import perf_counter
from db_read_stream import DbReadStream


@profile
def main():
    start_time = perf_counter()

    # Create the DB read stream,
    # and configure to execute a large query
    db_read_stream = DbReadStream(
        db=create_engine('postgres://postgres@localhost:5432'),
        query="SELECT * FROM test_record",
    )

    # Create S3 write stream
    s3_write_stream = smart_open('s3://my-s3-bucket/db.csv', 'wb')

    # Iterate through the DB records, and write to S3
    while True:
        # Read 1 MB at a time
        chunk = db_read_stream.read(1024 * 1024)
        if not chunk:
            break

        s3_write_stream.write(chunk)

    # Close the stream
    db_read_stream.close()
    s3_write_stream.close()

    duration = perf_counter() - start_time
    print(f"Complete in {round(duration, 2)}s")


main()
