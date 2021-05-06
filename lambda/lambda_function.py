# -*- coding: utf-8 -*-
import logging
import os
import requests
import json
import config
import utils
import language
import trakt_api

from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name, get_slot_value
from ask_sdk_core.handler_input import HandlerInput  # noqa: F401
from ask_sdk_model import Response  # noqa: F401
from ask_sdk_s3.adapter import S3Adapter
from datetime import datetime

s3_adapter = S3Adapter(bucket_name=os.environ["S3_PERSISTENCE_BUCKET"])
sb = CustomSkillBuilder(persistence_adapter=s3_adapter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

watch_lists = ('watchlist', 'watch list')
DATE_FORMAT = '%Y-%m-%d'
clientid = config.client_id
user = 'me'
is_auth = False


@sb.request_handler(can_handle_func=lambda input: is_request_type("LaunchRequest")(input)
                    or is_intent_name("AddMovie")(input))
def add_movie_intent_handler(handler_input):
    """Handler for Add Movie Intent."""

    # get our persistent_attributes
    # if the user has launched the app greet them
    # set out session attributes
    _perattr = handler_input.attributes_manager.persistent_attributes
    attr = handler_input.attributes_manager.session_attributes
    if is_request_type("LaunchRequest")(handler_input):
        # _usecustomlist = _perattr['usecustomlist']
        attr["movie"] = {}
        attr["show"] = {}
        attr['readBoxOffice'] = False
        attr['readMovies'] = False
        attr['readShows'] = False
        attr['readBoth'] = False
        attr['active_request'] = ''
        attr['repeat'] = ''
        handler_input.response_builder.speak("Welcome To Radar the Trakt.tv tracker").ask("")
        return handler_input.response_builder.response

    # Get the value of the users auth token
    h = handler_input.request_envelope.context.system.user.access_token
    # _list = 'watchlist'
    _usecustomlist = False
    # If we are not auth, let the user know
    if h is None:
        handler_input.response_builder.speak(language.AUTH_ERROR)
        return handler_input.response_builder.response
    # Set all our headers for the trakt-api
    headers = utils.build_headers(h, clientid)
    print("Header= " + str(headers))
    # Get the movie name and throw it onto the movie var
    movie = get_slot_value(handler_input=handler_input, slot_name="movieName")
    use_list = get_slot_value(handler_input=handler_input, slot_name="list_name")
    # reprompt = "Are you sure you want to add "+movie+' to your list ?'
    # user gave us nothing lets do some checks to make sure we have saved attributes
    _list, _usecustomlist = utils.get_list(use_list, _perattr)
    # search for move and get the object
    b = trakt_api.search(movie, headers, "movie", True)
    if b['error']:
        # handle this
        handler_input.response_builder.speak("I couldn't find the show you requested")
        return handler_input.response_builder.response
    # force our movie/show object into a small var to make things easier
    y = b["movie"]
    # dig through our search and add the movie/show to our list or our Watchlist
    if trakt_api.parse_search(b['type'], headers, y, _list, _usecustomlist, True):
        # media_name, media_type, a_list
        utils.notify(movie, b['type'], _list)
        handler_input.response_builder.speak(movie + " has been added to your " + _list + " list")  # .ask(reprompt)
    else:
        # TODO Fix the notify to allow errors
        # utils.notify(movie, b['type'], _list)
        handler_input.response_builder.speak("There was a problem adding " + movie + " to your list " + _list)
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_intent_name("AddShow"))
def add_show_intent_handler(handler_input):
    """ handler for Add Show Intent"""

    h = handler_input.request_envelope.context.system.user.access_token
    showtype = 'show'
    # If we are not auth, let the user know
    if h is None:
        reprompt = language.AUTH_ERROR
        handler_input.response_builder.speak(reprompt).ask(reprompt)
        return handler_input.response_builder.response
    headers = utils.build_headers(h, clientid)

    # get our persistent_attributes
    _perattr = handler_input.attributes_manager.persistent_attributes
    movie = get_slot_value(handler_input=handler_input, slot_name="showName")
    user_list = get_slot_value(handler_input=handler_input, slot_name="list_name")
    _list, _usecustomlist = utils.get_list(user_list, _perattr)
    # search for move and get the object
    b = trakt_api.search(movie, headers, showtype, False)
    if b['error']:
        # handle this
        handler_input.response_builder.speak(language.SHOW_404)
        return handler_input.response_builder.response

    y = b['show']
    # dig through our search and add the movie/show to our list or our Watchlist
    trakt_api.parse_search(b['type'], headers, y, _list, _usecustomlist, True)
    utils.notify(movie, b['type'], _list)
    handler_input.response_builder.speak(movie + " show has been added to your list " + str(_list))
    # .ask(reprompt)
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_intent_name("ChooseList"))
def choose_list_intent_handler(handler_input):
    """Handler for Choose List Intent."""
    # get the value of listName and throw it onto _thelist
    _thelist = get_slot_value(handler_input=handler_input, slot_name="listName")
    # Get the value of the users auth token
    h = handler_input.request_envelope.context.system.user.access_token
    # If we are not auth, let the user know
    if h is None:
        reprompt = language.AUTH_ERROR
        handler_input.response_builder.speak(reprompt).ask(reprompt)
        return handler_input.response_builder.response
    # Set all our headers for the trakt-api
    headers = utils.build_headers(h, clientid)
    session_attr = handler_input.attributes_manager.session_attributes
    if utils.list_tester(_thelist, session_attr, watch_lists):
        handler_input.response_builder.speak("Your List has been set to the default. This is the watchlist")
        # start saving the persistent attributes
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr['usecustomlist'] = False
        session_attr['list'] = 'watchlist'
        handler_input.attributes_manager.persistent_attributes = session_attr
        handler_input.attributes_manager.save_persistent_attributes()
        return handler_input.response_builder.response
    # user wanted a different custom list
    # lets get all their trakt.tv lists
    # TODO _customlist should probs be set to "watchlist" to start
    _foundlist = False
    _customlist = ''
    url = 'https://api.trakt.tv/users/me/lists'
    r = requests.get(url, headers=headers)
    # If everything is ok lets process
    if r.status_code == 200 or r.status_code == 201:
        # print(r.text)
        dcode = json.loads(r.text)
        i = 0
        while i < len(dcode):
            # print(dcode[i]['name'])
            # print(json.dumps(dcode[i], sort_keys=True, indent=4))
            o = dcode[i]['ids']['slug']
            # print(str(o) + " is our trakt slug")
            if dcode[i]['name'] == _thelist.lower():
                _foundlist = True
                # set the list to the user requested list
                _customlist = o
            i += 1
        # couldnt find the custom list notify and set to watchlist
        if not _foundlist:
            reprompt = "I couldn't find that list. Your list has been set to the default. This is the watchlist"
            handler_input.response_builder.speak(reprompt).ask(reprompt)
            # start saving the persistent attributes
            session_attr = handler_input.attributes_manager.session_attributes
            session_attr['usecustomlist'] = False
            session_attr['list'] = 'watchlist'
            handler_input.attributes_manager.persistent_attributes = session_attr
            handler_input.attributes_manager.save_persistent_attributes()
            return handler_input.response_builder.response

        # we found the list, save it and we can use it for all add requests
        handler_input.response_builder.speak(f"Your List has been set to {_thelist}")
        # start saving the persistent attributes
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr['usecustomlist'] = _foundlist
        session_attr['list'] = _customlist
        # save session attributes as persistent attributes
        handler_input.attributes_manager.persistent_attributes = session_attr
        handler_input.attributes_manager.save_persistent_attributes()
        return handler_input.response_builder.response
    else:
        # TODO Catch the error and tell alexa to output it nicely
        # revert to default settings and store them
        handler_input.response_builder.speak(language.TRAKT_DOWN)
        return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_intent_name("RemoveShow"))
