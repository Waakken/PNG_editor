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
    self.HDR_MODE = 5

    if debug:
      log.basicConfig(level=log.DEBUG)
    elif info:
      log.basicConfig(level=log.INFO)
    else:
      log.basicConfig(level=log.WARNING)
    log.basicConfig(format="%(levelname)s: %(message)s")

  #Check that first 8 byte of the file match the official PNG header:
  def checkHeader(self, hdr, writeToFile = None):
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
    log.info("End of image information")
  
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
  def reconPaeth(self, curRow, lastRow):
    # Recon(x) = Filt(x) + PaethPredictor(Recon(a), Recon(b), Recon(c))
    newRow = ""
    newRow += curRow[0]
    newRow += curRow[1]
    newRow += curRow[2]
    #newRow += b'\x00'
    for i in range(3, (self.width*3)):
     
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
  def reconSub(self, curRow, lastRow):
    # Recon(x) = Filt(x) + Recon(a)
    newRow = ""
    #newRow += b'\x00'
    newRow += curRow[0]
    newRow += curRow[1]
    newRow += curRow[2]
    for i in range(3, (self.width*3)):
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
  def reconAvg(self, curRow, lastRow):
    # Recon(x) = Filt(x) + floor((Recon(a) + Recon(b)) / 2)
    newRow = ""
    newRow += curRow[0]
    newRow += curRow[1]
    newRow += curRow[2]
    for i in range(3, (self.width*3)):
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
  def reconstData(self, chunkData):
      dt = datetime.datetime.now()
      startTime = dt.now()
      print "Decompressing image data.."
      newChunk = ""
      lastRow = [0] * self.width
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
          raise Warning("None filter is not implemented")
        elif newFilter == b'\x01':
          newRow = reconSub(newRow, lastRow)
        elif newFilter == b'\x02':
          raise Warning("Up filter is not implemented")
        elif newFilter == b'\x03':
          newRow = reconAvg(newRow, lastRow)
        elif newFilter == b'\x04':
          newRow = reconPaeth(newRow, lastRow)
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
  def editLine(self, line, redAdj = 0, blueAdj = 0, greenAdj = 0):
    line = bytearray(line)
    i = 0
    newLine = []
    fixedLine = []
    for byte in line:
      if i % 3 == 0:
        newLine.append(byte + redAdj)
      elif i % 3 == 1:
        newLine.append(byte + greenAdj)
      elif i % 3 == 2:
        newLine.append(byte + blueAdj)
      i += 1
    for byte in newLine:
      if byte > 255:
        byte = 255
        #byte = byte % 256
        fixedLine.append(byte)
      else:
        fixedLine.append(byte)
    pdb.set_trace()
    newLine = struct.pack("%sB" % len(fixedLine), *fixedLine)
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
        #print "Debug: Row %d Filter: %d" % (i, struct.unpack("B", newFilter[0])[0])
        if newFilter == b'\x00':
          newRow = editLine(newRow)
        else:
          #print "Warning: Only filter 0 gives expected results"
          #raise Warning("Unaccepted filter. Only 0 is accepted")
          newRow = editLine(newRow)
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
      print "Decompressing image data.."
      filterInfo = [0] * 5
      chunkData = zlib.decompress(chunkData)
      chunkData = StringIO.StringIO(chunkData)
      print "  ..lasted %f seconds" % (dt.now() - startTime).total_seconds()
      startTime = dt.now()
      #chunkData is a string. Each byte containg either R, B or G value
      print "Reading filter byte from each scanline.."
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
      print "  ..lasted %f seconds" % (dt.now() - startTime).total_seconds()
      print "Filter information:"
      print "Filter 0 (None) Used %d times in %d scanlines" % (filterInfo[0], self.height)
      print "Filter 1 (Sub) Used %d times in %d scanlines" % (filterInfo[1], self.height)
      print "Filter 2 (Up) Used %d times in %d scanlines" % (filterInfo[2], self.height)
      print "Filter 3 (Avg) Used %d times in %d scanlines" % (filterInfo[3], self.height)
      print "Filter 4 (Paeth) Used %d times in %d scanlines" % (filterInfo[4], self.height)
  
  #Do some changes to image and save it as newFilename
  def readImageChunks(self, filename, writeToFile = None, opMode = 0):
    readFp = open(filename, "r")
    header = readFp.read(8)
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
        print "No more chunks to read"
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
        dim = self.printIHDR(chunkData)
        if opMode == self.HDR_MODE:
          return
      elif chunkType == "IDAT":
        #Print filter info
        if opMode == self.FILTER_MODE:
          self.printFilterInfo(chunkData)      
        #Reconstruct data and save to new image
        elif opMode == self.RECON_MODE:
          chunkData = self.reconstData(chunkData)      
        #Edit color bytes and save to new image
        elif opMode == self.EDIT_MODE:
          chunkData = self.editColors(chunkData)      
        #Just read the chunks
        elif opMode == self.CHUNK_MODE:
          pass
      if writeToFile:
        print "Writing chunk to file", writeToFile
        print ""
        write_chunk(writeFp, chunkType, chunkData)
    readFp.close()
    if writeToFile:
      writeFp.close()
  
