import collections
import typing

import psutil
import sqlite3

from hydrus.core import HydrusData
from hydrus.core import HydrusPaths
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTemp
from hydrus.core import HydrusTime

def CheckHasSpaceForDBTransaction( db_dir, num_bytes ):
    
    space_needed = int( num_bytes * 1.1 )
    
    if HG.no_db_temp_files:
        
        approx_available_memory = psutil.virtual_memory().available * 4 / 5
        
        if approx_available_memory < num_bytes:
            
            raise Exception( 'I believe you need about {} available memory, since you are running in no_db_temp_files mode, but you only seem to have {}.'.format( HydrusData.ToHumanBytes( space_needed ), HydrusData.ToHumanBytes( approx_available_memory ) ) )
            
        
        db_disk_free_space = HydrusPaths.GetFreeSpace( db_dir )
        
        if db_disk_free_space < space_needed:
            
            raise Exception( 'I believe you need about {} on your db\'s disk partition, but you only seem to have {}.'.format( HydrusData.ToHumanBytes( space_needed ), HydrusData.ToHumanBytes( db_disk_free_space ) ) )
            
        
    else:
        
        temp_dir = HydrusTemp.GetCurrentTempDir()
        
        temp_disk_free_space = HydrusPaths.GetFreeSpace( temp_dir )
        
        temp_and_db_on_same_device = HydrusPaths.GetDevice( temp_dir ) == HydrusPaths.GetDevice( db_dir )
        
        if temp_and_db_on_same_device:
            
            space_needed *= 2
            
            if temp_disk_free_space < space_needed:
                
                raise Exception( 'I believe you need about {} on your db\'s disk partition, which I think also holds your temporary path, but you only seem to have {}.'.format( HydrusData.ToHumanBytes( space_needed ), HydrusData.ToHumanBytes( temp_disk_free_space ) ) )
                
            
        else:
            
            if temp_disk_free_space < space_needed:
                
                message = 'I believe you need about {} on your temporary path\'s disk partition, which I think is {}, but you only seem to have {}.'.format( HydrusData.ToHumanBytes( space_needed ), temp_dir, HydrusData.ToHumanBytes( temp_disk_free_space ) )
                
                if HydrusPaths.GetTotalSpace( temp_dir ) <= 4 * 1024 * 1024 * 1024:
                    
                    message += ' I think you might be using a ramdisk! You may want to instead launch hydrus with a different temp dir. Please check the "launch arguments" section of the help.'
                    
                else:
                    
                    message += ' Please note that temporary paths can be complicated, and if you have a ramdisk or OS settings limiting how large it can get, or you simply cannot free space on your system drive, you may want to instead launch hydrus with a different temp directory. Please check the "launch arguments" section of the help.'
                    
                
                raise Exception( message )
                
            
            db_disk_free_space = HydrusPaths.GetFreeSpace( db_dir )
            
            if db_disk_free_space < space_needed:
                
                raise Exception( 'I believe you need about {} on your db\'s disk partition, but you only seem to have {}.'.format( HydrusData.ToHumanBytes( space_needed ), HydrusData.ToHumanBytes( db_disk_free_space ) ) )
                
            
        
    

def ReadFromCancellableCursor( cursor, largest_group_size, cancelled_hook = None ):
    
    if cancelled_hook is None:
        
        return cursor.fetchall()
        
    
    results = []
    
    if cancelled_hook():
        
        return results
        
    
    NUM_TO_GET = 1
    
    group_of_results = cursor.fetchmany( NUM_TO_GET )
    
    while len( group_of_results ) > 0:
        
        results.extend( group_of_results )
        
        if cancelled_hook():
            
            break
            
        
        if NUM_TO_GET < largest_group_size:
            
            NUM_TO_GET *= 2
            
        
        group_of_results = cursor.fetchmany( NUM_TO_GET )
        
    
    return results
    