def remove_show_intent_handler(handler_input):
    """ handler for Remove Show Intent"""

    # Get the value of the users auth token
    h = handler_input.request_envelope.context.system.user.access_token
    # If we are not auth, let the user know
    if h is None:
        reprompt = language.AUTH_ERROR
        handler_input.response_builder.speak(reprompt).ask(reprompt)
        return handler_input.response_builder.response
    # Set all our headers for the trakt-api
    headers = utils.build_headers(h, clientid)
    # TODO make sure we change I,II,II type movies to 1,2,3
    # and vice versa
    # _usecustomlist = bool
    user_list = get_slot_value(handler_input=handler_input, slot_name="list_name")
    movie = str(get_slot_value(handler_input=handler_input, slot_name="showName"))

    # get our persistent_attributes
    attr = handler_input.attributes_manager.persistent_attributes
    _list, _usecustomlist = utils.get_list(user_list, attr)

    # if our list isnt empty then we can go ahead and deal with the request
    if _usecustomlist:
        url = 'https://api.trakt.tv/users/me/lists/' + _list + '/items/shows'
        r = requests.get(url, headers=headers)

        if r.status_code == 200 or r.status_code == 201:
            dcode = json.loads(r.text)
            # print(json.dumps(json.loads(r.text), sort_keys=True, indent=4))
            i = 0
            _moviefound = False
            while i < len(dcode):
                # print(dcode[i]['name'])
                # print(json.dumps(dcode[i], sort_keys=True, indent=4))
                o = dcode[i]['show']['title']
                # print(str(o) + " is our title")
                # if our movie name matches the movie send the request to delete it
                if o.lower() == movie.lower():
                    _moviefound = True
                    _id = dcode[i]['show']['ids']['trakt']  # noqa F841
                    # print("we found it")
                    # print(json.dumps(dcode[i], sort_keys=True, indent=4))
                    if trakt_api.parse_delete_search('show', headers, dcode[i]['show'], _list, _usecustomlist):
                        reprompt = f"I have deleted {o} from the list {_list}"
                        # media_name, media_type, a_list
                        utils.notify(movie, "show", _list, "removed")
                        handler_input.response_builder.speak(reprompt).ask(reprompt)
                        return handler_input.response_builder.response
                        # return  # print("we finished and deleted")  # exit("deleted")
                    else:
                        # return
                        handler_input.response_builder.speak(f"I had trouble deleting {o} from the list {_list}")
                        return handler_input.response_builder.response
                        # print("we found the film but there was an error deleting")  # exit("not deleted")
                i += 1
            # if we failed to find the movie
            if _moviefound is False:
                # print("we couldnt find the film")
                handler_input.response_builder.speak(f"I couldnt find {movie} on the list {_list}")
                return handler_input.response_builder.response
        # if our first request to trakt fails
        else:
            handler_input.response_builder.speak('I couldn\'t contact Trakt.tv API .' + url)
            return handler_input.response_builder.response
    # if our user didnt give us a list or they are using the watch list
    else:
        # WE DIDNT RECIEVE A LIST
        # TODO make sure we change I,II,II type movies to 1,2,3
        # and vice versa
        # search for movie and get the object
        b = trakt_api.search(movie, headers, "show", False)
        if b['error']:
            # handle this
            reprompt = language.SHOW_404
            handler_input.response_builder.speak(reprompt).ask(reprompt)
            return handler_input.response_builder.response
        # force our movie/show object into a small var to make things easier
        y = b['show']
        if trakt_api.parse_delete_search('show', headers, y, _list, False):
            # media_name, media_type, a_list
            utils.notify(movie, "show", _list, "removed")
            handler_input.response_builder.speak(f"I have deleted {movie} from the list {_list}")
            return handler_input.response_builder.response
        else:
            reprompt = f"I couldn't delete {movie} from the list {_list}"
            handler_input.response_builder.speak(reprompt).ask(reprompt)
            return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_intent_name("RemoveMovie"))
