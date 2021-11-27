import collections
import http.cookiejar
import os
import re
import threading
import time
import unicodedata
import urllib.parse

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core.networking import HydrusNetworking

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientStrings
from hydrus.client import ClientThreading
from hydrus.client.networking import ClientNetworkingContexts

def AddCookieToSession( session, name, value, domain, path, expires, secure = False, rest = None ):
    
    version = 0
    port = None
    port_specified = False
    domain_specified = True
    domain_initial_dot = domain.startswith( '.' )
    path_specified = True
    discard = False
    comment = None
    comment_url = None
    
    if rest is None:
        
        rest = {}
        
    
    cookie = http.cookiejar.Cookie( version, name, value, port, port_specified, domain, domain_specified, domain_initial_dot, path, path_specified, secure, expires, discard, comment, comment_url, rest )
    
    session.cookies.set_cookie( cookie )
    
def ConvertDomainIntoAllApplicableDomains( domain, discard_www = True ):
    
    # is an ip address or localhost, possibly with a port
    if '.' not in domain or re.search( r'^[\d\.:]+$', domain ) is not None:
        
        return [ domain ]
        
    
    domains = []
    
    if discard_www:
        
        domain = RemoveWWWFromDomain( domain )
        
    
    while domain.count( '.' ) > 0:
        
        domains.append( domain )
        
        domain = ConvertDomainIntoNextLevelDomain( domain )
        
    
    return domains
    
def ConvertDomainIntoNextLevelDomain( domain ):
    
    return '.'.join( domain.split( '.' )[1:] ) # i.e. strip off the leftmost subdomain maps.google.com -> google.com
    
def ConvertDomainIntoSecondLevelDomain( domain ):
    
    domains = ConvertDomainIntoAllApplicableDomains( domain )
    
    if len( domains ) == 0:
        
        raise HydrusExceptions.URLClassException( 'That url or domain did not seem to be valid!' )
        
    
    return domains[-1]
    
def ConvertHTTPSToHTTP( url ):
    
    if url.startswith( 'http://' ):
        
        return url
        
    elif url.startswith( 'https://' ):
        
        http_url = 'http://' + url[8:]
        
        return http_url
        
    else:
        
        raise Exception( 'Given a url that did not have a scheme!' )
        
    
def ConvertHTTPToHTTPS( url ):
    
    if url.startswith( 'https://' ):
        
        return url
        
    elif url.startswith( 'http://' ):
        
        https_url = 'https://' + url[7:]
        
        return https_url
        
    else:
        
        raise Exception( 'Given a url that did not have a scheme!' )
        
    
def ConvertQueryDictToText( query_dict, single_value_parameters, param_order = None ):
    
    # we now do everything with requests, which does all the unicode -> %20 business naturally, phew
    # we still want to call str explicitly to coerce integers and so on that'll slip in here and there
    
    if param_order is None:
        
        param_order = sorted( query_dict.keys() )
        
        single_value_parameters = list( single_value_parameters )
        single_value_parameters.sort()
        
        for i in range( len( single_value_parameters ) ):
            
            param_order.append( None )
            
        
    
    params = []
    
    single_value_parameter_index = 0
    
    for key in param_order:
        
        if key is None:
            
            try:
                
                params.append( single_value_parameters[ single_value_parameter_index ] )
                
            except IndexError:
                
                continue
                
            
            single_value_parameter_index += 1
            
        else:
            
            if key in query_dict:
                
                params.append( '{}={}'.format( key, query_dict[ key ] ) )
                
            
        
    
    query_text = '&'.join( params )
    
    return query_text
    
def ConvertQueryTextToDict( query_text ):
    
    # we generally do not want quote characters, %20 stuff, in our urls. we would prefer properly formatted unicode
    
    # so, let's replace all keys and values with unquoted versions
    # -but-
    # we only replace if it is a completely reversable operation!
    # odd situations like '6+girls+skirt', which comes here encoded as '6%2Bgirls+skirt', shouldn't turn into '6+girls+skirt'
    # so if there are a mix of encoded and non-encoded, we won't touch it here m8
    
    # except these chars, which screw with GET arg syntax when unquoted
    bad_chars = [ '&', '=', '/', '?', '#', ';', '+' ]
    
    param_order = []
    
    query_dict = {}
    single_value_parameters = []
    
    pairs = query_text.split( '&' )
    
    for pair in pairs:
        
        result = pair.split( '=', 1 )
        
        # for the moment, ignore tracker bugs and so on that have only key and no value
        
        if len( result ) == 1:
            
            ( value, ) = result
            
            if value == '':
                
                continue
                
            
            try:
                
                unquoted_value = urllib.parse.unquote( value )
                
                if True not in ( bad_char in unquoted_value for bad_char in bad_chars ):
                    
                    requoted_value = urllib.parse.quote( unquoted_value )
                    
                    if requoted_value == value:
                        
                        value = unquoted_value
                        
                    
                
            except:
                
                pass
                
            
            single_value_parameters.append( value )
            param_order.append( None )
            
        elif len( result ) == 2:
            
            ( key, value ) = result
            
            try:
                
                unquoted_key = urllib.parse.unquote( key )
                
                if True not in ( bad_char in unquoted_key for bad_char in bad_chars ):
                    
                    requoted_key = urllib.parse.quote( unquoted_key )
                    
                    if requoted_key == key:
                        
                        key = unquoted_key
                        
                    
                
            except:
                
                pass
                
            
            try:
                
                unquoted_value = urllib.parse.unquote( value )
                
                if True not in ( bad_char in unquoted_value for bad_char in bad_chars ):
                    
                    requoted_value = urllib.parse.quote( unquoted_value )
                    
                    if requoted_value == value:
                        
                        value = unquoted_value
                        
                    
                
            except:
                
                pass
                
            
            param_order.append( key )
            
            query_dict[ key ] = value
            
        
    
    return ( query_dict, single_value_parameters, param_order )
    
def ConvertURLClassesIntoAPIPairs( url_classes ):
    
    url_classes = list( url_classes )
    
    NetworkDomainManager.STATICSortURLClassesDescendingComplexity( url_classes )
    
    pairs = []
    
    for url_class in url_classes:
        
        if not url_class.UsesAPIURL():
            
            continue
            
        
        api_url = url_class.GetAPIURL( url_class.GetExampleURL() )
        
        for other_url_class in url_classes:
            
            if other_url_class == url_class:
                
                continue
                
            
            if other_url_class.Matches( api_url ):
                
                pairs.append( ( url_class, other_url_class ) )
                
                break
                
            
        
    
    return pairs
    
def ConvertURLIntoDomain( url ):
    
    parser_result = ParseURL( url )
    
    if parser_result.scheme == '':
        
        raise HydrusExceptions.URLClassException( 'URL "' + url + '" was not recognised--did you forget the http:// or https://?' )
        
    
    if parser_result.netloc == '':
        
        raise HydrusExceptions.URLClassException( 'URL "' + url + '" was not recognised--is it missing a domain?' )
        
    
    domain = parser_result.netloc
    
    return domain
    
def ConvertURLIntoSecondLevelDomain( url ):
    
    domain = ConvertURLIntoDomain( url )
    
    return ConvertDomainIntoSecondLevelDomain( domain )
    
def CookieDomainMatches( cookie, search_domain ):
    
    cookie_domain = cookie.domain
    
    # blah.com is viewable by blah.com
    matches_exactly = cookie_domain == search_domain
    
    # .blah.com is viewable by blah.com
    matches_dot = cookie_domain == '.' + search_domain
    
    # .blah.com applies to subdomain.blah.com, blah.com does not
    valid_subdomain = cookie_domain.startswith( '.' ) and search_domain.endswith( cookie_domain )
    
    return matches_exactly or matches_dot or valid_subdomain
    
def DomainEqualsAnotherForgivingWWW( test_domain, wwwable_domain ):
    
    # domain is either the same or starts with www. or www2. or something
    rule = r'^(www[^\.]*\.)?' + re.escape( wwwable_domain ) + '$'
    
    return re.search( rule, test_domain ) is not None
    
def GetCookie( cookies, search_domain, cookie_name_string_match ):
    
    for cookie in cookies:
        
        if CookieDomainMatches( cookie, search_domain ) and cookie_name_string_match.Matches( cookie.name ):
            
            return cookie
            
        
    
    raise HydrusExceptions.DataMissing( 'Cookie "' + cookie_name_string_match.ToString() + '" not found for domain ' + search_domain + '!' )
    
def GetSearchURLs( url ):
    
    search_urls = set()
    
    search_urls.add( url )
    
    try:
        
        normalised_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
        
        search_urls.add( normalised_url )
        
    except HydrusExceptions.URLClassException:
        
        pass
        
    
    for url in list( search_urls ):
        
        if url.startswith( 'http://' ):
            
            search_urls.add( ConvertHTTPToHTTPS( url ) )
            
        elif url.startswith( 'https://' ):
            
            search_urls.add( ConvertHTTPSToHTTP( url ) )
            
        
    
    for url in list( search_urls ):
        
        p = ParseURL( url )
        
        scheme = p.scheme
        netloc = p.netloc
        path = p.path
        params = ''
        query = p.query
        fragment = p.fragment
        
        if netloc.startswith( 'www' ):
            
            try:
                
                netloc = ConvertDomainIntoSecondLevelDomain( netloc )
                
            except HydrusExceptions.URLClassException:
                
                continue
                
            
        else:
            
            netloc = 'www.' + netloc
            
        
        r = urllib.parse.ParseResult( scheme, netloc, path, params, query, fragment )
        
        search_urls.add( r.geturl() )
        
    
    for url in list( search_urls ):
        
        if url.endswith( '/' ):
            
            search_urls.add( url[:-1] )
            
        else:
            
            search_urls.add( url + '/' )
            
        
    
    return search_urls
    
def NormaliseAndFilterAssociableURLs( urls ):
    
    normalised_urls = set()
    
    for url in urls:
        
        try:
            
            url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
            
        except HydrusExceptions.URLClassException:
            
            continue # not a url--something like "file:///C:/Users/Tall%20Man/Downloads/maxresdefault.jpg" ha ha ha
            
        
        normalised_urls.add( url )
        
    
    associable_urls = { url for url in normalised_urls if HG.client_controller.network_engine.domain_manager.ShouldAssociateURLWithFiles( url ) }
    
    return associable_urls
    
def ParseURL( url: str ) -> urllib.parse.ParseResult:
    
    url = url.strip()
    
    url = UnicodeNormaliseURL( url )
    
    return urllib.parse.urlparse( url )
    
OH_NO_NO_NETLOC_CHARACTERS = '?#'
OH_NO_NO_NETLOC_CHARACTERS_UNICODE_TRANSLATE = { ord( char ) : '_' for char in OH_NO_NO_NETLOC_CHARACTERS }

def UnicodeNormaliseURL( url: str ):
    
    if url.startswith( 'file:' ):
        
        return url
        
    
    # the issue is netloc, blah.com, cannot have certain unicode characters that look like others, or double ( e + accent ) characters that can be one accented-e, so we normalise
    # urllib.urlparse throws a valueerror if these are in, so let's switch out
    
    scheme_splitter = '://'
    netloc_splitter = '/'
    
    if scheme_splitter in url:
        
        ( scheme, netloc_and_path_and_rest ) = url.split( scheme_splitter, 1 )
        
        if netloc_splitter in netloc_and_path_and_rest:
            
            ( netloc, path_and_rest ) = netloc_and_path_and_rest.split( netloc_splitter, 1 )
            
        else:
            
            netloc = netloc_and_path_and_rest
            path_and_rest = None
            
        
        netloc = unicodedata.normalize( 'NFKC', netloc )
        
        netloc = netloc.translate( OH_NO_NO_NETLOC_CHARACTERS_UNICODE_TRANSLATE )
        
        scheme_and_netlock = scheme_splitter.join( ( scheme, netloc ) )
        
        if path_and_rest is None:
            
            url = scheme_and_netlock
            
        else:
            
            url = netloc_splitter.join( ( scheme_and_netlock, path_and_rest ) )
            
        
    
    return url
    
VALID_DENIED = 0
VALID_APPROVED = 1
VALID_UNKNOWN = 2

valid_str_lookup = {}

valid_str_lookup[ VALID_DENIED ] = 'denied'
valid_str_lookup[ VALID_APPROVED ] = 'approved'
valid_str_lookup[ VALID_UNKNOWN ] = 'unknown'

class NetworkDomainManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER
    SERIALISABLE_NAME = 'Domain Manager'
    SERIALISABLE_VERSION = 6
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.engine = None
        
        self._gugs = HydrusSerialisable.SerialisableList()
        self._url_classes = HydrusSerialisable.SerialisableList()
        self._parsers = HydrusSerialisable.SerialisableList()
        self._network_contexts_to_custom_header_dicts = collections.defaultdict( dict )
        
        self._parser_namespaces = []
        
        self._gug_keys_to_display = set()
        
        self._url_class_keys_to_display = set()
        self._url_class_keys_to_parser_keys = HydrusSerialisable.SerialisableBytesDictionary()
        
        self._second_level_domains_to_url_classes = collections.defaultdict( list )
        
        self._second_level_domains_to_network_infrastructure_errors = collections.defaultdict( list )
        
        from hydrus.client.importing.options import TagImportOptions
        
        self._file_post_default_tag_import_options = TagImportOptions.TagImportOptions()
        self._watchable_default_tag_import_options = TagImportOptions.TagImportOptions()
        
        self._url_class_keys_to_default_tag_import_options = {}
        
        self._gug_keys_to_gugs = {}
        self._gug_names_to_gugs = {}
        
        self._parser_keys_to_parsers = {}
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._RecalcCache()
        
    
    def _CleanURLClassKeysToParserKeys( self ):
        
        api_pairs = ConvertURLClassesIntoAPIPairs( self._url_classes )
        
        # anything that goes to an api url will be parsed by that api's parser--it can't have its own
        for ( a, b ) in api_pairs:
            
            unparseable_url_class_key = a.GetClassKey()
            
            if unparseable_url_class_key in self._url_class_keys_to_parser_keys:
                
                del self._url_class_keys_to_parser_keys[ unparseable_url_class_key ]
                
            
        
    
    def _GetDefaultTagImportOptionsForURL( self, url ):
        
        url_class = self._GetURLClass( url )
        
        if url_class is None or url_class.GetURLType() not in ( HC.URL_TYPE_POST, HC.URL_TYPE_WATCHABLE ):
            
            return self._file_post_default_tag_import_options
            
        
        try:
            
            ( url_class, url ) = self._GetNormalisedAPIURLClassAndURL( url )
            
        except HydrusExceptions.URLClassException:
            
            return self._file_post_default_tag_import_options
            
        
        # some lad decided to api convert one url type to another
        if url_class.GetURLType() not in ( HC.URL_TYPE_POST, HC.URL_TYPE_WATCHABLE ):
            
            return self._file_post_default_tag_import_options
            
        
        url_class_key = url_class.GetClassKey()
        
        if url_class_key in self._url_class_keys_to_default_tag_import_options:
            
            return self._url_class_keys_to_default_tag_import_options[ url_class_key ]
            
        else:
            
            url_type = url_class.GetURLType()
            
            if url_type == HC.URL_TYPE_POST:
                
                return self._file_post_default_tag_import_options
                
            elif url_type == HC.URL_TYPE_WATCHABLE:
                
                return self._watchable_default_tag_import_options
                
            else:
                
                raise HydrusExceptions.URLClassException( 'Could not find tag import options for that kind of URL Class!' )
                
            
        
    
    def _GetGUG( self, gug_key_and_name ):
        
        ( gug_key, gug_name ) = gug_key_and_name
        
        if gug_key in self._gug_keys_to_gugs:
            
            return self._gug_keys_to_gugs[ gug_key ]
            
        elif gug_name in self._gug_names_to_gugs:
            
            return self._gug_names_to_gugs[ gug_name ]
            
        else:
            
            return None
            
        
    
    def _GetNormalisedAPIURLClassAndURL( self, url ):
        
        url_class = self._GetURLClass( url )
        
        if url_class is None:
            
            raise HydrusExceptions.URLClassException( 'Could not find a URL Class for ' + url + '!' )
            
        
        seen_url_classes = set()
        
        seen_url_classes.add( url_class )
        
        api_url_class = url_class
        api_url = url
        
        while api_url_class.UsesAPIURL():
            
            api_url = api_url_class.GetAPIURL( api_url )
            
            api_url_class = self._GetURLClass( api_url )
            
            if api_url_class is None:
                
                raise HydrusExceptions.URLClassException( 'Could not find an API URL Class for ' + api_url + ' URL, which originally came from ' + url + '!' )
                
            
            if api_url_class in seen_url_classes:
                
                loop_size = len( seen_url_classes )
                
                if loop_size == 1:
                    
                    message = 'Could not find an API URL Class for ' + url + ' as the url class API-linked to itself!'
                    
                elif loop_size == 2:
                    
                    message = 'Could not find an API URL Class for ' + url + ' as the url class and its API url class API-linked to each other!'
                    
                else:
                    
                    message = 'Could not find an API URL Class for ' + url + ' as it and its API url classes linked in a loop of size ' + HydrusData.ToHumanInt( loop_size ) + '!'
                    
                
                raise HydrusExceptions.URLClassException( message )
                
            
            seen_url_classes.add( api_url_class )
            
        
        api_url = api_url_class.Normalise( api_url )
        
        return ( api_url_class, api_url )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gugs = self._gugs.GetSerialisableTuple()
        serialisable_gug_keys_to_display = [ gug_key.hex() for gug_key in self._gug_keys_to_display ]
        
        serialisable_url_classes = self._url_classes.GetSerialisableTuple()
        serialisable_url_class_keys_to_display = [ url_class_key.hex() for url_class_key in self._url_class_keys_to_display ]
        serialisable_url_class_keys_to_parser_keys = self._url_class_keys_to_parser_keys.GetSerialisableTuple()
        
        serialisable_file_post_default_tag_import_options = self._file_post_default_tag_import_options.GetSerialisableTuple()
        serialisable_watchable_default_tag_import_options = self._watchable_default_tag_import_options.GetSerialisableTuple()
        serialisable_url_class_keys_to_default_tag_import_options = [ ( url_class_key.hex(), tag_import_options.GetSerialisableTuple() ) for ( url_class_key, tag_import_options ) in list(self._url_class_keys_to_default_tag_import_options.items()) ]
        
        serialisable_default_tag_import_options_tuple = ( serialisable_file_post_default_tag_import_options, serialisable_watchable_default_tag_import_options, serialisable_url_class_keys_to_default_tag_import_options )
        
        serialisable_parsers = self._parsers.GetSerialisableTuple()
        serialisable_network_contexts_to_custom_header_dicts = [ ( network_context.GetSerialisableTuple(), list(custom_header_dict.items()) ) for ( network_context, custom_header_dict ) in list(self._network_contexts_to_custom_header_dicts.items()) ]
        
        return ( serialisable_gugs, serialisable_gug_keys_to_display, serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_parsers, serialisable_network_contexts_to_custom_header_dicts )
        
    
    def _GetURLClass( self, url ):
        
        domain = ConvertURLIntoSecondLevelDomain( url )
        
        if domain in self._second_level_domains_to_url_classes:
            
            url_classes = self._second_level_domains_to_url_classes[ domain ]
            
            for url_class in url_classes:
                
                try:
                    
                    url_class.Test( url )
                    
                    return url_class
                    
                except HydrusExceptions.URLClassException:
                    
                    continue
                    
                
            
        
        return None
        
    
    def _GetURLToFetchAndParser( self, url ):
        
        try:
            
            ( parser_url_class, parser_url ) = self._GetNormalisedAPIURLClassAndURL( url )
            
        except HydrusExceptions.URLClassException as e:
            
            raise HydrusExceptions.URLClassException( 'Could not find a parser for ' + url + '!' + os.linesep * 2 + str( e ) )
            
        
        url_class_key = parser_url_class.GetClassKey()
        
        if url_class_key in self._url_class_keys_to_parser_keys:
            
            parser_key = self._url_class_keys_to_parser_keys[ url_class_key ]
            
            if parser_key is not None and parser_key in self._parser_keys_to_parsers:
                
                return ( parser_url, self._parser_keys_to_parsers[ parser_key ] )
                
            
        
        raise HydrusExceptions.URLClassException( 'Could not find a parser for ' + parser_url_class.GetName() + ' URL Class!' )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gugs, serialisable_gug_keys_to_display, serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_parsers, serialisable_network_contexts_to_custom_header_dicts ) = serialisable_info
        
        self._gugs = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gugs )
        
        self._gug_keys_to_display = { bytes.fromhex( serialisable_gug_key ) for serialisable_gug_key in serialisable_gug_keys_to_display }
        
        self._url_classes = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_classes )
        
        self._url_class_keys_to_display = { bytes.fromhex( serialisable_url_class_key ) for serialisable_url_class_key in serialisable_url_class_keys_to_display }
        self._url_class_keys_to_parser_keys = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_class_keys_to_parser_keys )
        
        ( serialisable_file_post_default_tag_import_options, serialisable_watchable_default_tag_import_options, serialisable_url_class_keys_to_default_tag_import_options ) = serialisable_default_tag_import_options_tuple
        
        self._file_post_default_tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_post_default_tag_import_options )
        self._watchable_default_tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_watchable_default_tag_import_options )
        
        self._url_class_keys_to_default_tag_import_options = { bytes.fromhex( serialisable_url_class_key ) : HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options ) for ( serialisable_url_class_key, serialisable_tag_import_options ) in serialisable_url_class_keys_to_default_tag_import_options }
        
        self._parsers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_parsers )
        
        self._network_contexts_to_custom_header_dicts = collections.defaultdict( dict )
        
        for ( serialisable_network_context, custom_header_dict_items ) in serialisable_network_contexts_to_custom_header_dicts:
            
            network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
            custom_header_dict = dict( custom_header_dict_items )
            
            self._network_contexts_to_custom_header_dicts[ network_context ] = custom_header_dict
            
        
    
    def _RecalcCache( self ):
        
        self._second_level_domains_to_url_classes = collections.defaultdict( list )
        
        for url_class in self._url_classes:
            
            domain = ConvertDomainIntoSecondLevelDomain( url_class.GetDomain() )
            
            self._second_level_domains_to_url_classes[ domain ].append( url_class )
            
        
        for url_classes in self._second_level_domains_to_url_classes.values():
            
            NetworkDomainManager.STATICSortURLClassesDescendingComplexity( url_classes )
            
        
        self._gug_keys_to_gugs = { gug.GetGUGKey() : gug for gug in self._gugs }
        self._gug_names_to_gugs = { gug.GetName() : gug for gug in self._gugs }
        
        self._parser_keys_to_parsers = { parser.GetParserKey() : parser for parser in self._parsers }
        
        namespaces = set()
        
        for parser in self._parsers:
            
            namespaces.update( parser.GetNamespaces() )
            
        
        self._parser_namespaces = sorted( namespaces )
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_url_classes, serialisable_network_contexts_to_custom_header_dicts ) = old_serialisable_info
            
            url_classes = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_classes )
            
            url_class_names_to_display = {}
            url_class_names_to_page_parser_keys = HydrusSerialisable.SerialisableBytesDictionary()
            url_class_names_to_gallery_parser_keys = HydrusSerialisable.SerialisableBytesDictionary()
            
            for url_class in url_classes:
                
                name = url_class.GetName()
                
                if url_class.IsPostURL():
                    
                    url_class_names_to_display[ name ] = True
                    
                    url_class_names_to_page_parser_keys[ name ] = None
                    
                
                if url_class.IsGalleryURL() or url_class.IsWatchableURL():
                    
                    url_class_names_to_gallery_parser_keys[ name ] = None
                    
                
            
            serialisable_url_class_names_to_display = list(url_class_names_to_display.items())
            serialisable_url_class_names_to_page_parser_keys = url_class_names_to_page_parser_keys.GetSerialisableTuple()
            serialisable_url_class_names_to_gallery_parser_keys = url_class_names_to_gallery_parser_keys.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_url_classes, serialisable_url_class_names_to_display, serialisable_url_class_names_to_page_parser_keys, serialisable_url_class_names_to_gallery_parser_keys, serialisable_network_contexts_to_custom_header_dicts )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_url_classes, serialisable_url_class_names_to_display, serialisable_url_class_names_to_page_parser_keys, serialisable_url_class_names_to_gallery_parser_keys, serialisable_network_contexts_to_custom_header_dicts ) = old_serialisable_info
            
            parsers = HydrusSerialisable.SerialisableList()
            
            serialisable_parsing_parsers = parsers.GetSerialisableTuple()
            
            url_class_names_to_display = dict( serialisable_url_class_names_to_display )
            
            url_class_keys_to_display = []
            
            url_class_names_to_gallery_parser_keys = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_class_names_to_gallery_parser_keys )
            url_class_names_to_page_parser_keys = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_class_names_to_page_parser_keys )
            
            url_class_keys_to_parser_keys = HydrusSerialisable.SerialisableBytesDictionary()
            
            url_classes = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_classes )
            
            for url_class in url_classes:
                
                url_class_key = url_class.GetClassKey()
                
                name = url_class.GetName()
                
                if name in url_class_names_to_display and url_class_names_to_display[ name ]:
                    
                    url_class_keys_to_display.append( url_class_key )
                    
                
            
            serialisable_url_classes = url_classes.GetSerialisableTuple() # added random key this week, so save these changes back again!
            
            serialisable_url_class_keys_to_display = [ url_class_key.hex() for url_class_key in url_class_keys_to_display ]
            
            serialisable_url_class_keys_to_parser_keys = url_class_keys_to_parser_keys.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts ) = old_serialisable_info
            
            from hydrus.client.importing.options import TagImportOptions
            
            self._file_post_default_tag_import_options = TagImportOptions.TagImportOptions()
            self._watchable_default_tag_import_options = TagImportOptions.TagImportOptions()
            
            self._url_class_keys_to_default_tag_import_options = {}
            
            serialisable_file_post_default_tag_import_options = self._file_post_default_tag_import_options.GetSerialisableTuple()
            serialisable_watchable_default_tag_import_options = self._watchable_default_tag_import_options.GetSerialisableTuple()
            serialisable_url_class_keys_to_default_tag_import_options = [ ( url_class_key.hex(), tag_import_options.GetSerialisableTuple() ) for ( url_class_key, tag_import_options ) in list(self._url_class_keys_to_default_tag_import_options.items()) ]
            
            serialisable_default_tag_import_options_tuple = ( serialisable_file_post_default_tag_import_options, serialisable_watchable_default_tag_import_options, serialisable_url_class_keys_to_default_tag_import_options )
            
            new_serialisable_info = ( serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts ) = old_serialisable_info
            
            gugs = HydrusSerialisable.SerialisableList()
            
            serialisable_gugs = gugs.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_gugs, serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( serialisable_gugs, serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts ) = old_serialisable_info
            
            gugs = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gugs )
            
            gug_keys_to_display = [ gug.GetGUGKey() for gug in gugs if 'ugoira' not in gug.GetName() ]
            
            serialisable_gug_keys_to_display = [ gug_key.hex() for gug_key in gug_keys_to_display ]
            
            new_serialisable_info = ( serialisable_gugs, serialisable_gug_keys_to_display, serialisable_url_classes, serialisable_url_class_keys_to_display, serialisable_url_class_keys_to_parser_keys, serialisable_default_tag_import_options_tuple, serialisable_parsing_parsers, serialisable_network_contexts_to_custom_header_dicts )
            
            return ( 6, new_serialisable_info )
            
        
    
    def AddGUGs( self, new_gugs ):
        
        with self._lock:
            
            gugs = list( self._gugs )
            
            for gug in new_gugs:
                
                gug.SetNonDupeName( [ g.GetName() for g in gugs ] )
                
                gugs.append( gug )
                
            
        
        self.SetGUGs( gugs )
        
    
    def AddParsers( self, new_parsers ):
        
        with self._lock:
            
            parsers = list( self._parsers )
            
            for parser in new_parsers:
                
                parser.SetNonDupeName( [ p.GetName() for p in parsers ] )
                
                parsers.append( parser )
                
            
        
        self.SetParsers( parsers )
        
    
    def AddURLClasses( self, new_url_classes ):
        
        with self._lock:
            
            url_classes = list( self._url_classes )
            
            for url_class in new_url_classes:
                
                url_class.SetNonDupeName( [ u.GetName() for u in url_classes ] )
                
                url_classes.append( url_class )
                
            
        
        self.SetURLClasses( url_classes )
        
    
    def AlreadyHaveExactlyTheseHeaders( self, network_context, headers_list ):
        
        with self._lock:
            
            if network_context in self._network_contexts_to_custom_header_dicts:
                
                custom_headers_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                
                if len( headers_list ) != len( custom_headers_dict ):
                    
                    return False
                    
                
                for ( key, value, reason ) in headers_list:
                    
                    if key not in custom_headers_dict:
                        
                        return False
                        
                    
                    ( existing_value, existing_approved, existing_reason ) = custom_headers_dict[ key ]
                    
                    if existing_value != value:
                        
                        return False
                        
                    
                
                return True
                
            
        
        return False
        
    
    def AlreadyHaveExactlyThisGUG( self, new_gug ):
        
        with self._lock:
            
            # absent irrelevant variables, do we have the exact same object already in?
            
            gug_key_and_name = new_gug.GetGUGKeyAndName()
            
            dupe_gugs = [ gug.Duplicate() for gug in self._gugs ]
            
            for dupe_gug in dupe_gugs:
                
                dupe_gug.SetGUGKeyAndName( gug_key_and_name )
                
                if dupe_gug.DumpToString() == new_gug.DumpToString():
                    
                    return True
                    
                
            
        
        return False
        
    
    def AlreadyHaveExactlyThisParser( self, new_parser ):
        
        with self._lock:
            
            # absent irrelevant variables, do we have the exact same object already in?
            
            new_name = new_parser.GetName()
            new_parser_key = new_parser.GetParserKey()
            new_example_urls = new_parser.GetExampleURLs()
            new_example_parsing_context = new_parser.GetExampleParsingContext()
            
            dupe_parsers = [ ( parser.Duplicate(), parser ) for parser in self._parsers ]
            
            for ( dupe_parser, parser ) in dupe_parsers:
                
                dupe_parser.SetName( new_name )
                dupe_parser.SetParserKey( new_parser_key )
                dupe_parser.SetExampleURLs( new_example_urls )
                dupe_parser.SetExampleParsingContext( new_example_parsing_context )
                
                if dupe_parser.DumpToString() == new_parser.DumpToString():
                    
                    # since these are the 'same', let's merge example urls
                    
                    parser_example_urls = set( parser.GetExampleURLs() )
                    
                    parser_example_urls.update( new_example_urls )
                    
                    parser_example_urls = list( parser_example_urls )
                    
                    parser.SetExampleURLs( parser_example_urls )
                    
                    self._SetDirty()
                    
                    return True
                    
                
            
        
        return False
        
    
    def AlreadyHaveExactlyThisURLClass( self, new_url_class ):
        
        with self._lock:
            
            # absent irrelevant variables, do we have the exact same object already in?
            
            name = new_url_class.GetName()
            match_key = new_url_class.GetClassKey()
            example_url = new_url_class.GetExampleURL()
            
            dupe_url_classes = [ url_class.Duplicate() for url_class in self._url_classes ]
            
            for dupe_url_class in dupe_url_classes:
                
                dupe_url_class.SetName( name )
                dupe_url_class.SetClassKey( match_key )
                dupe_url_class.SetExampleURL( example_url )
                
                if dupe_url_class.DumpToString() == new_url_class.DumpToString():
                    
                    return True
                    
                
            
        
        return False
        
    
    def AutoAddDomainMetadatas( self, domain_metadatas, approved = False ):
        
        for domain_metadata in domain_metadatas:
            
            if not domain_metadata.HasHeaders():
                
                continue
                
            
            with self._lock:
                
                domain = domain_metadata.GetDomain()
                
                network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain )
                
                headers_list = domain_metadata.GetHeaders()
                
                custom_headers_dict = { key : ( value, approved, reason ) for ( key, value, reason ) in headers_list }
                
                self._network_contexts_to_custom_header_dicts[ network_context ] = custom_headers_dict
                
            
        
    
    def AutoAddURLClassesAndParsers( self, new_url_classes, dupe_url_classes, new_parsers ):
        
        for url_class in new_url_classes:
            
            url_class.RegenerateClassKey()
            
        
        for parser in new_parsers:
            
            parser.RegenerateParserKey()
            
        
        # any existing url matches that already do the job of the new ones should be hung on to but renamed
        
        with self._lock:
            
            prefix = 'zzz - renamed due to auto-import - '
            
            renamees = []
            
            for existing_url_class in self._url_classes:
                
                if existing_url_class.GetName().startswith( prefix ):
                    
                    continue
                    
                
                for new_url_class in new_url_classes:
                    
                    if new_url_class.Matches( existing_url_class.GetExampleURL() ) and existing_url_class.Matches( new_url_class.GetExampleURL() ):
                        
                        # the url matches match each other, so they are doing the same job
                        
                        renamees.append( existing_url_class )
                        
                        break
                        
                    
                
                
            
            for renamee in renamees:
                
                existing_names = [ url_class.GetName() for url_class in self._url_classes if url_class != renamee ]
                
                renamee.SetName( prefix + renamee.GetName() )
                
                renamee.SetNonDupeName( existing_names )
                
            
        
        self.AddURLClasses( new_url_classes )
        self.AddParsers( new_parsers )
        
        # we want to match these url matches and parsers together if possible
        
        with self._lock:
            
            url_classes_to_link = list( new_url_classes )
            
            # if downloader adds existing url match but updated parser, we want to update the existing link
            
            for dupe_url_class in dupe_url_classes:
                
                # this is to make sure we have the right match keys for the link update in a minute
                
                actual_existing_dupe_url_class = self._GetURLClass( dupe_url_class.GetExampleURL() )
                
                if actual_existing_dupe_url_class is not None:
                    
                    url_classes_to_link.append( actual_existing_dupe_url_class )
                    
                
            
            new_url_class_keys_to_parser_keys = NetworkDomainManager.STATICLinkURLClassesAndParsers( url_classes_to_link, new_parsers, {} )
            
            self._url_class_keys_to_parser_keys.update( new_url_class_keys_to_parser_keys )
            
            self._CleanURLClassKeysToParserKeys()
            
        
        # let's do a trytolink just in case there are loose ends due to some dupe being discarded earlier (e.g. url match is new, but parser was not).
        
        self.TryToLinkURLClassesAndParsers()
        
    
    def CanValidateInPopup( self, network_contexts ):
        
        # we can always do this for headers
        
        return True
        
    
    def ConvertURLsToMediaViewerTuples( self, urls ):
        
        show_unmatched_urls_in_media_viewer = HG.client_controller.new_options.GetBoolean( 'show_unmatched_urls_in_media_viewer' )
        
        url_tuples = []
        unmatched_url_tuples = []
        
        with self._lock:
            
            for url in urls:
                
                try:
                    
                    url_class = self._GetURLClass( url )
                    
                except HydrusExceptions.URLClassException:
                    
                    continue
                    
                
                if url_class is None:
                    
                    if show_unmatched_urls_in_media_viewer:
                        
                        try:
                            
                            domain = ConvertURLIntoDomain( url )
                            
                        except HydrusExceptions.URLClassException:
                            
                            continue
                            
                        
                        unmatched_url_tuples.append( ( domain, url ) )
                        
                    
                else:
                    
                    url_class_key = url_class.GetClassKey()
                    
                    if url_class_key in self._url_class_keys_to_display:
                        
                        url_class_name = url_class.GetName()
                        
                        url_tuples.append( ( url_class_name, url ) )
                        
                    
                
                if len( url_tuples ) == 10:
                    
                    break
                    
                
            
        
        url_tuples.sort()
        
        unmatched_url_tuples.sort()
        
        url_tuples.extend( unmatched_url_tuples )
        
        return url_tuples
        
    
    def DeleteGUGs( self, deletee_names ):
        
        with self._lock:
            
            gugs = [ gug for gug in self._gugs if gug.GetName() not in deletee_names ]
            
        
        self.SetGUGs( gugs )
        
    
    def DeleteURLClasses( self, deletee_names ):
        
        with self._lock:
            
            url_classes = [ url_class for url_class in self._url_classes if url_class.GetName() not in deletee_names ]
            
        
        self.SetURLClasses( url_classes )
        
    
    def DissolveParserLink( self, url_class_name, parser_name ):
        
        with self._lock:
            
            the_url_class = None
            
            for url_class in self._url_classes:
                
                if url_class.GetName() == url_class_name:
                    
                    the_url_class = url_class
                    
                    break
                    
                
            
            the_parser = None
            
            for parser in self._parsers:
                
                if parser.GetName() == parser_name:
                    
                    the_parser = parser
                    
                    break
                    
                
            
            if the_url_class is not None and the_parser is not None:
                
                url_class_key = the_url_class.GetClassKey()
                parser_key = the_parser.GetParserKey()
                
                if url_class_key in self._url_class_keys_to_parser_keys and self._url_class_keys_to_parser_keys[ url_class_key ] == parser_key:
                    
                    del self._url_class_keys_to_parser_keys[ url_class_key ]
                    
                
            
        
    
    def DomainOK( self, url ):
        
        with self._lock:
            
            try:
                
                domain = ConvertURLIntoSecondLevelDomain( url )
                
            except:
                
                return True
                
            
            # this will become flexible and customisable when I have domain profiles/status/ui
            # also should extend it to 'global', so if multiple domains are having trouble, we maybe assume the whole connection is down? it would really be nicer to have a better sockets-level check there
            
            if domain in self._second_level_domains_to_network_infrastructure_errors:
                
                number_of_errors = HG.client_controller.new_options.GetInteger( 'domain_network_infrastructure_error_number' )
                
                if number_of_errors == 0:
                    
                    return True
                    
                
                error_time_delta = HG.client_controller.new_options.GetInteger( 'domain_network_infrastructure_error_time_delta' )
                
                network_infrastructure_errors = self._second_level_domains_to_network_infrastructure_errors[ domain ]
                
                network_infrastructure_errors = [ timestamp for timestamp in network_infrastructure_errors if not HydrusData.TimeHasPassed( timestamp + error_time_delta ) ]
                
                self._second_level_domains_to_network_infrastructure_errors[ domain ] = network_infrastructure_errors
                
                if len( network_infrastructure_errors ) >= number_of_errors:
                    
                    return False
                    
                elif len( network_infrastructure_errors ) == 0:
                    
                    del self._second_level_domains_to_network_infrastructure_errors[ domain ]
                    
                
            
            return True
            
        
    
    def GenerateValidationPopupProcess( self, network_contexts ):
        
        with self._lock:
            
            header_tuples = []
            
            for network_context in network_contexts:
                
                if network_context in self._network_contexts_to_custom_header_dicts:
                    
                    custom_header_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                    
                    for ( key, ( value, approved, reason ) ) in list(custom_header_dict.items()):
                        
                        if approved == VALID_UNKNOWN:
                            
                            header_tuples.append( ( network_context, key, value, reason ) )
                            
                        
                    
                
            
            process = DomainValidationPopupProcess( self, header_tuples )
            
            return process
            
        
    
    def GetDefaultGUGKeyAndName( self ):
        
        with self._lock:
            
            gug_key = HG.client_controller.new_options.GetKey( 'default_gug_key' )
            gug_name = HG.client_controller.new_options.GetString( 'default_gug_name' )
            
            return ( gug_key, gug_name )
            
        
    
    def GetDefaultTagImportOptions( self ):
        
        with self._lock:
            
            return ( self._file_post_default_tag_import_options, self._watchable_default_tag_import_options, self._url_class_keys_to_default_tag_import_options )
            
        
    
    def GetDefaultTagImportOptionsForPosts( self ):
        
        with self._lock:
            
            return self._file_post_default_tag_import_options.Duplicate()
            
        
    
    def GetDefaultTagImportOptionsForURL( self, url ):
        
        with self._lock:
            
            return self._GetDefaultTagImportOptionsForURL( url )
            
        
    
    def GetDownloader( self, url ):
        
        with self._lock:
            
            # this might be better as getdownloaderkey, but we'll see how it shakes out
            # might also be worth being a getifhasdownloader
            
            # match the url to a url_class, then lookup that in a 'this downloader can handle this url_class type' dict that we'll manage
            
            pass
            
        
    
    def GetGUG( self, gug_key_and_name ):
        
        with self._lock:
            
            return self._GetGUG( gug_key_and_name )
            
        
    
    def GetGUGs( self ):
        
        with self._lock:
            
            return list( self._gugs )
            
        
    
    def GetGUGKeysToDisplay( self ):
        
        with self._lock:
            
            return set( self._gug_keys_to_display )
            
        
    
    def GetHeaders( self, network_contexts ):
        
        with self._lock:
            
            headers = {}
            
            for network_context in network_contexts:
                
                if network_context in self._network_contexts_to_custom_header_dicts:
                    
                    custom_header_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                    
                    for ( key, ( value, approved, reason ) ) in list(custom_header_dict.items()):
                        
                        if approved == VALID_APPROVED:
                            
                            headers[ key ] = value
                            
                        
                    
                
            
            return headers
            
        
    
    def GetInitialSearchText( self, gug_key_and_name ):
        
        with self._lock:
            
            gug = self._GetGUG( gug_key_and_name )
            
            if gug is None:
                
                return 'unknown downloader'
                
            else:
                
                return gug.GetInitialSearchText()
                
            
        
    
    def GetNetworkContextsToCustomHeaderDicts( self ):
        
        with self._lock:
            
            return dict( self._network_contexts_to_custom_header_dicts )
            
        
    
    def GetParser( self, name ):
        
        with self._lock:
            
            for parser in self._parsers:
                
                if parser.GetName() == name:
                    
                    return parser
                    
                
            
        
        return None
        
    
    def GetParsers( self ):
        
        with self._lock:
            
            return list( self._parsers )
            
        
    
    def GetParserNamespaces( self ):
        
        with self._lock:
            
            return list( self._parser_namespaces )
            
        
    
    def GetReferralURL( self, url, referral_url ):
        
        with self._lock:
            
            url_class = self._GetURLClass( url )
            
            if url_class is None:
                
                return referral_url
                
            else:
                
                return url_class.GetReferralURL( url, referral_url )
                
            
        
    
    def GetShareableCustomHeaders( self, network_context ):
        
        with self._lock:
            
            headers_list = []
            
            if network_context in self._network_contexts_to_custom_header_dicts:
                
                custom_header_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                
                for ( key, ( value, approved, reason ) ) in list(custom_header_dict.items()):
                    
                    headers_list.append( ( key, value, reason ) )
                    
                
            
            return headers_list
            
        
    
    def GetURLClass( self, url ):
        
        with self._lock:
            
            return self._GetURLClass( url )
            
        
    
    def GetURLClassFromName( self, name ):
        
        with self._lock:
            
            for url_class in self._url_classes:
                
                if url_class.GetName() == name:
                    
                    return url_class
                    
                
            
        
        raise HydrusExceptions.DataMissing( 'Did not find URL Class called "{}"!'.format( name ) )
        
    
    def GetURLClassHeaders( self, url ):
        
        with self._lock:
            
            url_class = self._GetURLClass( url )
            
            if url_class is not None:
                
                return url_class.GetHeaderOverrides()
                
            else:
                
                return {}
                
            
        
    
    def GetURLClasses( self ):
        
        with self._lock:
            
            return list( self._url_classes )
            
        
    
    def GetURLClassKeysToParserKeys( self ):
        
        with self._lock:
            
            return dict( self._url_class_keys_to_parser_keys )
            
        
    
    def GetURLClassKeysToDisplay( self ):
        
        with self._lock:
            
            return set( self._url_class_keys_to_display )
            
        
    
    def GetURLParseCapability( self, url ):
        
        with self._lock:
            
            url_class = self._GetURLClass( url )
            
            if url_class is None:
                
                return ( HC.URL_TYPE_UNKNOWN, 'unknown url', False, 'unknown url class' )
                
            
            url_type = url_class.GetURLType()
            match_name = url_class.GetName()
            
            try:
                
                ( url_to_fetch, parser ) = self._GetURLToFetchAndParser( url )
                
                can_parse = True
                cannot_parse_reason = ''
                
            except HydrusExceptions.URLClassException as e:
                
                can_parse = False
                cannot_parse_reason = str( e )
                
            
        
        return ( url_type, match_name, can_parse, cannot_parse_reason )
        
    
    def GetURLToFetchAndParser( self, url ):
        
        with self._lock:
            
            result = self._GetURLToFetchAndParser( url )
            
            if HG.network_report_mode:
                
                ( url_to_fetch, parser ) = result
                
                url_class = self._GetURLClass( url )
                
                url_name = url_class.GetName()
                
                url_to_fetch_match = self._GetURLClass( url_to_fetch )
                
                url_to_fetch_name = url_to_fetch_match.GetName()
                
                HydrusData.ShowText( 'request for URL to fetch and parser: {} ({}) -> {} ({}): {}'.format( url, url_name, url_to_fetch, url_to_fetch_name, parser.GetName() ) )
                
            
            return result
            
        
    
    def HasCustomHeaders( self, network_context ):
        
        with self._lock:
            
            return network_context in self._network_contexts_to_custom_header_dicts and len( self._network_contexts_to_custom_header_dicts[ network_context ] ) > 0
            
        
    
    def Initialise( self ):
        
        self._RecalcCache()
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def IsValid( self, network_contexts ):
        
        # for now, let's say that denied headers are simply not added, not that they invalidate a query
        
        for network_context in network_contexts:
            
            if network_context in self._network_contexts_to_custom_header_dicts:
                
                custom_header_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                
                for ( value, approved, reason ) in list(custom_header_dict.values()):
                    
                    if approved == VALID_UNKNOWN:
                        
                        return False
                        
                    
                
            
        
        return True
        
    
    def NormaliseURL( self, url ):
        
        with self._lock:
            
            url_class = self._GetURLClass( url )
            
            if url_class is None:
                
                p = ParseURL( url )
                
                scheme = p.scheme
                netloc = p.netloc
                path = p.path
                params = p.params
                
                ( query_dict, single_value_parameters, param_order ) = ConvertQueryTextToDict( p.query )
                
                query = ConvertQueryDictToText( query_dict, single_value_parameters )
                
                fragment = ''
                
                r = urllib.parse.ParseResult( scheme, netloc, path, params, query, fragment )
                
                normalised_url = r.geturl()
                
            else:
                
                normalised_url = url_class.Normalise( url )
                
            
            return normalised_url
            
        
    
    def OverwriteDefaultGUGs( self, gug_names ):
        
        with self._lock:
            
            from hydrus.client import ClientDefaults
            
            default_gugs = ClientDefaults.GetDefaultGUGs()
            
            existing_gug_names_to_keys = { gug.GetName() : gug.GetGUGKey() for gug in self._gugs }
            
            for gug in default_gugs:
                
                gug_name = gug.GetName()
                
                if gug_name in existing_gug_names_to_keys:
                    
                    gug.SetGUGKey( existing_gug_names_to_keys[ gug_name ] )
                    
                else:
                    
                    gug.RegenerateGUGKey()
                    
                
            
            existing_gugs = list( self._gugs )
            
            new_gugs = [ gug for gug in existing_gugs if gug.GetName() not in gug_names ]
            new_gugs.extend( [ gug for gug in default_gugs if gug.GetName() in gug_names ] )
            
        
        self.SetGUGs( new_gugs )
        
    
    def OverwriteDefaultParsers( self, parser_names ):
        
        with self._lock:
            
            from hydrus.client import ClientDefaults
            
            default_parsers = ClientDefaults.GetDefaultParsers()
            
            existing_parser_names_to_keys = { parser.GetName() : parser.GetParserKey() for parser in self._parsers }
            
            for parser in default_parsers:
                
                name = parser.GetName()
                
                if name in existing_parser_names_to_keys:
                    
                    parser.SetParserKey( existing_parser_names_to_keys[ name ] )
                    
                else:
                    
                    parser.RegenerateParserKey()
                    
                
            
            existing_parsers = list( self._parsers )
            
            new_parsers = [ parser for parser in existing_parsers if parser.GetName() not in parser_names ]
            new_parsers.extend( [ parser for parser in default_parsers if parser.GetName() in parser_names ] )
            
        
        self.SetParsers( new_parsers )
        
    
    def OverwriteDefaultURLClasses( self, url_class_names ):
        
        with self._lock:
            
            from hydrus.client import ClientDefaults
            
            default_url_classes = ClientDefaults.GetDefaultURLClasses()
            
            existing_class_names_to_keys = { url_class.GetName() : url_class.GetClassKey() for url_class in self._url_classes }
            
            for url_class in default_url_classes:
                
                name = url_class.GetName()
                
                if name in existing_class_names_to_keys:
                    
                    url_class.SetClassKey( existing_class_names_to_keys[ name ] )
                    
                else:
                    
                    url_class.RegenerateClassKey()
                    
                
            
            for url_class in default_url_classes:
                
                url_class.RegenerateClassKey()
                
            
            existing_url_classes = list( self._url_classes )
            
            new_url_classes = [ url_class for url_class in existing_url_classes if url_class.GetName() not in url_class_names ]
            new_url_classes.extend( [ url_class for url_class in default_url_classes if url_class.GetName() in url_class_names ] )
            
        
        self.SetURLClasses( new_url_classes )
        
    
    def OverwriteParserLink( self, url_class_name, parser_name ):
        
        with self._lock:
            
            url_class_to_link = None
            
            for url_class in self._url_classes:
                
                if url_class.GetName() == url_class_name:
                    
                    url_class_to_link = url_class
                    
                    break
                    
                
            
            if url_class_to_link is None:
                
                return False
                
            
            parser_to_link = None
            
            for parser in self._parsers:
                
                if parser.GetName() == parser_name:
                    
                    parser_to_link = parser
                    
                    break
                    
                
            
            if parser_to_link is None:
                
                return False
                
            
            url_class_key = url_class_to_link.GetClassKey()
            parser_key = parser_to_link.GetParserKey()
            
            self._url_class_keys_to_parser_keys[ url_class_key ] = parser_key
            
        
    
    def ReportNetworkInfrastructureError( self, url ):
        
        with self._lock:
            
            try:
                
                domain = ConvertURLIntoDomain( url )
                
            except:
                
                return
                
            
            self._second_level_domains_to_network_infrastructure_errors[ domain ].append( HydrusData.GetNow() )
            
        
    
    def ScrubDomainErrors( self, url ):
        
        with self._lock:
            
            try:
                
                domain = ConvertURLIntoSecondLevelDomain( url )
                
            except:
                
                return
                
            
            if domain in self._second_level_domains_to_network_infrastructure_errors:
                
                del self._second_level_domains_to_network_infrastructure_errors[ domain ]
                
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetDefaultFilePostTagImportOptions( self, tag_import_options ):
        
        with self._lock:
            
            self._file_post_default_tag_import_options = tag_import_options
            
        
    
    def SetDefaultGUGKeyAndName( self, gug_key_and_name ):
        
        with self._lock:
            
            ( gug_key, gug_name ) = gug_key_and_name
            
            HG.client_controller.new_options.SetKey( 'default_gug_key', gug_key )
            HG.client_controller.new_options.SetString( 'default_gug_name', gug_name )
            
        
    
    def SetDefaultTagImportOptions( self, file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_tag_import_options ):
        
        with self._lock:
            
            self._file_post_default_tag_import_options = file_post_default_tag_import_options
            self._watchable_default_tag_import_options = watchable_default_tag_import_options
            
            self._url_class_keys_to_default_tag_import_options = url_class_keys_to_tag_import_options
            
            self._SetDirty()
            
        
    
    def SetGUGs( self, gugs ):
        
        with self._lock:
            
            # by default, we will show new gugs
            
            old_gug_keys = { gug.GetGUGKey() for gug in self._gugs }
            gug_keys = { gug.GetGUGKey() for gug in gugs }
            
            added_gug_keys = gug_keys.difference( old_gug_keys )
            
            self._gug_keys_to_display.update( added_gug_keys )
            
            #
            
            self._gugs = HydrusSerialisable.SerialisableList( gugs )
            
            self._RecalcCache()
            
            self._SetDirty()
            
        
    
    def SetGUGKeysToDisplay( self, gug_keys_to_display ):
        
        with self._lock:
            
            self._gug_keys_to_display = set()
            
            self._gug_keys_to_display.update( gug_keys_to_display )
            
            self._SetDirty()
            
        
    
    def SetGlobalUserAgent( self, user_agent_string ):
        
        with self._lock:
            
            self._network_contexts_to_custom_header_dicts[ ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ][ 'User-Agent' ] = ( user_agent_string, True, 'Set by Client API' )
            
        
    
    def SetHeaderValidation( self, network_context, key, approved ):
        
        with self._lock:
            
            if network_context in self._network_contexts_to_custom_header_dicts:
                
                custom_header_dict = self._network_contexts_to_custom_header_dicts[ network_context ]
                
                if key in custom_header_dict:
                    
                    ( value, old_approved, reason ) = custom_header_dict[ key ]
                    
                    custom_header_dict[ key ] = ( value, approved, reason )
                    
                
            
            self._SetDirty()
            
        
    
    def SetNetworkContextsToCustomHeaderDicts( self, network_contexts_to_custom_header_dicts ):
        
        with self._lock:
            
            self._network_contexts_to_custom_header_dicts = network_contexts_to_custom_header_dicts
            
            self._SetDirty()
            
        
    
    def SetParsers( self, parsers ):
        
        with self._lock:
            
            self._parsers = HydrusSerialisable.SerialisableList()
            
            self._parsers.extend( parsers )
            
            self._parsers.sort( key = lambda p: p.GetName() )
            
            # delete orphans
            
            parser_keys = { parser.GetParserKey() for parser in parsers }
            
            deletee_url_class_keys = set()
            
            for ( url_class_key, parser_key ) in self._url_class_keys_to_parser_keys.items():
                
                if parser_key not in parser_keys:
                    
                    deletee_url_class_keys.add( url_class_key )
                    
                
            
            for deletee_url_class_key in deletee_url_class_keys:
                
                del self._url_class_keys_to_parser_keys[ deletee_url_class_key ]
                
            
            #
            
            self._RecalcCache()
            
            self._SetDirty()
            
        
    
    def SetURLClasses( self, url_classes ):
        
        with self._lock:
            
            # by default, we will show post urls
            
            old_post_url_class_keys = { url_class.GetClassKey() for url_class in self._url_classes if url_class.IsPostURL() }
            post_url_class_keys = { url_class.GetClassKey() for url_class in url_classes if url_class.IsPostURL() }
            
            added_post_url_class_keys = post_url_class_keys.difference( old_post_url_class_keys )
            
            self._url_class_keys_to_display.update( added_post_url_class_keys )
            
            #
            
            self._url_classes = HydrusSerialisable.SerialisableList()
            
            self._url_classes.extend( url_classes )
            
            self._url_classes.sort( key = lambda u: u.GetName() )
            
            #
            
            # delete orphans
            
            url_class_keys = { url_class.GetClassKey() for url_class in url_classes }
            
            self._url_class_keys_to_display.intersection_update( url_class_keys )
            
            for deletee_key in set( self._url_class_keys_to_parser_keys.keys() ).difference( url_class_keys ):
                
                del self._url_class_keys_to_parser_keys[ deletee_key ]
                
            
            # any url matches that link to another via the API conversion will not be using parsers
            
            url_class_api_pairs = ConvertURLClassesIntoAPIPairs( self._url_classes )
            
            for ( url_class_original, url_class_api ) in url_class_api_pairs:
                
                url_class_key = url_class_original.GetClassKey()
                
                if url_class_key in self._url_class_keys_to_parser_keys:
                    
                    del self._url_class_keys_to_parser_keys[ url_class_key ]
                    
                
            
            self._RecalcCache()
            
            self._SetDirty()
            
        
    
    def SetURLClassKeysToParserKeys( self, url_class_keys_to_parser_keys ):
        
        with self._lock:
            
            self._url_class_keys_to_parser_keys = HydrusSerialisable.SerialisableBytesDictionary()
            
            self._url_class_keys_to_parser_keys.update( url_class_keys_to_parser_keys )
            
            self._CleanURLClassKeysToParserKeys()
            
            self._SetDirty()
            
        
    
    def SetURLClassKeysToDisplay( self, url_class_keys_to_display ):
        
        with self._lock:
            
            self._url_class_keys_to_display = set()
            
            self._url_class_keys_to_display.update( url_class_keys_to_display )
            
            self._SetDirty()
            
        
    
    def ShouldAssociateURLWithFiles( self, url ):
        
        with self._lock:
            
            url_class = self._GetURLClass( url )
            
            if url_class is None:
                
                return True
                
            
            return url_class.ShouldAssociateWithFiles()
            
        
    
    def TryToLinkURLClassesAndParsers( self ):
        
        with self._lock:
            
            new_url_class_keys_to_parser_keys = NetworkDomainManager.STATICLinkURLClassesAndParsers( self._url_classes, self._parsers, self._url_class_keys_to_parser_keys )
            
            self._url_class_keys_to_parser_keys.update( new_url_class_keys_to_parser_keys )
            
            self._CleanURLClassKeysToParserKeys()
            
            self._SetDirty()
            
        
    
    def URLCanReferToMultipleFiles( self, url ):
        
        with self._lock:
            
            url_class = self._GetURLClass( url )
            
            if url_class is None:
                
                return False
                
            
            return url_class.CanReferToMultipleFiles()
            
        
    
    def URLDefinitelyRefersToOneFile( self, url ):
        
        with self._lock:
            
            url_class = self._GetURLClass( url )
            
            if url_class is None:
                
                return False
                
            
            return url_class.RefersToOneFile()
            
        
    
    @staticmethod
    def STATICLinkURLClassesAndParsers( url_classes, parsers, existing_url_class_keys_to_parser_keys ):
        
        url_classes = list( url_classes )
        
        NetworkDomainManager.STATICSortURLClassesDescendingComplexity( url_classes )
        
        parsers = list( parsers )
        
        parsers.sort( key = lambda p: p.GetName() )
        
        new_url_class_keys_to_parser_keys = {}
        
        api_pairs = ConvertURLClassesIntoAPIPairs( url_classes )
        
        # anything that goes to an api url will be parsed by that api's parser--it can't have its own
        api_pair_unparsable_url_classes = set()
        
        for ( a, b ) in api_pairs:
            
            api_pair_unparsable_url_classes.add( a )
            
        
        #
        
        # I have to do this backwards, going through parsers and then url_classes, so I can do a proper url match lookup like the real domain manager does it
        # otherwise, if we iterate through url matches looking for parsers to match them, we have gallery url matches thinking they match parser post urls
        # e.g.
        # The page parser might say it supports https://danbooru.donmai.us/posts/3198277
        # But the gallery url class might think it recognises that as https://danbooru.donmai.us/posts
        # 
        # So we have to do the normal lookup in the proper descending complexity order, not searching any further than the first, correct match
        
        for parser in parsers:
            
            example_urls = parser.GetExampleURLs()
            
            for example_url in example_urls:
                
                for url_class in url_classes:
                    
                    if url_class in api_pair_unparsable_url_classes:
                        
                        continue
                        
                    
                    if url_class.Matches( example_url ):
                        
                        # we have a match. this is the 'correct' match for this example url, and we should not search any more, so we break below
                        
                        url_class_key = url_class.GetClassKey()
                        
                        parsable = url_class.IsParsable()
                        linkable = url_class_key not in existing_url_class_keys_to_parser_keys and url_class_key not in new_url_class_keys_to_parser_keys
                        
                        if parsable and linkable:
                            
                            new_url_class_keys_to_parser_keys[ url_class_key ] = parser.GetParserKey()
                            
                        
                        break
                        
                    
                
            
        '''
        #
        
        for url_class in url_classes:
            
            if not url_class.IsParsable() or url_class in api_pair_unparsable_url_classes:
                
                continue
                
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in existing_url_class_keys_to_parser_keys:
                
                continue
                
            
            for parser in parsers:
                
                example_urls = parser.GetExampleURLs()
                
                if True in ( url_class.Matches( example_url ) for example_url in example_urls ):
                    
                    new_url_class_keys_to_parser_keys[ url_class_key ] = parser.GetParserKey()
                    
                    break
                    
                
            
        '''
        return new_url_class_keys_to_parser_keys
        
    
    @staticmethod
    def STATICSortURLClassesDescendingComplexity( url_classes ):
        
        # sort reverse = true so most complex come first
        
        # ( num_path_components, num_required_parameters, num_total_parameters, len_example_url )
        url_classes.sort( key = lambda u_c: u_c.GetSortingComplexityKey(), reverse = True )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER ] = NetworkDomainManager

