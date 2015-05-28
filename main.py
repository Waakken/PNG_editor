#!/usr/bin/env python

import struct
import zlib
import os
import StringIO
import datetime
import sys
import pdb
import optparse

from PngEdit import PngEdit as png

def setupArgParser():
  parser = optparse.OptionParser(usage="%prog image [options]")
  parser.add_option("-f", "--filter", action = "store_true", dest="printFilter", help="Print filter information")
  parser.add_option("-d", "--debug", action = "store_true", dest="debug", help="Print debug information")
  parser.add_option("-c", "--chunks", action = "store_true", dest="readChunks", help="Print chunk information")
  parser.add_option("-b", "--bytes", dest="readBytes", help="Print color bytes of LINE", metavar="LINE")
  parser.add_option("-H", "--hdr", action = "store_true", dest="readHdr", help="Print image information")
  parser.add_option("-p", "--pixel", action = "store_true", dest="readPixel", help="Print pixel information")
  parser.add_option("-r", "--recon", dest="reconFile", \
                    help="Create new reconstructed file in which all the data chunks are combined and pixel filtering is removed.", metavar="FILE")
  parser.add_option("-e", "--edit", dest="editFile", help="Save edited color data to this file", metavar="FILE")
  parser.add_option("-C", "--common", dest="commonFile", help="Create common-effect and save it to a file", metavar="FILE")
  parser.add_option("--blue", dest="blue", help="In edit mode: Add this value to blue bytes", metavar="INT")
  parser.add_option("--red", dest="red", help="In edit mode: Add this value to red bytes", metavar="INT")
  parser.add_option("--green", dest="green", help="In edit mode: Add this value to green bytes", metavar="INT")
  parser.add_option("--count", dest="pixelCount", help="In common-effect mode: Leave this many most common pixels", metavar="INT")
  return parser

def main():
  try:
    os.unlink("tempfile.png")
  except OSError:
    pass
  parser = setupArgParser()
  (options, args) = parser.parse_args()
  if len(args) != 1:
    parser.error("Please give one image to read")

  if options.readChunks or options.debug:
    p = png(debug = True)
  elif options.readHdr or options.readPixel:
    p = png(info = True)
  else:
    p = png()
  #pdb.set_trace()

  if options.blue:
    p.blueAdj = int(options.blue)
  if options.red:
    p.redAdj = int(options.red)
  if options.green:
    p.greenAdj = int(options.green)
  if options.pixelCount:
    p.pixelCount = int(options.pixelCount)
      

  # Print information:
  if options.readHdr:
    p.readChunks(args[0], opMode = p.HDR_MODE)
  if options.printFilter:
    p.readChunks(args[0], opMode = p.FILTER_MODE)
  if options.readChunks:
    p.readChunks(args[0], opMode = p.CHUNK_MODE)
  if options.readPixel:
    p.readChunks(args[0], opMode = p.PIXEL_MODE)
  if options.readBytes:
    p.readChunks(args[0], bytesLine = int(options.readBytes), opMode = p.BYTES_MODE)

  # Create new image:
  if options.reconFile:
    p.readChunks(args[0], writeToFile = "tempfile.png", opMode = p.SIMPLE_MODE)
    p.readChunks("tempfile.png", writeToFile = options.reconFile, opMode = p.RECON_MODE)
  if options.editFile:
    p.readChunks(args[0], writeToFile = options.editFile, opMode = p.EDIT_MODE)
  if options.commonFile:
    p.readChunks(args[0], writeToFile = options.commonFile, opMode = p.COMMON_EFFECT_MODE)

if __name__ == "__main__":
  main()