def remove_movie_intent_handler(handler_input):
    # Get the value of the users auth token
    h = handler_input.request_envelope.context.system.user.access_token
    # If we are not auth, let the user know
    if h is None:
        handler_input.response_builder.speak(language.AUTH_ERROR).ask(language.AUTH_ERROR)
        return handler_input.response_builder.response
    # Set all our headers for the trakt-api
    headers = utils.build_headers(h, clientid)
    # TODO make sure we change I,II,II type movies to 1,2,3
    # and vice versa
    user_list = get_slot_value(handler_input=handler_input, slot_name="list_name")
    movie = str(get_slot_value(handler_input=handler_input, slot_name="movieName"))

    # get our persistent_attributes
    attr = handler_input.attributes_manager.persistent_attributes
    _list, _usecustomlist = utils.get_list(user_list, attr)

    # if our list isnt empty then we can go ahead amd deal with the request
    if _usecustomlist:
        url = 'https://api.trakt.tv/users/me/lists/' + _list + '/items/movies'
        r = requests.get(url, headers=headers)

        if r.status_code == 200 or r.status_code == 201:
            dcode = json.loads(r.text)
            # print(json.dumps(json.loads(r.text), sort_keys=True, indent=4))
            i = 0
            _moviefound = False
            while i < len(dcode):
                # print(dcode[i]['name'])
                # print(json.dumps(dcode[i], sort_keys=True, indent=4))
                o = dcode[i]["movie"]['title']
                # print(str(o) + " is our title")
                # if our movie name matches the movie send the request to delete it
                if o.lower() == movie.lower():
                    _moviefound = True
                    # print("we found it")
                    # print(json.dumps(dcode[i], sort_keys=True, indent=4))
                    if trakt_api.parse_delete_search("movie", headers, dcode[i]["movie"], _list, _usecustomlist):
                        handler_input.response_builder.speak(f"I have deleted {o} from the list {_list}")
                        return handler_input.response_builder.response
                        # return  # print("we finished and deleted")  # exit("deleted")
                    else:
                        # return
                        handler_input.response_builder.speak(f"I had trouble deleting {o} from the list {_list}")
                        return handler_input.response_builder.response
                        # print("we found the film but there was an error deleting")  # exit("not deleted")
                i += 1
            # if we failed to find the movie
            if _moviefound is False:
                # print("we couldnt find the film")
                handler_input.response_builder.speak(f"I couldn't find {movie} on the list {_list}")
                return handler_input.response_builder.response
        # if our first request to trakt fails
        else:
            handler_input.response_builder.speak("I couldn't contact Trakt.tv API ." + url)
            return handler_input.response_builder.response
    # if our user didnt give us a list or they are using the watch list
    else:
        # WE DIDNT RECIEVE A LIST
        # TODO make sure we change I,II,II type movies to 1,2,3
        # and vice versa
        # search for movie and get the object
        b = trakt_api.search(movie, headers, "movie", False)
        if b['error']:
            # handle this
            reprompt = "I couldn't find the movie you requested"
            handler_input.response_builder.speak(reprompt).ask(reprompt)
            return handler_input.response_builder.response
        # force our movie/show object into a small var to make things easier
        y = b["movie"]
        if trakt_api.parse_delete_search("movie", headers, y, _list, False):
            # media_name, media_type, a_list
            utils.notify(movie, b['type'], _list, "removed")
            handler_input.response_builder.speak(f"I have deleted {movie} from the list {_list}")
            return handler_input.response_builder.response
        else:
            handler_input.response_builder.speak(f"I couldn't delete {movie} from the list {_list}")
            return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_intent_name("WhatsOn"))
