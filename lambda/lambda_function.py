# -*- coding: utf-8 -*-
"""Simple Alexa app."""

import logging
import json
import prompts
import bak
import ask_sdk_core.utils as ask_utils
import os
import requests

from datetime import datetime
from ask_sdk_s3.adapter import S3Adapter

s3_adapter=S3Adapter(bucket_name=os.environ["S3_PERSISTENCE_BUCKET"])
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.utils import get_slot_value
from ask_sdk_core.utils import is_request_type,is_intent_name
from ask_sdk_model import Response,session
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import (AbstractRequestHandler,AbstractExceptionHandler,
                                              AbstractRequestInterceptor,AbstractResponseInterceptor)
from ask_sdk_model.ui import SimpleCard
from ask_sdk_core.skill_builder import CustomSkillBuilder

sb=CustomSkillBuilder(persistence_adapter=s3_adapter)
logger=logging.getLogger(__name__)
clientid: str=""
user='me'

# We dont need these for Alexa but lets keep em around for DEBUG offline
access_token=''
expires_in=''
refresh_token=''
token_type=''
value=''
movie=''
showtype="movie"
speech_text=''
_listnamepretty=''
##
##our default headers, not really needed for Alexa
headers={
    'Content-Type':'application/json',
    'Authorization':'Bearer '+access_token,
    'trakt-api-version':'2',
    'trakt-api-key':clientid,
}


