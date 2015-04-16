#!/usr/bin/env python

import struct
import zlib
import os
import StringIO

#Check that first 8 byte of the file match the official PNG header:
def checkHeader(hdr, writeToFile = None):
  corrHeader = (137, 80, 78, 71, 13, 10, 26, 10)
  headerBytes = struct.unpack("8B", hdr)
  print 
  if headerBytes == corrHeader:
    if writeToFile:
      print "Writing header to file"
      writeToFile.write(bytearray(headerBytes))
    return True
  else:
    return False

#Convert 4 bytes to a unsigned integer
def convertToInt(lengthBytes):
  length = struct.unpack("!I", lengthBytes)[0]
  return length

#Print information contained in IHDR chunk.
#No error is raised if any of the bytes is in valid
def printIHDR(header):
  print "Image information"
  width = struct.unpack("!I", header[0:4])
  print "Width", width[0]
  height = struct.unpack("!I", header[4:8])
  print "Height", height[0]

  #Combination of bit depth and color type determine how many bytes each pixel contains
  #Bit depth should be one of these: 1, 2, 4, 8 or 16
  bitDepth = struct.unpack("!B", header[8])
  print "Bit depth", bitDepth[0]
  #Color type should be one of these: 0, 2, 3, 4, 6
  colorType = struct.unpack("!B", header[9])
  print "Color type", colorType[0]

  #Compression method should be 0
  compressionMethod = struct.unpack("!B", header[10])
  print "Compression method", compressionMethod[0]
  #Filter method should be 0
  filterMethod = struct.unpack("!B", header[11])
  print "Filter method", filterMethod[0]
  #Interlace method should be 0 or 1
  interLaceMethod = struct.unpack("!B", header[12])
  print "Interlace method", interLaceMethod[0]
  print "End of image information"
  return [width[0], height[0]]

# http://stackoverflow.com/questions/4612136/how-to-set-parameters-in-python-zlib-module
def write_chunk(outfile, chunkType, data=''):
    """
    Write a PNG chunk to the output file, including length and
    checksum.
    """
    # http://www.w3.org/TR/PNG/#5Chunk-layout
    outfile.write(struct.pack("!I", len(data)))
    outfile.write(chunkType)
    outfile.write(data)
    checksum = zlib.crc32(chunkType)
    checksum = zlib.crc32(data, checksum)
    outfile.write(struct.pack("!i", checksum))

# https://github.com/Alexis-D/png.py/blob/master/png.py
def paeth(a, b, c):
    """Simple implementation of http://www.w3.org/TR/PNG/#9Filter-type-4-Paeth
    (nearly c/p the pseudo-code)
    """
    try:
      a = struct.unpack("B", a)[0]
    except struct.error:
      a = 0
    try:
      b = struct.unpack("B", b)[0]
    except struct.error:
      b = 0
    try:
      c = struct.unpack("B", c)[0]
    except struct.error:
      c = 0
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)

    if pa <= pb and pa <= pc:
        return struct.pack("B", a)
    elif pb <= pc:
        return struct.pack("B", b)
    return struct.pack("B", c)

# Reconstruct one Paeth filtered scanline
def reconstructPaeth(curRow, lastRow, width):
  # Recon(x) = Filt(x) + PaethPredictor(Recon(a), Recon(b), Recon(c))
  newRow = ""
  newRow += curRow[0]
  newRow += curRow[1]
  newRow += curRow[2]
  #newRow += b'\x00'
  for i in range(3, (width*3)):
   
    filtX = curRow[i]

    try:
      reconA = struct.unpack("B", curRow[i-3])[0]
    except struct.error:
      reconA = 0

    try:
      reconB = struct.unpack("B", lastRow[i])[0]
    except struct.error:
      reconB = 0

    try:
      reconC = struct.unpack("B", lastRow[i-3])[0]
    except struct.error:
      reconA = 0

    reconX = struct.unpack("B", filtX)[0] + struct.unpack("B", paeth(reconA, reconB, reconC))[0]
    newRow += struct.pack("B", reconX)

  return newRow

# Reconstruct one Sub filtered scanline
def reconstructSub(curRow, lastRow, width):
  # Recon(x) = Filt(x) + Recon(a)
  newRow = ""
  #newRow += b'\x00'
  newRow += curRow[0]
  newRow += curRow[1]
  newRow += curRow[2]
  for i in range(3, (width*3)):
    try:
      x = struct.unpack("B", curRow[i])[0]
    except struct.error:
      x = 0
    try:
      a = struct.unpack("B", newRow[i-3])[0]
    except struct.error:
      a = 0
    newX = (a + x)
    if newX > 255:
      newX = newX % 256
    newRow += struct.pack("B", newX)
    #newRow[i] = curRow[i] + curRow[i-1]
  return newRow

