# -*- coding: utf-8 -*-
"""Simple Alexa app."""

import random  # noqa F401
import logging
import json
import config
import prompts
import bak
import os
import requests
import ask_sdk_core.utils as ask_utils  # noqa F401
import locale  # noqa F401
import gettext  # noqa F401
import re  # noqa: F401

from datetime import datetime
from ask_sdk_s3.adapter import S3Adapter
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.utils import get_slot_value
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model import Response, session  # noqa F401
from ask_sdk_core.skill_builder import SkillBuilder  # noqa F401
from ask_sdk_core.dispatch_components import (AbstractRequestHandler,
                                              AbstractExceptionHandler,
                                              AbstractRequestInterceptor,
                                              AbstractResponseInterceptor)  # noqa F401
from ask_sdk_model.ui import SimpleCard
from ask_sdk_core.skill_builder import CustomSkillBuilder

s3_adapter = S3Adapter(bucket_name=os.environ["S3_PERSISTENCE_BUCKET"])
sb = CustomSkillBuilder(persistence_adapter=s3_adapter)
logger = logging.getLogger(__name__)
clientid = config.client_id
user = 'me'
is_auth = False

# if you want a custom list use Set list Intent
our_list = 'watchlist'
_usecustomlist = False

# We dont need these for Alexa but lets keep em around for DEBUG offline
access_token = ''
expires_in = ''
refresh_token = ''
token_type = ''
value = ''
movie = ''
showtype = "movie"
speech_text = ''
_listnamepretty = ''

# our default headers, not really needed for Alexa
headers = {'Content-Type': 'application/json',
           'Authorization': 'Bearer ' + access_token,
           'trakt-api-version': '2',
           'trakt-api-key': clientid}


# Our action for finding if a show/movie is on our calendar
class WhatsOn(AbstractRequestHandler):
    """Handler for WhatsOn Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        attr = handler_input.attributes_manager.session_attributes  # noqa F841
        return is_intent_name("WhatsOn")(handler_input)

    def handle(self, handler_input):
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
            reprompt = 's'
            handler_input.response_builder.speak(
                "There is a problem with authorisation, "
                "please logout and log back in.")
            return handler_input.response_builder.response
        # Set all our headers for the trakt-api
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer ' + h,
                   'trakt-api-version': '2',
                   'trakt-api-key': clientid}
        # return handler_input.response_builder.response
        # _date gives 2020-04-17 format
        _type = get_slot_value(handler_input=handler_input, slot_name="typeMedia")
        _date = get_slot_value(handler_input=handler_input, slot_name="thedate")
        if _date is None:
            x = datetime.now()
            z = x.strftime('%Y-%m-%d')
        else:
            z = bak.validate(_date)
            # x=datetime.strptime(_date,'%Y-%m-%d')
            # z=x.strftime('%Y-%m-%d')
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
                    print("status code= " + str(r.status_code))  # we couldnt contact trakt.tv
                n = datetime.now()
                m = n.strftime('%Y-%m-%d')
                reprompt = ''
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
                        handler_input.response_builder.speak("You have " + str(
                            _movieitemcount) + " new movies on today. Would you like me to read the list out ?").ask(
                            reprompt)
                        attr["readMovies"] = True
                        return handler_input.response_builder.response
                        # return build_response(attributes,build_speechlet_response("radar",
                        # "speech_output", reprompt,False))
                    else:
                        handler_input.response_builder.speak(
                            "You have " + str(_movieitemcount) + " new movies on " + str(
                                z) + ". Would you like me to read the list out ?").ask(reprompt)
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
                    handler_input.response_builder.speak("I couldnt reach the trakt.tv API").ask("reprompt")
                    return handler_input.response_builder.response  # print("status code= "+str(r.status_code))
                n = datetime.now()
                m = n.strftime('%Y-%m-%d')
                reprompt = 'would you like me to read them out ?'
                if (_showitemcount - 1) < 0:
                    if z == m:
                        handler_input.response_builder.speak("you have no new episodes on today")
                        return handler_input.response_builder.response
                    else:
                        handler_input.response_builder.speak("you have no new episodes on " + str(z))
                        return handler_input.response_builder.response  # print("you have no new movies or episodes on today")
                else:
                    if z == m:
                        handler_input.response_builder.speak("You have " + str(
                            _showitemcount) + " new episodes on today. Would you like me to read the list out ?").ask(
                            reprompt)
                        attr["readShows"] = True
                        return handler_input.response_builder.response
                    else:
                        handler_input.response_builder.speak(
                            "You have " + str(_showitemcount) + " new episodes on " + str(
                                z) + ". Would you like me to read the list out ?").ask(reprompt)
                        attr["readShows"] = True
                        return handler_input.response_builder.response
            # not sure what we got
            else:
                handler_input.response_builder.speak(
                    "Im sorry i couldnt understand what you type you wanted").ask(
                    "Try saying, Alexa ask Radar what is on.")
                return handler_input.response_builder.response  # no idea what they user wanted
        else:
            handler_input.response_builder.speak(
                "Im sorry i couldnt understand what you type you wanted").ask(
                "Try saying, Alexa ask Radar what is on.")
            return handler_input.response_builder.response  # no idea what they user wanted
        # we didnt get a media, get both
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
            print("status code= " + str(r.status_code))
        n = datetime.now()
        m = n.strftime('%Y-%m-%d')
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
                handler_input.response_builder.speak("You have " + str(_movieitemcount) + " new movies and " + str(
                    _showitemcount) + " episodes on today. Would you like me to read the list out ?").ask(reprompt)
                attr['readBoth'] = True
                attr['readShows'] = False
                attr['readMovies'] = False
                return handler_input.response_builder.response
            else:
                handler_input.response_builder.speak(
                    "You have " + str(_movieitemcount) + " new movies and " + str(
                        _showitemcount) + " episodes on " + str(
                        z) + " Would you like me to read the list out ?").ask(reprompt)
                attr['readBoth'] = True
                attr['readShows'] = False
                attr['readMovies'] = False
                return handler_input.response_builder.response


# Our action for finding if a show is on one of our lists
class FindShow(AbstractRequestHandler):
    """Handler for FindShow Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("FindShow")(handler_input)

    def handle(self, handler_input):
        # Get the value of the users auth token
        h = handler_input.request_envelope.context.system.user.access_token
        showtype = 'show'  # noqa F841
        # If we are not auth, let the user know
        if h is None:
            reprompt = 's'
            handler_input.response_builder.speak(
                "There is a problem with authorisation, please logout and log back in.").ask(reprompt)
            return handler_input.response_builder.response
        # Set all our headers for the trakt-api
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + h, 'trakt-api-version': '2',
                   'trakt-api-key': clientid, }
        # showName
        # return handler_input.response_builder.response
        movie = get_slot_value(handler_input=handler_input, slot_name="showName")
        # TODO search the movie var and strip  "on my list" from the end incase Alexa fucks up
        #
        b = bak.search(movie, headers, "show", True)
        if b['error']:
            # handle this
            reprompt = '_'
            handler_input.response_builder.speak("I couldnt find the show you requested").ask(reprompt)
            return handler_input.response_builder.response

        # check if its a show or a movie
        # force our movie/show object into a small var to make things easier
        # we dont need this
        y = b['show']

        t = bak.search_lists(y, b, headers, "show")
        if t['found']:
            # print(movie+" found on the list "+t['list'])
            reprompt = '_'
            handler_input.response_builder.speak(movie + " is already on the list " + t['list']).ask(reprompt)
            return handler_input.response_builder.response
        else:
            reprompt = '_'
            handler_input.response_builder.speak(movie + " isnt on any of your lists.").ask(reprompt)
            return handler_input.response_builder.response


