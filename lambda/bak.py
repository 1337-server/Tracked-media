import requests
import json
import logging
import datetime

logger=logging.getLogger('tipper')
logger.setLevel(logging.DEBUG)
logger.debug('debug message')
logger.info('info message')
logging.basicConfig(filename='error.log',level=logging.DEBUG)
logging.debug('This message should go to the log file')
logging.info('So should this')
logging.warning('And this, too')

def validate(date_text) :
    try :
        c = datetime.datetime.strptime(date_text,'%Y-%m-%d')
        print("standard"+str(c))
        return c.strftime('%Y-%m-%d')
    except ValueError :
        # raise ValueError("Incorrect data format, should be YYYY-MM-DD")
        try :
            r = datetime.datetime.strptime(date_text+'-1',"%Y-W%W-%w")
            print(r)
            return r.strftime('%Y-%m-%d')
        except ValueError :
            try :
                c = datetime.datetime.strptime(date_text,'%Y')
                print("year"+str(c))
                return c.strftime('%Y-%m-%d')
            except ValueError :
                print("fuck")

# SIMPLE GET REQUEST TO MAKE OUR MAIN PAGE
# LOOK NICER
def easygeturl(url,headers,p=bool):
    # lets send a request for lists
    r=requests.get(url,headers=headers)
    if p is True:
        print("status code= "+str(r.status_code))
        if r.status_code==200 or r.status_code==201:
            # print(r.text)
            dcode=json.loads(r.text)
            # lets see it
            # m = dcode[1]['movie']
            print(json.dumps(dcode[0]['name'],sort_keys=True,indent=4))
            # print(json.dumps(dcode, sort_keys=True, indent=4))
            return dcode[0]
        else:
            print("status code= "+str(r.status_code))
            return
    else:
        if r.status_code==200 or r.status_code==201:
            dcode=json.loads(r.text)
            return dcode[0]
        else:
            return


# OUR MAIN SEARCH ENGINE
# ONLY BRINGS BACK THE FIRST THREE RESULT
def search(q,h,t,p=bool):
    # q =query
    # h =headers
    # t = type
    url="https://api.trakt.tv/search/"+t+"?query="+q
    m={}
    m['error']=True
    # get our info
    r=requests.get(url,headers=h)
    # if logging is on lets print stuff out
    if p is True:
        print("search status code= "+str(r.status_code))
        if r.status_code==200 or r.status_code==201:
            print(r.text)
            dcode=json.loads(r.text)
            # m = dcode[0][t]
            if len(dcode)<1:
                m['error'] = True
                return m
            m=dcode[0]
            #this might cause problems if we get less than 3 results
            m['2nd']=dcode[1]
            m['3rd']=dcode[2]
            m['error'] = False
            print ( json.dumps ( m , sort_keys = True , indent = 4 ) )
            return m
        else:
            m['error'] = True
            print("search status code= "+str(r.status_code))
            return m
    else:
        if r.status_code==200 or r.status_code==201:
            dcode=json.loads(r.text)
            if len(dcode)<1:
                m['error'] = True
                return m
            m=dcode[0]
            #this might cause problems if we get less than 3 results
            m['2nd']=dcode[1]
            m['3rd']=dcode[2]
            m['error'] = False
            return m
        else:
            m['error'] = True
            return m
    return m


