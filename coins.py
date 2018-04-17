from google.appengine.ext import ndb

# Model
class Coin(ndb.Model):
    name = ndb.StringProperty()
    buy = ndb.IntegerProperty()
    notice = ndb.BooleanProperty(default=False)
    noise = ndb.FloatProperty()
    volatility = ndb.FloatProperty()
    units = ndb.FloatProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)