# Our action for finding if a show is on one of our lists
class WhatsOn(AbstractRequestHandler):
    """Handler for WhatsOn Intent."""

    def can_handle(self,handler_input):
        # type: (HandlerInput) -> bool
        attr=handler_input.attributes_manager.session_attributes
        return is_intent_name("WhatsOn")(handler_input)# and (attr.get("readBoth") is False)

    def handle(self,handler_input):
        # Get the value of the users auth token
        h=handler_input.request_envelope.context.system.user.access_token
        # set the default to use todays datetime
        # OUR default items count
        _movieitemcount=0
        _showitemcount=0
        z=''
        attr=handler_input.attributes_manager.session_attributes
        attr["show"]={}
        attr["movie"]={}
        # If we are not auth, let the user know
        if len(h)<3:
            reprompt='s'
            handler_input.response_builder.speak("There is a problem with authorisation, please logout and log back in.").ask(reprompt)
            return handler_input.response_builder.response
        # Set all our headers for the trakt-api
        headers={
            'Content-Type':'application/json',
            'Authorization':'Bearer '+h,
            'trakt-api-version':'2',
            'trakt-api-key':clientid,
        }
        _type=get_slot_value(handler_input=handler_input,slot_name="typeMedia")
        _date=get_slot_value(handler_input=handler_input,slot_name="thedate")
        if _date is None:
            x=datetime.now()
            z=x.strftime('%Y-%m-%d')
        else:
            z=bak.validate(_date)
        # did they want a specific media ?
        if _type is None:
            #we got nothing
            print("__")
        else:
            # We got a movie ?
            _type1=str(_type).lower()
            if _type1=="movies" or _type1=="movie" or _type1=="films" or _type1=="film":
                
                # its a movie
                url="https://api.trakt.tv/calendars/my/movies/"+str(z)+"/7"
                # lets send a request for lists
                r=requests.get(url,headers=headers)

                
                if r.status_code==200 or r.status_code==201:
                    dcode=json.loads(r.text)
                    print(json.dumps(dcode,sort_keys=True,indent=4))
                    i=0
                    while i<len(dcode):
                        _title=str(dcode[i]["movie"]['title'])
                        attr["movie"][i]=_title
                        # print(_title)
                        # _traktid=dcode[i]['ids']['trakt']
                        # exit("yeet")
                        _movieitemcount+=1
                        i+=1
                    if (len(dcode)-1)<0:
                        print("no movie items")
                else:
                    print("status code= "+str(r.status_code))
                    # we couldnt contact trakt.tv
                n=datetime.now()
                m=n.strftime('%Y-%m-%d')
                reprompt=''
                should_end_session=False
                if (_movieitemcount-1)<0:
                    if z==m:
                        handler_input.response_builder.speak("you have no new movies today")
                        return handler_input.response_builder.response
                    else:
                        handler_input.response_builder.speak("you have no new movies on "+str(z))
                        return handler_input.response_builder.response
                        # print("you have no new movies or episodes on today")
                else:
                    reprompt='Would you like me to read them out ?'
                    if z==m:
                        handler_input.response_builder.speak("You have "+str(_movieitemcount)+" new movies on today").ask(reprompt)
                        attr["readMovies"]=True
                        return handler_input.response_builder.response
                        # return build_response(attributes,build_speechlet_response("radar", "speech_output", reprompt,False))
                    else:
                        handler_input.response_builder.speak("You have "+str(_movieitemcount)+" new movies on "+str(z)).ask(reprompt)
                        attr["readMovies"]=True
                        return handler_input.response_builder.response
            if _type1=='series' or _type1=='episodes' or _type1=='shows' or _type1=='show':
                
                # its a tv shows
                url2="https://api.trakt.tv/calendars/my/shows/"+str(z)+"/7"
                # lets send a request for lists
                r2=requests.get(url2,headers=headers)
                #print("status code= "+str(r2.status_code))
                if r2.status_code==200 or r2.status_code==201:
                    dcode2=json.loads(r2.text)
                    print(json.dumps(dcode2,sort_keys=True,indent=4))
                    i=0
                     
                    while i<len(dcode2):
                        _title=str(dcode2[i]["show"]['title'])
                        attr["show"][i]=_title                        
                        # print(_title)
                        # _traktid=dcode[i]['ids']['trakt']
                        # exit("yeet")
                        _showitemcount+=1
                        i+=1
                    if (len(dcode2)-1)<0:
                        print("no show items")
                else:
                    handler_input.response_builder.speak("I couldnt reach the trakt.tv API").ask("reprompt")
                    return handler_input.response_builder.response
                n=datetime.now()
                m=n.strftime('%Y-%m-%d')
                reprompt='would you like me to read them out ?'
                if (_showitemcount-1)<0:
                    if z==m:
                        handler_input.response_builder.speak("you have no new episodes on today").ask("")
                        return handler_input.response_builder.response
                    else:
                        handler_input.response_builder.speak("you have no new episodes on "+str(z)).ask("")
                        return handler_input.response_builder.response
                else:
                    if z==m:
                        handler_input.response_builder.speak(
                            "You have "+str(_showitemcount)+" new episodes on today").ask(reprompt)
                        attr["readShows"]=True
                        return handler_input.response_builder.response
                    else:
                        handler_input.response_builder.speak(
                            "You have "+str(_showitemcount)+" new episodes on "+str(z)).ask(reprompt)
                        attr["readShows"]=True
                        return handler_input.response_builder.response
            else:
                handler_input.response_builder.speak("Im sorry i couldnt understand what you media type you wanted").ask("Try saying, Alexa ask Radar what is on.")
                return handler_input.response_builder.response
                #no idea what they user wanted
        
        # we didnt get a media, get both
        # OUR default items count
        _movieitemcount=0
        _showitemcount=0
        url="https://api.trakt.tv/calendars/my/movies/"+str(z)+"/7"
        # lets send a request for lists
        r=requests.get(url,headers=headers)
        # print("status code= "+str(r.status_code))
        if r.status_code==200 or r.status_code==201:
            dcode=json.loads(r.text)
            print(json.dumps(dcode,sort_keys=True,indent=4))
            i=0
            while i<len(dcode):
                _title=str(dcode[i]["movie"]['title'])
                attr["movie"][i]=_title
                _movieitemcount+=1
                i+=1
            if (len(dcode)-1)<0:
                print("no movie items")
        else:
            handler_input.response_builder.speak("I cant seem to contact the trakt.tv API")
            return handler_input.response_builder.response

        url2="https://api.trakt.tv/calendars/my/shows/"+str(z)+"/7"
        # lets send a request for lists
        r2=requests.get(url2,headers=headers)
        print("status code= "+str(r2.status_code))
        if r2.status_code==200 or r2.status_code==201:
            dcode2=json.loads(r2.text)
            print(json.dumps(dcode2,sort_keys=True,indent=4))
            i=0
            while i<len(dcode2):
                _title=str(dcode2[i]["show"]['title'])
                attr["show"][i]=_title
                _showitemcount+=1
                i+=1
            if (len(dcode2)-1)<0:
                print("no show items")
        else:
            print("status code= "+str(r.status_code))
        n=datetime.now()
        m=n.strftime('%Y-%m-%d')
        reprompt='Would you like me to read them out ?'
        if (_movieitemcount-1)<0 and (_showitemcount-1)<0:
            if z==m:
                handler_input.response_builder.speak("you have no new movies or episodes on today").ask("")
                return handler_input.response_builder.response
            else:
                handler_input.response_builder.speak("you have no new movies or episodes on "+str(z)).ask("")
                return handler_input.response_builder.response
        else:
            if z==m:
                handler_input.response_builder.speak(
                    "You have "+str(_movieitemcount)+" new movies and "+str(_showitemcount)+" episodes on today").ask(
                    reprompt)
                attr["readBoth"]=True
                return handler_input.response_builder.response
            else:
                handler_input.response_builder.speak(
                    "You have "+str(_movieitemcount)+" new movies and "+str(_showitemcount)+" episodes on "+str(z)).ask(
                    reprompt)
                attr["readBoth"]=True
                return handler_input.response_builder.response


