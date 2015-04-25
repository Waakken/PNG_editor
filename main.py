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
  parser.add_option("-c", "--chunks", action = "store_true", dest="readChunks", help="Only read chunks from image")
  parser.add_option("-b", "--bytes", dest="readBytes", help="Print first line of color bytes, then exit")
  parser.add_option("-H", "--hdr", action = "store_true", dest="readHdr", help="Print image data then exit")
  parser.add_option("-r", "--recon", dest="reconFile", \
                    help="Save reconstructed data to this file", metavar="FILE")
  parser.add_option("-e", "--edit", dest="editFile", help="Save edited color data to this file", metavar="FILE")
  parser.add_option("-s", "--simple", dest="simpleFile", help="Combine all the data chunks. Leave only basic chunks to new file", metavar="FILE")
  return parser

def main():
  parser = setupArgParser()
  (options, args) = parser.parse_args()
  if len(args) != 1:
    parser.error("Please give one image to read")

  if options.readChunks or options.debug:
    p = png(debug = True)
  elif options.readHdr:
    p = png(info = True)
  else:
    p = png()
  #pdb.set_trace()

  if options.readHdr:
    p.readChunks(args[0], opMode = p.HDR_MODE)
  if options.printFilter:
    p.readChunks(args[0], opMode = p.FILTER_MODE)
  if options.readChunks:
    p.readChunks(args[0], opMode = p.CHUNK_MODE)
  if options.readBytes:
    p.readChunks(args[0], bytesLine = int(options.readBytes), opMode = p.BYTES_MODE)

  if options.simpleFile:
    p.readChunks(args[0], writeToFile = options.simpleFile, opMode = p.SIMPLE_MODE)
  if options.reconFile:
    p.readChunks(args[0], writeToFile = options.reconFile, opMode = p.RECON_MODE)

if __name__ == "__main__":
  main()