# Our action for finding if a movie is on one of our lists
class FindMovie(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("FindMovie")(handler_input)

    def handle(self, handler_input):
        # Get the value of the users auth token
        h = handler_input.request_envelope.context.system.user.access_token
        showtype = "movie"  # noqa F841
        # If we are not auth, let the user know
        if h is None:
            reprompt = 's'
            handler_input.response_builder.speak(
                "There is a problem with authorisation, please logout and log back in.").ask(reprompt)
            return handler_input.response_builder.response
        # Set all our headers for the trakt-api
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + h, 'trakt-api-version': '2',
                   'trakt-api-key': clientid, }
        movie = get_slot_value(handler_input=handler_input, slot_name="movieName")
        # TODO search the movie var and strip  "on my list" from the end incase Alexa fucks up
        #
        b = bak.search(movie, headers, "movie", True)
        if b['error']:
            # handle this
            reprompt = '_'
            handler_input.response_builder.speak("I couldnt find the movie you requested").ask(reprompt)
            return handler_input.response_builder.response

        # check if its a show or a movie
        # force our movie/show object into a small var to make things easier
        y = b["movie"]

        t = bak.search_lists(y, b, headers, "movie")
        if t['found']:
            # print(movie+" found on the list "+t['list'])
            reprompt = '_'
            handler_input.response_builder.speak(movie + " is already on the list " + t['list']).ask(reprompt)
            return handler_input.response_builder.response
        else:
            reprompt = '_'
            handler_input.response_builder.speak(movie + " isnt on any of your lists.").ask(reprompt)
            return handler_input.response_builder.response