# Our action for finding if a show is on one of our lists
class FindShow(AbstractRequestHandler):
    """Handler for FindShow Intent."""

    def can_handle(self,handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("FindShow")(handler_input)

    def handle(self,handler_input):
        # Get the value of the users auth token
        h=handler_input.request_envelope.context.system.user.access_token
        showtype='show'
        # If we are not auth, let the user know
        if len(h)<3:
            reprompt='s'
            handler_input.response_builder.speak(
                "There is a problem with authorisation, please logout and log back in.").ask(reprompt)
            return handler_input.response_builder.response
        # Set all our headers for the trakt-api
        headers={
            'Content-Type':'application/json',
            'Authorization':'Bearer '+h,
            'trakt-api-version':'2',
            'trakt-api-key':clientid,
        }
        movie=get_slot_value(handler_input=handler_input,slot_name="showName")
        b=bak.search(movie,headers,"show",True)
        if b['error'] is True:
            # handle this
            reprompt='_'
            handler_input.response_builder.speak("I couldnt find the show you requested").ask(reprompt)
            return handler_input.response_builder.response
        y=b['show']

        t=bak.search_lists(y,b,headers,"show")
        if t['found']:
            # print(movie+" found on the list "+t['list'])
            reprompt='_'
            handler_input.response_builder.speak(movie+" is already on the list "+t['list']).ask(reprompt)
            return handler_input.response_builder.response
        else:
            reprompt='_'
            handler_input.response_builder.speak(movie+" isnt on any of your lists.").ask(reprompt)
            return handler_input.response_builder.response


# Our action for finding if a movie is on one of our lists
class FindMovie(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self,handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("FindMovie")(handler_input)

    def handle(self,handler_input):
        # Get the value of the users auth token
        h=handler_input.request_envelope.context.system.user.access_token
        showtype="movie"
        # If we are not auth, let the user know
        if len(h)<3:
            reprompt='s'
            handler_input.response_builder.speak(
                "There is a problem with authorisation, please logout and log back in.").ask(reprompt)
            return handler_input.response_builder.response
        # Set all our headers for the trakt-api
        headers={
            'Content-Type':'application/json',
            'Authorization':'Bearer '+h,
            'trakt-api-version':'2',
            'trakt-api-key':clientid,
        }
        movie=get_slot_value(handler_input=handler_input,slot_name="movieName")
        # TODO search the movie var and strip  "on my list" from the end incase Alexa fucks up
        #
        b=bak.search(movie,headers,"movie",True)
        if b['error'] is True:
            # handle this
            reprompt='_'
            handler_input.response_builder.speak("I couldnt find the movie you requested").ask(reprompt)
            return handler_input.response_builder.response
        y=b["movie"]

        t=bak.search_lists(y,b,headers,"movie")
        if t['found']:
            # print(movie+" found on the list "+t['list'])
            reprompt='_'
            handler_input.response_builder.speak(movie+" is already on the list "+t['list']).ask(reprompt)
            return handler_input.response_builder.response
        else:
            reprompt='_'
            handler_input.response_builder.speak(movie+" isnt on any of your lists.").ask(reprompt)
            return handler_input.response_builder.response


# Our action for removing Show
class RemoveShow(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self,handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("RemoveShow")(handler_input)

    def handle(self,handler_input):
        # Get the value of the users auth token
        h=handler_input.request_envelope.context.system.user.access_token
        # If we are not auth, let the user know
        if len(h)<3:
            reprompt='s'
            handler_input.response_builder.speak(
                "There is a problem with authorisation, please logout and log back in.").ask(reprompt)
            return handler_input.response_builder.response
        # Set all our headers for the trakt-api
        headers={
            'Content-Type':'application/json',
            'Authorization':'Bearer '+h,
            'trakt-api-version':'2',
            'trakt-api-key':clientid,
        }
        # TODO make sure we change I,II,II type movies to 1,2,3
        # and vice versa
        _list=get_slot_value(handler_input=handler_input,slot_name="list_name")
        movie=str(get_slot_value(handler_input=handler_input,slot_name="showName"))

        # get our persistent_attributes
        attr=handler_input.attributes_manager.persistent_attributes
        _perlist=attr['list']
        _usecustomlist=attr['usecustomlist']
        # user gave us nothing lets do some checks to make sure we have saved attributes
        if _list==None:
            # they didnt give us a list use the default
            # attr = handler_input.attributes_manager.persistent_attributes
            _perlist=attr['list']
            # if default isnt set use watchlist
            if _perlist==None:
                _list='watchlist'
                _usecustomlist=False
            elif _perlist.lower()=='watchlist' or _perlist.lower()=='watch list':
                _usecustomlist=False
            else:
                _usecustomlist=True

            # user has a custom list set
            _list=_perlist
        else:
            _usecustomlist=True
            # this doesnt work
            _liststring=str(_list)
            if _list.lower()=='watchlist' or _list.lower()=='watch list':
                _usecustomlist=False
        # if we got nothing from the user and AND we have no pers data  set no custom list
        if _usecustomlist==None:
            _usecustomlist=False

        # if our list isnt empty then we can go ahead amd deal with the request
        if _usecustomlist:

            url='https://api.trakt.tv/users/me/lists/'+_list+'/items/shows'
            r=requests.get(url,headers=headers)

            if r.status_code==200 or r.status_code==201:
                dcode=json.loads(r.text)
                # print(json.dumps(json.loads(r.text), sort_keys=True, indent=4))
                i=0
                _moviefound=False
                while i<len(dcode):
                    # print(dcode[i]['name'])
                    # print(json.dumps(dcode[i], sort_keys=True, indent=4))
                    o=dcode[i]['show']['title']
                    # print(str(o) + " is our title")
                    # if our movie name matches the movie send the request to delete it
                    if o.lower()==movie.lower():
                        _moviefound=True
                        _id=dcode[i]['show']['ids']['trakt']
                        if bak.parse_delete_search('show',headers,dcode[i]['show'],_list,_usecustomlist,True):
                            reprompt='s'
                            handler_input.response_builder.speak("I have deleted "+o+" from the list "+_list).ask(
                                reprompt)
                            return handler_input.response_builder.response
                        else:
                            # return
                            reprompt='s'
                            handler_input.response_builder.speak(
                                "I had trouble deleting "+o+" from the list "+_list).ask(reprompt)
                            return handler_input.response_builder.response
                    i+=1
                # if we failed to find the movie
                if _moviefound==False:
                    # print("we couldnt find the film")
                    reprompt='s'
                    handler_input.response_builder.speak("i couldnt find "+movie+" on the list "+_list).ask(
                        reprompt)
                    return handler_input.response_builder.response
            # if our first request to trakt fails
            else:
                reprompt='s'
                handler_input.response_builder.speak('I couldnt contact Trakt.tv API .'+url).ask(reprompt)
                return handler_input.response_builder.response
                # print('Error with the request to trak.tv')
        # if our user didnt give us a list or they are using the watch list
        else:
            # WE DIDNT RECIEVE A LIST
            # TODO make sure we change I,II,II type movies to 1,2,3
            # and vice versa
            movie=str(get_slot_value(handler_input=handler_input,slot_name="showName"))
            # we assume the users is using a custom list
            # next if statement should take care of it
            _usecustomlist=True
            reprompt=''
            # search for movie and get the object
            b=bak.search(movie,headers,"show",False)
            if b['error'] is True:
                # handle this
                reprompt='_'
                handler_input.response_builder.speak("I couldnt find the show you requested").ask(reprompt)
                return handler_input.response_builder.response
            # force our movie/show object into a small var to make things easier
            y=b['show']
            if bak.parse_delete_search('show',headers,y,_list,False,False):
                reprompt='s'
                handler_input.response_builder.speak("I have deleted "+movie+" from the list "+_list).ask(
                    reprompt)
                return handler_input.response_builder.response
            else:
                handler_input.response_builder.speak("i couldn't delete "+movie+" from the list "+_list).ask(
                    reprompt)
                return handler_input.response_builder.response
            reprompt='Would you like me to remove it from your watchlist ?'
            handler_input.response_builder.speak('No list provieded. or error').ask(reprompt)
            return handler_input.response_builder.response


# Our action for removing movie
class RemoveMovie(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self,handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("RemoveMovie")(handler_input)

    def handle(self,handler_input):
        # Get the value of the users auth token
        h=handler_input.request_envelope.context.system.user.access_token
        # If we are not auth, let the user know
        if len(h)<3:
            reprompt='s'
            handler_input.response_builder.speak(
                "There is a problem with authorisation, please logout and log back in.").ask(reprompt)
            return handler_input.response_builder.response
        # Set all our headers for the trakt-api
        headers={
            'Content-Type':'application/json',
            'Authorization':'Bearer '+h,
            'trakt-api-version':'2',
            'trakt-api-key':clientid,
        }
        # TODO make sure we change I,II,II type movies to 1,2,3
        # and vice versa
        # _usecustomlist = bool
        _list=get_slot_value(handler_input=handler_input,slot_name="list_name")
        movie=str(get_slot_value(handler_input=handler_input,slot_name="movieName"))

        # get our persistent_attributes
        attr=handler_input.attributes_manager.persistent_attributes
        _perlist=attr['list']
        _usecustomlist=attr['usecustomlist']
        # user gave us nothing lets do some checks to make sure we have saved attributes
        if _list==None:
            # they didnt give us a list use the default
            # attr = handler_input.attributes_manager.persistent_attributes
            _perlist=attr['list']
            # if default isnt set use watchlist
            if _perlist==None:
                _list='watchlist'
                _usecustomlist=False
            elif _perlist.lower()=='watchlist' or _perlist.lower()=='watch list':
                _usecustomlist=False
            else:
                _usecustomlist=True

            # user has a custom list set
            _list=_perlist
        else:
            _usecustomlist=True
            # this doesnt work
            _liststring=str(_list)
            if _list.lower()=='watchlist' or _list.lower()=='watch list':
                _usecustomlist=False
        # if we got nothing from the user and AND we have no pers data  set no custom list
        if _usecustomlist==None:
            _usecustomlist=False

        # if our list isnt empty then we can go ahead amd deal with the request
        # TODO get this to check if list is empty or not
        if _usecustomlist:

            url='https://api.trakt.tv/users/me/lists/'+_list+'/items/movies'
            r=requests.get(url,headers=headers)

            if r.status_code==200 or r.status_code==201:
                dcode=json.loads(r.text)
                # print(json.dumps(json.loads(r.text), sort_keys=True, indent=4))
                i=0
                _moviefound=False
                while i<len(dcode):
                    o=dcode[i]["movie"]['title']
                    # if our movie name matches the movie send the request to delete it
                    if o.lower()==movie.lower():
                        _moviefound=True
                        _id=dcode[i]["movie"]['ids']['trakt']
                        if bak.parse_delete_search("movie",headers,dcode[i]["movie"],_list,_usecustomlist,True):
                            reprompt='s'
                            handler_input.response_builder.speak("I have deleted "+o+" from the list "+_list).ask(
                                reprompt)
                            return handler_input.response_builder.response
                        else:
                            # return
                            reprompt='s'
                            handler_input.response_builder.speak(
                                "I had trouble deleting "+o+" from the list "+_list).ask(reprompt)
                            return handler_input.response_builder.response
                    i+=1
                # if we failed to find the movie
                if _moviefound==False:
                    # print("we couldnt find the film")
                    reprompt='s'
                    handler_input.response_builder.speak("i couldnt find "+movie+" on the list "+_list).ask(
                        reprompt)
                    return handler_input.response_builder.response
            # if our first request to trakt fails
            else:
                reprompt='s'
                handler_input.response_builder.speak('I couldnt contact Trakt.tv API .'+url).ask(reprompt)
                return handler_input.response_builder.response
        # if our user didnt give us a list or they are using the watch list
        else:
            # WE DIDNT RECIEVE A LIST
            # TODO make sure we change I,II,II type movies to 1,2,3
            # and vice versa
            movie=str(get_slot_value(handler_input=handler_input,slot_name="movieName"))
            # we assume the users is using a custom list
            # next if statement should take care of it
            _usecustomlist=True
            reprompt=''
            # search for movie and get the object
            b=bak.search(movie,headers,"movie",False)
            if b['error'] is True:
                # handle this
                reprompt='_'
                handler_input.response_builder.speak("I couldnt find the movie you requested").ask(reprompt)
                return handler_input.response_builder.response
            # force our movie/show object into a small var to make things easier
            y=b["movie"]
            if bak.parse_delete_search("movie",headers,y,_list,False,False):
                reprompt='s'
                handler_input.response_builder.speak("I have deleted "+movie+" from the list "+_list).ask(
                    reprompt)
                return handler_input.response_builder.response
            else:
                handler_input.response_builder.speak("i couldn't delete "+movie+" from the list "+_list).ask(
                    reprompt)
                return handler_input.response_builder.response
            reprompt='Would you like me to remove it from your watchlist ?'
            handler_input.response_builder.speak('No list provieded. or error').ask(reprompt)
            return handler_input.response_builder.response


# Our action for letting the user pick their own custom list
class ChooseList(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self,handler_input):
        # type: (HandlerInput) -> bool
        attr=handler_input.attributes_manager.session_attributes
        return is_intent_name("ChooseList")(handler_input) and (attr.get("readBoth") is False)

    def handle(self,handler_input):
        # TODO Check that the user has supplied a value or we will throw errors
        #
        # get the value of listName and throw it onto _thelist
        _thelist=get_slot_value(handler_input=handler_input,slot_name="listName")

        # Get the value of the users auth token
        h=handler_input.request_envelope.context.system.user.access_token

        # If we are not auth, let the user know
        if len(h)<3:
            reprompt='s'
            handler_input.response_builder.speak(
                "There is a problem with authorisation, please logout and log back in.").ask(reprompt)
            return handler_input.response_builder.response
        # Set all our headers for the trakt-api
        headers={
            'Content-Type':'application/json',
            'Authorization':'Bearer '+h,
            'trakt-api-version':'2',
            'trakt-api-key':clientid,
        }

        # TODO check if the list is empty and different
        #
        #
        # NEED TO CHECK IF THE LIST ISNT NULL FIRST
        # if the user is wanting their default watch list we can save time and use defaults
        if _thelist is not None:
            if _thelist.lower()=='watchlist' or _thelist.lower()=='watch list':
                # need to set _custom list to false and set it to the persistant session
                # give feedback to the user
                handler_input.response_builder.speak("Your List has been set to the default. This is the watchlist").ask("reprompt")
                _usecustomlist=False
                # start saving the persistent attributes
                session_attr=handler_input.attributes_manager.session_attributes
                session_attr['usecustomlist']=False
                session_attr['list']='watchlist'
                # savesessionattributes as persistentattributes
                handler_input.attributes_manager.persistent_attributes=session_attr
                handler_input.attributes_manager.save_persistent_attributes()
                return handler_input.response_builder.response
        # if we dont have anything
        session_attr=handler_input.attributes_manager.session_attributes
        if _thelist is None and session_attr['list'] is None:
            handler_input.response_builder.speak("Your List has been set to the default. This is the watchlist").ask(
                "reprompt")
            _usecustomlist=False
            # start saving the persistent attributes
            session_attr=handler_input.attributes_manager.session_attributes
            session_attr['usecustomlist']=False
            session_attr['list']='watchlist'
            # savesessionattributes as persistentattributes
            handler_input.attributes_manager.persistent_attributes=session_attr
            handler_input.attributes_manager.save_persistent_attributes()
            return handler_input.response_builder.response
        # user wanted a different custom list
        # lets get all their trakt.tv lists
        # we need to set failsafe vars before we start
        _foundlist=False
        _customlist=''
        url='https://api.trakt.tv/users/me/lists'
        r=requests.get(url,headers=headers)
        # If everything is ok lets process
        if r.status_code==200 or r.status_code==201:
            # print(r.text)
            dcode=json.loads(r.text)
            i=0
            while i<len(dcode):
                o=dcode[i]['ids']['slug']
                if dcode[i]['name']==_thelist.lower():
                    _foundlist=True
                    # set the list to the user requested list
                    _customlist=o
                i+=1
            # couldnt find the custom list notify and set to watchlist
            if _foundlist==False:
                handler_input.response_builder.speak(
                    "We couldnt find that list. Your list has been set to the default. This is the watchlist").ask(
                    "reprompt")
                _usecustomlist=False
                # start saving the persistent attributes
                session_attr=handler_input.attributes_manager.session_attributes
                session_attr['usecustomlist']=False
                session_attr['list']='watchlist'
                handler_input.attributes_manager.persistent_attributes=session_attr
                handler_input.attributes_manager.save_persistent_attributes()
                return handler_input.response_builder.response

            # we found the list, save it and we can use it for all add requests
            handler_input.response_builder.speak("Your List has been set to "+_thelist).ask("Is this correct ?")
            # start saving the persistent attributes
            session_attr=handler_input.attributes_manager.session_attributes
            session_attr['usecustomlist']=_foundlist
            session_attr['list']=_customlist
            # save session attributes as persistent attributes
            handler_input.attributes_manager.persistent_attributes=session_attr
            handler_input.attributes_manager.save_persistent_attributes()
            return handler_input.response_builder.response
        else:
            # TODO Catch the error and tell alexa to output it nicely
            # revert to default settings and store them
            handler_input.response_builder.speak("There was a problem reaching Tracked TV").ask("")
            return handler_input.response_builder.response


class AddMovie(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self,handler_input):
        # type: (HandlerInput) -> bool
        return (is_request_type("LaunchRequest")(handler_input) or is_intent_name("AddMovie")(handler_input))

    def handle(self,handler_input):
        _perattr=handler_input.attributes_manager.persistent_attributes
        _perlist=_perattr['list']
        _usecustomlist=_perattr['usecustomlist']
        # if the user has launched the app greet them
        if is_request_type("LaunchRequest")(handler_input):
            #set out session attributes
            attr=handler_input.attributes_manager.session_attributes
            attr["movie"]={}
            attr["show"]={}
            attr["readMovies"]=False
            attr["readShows"]=False
            attr["readBoth"]=False
            attr["_active_request"]=''

            handler_input.response_builder.speak("Welcome.").ask("")
            return handler_input.response_builder.response
        
        # Get the value of the users auth token
        h=handler_input.request_envelope.context.system.user.access_token

        showtype="movie"
        # If we are not auth, let the user know
        if len(h)<3:
            reprompt='s'
            handler_input.response_builder.speak(
                "There is a problem with authorisation, please logout and log back in.").ask(reprompt)
            return handler_input.response_builder.response
        # Set all our headers for the trakt-api
        headers={
            'Content-Type':'application/json',
            'Authorization':'Bearer '+h,
            'trakt-api-version':'2',
            'trakt-api-key':clientid,
        }

        # Get the movie name and throw it onto the movie var
        movie=get_slot_value(handler_input=handler_input,slot_name="movieName")
        _list=get_slot_value(handler_input=handler_input,slot_name="list_name")
        reprompt="Are you sure you want to add "+movie+' to your list ?'
        
        # user gave us nothing lets do some checks to make sure we have saved attributes
        if _list==None:
            # they didnt give us a list use the default
            # attr = handler_input.attributes_manager.persistent_attributes
            _perlist=_perattr['list']
            # if default isnt set use watchlist
            if _perlist==None:
                _list='watchlist'
                _usecustomlist=False
            elif _perlist.lower()=='watchlist' or _perlist.lower()=='watch list':
                _usecustomlist=False
                _list='watchlist'
            else:
                _usecustomlist=True
                # user has a custom list set
                _list=_perlist
        else:
            _usecustomlist=True
            # this doesnt work
            _liststring=str(_list)
            if _list.lower()=='watchlist' or _list.lower()=='watch list':
                _usecustomlist=False

        reprompt="Are you sure you want to add "+movie+' to your list '+_list+" ?"
        
        b=bak.search(movie,headers,showtype,False)
        if b['error'] is True:
            # handle this
            reprompt='_'
            handler_input.response_builder.speak("I couldnt find the show you requested").ask(reprompt)
            return handler_input.response_builder.response
        # force our movie/show object into a small var to make things easier
        y=b["movie"]
        # dig through our search and add the movie/show to our list or our Watchlist
        bak.parse_search(b['type'],headers,y,_list,_usecustomlist,True)

        handler_input.response_builder.speak(movie+" has been added to your "+_list+" list").ask(reprompt)
        return handler_input.response_builder.response


class AddShow(AbstractRequestHandler):
    """Handler for addShow Intent."""

    def can_handle(self,handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AddShow")(handler_input)

    def handle(self,handler_input):
        h=handler_input.request_envelope.context.system.user.access_token
        showtype='show'
        # If we are not auth, let the user know
        if len(h)<3:
            reprompt='s'
            handler_input.response_builder.speak(
                "There is a problem with authorisation, please logout and log back in.").ask(reprompt)
            return handler_input.response_builder.response
        headers={
            'Content-Type':'application/json',
            'Authorization':'Bearer '+h,
            'trakt-api-version':'2',
            'trakt-api-key':clientid,
        }
        
        # get our persistent_attributes
        _perattr=handler_input.attributes_manager.persistent_attributes
        _perlist=_perattr['list']
        _usecustomlist=_perattr['usecustomlist']
        movie=get_slot_value(handler_input=handler_input,slot_name="showName")
        _list=get_slot_value(handler_input=handler_input,slot_name="list_name")
        reprompt="Are you sure you want to add "+movie+' to your list ?'
        
        # user gave us nothing lets do some checks to make sure we have saved attributes
        if _list==None:
            # they didnt give us a list use the default
            # attr = handler_input.attributes_manager.persistent_attributes
            _perlist=_perattr['list']
            # if default isnt set use watchlist
            if _perlist==None:
                _list='watchlist'
                _usecustomlist=False
            elif _perlist.lower()=='watchlist' or _perlist.lower()=='watch list':
                _usecustomlist=False
                _list='watchlist'
            else:
                _usecustomlist=True
                # user has a custom list set
                _list=_perlist
        else:
            _usecustomlist=True
            # this doesnt work
            _liststring=str(_list)
            if _list.lower()=='watchlist' or _list.lower()=='watch list':
                # ((str(_list)).lower())=='watchlist'
                # ((str(_list)).lower())=='watch list'
                _usecustomlist=False

        # search for move and get the object
        b=bak.search(movie,headers,showtype,False)
        if b['error'] is True:
            # handle this
            reprompt='_'
            handler_input.response_builder.speak("I couldnt find the show you requested").ask(reprompt)
            return handler_input.response_builder.response
        # print("trakt id= "+str(y['ids']['trakt']))

        y=b['show']
        # dig through our search and add the movie/show to our list or our Watchlist
        bak.parse_search(b['type'],headers,y,our_list,_usecustomlist,True)

        handler_input.response_builder.speak(movie+" show has been added to your yeet list").ask(reprompt)
        return handler_input.response_builder.response


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self,handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self,handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In HelpIntentHandler")

        # get localization data
        data=handler_input.attributes_manager.request_attributes["_"]

        speech=data[prompts.HELP_MESSAGE]
        reprompt=data[prompts.HELP_REPROMPT]
        handler_input.response_builder.speak(speech).ask(reprompt).set_card(SimpleCard(data[prompts.SKILL_NAME],speech))
        return handler_input.response_builder.response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""

    def can_handle(self,handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self,handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In CancelOrStopIntentHandler")

        # get localization data
        data=handler_input.attributes_manager.request_attributes["_"]
        speech=data[prompts.STOP_MESSAGE]
        # response_builder.set_should_end_session(True)
        handler_input.response_builder.speak("lataaaa bitch")
        return handler_input.response_builder.response


class FallbackIntentHandler(AbstractRequestHandler):
    """Handler for Fallback Intent.

    AMAZON.FallbackIntent is only available in en-US locale.
    This handler will not be triggered except in that locale,
    so it is safe to deploy on any locale.
    """

    def can_handle(self,handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self,handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")

        # get localization data
        data=handler_input.attributes_manager.request_attributes["_"]

        speech=data[prompts.FALLBACK_MESSAGE]
        reprompt=data[prompts.FALLBACK_REPROMPT]
        handler_input.response_builder.speak(speech)
        return handler_input.response_builder.response


class LocalizationInterceptor(AbstractRequestInterceptor):
    """
    Add function to request attributes, that can load locale specific data.
    """

    def process(self,handler_input):
        locale=handler_input.request_envelope.request.locale
        logger.info("Locale is {}".format(locale))

        # localized strings stored in language_strings.json
        with open("language_strings.json") as language_prompts:
            language_data=json.load(language_prompts)
        # set default translation data to broader translation
        if locale[:2] in language_data:
            data=language_data[locale[:2]]
            if locale in language_data:
                data.update(language_data[locale])
        else:
            data=language_data[locale]
        handler_input.attributes_manager.request_attributes["_"]=data


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""

    def can_handle(self,handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self,handler_input):
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

    def can_handle(self,handler_input,exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self,handler_input,exception):
        # type: (HandlerInput, Exception) -> Response
        logger.info("In CatchAllExceptionHandler")
        logger.error(exception,exc_info=True)

        handler_input.response_builder.speak("error"+str(exception))
        # response_builder.set_should_end_session(True)
        return handler_input.response_builder.response


# Request and Response loggers
class RequestLogger(AbstractRequestInterceptor):
    """Log the alexa requests."""

    def process(self,handler_input):
        # type: (HandlerInput) -> None
        logger.debug("Alexa Request: {}".format(handler_input.request_envelope.request))


class ResponseLogger(AbstractResponseInterceptor):
    """Log the alexa responses."""

    def process(self,handler_input,response):
        # type: (HandlerInput, Response) -> None
        logger.debug("Alexa Response: {}".format(response))


class MovieReadOut(AbstractRequestHandler):
    def can_handle(self,handler_input):
        # type: (HandlerInput) -> bool
        attr=handler_input.attributes_manager.session_attributes
        return (attr.get("readMovies"))

    def handle(self,handler_input):
        # type: (HandlerInput) -> Response
        #
        attr=handler_input.attributes_manager.session_attributes
        attr["readMovies"]=False
        x=attr["movie"]
        _size=len(x)
        logger.info("myTest")
        _alexaOut='Here is the list of movies you asked for,  '
        i=0
        while i<_size:
            _alexaOut+=str(x[str(i)]+",  ")

            i+=1
        handler_input.response_builder.speak(str(_alexaOut))
        # return handler_input.response_builder.response
        return handler_input.response_builder.response


class ShowReadOut(AbstractRequestHandler):
    def can_handle(self,handler_input):
        # type: (HandlerInput) -> bool
        attr=handler_input.attributes_manager.session_attributes
        return (attr.get("readShows"))

    def handle(self,handler_input):
        # type: (HandlerInput) -> Response
        #
        attr=handler_input.attributes_manager.session_attributes
        attr["readShows"]=False
        x=attr["show"]
        _size=len(x)
        logger.info("myTest")
        _alexaOut='Here is the list of shows you asked for,  '
        i=0
        while i<_size:
            _alexaOut+=str(x[str(i)]+",  ")
            i+=1
        handler_input.response_builder.speak(str(_alexaOut))
        # return handler_input.response_builder.response
        return handler_input.response_builder.response


class ReadBothOut(AbstractRequestHandler):
    def can_handle(self,handler_input):
        # type: (HandlerInput) -> bool
        attr=handler_input.attributes_manager.session_attributes
        return (attr.get("readBoth"))

    def handle(self,handler_input):
        # type: (HandlerInput) -> Response
        attr=handler_input.attributes_manager.session_attributes
        attr["readShows"]=False
        attr["readMovies"]=False
        attr["readBoth"]=False
        x=attr["show"]
        z=attr["movie"]
        _size=len(x)
        _size2=len(z)
        logger.info("myTest")
        _alexaOut='Here is the list of shows you asked for,  '
        i=0
        while i<_size:
            _alexaOut+=str(x[str(i)]+",  ")

            i+=1
        j=0
        _alexaOut+=str(",  Here are the list of movies, ")
        while j<_size2:
            _alexaOut+=str(z[str(j)]+",  ")

            j+=1
        handler_input.response_builder.speak(str(_alexaOut))
        # return handler_input.response_builder.response
        return handler_input.response_builder.response


# Register intent handlers
# sb.add_request_handler(PersistenceAttributesHandler())
sb.add_request_handler(ReadBothOut())
sb.add_request_handler(ShowReadOut())
sb.add_request_handler(MovieReadOut())
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
lambda_handler=sb.lambda_handler()
