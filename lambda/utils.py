import logging
import os
import boto3
import datetime
import json
import logging
import requests
import config
import apprise

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def notify(media_name, media_type, a_list, action="added"):
    # If the user has disabled notifications
    if not config.notify:
        return True
    # We should always get a list, but this handles no list being set
    if a_list is None:
        a_list = "Watch list"
    if config.SLACK_TOKENA != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            apobj.add('slack://' + str(config.SLACK_TOKENA) + "/" + str(config.SLACK_TOKENB) + "/" + str(
                config.SLACK_TOKENC) + "/" + str(config.SLACK_CHANNEL))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                title=config.notify_title.format(media_type, action),
                body=config.notify_body.format(media_name.title(), media_type, a_list, action),
            )
        except Exception as e:  # noqa: E722
            logging.error("Failed sending slacks apprise notification.  continuing  processing...error was " + str(e))
            # TODO: add userid to this and config
    if config.DISCORD_WEBHOOK_ID != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            # A sample pushbullet notification
            apobj.add('discord://' + str(config.DISCORD_WEBHOOK_ID) + '/' + str(config.DISCORD_TOKEN))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                title=config.notify_title.format(media_type, action),
                body=config.notify_body.format(media_name.title(), media_type, a_list, action),
            )
        except:  # noqa: E722
            logging.error("Failed sending discord apprise notification.  Continueing processing...")


def validate(date_text):
    try:
        c = datetime.datetime.strptime(date_text, '%Y-%m-%d')
        print("standard" + str(c))
        return c.strftime('%Y-%m-%d')
    except ValueError:
        # raise ValueError("Incorrect data format, should be YYYY-MM-DD")
        try:
            r = datetime.datetime.strptime(date_text + '-1', "%Y-W%W-%w")
            print(r)
            return r.strftime('%Y-%m-%d')
        except ValueError:
            try:
                c = datetime.datetime.strptime(date_text, '%Y')
                print("year" + str(c))
                return c.strftime('%Y-%m-%d')
            except ValueError:
                print("fuck")


# SIMPLE GET REQUEST TO MAKE OUR MAIN PAGE
# LOOK NICER
def easygeturl(url, headers, p=bool):
    # lets send a request for lists
    r = requests.get(url, headers=headers)
    if p is True:
        print("status code= " + str(r.status_code))
        if r.status_code == 200 or r.status_code == 201:
            # print(r.text)
            dcode = json.loads(r.text)
            # lets see it
            # m = dcode[1]['movie']
            print(json.dumps(dcode[0]['name'], sort_keys=True, indent=4))
            # print(json.dumps(dcode, sort_keys=True, indent=4))
            return dcode[0]
        else:
            print("status code= " + str(r.status_code))
            return
    else:
        if r.status_code == 200 or r.status_code == 201:
            dcode = json.loads(r.text)
            return dcode[0]
        else:
            return


# OUR MAIN SEARCH ENGINE
# ONLY BRINGS BACK THE FIRST THREE RESULT
def search(q, h, t, p=bool):
    # q =query
    # h =headers
    # t = type
    url = "https://api.trakt.tv/search/" + t + "?query=" + q
    m = {}
    m['error'] = True
    # get our info
    r = requests.get(url, headers=h)
    # if logging is on lets print stuff out
    if p is True:
        print("search status code= " + str(r.status_code))
        if r.status_code == 200 or r.status_code == 201:
            print(r.text)
            dcode = json.loads(r.text)
            # m = dcode[0][t]
            if len(dcode) < 1:
                m['error'] = True
                return m
            m = dcode[0]
            # this might cause problems if we get less than 3 results
            m['2nd'] = dcode[1]
            m['3rd'] = dcode[2]
            m['error'] = False
            print(json.dumps(m, sort_keys=True, indent=4))
            return m
        else:
            m['error'] = True
            print("search status code= " + str(r.status_code))
            return m
    else:
        if r.status_code == 200 or r.status_code == 201:
            dcode = json.loads(r.text)
            if len(dcode) < 1:
                m['error'] = True
                return m
            m = dcode[0]
            # this might cause problems if we get less than 3 results
            m['2nd'] = dcode[1]
            m['3rd'] = dcode[2]
            m['error'] = False
            return m
        else:
            m['error'] = True
            return m
    return m


