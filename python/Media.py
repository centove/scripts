#!/usr/bin/env python
# Shamlessly ripped from Plex.
#
# Take a file name and try and figure out the series, season, episode and optionally the year
# that the video file potentially belongs to. And strip out all the nonsense that usually
# is included in filenames.
#
import os
import re
import argparse
import sys
import datetime, unicodedata

video_exts = ['3g2', '3gp', 'asf', 'asx', 'avc', 'avi', 'avs', 'bivx', 'bup',
              'divx', 'dv', 'dvr-ms', 'evo', 'fli', 'flv', 'm2t', 'm2ts', 'm2v',
              'm4v', 'mkv', 'mov', 'mp4', 'mpeg', 'mpg', 'mts', 'nsv', 'nuv',
              'ogm', 'ogv', 'tp', 'pva', 'qt', 'rm', 'rmvb', 'sdp', 'svq3',
              'strm', 'ts', 'ty', 'vdr', 'viv', 'vob', 'vp3', 'wmv', 'wpl', 'wtv',
              'xsp', 'xvid', 'webm']
ignore_samples = ['[-\._]sample', 'sample[-\._]']
ignore_trailers = ['-trailer\.']
ignore_extras = ['^trailer.?$','-deleted\.', '-behindthescenes\.', '-interview\.', '-scene\.', '-featurette\.', '-short\.', '-other\.']
ignore_extras_startswith = ['^movie-trailer.*']
ignore_dirs =  ['\\bextras?\\b', '!?samples?', 'bonus', '.*bonus disc.*', 'bdmv', 'video_ts', '^interview.?$', '^scene.?$', '^trailer.?$', '^deleted.?(scene.?)?$', '^behind.?the.?scenes$', '^featurette.?$', '^short.?$', '^other.?$']
ignore_suffixes = ['.dvdmedia']
source_dict = {'bluray':['bdrc','bdrip','bluray','bd','brrip','hdrip','hddvd','hddvdrip'],'cam':['cam'],'dvd':['ddc','dvdrip','dvd','r1','r3','r5'],'retail':['retail'],
               'dtv':['dsr','dsrip','hdtv','pdtv','ppv'],'stv':['stv','tvrip'],'screener':['bdscr','dvdscr','dvdscreener','scr','screener'],
               'svcd':['svcd'],'vcd':['vcd'],'telecine':['tc','telecine'],'telesync':['ts','telesync'],'web':['webrip','web-dl'],'workprint':['wp','workprint']}
source = []
for d in source_dict:
  for s in source_dict[d]:
    if source != '':
      source.append(s)

audio = ['([^0-9])5\.1[ ]*ch(.)','([^0-9])5\.1([^0-9]?)','([^0-9])7\.1[ ]*ch(.)','([^0-9])7\.1([^0-9])']
subs = ['multi','multisubs']
misc = ['cd1','cd2','1cd','2cd','custom','internal','repack','read.nfo','readnfo','nfofix','proper','rerip','dubbed','subbed','extended','unrated','xxx','nfo','dvxa']
format = ['ac3','dc','divx','fragment','limited','ogg','ogm','ntsc','pal','ps3avchd','r1','r3','r5','720i','720p','1080i','1080p','remux','x264','xvid','vorbis','aac','dts','fs','ws','1920x1080','1280x720','h264','h','264','prores']
edition = ['dc','se'] # dc = directors cut, se = special edition
episode_regexps = [
    '(?P<show>.*?)[sS](?P<season>[0-9]+)[\._ ]*[eE](?P<ep>[0-9]+)[\._ ]*([- ]?[sS](?P<secondSeason>[0-9]+))?([- ]?[Ee+](?P<secondEp>[0-9]+))?', # S03E04-E05
    '(?P<show>.*?)[sS](?P<season>[0-9]{2})[\._\- ]+(?P<ep>[0-9]+)',                                                            # S03-03
    '(?P<show>.*?)([^0-9]|^)(?P<season>(19[3-9][0-9]|20[0-5][0-9]|[0-9]{1,2}))[Xx](?P<ep>[0-9]+)((-[0-9]+)?[Xx](?P<secondEp>[0-9]+))?',  # 3x03, 3x03-3x04, 3x03x04
    '(.*?)(^|[\._\- ])+(?P<season>sp)(?P<ep>[0-9]{2,3})([\._\- ]|$)+',  # SP01 (Special 01, equivalent to S00E01)
    '(.*?)[^0-9a-z](?P<season>[0-9]{1,2})(?P<ep>[0-9]{2})([\.\-][0-9]+(?P<secondEp>[0-9]{2})([ \-_\.]|$)[\.\-]?)?([^0-9a-z%]|$)' # .602.
  ]
