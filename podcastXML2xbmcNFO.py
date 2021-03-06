#!/usr/bin/env python

# This is a quickly hacked script to turn the ccc.media.de's podcast.xml,
# released for each Chaos Communication Congress, into XBMC *.nfo files.
#
# To find these files go to http://media.ccc.de/browse/congress/<INSERT YEAR HERE>/podcast.xml
#
# (c) 2014 by Florian Franzen

# ToDo: Scrap 'Fahrplan' info and add it to nfo (e.g. pictures of speaker)
# ToDo: Allow diffrent ending. Right now only '_h264-hq.mp4' is supported

import argparse

import xml.etree.ElementTree as ET
import urllib
import re
import codecs
import os
from collections import namedtuple

Talk = namedtuple("Talk", "title subtitle description speakers category prefix")

parser = argparse.ArgumentParser(description='Creates NFO files for each entry in a podcast.xml file.')

parser.add_argument('-x', '--xml-file', help='Path to the xml file. (Default: downloaded automatically)')

parser.add_argument('CONF_NUM', type=int, help='The conference the podcast.xml is from e.g. 30 if you run this for the 30c3.')
config = parser.parse_args()

# Parse XML file 
if config.xml_file is not None:
    tree = ET.parse(config.xml_file)
    root = tree.getroot()
else:
    podcast_xml = urllib.urlopen("http://media.ccc.de/browse/congress/%d/podcast.xml" % (1983 + config.CONF_NUM)).read()
    root = ET.fromstring(podcast_xml)

# Make sure directory exist
directory = 'S%02d/' % config.CONF_NUM

if not os.path.exists(directory):
    os.makedirs(directory)
os.chdir(directory)

# Parse all talks
all_talks = dict()

for item in root[0].findall('item'):
    title = item.find('title').text[6:]

    subtitle = item.find('{http://www.itunes.com/dtds/podcast-1.0.dtd}subtitle')
    if subtitle is not None:
        subtitle = subtitle.text

    category = item.find('{http://www.itunes.com/dtds/podcast-1.0.dtd}keywords').text

    speakers = item.find('{http://www.itunes.com/dtds/podcast-1.0.dtd}author')
    if speakers is not None:
        speakers = speakers.text.split(",")
    else:
        speakers = []

    description = item.find('description').text
    description = re.split('event on media: |about this event: ', description)[0].strip()

    # Extract prefix from link
    link = item.find('link').text
    match = re.search(r'(?<=/)[^/]*(?=(_webm\.webm|_h264(-hq|-iprod)?\.mp4))', link)
    if match is not None:
        prefix = match.group(0)
    else:
        print("Can not extract prefix from following link: ", link)
        continue

    # Extract id from prefix
    match = re.search(r'(?<=\d{2}c3-)\d{4}(?=-)', prefix)
    if match is not None:
        id_num = int(match.group(0))
    else:
        print("Can not extract ID from prefix: ", prefix)
        continue

    all_talks[id_num] = Talk(title, subtitle, description, speakers, category, prefix)

# Compute length of zero padding
num_talks = len(all_talks)
num_digit = 0
while num_talks != 0:
    num_digit += 1
    num_talks //= 10

# For each talk...
rename_file = "#! /bin/sh\n"
episode = 1
for id_num in sorted(all_talks):
    talk = all_talks[id_num]

    # ... create NFO files
    xml_file = r"""<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
    <episodedetails>
        <showtitle>Chaos Communication Congress</showtitle>
        <season>%d</season>
        <episode>%d</episode>
        <title>%s</title>""" % (config.CONF_NUM, episode, talk.title)

    if talk.subtitle is not None:
        xml_file += """
        <outline>%s</outline>""" % talk.subtitle

    xml_file += """
        <year>%s</year>
        <id>%s</id>
        <plot>
            %s
        </plot>
        <genre>Talk</genre>
        <tag>%s</tag>
    """ % (1983 + config.CONF_NUM, id_num, talk.description, talk.category)

    for speaker in talk.speakers:
        xml_file += r"""    <actor>
            <name>%s</name>
            <role></role>
        </actor>
    """ % speaker.strip()

    xml_file += r"</episodedetails>"

    file_pointer = codecs.open(talk.prefix + "_h264-hq.s%02de%0*d.nfo" % (config.CONF_NUM, num_digit, episode), "w", "utf-8-sig")
    file_pointer.write(xml_file)

    # ... collect the file names for the renaming script
    rename_file += "mv '%s' '%s'\n" % (talk.prefix + "_h264-hq.mp4", talk.prefix + "_h264-hq.s%02de%0*d.mp4" % (config.CONF_NUM, num_digit, episode))

    episode += 1

# Save rename script
f = open("rename.sh", "w")
f.write(rename_file)
f.close()

print("Finished parsing all %d talks of %dc3." % (episode - 1, config.CONF_NUM))