class TemporaryIntegerTableNameCache( object ):
    
    my_instance = None
    
    def __init__( self ):
        
        TemporaryIntegerTableNameCache.my_instance = self
        
        self._column_names_to_table_names = collections.defaultdict( collections.deque )
        self._column_names_counter = collections.Counter()
        
    
    @staticmethod
    def instance() -> 'TemporaryIntegerTableNameCache':
        
        if TemporaryIntegerTableNameCache.my_instance is None:
            
            raise Exception( 'TemporaryIntegerTableNameCache is not yet initialised!' )
            
        else:
            
            return TemporaryIntegerTableNameCache.my_instance
            
        
    
    def Clear( self ):
        
        self._column_names_to_table_names = collections.defaultdict( collections.deque )
        self._column_names_counter = collections.Counter()
        
    
    def GetName( self, column_name ):
        
        table_names = self._column_names_to_table_names[ column_name ]
        
        initialised = True
        
        if len( table_names ) == 0:
            
            initialised = False
            
            i = self._column_names_counter[ column_name ]
            
            table_name = 'mem.temp_int_{}_{}'.format( column_name, i )
            
            table_names.append( table_name )
            
            self._column_names_counter[ column_name ] += 1
            
        
        table_name = table_names.pop()
        
        return ( initialised, table_name )
        
    
    def ReleaseName( self, column_name, table_name ):
        
        self._column_names_to_table_names[ column_name ].append( table_name )
        
    
class TemporaryIntegerTable( object ):
    
    def __init__( self, cursor: sqlite3.Cursor, integer_iterable, column_name ):
        
        if not isinstance( integer_iterable, set ):
            
            integer_iterable = set( integer_iterable )
            
        
        self._cursor = cursor
        self._integer_iterable = integer_iterable
        self._column_name = column_name
        
        ( self._initialised, self._table_name ) = TemporaryIntegerTableNameCache.instance().GetName( self._column_name )
        
    
    def __enter__( self ):
        
        if not self._initialised:
            
            self._cursor.execute( 'CREATE TABLE IF NOT EXISTS {} ( {} INTEGER PRIMARY KEY );'.format( self._table_name, self._column_name ) )
            
        
        self._cursor.executemany( 'INSERT INTO {} ( {} ) VALUES ( ? );'.format( self._table_name, self._column_name ), ( ( i, ) for i in self._integer_iterable ) )
        
        return self._table_name
        
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        self._cursor.execute( 'DELETE FROM {};'.format( self._table_name ) )
        
        TemporaryIntegerTableNameCache.instance().ReleaseName( self._column_name, self._table_name )
        
        return False
        
    