date_regexps = [
    '(?P<year>[0-9]{4})[^0-9a-zA-Z]+(?P<month>[0-9]{2})[^0-9a-zA-Z]+(?P<day>[0-9]{2})([^0-9]|$)',                # 2009-02-10
    '(?P<month>[0-9]{2})[^0-9a-zA-Z]+(?P<day>[0-9]{2})[^0-9a-zA-Z(]+(?P<year>[0-9]{4})([^0-9a-zA-Z]|$)', # 02-10-2009
  ]
standalone_episode_regexs = [
  '(.*?)( \(([0-9]+)\))? - ([0-9]+)+x([0-9]+)(-[0-9]+[Xx]([0-9]+))?( - (.*))?',  # Newzbin style, no _UNPACK_
  '(.*?)( \(([0-9]+)\))?[Ss]([0-9]+)+[Ee]([0-9]+)(-[0-9]+[Xx]([0-9]+))?( - (.*))?'   # standard s00e00
  ]
season_regex = '.*?(?P<season>[0-9]+)$' # folder for a season
just_episode_regexs = [
    '(?P<ep>[0-9]{1,3})[\. -_]*of[\. -_]*[0-9]{1,3}',       # 01 of 08
    '^(?P<ep>[0-9]{1,3})[^0-9]',                           # 01 - Foo
    'e[a-z]*[ \.\-_]*(?P<ep>[0-9]{2,3})([^0-9c-uw-z%]|$)', # Blah Blah ep234
    '.*?[ \.\-_](?P<ep>[0-9]{2,3})[^0-9c-uw-z%]+',         # Flah - 04 - Blah
    '.*?[ \.\-_](?P<ep>[0-9]{2,3})$',                      # Flah - 04
    '.*?[^0-9x](?P<ep>[0-9]{2,3})$',                       # Flah707
    '^(?P<ep>[0-9]{1,3})$'                                 # 01
  ]
ends_with_number = '.*([0-9]{1,2})$'
ends_with_episode = ['[ ]*[0-9]{1,2}x[0-9]{1,3}$', '[ ]*S[0-9]+E[0-9]+$']
yearRx = '([\(\[\.\-])([1-2][0-9]{3})([\.\-\)\]_,+])'

def parse_file(fname):
#   print "parse file %s" % fname
   for rx in episode_regexps[0:-1]:
      match = re.search(rx, fname, re.IGNORECASE)
      if match:
         # Extract data.
         show = match.group('show')
         season = match.group('season')
         if season.lower() == 'sp':
           season = 0
         episode = int(match.group('ep'))
         endEpisode = episode
         if match.groupdict().has_key('secondEp') and match.group('secondEp'):
           endEpisode = int(match.group('secondEp'))
         name, year = CleanName(show)
         
#         print name, year, season, episode
         return name, season, episode, year

