import csv
import io
import boto3
from sqlalchemy.engine import Connection, create_engine
from memory_profiler import profile
from time import perf_counter


@profile
def main():
    start_time = perf_counter()

    # Load all DB records into memory
    db: Connection = create_engine('postgres://postgres@localhost:5432')
    results = db \
        .execute("SELECT * FROM test_record") \
        .fetchall()

    # Convert DB records to CSV
    csv_buffer = io.StringIO("")
    csv_writer = csv.writer(csv_buffer, lineterminator='\n')
    csv_writer.writerows(results)

    # Upload the CSV to S3
    s3 = boto3.client('s3')
    s3.put_object(
        Bucket='my-s3-bucket',
        Key='db.csv',
        Body=csv_buffer.getvalue().encode('utf8')
    )

    duration = perf_counter() - start_time
    print(f"Complete in {round(duration, 2)}s")


main()
