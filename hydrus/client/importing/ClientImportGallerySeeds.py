import collections
import itertools
import os
import random
import threading
import time
import traceback
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientParsing
from hydrus.client.importing import ClientImporting
from hydrus.client.metadata import ClientTags

def ConvertAllParseResultsToSubGallerySeeds( all_parse_results, can_generate_more_pages ):
    
    sub_gallery_seeds = []
    
    seen_urls = set()
    
    for parse_results in all_parse_results:
        
        parsed_request_headers = ClientParsing.GetHTTPHeadersFromParseResults( parse_results )
        
        parsed_urls = ClientParsing.GetURLsFromParseResults( parse_results, ( HC.URL_TYPE_SUB_GALLERY, ), only_get_top_priority = True )
        
        parsed_urls = HydrusData.DedupeList( parsed_urls )
        
        parsed_urls = [ url for url in parsed_urls if url not in seen_urls ]
        
        seen_urls.update( parsed_urls )
        
        for url in parsed_urls:
            
            gallery_seed = GallerySeed( url = url, can_generate_more_pages = can_generate_more_pages )
            
            gallery_seed.AddRequestHeaders( parsed_request_headers )
            
            gallery_seed.AddParseResults( parse_results )
            
            sub_gallery_seeds.append( gallery_seed )
            
        
    
    return sub_gallery_seeds
    

def GenerateGallerySeedLogStatus( statuses_to_counts ):
    
    num_successful = statuses_to_counts[ CC.STATUS_SUCCESSFUL_AND_NEW ]
    num_ignored = statuses_to_counts[ CC.STATUS_VETOED ]
    num_failed = statuses_to_counts[ CC.STATUS_ERROR ]
    num_skipped = statuses_to_counts[ CC.STATUS_SKIPPED ]
    num_unknown = statuses_to_counts[ CC.STATUS_UNKNOWN ]
    
    # add some kind of '(512 files found (so far))', which may be asking too much here
    # might be this is complicated and needs to be (partly) done in the object, which will know if it is paused or whatever.
    
    status_strings = []
    
    if num_successful > 0:
        
        s = HydrusData.ToHumanInt( num_successful ) + ' successful'
        
        status_strings.append( s )
        
    
    if num_ignored > 0:
        
        status_strings.append( HydrusData.ToHumanInt( num_ignored ) + ' ignored' )
        
    
    if num_failed > 0:
        
        status_strings.append( HydrusData.ToHumanInt( num_failed ) + ' failed' )
        
    
    if num_skipped > 0:
        
        status_strings.append( HydrusData.ToHumanInt( num_skipped ) + ' skipped' )
        
    
    if num_unknown > 0:
        
        status_strings.append( HydrusData.ToHumanInt( num_unknown ) + ' pending' )
        
    
    status = ', '.join( status_strings )
    
    total = sum( statuses_to_counts.values() )
    
    total_processed = total - num_unknown
    
    return ( status, ( total_processed, total ) )
    

