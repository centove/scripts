#!/usr/bin/python3
import os.path, sys, re
from titlecase import titlecase
import argparse
import datetime
import unicodedata



valid_extensions = (".avi", ".xvid", ".ogv", ".ogm", ".mkv", ".mpg", ".mp4", ".srt")
# cruft we want to strip
audio = ['([^0-9])5\.1[ ]*ch(.)','([^0-9])5\.1([^0-9]?)','([^0-9])7\.1[ ]*ch(.)','([^0-9])7\.1([^0-9])']
video = ['3g2', '3gp', 'asf', 'asx', 'avc', 'avi', 'avs', 'bivx', 'bup', 'divx', 'dv', 'dvr-ms', 'evo', 'fli', 'flv',
         'm2t', 'm2ts', 'm2v', 'm4v', 'mkv', 'mov', 'mp4', 'mpeg', 'mpg', 'mts', 'nsv', 'nuv', 'ogm', 'ogv', 'tp',
         'pva', 'qt', 'rm', 'rmvb', 'sdp', 'svq3', 'strm', 'ts', 'ty', 'vdr', 'viv', 'vob', 'vp3', 'wmv',
         'wtv', 'xsp', 'xvid', 'webm']
format= ['ac3','dc','divx','fragment','limited','ogg','ogm','ntsc','pal','ps3avchd','r1','r3','r5',
         'remux','x264','xvid','vorbis','aac','dts','fs','ws','1920x1080',
         '1280x720','h264','h','264','prores','uhd','2160p','truehd','atmos','hevc']              
misc  = ['cd1','cd2','1cd','2cd','custom','internal','repack','read.nfo','readnfo','nfofix','proper',
         'rerip','dubbed','subbed','extended','unrated','xxx','nfo','dvxa']
subs  = ['multi', 'multisubs']
sizes = ['480p', '720p', '1080p', '480i', '720i', '1080i']
src_dict = {'bluray':['bdrc','bdrip','bluray','bd','brrip','hdrip','hddvd','hddvdrip'],
                        'cam':['cam'],'dvd':['ddc','dvdrip','dvd','r1','r3','r5'],'retail':['retail'],
                        'dtv':['dsr','dsrip','hdtv','pdtv','ppv'],'stv':['stv','tvrip'],
                        'screener':['bdscr','dvdscr','dvdscreener','scr','screener'],
                        'svcd':['svcd'],'vcd':['vcd'],'telecine':['tc','telecine'],
                        'telesync':['ts','telesync'],'web':['webrip','web-dl'],'workprint':['wp','workprint']}
yearRx = '([\(\[ \.\-])([1-2][0-9]{3})([\.\-\)\]_,+])'
sizeRx = '([0-9]{3,4}[i|p])'

source = []
for d in src_dict:
    for s in src_dict[d]:
        if source != '':
            source.append(s);
reversed_tokens = set()
for f in format + source:
    if len(f) > 3:
        reversed_tokens.add(f[::-1].lower())