def parse_search(typ, headers, s_obj, our_list, _usecustom=bool, p=bool):
    if typ == 'movie':
        values = """
        {   "movies":[
          {
            "ids": {
              "trakt": """ + str(s_obj['ids']['trakt']) + """
            }
          }
        ],
       "shows":[],
       "seasons":[],
       "episodes":[],
       "people":[]
    }
    """
    else:
        values = """
            {   "movies":[],
           "shows":[
             {
                "ids": {
                    "trakt": """ + str(s_obj['ids']['trakt']) + """
                    }
            } ],
           "seasons":[],
           "episodes":[],
           "people":[]
        }
        """
    # u2= json.loads(u)
    if _usecustom:
        urll = "https://api.trakt.tv/users/me/lists/" + our_list + "/items"
        # print(json.dumps(u, sort_keys=True, indent=4))
    else:
        urll = 'https://api.trakt.tv/sync/watchlist'
    r2 = requests.post(urll, headers=headers, data=values)
    # decode json
    if r2.status_code == 200 or r2.status_code == 201:
        # decode json
        dcode3 = json.loads(r2.text)
        # lets see it
        if p:
            print(json.dumps(dcode3, sort_keys=True, indent=4))
        return True
    else:
        logger.warning('adding to list error! Status code = ' + str(r2.status_code))
        return False


def parse_delete_search(typ, headers, s_obj, our_list, _usecustom=bool, p=bool):
    if typ == 'movie':
        values = """
        {   "movies":[
          {
            "ids": {
              "trakt": """ + str(s_obj['ids']['trakt']) + """
            }
          }
        ],
       "shows":[],
       "seasons":[],
       "episodes":[],
       "people":[]
    }
    """
    else:
        values = """
            {   "movies":[],
           "shows":[
             {
                "ids": {
                    "trakt": """ + str(s_obj['ids']['trakt']) + """
                    }
            } ],
           "seasons":[],
           "episodes":[],
           "people":[]
        }
        """
    # u2= json.loads(u)
    if _usecustom:
        # https://api.trakt.tv/users/id/lists/list_id/items/remove
        urll = "https://api.trakt.tv/users/me/lists/" + our_list + "/items/remove"
        # print(json.dumps(u, sort_keys=True, indent=4))
    else:
        urll = 'https://api.trakt.tv/sync/watchlist/remove'
    r2 = requests.post(urll, headers=headers, data=values)
    # decode json
    if r2.status_code == 200 or r2.status_code == 201:
        # decode json
        dcode3 = json.loads(r2.text)
        # lets see it
        if p:
            print(json.dumps(dcode3, sort_keys=True, indent=4))
            return True
        # todo need to check the return results to see if its was deleted
        return True
    else:
        return False