def parse_search(typ,headers,s_obj,our_list,_usecustom=bool,p=bool):
    if typ=='movie':
        values="""
        {   "movies":[
          {
            "ids": {
              "trakt": """+str(s_obj['ids']['trakt'])+"""
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
        values="""
            {   "movies":[],
           "shows":[
             {
                "ids": { 
                    "trakt": """+str(s_obj['ids']['trakt'])+""" 
                    }
            } ],
           "seasons":[],
           "episodes":[],
           "people":[]
        }
        """
    if _usecustom:
        urll="https://api.trakt.tv/users/me/lists/"+our_list+"/items"
        # print(json.dumps(u, sort_keys=True, indent=4))
    else:
        urll='https://api.trakt.tv/sync/watchlist'
    r2=requests.post(urll,headers=headers,data=values)
    # decode json
    if r2.status_code==200 or r2.status_code==201:
        # decode json
        dcode3=json.loads(r2.text)
        # lets see it
        if p:
            print(json.dumps(dcode3,sort_keys=True,indent=4))
    else:
        logger.warning('adding to list error! Status code = '+str(r2.status_code))


def parse_delete_search(typ,headers,s_obj,our_list,_usecustom=bool,p=bool):
    if typ=='movie':
        values="""
        {   "movies":[
          {
            "ids": {
              "trakt": """+str(s_obj['ids']['trakt'])+"""
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
        values="""
            {   "movies":[],
           "shows":[
             {
                "ids": { 
                    "trakt": """+str(s_obj['ids']['trakt'])+""" 
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
        urll="https://api.trakt.tv/users/me/lists/"+our_list+"/items/remove"
        # print(json.dumps(u, sort_keys=True, indent=4))
    else:
        urll='https://api.trakt.tv/sync/watchlist/remove'
    r2=requests.post(urll,headers=headers,data=values)
    # decode json
    if r2.status_code==200 or r2.status_code==201:
        # decode json
        dcode3=json.loads(r2.text)
        # lets see it
        if p:
            print(json.dumps(dcode3,sort_keys=True,indent=4))
            return True
        #todo need to check the return results to see if its was deleted
        return True
    else:
        return False

def search_lists(_movieobj,_alt,headers,_type):
    _foundmatch=False
    a={}
    a['found']=False
    a['list']=''
    url='https://api.trakt.tv/users/me/lists'
    _movtype=_alt['type']
    _altmovie1=_alt['2nd'][_movtype]['ids']['trakt']
    _altmovie2=_alt['3rd'][_movtype]['ids']['trakt']
    r=requests.get(url,headers=headers)
    if r.status_code==200 or r.status_code==201:
        dcode=json.loads(r.text)
        i=0
        while i < len ( dcode ) :
            o=dcode[i]['ids']['slug']
            url2='https://api.trakt.tv/users/me/lists/'+str(o)+'/items'
            r2=requests.get(url2,headers=headers)
            j=0
            if r2.status_code==200 or r.status_code==201:
                dcode2=json.loads(r2.text)
                while j < len ( dcode2 ) :
                    # we need to parse the list and try to find the movie requested
                    _type=str(dcode2[j]['type'])
                    _traktid=dcode2[j][_type]['ids']['trakt']
                    #TODO THIS CAN LEAD TO SOME WONKY RESULTS IF THE USERS WANTS A SPECIFIC YEAR FILM
                    if _traktid==_movieobj['ids']['trakt'] or _traktid == _altmovie1 or _traktid == _altmovie2:
                        # print ( str ( _title ) + "  ===  " + str ( _movieobj [ 'ids' ] [ 'trakt' ] ) )
                        # print ( 'we found a match' )
                        a['found']=True
                        a['list']= str(dcode[i]['name'])
                        return a
                        # exit("yeet")
                    j+=1
            i+=1
        if _foundmatch is not True:
            url='https://api.trakt.tv/sync/watchlist'
            r3=requests.get(url,headers=headers)
            i=0
            if r3.status_code==200 or r.status_code==201:
                dcode3=json.loads(r3.text)
                for i in range(len(dcode3)):
                    # we need to parse the list and try to find the movie requested
                    _type=str(dcode3[i]['type'])
                    _traktid=dcode3[i][_type]['ids']['trakt']
                    #TODO THIS CAN LEAD TO SOME WONKY RESULTS IF THE USERS WANTS A SPECIFIC YEAR FILM
                    if _traktid==_movieobj['ids']['trakt'] or _traktid == _altmovie1 or _traktid == _altmovie2:
                        # print ( 'we found a match' )
                        a['found']=True
                        a['list']='watchlist'
                        return a
                    i+=1
                    # return False
            else:
                #print("couldnt reach trakt")
                a['found']=False
                a['list']=""
                return a
                #return False
    else:
        # print ( "couldnt reach trakt" )
        a['found']=False
        a['list']=""
        return a
        #return False
    return a