# Our action for removing Show
class RemoveShow(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("RemoveShow")(handler_input)

    def handle(self, handler_input):
        # Get the value of the users auth token
        h = handler_input.request_envelope.context.system.user.access_token
        # If we are not auth, let the user know
        if h is None:
            reprompt = 's'
            handler_input.response_builder.speak(
                "There is a problem with authorisation, please logout and log back in.").ask(reprompt)
            return handler_input.response_builder.response
        # Set all our headers for the trakt-api
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + h, 'trakt-api-version': '2',
                   'trakt-api-key': clientid}
        # TODO make sure we change I,II,II type movies to 1,2,3
        # and vice versa
        # _usecustomlist = bool
        _list = get_slot_value(handler_input=handler_input, slot_name="list_name")
        movie = str(get_slot_value(handler_input=handler_input, slot_name="showName"))

        # get our persistent_attributes
        attr = handler_input.attributes_manager.persistent_attributes
        try:
            _perlist = attr['list']
            _usecustomlist = attr['usecustomlist']
        except:  # noqa E722
            _perlist = None
            _usecustomlist = False
        # user gave us nothing lets do some checks to make sure we have saved attributes
        if _list is None:
            # they didnt give us a list use the default
            # attr = handler_input.attributes_manager.persistent_attributes
            # _perlist = attr['list']
            # if default isnt set use watchlist
            if _perlist is None:
                _list = 'watchlist'
                _usecustomlist = False
            elif _perlist.lower() == 'watchlist' or _perlist.lower() == 'watch list':
                _usecustomlist = False
                _list = _perlist
            else:
                _usecustomlist = True
                _list = _perlist
        else:
            _usecustomlist = True
            # this doesnt work
            _liststring = str(_list)  # noqa F841
            if _list.lower() == 'watchlist' or _list.lower() == 'watch list':
                # ((str(_list)).lower())=='watchlist'
                # ((str(_list)).lower())=='watch list'
                _usecustomlist = False
        # if we got nothing from the user and AND we have no pers data  set no custom list
        if _usecustomlist is None:
            _usecustomlist = False

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
                        if bak.parse_delete_search('show', headers, dcode[i]['show'], _list, _usecustomlist, True):
                            reprompt = 's'
                            # media_name, media_type, a_list
                            bak.notify(movie, "show", _list, "removed")
                            handler_input.response_builder.speak("I have deleted " + o + " from the list " + _list).ask(
                                reprompt)
                            return handler_input.response_builder.response
                            # return  # print("we finished and deleted")  # exit("deleted")
                        else:
                            # return
                            reprompt = 's'
                            handler_input.response_builder.speak(
                                "I had trouble deleting " + o + " from the list " + _list).ask(reprompt)
                            return handler_input.response_builder.response
                            # print("we found the film but there was an error deleting")  # exit("not deleted")
                    i += 1
                # if we failed to find the movie
                if _moviefound is False:
                    # print("we couldnt find the film")
                    reprompt = 's'
                    handler_input.response_builder.speak("i couldnt find " + movie + " on the list " + _list).ask(
                        reprompt)
                    return handler_input.response_builder.response
            # if our first request to trakt fails
            else:
                reprompt = 's'
                handler_input.response_builder.speak('I couldnt contact Trakt.tv API .' + url).ask(reprompt)
                return handler_input.response_builder.response  # print('Error with the request to trak.tv')
        # if our user didnt give us a list or they are using the watch list
        else:
            # WE DIDNT RECIEVE A LIST
            # TODO make sure we change I,II,II type movies to 1,2,3
            # and vice versa
            movie = str(get_slot_value(handler_input=handler_input, slot_name="showName"))
            # we assume the users is using a custom list
            # next if statement should take care of it
            _usecustomlist = True
            reprompt = ''
            # search for movie and get the object
            b = bak.search(movie, headers, "show", False)
            if b['error']:
                # handle this
                reprompt = '_'
                handler_input.response_builder.speak("I couldnt find the show you requested").ask(reprompt)
                return handler_input.response_builder.response
            # force our movie/show object into a small var to make things easier
            y = b['show']
            if bak.parse_delete_search('show', headers, y, _list, False, False):
                reprompt = 's'
                # media_name, media_type, a_list
                bak.notify(movie, "show", _list, "removed")
                handler_input.response_builder.speak("I have deleted " + movie + " from the list " + _list)
                return handler_input.response_builder.response
            else:
                handler_input.response_builder.speak("i couldn't delete " + movie + " from the list " + _list).ask(
                    reprompt)
                return handler_input.response_builder.response
            reprompt = 'Would you like me to remove it from your watchlist ?'
            handler_input.response_builder.speak('No list provieded. or error').ask(reprompt)
            return handler_input.response_builder.response