class DomainMetadataPackage( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DOMAIN_METADATA_PACKAGE
    SERIALISABLE_NAME = 'Domain Metadata'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, domain = None, headers_list = None, bandwidth_rules = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        if domain is None:
            
            domain = 'example.com'
            
        
        self._domain = domain
        self._headers_list = headers_list
        self._bandwidth_rules = bandwidth_rules
        
    
    def _GetSerialisableInfo( self ):
        
        if self._bandwidth_rules is None:
            
            serialisable_bandwidth_rules = self._bandwidth_rules
            
        else:
            
            serialisable_bandwidth_rules = self._bandwidth_rules.GetSerialisableTuple()
            
        
        return ( self._domain, self._headers_list, serialisable_bandwidth_rules )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._domain, self._headers_list, serialisable_bandwidth_rules ) = serialisable_info
        
        if serialisable_bandwidth_rules is None:
            
            self._bandwidth_rules = serialisable_bandwidth_rules
            
        else:
            
            self._bandwidth_rules = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_bandwidth_rules )
            
        
    
    def GetBandwidthRules( self ):
        
        return self._bandwidth_rules
        
    
    def GetDetailedSafeSummary( self ):
        
        components = [ 'For domain "' + self._domain + '":' ]
        
        if self.HasBandwidthRules():
            
            m = 'Bandwidth rules: '
            m += os.linesep
            m += os.linesep.join( [ HydrusNetworking.ConvertBandwidthRuleToString( rule ) for rule in self._bandwidth_rules.GetRules() ] )
            
            components.append( m )
            
        
        if self.HasHeaders():
            
            m = 'Headers: '
            m += os.linesep
            m += os.linesep.join( [ key + ' : ' + value + ' - ' + reason for ( key, value, reason ) in self._headers_list ] )
            
            components.append( m )
            
        
        joiner = os.linesep * 2
        
        s = joiner.join( components )
        
        return s
        
    
    def GetDomain( self ):
        
        return self._domain
        
    
    def GetHeaders( self ):
        
        return self._headers_list
        
    
    def GetSafeSummary( self ):
        
        components = []
        
        if self.HasBandwidthRules():
            
            components.append( 'bandwidth rules' )
            
        
        if self.HasHeaders():
            
            components.append( 'headers' )
            
        
        return ' and '.join( components ) + ' - ' + self._domain
        
    
    def HasBandwidthRules( self ):
        
        return self._bandwidth_rules is not None
        
    
    def HasHeaders( self ):
        
        return self._headers_list is not None
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DOMAIN_METADATA_PACKAGE ] = DomainMetadataPackage

