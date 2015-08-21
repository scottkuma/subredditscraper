#!/usr/bin/env python

__author__ = 'scottkuma'

import praw			# pip install praw
import argparse
from time import sleep
import socket
import shutil
import warnings
import os
import os.path
import sys
import imgurpython    		# pip install imgurpython
from imgurpython.helpers.error import ImgurClientError
import requests



with warnings.catch_warnings():
    warnings.simplefilter("ignore")
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
                        help='Limit the time period for submissions. Only affects "top" and "controversial" requests.',
                        choices=time_periods,
                        default="all")

    args = parser.parse_args()

    # Create necessary variables for script

    save_dir = args.basedir + "/" + args.subreddit + "/"
    already_done = []  # variable to hold reddit submission IDs that were parsed
                       # Trying to prevent work being done twice...
    parsed = 0     # number of URLs parsed
    imgur_api_call_count = 0    # tracking variable for # of calls to imgur API
    KEEP_CHARACTERS = (' ', '.', '_')   # characters (other than alphanumeric) to keep in filenames
    filetypes = ['jpg', 'jpeg', 'png', 'gif', 'gifv', 'webm']  # file types to download
    saved = 0


    # set socket timeout
    socket.setdefaulttimeout(args.timeout)

    try:
        # Create connection to reddit...
        r = praw.Reddit('ab_reddit_parser')

        # Create API connection to IMGUR...
        IMGUR_CLIENT_ID = '601caf77c951324'
        IMGUR_CLIENT_SECRET = '1992f212ad57071e09ad2c2fd44db67084a1f148'
        ic = imgurpython.ImgurClient(IMGUR_CLIENT_ID, IMGUR_CLIENT_SECRET)

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
                    print "\n"
                    print "-=" * 30 + "-"
                    print sub.score, "::", sub.title
                    url = sub.url

                    # some sources provide more than one URL to parse...
                    # We'll store these in a list, which also gives us the
                    # ability to skip over sites that we can't parse yet.
                    urllist = []

                    # Some trailing slashes can cause problems for our little client.
                    # we must remove them.
                    if url[-1] == '/':
                        url = url[:-1]

                    # Detect Special Cases
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
                            filetype = ic.get_image(imageid).type
                        except ImgurClientError as e:
                            print "Error Message:", e.error_message
                            print "Error code:", e.status_code
                            print "Continuing...."
                        imgur_api_call_count += 1
                        if filetype == 'image/jpeg':
                            url += '.jpg'
                        elif filetype == 'image/gif':
                            url += '.gif'
                        elif filetype == 'image/png':
                            url += '.png'
                        print "-->", url
                        urllist.append(url)

                    # download giphy GIFs (need to work on this - may not every work!)
                    elif "giphy" in url:
                        print "+" * 30, "GIPHY not implemented yet.... (skipping)"

                    # download gfycat GIFs
                    elif "gfycat" in url:
                        # some trailing anchors can cause problems for our little client.
                        # we must remove them.
                        if url[-1] == '#':
                            url = url[:-1]

                        # need to get the "gfyGifUrl" for the resource!
                        fh = requests.get(url)
                        for line in fh.iter_lines():
                            if "gfyGifUrl" in line:
                                gfyURL = line.split('"')[1]
                                urllist.append(gfyURL)

                    # download flickr pictures (Does not currently work, skips these photos)
                    elif "flickr" in url:
                        print "+" * 30, "FLICKR found.... (skipping)"

                    else:
                        # Not one of our special sites, so just append the URL to the list for download
                        urllist.append(url)

                    fileinURL = 0
                    for url in urllist:
                        fileinURL += 1  # increment this counter
                        filedesc = "".join(c for c in sub.title if c.isalnum() or c in KEEP_CHARACTERS).rstrip()
                        filename = str(url).split('/')[-1]

                        if len(urllist) > 1:
                            fullfilename = filedesc + " - {0:03d} - ".format(fileinURL) + filename
                        else:
                            fullfilename = filedesc + " - " + filename

                        file_path = save_dir + fullfilename

                        if os.path.isfile(file_path):
                            print "** Skipping \"" + fullfilename + "\" - file already exists..."
                        else:
                            try:
                                response = requests.get(url, stream=True)
                                total_length = response.headers.get('content-length')
                                if total_length is not None and response.headers['content-type'].split('/')[0] == 'image':
                                    print "Saving to: \"{}\"".format(file_path)
                                    with open(file_path, 'wb') as out_file:
                                        dl = 0
                                        total_length = int(total_length)
                                        for data in response.iter_content(chunk_size=1024):
                                            out_file.write(data)
                                            # Calculate & write progress bar to standard output.
                                            dl += len(data)
                                            done = int(50 * dl / total_length)
                                            sys.stdout.write("\r[%s>%s] %d / %d" % ('=' * (done - 1), ' ' * (50 - done), dl, total_length) )
                                            sys.stdout.flush()
                                        print " "
                                    # remove response object from memory to prevent leak.
                                    del response
                                    saved += 1
                                else:
                                    print "Skipped - either not an image or 0 length..."

                            except IOError:
                                print "Unable to retrieve this URL!"
                                pass

                        already_done.append(sub.id)
    except KeyboardInterrupt:
        print "\n\nCaught Keyboard Interrupt...ending gracefully."
    finally:
        print "\n\n Final Statistics:"
        print "-----------------"
        print parsed, "URLs parsed"
        #print parsed - len(already_done), "URLs skipped"
        print imgur_api_call_count, "calls made to IMGUR API."
        print saved, "images saved to directory."
        if args.iterate:
            sleep(args.sleep)