# Our action for removing movie
class RemoveMovie(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("RemoveMovie")(handler_input)

    def handle(self, handler_input):
        # Get the value of the users auth token
        h = handler_input.request_envelope.context.system.user.access_token
        # If we are not auth, let the user know
        if h is None:
            reprompt = 's'
            handler_input.response_builder.speak(
                "There is a problem with authorisation, please logout and log back in.").ask(reprompt)
            return handler_input.response_builder.response
        # Set all our headers for the trakt-api
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + h, 'trakt-api-version': '2',
                   'trakt-api-key': clientid, }
        # TODO make sure we change I,II,II type movies to 1,2,3
        # and vice versa
        # _usecustomlist = bool
        _list = get_slot_value(handler_input=handler_input, slot_name="list_name")
        movie = str(get_slot_value(handler_input=handler_input, slot_name="movieName"))

        # get our persistent_attributes
        attr = handler_input.attributes_manager.persistent_attributes
        try:
            _perlist = attr['list']
            _usecustomlist = attr['usecustomlist']
        except ValueError:
            _perlist = None
            _usecustomlist = False
        # TODO: move this list check to a function to make things neater/more readable
        # user gave us nothing lets do some checks to make sure we have saved attributes
        if _list is None:
            # they didnt give us a list use the default
            # attr = handler_input.attributes_manager.persistent_attributes
            # _perlist = attr['list']
            # if default isnt set use watchlist
            if _perlist is None:
                _list = 'watchlist'
                _usecustomlist = False
            elif _perlist.lower() == 'watchlist' or _perlist.lower() == 'watch list':
                _usecustomlist = False
                _list = _perlist
            else:
                _usecustomlist = True
                _list = _perlist
        else:
            _usecustomlist = True
            # this doesnt work
            _liststring = str(_list)  # noqa F841
            if _list.lower() == 'watchlist' or _list.lower() == 'watch list':
                # ((str(_list)).lower())=='watchlist'
                # ((str(_list)).lower())=='watch list'
                _usecustomlist = False
        # if we got nothing from the user and AND we have no pers data  set no custom list
        if _usecustomlist is None:
            _usecustomlist = False

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
                        _id = dcode[i]["movie"]['ids']['trakt']  # noqa F841
                        # print("we found it")
                        # print(json.dumps(dcode[i], sort_keys=True, indent=4))
                        if bak.parse_delete_search("movie", headers, dcode[i]["movie"], _list, _usecustomlist, True):
                            reprompt = 's'
                            handler_input.response_builder.speak("I have deleted " + o + " from the list " + _list).ask(
                                reprompt)
                            return handler_input.response_builder.response
                            # return  # print("we finished and deleted")  # exit("deleted")
                        else:
                            # return
                            reprompt = 's'
                            handler_input.response_builder.speak(
                                "I had trouble deleting " + o + " from the list " + _list).ask(reprompt)
                            return handler_input.response_builder.response
                            # print("we found the film but there was an error deleting")  # exit("not deleted")
                    i += 1
                # if we failed to find the movie
                if _moviefound is False:
                    # print("we couldnt find the film")
                    reprompt = 's'
                    handler_input.response_builder.speak("i couldnt find " + movie + " on the list " + _list).ask(
                        reprompt)
                    return handler_input.response_builder.response
            # if our first request to trakt fails
            else:
                reprompt = 's'
                handler_input.response_builder.speak('I couldnt contact Trakt.tv API .' + url).ask(reprompt)
                return handler_input.response_builder.response  # print('Error with the request to trak.tv')
        # if our user didnt give us a list or they are using the watch list
        else:
            # WE DIDNT RECIEVE A LIST
            # TODO make sure we change I,II,II type movies to 1,2,3
            # and vice versa
            movie = str(get_slot_value(handler_input=handler_input, slot_name="movieName"))
            # we assume the users is using a custom list
            # next if statement should take care of it
            _usecustomlist = True
            reprompt = ''
            # search for movie and get the object
            b = bak.search(movie, headers, "movie", False)
            if b['error']:
                # handle this
                reprompt = '_'
                handler_input.response_builder.speak("I couldnt find the movie you requested").ask(reprompt)
                return handler_input.response_builder.response
            # force our movie/show object into a small var to make things easier
            y = b["movie"]
            if bak.parse_delete_search("movie", headers, y, _list, False, False):
                reprompt = 's'
                # media_name, media_type, a_list
                bak.notify(movie, b['type'], _list, "removed")
                handler_input.response_builder.speak(
                    "I have deleted " + movie + " from the list " + _list)  # .ask(reprompt)
                return handler_input.response_builder.response
            else:
                handler_input.response_builder.speak(
                    "i couldn't delete " + movie + " from the list " + _list)  # .ask(reprompt)
                return handler_input.response_builder.response
            reprompt = 'Would you like me to remove it from your watchlist ?'
            handler_input.response_builder.speak('No list provieded. or error').ask(reprompt)
            return handler_input.response_builder.response


