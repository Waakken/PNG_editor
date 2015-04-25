import math
import pdb
import struct
import zlib
import datetime
import StringIO
import logging as log

class PngEdit():

  def __init__(self, debug = False, info = False):
    self.width = 0
    self.height = 0

    self.FILTER_MODE = 0
    self.RECON_MODE = 1
    self.EDIT_MODE = 2
    self.CHUNK_MODE = 3
    self.SIMPLE_MODE = 4
    self.HDR_MODE = 5
    self.BYTES_MODE = 6

    self.redAdj = 0
    self.blueAdj = 0
    self.greenAdj = 0

    #Format = "%(levelname)s: %(message)s"
    Format = "%(message)s"

    if debug:
      log.basicConfig(format = Format, level=log.DEBUG)
    elif info:
      log.basicConfig(format = Format, level=log.INFO)
    else:
      log.basicConfig(format = Format, level=log.WARNING)

  # Return matching mode as printable string
  def printMode(self, mode_nr):
    return {
      0 : "Filter Mode",
      1 : "Recon Mode",
      2 : "Edit Mode",
      3 : "Chunk Mode",
      4 : "Simple Mode",
      5 : "Header Mode",
      6 : "Bytes Mode",
    }[mode_nr]

  #Check that first 8 byte of the file match the official PNG header:
  def checkHeader(self, hdr, writeToFile = None):
    corrHeader = (137, 80, 78, 71, 13, 10, 26, 10)
    headerBytes = struct.unpack("8B", hdr)
    if headerBytes == corrHeader:
      if writeToFile:
        log.debug("Writing header to file")
        writeToFile.write(bytearray(headerBytes))
      return True
    else:
      return False
  
  #Convert 4 bytes to a unsigned integer
  def convertToInt(self, lengthBytes):
    length = struct.unpack("!I", lengthBytes)[0]
    return length
  
  #Print information contained in IHDR chunk.
  #No error is raised if any of the bytes is invalid
  def printIHDR(self, header):
    log.info("Image information")
    self.width = struct.unpack("!I", header[0:4])[0]
    log.info("Width %d" % self.width)
    self.height = struct.unpack("!I", header[4:8])[0]
    log.info("Height %d" % self.height)
  
    #Combination of bit depth and color type determine how many bytes each pixel contains
    #Bit depth should be one of these: 1, 2, 4, 8 or 16
    bitDepth = struct.unpack("!B", header[8])[0]
    log.info("Bit depth %d" % bitDepth)
    #Color type should be one of these: 0, 2, 3, 4, 6
    colorType = struct.unpack("!B", header[9])[0]
    log.info("Color type %d" % colorType)
  
    #Compression method should be 0
    compressionMethod = struct.unpack("!B", header[10])[0]
    log.info("Compression method %d" % compressionMethod)
    #Filter method should be 0
    filterMethod = struct.unpack("!B", header[11])[0]
    log.info("Filter method %d" % filterMethod)
    #Interlace method should be 0 or 1
    interLaceMethod = struct.unpack("!B", header[12])[0]
    log.info("Interlace method %d" % interLaceMethod)
  
    if (bitDepth != 8) or (colorType != 2):
      # Don't remove this warning unless correct support has been enabled
      raise Warning("Only bit depth 8 and color type 2 are supported")
    return
  
  # http://stackoverflow.com/questions/4612136/how-to-set-parameters-in-python-zlib-module
  def write_chunk(self, outfile, chunkType, data=''):
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
  def paeth(self, a, b, c):
      """Simple implementation of http://www.w3.org/TR/PNG/#9Filter-type-4-Paeth
      (nearly c/p the pseudo-code)
      """
      p = a + b - c
      pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
  
      if pa <= pb and pa <= pc:
          return a
      elif pb <= pc:
          return b
      return c
  
  # Reconstruct one Sub filtered scanline
  def reconSub(self, curRow, lastRow):
    # Recon(x) = Filt(x) + Recon(a)
    newRow = bytearray()
    curRow = bytearray(curRow)
    for i in range(0, (self.width*3)):
      if i < 3:
        a = 0
      else:
        a = newRow[i-3]
      x = curRow[i]
      newX = (a + x)
      if newX > 255:
        newX = newX % 256
      newRow.append(newX)
    newRow = str(newRow)
    return newRow
  
  # Reconstruct one Up filtered scanline
  def reconUp(self, curRow, lastRow):
    # Recon(x) = Filt(x) + Recon(b)
    newRow = bytearray()
    curRow = bytearray(curRow)
    lastRow = bytearray(lastRow)
    for i in range(0, (self.width*3)):
      b = lastRow[i]
      x = curRow[i]
      recX = (x + b)
      if recX > 255:
        recX = recX % 256
      newRow.append(recX)
    newRow = str(newRow)
    return newRow
  
  # Reconstruct one Avg filtered scanline
  def reconAvg(self, curRow, lastRow):
    # Recon(x) = Filt(x) + floor((Recon(a) + Recon(b)) / 2)
    newRow = bytearray()
    curRow = bytearray(curRow)
    lastRow = bytearray(lastRow)
    for i in range(0, (self.width*3)):
      if i < 3:
        a = 0
      else:
        a = newRow[i-3] 
      b = lastRow[i]
      floor = int(math.floor((a + b) / 2))
      recX = curRow[i] + floor
      if recX > 255:
        recX = recX % 256
      newRow.append(recX)
    newRow = str(newRow)
    return newRow

  # Reconstruct one Paeth filtered scanline
  def reconPaeth(self, curRow, lastRow):
    # Recon(x) = Filt(x) + PaethPredictor(Recon(a), Recon(b), Recon(c))
    newRow = bytearray()
    curRow = bytearray(curRow)
    lastRow = bytearray(lastRow)
    for i in range(0, (self.width*3)):
     
      if i < 3:
        a = 0
        c = 0
      else:
        a = newRow[i-3]
        c = lastRow[i-3]
      b = lastRow[i]
      x = curRow[i]

      recX = x + self.paeth(a, b, c)
      if recX > 255:
        recX = recX % 256
      newRow.append(recX)
  
    newRow = str(newRow)
    return newRow
  
  
  #Remove filtering from each line
  def reconData(self, chunkData):
      dt = datetime.datetime.now()
      startTime = dt.now()
      print "Decompressing image data.."
      newChunk = ""
      lastRow = [0] * (self.width * 3)
      chunkData = zlib.decompress(chunkData)
      oldLen = len(chunkData)
      chunkData = StringIO.StringIO(chunkData)
      print "  ..lasted %f seconds" % (dt.now() - startTime).total_seconds()
      startTime = dt.now()
      #chunkData is a string. Each byte containg either R, B or G value
      print "Reconstructing filtered data.."
      for i in range(self.height):
        newFilter = chunkData.read(1)
        newRow = chunkData.read(self.width*3)
        oldRowLen = len(newRow)
        #print "Debug: Row %d Filter: %d" % (i, struct.unpack("B", newFilter[0])[0])
        if newFilter == b'\x00':
          pass
        elif newFilter == b'\x01':
          newRow = self.reconSub(newRow, lastRow)
        elif newFilter == b'\x02':
          newRow = self.reconUp(newRow, lastRow)
        elif newFilter == b'\x03':
          newRow = self.reconAvg(newRow, lastRow)
        elif newFilter == b'\x04':
          newRow = self.reconPaeth(newRow, lastRow)
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
      print "  ..lasted %f seconds" % (dt.now() - startTime).total_seconds()
      startTime = dt.now()
      print "Compressing image data.."
      readyData = zlib.compress(newChunk)
      print "  ..lasted %f seconds" % (dt.now() - startTime).total_seconds()
      return readyData
  
  #Edit color values of a single non-filtered line
  def editLine(self, line):
    redAdj = self.redAdj
    blueAdj = self.blueAdj
    greenAdj = self.greenAdj
    #pdb.set_trace()
    line = bytearray(line)
    i = 0
    newLine = bytearray()
    for byte in line:
      if i % 3 == 0:
        newByte = byte + redAdj
        if newByte > 255:
          newByte = 255
        elif newByte < 0:
          newByte = 0
        newLine.append(newByte)
      if i % 3 == 1:
        newByte = byte + blueAdj
        if newByte > 255:
          newByte = 255
        elif newByte < 0:
          newByte = 0
        newLine.append(newByte)
      if i % 3 == 2:
        newByte = byte + greenAdj
        if newByte > 255:
          newByte = 255
        elif newByte < 0:
          newByte = 0
        newLine.append(newByte)
      i += 1
    #newLine = struct.pack("%sB" % len(fixedLine), *fixedLine)
    newLine = str(newLine)
    return newLine
  
  
  #Remove filtering from each line
  def editColors(self, chunkData):
      dt = datetime.datetime.now()
      startTime = dt.now()
      print "Decompressing image data.."
      newChunk = ""
      chunkData = zlib.decompress(chunkData)
      oldLen = len(chunkData)
      chunkData = StringIO.StringIO(chunkData)
      print "  ..lasted %f seconds" % (dt.now() - startTime).total_seconds()
      startTime = dt.now()
      #chunkData is a string. Each byte containg either R, B or G value
      print "Editing pixels.."
      for i in range(self.height):
        newFilter = chunkData.read(1)
        newRow = chunkData.read(self.width*3)
        oldRowLen = len(newRow)
        if newFilter == b'\x00':
          newRow = self.editLine(newRow)
        else:
          raise Warning("Unaccepted filter. Only 0 is accepted")
        newRowLen = len(newRow)
        if newRowLen != oldRowLen:
          print "Ending length of row:", newRowLen
          print "Debug: Starting length of row:", oldRowLen
          print "Debug: Row %d Filter: %d" % (i, struct.unpack("B", newFilter[0])[0])
          raise Warning("Reconstruct didn't provide correct amount of bytes")
        # Set filter of each line to 0
        newChunk += struct.pack("B", 0)
        newChunk += newRow
      newLen = len(newChunk)
      if newRowLen != oldRowLen:
        print "Debug: Old data length:", oldLen
        print "Debug: New data length:", newLen
        raise Warning("Reconstructed data doesn't contain correct amount of bytes")
      print "  ..lasted %f seconds" % (dt.now() - startTime).total_seconds()
      startTime = dt.now()
      print "Compressing image data.."
      readyData = zlib.compress(newChunk)
      print "  ..lasted %f seconds" % (dt.now() - startTime).total_seconds()
      return readyData
  
  def printFilterInfo(self, chunkData):
      dt = datetime.datetime.now()
      startTime = dt.now()
      #print "Decompressing image data.."
      filterInfo = [0] * 5
      chunkData = zlib.decompress(chunkData)
      chunkData = StringIO.StringIO(chunkData)
      #print "  ..lasted %f seconds" % (dt.now() - startTime).total_seconds()
      startTime = dt.now()
      #chunkData is a string. Each byte containg either R, B or G value
      #print "Reading filter byte from each scanline.."
      for i in range(self.height):
        newFilter = chunkData.read(1)
        newRow = chunkData.read(self.width*3)
        oldRowLen = len(newRow)
        #print "Debug: Row %d Filter: %d" % (i, struct.unpack("B", newFilter[0])[0])
        if newFilter == b'\x00':
          filterInfo[0] += 1
        elif newFilter == b'\x01':
          filterInfo[1] += 1
        elif newFilter == b'\x02':
          filterInfo[2] += 1
        elif newFilter == b'\x03':
          filterInfo[3] += 1
        elif newFilter == b'\x04':
          filterInfo[4] += 1
        else:
          raise Warning("Bad filter code")
        newRowLen = len(newRow)
        if newRowLen != oldRowLen:
          print "Ending length of row:", newRowLen
          print "Debug: Starting length of row:", oldRowLen
          print "Debug: Row %d Filter: %d" % (i, struct.unpack("B", newFilter[0])[0])
          raise Warning("Reconstruct didn't provide correct amount of bytes")
      #print "  ..lasted %f seconds" % (dt.now() - startTime).total_seconds()
      print "Filter information:"
      print "Filter 0 (None) Used %d times in %d scanlines" % (filterInfo[0], self.height)
      print "Filter 1 (Sub) Used %d times in %d scanlines" % (filterInfo[1], self.height)
      print "Filter 2 (Up) Used %d times in %d scanlines" % (filterInfo[2], self.height)
      print "Filter 3 (Avg) Used %d times in %d scanlines" % (filterInfo[3], self.height)
      print "Filter 4 (Paeth) Used %d times in %d scanlines" % (filterInfo[4], self.height)
  
  #Do some changes to image and save it as newFilename
  def readChunks(self, filename, bytesLine = 0, writeToFile = None, opMode = 0):
    log.debug("Operating mode: %s" % self.printMode(opMode))
    readFp = open(filename, "r")
    header = readFp.read(8)
    newData = ""
    chunkLenSum = 0
    dataChunkCount = 0
    if writeToFile:
      writeFp = open(writeToFile, "wb")
      retVal = self.checkHeader(header, writeToFile = writeFp)
    else:
      retVal = self.checkHeader(header)
    if retVal:
      log.debug("Header ok")
    else:
      raise Warning("Header is not correct PNG-header")
    while True:
      #Read 4-byte data length:
      lenBytes = readFp.read(4)
      #Break if there are no more chunks to read:
      if len(lenBytes) < 4:
        log.debug("All bytes read from file")
        break
      log.debug("Reading new chunk from PNG file %s" % filename)
      length = self.convertToInt(lenBytes)
      log.debug("Chunk length: %d bytes" % length)
      #Read 4-byte chunk type:
      chunkType = readFp.read(4)
      log.debug("Chunk type %s" % chunkType)
      #Read chunk data:
      chunkData = readFp.read(length)
      #Read chunk CRC:
      chunkCRCBytes = readFp.read(4)
      chunkCRC = self.convertToInt(chunkCRCBytes)
      #Calculate CRC of data:
      zlibCRC = zlib.crc32(chunkType)
      zlibCRC = zlib.crc32(chunkData, zlibCRC)
      if (zlibCRC & 0xffffffff) == chunkCRC:
        log.debug("CRC passed")
      else:
        print "CRC sum:", chunkCRC
        print "CRC (Python zlib):", (zlibCRC & 0xffffffff)
        raise Warning("CRC failed")

      if chunkType == "IHDR":
        self.printIHDR(chunkData)
        if opMode == self.HDR_MODE:
          break
        elif writeToFile:
          log.info("Writing chunk %s to file %s" % (chunkType, writeToFile))
          self.write_chunk(writeFp, chunkType, chunkData)

      elif chunkType == "IDAT":
        dataChunkCount += 1
        newData += chunkData
        chunkLenSum += length
        #Print filter info
        if opMode == self.FILTER_MODE:
          self.printFilterInfo(chunkData)      
        #Reconstruct data and save to new image
        elif opMode == self.RECON_MODE:
          newData = self.reconData(chunkData)
        #Edit color bytes and save to new image
        elif opMode == self.EDIT_MODE:
          newData = self.editColors(chunkData)      
        #Just read the chunks
        elif opMode == self.CHUNK_MODE:
          pass
        # Chunk was added to newData
        elif opMode == self.SIMPLE_MODE:
          pass
        # Print color bytes of the desired scanline
        elif opMode == self.BYTES_MODE:
          chunkData = zlib.decompress(chunkData)
          #pdb.set_trace()
          filtByte = ((self.width * 3) + 1) * bytesLine
          startByte = (((self.width * 3) + 1) * bytesLine) + 1
          endByte = startByte + (self.width * 3)
          print "Filter byte of line %d:" % bytesLine
          print "%d" % struct.unpack("B", chunkData[filtByte])[0]
          print "Color bytes of line %d:" % bytesLine
          chunkData = struct.unpack("%sB" % (self.width*3), chunkData[startByte:endByte])
          print "", chunkData
          break

      elif chunkType == "IEND":
        if writeToFile:
          log.info("Total calculated bytes in chunks: %d" % chunkLenSum)
          log.info("Total calculated bytes in new chunk: %d" % len(newData))
          log.info("Total data chunks in file: %d" % dataChunkCount)
          log.info("Writing chunk IDAT to file %s" % writeToFile)
          self.write_chunk(writeFp, "IDAT", newData)
          log.info("Writing chunk %s to file %s" % (chunkType, writeToFile))
          self.write_chunk(writeFp, chunkType, chunkData)
          print "New file created:", writeToFile
        elif opMode == self.CHUNK_MODE:
          log.info("Total calculated bytes in chunks: %d" % chunkLenSum)
          log.info("Total calculated bytes in new chunk: %d" % len(newData))
          log.info("Total data chunks in old file: %d new file: 1" % dataChunkCount)

    readFp.close()
    if writeToFile:
      writeFp.close()
  
