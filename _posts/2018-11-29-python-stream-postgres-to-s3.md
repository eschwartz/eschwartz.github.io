---
layout: post
tags : [python, AWS, S3, streaming, postgres]
title: "Using Python to Stream Large Data Sets from Postgres to AWS S3"
---

Streaming allows you to move and transform data without holding the data in memory, or in a intermediary file location. This allows you to work with very large data sets, without having to scale up your hardware.

In Python, you may be familiar with the built-in [`FileIO`](https://docs.python.org/3/library/io.html#io.FileIO) object used to read and write to files:

```python
# Create a FileIO object in write mode
dst_file = open('dst.txt', 'w')

# Create a FileIO object in read mode
src_file = open('src.txt', 'r')

# Iterate through the src.txt file data
for chunk in src_file:
    # Write to the dst.txt file
    dst_file.write(chunk)

# Close the file handles
src_file.close()
dst_file.close()
```

In this example, we're streaming data one chunk at a time from `src.txt`, and writing it to `dst.txt`. But what if we want to stream data between sources that are not files?

## Custom IO Streams in Python

Python allows to you create custom IO streams by extending the [`RawIOBase`](https://docs.python.org/3/library/io.html#io.RawIOBase) class. Admittedly, this is not an entirely straightforward process, nor is it well documented in the Python reference documentation. I'll give credit to [univerio](https://stackoverflow.com/users/341730/univerio) on [Stack Overflow for pointing me in the right direction on this](https://stackoverflow.com/a/47603741/830030).

Let's start out with a generic readable stream class to demonstrate the concept. This `CustomReadStream` class will read out an arbitrary string (`"iteration 1, iteration 2, ..."`), via a generator. Later, we'll modify this generator to iterate over actual database query results.

```python
class CustomReadStream(io.RawIOBase):

    def __init__(self):
        super().__init__()

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

        # Extract a chunk of data of the requested size from our buffer
        chunk = self._buffer[:size]
        self._buffer = self._buffer[size:]

        return chunk

    def _iterate(self) -> Iterator[bytes]:
        """
        This method will `yield` whatever data
        we want our read stream to provide.

        Later, we will modify this method
        to read from a postgres database.
        """
        for n in range(0, 100):
            yield f"iteration {n}, ".encode('utf8')

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
```

In implementing the `io.RawIOBase` class, we have created a ["file-like" object](https://docs.python.org/3/glossary.html#term-file-object). This allows us to stream data from `CustomReadStream` objects in the same way that we'd stream data from a file:

```python
read_io = CustomReadStream()
write_io = open('dst.txt', 'wb')

for chunk in read_io:
    # Write to the dst.txt file
    write_io.write(chunk)

# Close the IO objects
read_io.close()
write_io.close()
```

This gives us a `dst.txt` file that looks like:

```
iteration 0, iteration 1, iteration 2, iteration 3,...
```


Note that we can also pass a `size` argument to the `CustomReadStream#read()` method, to control this size of the "chunk" to read from the stream:

```python
read_io = CustomReadStream()
write_io = open('dst.txt', 'wb')
while True:
    # Only read 3 bytes at a time
    chunk = read_io.read(3)
    if not chunk:
        break

    # Split up the chunks by "|", so we can visualize the chunking behavior
    write_io.write(b'|')
    write_io.write(chunk)

read_io.close()
write_io.close()
```

Resulting in a `dst.txt` file that looks like:

```
|ite|rat|ion| 0,| it|era|tio|n 1|, i|ter|ati|on |2, |ite|rat|ion| 3,....
```

We now have fine-grained control -- to the byte -- over the amount of data we're keeping in memory for any give iteration.


## Streaming from a Postgres Database

Now that we have a handle on how to implement a custom readable stream in Python, we can modify our `CustomReadStream` class to read from a postgres database, instead of returning an arbitrary test string. We'll just need to reimplement the `_iterate` method to yield database records:

```python
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
```

You can see [the entire class implementation here](https://github.com/eschwartz/eschwartz.github.io/blob/master/assets/posts/2018-11-29-python-stream-postgres-to-s3/db_read_stream.py)

We can now read from the the database, using the same streaming interface we would use for reading from a file.

```python
# Create the DB read stream,
# and configure to execute a query
db_read_stream = DbReadStream(
    db=create_engine('postgres://postgres@localhost:5432'),
    query="SELECT * FROM test_record",
)

# Write results to a file
write_io = open('dst.csv', 'wb')

# Iterate through the DB records, and write to a file
while True:
    # Read 1 MB at a time
    chunk = db_read_stream.read(1024 * 1024)
    if not chunk:
        break

    write_io.write(chunk)

# Cleanup
db_read_stream.close()
write_io.close()
```


## Streaming Data to S3

We can stream data to AWS S3 file storage by using the [Multipart Upload API for S3](https://docs.aws.amazon.com/AmazonS3/latest/dev/uploadobjusingmpu.html). This API is somewhat complex -- luckily someone has already done the heavy lifting for us: the [`smart_open`](https://github.com/RaRe-Technologies/smart_open) library provides a streaming interface for reading and writing to S3.

As `smart_open` implements a file-like interface for streaming data, we can easily swap it out for our writable file stream:

```python
# Create the DB read stream,
# and configure to execute a query
db_read_stream = DbReadStream(
    db=create_engine('postgres://postgres@localhost:5432'),
    query="SELECT * FROM test_record",
)

# Open a writable stream on S3
write_io = smart_open('s3://my-s3-bucket/db.csv', 'wb')

# Iterate through the DB records, and write to the file on S3
while True:
    # Read 1 MB at a time
    chunk = db_read_stream.read(1024 * 1024)
    if not chunk:
        break

    write_io.write(chunk)

# Cleanup
db_read_stream.close()
write_io.close()
```

Looks pretty familiar, eh?

## Measuring Memory Usage

The core idea here is that we've limited our memory footprint by breaking up our data transfers and transformations into small chunks. But did it really work?

To test it out, we can use the [`memory_profiler`](https://pypi.org/project/memory_profiler/) package, and compare the behavior of a a streaming operation to an in-memory operation.

In this scenario, I've loaded a local postgres database instance with around 3 million records, which results in a 23.3 MB CSV file. In our first attempt, we'll load the entire table into memory, convert it to a CSV string (in memory), and write the string to a file on S3. You can [see the actual code here](https://github.com/eschwartz/eschwartz.github.io/blob/master/assets/posts/2018-11-29-python-stream-postgres-to-s3/profile_in_memory), but here are the profiler results:

```
Complete in 37.11s
Filename: profile_in_memory.py

Line #    Mem usage    Increment   Line Contents
================================================
     9     50.2 MiB     50.2 MiB   @profile
    10                             def main():
    11     50.2 MiB      0.0 MiB       start_time = perf_counter()
    12
    13     52.2 MiB      2.0 MiB       db: Connection = create_engine('postgres://postgres@localhost:5432')
    14
    15                                 # Load all DB records into memory
    16     52.2 MiB      0.0 MiB       results = db \
    17    350.7 MiB    298.5 MiB           .execute("SELECT * FROM test_record") \
    18                                     .fetchall()
    19
    20                                 # Convert DB records to CSV
    21    350.7 MiB      0.0 MiB       csv_buffer = io.StringIO("")
    22    350.7 MiB      0.0 MiB       csv_writer = csv.writer(csv_buffer, lineterminator='\n')
    23    370.4 MiB     19.7 MiB       csv_writer.writerows(results)
    24
    25                                 # Upload the CSV to S3
    26    375.1 MiB      4.7 MiB       s3 = boto3.client('s3')
    27    375.1 MiB      0.0 MiB       s3.put_object(
    28    375.1 MiB      0.0 MiB           Bucket='my-s3-bucket',
    29    375.1 MiB      0.0 MiB           Key='db.csv',
    30    425.2 MiB     50.1 MiB           Body=csv_buffer.getvalue().encode('utf8')
    31                                 )
    32
    33    425.2 MiB      0.0 MiB       duration = perf_counter() - start_time
    34    425.2 MiB      0.0 MiB       print(f"Complete in {round(duration, 2)}s")
```

You can see our memory usage topped out at around 425 MB, with the bulk of that going towards loading the DB records into in-memory Python objects. But it also includes the entire content of our CSV file loaded into memory.

Now, [using our streaming interface](https://github.com/eschwartz/eschwartz.github.io/blob/master/assets/posts/2018-11-29-python-stream-postgres-to-s3/profile_streaming.py):

```
Complete in 46.77s
Filename: profile_streaming.py

Line #    Mem usage    Increment   Line Contents
================================================
     8     79.8 MiB     79.8 MiB   @profile
     9                             def main():
    10     79.8 MiB      0.0 MiB       start_time = perf_counter()
    11
    12                                 # Create the DB read stream,
    13                                 # and configure to execute a large query
    14     79.8 MiB      0.0 MiB       db_read_stream = DbReadStream(
    15     79.8 MiB      0.0 MiB           db=create_engine('postgres://postgres@localhost:5432'),
    16     79.8 MiB      0.0 MiB           query="SELECT * FROM test_record",
    17                            ´     )
    18
    19                                 # Create S3 write stream
    20     82.4 MiB      2.6 MiB       s3_write_stream = smart_open('s3://my-s3-bucket/db.csv', 'wb')
    21
    22                                 # Iterate through the DB records, and write to S3
    23     82.4 MiB      0.0 MiB       while True:
    24                                     # Read 1 MB at a time
    25    107.1 MiB     -5.3 MiB           chunk = db_read_stream.read(1024 * 1024)
    26    107.1 MiB    -10.7 MiB           if not chunk:
    27    106.9 MiB     -0.2 MiB               break
    28
    29    107.4 MiB     11.0 MiB           s3_write_stream.write(chunk)
    30
    31                                 # Close the stream
    32    106.9 MiB      0.0 MiB       db_read_stream.close()
    33     84.9 MiB    -22.0 MiB       s3_write_stream.close()
    34
    35     84.9 MiB      0.0 MiB       duration = perf_counter() - start_time
    36     84.9 MiB      0.0 MiB       print(f"Complete in {round(duration, 2)}s")
```

Here we topped out at only 107 MB, with most of that going to the memory profiler itself.


## Conclusions

Implementing streaming interfaces can be a powerful tool for limiting your memory footprint. Admittedly, this introduces some code complexity, but if you're dealing with very large data sets (or very small machines, like an AWS Lambda instance), streaming your data in small chunks may be a necessity. And abstracting data sources behind `IO` implementations allows you to use a consistent interface across many different providers -- just look how `smart_open` allows you to work with S3, HDFS, WebHDFS, HTTP, and local files all using the same method signature.

For me personally, this was a great way to learn about how IO objects work in Python. I've recently transitioned to using Python after several years in the Node.js world. I will say using custom streams in Python does not seem to be _The Python Way™_:

 - There's no documentation for custom streams,
 - Streams may only use strings/bytes (ie, you can't stream a list of dictionary objects),
 - There's no concept of "Transform" streams or "piping" multiple streams together.

Compare this to Node.js which provides [simple and well-documented interfaces for implementing customs stream](https://nodejs.org/api/stream.html#stream_simplified_construction).

The result is a concept of streaming that is less powerful in Python that it is in other languages.

In retrospect, a simple generator to iterate through database results would probably be a simpler and more idiomatic solution in Python.


