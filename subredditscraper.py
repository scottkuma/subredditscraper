#!/usr/bin/env python

__author__ = 'scottkuma'

import praw			# pip install praw
import argparse
from time import sleep
import urllib
import socket
import os
import os.path
import sys
import imgurpython    		# pip install imgurpython
from imgurpython.helpers.error import ImgurClientError

parser = argparse.ArgumentParser(description='Scrape images from a Subreddit',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('subreddit')

parser.add_argument('--basedir', '-b',
                    help="Base directory to save files to - will be appended with a subreddit directory.\
                         Defaults to current directory.",
                    default=os.getcwd())

parser.add_argument('-t', '--threshold',
                    metavar='T',
                    help="Reject posts with less than this # of upvotes",
                    default=0,
                    type=int)

parser.add_argument('--timeout', '--to',
                    help="Stop attempting to connect to a submission's URL after X seconds",
                    metavar='X',
                    default=10,
                    type=int)

parser.add_argument('--sleep',
                    help="# of seconds to sleep between attempts to scrape subreddit",
                    metavar='S',
                    default=300,
                    type=int)

parser.add_argument('--limit',
                    help="Max # of submissions to retrieve",
                    default=None,
                    type=int)

parser.add_argument('--iterate',
                    help="Iterate over group endlessly",
                    action='store_true')

post_types = ['hot', 'new', 'rising', 'controversial', 'top']

parser.add_argument('--type', '-p',
                    help="Fetch a certain type of reddit submissions",
                    choices=post_types,
                    default='new')

time_periods = ['hour', 'day', 'week', 'month', 'year', 'all']

parser.add_argument('--period',
                    help='Limit the time period for submissions. Only affects "new" and "controversial" requests.',
                    choices=time_periods,
                    default="all")

args = parser.parse_args()

# set socket timeout
socket.setdefaulttimeout(args.timeout)

# Create connection to reddit...
r = praw.Reddit('ab_reddit_parser')

# Create API connection to IMGUR...
IMGUR_CLIENT_ID = '601caf77c951324'
IMGUR_CLIENT_SECRET = '1992f212ad57071e09ad2c2fd44db67084a1f148'
ic = imgurpython.ImgurClient(IMGUR_CLIENT_ID, IMGUR_CLIENT_SECRET)

# Create necessary variables for script

save_dir = args.basedir + "/" + args.subreddit + "/"
already_done = []  # variable to hold reddit submission IDs that were parsed
                   # Trying to prevent work being done twice...
parsed = 0     # number of URLs parsed
imgur_api_call_count = 0    # tracking variable for # of calls to imgur API
KEEP_CHARACTERS = (' ', '.', '_')   # characters (other than alphanumeric) to keep in filenames
filetypes = ['jpg', 'jpeg', 'png', 'gif', 'gifv', 'webm']  # file types to download


try:
    subreddit = r.get_subreddit(args.subreddit, fetch=True)   # get_top_from_all

except praw.errors.NotFound:
    print "Subreddit '{}' does not exist.".format(args.subreddit)
    sys.exit(0)

d = os.path.dirname(save_dir)
if not os.path.exists(d):
    os.makedirs(d)

iterate_once = True

while args.iterate or iterate_once:

    iterate_once = False

    if args.type == 'top':
        print "*** Fetching TOP submissions over past {}...".format(args.period)
        if args.period == "year":
            submissions = subreddit.get_top_from_year(limit=args.limit)
        elif args.period == "month":
            submissions = subreddit.get_top_from_month(limit=args.limit)
        elif args.period == "week":
            submissions = subreddit.get_top_from_week(limit=args.limit)
        elif args.period == "day":
            submissions = subreddit.get_top_from_day(limit=args.limit)
        elif args.period == "hour":
            submissions = subreddit.get_top_from_hour(limit=args.limit)
        else:
            submissions = subreddit.get_top_from_all(limit=args.limit)
    elif args.type == 'controversial':
        print "*** Fetching CONTROVERSIAL submissions over past {}...".format(args.period)
        if args.period == "year":
            submissions = subreddit.get_controversial_from_year(limit=args.limit)
        elif args.period == "month":
            submissions = subreddit.get_controversial_from_month(limit=args.limit)
        elif args.period == "week":
            submissions = subreddit.get_controversial_from_week(limit=args.limit)
        elif args.period == "day":
            submissions = subreddit.get_controversial_from_day(limit=args.limit)
        elif args.period == "hour":
            submissions = subreddit.get_controversial_from_hour(limit=args.limit)
        else:
            submissions = subreddit.get_controversial_from_all(limit=args.limit)
    elif args.type == 'hot':
        print "*** Fetching HOT submissions..."
        submissions = subreddit.get_hot(limit=args.limit)
    elif args.type == 'rising':
        print "*** Fetching RISING submissions..."
        submissions = subreddit.get_rising(limit=args.limit)
    else:
        print "*** Fetching NEW submissions..."
        submissions = subreddit.get_new(limit=args.limit)

    for sub in submissions:
        parsed += 1

        if sub.score >= args.threshold and sub.id not in already_done:
            print "\n\n"
            print "-=" * 20 + "-"
            print sub.score, "::", sub.title
            url = sub.url
            print url
            urllist = []


            # some trailing slashes can cause problems for our little client.
            # we must remove them.
            if url[-1] == '/':
                url = url[:-1]

            #Detect Special Cases
            if "imgur" in url and url.split('/')[-2] == 'a':
                print "Downloading from imgur album..."
                albumid = url.split('/')[-1].split('?')[0].split('#')[0]
                try:
                    for img in ic.get_album_images(albumid):
                        urllist.append(img.link)
                except ImgurClientError as e:
                    print "Error Message:", e.error_message
                    print "Error code:", e.status_code
                    print "Continuing...."
                imgur_api_call_count += 1
                print len(urllist), "images found"
            # need to remove anything after the image id, so...
            # removing anything that follows a ? or #
            elif "imgur" in url and url.split('.')[-1].split('?')[0].split('#')[0] not in filetypes:
                imageid = url.split('/')[-1].split('?')[0].split('#')[0]
                try:
                    type = ic.get_image(imageid).type
                except ImgurClientError as e:
                    print "Error Message:", e.error_message
                    print "Error code:", e.status_code
                    print "Continuing...."
                imgur_api_call_count += 1
                if type == 'image/jpeg':
                    url = url + '.jpg'
                elif type == 'image/gif':
                    url = url + '.gif'
                elif type == 'image/png':
                    url = url + '.png'
                print "-->", url
                urllist.append(url)


            # download gfycat GIFs
            elif "giphy" in url:
                print "+++++++++++++++++++++++++++++++++++++++++ GIPHY FOUND! (skipping)"

            elif "gfycat" in url:
                # some trailing anchors can cause problems for our little client.
                # we must remove them.
                if url[-1] == '#':
                    url = url[:-1]

                # need to get the "gfyGifUrl" for the resource!

                fh = urllib.urlopen(url)
                for line in fh.readlines():
                    if "gfyGifUrl" in line:
                        gfyURL = line.split('"')[1]

                urllist.append(gfyURL)


            else:
                urllist.append(url)

            fileinURL = 0
            for url in urllist:
                filedesc = "".join(c for c in sub.title if c.isalnum() or c in KEEP_CHARACTERS).rstrip()
                filename = str(url).split('/')[-1]

                if len(urllist) > 1:
                    fileinURL += 1
                    fullfilename = filedesc + " - {0:03d} - ".format(fileinURL) + filename
                else:
                    fullfilename = filedesc + " - " + filename

                print "...", fullfilename

                if os.path.isfile(save_dir + fullfilename):
                    print "** Skipping \"" + fullfilename + "\" - file already exists..."
                else:
                    try:
                        status = urllib.urlretrieve(url, save_dir + fullfilename)

                    except IOError:
                        print "Unable to retrieve this URL!"
                        pass

                already_done.append(sub.id)

    print parsed
    print imgur_api_call_count, "calls made to IMGUR API."
    print len(already_done), "images saved to directory."
    if args.iterate:
        sleep(args.sleep)
