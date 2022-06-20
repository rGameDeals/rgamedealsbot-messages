import sqlite3
import time
import praw
import prawcore
import requests
import logging
import datetime
import dateparser
import os
import re
import yaml
import pymysql

os.environ['TZ'] = 'UTC'

responded = 0
footer = ""

con = pymysql.connect(
    host=os.environ['MYSQL_HOST'],
    user=os.environ['MYSQL_USER'],
    passwd=os.environ['MYSQL_PASS'],
    db=os.environ['MYSQL_DB']
)

REDDIT_CID=os.environ['REDDIT_CID']
REDDIT_SECRET=os.environ['REDDIT_SECRET']
REDDIT_USER = os.environ['REDDIT_USER']
REDDIT_PASS = os.environ['REDDIT_PASS']
REDDIT_SUBREDDIT= os.environ['REDDIT_SUBREDDIT']
AGENT="python:rGameDeals-messages:2.0b (by dgc1980)"
AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36"

reddit = praw.Reddit(client_id=REDDIT_CID,
                     client_secret=REDDIT_SECRET,
                     password=REDDIT_PASS,
                     user_agent=AGENT,
                     username=REDDIT_USER)
subreddit = reddit.subreddit(REDDIT_SUBREDDIT)
wikiconfig=[]
apppath='/storage/'

#logging.basicConfig(level=logging.INFO,
#                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
#                    datefmt='%m-%d %H:%M')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

def checkuser(username):
  commentcount = 0
  commenttime = 0
  currenttime = str(int(time.time()))
  u = reddit.redditor(username)
  try:
    test = u.comment_karma
  except:
    return True
  if u == "JoyBuggy":
    return False
  if int(u.created_utc) > int(time.time()) - (86400 * wikiconfig['newuserdays']):
    return True

  if wikiconfig['userkarmatype'] == "comment":
    karma = reddit.redditor(u.name).comment_karma
  elif wikiconfig['userkarmatype'] == "link":
    karma = reddit.redditor(u.name).link_karma
  elif wikiconfig['userkarmatype'] == "combined":
    karma = reddit.redditor(u.name).link_karma + reddit.redditor(u.name).comment_karma
  else:
    karma = 9999999
  if karma <= wikiconfig['userkarma']:
    return True
  for comment in  reddit.redditor(username).comments.new(limit=10) :
    commenttime += ( int(currenttime) - int(comment.created_utc) )
    commentcount += 1
    if comment.subreddit.display_name.lower() in wikiconfig['suspectsubs']:
      return True
  #for submission in  reddit.redditor(username).submissions.new(limit=10) :
  #  commenttime += ( int(currenttime) - int(submission.created_utc) )
  #  commentcount += 1
  #  if submission.subreddit.display_name.lower() in Config.SuspectSubs:
  #    return True
  commentdays = ( (commenttime / commentcount) / 86400 )
  #if commentdays >= Config.HistoryDays:
  #  return True
  return False