class GallerySeed( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_SEED
    SERIALISABLE_NAME = 'Gallery Log Entry'
    SERIALISABLE_VERSION = 4
    
    def __init__( self, url = None, can_generate_more_pages = True ):
        
        if url is None:
            
            url = 'https://nostrils-central.cx/index.php?post=s&tag=hyper_nostrils&page=3'
            
        else:
            
            try:
                
                url = CG.client_controller.network_engine.domain_manager.NormaliseURL( url )
                
            except HydrusExceptions.URLClassException:
                
                pass
                
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.url = url
        self._can_generate_more_pages = can_generate_more_pages
        
        self._external_filterable_tags = set()
        self._external_additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
        
        self.created = HydrusTime.GetNow()
        self.modified = self.created
        self.status = CC.STATUS_UNKNOWN
        self.note = ''
        
        self._referral_url = None
        self._request_headers = {}
        
        self._force_next_page_url_generation = False
        
        self._run_token = HydrusData.GenerateKey()
        
    
    def __eq__( self, other ):
        
        if isinstance( other, GallerySeed ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self.url, self._run_token ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_external_filterable_tags = list( self._external_filterable_tags )
        serialisable_external_additional_service_keys_to_tags = self._external_additional_service_keys_to_tags.GetSerialisableTuple()
        
        return (
            self.url,
            self._can_generate_more_pages,
            serialisable_external_filterable_tags,
            serialisable_external_additional_service_keys_to_tags,
            self.created,
            self.modified,
            self.status,
            self.note,
            self._referral_url,
            self._request_headers
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            self.url,
            self._can_generate_more_pages,
            serialisable_external_filterable_tags,
            serialisable_external_additional_service_keys_to_tags,
            self.created,
            self.modified,
            self.status,
            self.note,
            self._referral_url,
            self._request_headers
            ) = serialisable_info
        
        self._external_filterable_tags = set( serialisable_external_filterable_tags )
        self._external_additional_service_keys_to_tags = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_external_additional_service_keys_to_tags )
        
    
    def _UpdateModified( self ):
        
        self.modified = HydrusTime.GetNow()
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( url, can_generate_more_pages, created, modified, status, note, referral_url ) = old_serialisable_info
            
            external_additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
            serialisable_external_additional_service_keys_to_tags = external_additional_service_keys_to_tags.GetSerialisableTuple()
            
            new_serialisable_info = ( url, can_generate_more_pages, serialisable_external_additional_service_keys_to_tags, created, modified, status, note, referral_url )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( url, can_generate_more_pages, serialisable_external_additional_service_keys_to_tags, created, modified, status, note, referral_url ) = old_serialisable_info
            
            external_filterable_tags = set()
            
            serialisable_external_filterable_tags = list( external_filterable_tags )
            
            new_serialisable_info = ( url, can_generate_more_pages, serialisable_external_filterable_tags, serialisable_external_additional_service_keys_to_tags, created, modified, status, note, referral_url )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( url, can_generate_more_pages, serialisable_external_filterable_tags, serialisable_external_additional_service_keys_to_tags, created, modified, status, note, referral_url ) = old_serialisable_info
            
            request_headers = {}
            
            new_serialisable_info = (
                url,
                can_generate_more_pages,
                serialisable_external_filterable_tags,
                serialisable_external_additional_service_keys_to_tags,
                created,
                modified,
                status,
                note,
                referral_url,
                request_headers
            )
            
            return ( 4, new_serialisable_info )
            
        
    
    def AddExternalAdditionalServiceKeysToTags( self, service_keys_to_tags ):
        
        self._external_additional_service_keys_to_tags.update( service_keys_to_tags )
        
    
    def AddExternalFilterableTags( self, tags ):
        
        self._external_filterable_tags.update( tags )
        
    
    def AddParseResults( self, parse_results ):
        
        tags = ClientParsing.GetTagsFromParseResults( parse_results )
        
        self._external_filterable_tags.update( tags )
        
        self._UpdateModified()
        
    
    def AddRequestHeaders( self, request_headers: dict ):
        
        self._request_headers.update( request_headers )
        
    
    def ForceNextPageURLGeneration( self ):
        
        self._force_next_page_url_generation = True
        
    
    def GenerateRestartedDuplicate( self, can_generate_more_pages ):
        
        gallery_seed = GallerySeed( url = self.url, can_generate_more_pages = can_generate_more_pages )
        
        if can_generate_more_pages:
            
            gallery_seed.ForceNextPageURLGeneration()
            
        
        return gallery_seed
        
    
    def GetAPIInfoDict( self, simple ):
        
        d = {}
        
        d[ 'url' ] = self.url
        d[ 'created' ] = self.created
        d[ 'modified' ] = self.modified
        d[ 'status' ] = self.status
        d[ 'note' ] = self.note
        
        return d
        
    
    def GetExampleNetworkJob( self, network_job_factory ):
        
        try:
            
            ( url_to_check, parser ) = CG.client_controller.network_engine.domain_manager.GetURLToFetchAndParser( self.url )
            
        except HydrusExceptions.URLClassException:
            
            url_to_check = self.url
            
        
        network_job = network_job_factory( 'GET', url_to_check )
        
        return network_job
        
    
    def SetReferralURL( self, referral_url ):
        
        self._referral_url = referral_url
        
    
    def SetRunToken( self, run_token: bytes ):
        
        self._run_token = run_token
        
    
    def SetStatus( self, status, note = '', exception = None ):
        
        if exception is not None:
            
            first_line = repr( exception ).splitlines()[0]
            
            note = f'{first_line}{HC.UNICODE_ELLIPSIS} (Copy note to see full error)'
            note += os.linesep
            note += traceback.format_exc()
            
            HydrusData.Print( 'Error when processing ' + self.url + ' !' )
            HydrusData.Print( traceback.format_exc() )
            
        
        self.status = status
        self.note = note
        
        self._UpdateModified()
        
    
    def WorksInNewSystem( self ):
        
        ( url_type, match_name, can_parse, cannot_parse_reason ) = CG.client_controller.network_engine.domain_manager.GetURLParseCapability( self.url )
        
        if url_type == HC.URL_TYPE_GALLERY and can_parse:
            
            return True
            
        
        return False
        
    
    def WorkOnURL( self, gallery_token_name, gallery_seed_log: "GallerySeedLog", file_seeds_callable, status_hook, title_hook, network_job_factory, network_job_presentation_context_factory, file_import_options, gallery_urls_seen_before = None ):
        
        if gallery_urls_seen_before is None:
            
            gallery_urls_seen_before = set()
            
        
        gallery_urls_seen_before.add( self.url )
        
        # maybe something like 'append urls' vs 'reverse-prepend' for subs or something
        
        # should also take--and populate--a set of urls we have seen this 'run', so we can bomb out if next_gallery_url ends up in some loop
        
        num_urls_added = 0
        num_urls_already_in_file_seed_cache = 0
        num_urls_total = 0
        result_404 = False
        added_new_gallery_pages = False
        stop_reason = ''
        
        try:
            
            gallery_url = self.url
            
            url_for_child_referral = gallery_url
            
            ( url_type, match_name, can_parse, cannot_parse_reason ) = CG.client_controller.network_engine.domain_manager.GetURLParseCapability( gallery_url )
            
            if url_type not in ( HC.URL_TYPE_GALLERY, HC.URL_TYPE_WATCHABLE ):
                
                raise HydrusExceptions.VetoException( 'Did not recognise this as a gallery or watchable URL!' )
                
            
            if not can_parse:
                
                raise HydrusExceptions.VetoException( 'Cannot parse {}: {}'.format( match_name, cannot_parse_reason) )
                
            
            ( url_to_check, parser ) = CG.client_controller.network_engine.domain_manager.GetURLToFetchAndParser( gallery_url )
            
            status_hook( 'downloading gallery page' )
            
            if self._referral_url is not None and self._referral_url != url_to_check:
                
                referral_url = self._referral_url
                
            elif gallery_url != url_to_check:
                
                referral_url = gallery_url
                
            else:
                
                referral_url = None
                
            
            network_job = network_job_factory( 'GET', url_to_check, referral_url = referral_url )
            
            for ( key, value ) in self._request_headers.items():
                
                network_job.AddAdditionalHeader( key, value )
                
            
            network_job.SetGalleryToken( gallery_token_name )
            
            network_job.OverrideBandwidth( 30 )
            
            CG.client_controller.network_engine.AddJob( network_job )
            
            with network_job_presentation_context_factory( network_job ) as njpc:
                
                network_job.WaitUntilDone()
                
            
            parsing_text = network_job.GetContentText()
            
            actual_fetched_url = network_job.GetActualFetchedURL()
            
            do_parse = True
            
            if actual_fetched_url != url_to_check:
                
                ( url_type, match_name, can_parse, cannot_parse_reason ) = CG.client_controller.network_engine.domain_manager.GetURLParseCapability( actual_fetched_url )
                
                if url_type == HC.URL_TYPE_GALLERY:
                    
                    if can_parse:
                        
                        gallery_url = actual_fetched_url
                        
                        url_for_child_referral = gallery_url
                        
                        ( url_to_check, parser ) = CG.client_controller.network_engine.domain_manager.GetURLToFetchAndParser( gallery_url )
                        
                    else:
                        
                        do_parse = False
                        
                        status = CC.STATUS_ERROR
                        
                        note = 'Could not parse {}: {}'.format( match_name, cannot_parse_reason )
                        
                    
                else:
                    
                    do_parse = False
                    
                    from hydrus.client.importing import ClientImportFileSeeds
                    
                    file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, actual_fetched_url )
                    
                    file_seed.SetReferralURL( url_for_child_referral )

                    file_seed.AddRequestHeaders( self._request_headers )
                    
                    file_seeds_callable( ( file_seed, ) )
                    
                    status = CC.STATUS_SUCCESSFUL_AND_NEW
                    
                    note = 'was redirected to a non-gallery url, which has been queued as a file import'
                    
                
            
            if do_parse:
                
                parsing_context = {
                    'gallery_url' : gallery_url,
                    'url' : url_to_check,
                    'post_index' : '0'
                }
                
                all_parse_results = parser.Parse( parsing_context, parsing_text )
                
                if len( all_parse_results ) == 0:
                    
                    raise HydrusExceptions.VetoException( 'The parser found nothing in the document!' )
                    
                
                file_seeds = ClientImporting.ConvertAllParseResultsToFileSeeds( all_parse_results, url_for_child_referral, file_import_options )
                
                title = ClientParsing.GetTitleFromAllParseResults( all_parse_results )
                
                if title is not None:
                    
                    title_hook( title )
                    
                
                for file_seed in file_seeds:
                    
                    file_seed.AddExternalFilterableTags( self._external_filterable_tags )
                    file_seed.AddExternalAdditionalServiceKeysToTags( self._external_additional_service_keys_to_tags )
                    
                
                num_urls_total = len( file_seeds )
                
                ( num_urls_added, num_urls_already_in_file_seed_cache, can_search_for_more_files, stop_reason ) = file_seeds_callable( file_seeds )
                
                status = CC.STATUS_SUCCESSFUL_AND_NEW
                
                note = HydrusData.ToHumanInt( num_urls_added ) + ' new urls found'
                
                if num_urls_already_in_file_seed_cache > 0:
                    
                    note += ' (' + HydrusData.ToHumanInt( num_urls_already_in_file_seed_cache ) + ' of page already in)'
                    
                
                if not can_search_for_more_files:
                    
                    note += ' - ' + stop_reason
                    
                
                if parser.CanOnlyGenerateGalleryURLs() or self._force_next_page_url_generation:
                    
                    can_add_more_gallery_urls = True
                    
                else:
                    
                    # only keep searching if we found any files, otherwise this could be a blank results page with another stub page
                    can_add_more_gallery_urls = num_urls_added > 0 and can_search_for_more_files
                    
                
                flattened_results = list( itertools.chain.from_iterable( all_parse_results ) )
                
                parsed_request_headers = ClientParsing.GetHTTPHeadersFromParseResults( flattened_results )
                
                self._request_headers.update( parsed_request_headers )
                
                sub_gallery_seeds = ConvertAllParseResultsToSubGallerySeeds( all_parse_results, can_generate_more_pages = self._can_generate_more_pages )
                
                new_sub_gallery_seeds = [ sub_gallery_seed for sub_gallery_seed in sub_gallery_seeds if sub_gallery_seed.url not in gallery_urls_seen_before ]
                
                if len( new_sub_gallery_seeds ) > 0:
                    
                    for sub_gallery_seed in sub_gallery_seeds:
                        
                        sub_gallery_seed.SetRunToken( self._run_token )
                        sub_gallery_seed.SetReferralURL( url_for_child_referral )
                        sub_gallery_seed.AddExternalFilterableTags( self._external_filterable_tags )
                        sub_gallery_seed.AddExternalAdditionalServiceKeysToTags( self._external_additional_service_keys_to_tags )
                        
                        gallery_urls_seen_before.add( sub_gallery_seed.url )
                        
                    
                    gallery_seed_log.AddGallerySeeds( sub_gallery_seeds, parent_gallery_seed = self )
                    
                    added_new_gallery_pages = True
                    
                    note += ' - {} sub-gallery urls found'.format( HydrusData.ToHumanInt( len( new_sub_gallery_seeds ) ) )
                    
                
                if self._can_generate_more_pages and can_add_more_gallery_urls:
                    
                    next_page_urls = ClientParsing.GetURLsFromParseResults( flattened_results, ( HC.URL_TYPE_NEXT, ), only_get_top_priority = True )
                    
                    if self.url in next_page_urls:
                        
                        next_page_urls.remove( self.url )
                        
                    
                    if url_to_check in next_page_urls:
                        
                        next_page_urls.remove( url_to_check )
                        
                    
                    if len( next_page_urls ) > 0:
                        
                        next_page_generation_phrase = ' next gallery pages found'
                        
                    else:
                        
                        # we have failed to parse a next page url, but we would still like one, so let's see if the url match can provide one
                        
                        url_class = CG.client_controller.network_engine.domain_manager.GetURLClass( url_to_check )
                        
                        if url_class is not None and url_class.CanGenerateNextGalleryPage():
                            
                            try:
                                
                                next_page_url = url_class.GetNextGalleryPage( url_to_check )
                                
                                next_page_urls = [ next_page_url ]
                                
                            except Exception as e:
                                
                                note += ' - Attempted to generate a next gallery page url, but failed!'
                                note += os.linesep
                                note += traceback.format_exc()
                                
                            
                        
                        next_page_generation_phrase = ' next gallery pages extrapolated from url class'
                        
                    
                    if len( next_page_urls ) > 0:
                        
                        next_page_urls = HydrusData.DedupeList( next_page_urls )
                        
                        new_next_page_urls = [ next_page_url for next_page_url in next_page_urls if next_page_url not in gallery_urls_seen_before ]
                        
                        duplicate_next_page_urls = gallery_urls_seen_before.intersection( new_next_page_urls )
                        
                        num_new_next_page_urls = len( new_next_page_urls )
                        num_dupe_next_page_urls = len( duplicate_next_page_urls )
                        
                        if num_new_next_page_urls > 0:
                            
                            next_gallery_seeds = [ GallerySeed( next_page_url ) for next_page_url in new_next_page_urls ]
                            
                            for next_gallery_seed in next_gallery_seeds:
                                
                                next_gallery_seed.SetRunToken( self._run_token )
                                next_gallery_seed.SetReferralURL( url_for_child_referral )
                                next_gallery_seed.AddExternalFilterableTags( self._external_filterable_tags )
                                next_gallery_seed.AddExternalAdditionalServiceKeysToTags( self._external_additional_service_keys_to_tags )
                                
                            
                            gallery_seed_log.AddGallerySeeds( next_gallery_seeds, parent_gallery_seed = self )
                            
                            added_new_gallery_pages = True
                            
                            gallery_urls_seen_before.update( new_next_page_urls )
                            
                            if num_dupe_next_page_urls == 0:
                                
                                note += ' - ' + HydrusData.ToHumanInt( num_new_next_page_urls ) + next_page_generation_phrase
                                
                            else:
                                
                                note += ' - ' + HydrusData.ToHumanInt( num_new_next_page_urls ) + next_page_generation_phrase + ', but ' + HydrusData.ToHumanInt( num_dupe_next_page_urls ) + ' had already been visited this run and were not added'
                                
                            
                        else:
                            
                            note += ' - ' + HydrusData.ToHumanInt( num_dupe_next_page_urls ) + next_page_generation_phrase + ', but they had already been visited this run and were not added'
                            
                        
                    
                
            
            self.SetStatus( status, note = note )
            
        except HydrusExceptions.ShutdownException:
            
            pass
            
        except HydrusExceptions.VetoException as e:
            
            status = CC.STATUS_VETOED
            
            note = str( e )
            
            self.SetStatus( status, note = note )
            
            if isinstance( e, HydrusExceptions.CancelledException ):
                
                status_hook( 'cancelled!' )
                
                time.sleep( 2 )
                
            
        except HydrusExceptions.InsufficientCredentialsException:
            
            status = CC.STATUS_VETOED
            note = '403'
            
            self.SetStatus( status, note = note )
            
            status_hook( '403' )
            
            time.sleep( 2 )
            
            result_404 = True
            
        except HydrusExceptions.NotFoundException:
            
            status = CC.STATUS_VETOED
            note = '404'
            
            self.SetStatus( status, note = note )
            
            status_hook( '404' )
            
            time.sleep( 2 )
            
            result_404 = True
            
        except Exception as e:
            
            status = CC.STATUS_ERROR
            
            self.SetStatus( status, exception = e )
            
            status_hook( 'error!' )
            
            time.sleep( 3 )
            
            if isinstance( e, HydrusExceptions.NetworkException ): # so the larger queue can set a delaywork or whatever
                
                raise
                
            
        finally:
            
            gallery_seed_log.NotifyGallerySeedsUpdated( ( self, ) )
            
        
        return ( num_urls_added, num_urls_already_in_file_seed_cache, num_urls_total, result_404, added_new_gallery_pages, stop_reason )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_SEED ] = GallerySeed

