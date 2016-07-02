#!/usr/bin/env python
#
# Recursive walk of a directory finding video files and calculate the duration
# of them all.
#
import subprocess
import datetime
import json
import pprint
import os
import re
import argparse
import sys
import datetime, unicodedata
valid_file_extensions = (".avi", ".xvid", ".ogv", ".ogm", ".mkv", ".mpg", ".mp4")

def main(arguments):
   parser = argparse.ArgumentParser(description=__doc__,
                                    formatter_class=argparse.RawDescriptionHelpFormatter)
   parser.add_argument('directory', help="starting directory")
   parser.add_argument('-b', '--base_dir', help="base directory")
   global args
   args = parser.parse_args(arguments)
   if args.directory and os.path.exists(args.directory):
      print ("Process directory: %s" % str(os.path.abspath(args.directory)))
      process_dir(os.path.abspath(args.directory))
   else:
      print ("Directory '%s' does not exist.", os.path.abspath(args.directory))

def process_dir(directory):
    processed = 0
    duration = 0
    for root, dirs, files in os.walk(directory):
        files.sort()
        dirs.sort()
        for filename in files:
            if not filename.endswith(valid_file_extensions):
                continue
            processed += 1
            file = os.path.join(root, filename)
            proc = subprocess.Popen(["ffprobe", '-hide_banner', '-loglevel', 'quiet', '-show_format', '-print_format', 'json', file], stdout=subprocess.PIPE)
            data = json.load(proc.stdout)
            duration += float(data['format']['duration'])
                
    print ("%d files %s in length" % (processed, datetime.timedelta(seconds=duration)))
    
if __name__ == "__main__":
   sys.exit(main(sys.argv[1:]))
