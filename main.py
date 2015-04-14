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

#Hello world -style editing of color bytes
def editColorBytes(chunkData, dimensions, colorAdj = 0):
    width = dimensions[0]
    height = dimensions[1]
    newChunk = ""
    chunkData = zlib.decompress(chunkData)
    oldLen = len(chunkData)
    print "Old data length:", oldLen
    chunkData = StringIO.StringIO(chunkData)
    #chunkData is a string. Each byte containg either R, B or G value
    for i in range(height):
      newRow = chunkData.read(width*3+1)
      print "Row %d Filter: %d" % (i, struct.unpack("B", newRow[0])[0])
    """
    i = 0
    for colorVal in chunkData:
      if (i % 3) == 2:
        oldVal = struct.unpack("B", colorVal)
        newVal = oldVal[0] + colorAdj
        #newVal = colorVal + struct.pack("B", colorAdj)
        if newVal > 255:
          newVal = 255
        newColor = struct.pack("B", newVal)
        newChunk += newColor
      else:
        newChunk += colorVal
      i += 1
    """
    newLen = len(newChunk)
    print "New data length:", newLen
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
      chunkData = editColorBytes(chunkData, dim)      
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
