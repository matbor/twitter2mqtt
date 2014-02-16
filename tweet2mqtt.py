#!/usr/bin/python
# Twitter2MQTT Topic
# by Matthew Bordignon October 2013  @bordignon
#
# Checks listed twitter accounts for new tweets and if any will publish
# them to a MQTT topic. i have mine setup with crontab every 5mins.
#
# Original twitter Code modified from: Tim Bueno
# https://github.com/timbueno/SimpleTweetArchiver
#

import mosquitto #using ver (81f1010 2013-10-04)
import tweepy 
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
import os
import sys
#for logging
import traceback
import time
import datetime
try:
    import json
except ImportError:
    import simplejson as json

#CHANGE SETTINGS BELOW HERE
pidfile = "/tmp/tweet2mqtt.pid"
# The consumer keys can be found on your application's Details page located at https://dev.twitter.com/apps (under "OAuth settings")
consumer_key="xxxxxxx"
consumer_secret="xxxxxxx"
# The access tokens can be found on your applications's Details page located at https://dev.twitter.com/apps (located under "Your access token")
access_token="xxxxxx"
access_token_secret="xxxxxx"
#mqtt settings
broker = "mqtt.localdomain" #mqtt broker host
broker_port = 1883 #mqtt broker port
topic_info = "/tweet/info 
topic_alert = "/tweet/alert"
willtopic = "/lwt/tweet2mqtt" #last will and testament (will_set) topic location
# TWITTER ACCOUNTS TO CHECK
theUserName = ['CFA_Updates',
               'IncidentAlertDR',
               'SP_AusNet',
               '3aw693']
#keyword alerts, send to topic_alert
keyword_alert = ['sassafras',
                 'kallista',
                 'ferny',
                 'lysterfield',
                 'tecoma',
                 'ferntree',
                 'belgrave',
                 'upwey',
                 'dandenong ranges',
                 'mount dandenong']
#used for display a icon for the twitter account
lookup_image = {'CFA_Updates': 'special://masterprofile/Thumbnails/cfa.png', 
                'IncidentAlertDR': 'special://masterprofile/Thumbnails/cfa.png', 
                'SP_AusNet':'special://masterprofile/Thumbnails/spausnet.png',
                '3aw693':'special://masterprofile/Thumbnails/3aw693.png'}
#CHANGE SETTINGS ABOVE HERE

# Create Twitter API Object
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

def on_connect(mosq, obj, rc):
    print("-- MQTT Broker Connected - rc: "+str(rc))
    mqttc.publish(willtopic, payload="online", qos=0, retain=True)
    
def on_disconnect(mosq, userdata, rc): 
    print("-- MQTT broker Disconnected from broker- rc: "+str(rc))

def on_message(mosq, obj, msg):
    print("-- MQTT "+msg.topic+" "+str(msg.qos)+" "+str(msg.payload))

def on_publish(mosq, obj, mid):
    print("-- MQTT - mid: "+str(mid))

def on_subscribe(mosq, obj, mid, granted_qos):
    print("-- MQTT - Subscribed: "+str(mid)+" "+str(granted_qos))

def on_log(mosq, obj, level, string):
    print("-- MQTT"+string)

#this will send notifications to prowl and xbmc
def sendnotification(msgsub, msgtxt): #subject and main text
    # my setup has two levels ALERT and INFO, so anyword in the keyword_alert list will be a classfied as an alert 
    # and publish to two mqtt topics, alert and info. Info only publish messages publish just to the info topic.
    # {"lvl":"1","sub":"xxxxxx","txt":"xxxxxx","img":"xxx","del":"10000"}
    print ("-- @"+msgsub.encode('utf8') +" - "+ msgtxt.encode('utf8'))
    
    msgjson = json.dumps(dict(
                                        lvl = '1',
                                        sub = msgsub,
                                        txt = msgtxt.encode('utf8'),
                                        delay = '20000',
                                        img = lookup_image[msgsub]
                                    ))
    print msgjson
    
    if any(word in msgtxt.lower() for word in keyword_alert): #checking for keyword in keyword_alert list
        print "-- ALERT KEYWORD FOUND"
        mqttc.publish(topic_alert, payload=msgjson, qos=0, retain=False) #publish to ALERT topic
    mqttc.publish(topic_info, payload=msgjson, qos=0, retain=True)    #publish to INFO topic


