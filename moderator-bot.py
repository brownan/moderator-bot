#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  moderator-bot.py
#  
#  Copyright 2012 Zach McCullough <nosrepa@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

import json
import urllib.request
import time
import re
import signal
import sys
from urllib.parse import urlencode
import http.cookiejar
from credentials import *

def p(data):
        print(time.strftime('\033[2K[\033[31m%y\033[39m/\033[31m%m\033[39m/\033[31m%d\033[39m]'
                             '[\033[31m%H\033[39m:\033[31m%M\033[39m:\033[31m%S\033[39m] ') + data)

def sigint_handler(signal, frame):
    '''Handles ^c'''
    p('Recieved SIGINT! Exiting...')
    sys.exit(0)


class Reddit(object):
    """Base class to perform the tasks of a redditor."""
    
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.cj = http.cookiejar.CookieJar() 
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.opener.addheaders = [('User-agent', 'prune_bans.py')]
        self._login()
    
    def _request(self, url, body=None):
        if body is not None:
            body = urlencode(body).encode('utf-8')
        with self.opener.open(url, data=body) as w:
            time.sleep(2)
            return json.loads(w.read().decode('utf-8'))
    
    def _login(self):
        p("Logging in as {}.".format(self.username))
        body = {'user' :self.username, 'passwd' : self.password, 'api_type' : 'json'}
        resp = self._request('https://www.reddit.com/api/login', body)
        self.modhash = resp['json']['data']['modhash']
    
    def post(self, url, body):
        """Sends a POST to the url and returns the json as a dict."""
        
        if 'api_type' not in body: body['api_type'] = 'json'
        
        body['uh'] = self.modhash
        
        return self._request(url, body)

    
    def get(self, url):
        if '.json' not in url: url += '.json'
        return self._request(url)

def main():
    suggestion = re.compile(r'''(?:^|\s|\[|<|\(|{)?(sug*estion|idea)(?:$|\s|\]|>|\)|:|})''', re.I)
    fixed = re.compile(r'''[\[<\({]?(fixed)(?:$|\s|\]|>|\)|:|})''', re.I)
    sleep_time = 60 * 5
    template_1 = ("This submission has been removed automatically.  According to our [subreddit rul"
                  "es](/r/{sub}/faq), suggestion posts must be self-posts only.  If you feel this w"
                  "as in error, please [message the moderators](/message/compose/?to=/r/{sub}&subje"
                  "ct=Removal%20Dispute).".format(sub=SUBREDDIT))
    template_2 = ("This submission has been removed automatically.  According to our [subreddit rul"
                  "es](/r/{sub}/faq), suggestion posts must have a description along with them, whi"
                  "ch is something you cannot convey with only a title.  If you feel this was in er"
                  "ror, please [message the moderators](/message/compose/?to={sub}&subject=Removal%"
                  "20Dispute).".format(sub=SUBREDDIT))
    template_3 = ("This submission has been removed automatically.  According to our [subreddit rul"
                  "es](/r/{sub}/faq), [Fixed] posts are not allowed.  If you feel this was in error"
                  ", please [message the moderators](/message/compose/?to={sub}&subject=Removal%20D"
                  "ipute).".format(sub=SUBREDDIT))
    r = Reddit(USERNAME, PASSWORD)
    p('Started monitoring submissions on /r/{}.'.format(SUBREDDIT))
    while True:
        p('Getting feed...')
        feed = r.get('http://reddit.com/r/{}/new/.json?sort=new'.format(SUBREDDIT))
        for f in feed['data']['children']:
            f = f['data']
            if suggestion.match(f['title']):
                if f['domain'] != 'self.{}'.format(SUBREDDIT):
                    p('Found [Suggestion] submission that is not a self post, removing.')
                    remove_body = {'spam' : 'False', 'r' : SUBREDDIT,
                                   'id' : f['name'], 'executed' : 'removed'}
                    comment_body = {'thing_id' : f['name'], 'text' : template_1}
                    r.post('http://www.reddit.com/api/remove', remove_body)
                    submission = r.post('http://www.reddit.com/api/comment',
                                        comment_body)['json']['data']['things'][0]['data']['id']
                    distinguish_body = {'id' : submission, 'executed' : 'distinguishing...'}
                    r.post('http://www.reddit.com/api/distinguish/yes', distinguish_body)
                elif not f['selftext']:
                    p('Found [Suggestion] submission that has no self-text, removing.')
                    remove_body = {'spam' : 'False', 'r' : SUBREDDIT,
                                   'id' : f['name'], 'executed' : 'removed'}
                    comment_body = {'thing_id' : f['name'], 'text' : template_2}
                    r.post('http://www.reddit.com/api/remove', remove_body)
                    submission = r.post('http://www.reddit.com/api/comment',
                                        comment_body)['json']['data']['things'][0]['data']['id']
                    distinguish_body = {'id' : submission, 'executed' : 'distinguishing...'}
                    r.post('http://www.reddit.com/api/distinguish/yes', distinguish_body)
            elif fixed.match(f['title']):
                p('Found [fixed] post, removing.')
                remove_body = {'spam' : 'False', 'r' : SUBREDDIT,
                               'id' : f['name'], 'executed' : 'removed'}
                comment_body = {'thing_id' : f['name'], 'text' : template_3}
                r.post('http://www.reddit.com/api/remove', remove_body)
                submission = r.post('http://www.reddit.com/api/comment',
                                    comment_body)['json']['data']['things'][0]['data']['id']
                distinguish_body = {'id' : submission, 'executed' : 'distinguishing...'}
                r.post('http://www.reddit.com/api/distinguish/yes', distinguish_body)
        p('Sleeping for {} seconds.'.format(sleep_time))
        time.sleep(sleep_time)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, sigint_handler)
    main()