# Our action for letting the user pick their own custom list
class ChooseList(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        attr = handler_input.attributes_manager.session_attributes  # noqa F841
        return is_intent_name("ChooseList")(handler_input)

    def handle(self, handler_input):
        # handler_input.response_builder.speak("List chooser").ask("reprompt")
        # TODO Check that the user has supplied a value or we will throw errors
        # get the value of listName and throw it onto _thelist
        _thelist = get_slot_value(handler_input=handler_input, slot_name="listName")

        # Get the value of the users auth token
        h = handler_input.request_envelope.context.system.user.access_token

        # If we are not auth, let the user know
        if h is None:
            reprompt = 's'  # noqa F841
            handler_input.response_builder.speak(
                "There is a problem with authorisation, please logout and log back in.").ask("reprompt")
            return handler_input.response_builder.response
        # Set all our headers for the trakt-api
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + h, 'trakt-api-version': '2',
                   'trakt-api-key': clientid}
        session_attr = handler_input.attributes_manager.session_attributes
        # TODO check if the list is empty and different
        # NEED TO CHECK IF THE LIST ISNT NULL FIRST
        # if the user is wanting their default watch list we can save time and use defaults
        if _thelist is not None:
            if _thelist.lower() == 'watchlist' or _thelist.lower() == 'watch list':
                # need to set _custom list to false and set it to the persistant session
                # give feedback to the user
                handler_input.response_builder.speak("Your List has been set to the default. This is the watchlist")
                _usecustomlist = False
                # start saving the persistent attributes
                session_attr['usecustomlist'] = False
                session_attr['list'] = 'watchlist'
                # savesessionattributes as persistentattributes
                handler_input.attributes_manager.persistent_attributes = session_attr
                handler_input.attributes_manager.save_persistent_attributes()
                return handler_input.response_builder.response
        # if we dont have shit
        # session_attr['list'] can cause issues if its not already set
        if _thelist is None and session_attr['list'] is None or _thelist == '' and session_attr['list'] == '':
            handler_input.response_builder.speak(
                "Your List has been set to the default. This is the watchlist")  # .ask("reprompt")
            _usecustomlist = False
            # start saving the persistent attributes
            session_attr = handler_input.attributes_manager.session_attributes
            session_attr['usecustomlist'] = False
            session_attr['list'] = 'watchlist'
            # savesessionattributes as persistentattributes
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
            if _foundlist is False:
                handler_input.response_builder.speak(
                    "We couldnt find that list. Your list has been set to the default. This is the watchlist").ask(
                    "reprompt")
                _usecustomlist = False  # noqa F841
                # start saving the persistent attributes
                session_attr = handler_input.attributes_manager.session_attributes
                session_attr['usecustomlist'] = False
                session_attr['list'] = 'watchlist'
                # savesessionattributes as persistentattributes
                handler_input.attributes_manager.persistent_attributes = session_attr
                handler_input.attributes_manager.save_persistent_attributes()
                return handler_input.response_builder.response

            # we found the list, save it and we can use it for all add requests
            handler_input.response_builder.speak("Your List has been set to " + _thelist)  # .ask("Is this correct ?")
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
            handler_input.response_builder.speak("There was a problem reaching Tracked TV").ask("")
            return handler_input.response_builder.response


class AddMovie(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_request_type("LaunchRequest")(handler_input) or is_intent_name("AddMovie")(handler_input))

    def handle(self, handler_input):
        # attr=handler_input.attributes_manager.persistent_attributes
        # _list=str(attr['list'])
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
        showtype = "movie"
        # If we are not auth, let the user know
        if h is None:
            reprompt = 's'
            handler_input.response_builder.speak(
                "There is a problem with authorisation, please logout and log back in.")  # .ask(reprompt)
            return handler_input.response_builder.response
        # Set all our headers for the trakt-api
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + h, 'trakt-api-version': '2',
                   'trakt-api-key': clientid}

        # Get the movie name and throw it onto the movie var
        movie = get_slot_value(handler_input=handler_input, slot_name="movieName")
        _list = get_slot_value(handler_input=handler_input, slot_name="list_name")
        # reprompt = "Are you sure you want to add "+movie+' to your list ?'

        # user gave us nothing lets do some checks to make sure we have saved attributes
        if _list is None or _list == '':
            # TODO find a better way to match list names
            # they didnt give us a list use the default

            # if default isnt set use watchlist
            if "list" in _perattr:
                if _perattr["list"] != 'watchlist' or _perattr["list"] != 'watch list':
                    _list = _perattr["list"]
                    _usecustomlist = True
                else:
                    _list = 'watchlist'
                    _usecustomlist = False
            else:
                _list = 'watchlist'
                _usecustomlist = False
        else:
            # TODO CHECK IF THE LIST IS watchlist
            _usecustomlist = True  # noqa F841
            # this doesnt work
            _liststring = str(_list)  # noqa F841
            if _list.lower() == 'watchlist' or _list.lower() == 'watch list':
                _usecustomlist = False  # noqa F841
        print(str(_usecustomlist))
        # search for move and get the object
        b = bak.search(movie, headers, showtype, True)
        if b['error']:
            # handle this
            reprompt = '_'  # noqa F841
            handler_input.response_builder.speak("I couldnt find the show you requested")  # .ask(reprompt)
            return handler_input.response_builder.response
        # force our movie/show object into a small var to make things easier
        y = b["movie"]
        # dig through our search and add the movie/show to our list or our Watchlist
        bak.parse_search(b['type'], headers, y, _list, _usecustomlist, True)
        # media_name, media_type, a_list
        bak.notify(movie, b['type'], _list)
        handler_input.response_builder.speak(movie + " has been added to your " + _list + " list")  # .ask(reprompt)
        return handler_input.response_builder.response