def search_lists(_movieobj, _alt, headers, _type):
    _foundmatch = False
    a = {}
    a['found'] = False
    a['list'] = ''
    url = 'https://api.trakt.tv/users/me/lists'
    _movtype = _alt['type']
    _altmovie1 = _alt['2nd'][_movtype]['ids']['trakt']
    _altmovie2 = _alt['3rd'][_movtype]['ids']['trakt']
    r = requests.get(url, headers=headers)
    # print ( _movieobj [ 'ids' ] [ 'trakt' ] )
    if r.status_code == 200 or r.status_code == 201:
        # print(r.text)
        dcode = json.loads(r.text)
        # print(json.dumps(dcode, sort_keys=True, indent=4))
        # exit(22231)
        i = 0
        # for each list in the array
        # for i in range(len(dcode)):
        while i < len(dcode):
            # print(dcode[i]['name'])
            # print(json.dumps(dcode[i], sort_keys=True, indent=4))
            o = dcode[i]['ids']['slug']
            # print(str(o) + " is our trakt id")
            # if our list name matches the list given
            url2 = 'https://api.trakt.tv/users/me/lists/' + str(o) + '/items'
            r2 = requests.get(url2, headers=headers)
            j = 0
            if r2.status_code == 200 or r.status_code == 201:
                dcode2 = json.loads(r2.text)
                while j < len(dcode2):
                    # for j in range(len(dcode2)):
                    # we need to parse the list and try to find the movie requested
                    _type = str(dcode2[j]['type'])
                    _traktid = dcode2[j][_type]['ids']['trakt']
                    # print(_title)
                    # print(_title + "  ===  " + _movieobj['ids']['trakt'])
                    # print(json.dumps(dcode2[j][_type], sort_keys=True, indent=4))
                    # TODO THIS CAN LEAD TO SOME WONKY RESULTS IF THE USERS WANTS A SPECIFIC YEAR FILM
                    if _traktid == _movieobj['ids']['trakt'] or _traktid == _altmovie1 or _traktid == _altmovie2:
                        # print ( str ( _title ) + "  ===  " + str ( _movieobj [ 'ids' ] [ 'trakt' ] ) )
                        # print ( 'we found a match' )
                        a['found'] = True
                        a['list'] = str(dcode[i]['name'])
                        return a
                        # exit("yeet")
                    j += 1
            i += 1
        if _foundmatch is not True:
            # print ( "didnt find in custom list, checking watchlist" )
            # https://api.trakt.tv/sync/watchlist
            url = 'https://api.trakt.tv/sync/watchlist'
            r3 = requests.get(url, headers=headers)
            i = 0
            if r3.status_code == 200 or r.status_code == 201:
                dcode3 = json.loads(r3.text)
                for i in range(len(dcode3)):
                    # while i < len ( dcode3 ) :
                    # we need to parse the list and try to find the movie requested
                    _type = str(dcode3[i]['type'])
                    _traktid = dcode3[i][_type]['ids']['trakt']
                    # print(str(dcode3[i]['type']))
                    # print ( _traktid )
                    # print(json.dumps(dcode2[i][_type], sort_keys=True, indent=4))
                    # TODO THIS CAN LEAD TO SOME WONKY RESULTS IF THE USERS WANTS A SPECIFIC YEAR FILM
                    if _traktid == _movieobj['ids']['trakt'] or _traktid == _altmovie1 or _traktid == _altmovie2:
                        # print ( 'we found a match' )
                        a['found'] = True
                        a['list'] = 'watchlist'
                        return a
                        # return True
                        # _foundmatch = True
                    i += 1
                    # return False
            else:
                print("couldnt reach trakt")
                a['found'] = False
                a['list'] = ""
                return a
                # return False
    else:
        # print ( "couldnt reach trakt" )
        a['found'] = False
        a['list'] = ""
        return a
        # return False
    return a


def list_cache(headers):
    # A function to cache the users lists and items to make things quicker
    _foundmatch = False  # noqa F841
    a = {}
    url = 'https://api.trakt.tv/users/me/lists'
    r = requests.get(url, headers=headers)
    if r.status_code == 200 or r.status_code == 201:
        dcode = json.loads(r.text)
        # print(json.dumps(dcode, sort_keys=True, indent=4))
        i = 0
        # for each list in the array
        while i < len(dcode):
            o = dcode[i]['ids']['slug']
            a[i] = {"name": o, "media": {}}
            # print(str(o) + " is our trakt id")
            # if our list name matches the list given
            url2 = 'https://api.trakt.tv/users/me/lists/' + str(o) + '/items'
            r2 = requests.get(url2, headers=headers)
            j = 0
            if r2.status_code == 200 or r.status_code == 201:
                dcode2 = json.loads(r2.text)
                while j < len(dcode2):
                    # for j in range(len(dcode2)):
                    _type = str(dcode2[j]['type'])
                    _title = dcode2[j][_type]['title']
                    _traktid = dcode2[j][_type]['ids']['trakt']
                    # a[i]["media"][j] = {_title:_traktid}
                    a[i]["media"][j] = dcode2[j]
                    j += 1
            i += 1
        url = 'https://api.trakt.tv/sync/watchlist'
        r3 = requests.get(url, headers=headers)
        w = i
        a[w] = {"name": "watchlist", "media": {}}
        i = 0
        if r3.status_code == 200 or r.status_code == 201:
            dcode3 = json.loads(r3.text)
            # print(json.dumps(dcode3,sort_keys=True,indent=4))
            for i in range(len(dcode3)):
                # while i < len ( dcode3 ) :
                # we need to parse the list and try to find the movie requested
                _type = str(dcode3[i]['type'])
                if _type == 'season':
                    _type = 'show'
                _title = dcode3[i][_type]['title']  # noqa F841
                _traktid = dcode3[i][_type]['ids']['trakt']  # noqa F841
                # a[w][i] = {_title : _traktid}
                a[w]['media'][i] = dcode3[i]
                i += 1  # return False
        else:
            print("couldnt reach trakt")
            a['error'] = True
            a['found'] = False
            a['list'] = ""
            return a  # return False
    else:
        # print ( "couldnt reach trakt" )
        a['error'] = True
        a['found'] = False
        a['list'] = ""
        return a  # return False
    # save our lists to cache
    return a