class DBBase( object ):
    
    def __init__( self ):
        
        self._c = None
        
    
    def _AnalyzeTempTable( self, temp_table_name ):
        
        # this is useful to do after populating a temp table so the query planner can decide which index to use in a big join that uses it
        
        self._Execute( 'ANALYZE {};'.format( temp_table_name ) )
        self._Execute( 'ANALYZE mem.sqlite_master;' ) # this reloads the current stats into the query planner, may no longer be needed
        
    
    def _CloseCursor( self ):
        
        if self._c is not None:
            
            self._c.close()
            
            del self._c
            
            self._c = None
            
        
    
    def _CreateIndex( self, table_name, columns, unique = False ):
        
        if unique:
            
            create_phrase = 'CREATE UNIQUE INDEX IF NOT EXISTS'
            
        else:
            
            create_phrase = 'CREATE INDEX IF NOT EXISTS'
            
        
        ideal_index_name = self._GenerateIdealIndexName( table_name, columns )
        
        index_name = ideal_index_name
        
        i = 0
        
        while self._ActuaIndexExists( index_name ):
            
            index_name = f'{ideal_index_name}_{i}'
            
            i += 1
            
        
        if '.' in table_name:
            
            table_name_simple = table_name.split( '.' )[1]
            
        else:
            
            table_name_simple = table_name
            
        
        statement = '{} {} ON {} ({});'.format( create_phrase, index_name, table_name_simple, ', '.join( columns ) )
        
        self._Execute( statement )
        
    
    def _Execute( self, query, *query_args ) -> sqlite3.Cursor:
        
        if HG.query_planner_mode and query not in HG.queries_planned:
            
            plan_lines = self._c.execute( 'EXPLAIN QUERY PLAN {}'.format( query ), *query_args ).fetchall()
            
            HG.query_planner_query_count += 1
            
            HG.controller.PrintQueryPlan( query, plan_lines )
            
        
        return self._c.execute( query, *query_args )
        
    
    def _ExecuteCancellable( self, query, query_args, cancelled_hook: typing.Callable[ [], bool ] ):
        
        cursor = self._Execute( query, query_args )
        
        return ReadFromCancellableCursor( cursor, 1024, cancelled_hook = cancelled_hook )
        
    
    def _ExecuteMany( self, query, args_iterator ):
        
        if HG.query_planner_mode and query not in HG.queries_planned:
            
            args_iterator = list( args_iterator )
            
            if len( args_iterator ) > 0:
                
                plan_lines = self._c.execute( 'EXPLAIN QUERY PLAN {}'.format( query ), args_iterator[0] ).fetchall()
                
                HG.query_planner_query_count += 1
                
                HG.controller.PrintQueryPlan( query, plan_lines )
                
            
        
        self._c.executemany( query, args_iterator )
        
    
    def _GenerateIdealIndexName( self, table_name, columns ):
        
        return '{}_{}_index'.format( table_name, '_'.join( columns ) )
        
    
    def _GetAttachedDatabaseNames( self, include_temp = False ):
        
        if include_temp:
            
            f = lambda schema_name, path: True
            
        else:
            
            f = lambda schema_name, path: schema_name != 'temp' and path != ''
            
        
        names = [ schema_name for ( number, schema_name, path ) in self._Execute( 'PRAGMA database_list;' ) if f( schema_name, path ) ]
        
        return names
        
    
    def _GetLastRowId( self ) -> int:
        
        return self._c.lastrowid
        
    
    def _GetRowCount( self ):
        
        row_count = self._c.rowcount
        
        if row_count == -1:
            
            return 0
            
        else:
            
            return row_count
            
        
    
    def _GetSumResult( self, result: typing.Optional[ typing.Tuple[ typing.Optional[ int ] ] ] ) -> int:
        
        if result is None or result[0] is None:
            
            sum_value = 0
            
        else:
            
            ( sum_value, ) = result
            
        
        return sum_value
        
    
    def _ActuaIndexExists( self, index_name ):
        
        if '.' in index_name:
            
            ( schema, index_name ) = index_name.split( '.', 1 )
            
            search_schemas = [ schema ]
            
        else:
            
            search_schemas = self._GetAttachedDatabaseNames()
            
        
        for schema in search_schemas:
            
            result = self._Execute( f'SELECT 1 FROM {schema}.sqlite_master WHERE name = ? and type = ?;', ( index_name, 'index' ) ).fetchone()
            
            if result is not None:
                
                return True
                
            
        
        return False
        
    
    def _IdealIndexExists( self, table_name, columns ):
        
        # ok due to deferred delete gubbins, we have overlapping index names. therefore this has to be more flexible than a static name
        # we'll search based on tbl_name in sqlite_master
        
        ideal_index_name = self._GenerateIdealIndexName( table_name, columns )
        
        if '.' in ideal_index_name:
            
            ( schema, ideal_index_name ) = ideal_index_name.split( '.', 1 )
            
            search_schemas = [ schema ]
            
        else:
            
            search_schemas = self._GetAttachedDatabaseNames()
            
        
        if '.' in table_name:
            
            table_name = table_name.split( '.', 1 )[1]
            
        
        for schema in search_schemas:
            
            table_result = self._Execute( f'SELECT 1 FROM {schema}.sqlite_master WHERE name = ?;', ( table_name, ) ).fetchone()
            
            if table_result is None:
                
                continue
                
            
            # ok the table exists on this db, so let's see if it has our index, whatever its actual name
            
            all_indices_of_this_table = self._STL( self._Execute( f'SELECT name FROM {schema}.sqlite_master WHERE tbl_name = ? AND type = ?;', ( table_name, 'index' ) ) )
            
            for index_name in all_indices_of_this_table:
                
                if ideal_index_name in index_name:
                    
                    return True
                    
                
            
        
        return False
        
    
    def _MakeTemporaryIntegerTable( self, integer_iterable, column_name ):
        
        return TemporaryIntegerTable( self._c, integer_iterable, column_name )
        
    
    def _SetCursor( self, c: sqlite3.Cursor ):
        
        self._c = c
        
    
    def _STI( self, iterable_cursor ):
        
        # strip singleton tuples to an iterator
        
        return ( item for ( item, ) in iterable_cursor )
        
    
    def _STL( self, iterable_cursor ):
        
        # strip singleton tuples to a list
        
        return [ item for ( item, ) in iterable_cursor ]
        
    
    def _STS( self, iterable_cursor ):
        
        # strip singleton tuples to a set
        
        return { item for ( item, ) in iterable_cursor }
        
    
    def _TableExists( self, table_name ):
        
        if '.' in table_name:
            
            ( schema, table_name ) = table_name.split( '.', 1 )
            
            search_schemas = [ schema ]
            
        else:
            
            search_schemas = self._GetAttachedDatabaseNames()
            
        
        for schema in search_schemas:
            
            result = self._Execute( f'SELECT 1 FROM {schema}.sqlite_master WHERE name = ? AND type = ?;', ( table_name, 'table' ) ).fetchone()
            
            if result is not None:
                
                return True
                
            
        
        return False
        
    

