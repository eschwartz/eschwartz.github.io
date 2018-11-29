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
