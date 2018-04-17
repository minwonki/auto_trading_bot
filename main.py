# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from coins import Coin

import jinja2
import webapp2

import os
import urllib
import urllib2
import json
import logging
import re
import math
from time import sleep
from xcoin_api_client import *

api_key = "key";
api_secret = "secret";

api = XCoinAPI(api_key, api_secret);

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
# [END imports]

#coinKeys = ['BTC', 'ETH', 'DASH', 'LTC', 'ETC', 'XRP', 'BCH', 'XMR', 'ZEC', 'QTUM', 'BTG', 'EOS', 'ICX']
coinKeys = ['ETH', 'LTC', 'XRP', 'DASH', 'EOS']
hdr = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6)'}
noti_site = 'https://api.bithumb.com/public/ticker/'
cal_site = 'https://api.bithumb.com/public/ticker/'

openKey = 'opening_price'
highKey = 'max_price'
lowKey = 'min_price'
lastKey = 'closing_price'
dataKey = 'data'


    
class MainPage(webapp2.RequestHandler):
    def get(self):
        coins = Coin.query().order(-Coin.date).fetch(len(coinKeys))
        template_values = {
            'coins': coins,
        }
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))

class Notice(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        coins = Coin.query().order(-Coin.date).fetch(len(coinKeys))
        for coin in coins:
	  site = noti_site + coin.name
          req = urllib2.Request(site, headers=hdr)
          obj = json.load(urllib2.urlopen(req))

          if int(obj[dataKey][lastKey]) > coin.buy and coin.notice == False:
              noise_coins = Coin.query(Coin.name == str(coin.name)).order(-Coin.date).fetch(30)
              noise = 0.0
              for noise_coin in noise_coins:
                  noise = noise + noise_coin.noise
              msg = "Buy:" + coin.name + ", Price:" + str(coin.buy) + ", Noise:" + str(noise/len(noise_coins))
              enableCoins = self.getEnableCoins()
              units = api.selectUnits(coin.name, coin.volatility, enableCoins)
              coin.units = api.marketBuy(coin.name, units)
              coin.notice = True
              coin.put()
              logging.info(msg)
              #broadcast("Buy:" + coin.name + ",price:" + str(coin.buy) + ", Noise:" + str(noise/len(noise_coins)))

    def getEnableCoins(self):
        coins = Coin.query().order(-Coin.date).fetch(len(coinKeys))
        enableCoins = 0
        for coin in coins:
            if coin.notice == True:
               enableCoins = enableCoins + 1
        enableCoins = len(coins) - enableCoins
        logging.info(enableCoins)
        return enableCoins   

class Calculate(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        coins = Coin.query().order(-Coin.date).fetch(len(coinKeys))

        for coin in coins:
          if coin.notice:
	    site = noti_site + coin.name
            req = urllib2.Request(site, headers=hdr)
            body = json.load(urllib2.urlopen(req))
            obj = body
            msg = coin.name + " -> return:" + str((float(obj[dataKey][lastKey])/float(coin.buy) - 1)*100) + "%"
            #broadcase(msg)
            result = api.marketSell(coin.name, coin.units)
            logging.info(msg)
            sleep(15)

        for key in coinKeys:
	  site = cal_site + key
          req = urllib2.Request(site, headers=hdr)
          obj = json.load(urllib2.urlopen(req))
          openValue = float(obj[dataKey][openKey])
          lastValue = float(obj[dataKey][lastKey])
          highValue = float(obj[dataKey][highKey])
          lowValue  = float(obj[dataKey][lowKey])

          logging.info("key:"+key+",last:"+str(lastValue))
          buy = lastValue + 0.5 * (highValue - lowValue)
          noise = 1 - math.fabs(openValue - lastValue) / (highValue - lowValue)
          volatility = (highValue - lowValue)/lastValue * 100 
          coin = Coin(name=key, buy=int(buy), noise=float(noise), volatility = float(volatility), units = 0.01)
          coin.put()
          
class AddPage(webapp2.RequestHandler):
    def post(self):
        coin_name = self.request.get('name')
        coin_buy = self.request.get('buy')
        coin_noise = self.request.get('noise')
        coin_volatility = self.request.get('volatility')
        coin = Coin(name=coin_name, buy=int(coin_buy), noise=float(coin_noise), volatility = float(coin_volatility), units = 0.01)
        coin.put()
        self.redirect('/')

class DelPage(webapp2.RequestHandler):
    def post(self):
        urlsafe = self.request.get('urlsafe')
        coin_key = ndb.Key(urlsafe=urlsafe)
        coin = coin_key.get()
        coin.key.delete() 
        self.redirect('/')
       
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/task/add', AddPage),
    ('/task/delete', DelPage),
    ('/task/calc', Calculate),
    ('/task/notice', Notice),
], debug=True)