def listparser(_mywatchlist, _boxoffice, _listtype):
    # print(_item)
    _notfound = {}
    i = 0
    # while i<len(_list) :
    # loop through each list
    for i in range(len(_mywatchlist)):
        # print(_list)
        j = 0
        # loop through each item on the list
        for j in range(len(_mywatchlist[i]['media'])):
            # while j<len(_list[i]['media']):
            # print("my watch list item = "+str(_mywatchlist[i]['media']))
            # _type = str(_mywatchlist[i]['media'][j]['type'])
            # only trig for popular list every other fucking list is fine
            if _listtype == 'popular':
                _type = _mywatchlist[i]['media'][j]['type']
                # print(str(_boxoffice))
                # print(str(_mywatchlist[i]['media'][j]))
                if _type != 'season':
                    _ids = _mywatchlist[i]['media'][j][_type]['ids']['trakt']
                    _title = _mywatchlist[i]['media'][j][_type]['title']
                    _boxofficeids = _boxoffice['ids']['trakt']
                    # print(str(_boxoffice))
                    if _ids == _boxofficeids:
                        # if _title==_boxoffice['movie']['title'] :
                        print("we found " + _title)
                        return  # {"":"","":""}
                    else:
                        _botitle = str(_boxoffice['title'])
                        _notfound = {"title": _botitle, "id": _boxoffice['ids']['trakt']}
            else:
                _type = _mywatchlist[i]['media'][j]['type']
                if _type == 'show' or _type == 'season':
                    print("")
                    # _title goes here
                    # _notfound[_botitle] = _boxoffice['movie']['ids']['trakt']
                    # ignore we cant match shows with box office
                    # _title = _mywatchlist[i]['media'][j]['movie']['title']
                # THIS IS FINE, DONT BREAK IT
                else:
                    _title = _mywatchlist[i]['media'][j]['movie']['title']
                    _ids = _mywatchlist[i]['media'][j]['movie']['ids']['trakt']
                    print(str(_ids) + " ==== " + str(_boxoffice['movie']['ids']['trakt']))
                    if _ids == _boxoffice['movie']['ids']['trakt']:
                        print("we found " + _title)
                        return  # {"":"","":""}
                    else:
                        _botitle = str(_boxoffice['movie']['title'])
                        _notfound = {"title": _botitle, "id": _boxoffice['movie']['ids']['trakt']}
                        # _notfound[_botitle] = _boxoffice['movie']['ids']['trakt']

            j += 1
            # _item[i][_type]['title']
            # print(_title)
        i += 1
        # print(str(_notfound))
        # _notfound.remove(None)
    return _notfound


def addOneMovie(_movieobj, _usecustom, headers, _list):
    values = """
        {   "movies":[
          {
            "ids": {
              "trakt": """ + str(_movieobj['id']) + """
            }
          }
        ],
       "shows":[],
       "seasons":[],
       "episodes":[],
       "people":[]
    }
    """
    # u2= json.loads(u)
    if _usecustom:
        urll = "https://api.trakt.tv/users/me/lists/" + _list + "/items"
    else:
        urll = 'https://api.trakt.tv/sync/watchlist'
    r2 = requests.post(urll, headers=headers, data=values)
    # decode json
    if r2.status_code == 200 or r2.status_code == 201:
        # decode json
        dcode3 = json.loads(r2.text)  # noqa F841
        # lets see it
        return True
    else:
        logger.warning('adding to list error! Status code = ' + str(r2.status_code))
        return False


def add_movies(_movieobj, use_custom, headers, _list):
    values = """
        {   "movies":[
            
                """ + _movieobj + """
            
        ],
       "shows":[],
       "seasons":[],
       "episodes":[],
       "people":[]
    }
    """
    # u2= json.loads(u)
    logger.debug('Status code = {}'.format(str(values)))
    logger.debug('custom = ' + str(use_custom))
    if use_custom and _list != 'watchlist' and _list != 'watch list':
        urll = "https://api.trakt.tv/users/me/lists/" + _list + "/items"
    else:
        urll = 'https://api.trakt.tv/sync/watchlist'
    logger.debug("url ={}".format(urll))
    r2 = requests.post(urll, headers=headers, data=values)
    # decode json
    if r2.status_code == 200 or r2.status_code == 201:
        # decode json
        dcode3 = json.loads(r2.text)  # noqa F841
        # lets see it
        return True
    else:
        logger.error('adding to list error! Status code = ' + str(r2.status_code))
        return False