class AddShow(AbstractRequestHandler):
    """Handler for addShow Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AddShow")(handler_input)

    def handle(self, handler_input):
        h = handler_input.request_envelope.context.system.user.access_token
        showtype = 'show'
        # If we are not auth, let the user know
        if h is None:
            reprompt = 's'
            handler_input.response_builder.speak(
                "There is a problem with authorisation, please logout and log back in.").ask(reprompt)
            return handler_input.response_builder.response
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + h, 'trakt-api-version': '2',
                   'trakt-api-key': clientid}

        # get our persistent_attributes
        _perattr = handler_input.attributes_manager.persistent_attributes
        # _perlist = _perattr['list']
        # _usecustomlist = _perattr['usecustomlist']
        # logger.debug("Alexa Response: {}".format(response))
        # speech_text = 'boop2'  # + str(format(response))
        movie = get_slot_value(handler_input=handler_input, slot_name="showName")
        _list = get_slot_value(handler_input=handler_input, slot_name="list_name")
        reprompt = "Are you sure you want to add " + movie + ' to your list ?'

        # if default isnt set use watchlist
        if "list" in _perattr:
            if _perattr["list"] != 'watchlist' or _perattr["list"] != 'watch list':
                _list = _perattr["list"]
                _usecustomlist = True
            else:
                _list = 'watchlist'
                _usecustomlist = False
        else:
            _list = 'watchlist'
            _usecustomlist = False

        # search for move and get the object
        b = bak.search(movie, headers, showtype, False)
        if b['error']:
            # handle this
            handler_input.response_builder.speak("I couldnt find the show you requested")  # .ask(reprompt)
            return handler_input.response_builder.response
        # print("trakt id= "+str(y['ids']['trakt']))

        y = b['show']
        # dig through our search and add the movie/show to our list or our Watchlist
        bak.parse_search(b['type'], headers, y, _list, _usecustomlist, True)
        bak.notify(movie, b['type'], _list)
        handler_input.response_builder.speak(movie + " show has been added to your list " + str(_list))
        # .ask(reprompt)
        return handler_input.response_builder.response


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In HelpIntentHandler")

        # get localization data
        data = handler_input.attributes_manager.request_attributes["_"]

        speech = data[prompts.HELP_MESSAGE]
        reprompt = data[prompts.HELP_REPROMPT]
        handler_input.response_builder.speak(speech).ask(reprompt).set_card(
            SimpleCard(data[prompts.SKILL_NAME], speech))
        return handler_input.response_builder.response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.CancelIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In CancelOrStopIntentHandler")
        # get localization data
        data = handler_input.attributes_manager.request_attributes["_"]
        speech = data[prompts.STOP_MESSAGE]  # noqa F841
        # response_builder.set_should_end_session(True)
        handler_input.response_builder.speak("lataaaa bitch")
        return handler_input.response_builder.response


class FallbackIntentHandler(AbstractRequestHandler):
    """Handler for Fallback Intent.

    AMAZON.FallbackIntent is only available in en-US locale.
    This handler will not be triggered except in that locale,
    so it is safe to deploy on any locale.
    """

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")

        # get localization data
        data = handler_input.attributes_manager.request_attributes["_"]
        speech = data[prompts.FALLBACK_MESSAGE]
        handler_input.response_builder.speak(speech)
        return handler_input.response_builder.response


class LocalizationInterceptor(AbstractRequestInterceptor):
    """
    Add function to request attributes, that can load locale specific data.
    """

    def process(self, handler_input):
        locale = handler_input.request_envelope.request.locale  # noqa F811
        logger.info("Locale is {}".format(locale))

        # localized strings stored in language_strings.json
        with open("language_strings.json") as language_prompts:
            language_data = json.load(language_prompts)
        # set default translation data to broader translation
        if locale[:2] in language_data:
            data = language_data[locale[:2]]
            # if a more specialized translation exists, then select it instead
            # example: "fr-CA" will pick "fr" translations first, but if "fr-CA" translation exists,
            # then pick that instead
            if locale in language_data:
                data.update(language_data[locale])
        else:
            data = language_data[locale]
        handler_input.attributes_manager.request_attributes["_"] = data


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("SessionEndedRequest")(handler_input)  # AMAZON.NoIntent

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In SessionEndedRequestHandler")
        logger.info("Session ended reason: {}".format(handler_input.request_envelope.request.reason))
        # response_builder.set_should_end_session(True)
        return handler_input.response_builder.response


# Exception Handler
class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Catch all exception handler, log exception and
    respond with custom message.
    """

    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.info("In CatchAllExceptionHandler")
        logger.error(exception, exc_info=True)

        handler_input.response_builder.speak("error: " + str(exception))
        # response_builder.set_should_end_session(True)
        return handler_input.response_builder.response


# Request and Response loggers
class RequestLogger(AbstractRequestInterceptor):
    """Log the alexa requests."""

    def process(self, handler_input):
        # type: (HandlerInput) -> None
        logger.debug("Alexa Request: {}".format(handler_input.request_envelope.request))


class ResponseLogger(AbstractResponseInterceptor):
    """Log the alexa responses."""

    def process(self, handler_input, response):
        # type: (HandlerInput, Response) -> None
        logger.debug("Alexa Response: {}".format(response))


class JustStop(AbstractRequestHandler):
    """AMAZON.NoIntent"""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.NoIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        attr = handler_input.attributes_manager.session_attributes
        attr['readShows'] = False
        attr['readMovies'] = False
        attr['readBoth'] = False
        attr['active_request'] = ''
        attr['repeat'] = ''
        attr['movie'] = {}
        attr['show'] = {}
        attr['readBoxOffice'] = False
        handler_input.response_builder.speak("OK Mate calm down.")
        return handler_input.response_builder.response