def whats_on_intent_handler(handler_input):
    # Get the value of the users auth token
    h = handler_input.request_envelope.context.system.user.access_token
    # set the default to use todays datetime
    # OUR default items count
    _movieitemcount = 0
    _showitemcount = 0
    z = ''
    attr = handler_input.attributes_manager.session_attributes
    attr["show"] = {}
    attr["movie"] = {}
    attr['readBoth'] = False
    attr['readShows'] = False
    attr['readMovies'] = False
    attr['readBoxOffice'] = False
    attr['repeat'] = ''
    attr['active_request'] = ''

    # If we are not auth, let the user know
    if h is None:
        handler_input.response_builder.speak(language.AUTH_ERROR)
        return handler_input.response_builder.response
    # Set all our headers for the trakt-api
    headers = utils.build_headers(h, clientid)
    # return handler_input.response_builder.response
    # _date gives 2020-04-17 format
    _type = get_slot_value(handler_input=handler_input, slot_name="typeMedia")
    _date = get_slot_value(handler_input=handler_input, slot_name="thedate")
    if _date is None:
        x = datetime.now()
        z = x.strftime(DATE_FORMAT)
    else:
        z = utils.validate(_date)
    # did they want a specific media ?
    if _type is not None:
        # We got a movie ?
        _type1 = str(_type).lower()
        if _type1 == "movies" or _type1 == "movie" or _type1 == "films" or _type1 == "film":
            # its a movie
            url = "https://api.trakt.tv/calendars/my/movies/" + str(z) + "/7"
            # lets send a request for lists
            r = requests.get(url, headers=headers)

            # attributes = handler_input.attributes_manager.session_attributes()
            if r.status_code == 200 or r.status_code == 201:
                dcode = json.loads(r.text)
                print(json.dumps(dcode, sort_keys=True, indent=4))
                i = 0
                while i < len(dcode):
                    # for j in range(len(dcode2)):
                    # we need to parse the list and try to find the movie requested
                    _title = str(dcode[i]["movie"]['title'])
                    attr["movie"][i] = _title
                    _movieitemcount += 1
                    i += 1
                if (len(dcode) - 1) < 0:
                    print("no movie items")
            else:
                print(f"status code= {r.status_code}")
            n = datetime.now()
            m = n.strftime(DATE_FORMAT)
            should_end_session = False  # noqa F841
            if (_movieitemcount - 1) < 0:
                if z == m:
                    handler_input.response_builder.speak("you have no new movies today")
                    return handler_input.response_builder.response
                else:
                    handler_input.response_builder.speak("you have no new movies on " + str(z))
                    return handler_input.response_builder.response
                    # print("you have no new movies or episodes on today")
            else:
                reprompt = 'Would you like me to read the list out ?'
                if z == m:
                    handler_input.response_builder.speak(f"You have {_movieitemcount} new movies on today. "
                                                         + reprompt).ask(reprompt)
                    attr["readMovies"] = True
                    return handler_input.response_builder.response
                else:
                    handler_input.response_builder.speak(f"You have {_movieitemcount} new movies on {z}."
                                                         "Would you like me to read the list out ?").ask(reprompt)
                    attr["readMovies"] = True
                    return handler_input.response_builder.response
        # Series
        if _type1 == 'series' or _type1 == 'episodes' or _type1 == 'shows' or _type1 == 'show':
            # its a tv shows
            url2 = "https://api.trakt.tv/calendars/my/shows/" + str(z) + "/7"
            # lets send a request for lists
            r2 = requests.get(url2, headers=headers)
            # print("status code= "+str(r2.status_code))
            if r2.status_code == 200 or r2.status_code == 201:
                dcode2 = json.loads(r2.text)
                print(json.dumps(dcode2, sort_keys=True, indent=4))
                i = 0

                while i < len(dcode2):
                    # for j in range(len(dcode2)):
                    # we need to parse the list and try to find the movie requested
                    _title = str(dcode2[i]["show"]['title'])
                    attr["show"][i] = _title
                    # print(_title)
                    _showitemcount += 1
                    i += 1
                if (len(dcode2) - 1) < 0:
                    print("no show items")
            # something broke or we have nothing
            else:
                repromt = "I couldn't reach the trakt.tv API"
                handler_input.response_builder.speak(repromt).ask(repromt)
                return handler_input.response_builder.response
            n = datetime.now()
            m = n.strftime(DATE_FORMAT)
            reprompt = 'Would you like me to read them out ?'
            if (_showitemcount - 1) < 0:
                if z == m:
                    handler_input.response_builder.speak("you have no new episodes on today")
                    return handler_input.response_builder.response
                else:
                    handler_input.response_builder.speak(f"you have no new episodes on {z}")
                    return handler_input.response_builder.response
            else:
                if z == m:
                    handler_input.response_builder.speak(f"You have {_showitemcount} new episodes on today. "
                                                         f"Would you like me to read the list out ?").ask(reprompt)
                    attr["readShows"] = True
                    return handler_input.response_builder.response
                else:
                    handler_input.response_builder.speak(
                        f"You have {_showitemcount} new episodes on {z}. "
                        f"Would you like me to read the list out ?").ask("Would you like me to read the list out ?")
                    attr["readShows"] = True
                    return handler_input.response_builder.response
        # not sure what we got
        else:
            handler_input.response_builder.speak(
                "I'm sorry I couldn't understand what you type you wanted").ask(
                "Try saying, Alexa ask Radar what is on.")
            return handler_input.response_builder.response
    # OUR default items count
    _movieitemcount = 0
    _showitemcount = 0
    url = "https://api.trakt.tv/calendars/my/movies/" + str(z) + "/1"
    # lets send a request for lists
    r = requests.get(url, headers=headers)
    # print("status code= "+str(r.status_code))
    if r.status_code == 200 or r.status_code == 201:
        dcode = json.loads(r.text)
        print(json.dumps(dcode, sort_keys=True, indent=4))
        i = 0
        while i < len(dcode):
            # for j in range(len(dcode2)):
            # we need to parse the list and try to find the movie requested
            _title = str(dcode[i]["movie"]['title'])
            attr["movie"][i] = _title
            # print(_title)
            # _traktid=dcode[i]['ids']['trakt']
            # exit("yeet")
            _movieitemcount += 1
            i += 1
        if (len(dcode) - 1) < 0:
            print("no movie items")
    else:
        handler_input.response_builder.speak("I cant seem to contact the trakt.tv API. Please try again.")
        return handler_input.response_builder.response

    url2 = "https://api.trakt.tv/calendars/my/shows/" + str(z) + "/7"
    # lets send a request for lists
    r2 = requests.get(url2, headers=headers)
    print("status code= " + str(r2.status_code))
    if r2.status_code == 200 or r2.status_code == 201:
        dcode2 = json.loads(r2.text)
        print(json.dumps(dcode2, sort_keys=True, indent=4))
        i = 0
        while i < len(dcode2):
            # for j in range(len(dcode2)):
            # we need to parse the list and try to find the movie requested
            _title = str(dcode2[i]["show"]['title'])
            attr["show"][i] = _title
            # print(_title)
            # _traktid=dcode[i]['ids']['trakt']
            # exit("yeet")
            _showitemcount += 1
            i += 1
        if (len(dcode2) - 1) < 0:
            print("no show items")
    else:
        print(f"status code= {r.status_code}")
    n = datetime.now()
    m = n.strftime(DATE_FORMAT)
    reprompt = 'Would you like me to read them out ?'
    if (_movieitemcount - 1) < 0 and (_showitemcount - 1) < 0:
        if z == m:
            handler_input.response_builder.speak("you have no new movies or episodes on today")
            return handler_input.response_builder.response
        else:
            handler_input.response_builder.speak("you have no new movies or episodes on " + str(z))
            return handler_input.response_builder.response
            # print("you have no new movies or episodes on today")
    else:
        if z == m:
            handler_input.response_builder.speak(f"You have {_movieitemcount} new movies and {_showitemcount}"
                                                 f" episodes on Today. "
                                                 f"Would you like me to read the list out ?").ask(reprompt)
            attr['readBoth'] = True
            attr['readShows'] = False
            attr['readMovies'] = False
            return handler_input.response_builder.response
        else:
            handler_input.response_builder.speak(
                f"You have {_movieitemcount} new movies and {_showitemcount} episodes on {z}."
                f"Would you like me to read the list out ?").ask(reprompt)
            attr['readBoth'] = True
            attr['readShows'] = False
            attr['readMovies'] = False
            return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_intent_name("GetPopular"))