logging.info("Monitoring inbox...")
while True:
    try:
        for msg in reddit.inbox.stream():
            con.ping(reconnect=True)
            expired = False
            oops = False
            setsched = False
            responded = 0

            wikiconfig = yaml.safe_load( reddit.subreddit('gamedeals').wiki['gamedealsbot-config'].content_md )

            # checks if bot has already replied (good if script has to restart)
            try:
                if isinstance(msg, praw.models.Comment):
                    for comment in msg.refresh().replies:
                        try:
                            if comment.author.name == REDDIT_USER:
                                responded = 0
                        except AttributeError:
                            responded = 0
                if msg.author is not None:
                    logging.info("Message recieved from " + msg.author.name + ": " + msg.body)
                    logging.info("* " + msg.submission.id + ": " + msg.submission.title)
            except AttributeError:
                logging.info("error checking comment by: " + msg.author.name)
            try:
                if responded == 0:
                    if isinstance(msg, praw.models.Comment) and msg.author:
                        text = msg.body.lower()
                        u = msg.author
                        ismod = False
                        if msg.author:
                          if msg.author.name in ['dgc1980','SquareWheel','smeggysmeg','smeggysmeg','ronin19','treblah3','caninehere','caninehere','oxygENigma','wayward_wanderer']:
                            ismod = True
                        usertest = checkuser(msg.author.name)
                        try:
                          #print(wikiconfig)
                          extrig = wikiconfig['expired-trigger']
                          if text.index( extrig ) > -1:
                            expired = True
                        except ValueError:
                            pass
                        try:
                          if text.index(wikiconfig['available-trigger']) > -1:
                            oops = True
                        except ValueError:
                            pass
                        try:
                          if text.index(wikiconfig['schedule-trigger']) > -1:
                           if msg.author.name == msg.submission.author.name or ismod and wikiconfig['schedule-by'] == 'submitter':
                             setsched = True
                           elif ismod and wikiconfig['schedule-by'] == 'mods':
                             setsched = True
                           elif wikiconfig['schedule-by'] == 'anyone':
                             setsched = True
                        except ValueError:
                             pass

                        if str(msg.submission.subreddit) not in REDDIT_SUBREDDIT:
                          setsched = False
                          oops = False
                          expired = False
                          logging.info("abuse https://redd.id/" + msg.submission.id + " by: "+msg.author.name)
                          msg.mark_read()

                        if oops:
                          if not msg.submission.spoiler:
                              alreadyavailablereply = wikiconfig['already-available']
                              alreadyavailablereply = alreadyavailablereply.replace('{{expired trigger}}',wikiconfig['expired-trigger'])
                              alreadyavailablereply = alreadyavailablereply.replace('{{available trigger}}',wikiconfig['available-trigger'])
                              alreadyavailablereply = alreadyavailablereply.replace('{{author}}', msg.author.name)

                              myreply = msg.reply( alreadyavailablereply )
                              myreply.mod.distinguish(how='yes')

                              msg.mark_read()
                              logging.info("already available... responded to: " + msg.author.name)
                          else:
                              msg.submission.mod.unspoiler()
                              msg.submission.mod.flair(text='')
                              logging.info("unflairing " + msg.submission.title + "requested by: "+msg.author.name)

                              con = pymysql.connect( host=os.environ['MYSQL_HOST'], user=os.environ['MYSQL_USER'], passwd=os.environ['MYSQL_PASS'], db=os.environ['MYSQL_DB'] )
                              cursorObj = con.cursor()
                              cursorObj.execute('SELECT * FROM flairs WHERE postid = "'+msg.submission.id+'"')
                              rows = cursorObj.fetchall()
                              msg.mark_read()
                              if len(rows) != 0 and rows[0][2] != "Expired":
                                try:
                                  cursorObj.execute('DELETE FROM flairs WHERE postid = "'+msg.submission.id+'"')
                                  con.commit()
                                except:
                                  pass
                                msg.submission.mod.flair(text=rows[0][2], css_class='')

                              availablereply = wikiconfig['available-reply']
                              availablereply = availablereply.replace('{{expired trigger}}',wikiconfig['expired-trigger'])
                              availablereply = availablereply.replace('{{available trigger}}',wikiconfig['available-trigger'])
                              availablereply = availablereply.replace('{{author}}', msg.author.name)

                              myreply = msg.reply( availablereply )
                              myreply.mod.distinguish(how='yes')
                              msg.mark_read()

                        elif setsched:
                          #try:
                          if re.search("(\d{1,2}:\d{2} \d{2}\/\d{2}\/\d{4})", text) is not None:
                            match1 = re.search("(\d{1,2}:\d{2} \d{2}\/\d{2}\/\d{4})", text)
                            tm = datetime.datetime.strptime(match1.group(1), "%H:%M %d/%m/%Y")
                            tm2 = time.mktime(tm.timetuple())
                            con = pymysql.connect( host=os.environ['MYSQL_HOST'], user=os.environ['MYSQL_USER'], passwd=os.environ['MYSQL_PASS'], db=os.environ['MYSQL_DB'] )

                            cursorObj = con.cursor()
                            cursorObj.execute('DELETE from schedules WHERE postid = "' + msg.submission.id + '"')
                            cursorObj.execute('INSERT into schedules(postid, schedtime) values(%s,%s)',(msg.submission.id,tm2) )
                            con.commit()
                            logging.info("setting up schedule: " + msg.author.name + "for https://redd.it/" + msg.submission.id + " at " + str(tm.strftime('%Y-%m-%d %H:%M:%S'))  )
                            schedulereply = wikiconfig['schedule-message']
                            schedulereply = schedulereply.replace('{{expired trigger}}',wikiconfig['expired-trigger'])
                            schedulereply = schedulereply.replace('{{available trigger}}',wikiconfig['available-trigger'])
                            schedulereply = schedulereply.replace('{{author}}', msg.author.name)
                            schedulereply = schedulereply.replace('{{time}}', str(tm.strftime('%Y-%m-%d %H:%M:%S'))   )

                            myreply = msg.reply( schedulereply )
                            myreply.mod.distinguish(how='yes')
                            msg.mark_read()
                          else:
                            match1 = re.search(wikiconfig['schedule-trigger'] + "\ ([\w\:\ \-\+]+)", text)
                            #tm = time.mktime(datetime.datetime.strptime(match1.group(1), "%H:%M %d/%m/%Y").timetuple())
                            print( match1 )
                            tm = dateparser.parse( match1.group(1), settings={'PREFER_DATES_FROM': 'future', 'TIMEZONE': 'UTC', 'TO_TIMEZONE': 'UTC'} )
                            tm2 = time.mktime( tm.timetuple() )
                            con = pymysql.connect( host=os.environ['MYSQL_HOST'], user=os.environ['MYSQL_USER'], passwd=os.environ['MYSQL_PASS'], db=os.environ['MYSQL_DB'] )
                            cursorObj = con.cursor()
                            cursorObj.execute('DELETE from schedules WHERE postid = "' + msg.submission.id + '"')
                            cursorObj.execute('INSERT into schedules(postid, schedtime) values(%s,%s)',(msg.submission.id,tm2) )
                            con.commit()
                            logging.info("setting up schedule: " + msg.author.name + "for https://redd.it/" + msg.submission.id + " at " + str(tm.strftime('%Y-%m-%d %H:%M:%S'))  )
                            schedulereply = wikiconfig['schedule-message']
                            schedulereply = schedulereply.replace('{{expired trigger}}',wikiconfig['expired-trigger'])
                            schedulereply = schedulereply.replace('{{available trigger}}',wikiconfig['available-trigger'])
                            schedulereply = schedulereply.replace('{{author}}', msg.author.name)
                            schedulereply = schedulereply.replace('{{time}}', str(tm.strftime('%Y-%m-%d %H:%M:%S'))   )

                            myreply = msg.reply( schedulereply )
                            myreply.mod.distinguish(how='yes')
                            msg.mark_read()
                          #except:
                          #  pass
                          msg.mark_read()
                        elif expired and not usertest:
                            if msg.submission.spoiler:
                                alreadyexpired = wikiconfig['already-expired-reply']
                                alreadyexpired = alreadyexpired.replace('{{expired trigger}}',wikiconfig['expired-trigger'])
                                alreadyexpired = alreadyexpired.replace('{{available trigger}}',wikiconfig['available-trigger'])
                                alreadyexpired = alreadyexpired.replace('{{author}}', msg.author.name)

                                myreply = msg.reply(alreadyexpired)
                                myreply.mod.distinguish(how='yes')
                                msg.mark_read()
                                logging.info("already expired... responded to: " + msg.author.name)
                            else:
                                title_url = msg.submission.url
                                con = pymysql.connect( host=os.environ['MYSQL_HOST'], user=os.environ['MYSQL_USER'], passwd=os.environ['MYSQL_PASS'], db=os.environ['MYSQL_DB'] )
                                cursorObj = con.cursor()
                                if msg.submission.link_flair_text is not None:
                                  if msg.submission.link_flair_text != "Expired":
                                    flairtime = str( int(time.time()))
                                    cursorObj.execute('INSERT INTO flairs(postid, flairtext, timeset) VALUES(%s,%s,%s)', (msg.submission.id,msg.submission.link_flair_text,flairtime ) )
                                    con.commit()
                                msg.submission.mod.spoiler()
                                msg.submission.mod.flair(text='Expired', css_class='expired')
                                logging.info("flairing... responded to: " + msg.author.name)

                                expiredmsg = wikiconfig['expired-reply']
                                expiredmsg = expiredmsg.replace('{{expired trigger}}',wikiconfig['expired-trigger'])
                                expiredmsg = expiredmsg.replace('{{available trigger}}',wikiconfig['available-trigger'])
                                expiredmsg = expiredmsg.replace('{{author}}', msg.author.name)

                                myreply = msg.reply(expiredmsg)
                                myreply.mod.distinguish(how='yes')
                                msg.mark_read()
                        elif expired and usertest:
                          msg.report('possible bot abuse')
                          logging.info("maybe abuse from user?: https://reddit.com/u/" + msg.author.name + " on post https://reddit.com/" + msg.submission.id )
                          msg.mark_read()
                        elif oops and usertest:
                          msg.report('possible bot abuse')
                          logging.info("maybe abuse from user?: https://reddit.com/u/" + msg.author.name + " on post https://reddit.com/" + msg.submission.id )
                          msg.mark_read()
                        elif usertest:
                          msg.mark_read()

            except AttributeError:
                raise
                logging.info("error checking comment by: " + msg.author.name)
    except (prawcore.exceptions.RequestException, prawcore.exceptions.ResponseException):
        logging.info ("Error connecting to reddit servers. Retrying in 1 minute...")
        time.sleep(60)

    except praw.exceptions.APIException:
        logging.info ("rate limited, wait 5 seconds")
        time.sleep(5)