class DomainValidationPopupProcess( object ):
    
    def __init__( self, domain_manager, header_tuples ):
        
        self._domain_manager = domain_manager
        
        self._header_tuples = header_tuples
        
        self._is_done = False
        
    
    def IsDone( self ):
        
        return self._is_done
        
    
    def Start( self ):
        
        try:
            
            results = []
            
            for ( network_context, key, value, reason ) in self._header_tuples:
                
                job_key = ClientThreading.JobKey()
                
                # generate question
                
                question = 'For the network context ' + network_context.ToString() + ', can the client set this header?'
                question += os.linesep * 2
                question += key + ': ' + value
                question += os.linesep * 2
                question += reason
                
                job_key.SetVariable( 'popup_yes_no_question', question )
                
                HG.client_controller.pub( 'message', job_key )
                
                result = job_key.GetIfHasVariable( 'popup_yes_no_answer' )
                
                while result is None:
                    
                    if HG.view_shutdown:
                        
                        return
                        
                    
                    time.sleep( 0.25 )
                    
                    result = job_key.GetIfHasVariable( 'popup_yes_no_answer' )
                    
                
                if result:
                    
                    approved = VALID_APPROVED
                    
                else:
                    
                    approved = VALID_DENIED
                    
                
                self._domain_manager.SetHeaderValidation( network_context, key, approved )
                
            
        finally:
            
            self._is_done = True
            
        
    