def get_popular_intent_handler(handler_input):
    user_listtype = get_slot_value(handler_input=handler_input, slot_name="list")
    h = handler_input.request_envelope.context.system.user.access_token
    attr = handler_input.attributes_manager.session_attributes
    attr["movie"] = {}
    attr["show"] = {}
    attr = utils.test_session_attribs(attr)
    _listtype = utils.get_popular_list(user_listtype)
    url = "https://api.trakt.tv/movies/" + _listtype
    # If we are not auth, let the user know
    if h is None:
        handler_input.response_builder.speak(language.AUTH_ERROR)
        return handler_input.response_builder.response
    # Set all our headers for the trakt-api
    headers = utils.build_headers(h, clientid)
    print(url)
    r = requests.get(url, headers=headers)
    print(f"status code= {r.status_code}")
    if r.status_code == 200 or r.status_code == 201:
        boxoffice = json.loads(r.text)
        # print(json.dumps(boxoffice,sort_keys=True,indent=4))
        _notfound = {}
        _mywatchlist = trakt_api.list_cache(headers)
        if "error" in _mywatchlist:
            handler_input.response_builder.speak("I had trouble getting your lists from the trakt.tv api")
            return handler_input.response_builder.response
            # exit("error: 64")
        i = 0
        j = 0
        # for every item in the boxoffice
        for i in range(len(boxoffice)):
            # if 'movie' in boxoffice[i]:
            b = trakt_api.listparser(_mywatchlist, boxoffice[i], _listtype)
            if b is not None:
                _notfound[j] = b
                j += 1
                # print("got movie")
                # _notfound[i] = trakt_api.listparser(_mywatchlist,boxoffice[i],"movie")
            i += 1
        print(str(_notfound))
        if len(_notfound) > 0:
            attr['active_request'] = ''
            attr["movie"] = _notfound
            attr["show"] = {}
            attr['readBoth'] = False
            attr['readShows'] = False
            attr['readMovies'] = False
            attr['readBoxOffice'] = True
            attr['repeat'] = ''
            # TODO DONT KNOW IF ITS TRULY MISSING,
            # IT COULD BE THEY DONT HAVE THEM WATCHED/list BUT IN COLLECTION
            handler_input.response_builder.speak("you are missing " + str(len(_notfound))
                                                 + " out of 10 from the "
                                                 + _listtype
                                                 + " list. Do you want to hear the list ?").ask(
                "Do you want to hear the list ?")
            return handler_input.response_builder.response
            # print("you are missing "+str(len(_notfound))+" out of 10 from the "+_
            # listtype+" list. Do you want to hear the list ?")
            # save our list to session attributes
            # and then ask the user if they want to save
            # have and then deal with it in the AMAZON.YesIntent
        else:
            handler_input.response_builder.speak("You have all the items from this list")
            return handler_input.response_builder.response
            # print("you have all the items from this list")
    else:
        handler_input.response_builder.speak("I couldn't contact the trakt.tv api")
        return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_intent_name("FindShow"))