def main_loop():
    #clear the screen
    #display current date and time
    now = datetime.datetime.now()
    # step though all the twitter acoounts.
    for z in theUserName:
        print " "
        print "************"
        print "-- checking Twitter User : @" +z +" "+now.strftime("%Y-%m-%d %H:%M")
        #tweetid file
        idFile = z + '.tweetid'
        pwd = os.getcwd() #use the current working directory
        pwd = pwd.strip('"\n')
        idFile = os.path.join(pwd, idFile) # join dir and filename
        print "-- TweetIDFile : " +idFile
        
        # helpful variables
        status_list = [] # Create empty list to hold statuses
        cur_status_count = 0 # set current status count to zero

        if os.path.exists(idFile):
            # Get most recent tweet id from file
            f = open(idFile, 'r')
            idValue = f.read()
            f.close()
            idValue = int(idValue)
            print "-- tweetID file found! "
            print "-- tweetID read from file " +str(idValue)
            print "-- checking to see if there is any new tweets... "
            
            # Get first page of unarchived statuses
            #30 jan added the below try/except to see if i get anymore errors.
            #http://stackoverflow.com/questions/2083987/how-to-retry-after-exception-in-python
            while True: 
                try:
                    statuses = api.user_timeline(count=200, include_rts=True, since_id=idValue, screen_name=z) #changed from 200 to 50
                except tweepy.error.TweepError:
                    print "#### ERROR getting tweet ####"
                    print "-- We will pause for 60 seconds before trying again"
                    sendnotification("tweet2mqtt",("Error getting tweet for : @" +z))
                    time.sleep(60)
                    continue
                break
            # Get User information for display
            if statuses != []:
                theUser = statuses[0].author
                total_status_count = theUser.statuses_count

            while statuses != []:
                cur_status_count = cur_status_count + len(statuses)
                for status in statuses:
                    status_list.append(status)
                    
                theMaxId = statuses[-1].id
                theMaxId = theMaxId - 1
                # Get next page of unarchived statuses
                statuses = api.user_timeline(count=200, include_rts=True, since_id=idValue, max_id=theMaxId, screen_name=z) #changed from 200 to 50
                
        else:
            print "-- No tweetID file found"
            print "-- Please create a new archive file called : " +idFile
            print ""
            sendnotification("tweet2mqtt",("No tweetid file found for @"+z))
            time.sleep(20)

        # Write most recent tweet id to file for reuse
        if status_list != []:
            for status in reversed(status_list):
                sendnotification(z,status.text)
            # Write most recent tweet id to file
            print "-- saving last tweet id to file. ID:"+str(status_list[0].id)
            f = open(idFile, 'w')
            f.write(str(status_list[0].id))
            f.close()
        print "-- We had found " + str(len(status_list)) + " more tweets since you last run"
        print "-- Finished with account : @" + z
        time.sleep(2) #just a small delay so i can read the screen!
    
if __name__ == '__main__':

    pid = str(os.getpid())
    if os.path.isfile(pidfile):
        print "%s already exists, exiting" % pidfile
        sys.exit()
    else:
        file(pidfile, 'w').write(pid)
    
    try:
        mqttc = mosquitto.Mosquitto()
        mqttc.on_message = on_message
        mqttc.on_connect = on_connect
        mqttc.on_publish = on_publish
        mqttc.on_subscribe = on_subscribe
        #mqttc.on_log = on_log # Uncomment to enable debug messages
        mqttc.will_set(willtopic, payload="offline", qos=0, retain=True)
        mqttc.connect(broker, broker_port, 60)
        mqttc.loop_start()
        
        main_loop()
        
        mqttc.loop_stop()
        mqttc.disconnect()
        os.unlink(pidfile)
             
    except:
        print >> sys.stderr, '\nExiting by user request.\n'
        type, value, tb = sys.exc_info()
        traceback.print_exc()
        last_frame = lambda tb=tb: last_frame(tb.tb_next) if tb.tb_next else tb
        frame = last_frame().tb_frame
        ns = dict(frame.f_globals)
        ns.update(frame.f_locals)
        #code.interact(local=ns)
        traceback.print_exc(file=open("errlog.txt","w"))
        os.unlink(pidfile)
        sys.exit(0)
