twitter2mqtt
============


Simple python script that monitors twitter user accounts then publishes any new tweets to a mqtt topic. 

Before u run it I suggest you create a file in the directory where u are running it with the following twitterusername.tweetid for example, if you want to follow the username @bordgnon I would create a file called bordignon.tweetid and within that file I would put the last tweet id number the user sent for example, 434971444561596416

Has a bonus that if certain words are mentioned there get sent to another topic as well, maybe for alerts.

I run this script every 5minutes using crontab.