# readout function
# AMAZON.YesIntent
class ReadBothOut(AbstractRequestHandler):
    """YesIntent Handler"""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.YesIntent")(handler_input) or is_intent_name("AMAZON.RepeatIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        attr = handler_input.attributes_manager.session_attributes
        try:
            attr['readShows']
        except ValueError:
            attr['readShows'] = False
        try:
            attr['readMovies']
        except ValueError:
            attr['readMovies'] = False
        try:
            attr['readBoth']
        except ValueError:
            attr['readBoth'] = False
        try:
            attr['repeat']
        except ValueError:
            attr['repeat'] = ''
        try:
            attr['active_request']
        except ValueError:
            attr['active_request'] = ''
        _alexaOut = ''
        # do we want to add the movies to our defualt list ?
        if attr['active_request'] == 'AddMovies':
            # movies read out here
            x = attr["movie"]
            _size = len(x)
            logger.info("active_request")
            _alexaOut = 'Here is the list of movies that i have added... '
            i = 0
            _perattr = handler_input.attributes_manager.persistent_attributes
            # Get the value of the users auth token
            h = handler_input.request_envelope.context.system.user.access_token
            # If we are not auth, let the user know
            if h is None:
                handler_input.response_builder.speak(
                    "There is a problem with authorisation, please logout and log back in.")
                return handler_input.response_builder.response
            # Set all our headers for the trakt-api
            headers = {'Content-Type': 'application/json',
                       'Authorization': 'Bearer ' + h,
                       'trakt-api-version': '2',
                       'trakt-api-key': clientid}
            # TODO find a better way to match list names
            # they didnt give us a list use the default
            # if a list isnt set use watchlist
            if "list" in _perattr:
                _list = _perattr["list"]
                _usecustomlist = True  # noqa F841
            else:
                _list = 'watchlist'
                _usecustomlist = False  # noqa F841
            while i < _size:
                # for j in range(len(dcode2)):
                # we need to parse the list and try to find the movie requested
                if bak.addOneMovie(x[str(i)], _usecustomlist, headers, _list):
                    _alexaOut += str(",  " + x[str(i)]['title'])
                else:
                    _alexaOut += str(" ")
                i += 1
            handler_input.response_builder.speak(str(_alexaOut)).ask("Say Repeat to hear the list again")
            attr['readShows'] = False
            attr['readMovies'] = False
            attr['readBoth'] = False
            attr['readBoxOffice'] = False
            attr['active_request'] = ''
            attr['repeat'] = ''
            attr['show'] = {}
            attr['movie'] = {}
            return handler_input.response_builder.response
        # shows read out here
        if attr['readShows'] and not attr['readMovies'] or is_intent_name("AMAZON.RepeatIntent") and \
                attr['repeat'] == 'readShows':
            attr = handler_input.attributes_manager.session_attributes
            x = attr["show"]
            _size = len(x)
            logger.info("readShows")
            _alexaOut = 'Here is the list of shows you asked for,  '
            i = 0
            while i < _size:
                # for j in range(len(dcode2)):
                _alexaOut += str(",  " + x[str(i)])
                i += 1
            handler_input.response_builder.speak(str(_alexaOut)).ask("Say Repeat to hear the list again")
            attr['readShows'] = False
            attr['readBoxOffice'] = False
            attr['readMovies'] = False
            attr['readBoth'] = False
            attr['repeat'] = 'readShows'
            return handler_input.response_builder.response
        # movies read out here
        if attr['readMovies'] and not attr['readShows'] or \
                is_intent_name("AMAZON.RepeatIntent") and attr['repeat'] == 'readMovies':
            # movies read out here
            attr = handler_input.attributes_manager.session_attributes
            x = attr["movie"]
            _size = len(x)
            logger.info("readMovies")
            _alexaOut = 'Here is the list of movies you asked for,  '
            i = 0
            while i < _size:
                # for j in range(len(dcode2)):
                # we need to parse the list and try to find the movie requested
                _alexaOut += str(",  " + x[str(i)])
                i += 1
            handler_input.response_builder.speak(str(_alexaOut)).ask("Say Repeat to hear the list again")
            attr['readShows'] = False
            attr['readMovies'] = False
            attr['readBoth'] = False
            attr['readBoxOffice'] = False
            attr['repeat'] = 'readMovies'
            return handler_input.response_builder.response
        # both read out here
        if attr['readBoth'] or is_intent_name("AMAZON.RepeatIntent") and attr['repeat'] == 'readBoth':
            x = attr["show"]
            z = attr["movie"]
            _size = len(x)
            _size2 = len(z)
            if (_size - 1) < 0:
                _alexaOut += str(" ")
            else:
                _alexaOut += str('Here is the list of shows you asked for....  ')
            i = 0
            while i < _size:
                _alexaOut += str(",  " + x[str(i)])
                i += 1
            j = 0
            if (_size2 - 1) < 0:
                _alexaOut += str(" ")
            else:
                _alexaOut += str(",  Here are the list of movies, ")
            while j < _size2:
                _alexaOut += str(z[str(j)] + ",  ")
                j += 1
            attr['readShows'] = False
            attr['readMovies'] = False
            attr['readBoth'] = False
            attr['readBoxOffice'] = False
            attr['repeat'] = 'readBoth'
            handler_input.response_builder.speak(str(_alexaOut)).ask("Say Repeat to hear the list again")
            return handler_input.response_builder.response
        # read out box office
        # repeat wont work
        if attr['readBoxOffice'] or is_intent_name("AMAZON.RepeatIntent") and attr['repeat'] == 'readBoxOffice':
            # movies read out here
            x = attr["movie"]
            _size = len(x)
            logger.info("readBoxOffice")
            _alexaOut = 'Here is the list of movies you asked for'
            i = 0
            while i < _size:
                # for j in range(len(dcode2)):
                # we need to parse the list and try to find the movie requested
                _alexaOut += str(",  " + x[str(i)]['title'])
                i += 1
            _alexaOut += " Would you like me to add the movies to your default list ?"
            attr['readShows'] = False
            attr['readMovies'] = False
            attr['readBoth'] = False
            attr['active_request'] = 'AddMovies'
            attr['repeat'] = 'readBoxOffice'
            attr['readBoxOffice'] = False
            handler_input.response_builder.speak(_alexaOut).ask(
                "Would you like me to add the movies to your default list ?")
            return handler_input.response_builder.response
        # user got here with no lists
        attr['readShows'] = False
        attr['readMovies'] = False
        attr['readBoth'] = False
        attr['repeat'] = ''
        attr['readBoxOffice'] = False
        handler_input.response_builder.speak("Im sorry i didnt understand.")
        return handler_input.response_builder.response


