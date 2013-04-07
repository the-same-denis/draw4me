#!/usr/bin/env python

# Copyright (C) 2012 Denis G. <the.same.denis@gmail.com>
# Licensed under a MIT license (http://opensource.org/licenses/MIT)

import re
import random
import requests
from HTMLParser import HTMLParser

lang = 'en'
users = [
#   {
#       'email':    'user@example.com',
#       'password': 'topsecret',
#       'soldier':  'MyGreatSoldier'
#   },
#   {
#       ...
#   },
#   ...
]

base_url = 'https://battlefield.play4free.com/' + lang + '/%s'
        
def drawCard(email, password, soldierName):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.22 (KHTML, like Gecko) Ubuntu Chromium/25.0.1364.160 Chrome/25.0.1364.160 Safari/537.22'
    }

    """
    initial request
    ================================================================================
    """
    s = requests.Session()
    s.headers = headers
    r = s.get(base_url % 'profile')
    print "Initial status: %s" % r.status_code
    if r.status_code != 200:
        print 'Stopping'
        return (None, 'Initial connection error')

    # get csrf token
    parser = CSRFParser()
    parser.feed(r.text)
    csrf_token = parser.csrf_token

    print 'Initial CSRF token: %s' % csrf_token
    if not csrf_token:
        print 'Stopping'
        return (None, 'Initial CSRF error')

    """
    login
    ================================================================================
    """
    r = s.post(base_url % 'user/login', data={
        '_csrf_token': csrf_token,
        'mail': email,
        'password': password
    })

    print 'Login status: %s' % r.status_code
    if r.status_code != 200:
        print 'Stopping'
        return (None, 'Login connection error')

    if 'magmaError' in r.content:
        print 'Login error. Stopping'
        return (None, 'Login error')

    parser = ProfileIDParser()
    parser.feed(r.text)
    profile_id = parser.profile_id

    print 'Profile ID: %s' % profile_id
    if not profile_id:
        print 'Stopping'
        return (None, 'Profile ID obtaining error')

    """
    get soldiers
    ================================================================================
    """
    r = s.get(base_url % '/profile/soldiers/' + profile_id)
    print 'Soldiers info status: %s' % r.status_code
    if r.status_code != 200:
        print 'Stopping'
        return (None, 'Soldiers connection error')

    soldiersData = r.json().get('data', None)
    if not soldiersData:
        print 'Can\'t obtain soldiers data. Stopping'
        return (None, 'Soldiers obtaining error')

    soldierId = None
    print 'Soldiers:'
    for soldier in soldiersData:
        print '  [kit: %s]:' % soldier['kit']
        if soldier['name'] == soldierName:
            soldierId = soldier['id']

        for key in soldier:
            print '    %s: %s' % (key, soldier[key])

        print ''

    if not soldierId:
        print 'Wrong soldier name. Stopping'
        return (None, 'Wrong soldier name')

    """
    get general draw info
    ================================================================================
    """
    r = s.get(base_url % '/draw/initializeDrawData')

    print 'Draw initialization status: %s' % r.status_code
    if r.status_code != 200:
        print 'Stopping'
        return (None, 'General draw info connection error')

    # check for available draws
    generalDrawData = r.json().get('data', None)
    if not generalDrawData:
        print 'Can\'t obtain general draw data. Stopping'
        return (None, 'General draw info obtaining error')

    drawCSRFToken = generalDrawData.get('_csrf_token', None)
    print 'Draw CSRF token: %s' % drawCSRFToken
    if not drawCSRFToken:
        print 'Stopping'
        return (None, 'Draw CSRF token error')

    drawsAvailable = generalDrawData.get('drawBalance', -1)
    print 'Draws available: %s' % drawsAvailable
    if drawsAvailable <= 0:
        print 'Stopping'
        return (None, 'No draws available')

    """
    draw a card
    ================================================================================
    """
    rand = random.random() * 1000
    card = random.randint(0, 5)
    r = s.get(base_url % '/draw/drawCard', params = {
        'personaId': soldierId,
        'card': card,
        '_csrd_token': drawCSRFToken,
        'r': rand
    })

    print 'Draw status: %s' % r.status_code
    if r.status_code != 200:
        print 'Stopping'
        return (None, 'Draw connection error')

    drawData = r.json().get('data', None)
    if not drawData:
        print 'No draw data. Stopping'
        return (None, 'Draw data error')

    for c in drawData['hand']:
        if c.get('prize', False):
            print 'Hooray! Your prize is:'
            print '================================================================================'
            print '    %s - %s' % (c['name'], c['duration'])
            print '================================================================================'

            return (c, None)

    return (None, 'Unknown error')

class CSRFParser(HTMLParser):
    csrf_token = None

    def handle_starttag(self, tag, attrs):
        if tag == 'input':
            dct = {}
            for name, value in attrs:
                dct[name] = value

            if dct.get('name', None) == '_csrf_token':
                self.csrf_token = dct.get('value', None)

class ProfileIDParser(HTMLParser):
    profile_id = None
    in_profile = False
    divs = 0

    def handle_starttag(self, tag, attrs):
        if not self.in_profile:
            if tag == 'div' and (u'class', u'main-soldier') in attrs:
                self.in_profile = True
        else:
            if tag == 'div':
                self.divs += 1

            if tag == 'a':
                for name, value in attrs:
                    if name == 'href':
                        r = re.match('^\/' + lang +'\/profile\/([0-9]+)$', value)
                        if r:
                            self.profile_id = r.group(1)

    def handle_endtag(self, tag):
        if self.in_profile:
            if tag == 'div':
                if self.divs <= 0:
                    self.in_profile = False
                else:
                    self.divs -= 1

if __name__ == '__main__':
    for user in users:
        print '--------------------------------------------------------------------------------'
        print ' Trying "%s" - "%s"...' % (user['email'], user['soldier'])
        print '--------------------------------------------------------------------------------'
        user['card'], user['error'] = drawCard(user['email'], user['password'], user['soldier'])

    print ''
    print '--------------------------------------------------------------------------------'
    print ' Summary:'
    print '--------------------------------------------------------------------------------'
    for user in users:
        if user['card']:
            print '{:>15}:   {} - {}'.format(
                user['soldier'],
                user['card']['name'],
                user['card']['duration']
            )
        else:
            print '{:>15}:   {}'.format(
                user['soldier'],
                user['error']
            )
    print '--------------------------------------------------------------------------------'