GALLERY_INDEX_TYPE_PATH_COMPONENT = 0
GALLERY_INDEX_TYPE_PARAMETER = 1

class GalleryURLGenerator( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_URL_GENERATOR
    SERIALISABLE_NAME = 'Gallery URL Generator'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name, gug_key = None, url_template = None, replacement_phrase = None, search_terms_separator = None, initial_search_text = None, example_search_text = None ):
        
        if gug_key is None:
            
            gug_key = HydrusData.GenerateKey()
            
        
        if url_template is None:
            
            url_template = 'https://example.com/search?q=%tags%&index=0'
            
        
        if replacement_phrase is None:
            
            replacement_phrase = '%tags%'
            
        
        if search_terms_separator is None:
            
            search_terms_separator = '+'
            
        
        if initial_search_text is None:
            
            initial_search_text = 'search tags'
            
        
        if example_search_text is None:
            
            example_search_text = 'blue_eyes blonde_hair'
            
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._gallery_url_generator_key = gug_key
        self._url_template = url_template
        self._replacement_phrase = replacement_phrase
        self._search_terms_separator = search_terms_separator
        self._initial_search_text = initial_search_text
        self._example_search_text = example_search_text
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_url_generator_key = self._gallery_url_generator_key.hex()
        
        return ( serialisable_gallery_url_generator_key, self._url_template, self._replacement_phrase, self._search_terms_separator, self._initial_search_text, self._example_search_text )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gallery_url_generator_key, self._url_template, self._replacement_phrase, self._search_terms_separator, self._initial_search_text, self._example_search_text ) = serialisable_info
        
        self._gallery_url_generator_key = bytes.fromhex( serialisable_gallery_url_generator_key )
        
    
    def CheckFunctional( self ):
        
        try:
            
            example_url = self.GetExampleURL()
            
            ( url_type, match_name, can_parse, cannot_parse_reason ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( example_url )
            
        except Exception as e:
            
            raise HydrusExceptions.ParseException( 'Unusual error: {}'.format( e ) )
            
        
        if url_type == HC.URL_TYPE_UNKNOWN:
            
            raise HydrusExceptions.ParseException( 'No URL Class for example URL!' )
            
        
        if not can_parse:
            
            raise HydrusExceptions.ParseException( 'Cannot parse {}: {}'.format( match_name, cannot_parse_reason ) )
            
        
    
    def GenerateGalleryURL( self, query_text ):
        
        if self._replacement_phrase == '':
            
            raise HydrusExceptions.GUGException( 'No replacement phrase!' )
            
        
        if self._replacement_phrase not in self._url_template:
            
            raise HydrusExceptions.GUGException( 'Replacement phrase not in URL template!' )
            
        
        ( first_part, second_part ) = self._url_template.split( self._replacement_phrase, 1 )
        
        search_phrase_seems_to_go_in_path = '?' not in first_part
        
        search_terms = query_text.split( ' ' )
        
        # if a user enters "%20" in a query, or any other percent-encoded char, we turn it into human here, lest it be re-quoted in a moment
        # if a user enters "%25", i.e. "%", followed by some characters, then all bets are off
        search_terms = [ urllib.parse.unquote( search_term ) for search_term in search_terms ]
        
        if search_phrase_seems_to_go_in_path:
            
            # encode all this gubbins since requests won't be able to do it
            # this basically fixes e621 searches for 'male/female', which through some httpconf trickery are embedded in path but end up in a query, so need to be encoded right beforehand
            
            encoded_search_terms = [ urllib.parse.quote( search_term, safe = '' ) for search_term in search_terms ]
            
        else:
            
            encoded_search_terms = []
            
            for search_term in search_terms:
                
                # when the tags separator is '+' but the tags include '6+girls', we run into fun internet land
                
                bad_chars = [ self._search_terms_separator, '&', '=', '/', '?', '#', ';' ]
                
                if True in ( bad_char in search_term for bad_char in bad_chars ):
                    
                    search_term = urllib.parse.quote( search_term, safe = '' )
                    
                
                encoded_search_terms.append( search_term )
                
            
        
        try:
            
            search_phrase = self._search_terms_separator.join( encoded_search_terms )
            
            gallery_url = self._url_template.replace( self._replacement_phrase, search_phrase )
            
        except Exception as e:
            
            raise HydrusExceptions.GUGException( str( e ) )
            
        
        return gallery_url
        
    
    def GenerateGalleryURLs( self, query_text ):
        
        return ( self.GenerateGalleryURL( query_text ), )
        
    
    def GetExampleURL( self ):
        
        return self.GenerateGalleryURL( self._example_search_text )
        
    
    def GetExampleURLs( self ):
        
        return ( self.GetExampleURL(), )
        
    
    def GetGUGKey( self ):
        
        return self._gallery_url_generator_key
        
    
    def GetGUGKeyAndName( self ):
        
        return ( self._gallery_url_generator_key, self._name )
        
    
    def GetInitialSearchText( self ):
        
        return self._initial_search_text
        
    
    def GetSafeSummary( self ):
        
        return 'Downloader "' + self._name + '" - ' + ConvertURLIntoDomain( self.GetExampleURL() )
        
    
    def GetURLTemplateVariables( self ):
        
        return ( self._url_template, self._replacement_phrase, self._search_terms_separator, self._example_search_text )
        
    
    def IsFunctional( self ):
        
        try:
            
            self.CheckFunctional()
            
            return True
            
        except HydrusExceptions.ParseException:
            
            return False
            
        
    
    def SetGUGKey( self, gug_key: bytes ):
        
        self._gallery_url_generator_key = gug_key
        
    
    def SetGUGKeyAndName( self, gug_key_and_name ):
        
        ( gug_key, name ) = gug_key_and_name
        
        self._gallery_url_generator_key = gug_key
        self._name = name
        
    
    def RegenerateGUGKey( self ):
        
        self._gallery_url_generator_key = HydrusData.GenerateKey()
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_URL_GENERATOR ] = GalleryURLGenerator