def find_show_handler(handler_input):
    """Handler for Find Show Intent"""

    # Get the value of the users auth token
    h = handler_input.request_envelope.context.system.user.access_token
    # If we are not auth, let the user know
    if h is None:
        reprompt = 's'
        handler_input.response_builder.speak(
            language.AUTH_ERROR).ask(reprompt)
        return handler_input.response_builder.response
    # Set all our headers for the trakt-api
    headers = utils.build_headers(h, clientid)
    # showName
    # return handler_input.response_builder.response
    movie = get_slot_value(handler_input=handler_input, slot_name="showName")
    # TODO search the movie var and strip  "on my list" from the end incase Alexa fucks up
    b = trakt_api.search(movie, headers, "show", True)
    if b['error']:
        # handle this
        reprompt = '_'
        handler_input.response_builder.speak(language.SHOW_404).ask(reprompt)
        return handler_input.response_builder.response
    # check if its a show or a movie
    # force our movie/show object into a small var to make things easier
    # we dont need this
    y = b['show']
    t = trakt_api.search_lists(y, b, headers, "show")
    if t['found']:
        # print(movie+" found on the list "+t['list'])
        reprompt = '_'
        handler_input.response_builder.speak(movie + " is already on the list " + t['list']).ask(reprompt)
        return handler_input.response_builder.response
    else:
        reprompt = '_'
        handler_input.response_builder.speak(movie + " isnt on any of your lists.").ask(reprompt)
        return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_intent_name("FindMovie"))