class GallerySeedLog( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_SEED_LOG
    SERIALISABLE_NAME = 'Gallery Log'
    SERIALISABLE_VERSION = 1
    
    COMPACT_NUMBER = 100
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._gallery_seeds = HydrusSerialisable.SerialisableList()
        
        self._gallery_seeds_to_indices = {}
        
        self._gallery_seed_log_key = HydrusData.GenerateKey()
        
        self._status_cache = None
        
        self._status_dirty = True
        
        self._lock = threading.Lock()
        
    
    def __len__( self ):
        
        return len( self._gallery_seeds )
        
    
    def _GenerateStatus( self ):
        
        statuses_to_counts = self._GetStatusesToCounts()
        
        self._status_cache = GenerateGallerySeedLogStatus( statuses_to_counts )
        
        self._status_dirty = False
        
    
    def _GetNextGallerySeed( self, status: int ) -> typing.Optional[ GallerySeed ]:
        
        for gallery_seed in self._gallery_seeds:
            
            if gallery_seed.status == status:
                
                return gallery_seed
                
            
        
        return None
        
    
    def _GetStatusesToCounts( self ):
        
        statuses_to_counts = collections.Counter()
        
        for gallery_seed in self._gallery_seeds:
            
            statuses_to_counts[ gallery_seed.status ] += 1
            
        
        return statuses_to_counts
        
    
    def _GetGallerySeeds( self, status = None ):
        
        if status is None:
            
            return list( self._gallery_seeds )
            
        else:
            
            return [ gallery_seed for gallery_seed in self._gallery_seeds if gallery_seed.status == status ]
            
        
    
    def _GetSerialisableInfo( self ):
        
        return self._gallery_seeds.GetSerialisableTuple()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        with self._lock:
            
            self._gallery_seeds = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_info )
            
            self._gallery_seeds_to_indices = { gallery_seed : index for ( index, gallery_seed ) in enumerate( self._gallery_seeds ) }
            
        
    
    def _SetStatusDirty( self ):
        
        self._status_dirty = True
        
    
    def AddGallerySeeds( self, gallery_seeds, parent_gallery_seed: typing.Optional[ GallerySeed ] = None ) -> int:
        
        if len( gallery_seeds ) == 0:
            
            return 0
            
        
        seen_urls = set()
        new_gallery_seeds = []
        
        with self._lock:
            
            for gallery_seed in gallery_seeds:
                
                if gallery_seed.url in seen_urls:
                    
                    continue
                    
                
                if gallery_seed in self._gallery_seeds_to_indices:
                    
                    continue
                    
                
                new_gallery_seeds.append( gallery_seed )
                
                seen_urls.add( gallery_seed.url )
                
            
            if len( new_gallery_seeds ) == 0:
                
                return 0
                
            
            if parent_gallery_seed is None or parent_gallery_seed not in self._gallery_seeds:
                
                insertion_index = len( self._gallery_seeds )
                
            else:
                
                insertion_index = self._gallery_seeds.index( parent_gallery_seed ) + 1
                
            
            original_insertion_index = insertion_index
            
            for gallery_seed in new_gallery_seeds:
                
                self._gallery_seeds.insert( insertion_index, gallery_seed )
                
                insertion_index += 1
                
            
            self._gallery_seeds_to_indices = { gallery_seed : index for ( index, gallery_seed ) in enumerate( self._gallery_seeds ) }
            
            self._SetStatusDirty()
            
            updated_gallery_seeds = self._gallery_seeds[ original_insertion_index : ]
            
        
        self.NotifyGallerySeedsUpdated( updated_gallery_seeds )
        
        return len( new_gallery_seeds )
        
    
    def AdvanceGallerySeed( self, gallery_seed ):
        
        updated_gallery_seeds = []
        
        with self._lock:
            
            if gallery_seed in self._gallery_seeds_to_indices:
                
                index = self._gallery_seeds_to_indices[ gallery_seed ]
                
                if index > 0:
                    
                    swapped_gallery_seed = self._gallery_seeds[ index - 1 ]
                    
                    self._gallery_seeds.remove( gallery_seed )
                    
                    self._gallery_seeds.insert( index - 1, gallery_seed )
                    
                    self._gallery_seeds_to_indices[ gallery_seed ] = index - 1
                    self._gallery_seeds_to_indices[ swapped_gallery_seed ] = index
                    
                    updated_gallery_seeds = ( gallery_seed, swapped_gallery_seed )
                    
            
        
        self.NotifyGallerySeedsUpdated( updated_gallery_seeds )
        
    
    def CanCompact( self, compact_before_this_source_time ):
        
        with self._lock:
            
            if len( self._gallery_seeds ) <= self.COMPACT_NUMBER:
                
                return False
                
            
            for gallery_seed in self._gallery_seeds[:-self.COMPACT_NUMBER]:
                
                if gallery_seed.status == CC.STATUS_UNKNOWN:
                    
                    continue
                    
                
                if gallery_seed.created < compact_before_this_source_time:
                    
                    return True
                    
                
            
        
        return False
        
    
    def CanRestartFailedSearch( self ):
        
        with self._lock:
            
            if len( self._gallery_seeds ) == 0:
                
                return False
                
            
            last_gallery_seed = self._gallery_seeds[-1]
            
            if last_gallery_seed.status == CC.STATUS_ERROR:
                
                return True
                
            
        
    
    def Compact( self, compact_before_this_source_time ):
        
        with self._lock:
            
            if len( self._gallery_seeds ) <= self.COMPACT_NUMBER:
                
                return
                
            
            new_gallery_seeds = HydrusSerialisable.SerialisableList()
            
            for gallery_seed in self._gallery_seeds[:-self.COMPACT_NUMBER]:
                
                still_to_do = gallery_seed.status == CC.STATUS_UNKNOWN
                still_relevant = gallery_seed.created > compact_before_this_source_time
                
                if still_to_do or still_relevant:
                    
                    new_gallery_seeds.append( gallery_seed )
                    
                
            
            new_gallery_seeds.extend( self._gallery_seeds[-self.COMPACT_NUMBER:] )
            
            self._gallery_seeds = new_gallery_seeds
            self._gallery_seeds_to_indices = { gallery_seed : index for ( index, gallery_seed ) in enumerate( self._gallery_seeds ) }
            
            self._SetStatusDirty()
            
        
    
    def DelayGallerySeed( self, gallery_seed ):
        
        updated_gallery_seeds = []
        
        with self._lock:
            
            if gallery_seed in self._gallery_seeds_to_indices:
                
                index = self._gallery_seeds_to_indices[ gallery_seed ]
                
                if index < len( self._gallery_seeds ) - 1:
                    
                    swapped_gallery_seed = self._gallery_seeds[ index + 1 ]
                    
                    self._gallery_seeds.remove( gallery_seed )
                    
                    self._gallery_seeds.insert( index + 1, gallery_seed )
                    
                    self._gallery_seeds_to_indices[ swapped_gallery_seed ] = index
                    self._gallery_seeds_to_indices[ gallery_seed ] = index + 1
                    
                    updated_gallery_seeds = ( swapped_gallery_seed, gallery_seed )
                    
                
            
        
        self.NotifyGallerySeedsUpdated( updated_gallery_seeds )
        
    
    def GetExampleGallerySeed( self ):
        
        with self._lock:
            
            if len( self._gallery_seeds ) == 0:
                
                return None
                
            else:
                
                example_seed = self._GetNextGallerySeed( CC.STATUS_UNKNOWN )
                
                if example_seed is None:
                    
                    example_seed = random.choice( self._gallery_seeds[-10:] )
                    
                
                return example_seed
                
            
        
    
    def GetAPIInfoDict( self, simple ):
        
        with self._lock:
            
            d = {}
            
            if self._status_dirty:
                
                self._GenerateStatus()
                
            
            ( status, ( total_processed, total ) ) = self._status_cache
            
            d[ 'status' ] = status
            d[ 'total_processed' ] = total_processed
            d[ 'total_to_process' ] = total
            
            if not simple:
                
                d[ 'log_items' ] = [ gallery_seed.GetAPIInfoDict( simple ) for gallery_seed in self._gallery_seeds ]
                
            
            return d
            
        
    
    def GetGallerySeedLogKey( self ):
        
        return self._gallery_seed_log_key
        
    
    def GetGallerySeedCount( self, status = None ):
        
        result = 0
        
        with self._lock:
            
            if status is None:
                
                result = len( self._gallery_seeds )
                
            else:
                
                for gallery_seed in self._gallery_seeds:
                    
                    if gallery_seed.status == status:
                        
                        result += 1
                        
                    
                
            
        
        return result
        
    
    def GetGallerySeeds( self, status = None ):
        
        with self._lock:
            
            return self._GetGallerySeeds( status )
            
        
    
    def GetGallerySeedIndex( self, gallery_seed ):
        
        with self._lock:
            
            return self._gallery_seeds_to_indices[ gallery_seed ]
            
        
    
    def GetNextGallerySeed( self, status ):
        
        with self._lock:
            
            return self._GetNextGallerySeed( status )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            if self._status_dirty:
                
                self._GenerateStatus()
                
            
            return self._status_cache
            
        
    
    def GetStatusesToCounts( self ):
        
        with self._lock:
            
            return self._GetStatusesToCounts()
            
        
    
    def HasGallerySeed( self, gallery_seed ):
        
        with self._lock:
            
            return gallery_seed in self._gallery_seeds_to_indices
            
        
    
    def HasGalleryURL( self, url ):
        
        search_gallery_seed = GallerySeed( url )
        
        search_url = search_gallery_seed.url
        
        return search_url in ( gallery_seed.url for gallery_seed in self._gallery_seeds )
        
    
    def NotifyGallerySeedsUpdated( self, gallery_seeds ):
        
        if len( gallery_seeds ) == 0:
            
            return
            
        
        with self._lock:
            
            self._SetStatusDirty()
            
        
        CG.client_controller.pub( 'gallery_seed_log_gallery_seeds_updated', self._gallery_seed_log_key, gallery_seeds )
        
    
    def RemoveGallerySeeds( self, gallery_seeds_to_delete ):
        
        with self._lock:
            
            gallery_seeds_to_delete = { gallery_seed for gallery_seed in gallery_seeds_to_delete if gallery_seed in self._gallery_seeds_to_indices }
            
            if len( gallery_seeds_to_delete ) == 0:
                
                return
                
            
            earliest_affected_index = min( ( self._gallery_seeds_to_indices[ gallery_seed ] for gallery_seed in gallery_seeds_to_delete ) )
            
            self._gallery_seeds = HydrusSerialisable.SerialisableList( [ gallery_seed for gallery_seed in self._gallery_seeds if gallery_seed not in gallery_seeds_to_delete ] )
            
            self._gallery_seeds_to_indices = { gallery_seed : index for ( index, gallery_seed ) in enumerate( self._gallery_seeds ) }
            
            self._SetStatusDirty()
            
            index_shuffled_gallery_seeds = self._gallery_seeds[ earliest_affected_index : ]
            
        
        updated_gallery_seeds = gallery_seeds_to_delete.union( index_shuffled_gallery_seeds )
        
        self.NotifyGallerySeedsUpdated( updated_gallery_seeds )
        
    
    def RemoveGallerySeedsByStatus( self, statuses_to_remove ):
        
        with self._lock:
            
            gallery_seeds_to_delete = [ gallery_seed for gallery_seed in self._gallery_seeds if gallery_seed.status in statuses_to_remove ]
            
        
        self.RemoveGallerySeeds( gallery_seeds_to_delete )
        
    
    def RemoveAllButUnknownGallerySeeds( self ):
        
        with self._lock:
            
            gallery_seeds_to_delete = [ gallery_seed for gallery_seed in self._gallery_seeds if gallery_seed.status != CC.STATUS_UNKNOWN ]
            
        
        self.RemoveGallerySeeds( gallery_seeds_to_delete )
        
    
    def RestartFailedSearch( self ):
        
        with self._lock:
            
            if len( self._gallery_seeds ) == 0:
                
                return
                
            
            last_gallery_seed = self._gallery_seeds[-1]
            
            if last_gallery_seed.status != CC.STATUS_ERROR:
                
                return
                
            
            can_generate_more_pages = True
            
            new_gallery_seeds = ( last_gallery_seed.GenerateRestartedDuplicate( can_generate_more_pages ), )
            
        
        self.AddGallerySeeds( new_gallery_seeds )
        self.NotifyGallerySeedsUpdated( new_gallery_seeds )
        
    
    def RetryFailed( self ):
        
        with self._lock:
            
            failed_gallery_seeds = self._GetGallerySeeds( CC.STATUS_ERROR )
            
            for gallery_seed in failed_gallery_seeds:
                
                gallery_seed.SetStatus( CC.STATUS_UNKNOWN )
                
            
        
        self.NotifyGallerySeedsUpdated( failed_gallery_seeds )
        
    
    def WorkToDo( self ):
        
        with self._lock:
            
            if self._status_dirty:
                
                self._GenerateStatus()
                
            
            ( status, ( total_processed, total ) ) = self._status_cache
            
            return total_processed < total
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_SEED_LOG ] = GallerySeedLog
