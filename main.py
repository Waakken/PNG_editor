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
  #parser.add_option("-w", "--write", dest="writeFile", help="Write data to this file", metavar="FILE")
  parser.add_option("-f", "--filter", action = "store_true", dest="printFilter", help="Print filter information")
  parser.add_option("-d", "--debug", action = "store_true", dest="debug", help="Print debug information")
  parser.add_option("-c", "--chunks", action = "store_true", dest="readChunks", help="Only read chunks from image")
  parser.add_option("-H", "--hdr", action = "store_true", dest="readHdr", help="Print image data")
  parser.add_option("-r", "--recon", dest="reconFile", \
                    help="Save reconstructed data to this file", metavar="FILE")
  parser.add_option("-e", "--edit", dest="editFile", help="Save edited color data to this file", metavar="FILE")
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
    p.readImageChunks(args[0], opMode = p.HDR_MODE)
  if options.printFilter:
    p.readImageChunks(args[0], opMode = p.FILTER_MODE)
  if options.readChunks:
    p.readImageChunks(args[0], opMode = p.CHUNK_MODE)

if __name__ == "__main__":
  main()