class NestedGalleryURLGenerator( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NESTED_GALLERY_URL_GENERATOR
    SERIALISABLE_NAME = 'Nested Gallery URL Generator'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name, gug_key = None, initial_search_text = None, gug_keys_and_names = None ):
        
        if gug_key is None:
            
            gug_key = HydrusData.GenerateKey()
            
        
        if initial_search_text is None:
            
            initial_search_text = 'search tags'
            
        
        if gug_keys_and_names is None:
            
            gug_keys_and_names = []
            
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._gallery_url_generator_key = gug_key
        self._initial_search_text = initial_search_text
        self._gug_keys_and_names = gug_keys_and_names
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gug_key = self._gallery_url_generator_key.hex()
        serialisable_gug_keys_and_names = [ ( gug_key.hex(), gug_name ) for ( gug_key, gug_name ) in self._gug_keys_and_names ]
        
        return ( serialisable_gug_key, self._initial_search_text, serialisable_gug_keys_and_names )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gug_key, self._initial_search_text, serialisable_gug_keys_and_names ) = serialisable_info
        
        self._gallery_url_generator_key = bytes.fromhex( serialisable_gug_key )
        self._gug_keys_and_names = [ ( bytes.fromhex( gug_key ), gug_name ) for ( gug_key, gug_name ) in serialisable_gug_keys_and_names ]
        
    
    def CheckFunctional( self ):
        
        for gug_key_and_name in self._gug_keys_and_names:
            
            gug = HG.client_controller.network_engine.domain_manager.GetGUG( gug_key_and_name )
            
            if gug is not None:
                
                gug.CheckFunctional()
                
            
        
    
    def GenerateGalleryURLs( self, query_text ):
        
        gallery_urls = []
        
        for gug_key_and_name in self._gug_keys_and_names:
            
            gug = HG.client_controller.network_engine.domain_manager.GetGUG( gug_key_and_name )
            
            if gug is not None:
                
                gallery_urls.append( gug.GenerateGalleryURL( query_text ) )
                
            
        
        return gallery_urls
        
    
    def GetExampleURLs( self ):
        
        example_urls = []
        
        for gug_key_and_name in self._gug_keys_and_names:
            
            gug = HG.client_controller.network_engine.domain_manager.GetGUG( gug_key_and_name )
            
            if gug is not None:
                
                example_urls.append( gug.GetExampleURL() )
                
            
        
        return example_urls
        
    
    def GetGUGKey( self ):
        
        return self._gallery_url_generator_key
        
    
    def GetGUGKeys( self ):
        
        return [ gug_key for ( gug_key, gug_name ) in self._gug_keys_and_names ]
        
    
    def GetGUGKeysAndNames( self ):
        
        return list( self._gug_keys_and_names )
        
    
    def GetGUGKeyAndName( self ):
        
        return ( self._gallery_url_generator_key, self._name )
        
    
    def GetGUGNames( self ):
        
        return [ gug_name for ( gug_key, gug_name ) in self._gug_keys_and_names ]
        
    
    def GetInitialSearchText( self ):
        
        return self._initial_search_text
        
    
    def GetSafeSummary( self ):
        
        return 'Nested downloader "' + self._name + '" - ' + ', '.join( ( name for ( gug_key, name ) in self._gug_keys_and_names ) )
        
    
    def IsFunctional( self ):
        
        try:
            
            self.CheckFunctional()
            
            return True
            
        except HydrusExceptions.ParseException:
            
            return False
            
        
    
    def RegenerateGUGKey( self ):
        
        self._gallery_url_generator_key = HydrusData.GenerateKey()
        
        self._gug_keys_and_names = [ ( HydrusData.GenerateKey(), name ) for ( gug_key, name ) in self._gug_keys_and_names ]
        
    
    def RepairGUGs( self, available_gugs ):
        
        available_keys_to_gugs = { gug.GetGUGKey() : gug for gug in available_gugs }
        available_names_to_gugs = { gug.GetName() : gug for gug in available_gugs }
        
        good_gug_keys_and_names = []
        
        for ( gug_key, gug_name ) in self._gug_keys_and_names:
            
            if gug_key in available_keys_to_gugs:
                
                gug = available_keys_to_gugs[ gug_key ]
                
            elif gug_name in available_names_to_gugs:
                
                gug = available_names_to_gugs[ gug_name ]
                
            else:
                
                continue
                
            
            good_gug_keys_and_names.append( ( gug.GetGUGKey(), gug.GetName() ) )
            
        
        self._gug_keys_and_names = good_gug_keys_and_names
        
    
    def SetGUGKey( self, gug_key: bytes ):
        
        self._gallery_url_generator_key = gug_key
        
    
    def SetGUGKeyAndName( self, gug_key_and_name ):
        
        ( gug_key, name ) = gug_key_and_name
        
        self._gallery_url_generator_key = gug_key
        self._name = name
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NESTED_GALLERY_URL_GENERATOR ] = NestedGalleryURLGenerator

def RemoveWWWFromDomain( domain ):
    
    if domain.count( '.' ) > 1 and domain.startswith( 'www' ):
        
        domain = ConvertDomainIntoNextLevelDomain( domain )
        
    
    return domain
    
