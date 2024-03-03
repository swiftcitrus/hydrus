import collections
import random
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDBBase
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTime

from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices

class ClientDBSimilarFiles( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices, modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage ):
        
        self.modules_services = modules_services
        self.modules_files_storage = modules_files_storage
        
        ClientDBModule.ClientDBModule.__init__( self, 'client similar files', cursor )
        
        self._perceptual_hash_id_to_vp_tree_node_cache = {}
        self._non_vp_treed_perceptual_hash_ids = set()
        self._root_node_perceptual_hash_id = None
        
    
    def _AddLeaf( self, perceptual_hash_id, perceptual_hash ):
        
        result = self._Execute( 'SELECT phash_id FROM shape_vptree WHERE parent_id IS NULL;' ).fetchone()
        
        parent_id = None
        
        if result is not None:
            
            ( root_node_perceptual_hash_id, ) = result
            
            ancestors_we_are_inside = []
            ancestors_we_are_outside = []
            
            an_ancestor_is_unbalanced = False
            
            next_ancestor_id = root_node_perceptual_hash_id
            
            while next_ancestor_id is not None:
                
                ancestor_id = next_ancestor_id
                
                ( ancestor_perceptual_hash, ancestor_radius, ancestor_inner_id, ancestor_inner_population, ancestor_outer_id, ancestor_outer_population ) = self._Execute( 'SELECT phash, radius, inner_id, inner_population, outer_id, outer_population FROM shape_perceptual_hashes NATURAL JOIN shape_vptree WHERE phash_id = ?;', ( ancestor_id, ) ).fetchone()
                
                distance_to_ancestor = HydrusData.Get64BitHammingDistance( perceptual_hash, ancestor_perceptual_hash )
                
                if ancestor_radius is None or distance_to_ancestor <= ancestor_radius:
                    
                    ancestors_we_are_inside.append( ancestor_id )
                    ancestor_inner_population += 1
                    next_ancestor_id = ancestor_inner_id
                    
                    if ancestor_inner_id is None:
                        
                        self._Execute( 'UPDATE shape_vptree SET inner_id = ?, radius = ? WHERE phash_id = ?;', ( perceptual_hash_id, distance_to_ancestor, ancestor_id ) )
                        
                        self._ClearPerceptualHashesFromVPTreeNodeCache( ( ancestor_id, ) )
                        
                        parent_id = ancestor_id
                        
                    
                else:
                    
                    ancestors_we_are_outside.append( ancestor_id )
                    ancestor_outer_population += 1
                    next_ancestor_id = ancestor_outer_id
                    
                    if ancestor_outer_id is None:
                        
                        self._Execute( 'UPDATE shape_vptree SET outer_id = ? WHERE phash_id = ?;', ( perceptual_hash_id, ancestor_id ) )
                        
                        self._ClearPerceptualHashesFromVPTreeNodeCache( ( ancestor_id, ) )
                        
                        parent_id = ancestor_id
                        
                    
                
                if not an_ancestor_is_unbalanced and ancestor_inner_population + ancestor_outer_population > 16:
                    
                    larger = max( ancestor_inner_population, ancestor_outer_population )
                    smaller = min( ancestor_inner_population, ancestor_outer_population )
                    
                    if smaller / larger < 0.5:
                        
                        self._Execute( 'INSERT OR IGNORE INTO shape_maintenance_branch_regen ( phash_id ) VALUES ( ? );', ( ancestor_id, ) )
                        
                        # we only do this for the eldest ancestor, as the eventual rebalancing will affect all children
                        
                        an_ancestor_is_unbalanced = True
                        
                    
                
            
            self._ExecuteMany( 'UPDATE shape_vptree SET inner_population = inner_population + 1 WHERE phash_id = ?;', ( ( ancestor_id, ) for ancestor_id in ancestors_we_are_inside ) )
            self._ExecuteMany( 'UPDATE shape_vptree SET outer_population = outer_population + 1 WHERE phash_id = ?;', ( ( ancestor_id, ) for ancestor_id in ancestors_we_are_outside ) )
            
            self._ClearPerceptualHashesFromVPTreeNodeCache( ancestors_we_are_inside )
            self._ClearPerceptualHashesFromVPTreeNodeCache( ancestors_we_are_outside )
            
        
        radius = None
        inner_id = None
        inner_population = 0
        outer_id = None
        outer_population = 0
        
        self._Execute( 'INSERT OR REPLACE INTO shape_vptree ( phash_id, parent_id, radius, inner_id, inner_population, outer_id, outer_population ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( perceptual_hash_id, parent_id, radius, inner_id, inner_population, outer_id, outer_population ) )
        
        self._ClearPerceptualHashesFromVPTreeNodeCache( ( perceptual_hash_id, ) )
        
    
    def _GenerateBranch( self, job_status, parent_id, perceptual_hash_id, perceptual_hash, children ):
        
        process_queue = collections.deque()
        
        process_queue.append( ( parent_id, perceptual_hash_id, perceptual_hash, children ) )
        
        insert_rows = []
        
        num_done = 0
        num_to_do = len( children ) + 1
        
        all_altered_phash_ids = set()
        
        while len( process_queue ) > 0:
            
            job_status.SetStatusText( 'generating new branch -- ' + HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do ), 2 )
            
            ( parent_id, perceptual_hash_id, perceptual_hash, children ) = process_queue.popleft()
            
            if len( children ) == 0:
                
                inner_id = None
                inner_population = 0
                
                outer_id = None
                outer_population = 0
                
                radius = None
                
            else:
                
                children = sorted( ( ( HydrusData.Get64BitHammingDistance( perceptual_hash, child_perceptual_hash ), child_id, child_perceptual_hash ) for ( child_id, child_perceptual_hash ) in children ) )
                
                median_index = len( children ) // 2
                
                median_radius = children[ median_index ][0]
                
                inner_children = [ ( child_id, child_perceptual_hash ) for ( distance, child_id, child_perceptual_hash ) in children if distance < median_radius ]
                radius_children = [ ( child_id, child_perceptual_hash ) for ( distance, child_id, child_perceptual_hash ) in children if distance == median_radius ]
                outer_children = [ ( child_id, child_perceptual_hash ) for ( distance, child_id, child_perceptual_hash ) in children if distance > median_radius ]
                
                if len( inner_children ) <= len( outer_children ):
                    
                    radius = median_radius
                    
                    inner_children.extend( radius_children )
                    
                else:
                    
                    radius = median_radius - 1
                    
                    outer_children.extend( radius_children )
                    
                
                inner_population = len( inner_children )
                outer_population = len( outer_children )
                
                ( inner_id, inner_perceptual_hash ) = self._PopBestRootNode( inner_children ) #HydrusData.MedianPop( inner_children )
                
                if len( outer_children ) == 0:
                    
                    outer_id = None
                    
                else:
                    
                    ( outer_id, outer_perceptual_hash ) = self._PopBestRootNode( outer_children ) #HydrusData.MedianPop( outer_children )
                    
                
            
            insert_rows.append( ( perceptual_hash_id, parent_id, radius, inner_id, inner_population, outer_id, outer_population ) )
            
            all_altered_phash_ids.add( perceptual_hash_id )
            
            if inner_id is not None:
                
                process_queue.append( ( perceptual_hash_id, inner_id, inner_perceptual_hash, inner_children ) )
                
            
            if outer_id is not None:
                
                process_queue.append( ( perceptual_hash_id, outer_id, outer_perceptual_hash, outer_children ) )
                
            
            num_done += 1
            
        
        job_status.SetStatusText( 'branch constructed, now committing', 2 )
        
        self._ExecuteMany( 'INSERT OR REPLACE INTO shape_vptree ( phash_id, parent_id, radius, inner_id, inner_population, outer_id, outer_population ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', insert_rows )
        
        self._ClearPerceptualHashesFromVPTreeNodeCache( all_altered_phash_ids )
        
    
    def _GetHashIdsWithPixelHashId( self, pixel_hash_id: int ) -> typing.Set[ int ]:
        
        pixel_dupe_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM pixel_hash_map WHERE pixel_hash_id = ?;', ( pixel_hash_id, ) ) )
        
        return pixel_dupe_hash_ids
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'external_master.shape_perceptual_hash_map' ] = [
            ( [ 'hash_id' ], False, 451 )
        ]
        
        index_generation_dict[ 'main.shape_vptree' ] = [
            ( [ 'parent_id' ], False, 536 )
        ]
        
        index_generation_dict[ 'main.pixel_hash_map' ] = [
            ( [ 'pixel_hash_id' ], False, 465 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'external_master.shape_perceptual_hashes' : ( 'CREATE TABLE IF NOT EXISTS {} ( phash_id INTEGER PRIMARY KEY, phash BLOB_BYTES UNIQUE );', 451 ),
            'external_master.shape_perceptual_hash_map' : ( 'CREATE TABLE IF NOT EXISTS {} ( phash_id INTEGER, hash_id INTEGER, PRIMARY KEY ( phash_id, hash_id ) );', 451 ),
            'main.shape_vptree' : ( 'CREATE TABLE IF NOT EXISTS {} ( phash_id INTEGER PRIMARY KEY, parent_id INTEGER, radius INTEGER, inner_id INTEGER, inner_population INTEGER, outer_id INTEGER, outer_population INTEGER );', 536 ),
            'main.shape_maintenance_branch_regen' : ( 'CREATE TABLE IF NOT EXISTS {} ( phash_id INTEGER PRIMARY KEY );', 536 ),
            'main.shape_search_cache' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, searched_distance INTEGER );', 451 ),
            'main.pixel_hash_map' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER, pixel_hash_id INTEGER, PRIMARY KEY ( hash_id, pixel_hash_id ) );', 465 )
        }
        
    
    def _GetPerceptualHashes( self, perceptual_hash_ids: typing.Collection[ int ] ) -> typing.Set[ bytes ]:
        
        with self._MakeTemporaryIntegerTable( perceptual_hash_ids, 'phash_id' ) as temp_table_name:
            
            perceptual_hashes = self._STS( self._Execute( f'SELECT phash FROM shape_perceptual_hashes NATURAL JOIN {temp_table_name};' ) )
            
        
        return perceptual_hashes
        
    
    def _GetPerceptualHashId( self, perceptual_hash, do_not_create = False ):
        
        result = self._Execute( 'SELECT phash_id FROM shape_perceptual_hashes WHERE phash = ?;', ( sqlite3.Binary( perceptual_hash ), ) ).fetchone()
        
        if result is None:
            
            if do_not_create:
                
                return None
                
            
            self._Execute( 'INSERT INTO shape_perceptual_hashes ( phash ) VALUES ( ? );', ( sqlite3.Binary( perceptual_hash ), ) )
            
            perceptual_hash_id = self._GetLastRowId()
            
            self._AddLeaf( perceptual_hash_id, perceptual_hash )
            
        else:
            
            ( perceptual_hash_id, ) = result
            
        
        return perceptual_hash_id
        
    
    def _GetPerceptualHashIdsFromHashId( self, hash_id: int ) -> typing.Set[ int ]:
        
        perceptual_hash_ids = self._STS( self._Execute( 'SELECT phash_id FROM shape_perceptual_hash_map WHERE hash_id = ?;', ( hash_id, ) ) )
        
        return perceptual_hash_ids
        
    
    def _GetPixelHashId( self, hash_id: int ) -> typing.Optional[ int ]:
        
        result = self._Execute( 'SELECT pixel_hash_id FROM pixel_hash_map WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None:
            
            return None
            
        else:
            
            ( pixel_hash_id, ) = result
            
            return pixel_hash_id
            
        
    
    def _PopBestRootNode( self, node_rows ):
        
        if len( node_rows ) == 1:
            
            root_row = node_rows.pop()
            
            return root_row
            
        
        MAX_VIEWPOINTS = 256
        MAX_SAMPLE = 64
        
        if len( node_rows ) > MAX_VIEWPOINTS:
            
            viewpoints = random.sample( node_rows, MAX_VIEWPOINTS )
            
        else:
            
            viewpoints = node_rows
            
        
        if len( node_rows ) > MAX_SAMPLE:
            
            sample = random.sample( node_rows, MAX_SAMPLE )
            
        else:
            
            sample = node_rows
            
        
        final_scores = []
        
        for ( v_id, v_perceptual_hash ) in viewpoints:
            
            views = sorted( ( HydrusData.Get64BitHammingDistance( v_perceptual_hash, s_perceptual_hash ) for ( s_id, s_perceptual_hash ) in sample if v_id != s_id ) )
            
            # let's figure out the ratio of left_children to right_children, preferring 1:1, and convert it to a discrete integer score
            
            median_index = len( views ) // 2
            
            radius = views[ median_index ]
            
            num_left = len( [ 1 for view in views if view < radius ] )
            num_radius = len( [ 1 for view in views if view == radius ] )
            num_right = len( [ 1 for view in views if view > radius ] )
            
            if num_left <= num_right:
                
                num_left += num_radius
                
            else:
                
                num_right += num_radius
                
            
            smaller = min( num_left, num_right )
            larger = max( num_left, num_right )
            
            ratio = smaller / larger
            
            ratio_score = int( ratio * MAX_SAMPLE / 2 )
            
            # now let's calc the standard deviation--larger sd tends to mean less sphere overlap when searching
            
            mean_view = sum( views ) / len( views )
            squared_diffs = [ ( view - mean_view  ) ** 2 for view in views ]
            sd = ( sum( squared_diffs ) / len( squared_diffs ) ) ** 0.5
            
            final_scores.append( ( ratio_score, sd, v_id ) )
            
        
        final_scores.sort()
        
        # we now have a list like [ ( 11, 4.0, [id] ), ( 15, 3.7, [id] ), ( 15, 4.3, [id] ) ]
        
        ( ratio_gumpf, sd_gumpf, root_id ) = final_scores.pop()
        
        for ( i, ( v_id, v_perceptual_hash ) ) in enumerate( node_rows ):
            
            if v_id == root_id:
                
                root_row = node_rows.pop( i )
                
                return root_row
                
            
        
    
    def _RegenerateBranch( self, job_status, perceptual_hash_id ):
        
        job_status.SetStatusText( 'reviewing existing branch', 2 )
        
        # grab everything in the branch
        
        ( parent_id, ) = self._Execute( 'SELECT parent_id FROM shape_vptree WHERE phash_id = ?;', ( perceptual_hash_id, ) ).fetchone()
        
        if parent_id is None:
            
            # this is the root node! we can't rebalance since there is no parent to spread across!
            
            self._Execute( 'DELETE FROM shape_maintenance_branch_regen WHERE phash_id = ?;', ( perceptual_hash_id, ) )
            
            return
            
        
        cte_table_name = 'branch ( branch_phash_id )'
        initial_select = 'SELECT ?'
        recursive_select = 'SELECT phash_id FROM shape_vptree, branch ON parent_id = branch_phash_id'
        query_on_cte_table_name = 'SELECT branch_phash_id, phash FROM branch, shape_perceptual_hashes ON phash_id = branch_phash_id'
        
        # use UNION (large memory, set), not UNION ALL (small memory, inifinite loop on damaged cyclic graph causing 200GB journal file and disk full error, jesus)
        query = 'WITH RECURSIVE {} AS ( {} UNION {} ) {};'.format( cte_table_name, initial_select, recursive_select, query_on_cte_table_name )
        
        unbalanced_nodes = self._Execute( query, ( perceptual_hash_id, ) ).fetchall()
        
        # removal of old branch, maintenance schedule, and orphan perceptual_hashes
        
        job_status.SetStatusText( HydrusData.ToHumanInt( len( unbalanced_nodes ) ) + ' leaves found--now clearing out old branch', 2 )
        
        unbalanced_perceptual_hash_ids = { p_id for ( p_id, p_h ) in unbalanced_nodes }
        
        self._ExecuteMany( 'DELETE FROM shape_vptree WHERE phash_id = ?;', ( ( p_id, ) for p_id in unbalanced_perceptual_hash_ids ) )
        
        self._ClearPerceptualHashesFromVPTreeNodeCache( unbalanced_perceptual_hash_ids )
        
        self._ExecuteMany( 'DELETE FROM shape_maintenance_branch_regen WHERE phash_id = ?;', ( ( p_id, ) for p_id in unbalanced_perceptual_hash_ids ) )
        
        with self._MakeTemporaryIntegerTable( unbalanced_perceptual_hash_ids, 'phash_id' ) as temp_perceptual_hash_ids_table_name:
            
            useful_perceptual_hash_ids = self._STS( self._Execute( 'SELECT phash_id FROM {} CROSS JOIN shape_perceptual_hash_map USING ( phash_id );'.format( temp_perceptual_hash_ids_table_name ) ) )
            
        
        orphan_perceptual_hash_ids = unbalanced_perceptual_hash_ids.difference( useful_perceptual_hash_ids )
        
        self._ExecuteMany( 'DELETE FROM shape_perceptual_hashes WHERE phash_id = ?;', ( ( p_id, ) for p_id in orphan_perceptual_hash_ids ) )
        
        useful_nodes = [ row for row in unbalanced_nodes if row[0] in useful_perceptual_hash_ids ]
        
        useful_population = len( useful_nodes )
        
        # now create the new branch, starting by choosing a new root and updating the parent's left/right reference to that
        
        if useful_population > 0:
            
            ( new_perceptual_hash_id, new_perceptual_hash ) = self._PopBestRootNode( useful_nodes )
            
        else:
            
            new_perceptual_hash_id = None
            new_perceptual_hash = None
            
        
        result = self._Execute( 'SELECT inner_id FROM shape_vptree WHERE phash_id = ?;', ( parent_id, ) ).fetchone()
        
        if result is None:
            
            # expected parent is not in the tree!
            # somehow some stuff got borked
            
            self._Execute( 'DELETE FROM shape_maintenance_branch_regen;' )
            
            HydrusData.ShowText( 'Your similar files search tree seemed to be damaged. Please regenerate it under the _database_ menu!' )
            
            return
            
        
        ( parent_inner_id, ) = result
        
        if parent_inner_id == perceptual_hash_id:
            
            query = 'UPDATE shape_vptree SET inner_id = ?, inner_population = ? WHERE phash_id = ?;'
            
        else:
            
            query = 'UPDATE shape_vptree SET outer_id = ?, outer_population = ? WHERE phash_id = ?;'
            
        
        self._Execute( query, ( new_perceptual_hash_id, useful_population, parent_id ) )
        
        self._ClearPerceptualHashesFromVPTreeNodeCache( ( parent_id, ) )
        
        if useful_population > 0:
            
            self._GenerateBranch( job_status, parent_id, new_perceptual_hash_id, new_perceptual_hash, useful_nodes )
            
        
    
    def _ClearPerceptualHashesFromVPTreeNodeCache( self, perceptual_hash_ids: typing.Collection[ int ] ):
        
        for perceptual_hash_id in perceptual_hash_ids:
            
            if perceptual_hash_id in self._perceptual_hash_id_to_vp_tree_node_cache:
                
                del self._perceptual_hash_id_to_vp_tree_node_cache[ perceptual_hash_id ]
                
            
            self._non_vp_treed_perceptual_hash_ids.discard( perceptual_hash_id )
            
            if self._root_node_perceptual_hash_id == perceptual_hash_id:
                
                self._root_node_perceptual_hash_id = None
                
            
        
    
    def _RepairRepopulateTables( self, repopulate_table_names, cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper ):
        
        if 'main.shape_vptree' in repopulate_table_names or 'main.shape_maintenance_branch_regen' in repopulate_table_names:
            
            self.RegenerateTree()
            
        
    
    def _TryToPopulatePerceptualHashToVPTreeNodeCache( self, perceptual_hash_ids: typing.Collection[ int ] ):
        
        if len( self._perceptual_hash_id_to_vp_tree_node_cache ) > 1000000:
            
            if not isinstance( perceptual_hash_ids, set ):
                
                perceptual_hash_ids = set( perceptual_hash_ids )
                
            
            self._perceptual_hash_id_to_vp_tree_node_cache = { perceptual_hash_id : phash for ( perceptual_hash_id, phash ) in self._perceptual_hash_id_to_vp_tree_node_cache.items() if perceptual_hash_id in perceptual_hash_ids }
            
        
        uncached_perceptual_hash_ids = { perceptual_hash_id for perceptual_hash_id in perceptual_hash_ids if perceptual_hash_id not in self._perceptual_hash_id_to_vp_tree_node_cache and perceptual_hash_id not in self._non_vp_treed_perceptual_hash_ids }
        
        if len( uncached_perceptual_hash_ids ) > 0:
            
            if len( uncached_perceptual_hash_ids ) == 1:
                
                ( uncached_perceptual_hash_id, ) = uncached_perceptual_hash_ids
                
                rows = self._Execute( 'SELECT phash_id, phash, radius, inner_id, outer_id FROM shape_perceptual_hashes CROSS JOIN shape_vptree USING ( phash_id ) WHERE phash_id = ?;', ( uncached_perceptual_hash_id, ) ).fetchall()
                
            else:
                
                with self._MakeTemporaryIntegerTable( uncached_perceptual_hash_ids, 'phash_id' ) as temp_table_name:
                    
                    # temp perceptual_hash_ids to actual perceptual_hashes and tree info
                    rows = self._Execute( 'SELECT phash_id, phash, radius, inner_id, outer_id FROM {} CROSS JOIN shape_perceptual_hashes USING ( phash_id ) CROSS JOIN shape_vptree USING ( phash_id );'.format( temp_table_name ) ).fetchall()
                    
                
            
            uncached_perceptual_hash_ids_to_vp_tree_nodes = { perceptual_hash_id : ( phash, radius, inner_id, outer_id ) for ( perceptual_hash_id, phash, radius, inner_id, outer_id ) in rows }
            
            if len( uncached_perceptual_hash_ids_to_vp_tree_nodes ) < len( uncached_perceptual_hash_ids ):
                
                for perceptual_hash_id in uncached_perceptual_hash_ids:
                    
                    if perceptual_hash_id not in uncached_perceptual_hash_ids_to_vp_tree_nodes:
                        
                        self._non_vp_treed_perceptual_hash_ids.add( perceptual_hash_id )
                        
                    
                
            
            self._perceptual_hash_id_to_vp_tree_node_cache.update( uncached_perceptual_hash_ids_to_vp_tree_nodes )
            
        
    
    def AssociatePerceptualHashes( self, hash_id, perceptual_hashes ):
        
        perceptual_hash_ids = set()
        
        for perceptual_hash in perceptual_hashes:
            
            perceptual_hash_id = self._GetPerceptualHashId( perceptual_hash )
            
            perceptual_hash_ids.add( perceptual_hash_id )
            
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO shape_perceptual_hash_map ( phash_id, hash_id ) VALUES ( ?, ? );', ( ( perceptual_hash_id, hash_id ) for perceptual_hash_id in perceptual_hash_ids ) )
        
        if self._GetRowCount() > 0:
            
            self._Execute( 'REPLACE INTO shape_search_cache ( hash_id, searched_distance ) VALUES ( ?, ? );', ( hash_id, None ) )
            
        
        return perceptual_hash_ids
        
    
    def ClearPixelHash( self, hash_id: int ):
        
        self._Execute( 'DELETE FROM pixel_hash_map WHERE hash_id = ?;', ( hash_id, ) )
        
    
    def DisassociatePerceptualHashes( self, hash_id, perceptual_hash_ids ):
        
        self._ExecuteMany( 'DELETE FROM shape_perceptual_hash_map WHERE phash_id = ? AND hash_id = ?;', ( ( perceptual_hash_id, hash_id ) for perceptual_hash_id in perceptual_hash_ids ) )
        
        useful_perceptual_hash_ids = { perceptual_hash for ( perceptual_hash, ) in self._Execute( 'SELECT phash_id FROM shape_perceptual_hash_map WHERE phash_id IN ' + HydrusData.SplayListForDB( perceptual_hash_ids ) + ';' ) }
        
        useless_perceptual_hash_ids = perceptual_hash_ids.difference( useful_perceptual_hash_ids )
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO shape_maintenance_branch_regen ( phash_id ) VALUES ( ? );', ( ( perceptual_hash_id, ) for perceptual_hash_id in useless_perceptual_hash_ids ) )
        
    
    def FileIsInSystem( self, hash_id ):
        
        result = self._Execute( 'SELECT 1 FROM shape_search_cache WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        return result is not None
        
    
    def GetMaintenanceStatus( self ):
        
        searched_distances_to_count = collections.Counter( dict( self._Execute( 'SELECT searched_distance, COUNT( * ) FROM shape_search_cache GROUP BY searched_distance;' ) ) )
        
        return searched_distances_to_count
        
    
    def GetHashIdsToPixelHashes( self, hash_ids_table_name: str ):
        
        return dict( self._Execute( f'SELECT {hash_ids_table_name}.hash_id, hash FROM {hash_ids_table_name} CROSS JOIN pixel_hash_map ON ( {hash_ids_table_name}.hash_id = pixel_hash_map.hash_id ) CROSS JOIN hashes ON ( pixel_hash_map.pixel_hash_id = hashes.hash_id );' ) )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            return [
                ( 'shape_perceptual_hash_map', 'hash_id' ),
                ( 'shape_search_cache', 'hash_id' ),
                ( 'pixel_hash_map', 'hash_id' ),
                ( 'pixel_hash_map', 'pixel_hash_id' )
            ]
            
        
        return []
        
    
    def MaintainTree( self, maintenance_mode = HC.MAINTENANCE_FORCED, job_status = None, stop_time = None ):
        
        time_started = HydrusTime.GetNow()
        pub_job_status = False
        job_status_pubbed = False
        
        if job_status is None:
            
            job_status = ClientThreading.JobStatus( maintenance_mode = maintenance_mode, cancellable = True )
            
            pub_job_status = True
            
        
        try:
            
            job_status.SetStatusTitle( 'similar files metadata maintenance' )
            
            rebalance_perceptual_hash_ids = self._STL( self._Execute( 'SELECT phash_id FROM shape_maintenance_branch_regen;' ) )
            
            num_to_do = len( rebalance_perceptual_hash_ids )
            
            while len( rebalance_perceptual_hash_ids ) > 0:
                
                if pub_job_status and not job_status_pubbed and HydrusTime.TimeHasPassed( time_started + 5 ):
                    
                    CG.client_controller.pub( 'modal_message', job_status )
                    
                    job_status_pubbed = True
                    
                
                ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                
                should_stop = CG.client_controller.ShouldStopThisWork( maintenance_mode, stop_time = stop_time )
                
                if should_quit or should_stop:
                    
                    return
                    
                
                num_done = num_to_do - len( rebalance_perceptual_hash_ids )
                
                text = 'rebalancing similar file metadata - ' + HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do )
                
                CG.client_controller.frame_splash_status.SetSubtext( text )
                job_status.SetStatusText( text )
                job_status.SetVariable( 'popup_gauge_1', ( num_done, num_to_do ) )
                
                with self._MakeTemporaryIntegerTable( rebalance_perceptual_hash_ids, 'phash_id' ) as temp_table_name:
                    
                    # temp perceptual hashes to tree
                    result = self._Execute( 'SELECT phash_id FROM {} CROSS JOIN shape_vptree USING ( phash_id ) ORDER BY inner_population + outer_population DESC;'.format( temp_table_name ) ).fetchone()
                    
                    if result is None:
                        
                        self._Execute( 'DELETE FROM shape_maintenance_branch_regen;' )
                        
                        return
                        
                    else:
                        
                        ( biggest_perceptual_hash_id, ) = result
                        
                    
                
                self._RegenerateBranch( job_status, biggest_perceptual_hash_id )
                
                rebalance_perceptual_hash_ids = self._STL( self._Execute( 'SELECT phash_id FROM shape_maintenance_branch_regen;' ) )
                
            
        finally:
            
            job_status.SetStatusText( 'done!' )
            job_status.DeleteVariable( 'popup_gauge_1' )
            job_status.DeleteStatusText( 2 ) # used in the regenbranch call
            
            job_status.FinishAndDismiss( 5 )
            
        
    
    def MaintenanceDue( self ):
        
        new_options = CG.client_controller.new_options
        
        if new_options.GetBoolean( 'maintain_similar_files_duplicate_pairs_during_idle' ):
            
            search_distance = new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' )
            
            ( count, ) = self._Execute( 'SELECT COUNT( * ) FROM ( SELECT 1 FROM shape_search_cache WHERE searched_distance IS NULL or searched_distance < ? LIMIT 100 );', ( search_distance, ) ).fetchone()
            
            if count >= 100:
                
                return True
                
            
        
        return False
        
    
    def RegenerateTree( self ):
        
        job_status = ClientThreading.JobStatus()
        
        try:
            
            job_status.SetStatusTitle( 'regenerating similar file search data' )
            
            CG.client_controller.pub( 'modal_message', job_status )
            
            job_status.SetStatusText( 'purging search info of orphans' )
            
            ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = ClientDBFilesStorage.GenerateFilesTableNames( self.modules_services.combined_local_file_service_id )
            
            self._Execute( 'DELETE FROM shape_perceptual_hash_map WHERE hash_id NOT IN ( SELECT hash_id FROM {} );'.format( current_files_table_name ) )
            
            job_status.SetStatusText( 'gathering all leaves' )
            
            self._Execute( 'DELETE FROM shape_vptree;' )
            
            self._perceptual_hash_id_to_vp_tree_node_cache = {}
            self._non_vp_treed_perceptual_hash_ids = set()
            self._root_node_perceptual_hash_id = None
            
            all_nodes = self._Execute( 'SELECT phash_id, phash FROM shape_perceptual_hashes;' ).fetchall()
            
            job_status.SetStatusText( HydrusData.ToHumanInt( len( all_nodes ) ) + ' leaves found, now regenerating' )
            
            ( root_id, root_perceptual_hash ) = self._PopBestRootNode( all_nodes ) #HydrusData.RandomPop( all_nodes )
            
            self._GenerateBranch( job_status, None, root_id, root_perceptual_hash, all_nodes )
            
            self._Execute( 'DELETE FROM shape_maintenance_branch_regen;' )
            
        finally:
            
            job_status.SetStatusText( 'done!' )
            job_status.DeleteStatusText( 2 )
            
            job_status.FinishAndDismiss( 5 )
            
        
    
    def ResetSearch( self, hash_ids ):
        
        self._ExecuteMany( 'UPDATE shape_search_cache SET searched_distance = NULL WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in hash_ids ) )
        
    
    def SearchFile( self, hash_id: int, max_hamming_distance: int ) -> typing.List:
        
        similar_hash_ids_and_distances = [ ( hash_id, 0 ) ]
        
        pixel_hash_id = self._GetPixelHashId( hash_id )
        
        if pixel_hash_id is not None:
            
            similar_hash_ids_and_distances.extend( self.SearchPixelHashes( ( pixel_hash_id, ) ) )
            
        
        if max_hamming_distance == 0:
            
            exact_match_hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM shape_perceptual_hash_map WHERE phash_id IN ( SELECT phash_id FROM shape_perceptual_hash_map WHERE hash_id = ? );', ( hash_id, ) ) )
            
            similar_hash_ids_and_distances.extend( [ ( exact_match_hash_id, 0 ) for exact_match_hash_id in exact_match_hash_ids ] )
            
        else:
            
            perceptual_hash_ids = self._GetPerceptualHashIdsFromHashId( hash_id )
            
            perceptual_hashes = self._GetPerceptualHashes( perceptual_hash_ids )
            
            similar_hash_ids_and_distances.extend( self.SearchPerceptualHashes( perceptual_hashes, max_hamming_distance ) )
            
        
        similar_hash_ids_and_distances = HydrusData.DedupeList( similar_hash_ids_and_distances )
        
        return similar_hash_ids_and_distances
        
    
    def SearchPixelHashes( self, search_pixel_hash_ids: typing.Collection[ int ] ):
        
        similar_hash_ids_and_distances = []
        
        for search_pixel_hash_id in search_pixel_hash_ids:
            
            pixel_dupe_hash_ids = self._GetHashIdsWithPixelHashId( search_pixel_hash_id )
            
            similar_hash_ids_and_distances.extend( [ ( pixel_dupe_hash_id, 0 ) for pixel_dupe_hash_id in pixel_dupe_hash_ids ] )
            
        
        similar_hash_ids_and_distances = HydrusData.DedupeList( similar_hash_ids_and_distances )
        
        return similar_hash_ids_and_distances
        
    
    def SearchPerceptualHashes( self, search_perceptual_hashes: typing.Collection[ bytes ], max_hamming_distance: int ) -> typing.List:
        
        similar_hash_ids_and_distances = []
        
        if len( search_perceptual_hashes ) == 0:
            
            return similar_hash_ids_and_distances
            
        
        if max_hamming_distance == 0:
            
            perceptual_hash_ids = set()
            
            for search_perceptual_hash in search_perceptual_hashes:
                
                perceptual_hash_id = self._GetPerceptualHashId( search_perceptual_hash, do_not_create = True )
                
                if perceptual_hash_id is not None:
                    
                    perceptual_hash_ids.add( perceptual_hash_id )
                    
                
            
            if len( perceptual_hash_ids ) > 0:
                
                with self._MakeTemporaryIntegerTable( perceptual_hash_ids, 'phash_id' ) as temp_table_name:
                    
                    similar_hash_ids = self._STL( self._Execute( f'SELECT hash_id FROM shape_perceptual_hash_map NATURAL JOIN {temp_table_name};' ) )
                    
                
                similar_hash_ids_and_distances.extend( [ ( similar_hash_id, 0 ) for similar_hash_id in similar_hash_ids ] )
                
            
        else:
            
            search_radius = max_hamming_distance
            
            if self._root_node_perceptual_hash_id is None:
                
                top_node_result = self._Execute( 'SELECT phash_id FROM shape_vptree WHERE parent_id IS NULL;' ).fetchone()
                
                if top_node_result is None:
                    
                    return similar_hash_ids_and_distances
                    
                
                ( self._root_node_perceptual_hash_id, ) = top_node_result
                
            
            similar_perceptual_hash_ids_to_distances = {}
            
            num_cycles = 0
            total_nodes_searched = 0
            
            for search_perceptual_hash in search_perceptual_hashes:
                
                next_potentials = [ self._root_node_perceptual_hash_id ]
                
                while len( next_potentials ) > 0:
                    
                    current_potentials = next_potentials
                    next_potentials = []
                    
                    num_cycles += 1
                    total_nodes_searched += len( current_potentials )
                    
                    # this is no longer an iterable inside the main node SELECT because it was causing crashes on linux!!
                    # after investigation, it seemed to be SQLite having a problem with part of Get64BitHammingDistance touching perceptual_hashes it presumably was still hanging on to
                    # the crash was in sqlite code, again presumably on subsequent fetch
                    # adding a fake delay in seemed to fix it also. guess it was some memory maintenance buffer/bytes thing
                    # anyway, we now just get the whole lot of results first and then work on the whole lot
                    # UPDATE: we moved to a cache finally, so the iteration danger is less worrying, but leaving the above up anyway
                    
                    self._TryToPopulatePerceptualHashToVPTreeNodeCache( current_potentials )
                    
                    for node_perceptual_hash_id in current_potentials:
                        
                        if node_perceptual_hash_id not in self._perceptual_hash_id_to_vp_tree_node_cache:
                            
                            # something crazy happened, probably a broken tree branch, move on
                            continue
                            
                        
                        ( node_perceptual_hash, node_radius, inner_perceptual_hash_id, outer_perceptual_hash_id ) = self._perceptual_hash_id_to_vp_tree_node_cache[ node_perceptual_hash_id ]
                        
                        # first check the node itself--is it similar?
                        
                        node_hamming_distance = HydrusData.Get64BitHammingDistance( search_perceptual_hash, node_perceptual_hash )
                        
                        if node_hamming_distance <= search_radius:
                            
                            if node_perceptual_hash_id in similar_perceptual_hash_ids_to_distances:
                                
                                current_distance = similar_perceptual_hash_ids_to_distances[ node_perceptual_hash_id ]
                                
                                similar_perceptual_hash_ids_to_distances[ node_perceptual_hash_id ] = min( node_hamming_distance, current_distance )
                                
                            else:
                                
                                similar_perceptual_hash_ids_to_distances[ node_perceptual_hash_id ] = node_hamming_distance
                                
                            
                        
                        # now how about its children--where should we search next?
                        
                        if node_radius is not None:
                            
                            # we have two spheres--node and search--their centers separated by node_hamming_distance
                            # we want to search inside/outside the node_sphere if the search_sphere intersects with those spaces
                            # there are four possibles:
                            # (----N----)-(--S--)    intersects with outer only - distance between N and S > their radii
                            # (----N---(-)-S--)      intersects with both
                            # (----N-(--S-)-)        intersects with both
                            # (---(-N-S--)-)         intersects with inner only - distance between N and S + radius_S does not exceed radius_N
                            
                            if inner_perceptual_hash_id is not None:
                                
                                spheres_disjoint = node_hamming_distance > ( node_radius + search_radius )
                                
                                if not spheres_disjoint: # i.e. they intersect at some point
                                    
                                    next_potentials.append( inner_perceptual_hash_id )
                                    
                                
                            
                            if outer_perceptual_hash_id is not None:
                                
                                search_sphere_subset_of_node_sphere = ( node_hamming_distance + search_radius ) <= node_radius
                                
                                if not search_sphere_subset_of_node_sphere: # i.e. search sphere intersects with non-node sphere space at some point
                                    
                                    next_potentials.append( outer_perceptual_hash_id )
                                    
                                
                            
                        
                    
                
            
            if HG.db_report_mode:
                
                HydrusData.ShowText( 'Similar file search touched {} nodes over {} cycles.'.format( HydrusData.ToHumanInt( total_nodes_searched ), HydrusData.ToHumanInt( num_cycles ) ) )
                
            
            # so, now we have perceptual_hash_ids and distances. let's map that to actual files.
            # files can have multiple perceptual_hashes, and perceptual_hashes can refer to multiple files, so let's make sure we are setting the smallest distance we found
            
            similar_perceptual_hash_ids = list( similar_perceptual_hash_ids_to_distances.keys() )
            
            with self._MakeTemporaryIntegerTable( similar_perceptual_hash_ids, 'phash_id' ) as temp_table_name:
                
                # temp perceptual_hashes to hash map
                similar_perceptual_hash_ids_to_hash_ids = HydrusData.BuildKeyToListDict( self._Execute( 'SELECT phash_id, hash_id FROM {} CROSS JOIN shape_perceptual_hash_map USING ( phash_id );'.format( temp_table_name ) ) )
                
            
            similar_hash_ids_to_distances = {}
            
            for ( perceptual_hash_id, hash_ids ) in similar_perceptual_hash_ids_to_hash_ids.items():
                
                distance = similar_perceptual_hash_ids_to_distances[ perceptual_hash_id ]
                
                for hash_id in hash_ids:
                    
                    if hash_id not in similar_hash_ids_to_distances:
                        
                        similar_hash_ids_to_distances[ hash_id ] = distance
                        
                    else:
                        
                        current_distance = similar_hash_ids_to_distances[ hash_id ]
                        
                        if distance < current_distance:
                            
                            similar_hash_ids_to_distances[ hash_id ] = distance
                            
                        
                    
                
            
            similar_hash_ids_and_distances.extend( similar_hash_ids_to_distances.items() )
            
        
        similar_hash_ids_and_distances = HydrusData.DedupeList( similar_hash_ids_and_distances )
        
        return similar_hash_ids_and_distances
        
    
    def SetPixelHash( self, hash_id: int, pixel_hash_id: int ):
        
        self.ClearPixelHash( hash_id )
        
        self._Execute( 'INSERT INTO pixel_hash_map ( hash_id, pixel_hash_id ) VALUES ( ?, ? );', ( hash_id, pixel_hash_id ) )
        
        ( count, ) = self._Execute( 'SELECT COUNT( * ) FROM pixel_hash_map WHERE pixel_hash_id = ?;', ( pixel_hash_id, ) ).fetchone()
        
        if count > 1:
            
            self._Execute( 'REPLACE INTO shape_search_cache ( hash_id, searched_distance ) VALUES ( ?, ? );', ( hash_id, None ) )
            
        
    
    def SetPerceptualHashes( self, hash_id, perceptual_hashes ):
        
        current_perceptual_hash_ids = self._STS( self._Execute( 'SELECT phash_id FROM shape_perceptual_hash_map WHERE hash_id = ?;', ( hash_id, ) ) )
        
        if len( current_perceptual_hash_ids ) > 0:
            
            self.DisassociatePerceptualHashes( hash_id, current_perceptual_hash_ids )
            
        
        if len( perceptual_hashes ) > 0:
            
            self.AssociatePerceptualHashes( hash_id, perceptual_hashes )
            
        
    
    def StopSearchingFile( self, hash_id ):
        
        perceptual_hash_ids = self._STS( self._Execute( 'SELECT phash_id FROM shape_perceptual_hash_map WHERE hash_id = ?;', ( hash_id, ) ) )
        
        self.DisassociatePerceptualHashes( hash_id, perceptual_hash_ids )
        
        self._Execute( 'DELETE FROM shape_search_cache WHERE hash_id = ?;', ( hash_id, ) )
        
    
