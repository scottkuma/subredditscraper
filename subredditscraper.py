#!/usr/bin/env python

import praw  # pip install praw
import humanfriendly  # pip install humanfriendly
import imgurpython  # pip install imgurpython
import argparse
from time import sleep
import socket
import warnings
import os
import os.path
import sys
from imgurpython.helpers.error import ImgurClientError
import requests
import pprint
import urllib2
from bs4 import BeautifulSoup
import datetime


__author__ = 'scottkuma'

#INSERT YOUR API INFO HERE
REDDIT_CLIENT_ID = ''
REDDIT_CLIENT_SECRET = ''
REDDIT_USERNAME=''
REDDIT_PASSWORD=''
IMGUR_CLIENT_ID = ''
IMGUR_CLIENT_SECRET = ''

# TODO: make a requirements.txt file to auto-install requirements


with warnings.catch_warnings():
	warnings.simplefilter("ignore")
	parser = argparse.ArgumentParser(description='Scrape images from a Subreddit',
									 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('subreddit')

	parser.add_argument('--basedir', '-b',
						help="Base directory to save files to - will be appended with a subreddit directory.\
							 Defaults to <current directory>/Pictures.",
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
						default=100,
						type=int)

	parser.add_argument('--albumthreshold',
						help="Above this #, will download into subdirectories",
						default=5,
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

	# human-parseable filesize limits.
	parser.add_argument('--maxsize',
						help='Do not download files that are greater than this size in bytes.',
						default="30M")
	group = parser.add_mutually_exclusive_group()
						
	group.add_argument('--multireddit', '-m',
						help="Download from the user's multireddit",
						action='store_true')

	group.add_argument('--search', '-s',
						 help="Search for a string in reddit",
						 action='store_true')

	args = parser.parse_args()

	# Create necessary variables for script

	# Delete any trailing slashes
	if args.subreddit[-1] == "/":
		args.subreddit = args.subreddit[:-1]

	save_dir = args.basedir + "/" + args.subreddit + "/"
	already_done = []  # variable to hold reddit submission IDs that were parsed
	# Trying to prevent work being done twice...
	parsed = 0  # number of URLs parsed
	imgur_api_call_count = 0  # tracking variable for # of calls to imgur API
	KEEP_CHARACTERS = (' ', '.', '_')  # characters (other than alphanumeric) to keep in filenames
	filetypes = ['jpg', 'jpeg', 'png', 'webm', 'gif']  # file types to download
	saved = 0
	MAX_SIZE = humanfriendly.parse_size(args.maxsize)
	sleeptime = int(args.sleep)
	
	allurls = [['Title', 'URL', 'UTC Created Time', 'Subreddit Name', 'Permalink']]

	if args.limit == 100:
		print "Default limit of 100 URLs parsed!"


	# set socket timeout
	socket.setdefaulttimeout(args.timeout)

	try:
		# Create connection to reddit...
		
	  
		r = praw.Reddit(client_id=REDDIT_CLIENT_ID,
					 client_secret=REDDIT_CLIENT_SECRET,
					 username=REDDIT_USERNAME,
					 password=REDDIT_PASSWORD,
					 user_agent='SubRedditScraper v0.8')
		

		me = r.user.me()
		
		multis = {}
		
		for m in me.multireddits():
			thispath = m.path.split('/')[-1]
			multis[thispath] = m


		# Create API connection to IMGUR...

		ic = imgurpython.ImgurClient(IMGUR_CLIENT_ID, IMGUR_CLIENT_SECRET)

		try:
			subreddit = ''
			if args.multireddit:
				if args.subreddit in multis:
					subreddit = multis[args.subreddit]
				else:
					print "\n\n** ERROR: Multireddit {} does not exit for user {}.".format(args.subreddit, REDDIT_USERNAME)
					sys.exit(0)
			elif args.search:
				subreddit = r.subreddit('all').search(args.subreddit, limit=args.limit)
			else:
				subreddit = r.subreddit(args.subreddit)  # get_top_from_all
				

		except ():
			print "\n\n** ERROR: Subreddit '{}' does not exist.".format(args.subreddit)
			sys.exit(0)

		d = os.path.dirname(save_dir)
		if not os.path.exists(d):
			os.makedirs(d)

		iterate_once = True

		while args.iterate or iterate_once:

			iterate_once = False

			if args.search:
				submissions = subreddit 
			else:
				if args.type == 'top':
					print "*** Fetching TOP submissions over past {}...".format(args.period)
					submissions = subreddit.top(args.period,limit=args.limit)
				elif args.type == 'controversial':
					print "*** Fetching CONTROVERSIAL submissions over past {}...".format(args.period)
					submissions = subreddit.controversial(args.period,limit=args.limit)
				elif args.type == 'hot':
					print "*** Fetching HOT submissions..."
					submissions = subreddit.hot(limit=args.limit)
				elif args.type == 'rising':
					print "*** Fetching RISING submissions..."
					submissions = subreddit.rising(limit=args.limit)
				else:
					print "*** Fetching NEW submissions..."
					submissions = subreddit.new(limit=args.limit)

			for sub in submissions:
				parsed += 1
				
				#pprint.pprint(vars(sub))
				#sys.exit(0)

				if sub.score >= args.threshold and sub.id not in already_done:
					print "\n"
					print "-=" * 30 + "-"
					print "Item # ", parsed, "/", args.limit
					print "Title: ", sub.title.encode(encoding="UTF-8")
					print "Item Score: ", sub.score, "\n"
					
					url = sub.url
					allurls.append([sub.title, url, datetime.datetime.fromtimestamp(sub.created_utc).strftime('%Y-%m-%d %H:%M:%S'), sub.subreddit_name_prefixed, u"https://www.reddit.com" + sub.permalink])

					# Some sources provide more than one URL to parse...
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
							imagelist = ic.get_album_images(albumid)
							print "# images found: " + str(len(imagelist))
							if len(imagelist) > args.albumthreshold:
								albumflag = True
							else:
								albumflag = False
							for img in imagelist:
								if albumflag:
									urllist.append([img.link, albumid])
								else:
									print img.link
									urllist.append([img.link])
						except ImgurClientError as e:
							print "Error Message:", e.error_message
							print "Error code:", e.status_code
							print "URL:", url
							print "Continuing...."
						imgur_api_call_count += 1
						print len(urllist), "images found"

					# need to remove anything after the image id, so...
					# removing anything that follows a ? or #
					elif "imgur" in url and url.split('.')[-1].split('?')[0].split('#')[0] not in filetypes:
						print "SPECIAL SNOWFLAKE: URL: {}".format(url)
						imageid = url.split('/')[-1].split('?')[0].split('#')[0].split('.')[0]
						print "IMAGEID: {}".format(imageid)
						try:
							filetype = ic.get_image(imageid).type
							imgur_api_call_count += 1
							print "Trimmed file: Filetype: {}".format(filetype)
							if filetype == 'image/jpeg':
								url += '.jpg'
							elif filetype == 'image/gif':
								url += '.gif'
							elif filetype == 'image/png':
								url += '.png'
							elif filetype == 'text':
								url = url.split('.')[0]
								url += '.gif'
							else:
								print "Filetype: {}".format(filetype)
							print "-->", url
							urllist.append([url])
						except ImgurClientError as e:
							print "Error Message:", e.error_message
							print "Error code:", e.status_code
							print "URL:", url
							print "Continuing...."

					# TODO: download giphy GIFs (need to work on this - may not ever work!)
					elif "giphy" in url:
						print "+" * 30, "GIPHY not implemented yet.... (skipping)"

					# download gfycat GIFs
					elif "gfycat" in url:
						print url
						try:
							page = urllib2.urlopen(url).read()
							soup = BeautifulSoup(page)
							soup.prettify()
							#print soup.find_all('source', {'type': "video/webm"})
							for anchor in soup.find_all('source', {'type': "video/webm"}):
								#print anchor['src']
								if [anchor['src']] not in urllist:
									urllist.append( [anchor['src']] )
						except TypeError as e:
							print "Could not find a webm link"
							print "Continuing"
							

					# download flickr pictures (Does not currently work, skips these photos)
					elif "flickr" in url:
						print "+" * 30, "FLICKR found.... (skipping)"

					else:
						# Not one of our special sites, so just append the URL to the list for download
						urllist.append([url])

					fileinURL = 0
					for urlpair in urllist:
						url = urlpair[0]
						albumid = False
						filedesc = "".join(c for c in sub.title if c.isalnum() or c in KEEP_CHARACTERS).rstrip()
						filename = str(url).split('/')[-1]

						if len(urlpair) > 1:
							albumid = urlpair[1]
							album_save_dir = save_dir + filedesc + " - " + albumid + "/"
							ad = os.path.dirname(album_save_dir)
							if not os.path.exists(ad):
								print "MAKING DIRECTORY " + ad
								os.makedirs(ad)

						fileinURL += 1  # increment this counter


						if len(urllist) > 1:
							fullfilename = filedesc + " - {0:03d} - ".format(fileinURL) + filename
						else:
							fullfilename = filedesc + " - " + filename

						if len(urlpair) > 1:
							file_path = ad + "/" + fullfilename
						else:
							file_path = save_dir + fullfilename

						if os.path.isfile(file_path.encode(encoding="UTF-8")):
							print "** Skipping \"" + fullfilename + "\" - file already exists..."
						else:
							try:
								response = requests.get(url, stream=True)

								if response.headers.get('content-length') is None:
									total_length = 0
								else:
									total_length = int(response.headers.get('content-length'))

								print "TL: {}".format(total_length)
								print "RH: {}".format(response.headers['content-type'].split('/')[0])

								if total_length > 0 and total_length < MAX_SIZE and \
												response.headers['content-type'].split('/')[0] in ['video', 'image']:
									print "Saving to: \"{}\"".format(file_path.encode('utf-8'))
									with open(file_path, 'wb') as out_file:
										dl = 0
										total_length = int(total_length)
										for data in response.iter_content(chunk_size=1024):
											out_file.write(data)
											# Calculate & write progress bar to standard output.
											dl += len(data)
											done = int(30 * dl / total_length)
											sys.stdout.write("\r[%s>%s] %s / %s     " % (
											'=' * (done - 1), ' ' * (30 - done), humanfriendly.format_size(dl, True),
											humanfriendly.format_size(total_length, True)))
											sys.stdout.flush()
										print " "
									# remove response object from memory to prevent leak.
									del response
									saved += 1
								elif total_length >= MAX_SIZE:
									print "Skipped - File length {} is greater than maximum size of {} bytes...".format(
										total_length, MAX_SIZE)
									print url
								elif response.headers['content-type'].split('/')[0] not in ['video', 'image']:
									print "Skipped - response type not \"image\""
									print url
								else:
									print "Skipped - File is either not an image or 0 length..."
									print url

							except (IOError, UnicodeEncodeError) as e:
								print "Unable to retrieve this URL!"
								print url
								print e
								sleep(5)
								pass

						already_done.append(sub.id)
			if args.iterate:
				print "\n\n Statistics:"
				print "-----------"
				print parsed, "URLs parsed"
				# print parsed - len(already_done), "URLs skipped"
				print imgur_api_call_count, "calls made to IMGUR API."
				print saved, "images saved to directory."
				if args.iterate:
					print "\n\nSubreddit iteration complete. Sleeping for {} seconds. **YAWN**".format(sleeptime)
					sleep(args.sleep)

	except KeyboardInterrupt:
		print "\n\nCaught Keyboard Interrupt...ending gracefully."
	finally:
		print "\n\n Final Statistics:"
		print "-----------------"
		print parsed, "URLs parsed"
		# print parsed - len(already_done), "URLs skipped"
		print imgur_api_call_count, "calls made to IMGUR API."
		print saved, "images saved to directory."
		
		with open(save_dir +"__allurls.csv",'w') as outfile:
			line = 0
			for u in allurls:
				line += 1
				#print u
				outstring = u"\"{}\", {}, {}, \"{}\", {}\n".format(u[0], u[1], u[2], u[3], u[4]).encode('UTF-8')
				#print(outstring)
				outfile.write(outstring)
