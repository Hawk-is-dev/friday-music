import httpx
# Monkeypatch httpx to fix youtube-search-python compatibility (proxies -> proxy)
_original_init = httpx.AsyncClient.__init__
def _new_init(self, *args, **kwargs):
    if "proxies" in kwargs:
        kwargs["proxy"] = kwargs.pop("proxies")
    _original_init(self, *args, **kwargs)
httpx.AsyncClient.__init__ = _new_init

# Monkeypatch youtubesearchpython to prevent crash when channel id or video id is None
try:
    from youtubesearchpython.handlers.componenthandler import ComponentHandler, videoElementKey
    def _patched_getVideoComponent(self, element: dict, shelfTitle: str = None) -> dict:
        video = element[videoElementKey]
        component = {
            'type':                           'video',
            'id':                              self._getValue(video, ['videoId']),
            'title':                           self._getValue(video, ['title', 'runs', 0, 'text']),
            'publishedTime':                   self._getValue(video, ['publishedTimeText', 'simpleText']),
            'duration':                        self._getValue(video, ['lengthText', 'simpleText']),
            'viewCount': {
                'text':                        self._getValue(video, ['viewCountText', 'simpleText']),
                'short':                       self._getValue(video, ['shortViewCountText', 'simpleText']),
            },
            'thumbnails':                      self._getValue(video, ['thumbnail', 'thumbnails']),
            'richThumbnail':                   self._getValue(video, ['richThumbnail', 'movingThumbnailRenderer', 'movingThumbnailDetails', 'thumbnails', 0]),
            'descriptionSnippet':              self._getValue(video, ['detailedMetadataSnippets', 0, 'snippetText', 'runs']),
            'channel': {
                'name':                        self._getValue(video, ['ownerText', 'runs', 0, 'text']),
                'id':                          self._getValue(video, ['ownerText', 'runs', 0, 'navigationEndpoint', 'browseEndpoint', 'browseId']),
                'thumbnails':                  self._getValue(video, ['channelThumbnailSupportedRenderers', 'channelThumbnailWithLinkRenderer', 'thumbnail', 'thumbnails']),
            },
            'accessibility': {
                'title':                       self._getValue(video, ['title', 'accessibility', 'accessibilityData', 'label']),
                'duration':                    self._getValue(video, ['lengthText', 'accessibility', 'accessibilityData', 'label']),
            },
        }
        component['link'] = 'https://www.youtube.com/watch?v=' + (component['id'] or '')
        component['channel']['link'] = 'https://www.youtube.com/channel/' + (component['channel']['id'] or '')
        component['shelfTitle'] = shelfTitle
        return component
    ComponentHandler._getVideoComponent = _patched_getVideoComponent
except Exception:
    pass


from SANYAMUSIC.core.bot import SANYA
from SANYAMUSIC.core.dir import dirr
from SANYAMUSIC.core.git import git
from SANYAMUSIC.core.userbot import Userbot
from SANYAMUSIC.misc import dbb, heroku
from SafoneAPI import SafoneAPI
from .logging import LOGGER

dirr()
# git() # to enable/disable auto update via upstream repo 
dbb()
heroku()

# These will be initialized in __main__.py after the loop starts
# These will be initialized lazily to avoid loop mismatch
_app = None
_userbot = None
_api = None

def get_app():
    global _app
    if _app is None:
        _app = SANYA()
    return _app

def get_userbot():
    global _userbot
    if _userbot is None:
        _userbot = Userbot()
    return _userbot

def get_api():
    global _api
    if _api is None:
        _api = SafoneAPI()
    return _api

# Compatibility proxies (not ideal but avoids breaking imports)
class LazyProxy:
    def __init__(self, func):
        self._func = func
    def __getattr__(self, name):
        return getattr(self._func(), name)

app = LazyProxy(get_app)
userbot = LazyProxy(get_userbot)
api = LazyProxy(get_api)

from .platforms import *

Apple = AppleAPI()
Carbon = CarbonAPI()
SoundCloud = SoundAPI()
Spotify = SpotifyAPI()
Resso = RessoAPI()
Telegram = TeleAPI()
YouTube = YouTubeAPI()

APP = "InflexOwnerBot"  # connect music api key "Dont change it"