SEND_REFERRAL_URL_ONLY_IF_PROVIDED = 0
SEND_REFERRAL_URL_NEVER = 1
SEND_REFERRAL_URL_CONVERTER_IF_NONE_PROVIDED = 2
SEND_REFERRAL_URL_ONLY_CONVERTER = 3

SEND_REFERRAL_URL_TYPES = [ SEND_REFERRAL_URL_ONLY_IF_PROVIDED, SEND_REFERRAL_URL_NEVER, SEND_REFERRAL_URL_CONVERTER_IF_NONE_PROVIDED, SEND_REFERRAL_URL_ONLY_CONVERTER ]

send_referral_url_string_lookup = {}

send_referral_url_string_lookup[ SEND_REFERRAL_URL_ONLY_IF_PROVIDED ] = 'send a referral url if available'
send_referral_url_string_lookup[ SEND_REFERRAL_URL_NEVER ] = 'never send a referral url'
send_referral_url_string_lookup[ SEND_REFERRAL_URL_CONVERTER_IF_NONE_PROVIDED ] = 'use the converter if no referral is available'
send_referral_url_string_lookup[ SEND_REFERRAL_URL_ONLY_CONVERTER ] = 'always use the converter referral url'

class URLClass( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_URL_CLASS
    SERIALISABLE_NAME = 'URL Class'
    SERIALISABLE_VERSION = 11
    
    def __init__(
        self,
        name: str,
        url_class_key = None,
        url_type = None,
        preferred_scheme = 'https',
        netloc = 'hostname.com',
        path_components = None,
        parameters = None,
        has_single_value_parameters = False,
        single_value_parameters_string_match = None,
        header_overrides = None,
        api_lookup_converter = None,
        send_referral_url = SEND_REFERRAL_URL_ONLY_IF_PROVIDED,
        referral_url_converter = None,
        gallery_index_type = None,
        gallery_index_identifier = None,
        gallery_index_delta = 1,
        example_url = 'https://hostname.com/post/page.php?id=123456&s=view'
    ):
        
        if url_class_key is None:
            
            url_class_key = HydrusData.GenerateKey()
            
        
        if url_type is None:
            
            url_type = HC.URL_TYPE_POST
            
        
        if path_components is None:
            
            path_components = []
            
            path_components.append( ( ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ), None ) )
            path_components.append( ( ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'page.php', example_string = 'page.php' ), None ) )
            
        
        if parameters is None:
            
            parameters = {}
            
            parameters[ 's' ] = ( ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'view', example_string = 'view' ), None )
            parameters[ 'id' ] = ( ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FLEXIBLE, match_value = ClientStrings.NUMERIC, example_string = '123456' ), None )
            
        
        if single_value_parameters_string_match is None:
            
            single_value_parameters_string_match = ClientStrings.StringMatch()
            
        
        if header_overrides is None:
            
            header_overrides = {}
            
        
        if api_lookup_converter is None:
            
            api_lookup_converter = ClientStrings.StringConverter( example_string = 'https://hostname.com/post/page.php?id=123456&s=view' )
            
        
        if referral_url_converter is None:
            
            referral_url_converter = ClientStrings.StringConverter( example_string = 'https://hostname.com/post/page.php?id=123456&s=view' )
            
        
        # if the args are not serialisable stuff, lets overwrite here
        
        path_components = HydrusSerialisable.SerialisableList( path_components )
        parameters = HydrusSerialisable.SerialisableDictionary( parameters )
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._url_class_key = url_class_key
        self._url_type = url_type
        self._preferred_scheme = preferred_scheme
        self._netloc = netloc
        
        self._match_subdomains = False
        self._keep_matched_subdomains = False
        self._alphabetise_get_parameters = True
        self._can_produce_multiple_files = False
        self._should_be_associated_with_files = True
        self._keep_fragment = False
        
        self._path_components = path_components
        self._parameters = parameters
        self._has_single_value_parameters = has_single_value_parameters
        self._single_value_parameters_string_match = single_value_parameters_string_match
        self._header_overrides = header_overrides
        self._api_lookup_converter = api_lookup_converter
        
        self._send_referral_url = send_referral_url
        self._referral_url_converter = referral_url_converter
        
        self._gallery_index_type = gallery_index_type
        self._gallery_index_identifier = gallery_index_identifier
        self._gallery_index_delta = gallery_index_delta
        
        self._example_url = example_url
        
    
    def _ClipNetLoc( self, netloc ):
        
        if self._keep_matched_subdomains:
            
            # for domains like artistname.website.com, where removing the subdomain may break the url, we leave it alone
            
            pass
            
        else:
            
            # for domains like mediaserver4.website.com, where multiple subdomains serve the same content as the larger site
            
            if not DomainEqualsAnotherForgivingWWW( netloc, self._netloc ):
                
                netloc = self._netloc
                
            
        
        return netloc
        
    
    def _ClipAndFleshOutPath( self, path, allow_clip = True ):
        
        # /post/show/1326143/akunim-anthro-armband-armwear-clothed-clothing-fem
        
        while path.startswith( '/' ):
            
            path = path[ 1 : ]
            
        
        # post/show/1326143/akunim-anthro-armband-armwear-clothed-clothing-fem
        
        path_components = path.split( '/' )
        
        if allow_clip or len( path_components ) < len( self._path_components ):
            
            clipped_path_components = []
            
            for ( index, ( string_match, default ) ) in enumerate( self._path_components ):
                
                if len( path_components ) > index: # the given path has the value
                    
                    clipped_path_component = path_components[ index ]
                    
                elif default is not None:
                    
                    clipped_path_component = default
                    
                else:
                    
                    raise HydrusExceptions.URLClassException( 'Could not clip path--given url appeared to be too short!' )
                    
                
                clipped_path_components.append( clipped_path_component )
                
            
            path = '/'.join( clipped_path_components )
            
        
        # post/show/1326143
        
        path = '/' + path
        
        # /post/show/1326143
        
        return path
        
    
    def _ClipAndFleshOutQuery( self, query, allow_clip = True ):
        
        ( query_dict, single_value_parameters, param_order ) = ConvertQueryTextToDict( query )
        
        if allow_clip:
            
            query_dict = { key : value for ( key, value ) in query_dict.items() if key in self._parameters }
            
        
        for ( key, ( string_match, default ) ) in self._parameters.items():
            
            if key not in query_dict:
                
                if default is None:
                    
                    raise HydrusExceptions.URLClassException( 'Could not flesh out query--no default for ' + key + ' defined!' )
                    
                else:
                    
                    query_dict[ key ] = default
                    
                    param_order.append( key )
                    
                
            
        
        if self._alphabetise_get_parameters:
            
            param_order = None
            
        
        if not self._has_single_value_parameters:
            
            single_value_parameters = []
            
        
        query = ConvertQueryDictToText( query_dict, single_value_parameters, param_order = param_order )
        
        return query
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_class_key = self._url_class_key.hex()
        serialisable_path_components = [ ( string_match.GetSerialisableTuple(), default ) for ( string_match, default ) in self._path_components ]
        serialisable_parameters = [ ( key, ( string_match.GetSerialisableTuple(), default ) ) for ( key, ( string_match, default ) ) in self._parameters.items() ]
        serialisable_single_value_parameters_string_match = self._single_value_parameters_string_match.GetSerialisableTuple()
        serialisable_header_overrides = list( self._header_overrides.items() )
        serialisable_api_lookup_converter = self._api_lookup_converter.GetSerialisableTuple()
        serialisable_referral_url_converter = self._referral_url_converter.GetSerialisableTuple()
        
        booleans = ( self._match_subdomains, self._keep_matched_subdomains, self._alphabetise_get_parameters, self._can_produce_multiple_files, self._should_be_associated_with_files, self._keep_fragment )
        
        return (
            serialisable_url_class_key,
            self._url_type,
            self._preferred_scheme,
            self._netloc,
            booleans,
            serialisable_path_components,
            serialisable_parameters,
            self._has_single_value_parameters,
            serialisable_single_value_parameters_string_match,
            serialisable_header_overrides,
            serialisable_api_lookup_converter,
            self._send_referral_url,
            serialisable_referral_url_converter,
            self._gallery_index_type,
            self._gallery_index_identifier,
            self._gallery_index_delta,
            self._example_url
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            serialisable_url_class_key,
            self._url_type,
            self._preferred_scheme,
            self._netloc,
            booleans,
            serialisable_path_components,
            serialisable_parameters,
            self._has_single_value_parameters,
            serialisable_single_value_parameters_string_match,
            serialisable_header_overrides,
            serialisable_api_lookup_converter,
            self._send_referral_url,
            serialisable_referral_url_converter,
            self._gallery_index_type,
            self._gallery_index_identifier,
            self._gallery_index_delta,
            self._example_url
            ) = serialisable_info
        
        ( self._match_subdomains, self._keep_matched_subdomains, self._alphabetise_get_parameters, self._can_produce_multiple_files, self._should_be_associated_with_files, self._keep_fragment ) = booleans
        
        self._url_class_key = bytes.fromhex( serialisable_url_class_key )
        self._path_components = [ ( HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_match ), default ) for ( serialisable_string_match, default ) in serialisable_path_components ]
        self._parameters = { key : ( HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_match ), default ) for ( key, ( serialisable_string_match, default ) ) in serialisable_parameters }
        self._single_value_parameters_string_match = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_single_value_parameters_string_match )
        self._header_overrides = dict( serialisable_header_overrides )
        self._api_lookup_converter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_api_lookup_converter )
        self._referral_url_converter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_referral_url_converter )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, example_url ) = old_serialisable_info
            
            url_class_key = HydrusData.GenerateKey()
            
            serialisable_url_class_key = url_class_key.hex()
            
            api_lookup_converter = ClientStrings.StringConverter( example_string = example_url )
            
            serialisable_api_lookup_converter = api_lookup_converter.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, example_url )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, example_url ) = old_serialisable_info
            
            if url_type in ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST ):
                
                should_be_associated_with_files = True
                
            else:
                
                should_be_associated_with_files = False
                
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, should_be_associated_with_files, example_url )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, should_be_associated_with_files, example_url ) = old_serialisable_info
            
            can_produce_multiple_files = False
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, can_produce_multiple_files, should_be_associated_with_files, example_url )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, can_produce_multiple_files, should_be_associated_with_files, example_url ) = old_serialisable_info
            
            gallery_index_type = None
            gallery_index_identifier = None
            gallery_index_delta = 1
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url ) = old_serialisable_info
            
            path_components = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_path_components )
            parameters = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_parameters )
            
            path_components = [ ( value, None ) for value in path_components ]
            parameters = { key : ( value, None ) for ( key, value ) in list(parameters.items()) }
            
            serialisable_path_components = [ ( string_match.GetSerialisableTuple(), default ) for ( string_match, default ) in path_components ]
            serialisable_parameters = [ ( key, ( string_match.GetSerialisableTuple(), default ) ) for ( key, ( string_match, default ) ) in list(parameters.items()) ]
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url ) = old_serialisable_info
            
            send_referral_url = SEND_REFERRAL_URL_ONLY_IF_PROVIDED
            referral_url_converter = ClientStrings.StringConverter( example_string = 'https://hostname.com/post/page.php?id=123456&s=view' )
            
            serialisable_referrel_url_converter = referral_url_converter.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url )
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url ) = old_serialisable_info
            
            alphabetise_get_parameters = True
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, alphabetise_get_parameters, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url )
            
            return ( 8, new_serialisable_info )
            
        
        if version == 8:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, match_subdomains, keep_matched_subdomains, alphabetise_get_parameters, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, can_produce_multiple_files, should_be_associated_with_files, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url ) = old_serialisable_info
            
            keep_fragment = False
            
            booleans = ( match_subdomains, keep_matched_subdomains, alphabetise_get_parameters, can_produce_multiple_files, should_be_associated_with_files, keep_fragment )
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, booleans, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url )
            
            return ( 9, new_serialisable_info )
            
        
        if version == 9:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, booleans, serialisable_path_components, serialisable_parameters, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url ) = old_serialisable_info
            
            header_overrides = {}
            
            serialisable_header_overrides = list( header_overrides.items() )
            
            new_serialisable_info = ( serialisable_url_class_key, url_type, preferred_scheme, netloc, booleans, serialisable_path_components, serialisable_parameters, serialisable_header_overrides, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url )
            
            return ( 10, new_serialisable_info )
            
        
        if version == 10:
            
            ( serialisable_url_class_key, url_type, preferred_scheme, netloc, booleans, serialisable_path_components, serialisable_parameters, serialisable_header_overrides, serialisable_api_lookup_converter, send_referral_url, serialisable_referrel_url_converter, gallery_index_type, gallery_index_identifier, gallery_index_delta, example_url ) = old_serialisable_info
            
            has_single_value_parameters = False
            single_value_parameters_string_match = ClientStrings.StringMatch()
            
            serialisable_single_value_parameters_match = single_value_parameters_string_match.GetSerialisableTuple()
            
            new_serialisable_info = (
                serialisable_url_class_key,
                url_type,
                preferred_scheme,
                netloc,
                booleans,
                serialisable_path_components,
                serialisable_parameters,
                has_single_value_parameters,
                serialisable_single_value_parameters_match,
                serialisable_header_overrides,
                serialisable_api_lookup_converter,
                send_referral_url,
                serialisable_referrel_url_converter,
                gallery_index_type,
                gallery_index_identifier,
                gallery_index_delta,
                example_url
            )
            
            return ( 11, new_serialisable_info )
            
        
    
    def AlphabetiseGetParameters( self ):
        
        return self._alphabetise_get_parameters
        
    
    def CanGenerateNextGalleryPage( self ):
        
        if self._url_type == HC.URL_TYPE_GALLERY:
            
            if self._gallery_index_type is not None:
                
                return True
                
            
        
        return False
        
    
    def CanReferToMultipleFiles( self ):
        
        is_a_gallery_page = self._url_type in ( HC.URL_TYPE_GALLERY, HC.URL_TYPE_WATCHABLE )
        
        is_a_multipost_post_page = self._url_type == HC.URL_TYPE_POST and self._can_produce_multiple_files
        
        return is_a_gallery_page or is_a_multipost_post_page
        
    
    def ClippingIsAppropriate( self ):
        
        return self._should_be_associated_with_files or self.UsesAPIURL()
        
    
    def GetAPIURL( self, url = None ):
        
        if url is None:
            
            url = self._example_url
            
        
        url = self.Normalise( url )
        
        return self._api_lookup_converter.Convert( url )
        
    
    def GetClassKey( self ):
        
        return self._url_class_key
        
    
    def GetDomain( self ):
        
        return self._netloc
        
    
    def GetExampleURL( self ):
        
        return self._example_url
        
    
    def GetGalleryIndexValues( self ):
        
        return ( self._gallery_index_type, self._gallery_index_identifier, self._gallery_index_delta )
        
    
    def GetHeaderOverrides( self ):
        
        return self._header_overrides
        
    
    def GetNextGalleryPage( self, url ):
        
        url = self.Normalise( url )
        
        p = ParseURL( url )
        
        scheme = p.scheme
        netloc = p.netloc
        path = p.path
        query = p.query
        params = ''
        fragment = p.fragment
        
        if self._gallery_index_type == GALLERY_INDEX_TYPE_PATH_COMPONENT:
            
            page_index_path_component_index = self._gallery_index_identifier
            
            while path.startswith( '/' ):
                
                path = path[ 1 : ]
                
            
            path_components = path.split( '/' )
            
            try:
                
                page_index = path_components[ page_index_path_component_index ]
                
            except IndexError:
                
                raise HydrusExceptions.URLClassException( 'Could not generate next gallery page--not enough path components!' )
                
            
            try:
                
                page_index = int( page_index )
                
            except:
                
                raise HydrusExceptions.URLClassException( 'Could not generate next gallery page--index component was not an integer!' )
                
            
            path_components[ page_index_path_component_index ] = str( page_index + self._gallery_index_delta )
            
            path = '/' + '/'.join( path_components )
            
        elif self._gallery_index_type == GALLERY_INDEX_TYPE_PARAMETER:
            
            page_index_name = self._gallery_index_identifier
            
            ( query_dict, single_value_parameters, param_order ) = ConvertQueryTextToDict( query )
            
            if page_index_name not in query_dict:
                
                raise HydrusExceptions.URLClassException( 'Could not generate next gallery page--did not find ' + str( self._gallery_index_identifier ) + ' in parameters!' )
                
            
            page_index = query_dict[ page_index_name ]
            
            try:
                
                page_index = int( page_index )
                
            except:
                
                raise HydrusExceptions.URLClassException( 'Could not generate next gallery page--index component was not an integer!' )
                
            
            query_dict[ page_index_name ] = page_index + self._gallery_index_delta
            
            if self._alphabetise_get_parameters:
                
                param_order = None
                
            
            if not self._has_single_value_parameters:
                
                single_value_parameters = []
                
            
            query = ConvertQueryDictToText( query_dict, single_value_parameters, param_order = param_order )
            
        else:
            
            raise NotImplementedError( 'Did not understand the next gallery page rules!' )
            
        
        r = urllib.parse.ParseResult( scheme, netloc, path, params, query, fragment )
        
        return r.geturl()
        
    
    def GetReferralURL( self, url, referral_url ):
        
        if self._send_referral_url == SEND_REFERRAL_URL_ONLY_IF_PROVIDED:
            
            return referral_url
            
        elif self._send_referral_url == SEND_REFERRAL_URL_NEVER:
            
            return None
            
        elif self._send_referral_url in ( SEND_REFERRAL_URL_CONVERTER_IF_NONE_PROVIDED, SEND_REFERRAL_URL_ONLY_CONVERTER ):
            
            try:
                
                converted_referral_url = self._referral_url_converter.Convert( url )
                
            except HydrusExceptions.StringConvertException:
                
                return referral_url
                
            
            p1 = self._send_referral_url == SEND_REFERRAL_URL_ONLY_CONVERTER
            p2 = self._send_referral_url == SEND_REFERRAL_URL_CONVERTER_IF_NONE_PROVIDED and referral_url is None
            
            if p1 or p2:
                
                return converted_referral_url
                
            else:
                
                return referral_url
                
            
        
        return referral_url
        
    
    def GetSafeSummary( self ):
        
        return 'URL Class "' + self._name + '" - ' + ConvertURLIntoDomain( self.GetExampleURL() )
        
    
    def GetSingleValueParameterData( self ):
        
        return ( self._has_single_value_parameters, self._single_value_parameters_string_match )
        
    
    def GetSortingComplexityKey( self ):
        
        # we sort url classes so that
        # site.com/post/123456
        # comes before
        # site.com/search?query=blah
        
        # I used to do gallery first, then post, then file, but it ultimately was unhelpful in some situations and better handled by strict component/parameter matching
        
        num_required_path_components = len( [ 1 for ( string_match, default ) in self._path_components if default is None ] )
        num_total_path_components = len( self._path_components )
        num_required_parameters = len( [ 1 for ( key, ( string_match, default ) ) in self._parameters.items() if default is None ] )
        num_total_parameters = len( self._parameters )
        len_example_url = len( self.Normalise( self._example_url ) )
        
        return ( num_required_parameters, num_total_path_components, num_required_parameters, num_total_parameters, len_example_url )
        
    
    def GetURLBooleans( self ):
        
        return ( self._match_subdomains, self._keep_matched_subdomains, self._alphabetise_get_parameters, self._can_produce_multiple_files, self._should_be_associated_with_files, self._keep_fragment )
        
    
    def GetURLType( self ):
        
        return self._url_type
        
    
    def IsGalleryURL( self ):
        
        return self._url_type == HC.URL_TYPE_GALLERY
        
    
    def IsParsable( self ):
        
        return self._url_type in ( HC.URL_TYPE_POST, HC.URL_TYPE_GALLERY, HC.URL_TYPE_WATCHABLE )
        
    
    def IsPostURL( self ):
        
        return self._url_type == HC.URL_TYPE_POST
        
    
    def IsWatchableURL( self ):
        
        return self._url_type == HC.URL_TYPE_WATCHABLE
        
    
    def Matches( self, url ):
        
        try:
            
            self.Test( url )
            
            return True
            
        except HydrusExceptions.URLClassException:
            
            return False
            
        
    
    def MatchesSubdomains( self ):
        
        return self._match_subdomains
        
    
    def Normalise( self, url ):
        
        p = ParseURL( url )
        
        scheme = self._preferred_scheme
        params = ''
        
        if self._keep_fragment:
            
            fragment = p.fragment
            
        else:
            
            fragment = ''
            
        
        if self.ClippingIsAppropriate():
            
            netloc = self._ClipNetLoc( p.netloc )
            path = self._ClipAndFleshOutPath( p.path )
            query = self._ClipAndFleshOutQuery( p.query )
            
        else:
            
            netloc = p.netloc
            path = self._ClipAndFleshOutPath( p.path, allow_clip = False )
            query = self._ClipAndFleshOutQuery( p.query, allow_clip = False )
            
        
        r = urllib.parse.ParseResult( scheme, netloc, path, params, query, fragment )
        
        return r.geturl()
        
    
    def RefersToOneFile( self ):
        
        is_a_direct_file_page = self._url_type == HC.URL_TYPE_FILE
        
        is_a_single_file_post_page = self._url_type == HC.URL_TYPE_POST and not self._can_produce_multiple_files
        
        return is_a_direct_file_page or is_a_single_file_post_page
        
    
    def RegenerateClassKey( self ):
        
        self._url_class_key = HydrusData.GenerateKey()
        
    
    def SetAlphabetiseGetParameters( self, alphabetise_get_parameters: bool ):
        
        self._alphabetise_get_parameters = alphabetise_get_parameters
        
    
    def SetClassKey( self, match_key ):
        
        self._url_class_key = match_key
        
    
    def SetExampleURL( self, example_url ):
        
        self._example_url = example_url
        
    
    def SetSingleValueParameterData( self, has_single_value_parameters: bool, single_value_parameters_string_match: ClientStrings.StringMatch ):
        
        self._has_single_value_parameters = has_single_value_parameters
        self._single_value_parameters_string_match = single_value_parameters_string_match
        
    
    def SetURLBooleans(
        self,
        match_subdomains: bool,
        keep_matched_subdomains: bool,
        alphabetise_get_parameters: bool,
        can_produce_multiple_files: bool,
        should_be_associated_with_files: bool,
        keep_fragment: bool
    ):
        
        self._match_subdomains = match_subdomains
        self._keep_matched_subdomains = keep_matched_subdomains
        self._alphabetise_get_parameters = alphabetise_get_parameters
        self._can_produce_multiple_files = can_produce_multiple_files
        self._should_be_associated_with_files = should_be_associated_with_files
        self._keep_fragment = keep_fragment
        
    
    def ShouldAssociateWithFiles( self ):
        
        return self._should_be_associated_with_files
        
    
    def Test( self, url ):
        
        p = ParseURL( url )
        
        if self._match_subdomains:
            
            if p.netloc != self._netloc and not p.netloc.endswith( '.' + self._netloc ):
                
                raise HydrusExceptions.URLClassException( p.netloc + ' (potentially excluding subdomains) did not match ' + self._netloc )
                
            
        else:
            
            if not DomainEqualsAnotherForgivingWWW( p.netloc, self._netloc ):
                
                raise HydrusExceptions.URLClassException( p.netloc + ' did not match ' + self._netloc )
                
            
        
        url_path = p.path
        
        while url_path.startswith( '/' ):
            
            url_path = url_path[ 1 : ]
            
        
        url_path_components = url_path.split( '/' )
        
        for ( index, ( string_match, default ) ) in enumerate( self._path_components ):
            
            if len( url_path_components ) > index:
                
                url_path_component = url_path_components[ index ]
                
                try:
                    
                    string_match.Test( url_path_component )
                    
                except HydrusExceptions.StringMatchException as e:
                    
                    raise HydrusExceptions.URLClassException( str( e ) )
                    
                
            elif default is None:
                
                raise HydrusExceptions.URLClassException( url_path + ' did not have enough of the required path components!' )
                
            
        
        ( url_parameters, single_value_parameters, param_order ) = ConvertQueryTextToDict( p.query )
        
        for ( key, ( string_match, default ) ) in self._parameters.items():
            
            if key not in url_parameters:
                
                if default is None:
                    
                    raise HydrusExceptions.URLClassException( key + ' not found in ' + p.query )
                    
                else:
                    
                    continue
                    
                
            
            value = url_parameters[ key ]
            
            try:
                
                string_match.Test( value )
                
            except HydrusExceptions.StringMatchException as e:
                
                raise HydrusExceptions.URLClassException( str( e ) )
                
            
        
        if self._has_single_value_parameters:
            
            if len( single_value_parameters ) == 0:
                
                raise HydrusExceptions.URLClassException( 'Was expecting single-value parameter(s), but this URL did not seem to have any.' )
                
            
            for single_value_parameter in single_value_parameters:
                
                try:
                    
                    self._single_value_parameters_string_match.Test( single_value_parameter )
                    
                except HydrusExceptions.StringMatchException as e:
                    
                    raise HydrusExceptions.URLClassException( str( e ) )
                    
                
            
        
    
    def ToTuple( self ):
        
        return ( self._url_type, self._preferred_scheme, self._netloc, self._path_components, self._parameters, self._api_lookup_converter, self._send_referral_url, self._referral_url_converter, self._example_url )
        
    
    def UsesAPIURL( self ):
        
        return self._api_lookup_converter.MakesChanges()
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_URL_CLASS ] = URLClass
