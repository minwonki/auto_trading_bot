from google.appengine.api import urlfetch
from google.appengine.ext import ndb

import webapp2

import os
import urllib
import urllib2
import json
import logging
import re
import math

TOKEN = '416103267:AAGB-jJmV5R81WXcMnTPWCrbv6XvcE7KO28'
BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'
CMD_START     = '/start'
CMD_STOP      = '/stop'
CMD_HELP      = '/help'
CMD_BROADCAST = '/broadcast'
USAGE = u"""[usage] usage
/start - (bot start)
/stop  - (bot stop)
/help  - (show help)
"""
MSG_START = u'bot start.'
MSG_STOP  = u'bot stop.'
CUSTOM_KEYBOARD = [
        [CMD_START],
        [CMD_STOP],
        [CMD_HELP],
        ]

class EnableStatus(ndb.Model):
    enabled = ndb.BooleanProperty(required=True, indexed=True, default=False,)

def set_enabled(chat_id, enabled):
    u"""set_enabled: bot start/stop status change
    chat_id:    (integer) bot start/stop chatting id
    enabled:    (boolean) bot start/stop status
    """
    es = EnableStatus.get_or_insert(str(chat_id))
    es.enabled = enabled
    es.put()

def get_enabled(chat_id):
    u"""get_enabled: return bot start/stop
    return: (boolean)
    """
    es = EnableStatus.get_by_id(str(chat_id))
    if es:
        return es.enabled
    return False

def get_enabled_chats():
    u"""get_enabled: return bot chat list
    return: (list of EnableStatus)
    """
    query = EnableStatus.query(EnableStatus.enabled == True)
    return query.fetch()

def send_msg(chat_id, text, reply_to=None, no_preview=True, keyboard=None):
    u"""send_msg: send message
    chat_id:    (integer) message chat ID
    text:       (string)  message context
    reply_to:   (integer) ~reply
    no_preview: (boolean) URL no preview
    keyboard:   (list)    set custom keyboard
    """
    params = {
        'chat_id': str(chat_id),
        'text': text.encode('utf-8'),
        }
    if reply_to:
        params['reply_to_message_id'] = reply_to
    if no_preview:
        params['disable_web_page_preview'] = no_preview
    if keyboard:
        reply_markup = json.dumps({
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': False,
            'selective': (reply_to != None),
            })
        params['reply_markup'] = reply_markup
    try:
        urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode(params)).read()
    except Exception as e:
        logging.exception(e)

def testCall(text):
    logging.warning(text)

def broadcast(text):
    u"""broadcast: broadcast message
    text:       (string)  message context
    """
    for chat in get_enabled_chats():
        send_msg(chat.key.string_id(), text)

def cmd_start(chat_id):
    u"""cmd_start: cmd_start
    chat_id: (integer) chatting ID
    """
    set_enabled(chat_id, True)
    send_msg(chat_id, MSG_START, keyboard=CUSTOM_KEYBOARD)

def cmd_stop(chat_id):
    u"""cmd_stop: cmd_stop
    chat_id: (integer) chatting ID
    """
    set_enabled(chat_id, False)
    send_msg(chat_id, MSG_STOP)

def cmd_help(chat_id):
    u"""cmd_help: cmd_help
    chat_id: (integer) chatting ID
    """
    send_msg(chat_id, USAGE, keyboard=CUSTOM_KEYBOARD)

def cmd_broadcast(chat_id, text):
    u"""cmd_broadcast: cmd_broadcast
    chat_id: (integer) chat ID
    text:    (string)  text
    """
    send_msg(chat_id, u'broadcast message', keyboard=CUSTOM_KEYBOARD)
    broadcast(text)

def cmd_echo(chat_id, text, reply_to):
    u"""cmd_echo: cmd_echo
    chat_id:  (integer) chat ID
    text:     (string)  text
    reply_to: (integer) replay ID
    """
    send_msg(chat_id, text, reply_to=reply_to)

def process_cmds(msg):
    u"""processc_cmd
    chat_id: (integer) chat ID
    text:    (string)  text
    """
    msg_id = msg['message_id']
    chat_id = msg['chat']['id']
    text = msg.get('text')
    if (not text):
        return
    if CMD_START == text:
        cmd_start(chat_id)
        return
    if (not get_enabled(chat_id)):
        return
    if CMD_STOP == text:
        cmd_stop(chat_id)
        return
    if CMD_HELP == text:
        cmd_help(chat_id)
        return
    cmd_broadcast_match = re.match('^' + CMD_BROADCAST + ' (.*)', text)
    if cmd_broadcast_match:
        cmd_broadcast(chat_id, cmd_broadcast_match.group(1))
        return
    cmd_echo(chat_id, text, reply_to=msg_id)
    return

# /me request
class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe'))))

# /updates request
class GetUpdatesHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getUpdates'))))

# /set-webhook request
class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        url = self.request.get('url')
        if url:
            self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'setWebhook', urllib.urlencode({'url': url})))))

# /webhook
class WebhookHandler(webapp2.RequestHandler):
    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        self.response.write(json.dumps(body))
        logging.warning(body['message'])
        process_cmds(body['message'])

app = webapp2.WSGIApplication([
    ('/telegram/me', MeHandler),
    ('/telegram/updates', GetUpdatesHandler),
    ('/telegram/set-webhook', SetWebhookHandler),
    ('/telegram/webhook', WebhookHandler),
], debug=True)