def CleanName(name):
    name_tokens_lowercase = set()
    for t in re.split('([^ \-_\.\(\)+]+)', name):
        t = t.strip()
        if not re.match('[\.\-_\(\)+]+', t) and len(t) > 0:
            name_tokens_lowercase.add(t.lower())
    if len(set.intersection(name_tokens_lowercase, reversed_tokens)) > 2:
        name = name[::-1]
    orig = name
    try:
        name = unicodedata.normalize('NFKC', name.decode(sys.getfilesystemencoding()))
    except:
        try:
            name = unicodedata.normalize('NFKC', name.decode('utf-8'))
        except:
            pass
    name = name.lower()
    
    # Grab the year if specified
    year = None
    yearMatch = re.search(yearRx, name)
    if yearMatch:
        yearStr = yearMatch.group(2)
        yearInt = int(yearStr)
        if yearInt > 1900 and yearInt < (datetime.date.today().year + 1):
            year = int(yearStr)
            name = name.replace(yearMatch.group(1) + yearStr + yearMatch.group(3), ' *yearBreak* ')

    # Grab the size if it's one that we want
    size = None
    sizeMatch = re.search(sizeRx, name)
    if sizeMatch:
        size = sizeMatch.group(1)
        print ("Resolution detected as %s" % (size))
        
    # Take out things in brackets. (sub acts weird here, so we have to do it a few times)
    done = False
    while done == False:
        (name, count) = re.subn(r'\[[^\]]+\]', '', name, re.IGNORECASE)
        if count == 0:
            done = True
    # Take out audio specs, after suffixing with space to simplify rx.
    name = name + ' '
    for s in audio:
        rx = re.compile(s, re.IGNORECASE)
        name = rx.sub(' ', name)

    # Now we tokenize it
    tokens = re.split('([^ \-_\.\(\)+]+)', name)

    # Process the tokens
    newTokens = []
    tokenBitmap = []
    seenTokens = {}
    finalTokens = []

    for t in tokens:
            t = t.strip()
            if not re.match('[\.\-_\(\)+]+', t) and len(t) > 0:
                newTokens.append(t)
    if newTokens[-1] != '*yearBreak*':
        extension = "." + newTokens[-1]
    else:
        extension = None
    # Now we build a bitmap of what we want to keep (good) and what to toss (bad)
    garbage = subs
    garbage.extend(misc)
    garbage.extend(format)
    garbage.extend(source)
    garbage.extend(video)
    garbage = set(garbage)
    for t in  reversed(newTokens):
        if t.lower() in garbage and t.lower() not in seenTokens:
            seenTokens[t.lower()] = True
            tokenBitmap.insert(0, False)
        else:
            tokenBitmap.insert(0,True)
    numGood = 0
    numBad  = 0
    for i in range(len(tokenBitmap)):
        good = tokenBitmap[i]
        if len(tokenBitmap) <= 2:
            good = True
        if good and numBad <= 2:
            if newTokens[i] =='*yearBreak*':
                if i == 0:
                    continue
                else:
                    break
            else:
                finalTokens.append(newTokens[i])
        elif not good and newTokens[i].lower() == 'dc':
            if i+1 < len(newTokens) and newTokens[i+1].lower() in ['comic', 'comics']:
                finalTokens.append('DC')
            else:
                finalTokens.append("(Director's cut)")
    if good == True:
        numGood += 1
    else:
        numBad += 1
    if len(finalTokens) == 0 and len(newTokens) > 0:
        finalTokens.append(newTokens[0])

    finalTokens.append("(" + str(year) + ")")

    cleanedName = ' '.join(finalTokens)
    
    if extension and extension in valid_extensions:
        if size:
            cleanedName += " - " + size
        cleanedName += extension
    return (titlecase(cleanedName), year)

def renameFile(old, new):
    if os.path.exists(new):
        print ("Not renaming '%s' as it already exists." % (new)) if args.verbose else None
    else:
        print ("mv %s -> %s" % (old, new))
        if not args.dry_run:
            os.rename(old, new)
        

def process_directory(directory):
    print ("Processing directory '%s'" % directory)
    for root, dirs, files in os.walk(directory, True):
        for name in files:
            if not name.endswith(valid_extensions):
                if os.path.isfile(name):
                     print ("Potential junk %s" % (name))
                continue
            if args.process_directories:
                print ("Process Directory: %s - %s" % (os.path.basename(root), name)) if args.verbose else None
                newDirectory = CleanName(os.path.basename(root))
                renameFile(root, os.path.join(os.path.dirname(root),newDirectory[0]))
                    
            newName = CleanName(name)
            if newName != name:
                if args.process_directories:
                    renameFile(os.path.join(newDirectory[0], name), os.path.join(newDirectory[0], newName[0]))
                else:
                    renameFile(os.path.join(root, name), os.path.join(root, newName[0]))

def FindYear(words):
  yearRx = '^[1-2][0-9]{3}$'
  i = 0
  for w in words:
    if re.match(yearRx, w):
      year = int(w)
      if year > 1900 and year < datetime.date.today().year + 1:
        return i
    i += 1

  return None

#
#  -*- MAIN -*-
#
def main(arguments):
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs='*',
                        default=os.getcwd(),
                        help="Starting Directory")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Increase output verbosity")
    parser.add_argument("-d",'--process_directories', action="store_true", default=False,
                        help="Process directories only")
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help="Don't rename or delete things just show what would happen.")
    
    
    args = parser.parse_args(arguments)

    if isinstance(args.directory, str) and args.directory and os.path.exists(args.directory):
        process_directory(args.directory)
    else:
        for directory in args.directory:
            if os.path.exists(directory):
                process_directory(directory)

if __name__ == "__main__":
     sys.exit(main(sys.argv[1:]))

