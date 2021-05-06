import datetime
import json
import logging
import requests
import config
import apprise
import language
import trakt_api

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
TRAKT_WATCHLIST = 'https://api.trakt.tv/sync/watchlist'
STR_DATETIME = '%Y-%m-%d'


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
            apobj.add(f'slack://{config.SLACK_TOKENA}/{config.SLACK_TOKENB}'
                      f'/{config.SLACK_TOKENC}/{config.SLACK_CHANNEL}')
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                title=config.notify_title.format(media_type, action),
                body=config.notify_body.format(media_name.title(), media_type, a_list, action),
            )
        except Exception as e:  # noqa: E722
            logging.error(f"Failed sending slacks apprise notification.  Continuing  processing...error: {e}")
            # TODO: add userid to this and config
    if config.DISCORD_WEBHOOK_ID != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            # A sample pushbullet notification
            apobj.add(f'discord://{config.DISCORD_WEBHOOK_ID}/{config.DISCORD_TOKEN}')
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                title=config.notify_title.format(media_type, action),
                body=config.notify_body.format(media_name.title(), media_type, a_list, action),
            )
        except Exception as e:  # noqa: E722
            logging.error(f"Failed sending discord apprise notification.  Continuing processing...Error: {e}")


def validate(date_text):
    try:
        c = datetime.datetime.strptime(date_text, STR_DATETIME)
        print("standard" + str(c))
        return c.strftime(STR_DATETIME)
    except ValueError:
        # raise ValueError("Incorrect data format, should be YYYY-MM-DD")
        try:
            r = datetime.datetime.strptime(date_text + '-1', "%Y-W%W-%w")
            print(r)
            return r.strftime(STR_DATETIME)
        except ValueError:
            try:
                c = datetime.datetime.strptime(date_text, '%Y')
                print("year" + str(c))
                return c.strftime(STR_DATETIME)
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
    else:
        if r.status_code == 200 or r.status_code == 201:
            dcode = json.loads(r.text)
            return dcode[0]


def get_list(_list, persistent_attributes):
    """
    Check if the user supplied a list and if its a custom list, also check for for any saved lists

    :param _list: User supplied list
    :param persistent_attributes: The persistent attribs from the app
    :return: The list name , If list is custom or not
    """
    if _list is not None and (_list.lower() != 'watchlist' and _list.lower() != 'watch list'):
        return _list, True
    else:
        # if default isnt set use watchlist
        if "list" in persistent_attributes:
            if persistent_attributes["list"] != 'watchlist' and persistent_attributes["list"] != 'watch list':
                _list = persistent_attributes["list"]
                _usecustomlist = True
            else:
                _list = 'watchlist'
                _usecustomlist = False
        else:
            _list = 'watchlist'
            _usecustomlist = False
    return _list, _usecustomlist


def get_popular_list(list_type):
    """
    function to check the user supplied a valid list type for tracked

    :param list_type:  User supplied list
    :return: A valid list type for the trakt api
    """
    # if we got nothing set the default
    if list_type is None:
        list_type = 'boxoffice'
    # fixing box office to slug type
    if list_type == 'box office':
        list_type = 'boxoffice'
    x = ('popular', ' boxoffice', ' box office', 'trending', 'collected', 'played', 'watched')
    if list_type not in x:
        list_type = 'boxoffice'
    return list_type


def build_headers(access_token, client_id):
    """

    :param access_token: Access token granted when the user links their account
    :param client_id: This is the api key for your own app
    :return: Dict of headers
    """
    return {'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'trakt-api-version': '2',
            'trakt-api-key': client_id}


def list_tester(user_list, session_list, watch_lists):
    """
    :param user_list: The user list if they supplied one
    :param session_list: The session attributes or persistent attributes
    :param watch_lists: tuple of watch list aliases
    :return: True if list is a custom list, False if watchlist
    """
    try:
        session_list['list']
    except KeyError:
        session_list['list'] = None
    if user_list is None and session_list['list'] is None:
        return True
    if not user_list and not session_list['list']:
        return True
    if user_list.lower() in watch_lists:
        return True
    return False


def test_session_attribs(attr):
    try:
        attr['readShows']
    except (ValueError, KeyError):
        attr['readShows'] = False
    try:
        attr['readMovies']
    except (ValueError, KeyError):
        attr['readMovies'] = False
    try:
        attr['readBoth']
    except (ValueError, KeyError):
        attr['readBoth'] = False
    try:
        attr['repeat']
    except (ValueError, KeyError):
        attr['repeat'] = ''
    try:
        attr['active_request']
    except (ValueError, KeyError):
        attr['active_request'] = ''
    try:
        attr['readBoxOffice']
    except (ValueError, KeyError):
        attr['readBoxOffice'] = False
    return attr