# get popular lists and add them to our list
class GetPopular(AbstractRequestHandler):

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("GetPopular")(handler_input)

    def handle(self, handler_input):
        _listtype = get_slot_value(handler_input=handler_input, slot_name="list")
        h = handler_input.request_envelope.context.system.user.access_token
        attr = handler_input.attributes_manager.session_attributes
        attr["movie"] = {}
        attr["show"] = {}
        attr['readBoxOffice'] = False
        attr['readMovies'] = False
        attr['readShows'] = False
        attr['readBoth'] = False
        attr['active_request'] = ''
        attr['repeat'] = ''
        # if we got nothing set the default
        if _listtype is None:
            _listtype = 'boxoffice'
        # fixing box office to slug type
        if _listtype == 'box office':
            _listtype = 'boxoffice'
            # handler_input.response_builder.speak(_listtype)
            # return handler_input.response_builder.response

        if _listtype != 'popular' and _listtype != ' boxoffice' and _listtype != ' box office' and \
                _listtype != 'trending' and _listtype != 'collected' and \
                _listtype != 'played' and _listtype != 'watched':
            _listtype = 'boxoffice'
            # handler_input.response_builder.speak("Thats not even a real list mate")
            # return handler_input.response_builder.response
        url = "https://api.trakt.tv/movies/" + _listtype
        # If we are not auth, let the user know
        if h is None:
            handler_input.response_builder.speak(
                "There is a problem with authorisation, please logout and log back in.")
            return handler_input.response_builder.response
        # Set all our headers for the trakt-api
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer ' + h,
                   'trakt-api-version': '2',
                   'trakt-api-key': clientid}
        r = requests.get(url, headers=headers)
        print("status code= " + str(r.status_code))
        if r.status_code == 200 or r.status_code == 201:
            boxoffice = json.loads(r.text)
            # print(json.dumps(boxoffice,sort_keys=True,indent=4))
            _notfound = {}
            _mywatchlist = bak.list_cache(headers)
            if "error" in _mywatchlist:
                handler_input.response_builder.speak("I had trouble getting your lists from the trakt.tv api")
                return handler_input.response_builder.response
                # exit("error: 64")
            i = 0
            j = 0
            # for every item in the boxoffice
            for i in range(len(boxoffice)):
                # if 'movie' in boxoffice[i]:
                b = bak.listparser(_mywatchlist, boxoffice[i], _listtype)
                if b is not None:
                    _notfound[j] = b
                    j += 1
                    # print("got movie")
                    # _notfound[i] = bak.listparser(_mywatchlist,boxoffice[i],"movie")
                i += 1
            print(str(_notfound))
            if len(_notfound) > 0:
                attr = handler_input.attributes_manager.session_attributes
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
                handler_input.response_builder.speak("you have all the items from this list")
                # .ask("Do you want to add the missing movies to your list ?")
                return handler_input.response_builder.response
                # print("you have all the items from this list")
        else:
            handler_input.response_builder.speak("I couldnt contact the trakt.tv api")
            # .ask("Do you want to add the missing movies to your list ?")
            return handler_input.response_builder.response
            # print("status code= "+str(r.status_code))


# Register intent handlers
sb.add_request_handler(GetPopular())
sb.add_request_handler(JustStop())
sb.add_request_handler(ReadBothOut())
sb.add_request_handler(WhatsOn())
sb.add_request_handler(FindShow())
sb.add_request_handler(FindMovie())
sb.add_request_handler(RemoveShow())
sb.add_request_handler(RemoveMovie())
sb.add_request_handler(ChooseList())
sb.add_request_handler(AddMovie())
sb.add_request_handler(AddShow())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

# Register exception handlers
sb.add_exception_handler(CatchAllExceptionHandler())

# Register request and response interceptors
sb.add_global_request_interceptor(LocalizationInterceptor())
sb.add_global_request_interceptor(RequestLogger())
sb.add_global_response_interceptor(ResponseLogger())

# Handler name that is used on AWS lambda
lambda_handler = sb.lambda_handler()