def CleanName(name):
   orig = name
   try:
      name = unicodedata.normalize('NFKC', name.decode(sys.getfilesystemencoding()))
   except:
      try:
         name = unicodedata.normalize('NFKC', name.decode('utf-8'))
      except:
         pass
   name = name.lower()
   year = None
   yearMatch = re.search(yearRx, name)
   if yearMatch:
      yearStr = yearMatch.group(2)
      yearInt = int(yearStr)
      if yearInt > 1900 and yearInt < (datetime.date.today().year + 1):
         year = int(yearStr)
         name = name.replace(yearMatch.group(1) + yearStr + yearMatch.group(3), ' *yearBreak* ')

   # Take out things in brackets. (sub acts weird here, so we have to do it a few times)
   done = False
   while done == False:
     (name, count) = re.subn(r'\[[^\]]+\]', '', name, re.IGNORECASE)
     if count == 0:
       done = True

   # Take out bogus suffixes.
   for suffix in ignore_suffixes:
     rx = re.compile(suffix + '$', re.IGNORECASE)
     name = rx.sub('', name)
   
   # Take out audio specs, after suffixing with space to simplify rx.
   name = name + ' '
   for s in audio:
     rx = re.compile(s, re.IGNORECASE)
     name = rx.sub(' ', name)
     
   # Now tokenize.
   tokens = re.split('([^ _\.\(\)+]+)', name)
   
   # Process tokens.
   newTokens = []
   for t in tokens:
     t = t.strip()
     if not re.match('[\._\(\)+]+', t) and len(t) > 0:
     #if t not in ('.', '-', '_', '(', ')') and len(t) > 0:
       newTokens.append(t)
   
   # Now build a bitmap of good and bad tokens.
   tokenBitmap = []
   garbage = subs
   garbage.extend(misc)
   garbage.extend(format)
   garbage.extend(edition)
   garbage.extend(source)
   garbage.extend(video_exts)
   garbage = set(garbage)
   
   # Keep track of whether we've encountered a garbage token since they shouldn't appear more than once.
   seenTokens = {}
   # Go through the tokens backwards since the garbage most likely appears at the end of the file name.
   # If we've seen a token already, don't consider it garbage the second time.  Helps cases like "Internal.Affairs.1990-INTERNAL.mkv"
   #
   for t in reversed(newTokens):
     if t.lower() in garbage and t.lower() not in seenTokens:
       tokenBitmap.insert(0, False)
       seenTokens[t.lower()] = True
     else:
       tokenBitmap.insert(0, True)
   
   
   # Now strip out the garbage, with one heuristic; if we encounter 2+ BADs after encountering
   # a GOOD, take out the rest (even if they aren't BAD). Special case for director's cut.
   numGood = 0
   numBad  = 0
   
   finalTokens = []
   for i in range(len(tokenBitmap)):
     good = tokenBitmap[i]
   
     # If we've only got one or two tokens, don't whack any, they might be part of
     # the actual name (e.g. "Internal Affairs" "XXX 2")
     #
     if len(tokenBitmap) <= 2:
       good = True
   
     if good and numBad < 2:
       if newTokens[i] == '*yearBreak*':
         # If the year token is first just skip it and keep reading,
         # otherwise we can ignore everything after it.
         #
         if i == 0:
           continue
         else:
           break
       else:
         finalTokens.append(newTokens[i])
     elif not good and newTokens[i].lower() == 'dc':
       finalTokens.append("(Director's cut)")
   
     if good == True:
       numGood += 1
     else:
       numBad += 1
   
   # If we took *all* the tokens out, use the first one, otherwise we'll end up with no name at all.
   if len(finalTokens) == 0 and len(newTokens) > 0:
     finalTokens.append(newTokens[0])
   
#   print "CLEANED [%s] => [%s]" % (orig, u' '.join(finalTokens))
#   print "TOKENS: ", newTokens
#   print "BITMAP: ", tokenBitmap
#   print "FINAL:  ", finalTokens
   
   cleanedName = ' '.join(finalTokens)
   # If we failed to decode/encode above, we may still be dealing with a non-ASCII string here,
   # which will raise if we try to encode it, so let's just handle it and hope for the best!
   #
   try:
     cleanedName = cleanedName.encode('utf-8')
   except:
     pass
   # Return something we can feed to imdb/thetvdb/moviedb to fetch metadata
   return cleanedName, year