def read_box_office(attr):
    # TODO: fix bug not reading out if there are 10 items.
    # movies read out here
    x = attr["movie"]
    _size = len(x)
    logger.info("readBoxOffice")
    _alexa_out = 'Here is the list of movies you asked for'
    i = 0
    while i < _size:
        # we need to parse the list and try to find the movie requested
        _alexa_out += ", " + str(x[str(i)]['title']).replace("-", "").replace(":", "")
        i += 1
    _alexa_out += ". Would you like me to add the movies to your default list ?"
    attr['readShows'] = False
    attr['readMovies'] = False
    attr['readBoth'] = False
    attr['active_request'] = 'AddMovies'
    attr['repeat'] = 'readBoxOffice'
    attr['readBoxOffice'] = False
    print(_alexa_out)
    return attr, _alexa_out


def read_out_both(attr, _alexa_out):
    x = attr["show"]
    z = attr["movie"]
    _size = len(x)
    _size2 = len(z)
    if (_size - 1) < 0:
        _alexa_out += str(" ")
    else:
        _alexa_out += str('Here is the list of shows you asked for....  ')
    i = 0
    while i < _size:
        _alexa_out += str(",  " + x[str(i)])
        i += 1
    j = 0
    if (_size2 - 1) < 0:
        _alexa_out += str(" ")
    else:
        _alexa_out += str(",  Here are the list of movies, ")
    while j < _size2:
        _alexa_out += str(z[str(j)] + ",  ")
        j += 1
    attr['readShows'] = False
    attr['readMovies'] = False
    attr['readBoth'] = False
    attr['readBoxOffice'] = False
    attr['repeat'] = 'readBoth'

    return attr, _alexa_out


def read_out_shows(attr):
    x = attr["show"]
    _size = len(x)
    logger.info("readShows")
    _alexa_out = 'Here is the list of shows you asked for,  '
    i = 0
    while i < _size:
        # for j in range(len(dcode2)):
        _alexa_out += str(",  " + x[str(i)])
        i += 1
    attr['readShows'] = False
    attr['readBoxOffice'] = False
    attr['readMovies'] = False
    attr['readBoth'] = False
    attr['repeat'] = 'readShows'
    return attr, _alexa_out


def read_out_movies(attr):
    x = attr["movie"]
    _size = len(x)
    logger.info("readMovies")
    _alexa_out = 'Here is the list of movies you asked for,  '
    i = 0
    while i < _size:
        # for j in range(len(dcode2)):
        # we need to parse the list and try to find the movie requested
        _alexa_out += str(",  " + x[str(i)])
        i += 1
    attr['readShows'] = False
    attr['readMovies'] = False
    attr['readBoth'] = False
    attr['readBoxOffice'] = False
    attr['repeat'] = 'readMovies'
    return attr, _alexa_out


def read_add_movies(_perattr, attr, headers):
    # movies read out here
    x = attr["movie"]
    _size = len(x)
    logger.info("active_request")
    _alexa_out = 'Here is the list of movies that i have added '
    i = 0
    _usecustomlist = False
    # TODO find a better way to match list names and also fix _usecustomlist not being set correctly
    # they didnt give us a list use the default
    # if a list isnt set use watchlist
    if "list" in _perattr:
        _list = _perattr["list"]
        if _list != "watchlist" or _list != "watch list":
            _usecustomlist = True  # noqa F841
    else:
        _list = 'watchlist'
        _usecustomlist = False  # noqa F841
    movie_list = ""

    while i < _size:
        # for j in range(len(dcode2)):
        # we need to parse the list and try to find the movie requested
        # if trakt_api.add_one_movie(x[str(i)], _usecustomlist, headers, _list):
        #    _alexa_out += str(",  " + x[str(i)]['title'])
        # else:
        #    _alexa_out += str(" ")
        _alexa_out += str(",  " + x[str(i)]['title'])
        if i == 0:
            # "ids": {""" + _movieobj + """}
            movie_list += """{"ids": {"trakt": """ + str(x[str(i)]['id']) + "}}"
        else:
            movie_list += """,\n{"ids": { "trakt": """ + str(x[str(i)]['id']) + "}}"
        i += 1
    if trakt_api.add_movies(movie_list, _usecustomlist, headers, _list):
        _alexa_out += str(". ")
    else:
        _alexa_out = "I couldn't add the movies, there was an error"
    attr['readShows'] = False
    attr['readMovies'] = False
    attr['readBoth'] = False
    attr['readBoxOffice'] = False
    attr['active_request'] = ''
    attr['repeat'] = ''
    attr['show'] = {}
    attr['movie'] = {}
    return attr, _alexa_out


def read_shows_check(attr, intent):
    if attr['readShows'] and not attr['readMovies'] \
            or intent and attr['repeat'] == 'readShows':
        return True
    return False