def find_movie_handler(handler_input):
    """Handler for Find Movie Intent"""

    # Get the value of the users auth token
    h = handler_input.request_envelope.context.system.user.access_token
    # If we are not auth, let the user know
    if h is None:
        handler_input.response_builder.speak(language.AUTH_ERROR).ask(language.AUTH_ERROR)
        return handler_input.response_builder.response
    # Set all our headers for the trakt-api
    headers = utils.build_headers(h, clientid)
    movie = get_slot_value(handler_input=handler_input, slot_name="movieName")
    # TODO search the movie var and strip  "on my list" from the end incase Alexa fucks up
    #
    b = trakt_api.search(movie, headers, "movie", True)
    if b['error']:
        # handle this
        reprompt = '_'
        handler_input.response_builder.speak("I couldnt find the movie you requested").ask(reprompt)
        return handler_input.response_builder.response
    # check if its a show or a movie
    # force our movie/show object into a small var to make things easier
    y = b["movie"]

    t = trakt_api.search_lists(y, b, headers, "movie")
    if t['found']:
        # print(movie+" found on the list "+t['list'])
        reprompt = movie + " is already on the list " + t['list']
        handler_input.response_builder.speak(reprompt).ask(reprompt)
        return handler_input.response_builder.response
    else:
        reprompt = movie + " isn't on any of your lists."
        handler_input.response_builder.speak(reprompt).ask(reprompt)
        return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
def help_intent_handler(handler_input):
    """Handler for Help Intent."""
    speech_text = "booop"
    reprompt = "booop."
    handler_input.response_builder.speak(speech_text).ask(reprompt)
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=lambda input: is_intent_name("AMAZON.CancelIntent")(input)
                    or is_intent_name("AMAZON.StopIntent")(input))
def cancel_and_stop_intent_handler(handler_input):
    """Single handler for Cancel and Stop Intent."""

    speech_text = "OK Mate calm down."
    attr = handler_input.attributes_manager.session_attributes
    attr['readShows'] = False
    attr['readMovies'] = False
    attr['readBoth'] = False
    attr['active_request'] = ''
    attr['repeat'] = ''
    attr['movie'] = {}
    attr['show'] = {}
    attr['readBoxOffice'] = False
    handler_input.response_builder.speak(speech_text).set_should_end_session(True)
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_request_type("SessionEndedRequest"))
def session_ended_request_handler(handler_input):
    """Handler for Session End."""

    logger.info(f"Session ended with reason: {handler_input.request_envelope.request.reason}")
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=lambda input: is_intent_name("AMAZON.YesIntent")(input)
                    or is_intent_name("AMAZON.RepeatIntent")(input))