JOURNAL_SIZE_LIMIT = 128 * 1024 * 1024
JOURNAL_ZERO_PERIOD = 900
MEM_REFRESH_PERIOD = 600
WAL_PASSIVE_CHECKPOINT_PERIOD = 300
WAL_TRUNCATE_CHECKPOINT_PERIOD = 900

class DBCursorTransactionWrapper( DBBase ):
    
    def __init__( self, c: sqlite3.Cursor, transaction_commit_period: int ):
        
        DBBase.__init__( self )
        
        self._SetCursor( c )
        
        self._transaction_commit_period = transaction_commit_period
        
        self._transaction_start_time = 0
        self._in_transaction = False
        self._transaction_contains_writes = False
        
        self._last_mem_refresh_time = HydrusTime.GetNow()
        self._last_wal_passive_checkpoint_time = HydrusTime.GetNow()
        self._last_wal_truncate_checkpoint_time = HydrusTime.GetNow()
        self._last_journal_zero_time = HydrusTime.GetNow()
        
        self._pubsubs = []
        
    
    def _ZeroJournal( self ):
    
        if HG.db_journal_mode not in ( 'PERSIST', 'WAL' ):
            
            return
            
        
        self._Execute( 'BEGIN IMMEDIATE;' )
        
        # durable_temp is not excluded here
        db_names = [ name for ( index, name, path ) in self._Execute( 'PRAGMA database_list;' ) if name not in ( 'mem', 'temp' ) ]
        
        for db_name in db_names:
            
            self._Execute( 'PRAGMA {}.journal_size_limit = {};'.format( db_name, 0 ) )
            
        
        self._Execute( 'COMMIT;' )
        
        for db_name in db_names:
            
            self._Execute( 'PRAGMA {}.journal_size_limit = {};'.format( db_name, JOURNAL_SIZE_LIMIT ) )
            
        
    
    def BeginImmediate( self ):
        
        if not self._in_transaction:
            
            self._Execute( 'BEGIN IMMEDIATE;' )
            self._Execute( 'SAVEPOINT hydrus_savepoint;' )
            
            self._transaction_start_time = HydrusTime.GetNow()
            self._in_transaction = True
            self._transaction_contains_writes = False
            
        
    
    def CleanPubSubs( self ):
        
        self._pubsubs = []
        
    
    def Commit( self ):
        
        if self._in_transaction:
            
            self.DoPubSubs()
            
            self.CleanPubSubs()
            
            self._Execute( 'COMMIT;' )
            
            self._in_transaction = False
            self._transaction_contains_writes = False
            
            if HG.db_journal_mode == 'WAL' and HydrusTime.TimeHasPassed( self._last_wal_passive_checkpoint_time + WAL_PASSIVE_CHECKPOINT_PERIOD ):
                
                if HydrusTime.TimeHasPassed( self._last_wal_truncate_checkpoint_time + WAL_TRUNCATE_CHECKPOINT_PERIOD ):
                    
                    self._Execute( 'PRAGMA wal_checkpoint(TRUNCATE);' )
                    
                    self._last_wal_truncate_checkpoint_time = HydrusTime.GetNow()
                    
                else:
                    
                    self._Execute( 'PRAGMA wal_checkpoint(PASSIVE);' )
                    
                
                self._last_wal_passive_checkpoint_time = HydrusTime.GetNow()
                
            
            if HydrusTime.TimeHasPassed( self._last_mem_refresh_time + MEM_REFRESH_PERIOD ):
                
                self._Execute( 'DETACH mem;' )
                self._Execute( 'ATTACH ":memory:" AS mem;' )
                
                TemporaryIntegerTableNameCache.instance().Clear()
                
                self._last_mem_refresh_time = HydrusTime.GetNow()
                
            
            if HG.db_journal_mode == 'PERSIST' and HydrusTime.TimeHasPassed( self._last_journal_zero_time + JOURNAL_ZERO_PERIOD ):
                
                self._ZeroJournal()
                
                self._last_journal_zero_time = HydrusTime.GetNow()
                
            
        else:
            
            HydrusData.Print( 'Received a call to commit, but was not in a transaction!' )
            
        
    
    def CommitAndBegin( self ):
        
        if self._in_transaction:
            
            self.Commit()
            
            self.BeginImmediate()
            
        
    
    def DoPubSubs( self ):
        
        for ( topic, args, kwargs ) in self._pubsubs:
            
            HG.controller.pub( topic, *args, **kwargs )
            
        
    
    def InTransaction( self ):
        
        return self._in_transaction
        
    
    def NotifyWriteOccuring( self ):
        
        self._transaction_contains_writes = True
        
    
    def pub_after_job( self, topic, *args, **kwargs ):
        
        if len( args ) == 0 and len( kwargs ) == 0:
            
            if ( topic, args, kwargs ) in self._pubsubs:
                
                return
                
            
        
        self._pubsubs.append( ( topic, args, kwargs ) )
        
    
    def Rollback( self ):
        
        if self._in_transaction:
            
            self._Execute( 'ROLLBACK TO hydrus_savepoint;' )
            
            # any temp int tables created in this lad will be rolled back, so 'initialised' can't be trusted. just reset, no big deal
            TemporaryIntegerTableNameCache.instance().Clear()
            
            # still in transaction
            # transaction may no longer contain writes, but it isn't important to figure out that it doesn't
            
        else:
            
            HydrusData.Print( 'Received a call to rollback, but was not in a transaction!' )
            
        
    
    def Save( self ):
        
        if self._in_transaction:
            
            try:
                
                self._Execute( 'RELEASE hydrus_savepoint;' )
                
            except sqlite3.OperationalError:
                
                HydrusData.Print( 'Tried to release a database savepoint, but failed!' )
                
            
            self._Execute( 'SAVEPOINT hydrus_savepoint;' )
            
        else:
            
            HydrusData.Print( 'Received a call to save, but was not in a transaction!' )
            
        
    
    def TimeToCommit( self ):
        
        return self._in_transaction and self._transaction_contains_writes and HydrusTime.TimeHasPassed( self._transaction_start_time + self._transaction_commit_period )
        
    