# Reconstruct one Avg filtered scanline
def reconstructAvg(curRow, lastRow, width):
  # Recon(x) = Filt(x) + floor((Recon(a) + Recon(b)) / 2)
  newRow = ""
  newRow += curRow[0]
  newRow += curRow[1]
  newRow += curRow[2]
  for i in range(3, (width*3)):
    try:
      a = struct.unpack("B", curRow[i-3])[0]
    except struct.error:
      a = 0
    try:
      b = struct.unpack("B", lastRow[i])[0]
    except struct.error:
      b = 0
    x = round( (a + b) / 2)
    newRow += struct.pack("B", x)
    #newRow[i] = curRow[i] + curRow[i-1]
  return newRow

#Remove filtering from each line
def reconstData(chunkData, dimensions, colorAdj = 0):
    print "Reconstructing filtered data.."
    width = dimensions[0]
    height = dimensions[1]
    newChunk = ""
    lastRow = [0] * width
    chunkData = zlib.decompress(chunkData)
    oldLen = len(chunkData)
    chunkData = StringIO.StringIO(chunkData)
    #chunkData is a string. Each byte containg either R, B or G value
    for i in range(height):
      newFilter = chunkData.read(1)
      newRow = chunkData.read(width*3)
      oldRowLen = len(newRow)
      #print "Debug: Row %d Filter: %d" % (i, struct.unpack("B", newFilter[0])[0])
      if newFilter == b'\x00':
        raise Warning("None filter is not implemented")
      elif newFilter == b'\x01':
        newRow = reconstructSub(newRow, lastRow, width)
      elif newFilter == b'\x02':
        raise Warning("Up filter is not implemented")
      elif newFilter == b'\x03':
        newRow = reconstructAvg(newRow, lastRow, width)
      elif newFilter == b'\x04':
        newRow = reconstructPaeth(newRow, lastRow, width)
      else:
        raise Warning("Bad filter code")
      newRowLen = len(newRow)
      if newRowLen != oldRowLen:
        print "Ending length of row:", newRowLen
        print "Debug: Starting length of row:", oldRowLen
        print "Debug: Row %d Filter: %d" % (i, struct.unpack("B", newFilter[0])[0])
        raise Warning("Reconstruct didn't provide correct amount of bytes")
      # Set filter of each line to 0
      newChunk += struct.pack("B", 0)
      newChunk += newRow
      lastRow = newRow
    newLen = len(newChunk)
    if newRowLen != oldRowLen:
      print "Debug: Old data length:", oldLen
      print "Debug: New data length:", newLen
      raise Warning("Reconstructed data doesn't contain correct amount of bytes")
    readyData = zlib.compress(newChunk)
    return readyData

#Do some changes to image and save it as newFilename
def editImageFile(filename, newFilename):
  fp = open(filename, "r")
  new_fp = open(newFilename, "wb")
  header = fp.read(8)
  if checkHeader(header, writeToFile = new_fp):
    print "Header ok"
  else:
    raise Warning("Header is not correct PNG-header")
  print ""
  while True:
    #Read 4-byte data length:
    lenBytes = fp.read(4)
    #Break if there are no more chunks to read:
    if len(lenBytes) < 4:
      print "No more chunks to read"
      break
    print "Reading new chunk from PNG file", filename
    length = convertToInt(lenBytes)
    print "Chunk length: %d bytes" % length
    #Read 4-byte chunk type:
    chunkType = fp.read(4)
    print "Chunk type", chunkType
    #Read chunk data:
    chunkData = fp.read(length)
    #Read chunk CRC:
    chunkCRCBytes = fp.read(4)
    chunkCRC = convertToInt(chunkCRCBytes)
    #Calculate CRC of data:
    zlibCRC = zlib.crc32(chunkType)
    zlibCRC = zlib.crc32(chunkData, zlibCRC)
    if (zlibCRC & 0xffffffff) == chunkCRC:
      print "CRC passed"
    else:
      print "CRC sum:", chunkCRC
      print "CRC (Python zlib):", (zlibCRC & 0xffffffff)
      raise Warning("CRC failed")
    if chunkType == "IHDR":
      dim = printIHDR(chunkData)
    elif chunkType == "IDAT":
      chunkData = reconstData(chunkData, dim)      
    print "Writing chunk to file", newFilename
    print ""
    write_chunk(new_fp, chunkType, chunkData)
  fp.close()
  new_fp.close()

def main():
  newImgFile = "newImage.png"
  imgFile = "image.png"
  try:
    os.unlink(newImgFile)
  except OSError:
    pass
  editImageFile(imgFile, newImgFile)

if __name__ == "__main__":
  main()