def read_out_handler(handler_input):
    """Handler for Yes/Repeat Intent This is used as a list reader"""

    attr = utils.test_session_attribs(handler_input.attributes_manager.session_attributes)
    # Get the value of the users auth token
    h = handler_input.request_envelope.context.system.user.access_token
    # If we are not auth, let the user know
    if h is None:
        handler_input.response_builder.speak(language.AUTH_ERROR)
        return handler_input.response_builder.response
    _alexa_out = ''
    # Set all our headers for the trakt-api
    headers = utils.build_headers(h, clientid)

    # do we want to add the movies to our default list ?
    if attr['active_request'] == 'AddMovies':
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        attr, _alexa_out = utils.read_add_movies(persistent_attributes, attr, headers)
        handler_input.response_builder.speak(str(_alexa_out)).ask(language.REPEAT_LIST)
        return handler_input.response_builder.response

    # shows read out here
    if utils.read_shows_check(attr, is_intent_name("AMAZON.RepeatIntent")):
        attr, _alexa_out = utils.read_out_shows(attr)
        handler_input.response_builder.speak(str(_alexa_out)).ask(language.REPEAT_LIST)
        return handler_input.response_builder.response

    # movies read out here
    if attr['readMovies'] and not attr['readShows'] \
            or is_intent_name("AMAZON.RepeatIntent") and attr['repeat'] == 'readMovies':
        # movies read out here
        attr, _alexa_out = utils.read_out_movies(attr)
        handler_input.response_builder.speak(str(_alexa_out)).ask(language.REPEAT_LIST)
        return handler_input.response_builder.response

    # both read out here
    if attr['readBoth'] or is_intent_name("AMAZON.RepeatIntent") and attr['repeat'] == 'readBoth':
        attr, _alexa_out = utils.read_out_both(attr, _alexa_out)
        handler_input.response_builder.speak(str(_alexa_out)).ask(language.REPEAT_LIST)
        return handler_input.response_builder.response

    # read out box office
    # repeat wont work
    if attr['readBoxOffice'] or is_intent_name("AMAZON.RepeatIntent") and attr['repeat'] == 'readBoxOffice':
        attr, _alexa_out = utils.read_box_office(attr)
        handler_input.response_builder.speak(str(_alexa_out)).ask(language.REPEAT_LIST)
        return handler_input.response_builder.response

    # user got here with no lists
    attr['readShows'] = False
    attr['readMovies'] = False
    attr['readBoth'] = False
    attr['repeat'] = ''
    attr['readBoxOffice'] = False
    handler_input.response_builder.speak("Im sorry I didn't understand.")
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.NoIntent"))
def no_handler(handler_input):
    """Handler for No Intent, only if the player said no for
    a new game.
    """
    session_attr = handler_input.attributes_manager.session_attributes
    session_attr['game_state'] = "ENDED"
    session_attr['ended_session_count'] = ""
    handler_input.attributes_manager.persistent_attributes = session_attr
    handler_input.attributes_manager.save_persistent_attributes()
    speech_text = "Ok. See you next time!!"
    handler_input.response_builder.speak(speech_text)
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=lambda input: is_intent_name("AMAZON.FallbackIntent")(input))
def fallback_handler(handler_input):
    """AMAZON.FallbackIntent is only available in en-US locale.
    This handler will not be triggered except in that locale,
    so it is safe to deploy on any locale.
    """

    # session_attr = handler_input.attributes_manager.session_attributes
    speech_text = ""
    reprompt = "Say yes to start the game or no to quit."
    handler_input.response_builder.speak(speech_text).ask(reprompt)
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=lambda input: True)
def unhandled_intent_handler(handler_input):
    """Handler for all other unhandled requests."""

    speech = "Say yes to continue or no to end the game!!"
    handler_input.response_builder.speak(speech).ask(speech)
    return handler_input.response_builder.response


@sb.exception_handler(can_handle_func=lambda i, e: True)
def all_exception_handler(handler_input, exception):
    """Catch all exception handler, log exception and
    respond with custom message.
    """
    logger.error(exception, exc_info=True)
    # speech = "Sorry, I can't understand that. Please say again!!"
    speech = "error: " + str(exception)
    handler_input.response_builder.speak(speech).ask(speech)
    return handler_input.response_builder.response


@sb.global_response_interceptor()
def log_response(handler_input, response):
    """Response logger."""
    logger.info("Response: {}".format(response))


lambda_handler = sb.lambda_handler()
