import io
from typing import Iterator


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


# We can use our read stream just like we'd
# used our FileIO readable streams, to read and write data.
read_io = CustomReadStream()
write_io = open('dst.txt', 'wb')

for chunk in read_io:
    # Write to the dst.txt file
    write_io.write(chunk)

# Close the IO objects
read_io.close()
write_io.close()

# We can also limit the amount of data held in memory
# at any given point, by passing a `size` argument to read:
read_io = CustomReadStream()
write_io = open('dst-chunked.txt', 'wb')
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
