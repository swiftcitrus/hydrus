import collections
import hashlib
import itertools    
import math
import os
import random
import sqlite3
import time
import traceback
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDB
from hydrus.core import HydrusDBBase
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core.networking import HydrusNetwork

from hydrus.client import ClientAPI
from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientDefaults
from hydrus.client import ClientFiles
from hydrus.client import ClientLocation
from hydrus.client import ClientOptions
from hydrus.client import ClientSearch
from hydrus.client import ClientServices
from hydrus.client import ClientThreading
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesDuplicates
from hydrus.client.db import ClientDBFilesInbox
from hydrus.client.db import ClientDBFilesMaintenance
from hydrus.client.db import ClientDBFilesMaintenanceQueue
from hydrus.client.db import ClientDBFilesMetadataBasic
from hydrus.client.db import ClientDBFilesMetadataRich
from hydrus.client.db import ClientDBFilesPhysicalStorage
from hydrus.client.db import ClientDBFilesSearch
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBFilesViewingStats
from hydrus.client.db import ClientDBMaintenance
from hydrus.client.db import ClientDBMappingsCacheCombinedFilesDisplay
from hydrus.client.db import ClientDBMappingsCacheCombinedFilesStorage
from hydrus.client.db import ClientDBMappingsCacheSpecificDisplay
from hydrus.client.db import ClientDBMappingsCacheSpecificStorage
from hydrus.client.db import ClientDBMappingsCounts
from hydrus.client.db import ClientDBMappingsCountsUpdate
from hydrus.client.db import ClientDBMappingsStorage
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBNotesMap
from hydrus.client.db import ClientDBRepositories
from hydrus.client.db import ClientDBSerialisable
from hydrus.client.db import ClientDBServicePaths
from hydrus.client.db import ClientDBServices
from hydrus.client.db import ClientDBSimilarFiles
from hydrus.client.db import ClientDBTagDisplay
from hydrus.client.db import ClientDBTagParents
from hydrus.client.db import ClientDBTagSearch
from hydrus.client.db import ClientDBTagSiblings
from hydrus.client.db import ClientDBURLMap
from hydrus.client.importing import ClientImportFiles
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult
from hydrus.client.media import ClientMediaResultCache
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientTagsHandling
from hydrus.client.networking import ClientNetworkingBandwidth
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingLogin
from hydrus.client.networking import ClientNetworkingSessions

from hydrus.client.importing import ClientImportSubscriptionLegacy
from hydrus.client.networking import ClientNetworkingSessionsLegacy
from hydrus.client.networking import ClientNetworkingBandwidthLegacy

#
#                                𝓑𝓵𝓮𝓼𝓼𝓲𝓷𝓰𝓼 𝓸𝓯 𝓽𝓱𝓮 𝓢𝓱𝓻𝓲𝓷𝓮 𝓸𝓷 𝓽𝓱𝓲𝓼 𝓗𝓮𝓵𝓵 𝓒𝓸𝓭𝓮
#                                              ＲＥＳＯＬＶＥ ＩＮＣＩＤＥＮＴ
#
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓██▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▒█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓▓▓▓█▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██ █▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒░▒▓▓▓░  █▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▓▒  ░▓▓▓ ▒█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▓▒  ▓▓▓▓ ▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▓▓▒▒▒▒▒▓  ▓▓▓▓  ▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▒█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ░▓░  ▓▓▓▓▒▒▒▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▓▓▓█▒ ▓▓▓█  ▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░ ▓░  ▓▒▒▒▒▒▒▒▒▒▒▒▓▓▓▓▒▓▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓  ▓▓▓░   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  ▒▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▒▒▒▓▓▓▓▒▒▒▒▒▒▒▒▒▒▓  ▓▓▓   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█  ▒█▓░▒▓▒▒▒▒▓▓▓█▓████████████▓▓▓▓▓▒▒▒▓  ▒▓▓▓  ▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ░█▓ ░▓▓█████████▓███▓█▓███████▓▓▓▓▓ ░▓▓█  █▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓█▓▓▓▓▓▓▓▓▓▓▓▓▓█▒▒█▓▓▓▓▓▓▓▓▓▓  ▓▓ ░██████▓███▓█████▓▓▓▓▓█████▓▓▓▒ ▓▓▓▒ ▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒███▓▓▓▓▓▓▓▓▓▓▓████▓█▓▓▓▓▓▓▓▓▓▓█░▓▓███▓▓▓█▓█▓▓▓█▓█▓███▓▓▓▓▓▓██████▓ ▓▓▓   ▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▒▓▓▓█▒▓▓▒▓▓▓██▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒██████▓▓▓▓▓████▓▓█▓▓██▓▓▓▓▓▓██▓███ ▓█   ██▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓ ▒███▒█▒▓█▓▓███▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██▓█▓▓██▓▓▓▓▓▓▓▓██▓▓▓▓█▓░▒▒▒▓▓█████ ▒█  ▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓░▓██▓▒█▓████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓███▓▓▓█▓▓██▓▓▓▓▓▓▓▓▓█▓▓▓▓█░ ▓▓▓▓█████▓▓▓░   █▓▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▒▓██▓▒█▓▓█▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██▓▓▓▓▓▓▓▓▓██▓▓▓▓▓▒▒▒▓▒ ▒▓▓░▓▓▓▓▓█████▓▓▒  ▓▓▓▒▓▓  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓███▓███▓▓▓▒█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓█▓█▓▓█▓▓▓▓███▓▒▒▒▒░░▓▓▓▓█▓▓▓▓▓███████▓▓░██▓▓▓▓▒ ▒▓ ▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▒▓█▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓▓▓▓▓▓█▓▓▓▓▒▒▓██▓▓▒▓▓▓▓████▓▓▓▓▓██▓▓███▒ ▒█▓▒░░ ▓▓ ▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒██▒▓▓█▓█▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██▓▓█▓█▓▒▓█▓▓▓▓▓▓▓▓██████▓▓███▓▓▓▓█████▓█▓  ▓  ░▒▓▓▒ ▒█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓▓█▓▓█▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██▓▓█▓▓█▓▓▓▓▓▓██▓██████████████▓▓▓███▓▓▓█░░█░▒▓▓░▒▒ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██▒▓██▓█▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒██▓▓█▓▓▓██▓▓▓▓░▓█▓▒▓███████████▓▓▓███▓▓▓█▓▒▒▓▒   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓█▒▓██▓▓█▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓███ ▓███░▒▒  ▓▓▒     ░░▒░░▓█▓▓██▓▓▓▓█▓▓▒  ▒█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓██▓▓███▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓██▓███   ███  ▒   ▒▒░░▓▓▒██   ██████▓▓▓█░▒▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██▓▓██▓█▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██▓█▒   ░██▓  ░▒▒▓█████▓    █▓█▓██▓▓▓█▓██▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒██▓▓██▓▒█▒█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██▓▒▓  ░   ▒▒   ▒ ░█▓▒      ▒ ░░▒█▓▓█████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓███▓███▒█▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓██▒  ▒▓▓▒                  ░▓▒▒██▓▓███▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓░▓▓█░▓█▒▓█▓███▓▓▒▓▓▓▓▓▓▓▒▓██▒▓████                  ▒▓░▒█▓▓█▓██▓█▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██▓▓██▓░█▓█▓▒▒▒▓▓██▓▓▒▓▓▓▓▓▒▓██▒  ▓░                  ▒▓▒▓█▓███▓▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓▒▓▓█████▓▓▓██▒▓█▓█▓▓▓▓▒▒██▓▓▓▓▓▓▓▓▒▓█▓                      ▒▓▒▓█▓▓█▓█▓▓█▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▒░▒▓▓███▓▓██▓▓▓▓█▓▓█▓██▓█▓▓▒▓█▓▓▓▓▓▓▓▓▓▓▓▓▒   ░                 ▓▓▒▓█▒██▓▓▓▓█▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓▓█████▓▒▓▓▓█▓▓▓▓██▒█▓▓███▓▓▓▒██▓▓▓▓▓▓▓▓▓▓▓▓░                   ▓█▒░▒▒▓██▓█▓▓█▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█████▓▓  ▓▓██▓▓▓██▒▓█▓█▓▒▓▓▓▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓░    ░░          ░▒█▒▒▒░▒▓█▓▓▓▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▓█▓▓▓   ▒██▓▓▓▓█▓▒██▓▓▒▓▓▓▓▒██▓▓▓▓▓▓▓▓▓▓▓▓█▓             ░▓░░ ░███▓██▓▓▓▓▓█▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒██▓▓▓░▓██▓▓▓▓██░▓█▓▓▓▓▓▓▓▒▓██▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒        ░▓▒  ░ ▓███▓██▓█▓▓▓█▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓█▓█▓▒▓██▓▓▓██▓▒█▓▓▓▓▓▓▓▓▒██▓▒▓▓▓▓▓▓▓▓▓▓█▓▓▓▓▓░   ▓█▓      █▓▓█▓█▓▓█▓▓▓██▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██   ░██▓▓▓▓█▓▒▓█▓▓▒▓▓▓▓▒▓█▓▓▓▓▓▓▓▓▓▒███▓▒▓▓▓▓███▓░       █▓▓█▓█▓▓█▓▓▓██▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓  █▓░  ░█▓▓▓▓██▓▓██▓▓▒▓▓▓▓▒██▓▓▓▓▓▓▓▓▒▓█▓▓▓▒▓▓▓▓▓░        ░█▒▓█▓█▓▓▓█▓▓▓▓▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█░ ░   ███  ██▓▓▓██▓▒██▓▓▒▓▓▓▓▒▓██▓▓▓▓▓▓▓▒▓█▓▓▓▒▒▓▓█▓          █▓██▒█▓▓▓▓█▓▓▓█▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒    ░  ███  ▓█▓▓▓▓██▒▓█▓▓▓▓▓▓▓▓▒██▓▒▓▓▓▓▓▓▓██▓█▒▓▓█▓░          █▓██▒▓██████▓▓▓▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█      ▓ ▓█   ░█▓▓▓▓██▓▓██▓▓▒▓▓▓▓▒▓█▓▓▒▓▓▓▓▓░▓███▓▓█░            █▓█▓▓▓▓▓█▓░███▓▓▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓█  ▓▒ ██▒    ▒████▓███▒▓█▓▓▓▒▓▓▓▒▓██▓▓▓▓▓▓▓▒▒███▓▓▒     ▒      ▓███▓▓▓▓▓ ░░▓▓██▓▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██▓▓█▓██     ▓█▓▓▓▓▓██▓▓██▓▓▒▒▓▒▒▒▓██▓▒      ▓█▓██   ░        ▓▒▓██▓▓▓▒  ░    ██▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓██▓█████▓      ▓██▓█████▓▓▓█▓▓▓▓▓▓▓▓█▒██     █░▒▓▓▓█           ▓▒▓██▓▒░  ▒▒      █▓▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓████▓         ▓█████████▓▓██▓▓▓▓▓█▓▓▓██▒   █▓  ▓▒▓▒          ▓▓▓█▓   ▒▓         ▒█▓▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒██▓▒▓░        ▒███▓█████▓▓███▓▓▓▓▓█████▓  ▓▓▓░ ▓▒▓▒        ▒▓▓▓▒  ▓▓▓█▒          ▓█▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▓▓▓▒        ███▓▓█████▓▓████▓▓▓███▓░   ▓▓▓█▓ ▓▓▓       ▓█▒░  ▒▒▓▓▓█            ██▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▓▒▓▒▓▓▓▓▓▓▓▓▓▓█▓       ▒███▓█████▓▓▓█▓▓▓███▓     ▓▓▓▓▓  ▒▓▓     ▓▓▒  ▒▓▒█▓▓▒▓▓            ▓█▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▓▒▒█▓▒▓▒▓▓▓▓▓▓▓▓█▒       ███▓▓█▒██▓▓█▓███▓▓▓░    ▓▓▒▓▒▓▓█  ▓▒ ░▓▓░   ▒█▓▓▓▒▒▓▓▓            ▒█▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▓▒▒▓▓▓▓▓▒▓▓▒▒▒▓▓▓▓▓       ▒██▓█▒▒▓██▒████▓▒▒▓    ▓▓▒▓▒▒▒▓▓▓ ▒▒ ▒▓░▓▒█▓▓▒▒▒▒▒▒▒▓▒             █▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▓▓▓▓▓▒▒▓█▓▓▓▓▓▓▓▓▓▓▒▓▒▒▓▒       ▓███▓▓▓██░▓▓██▓▒▓▒   ▓▓▒▒▒▒▒▒▓▓▓█▓░ ▒█▓▓▓▓▓▒▒▒▒▒▒▒▒▓▒  ░░         ▓▓▒▒▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▓▒▓▒▓▒▒▓█▓██▓▓▓▓▓▓▓▓▓▓▓▓▓▓░      ▒█▓▓█▓▒██░░ ▒██▒▓  ░▓▒▒▒▒▒▒▒▒▓▓▓▓▓█▓▓█▓▓▒▒▒▒▒▒▒▒▒▒▒▓░ ░▒▓▓         █▓▓▓▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓
# ▒▓▓▓▒▒▓█▓▓▓█▓▓▓▓▓▓▒▓▓▓▓▓▓▓██████████▓██▒▓█▓▓  ██▓▓  ▓▒▒▒▒▒▒▒▒▒▒▓▓▓░▒▓▒▓▓▒▒▒▒▒▒▒▒▒▒▒▒▓░░▒▒░▒▓        ▒███▒▓▓▓▒▓▓▓▓▓▓▓▒▓▓▓
# ▓▓▓▒▒▓█▓▓████▓▓▓▓▓▓▓▓▓▓▓▓█▓▓███████▓▒▓█▓▓██▒▒ ▓██  ▒▓▒▒▒▒▒▒▒▒▒▒▓▓░ ▒▒░▓▓▒▒▒▒▒▒▒▒▒▒▒▒▓▒ ░░░░█▓        ▓█▒▒▓▓▓▓▒▓▓▓▓▓▓▓▓▓▓
# ▒▓▒▒▓███████████▓▓▓▓▓▓▓▓▓▓▓█▓▓▓▓▓▓██▒▓█▓▒██▒▓░▒██  ▓▓▒▒▒▒▒▒▒▒▒▒▓▒  ▒▒░▓▓▒▒▒▒▒▒▒▒▒▒▒▒▓▓  ░░▒▓▓░    ▒░▒   ▒▓▒▓▒▓▒▓▒▓▒▓▒▓▒▓
# ▓▒▓▒▓▓▓▓███████▓█▓██▓▓█▓▓▓▓▓▓▓▓▓█▓██▓▓██▒▓█▓▒▓▓██░ ▒▓▒▓▒▓▓▓▒▒▓▓▓ ░░▒░ ▒▓▒▒▒▒▒▒▒▒▒▒▒▒▓▓  ░ ▓▓▓▓  ▒ ▒     ▒▓▓▒▓▒▓▒▓▓▓▒▓▒▓▒
# ▒▓▒▓▒▒▒▒▒▓▓██████████▓▓▓▓▓▓█▓█▓█▓███▓▓▓█▓▒██▒▓█▒██ ░█▓▓▓▓▓▓▓▓▓▓  ▒▒▒░ ▒▓▒▒▒▒▒▒▒▒▒▒▒▓▓▓ ░░▒▓▒▓█▒ ░       ██▒▓▒▓▒▓▒▓▒▓▒▓▒▓
# ▓▒▓▒▓▒▓▒▒▒▒▒▒▒▓▓█████████▓▓██████████▓▓█▓▒▓██▓█▒▓█░ ▓▓▓▓▓▓▓▓▓█▒ ▒▒▓░▒ ░█▓▓▓▒▓▓▓▓▓▓▓▒▓▓▒ ▒▓▓▒▓▒░    ░▒█▒ ▓▒▓▓▓▒▓▒▓▒▓▒▓▒▓▒
# ▒▓▒▓▒▓▒▓▒▓▒▒▒▒▒▒▒▒▒▓▓▓▓▓▓▓███████▓▓██▓▓▓█▒▒██▓▓▓▓█▓ ░█▓▓▓▓▓▓▓▓  ▒▒▒ ▒  █▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ▒▓▒▓▒▓▓▓▓▓░▓█▓▒   ▒▓▒▓▒▓▒▓▒▓▒▓▒▓
# ▓▒▓▒▓▒▓▒▓▒▒▒▓▒▓▒▒▒▒▒▒▒▒▒▒▒▒▒▓    ░▓▒██▓▓▓▓▒▓█▓▓█▓▓█ ░▓▓▓▓▓▓▓█░ ░▒▒▒ ▒  █▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▒▒▓▒▒▒▒▓▓▓▒░ ░      ▓▓▒▓▒▓▒▓▒▓▒▒▒
# ▒▓▒▓▒▒▒▒▒▒▒▒▒▒▒▓▒▒▒▒▒▒▒▒▒▒▒▒▓▒   ▒░  ██▓██▒▓██▓█▓▒█▒░▓▓▓▓▓▓▓▓  ░▓▓▒ ▒  ▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▓▒          ▓▓▒▒▒▓▒▒▒▓▒▒
# ▓▒▓▒▓▒▓▒▒▒▒▒▒▒▓▒▒▒▒▒▓▒▒▒▓▒▒▒▓▓░░░    ▓██▓█▓▓██▓▓█▒█▓▒▓▓▓▓▓▓▓░  ░▓▒░ ▒  ▒▒▒█▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▒▒▒▒▒▒▓▓▒         ░▓▓▒▒▒▒▒▒▒▓▒
# ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▒ ░     ██▓▓█▒▓█▓▒█▓▓█▓▓▓▓▓▓▓▓░  ░▓▓  ▒░ ▒▒ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▓▒▓▒▓▓▒     ░░░ ░▓▓▒▒▒▓▒▒▒▒
# ▓▒▒▒▒▒▒▒▒▒▒▒▒▒▓▒▒▒▓▒▒▒▒▒▒▒▒▒▒▒▓ ░░    ▓██▓█▒▓██▓▓▓▓█▓▓▓▓▓▓▓▓██▒░▒▒  ▓▒ ░▓ ░█▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▓▒▒▒▓▒▓▓     ░░░░ ▒▓▓▒▒▒▒▒▓▒
# ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓ ░░   ░██▓▓▓▒██▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▒  ▒▒  ▓░ ▓▓▓▓▓▓▓▓▓▓▓█▒▒▒▒▒▒▒▒▒▒▒▒▓▓▒       ░ ▒▓▓▒▒▒▒▒▒
# ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▒▒▒▒▓▓ ░░   ██▓▓█▒▓██▓██▓▓▓▓▓▓▓▓▓▓▓▓▓█▒  ▒▓  ░▒  ▓▓▓▓▓▓▓▓▓█▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓ ░ ░░░     ▒▓▒▒▒▒▒▒
# ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓░    ▓██▓▓▓▒██▓▓▓▓▓▓▓▓▒▒▒▓▓▓▓▓▓░  ░▓▒▓▓▓░▒▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▓▒     ░░ ░░  ▒▓▒▒▒▒▒
# ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▒  ▓█▓█▓▓█▒███▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▓▓▓▒▒▓█▓█▓▓█▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓      ░░░ ░░  ▓▒▒▒▒▒
# ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▓▓▓▒▓█▓█▓▓██▓▒▓▓▓▓▓▓▓▓▓▓▓▒▒▒▓▓▓▓▓▓▒▒▒▒▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▓▓     ░  ░░░░░  ▓▓▒▒▒▒
# ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓██▒▒▓▓█▓▓▒▓██▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▓▒  ▒░   ░ ░░░░░  ▓▒▒▒▒▒
# ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒██▓▒▓▓▓▒▓▓▓█▓▒▒▓▓▓▒▓▒▒▒▓▒▒▒▒▓▓▒▒▒▓▓▓▓▓▓▓▒▒▒▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▓░  ██▓   ░  ░░░░ ▒▓▒▒▒▒▒
# ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░▓██▒▓▓▓█▓▓██▓▒▓▓▓▓▓▒▒▒▒▒▒▒▒▒▓▒▓▓▓▓▓▒▓▒▓▓▒▓▓▓▓▓▒▓▓▒▒▒▒▒▒▒▒▒▓░▓█▒▒░▒    ░ ░░░░ ▒▓▒▒▒▒▒
# ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒██▓▓▓▓▓███▓▒▓▒▓▒▓▒▓▒▒▒▒▒▒▒▒▓▓▒▓▒▓▓▓▓▓▒▒▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▓▓██▒   ▒░      ░░░ ▓▒▒▒▒▒▒
# ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒███▓▒▓██▓█▓▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓▓▓▓▓▓▓▓▒▒▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒█░    ▒       ░░ ░▓▒▒▒▒▒▒
# ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓██▓▓▓▒▒▓▓▓▓▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▓▓        ▒░▓░  ░░ ▒▓▒▒▒▒▒▒
# ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░▒▒░░▓▓▒▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▓▓▓  ░▒▒▒▒       ▓████▒     ▒▒▒▒▒▒▒▒

def BlockingSafeShowMessage( message ):
    
    HydrusData.DebugPrint( message )
    
    HG.client_controller.CallBlockingToQt( HG.client_controller.app, QW.QMessageBox.warning, None, 'Warning', message )
    
def report_content_speed_to_job_key( job_key, rows_done, total_rows, precise_timestamp, num_rows, row_name ):
    
    it_took = HydrusData.GetNowPrecise() - precise_timestamp
    
    rows_s = HydrusData.ToHumanInt( int( num_rows / it_took ) )
    
    popup_message = 'content row ' + HydrusData.ConvertValueRangeToPrettyString( rows_done, total_rows ) + ': processing ' + row_name + ' at ' + rows_s + ' rows/s'
    
    HG.client_controller.frame_splash_status.SetText( popup_message, print_to_log = False )
    job_key.SetStatusText( popup_message, 2 )
    
def report_speed_to_job_key( job_key, precise_timestamp, num_rows, row_name ):
    
    it_took = HydrusData.GetNowPrecise() - precise_timestamp
    
    rows_s = HydrusData.ToHumanInt( int( num_rows / it_took ) )
    
    popup_message = 'processing ' + row_name + ' at ' + rows_s + ' rows/s'
    
    HG.client_controller.frame_splash_status.SetText( popup_message, print_to_log = False )
    job_key.SetStatusText( popup_message, 2 )
    
def report_speed_to_log( precise_timestamp, num_rows, row_name ):
    
    if num_rows == 0:
        
        return
        
    
    it_took = HydrusData.GetNowPrecise() - precise_timestamp
    
    rows_s = HydrusData.ToHumanInt( int( num_rows / it_took ) )
    
    summary = 'processed ' + HydrusData.ToHumanInt( num_rows ) + ' ' + row_name + ' at ' + rows_s + ' rows/s'
    
    HydrusData.Print( summary )
    
class JobDatabaseClient( HydrusData.JobDatabase ):
    
    def _DoDelayedResultRelief( self ):
        
        if HG.db_ui_hang_relief_mode:
            
            if QC.QThread.currentThread() == HG.client_controller.main_qt_thread:
                
                HydrusData.Print( 'ui-hang event processing: begin' )
                QW.QApplication.instance().processEvents()
                HydrusData.Print( 'ui-hang event processing: end' )
                
            
        
    
class DB( HydrusDB.HydrusDB ):
    
    READ_WRITE_ACTIONS = [ 'service_info', 'system_predicates', 'missing_thumbnail_hashes' ]
    
    def __init__( self, controller, db_dir, db_name ):
        
        self._initial_messages = []
        
        self._have_printed_a_cannot_vacuum_message = False
        
        self._weakref_media_result_cache = ClientMediaResultCache.MediaResultCache()
        
        self._after_job_content_update_jobs = []
        self._regen_tags_managers_hash_ids = set()
        self._regen_tags_managers_tag_ids = set()
        
        HydrusDB.HydrusDB.__init__( self, controller, db_dir, db_name )
        
    
    def _AddFiles( self, service_id, rows ):
        
        hash_ids = { row[0] for row in rows }
        
        existing_hash_ids = self.modules_files_storage.FilterHashIdsToStatus( service_id, hash_ids, HC.CONTENT_STATUS_CURRENT )
        
        new_hash_ids = hash_ids.difference( existing_hash_ids )
        
        if len( new_hash_ids ) > 0:
            
            service = self.modules_services.GetService( service_id )
            
            service_type = service.GetServiceType()
            
            valid_rows = [ ( hash_id, timestamp ) for ( hash_id, timestamp ) in rows if hash_id in new_hash_ids ]
            
            # if we are adding to a local file domain, either an import or an undelete, remove any from the trash and add to the umbrella services if needed
            
            if service_type == HC.LOCAL_FILE_DOMAIN:
                
                self._DeleteFiles( self.modules_services.trash_service_id, new_hash_ids )
                
                self._AddFiles( self.modules_services.combined_local_media_service_id, valid_rows )
                self._AddFiles( self.modules_services.combined_local_file_service_id, valid_rows )
                
            
            if service_type == HC.LOCAL_FILE_UPDATE_DOMAIN:
                
                self._AddFiles( self.modules_services.combined_local_file_service_id, valid_rows )
                
            
            # insert the files
            
            pending_changed = self.modules_files_storage.AddFiles( service_id, valid_rows )
            
            if pending_changed:
                
                self._cursor_transaction_wrapper.pub_after_job( 'notify_new_pending' )
                
            
            delta_size = self.modules_files_metadata_basic.GetTotalSize( new_hash_ids )
            num_viewable_files = self.modules_files_metadata_basic.GetNumViewable( new_hash_ids )
            num_files = len( new_hash_ids )
            num_inbox = len( new_hash_ids.intersection( self.modules_files_inbox.inbox_hash_ids ) )
            
            service_info_updates = []
            
            service_info_updates.append( ( delta_size, service_id, HC.SERVICE_INFO_TOTAL_SIZE ) )
            service_info_updates.append( ( num_viewable_files, service_id, HC.SERVICE_INFO_NUM_VIEWABLE_FILES ) )
            service_info_updates.append( ( num_files, service_id, HC.SERVICE_INFO_NUM_FILES ) )
            service_info_updates.append( ( num_inbox, service_id, HC.SERVICE_INFO_NUM_INBOX ) )
            
            # remove any records of previous deletion
            
            if service_id != self.modules_services.trash_service_id:
                
                num_deleted = self.modules_files_storage.ClearDeleteRecord( service_id, new_hash_ids )
                
                service_info_updates.append( ( -num_deleted, service_id, HC.SERVICE_INFO_NUM_DELETED_FILES ) )
                
            
            # if entering the combined local domain, update the hash cache
            
            if service_id == self.modules_services.combined_local_file_service_id:
                
                self.modules_hashes_local_cache.AddHashIdsToCache( new_hash_ids )
                
            
            # if adding an update file, repo manager wants to know
            
            if service_id == self.modules_services.local_update_service_id:
                
                self.modules_repositories.NotifyUpdatesImported( new_hash_ids )
                
            
            # if we track tags for this service, update the a/c cache
            
            if service_type in HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES:
                
                tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                
                with self._MakeTemporaryIntegerTable( new_hash_ids, 'hash_id' ) as temp_hash_id_table_name:
                    
                    for tag_service_id in tag_service_ids:
                        
                        self.modules_mappings_cache_specific_storage.AddFiles( service_id, tag_service_id, new_hash_ids, temp_hash_id_table_name )
                        self.modules_mappings_cache_specific_display.AddFiles( service_id, tag_service_id, new_hash_ids, temp_hash_id_table_name )
                        
                    
                
            
            # now update the combined deleted files service
            
            if service_type in HC.FILE_SERVICES_COVERED_BY_COMBINED_DELETED_FILE:
                
                location_context = self.modules_files_storage.GetLocationContextForAllServicesDeletedFiles()
                
                still_deleted_hash_ids = self.modules_files_storage.FilterHashIds( location_context, new_hash_ids )
                
                no_longer_deleted_hash_ids = new_hash_ids.difference( still_deleted_hash_ids )
                
                self._DeleteFiles( self.modules_services.combined_deleted_file_service_id, no_longer_deleted_hash_ids )
                
            
            # push the service updates, done
            
            self._ExecuteMany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', service_info_updates )
            
        
    
    def _AddService( self, service_key, service_type, name, dictionary ):
        
        name = self.modules_services.GetNonDupeName( name )
        
        service_id = self.modules_services.AddService( service_key, service_type, name, dictionary )
        
        self._AddServiceCreateFilesTables( service_id, service_type )
        
        if service_type in HC.REPOSITORIES:
            
            self.modules_repositories.GenerateRepositoryTables( service_id )
            
        
        self._AddServiceCreateMappingsTables( service_id, service_type )
        
    
    def _AddServiceCreateFilesTables( self, service_id, service_type ):
        
        if service_type in HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES:
            
            self.modules_files_storage.GenerateFilesTables( service_id )
            
            tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
            for tag_service_id in tag_service_ids:
                
                self.modules_mappings_cache_specific_storage.Generate( service_id, tag_service_id )
                
            
        
    
    def _AddServiceCreateMappingsTables( self, service_id, service_type ):
        
        if service_type in HC.REAL_TAG_SERVICES:
            
            self.modules_tag_search.Generate( self.modules_services.combined_file_service_id, service_id )
            
            file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES )
            
            for file_service_id in file_service_ids:
                
                self.modules_tag_search.Generate( file_service_id, service_id )
                
            
            self.modules_tag_parents.Generate( service_id )
            self.modules_tag_siblings.Generate( service_id )
            
            self.modules_mappings_storage.GenerateMappingsTables( service_id )
            
            self.modules_mappings_cache_combined_files_storage.Generate( service_id )
            
            file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
            
            for file_service_id in file_service_ids:
                
                self.modules_mappings_cache_specific_storage.Generate( file_service_id, service_id )
                
            
        
        if service_type in HC.FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES:
            
            tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
            for tag_service_id in tag_service_ids:
                
                self.modules_tag_search.Generate( service_id, tag_service_id )
                
            
        
    
    def _Backup( self, path ):
        
        self._CloseDBConnection()
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        try:
            
            job_key.SetStatusTitle( 'backing up db' )
            
            self._controller.pub( 'modal_message', job_key )
            
            job_key.SetStatusText( 'closing db' )
            
            HydrusPaths.MakeSureDirectoryExists( path )
            
            for filename in self._db_filenames.values():
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                job_key.SetStatusText( 'copying ' + filename )
                
                source = os.path.join( self._db_dir, filename )
                dest = os.path.join( path, filename )
                
                HydrusPaths.MirrorFile( source, dest )
                
            
            additional_filenames = self._GetPossibleAdditionalDBFilenames()
            
            for additional_filename in additional_filenames:
                
                source = os.path.join( self._db_dir, additional_filename )
                dest = os.path.join( path, additional_filename )
                
                if os.path.exists( source ):
                    
                    HydrusPaths.MirrorFile( source, dest )
                    
                
            
            def is_cancelled_hook():
                
                return job_key.IsCancelled()
                
            
            def text_update_hook( text ):
                
                job_key.SetStatusText( text )
                
            
            client_files_default = os.path.join( self._db_dir, 'client_files' )
            
            if os.path.exists( client_files_default ):
                
                HydrusPaths.MirrorTree( client_files_default, os.path.join( path, 'client_files' ), text_update_hook = text_update_hook, is_cancelled_hook = is_cancelled_hook )
                
            
        finally:
            
            self._InitDBConnection()
            
            job_key.SetStatusText( 'backup complete!' )
            
            job_key.Finish()
            
        
    
    def _CacheTagDisplayForceFullSyncTagsOnSpecifics( self, tag_service_id, file_service_ids ):
        
        # this assumes the caches are empty. it is a 'quick' force repopulation for emergency fill-in maintenance
        
        tag_ids_in_dispute = set()
        
        tag_ids_in_dispute.update( self.modules_tag_siblings.GetAllTagIds( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id ) )
        tag_ids_in_dispute.update( self.modules_tag_parents.GetAllTagIds( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id ) )
        
        for tag_id in tag_ids_in_dispute:
            
            storage_implication_tag_ids = { tag_id }
            
            actual_implication_tag_ids = self.modules_tag_display.GetImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, tag_id )
            
            add_implication_tag_ids = actual_implication_tag_ids.difference( storage_implication_tag_ids )
            
            if len( add_implication_tag_ids ) > 0:
                
                for file_service_id in file_service_ids:
                    
                    self.modules_mappings_cache_specific_display.AddImplications( file_service_id, tag_service_id, add_implication_tag_ids, tag_id )
                    
                
            
            delete_implication_tag_ids = storage_implication_tag_ids.difference( actual_implication_tag_ids )
            
            if len( delete_implication_tag_ids ) > 0:
                
                for file_service_id in file_service_ids:
                    
                    self.modules_mappings_cache_specific_display.DeleteImplications( file_service_id, tag_service_id, delete_implication_tag_ids, tag_id )
                    
                
            
        
        for block_of_tag_ids in HydrusData.SplitIteratorIntoChunks( tag_ids_in_dispute, 1024 ):
            
            self._CacheTagsSyncTags( tag_service_id, block_of_tag_ids, just_these_file_service_ids = file_service_ids )
            
        
    
    def _CacheTagDisplayGetApplicationStatusNumbers( self, service_key ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        ( sibling_rows_to_add, sibling_rows_to_remove, parent_rows_to_add, parent_rows_to_remove, num_actual_rows, num_ideal_rows ) = self.modules_tag_display.GetApplicationStatus( service_id )
        
        status = {
            'num_siblings_to_sync' : len( sibling_rows_to_add ) + len( sibling_rows_to_remove ),
            'num_parents_to_sync' : len( parent_rows_to_add ) + len( parent_rows_to_remove ),
            'num_actual_rows' : num_actual_rows,
            'num_ideal_rows' : num_ideal_rows,
            'waiting_on_tag_repos' : []
        }
        
        for ( applicable_service_ids, content_type ) in [
            ( self.modules_tag_parents.GetApplicableServiceIds( service_id ), HC.CONTENT_TYPE_TAG_PARENTS ),
            ( self.modules_tag_siblings.GetApplicableServiceIds( service_id ), HC.CONTENT_TYPE_TAG_SIBLINGS )
        ]:
            
            for applicable_service_id in applicable_service_ids:
                
                service = self.modules_services.GetService( applicable_service_id )
                
                if service.GetServiceType() == HC.TAG_REPOSITORY:
                    
                    if self.modules_repositories.HasLotsOfOutstandingLocalProcessing( applicable_service_id, ( content_type, ) ):
                        
                        status[ 'waiting_on_tag_repos' ].append( 'waiting on {} for {} processing'.format( service.GetName(), HC.content_type_string_lookup[ content_type ] ) )
                        
                    
                
            
        
        return status
        
    
    def _CacheTagDisplaySync( self, service_key: bytes, work_time = 0.5 ):
        
        # ok, this is the big maintenance lad
        # basically, we fetch what is in actual, what should be in ideal, and migrate
        # the important change here as compared to the old system is that if you have a bunch of parents like 'character name' -> 'female', which might be a 10k-to-1 relationship, adding a new link to the chain does need much work
        # we compare the current structure, the ideal structure, and just make the needed changes
        
        time_started = HydrusData.GetNowFloat()
        
        tag_service_id = self.modules_services.GetServiceId( service_key )
        
        all_tag_ids_altered = set()
        
        ( sibling_rows_to_add, sibling_rows_to_remove, parent_rows_to_add, parent_rows_to_remove, num_actual_rows, num_ideal_rows ) = self.modules_tag_display.GetApplicationStatus( tag_service_id )
        
        while len( sibling_rows_to_add ) + len( sibling_rows_to_remove ) + len( parent_rows_to_add ) + len( parent_rows_to_remove ) > 0 and not HydrusData.TimeHasPassedFloat( time_started + work_time ):
            
            # ok, so it turns out that migrating entire chains at once was sometimes laggy for certain large parent chains like 'azur lane'
            # imagine the instance where we simply want to parent a hundred As to a single B--we obviously don't have to do all that in one go
            # therefore, we are now going to break the migration into smaller pieces
            
            # I spent a large amount of time trying to figure out a way to _completely_ sync subsets of a chain's tags. this was a gigantic logical pain and complete sync couldn't get neat subsets in certain situations
            
            # █▓█▓███▓█▓███████████████████████████████▓▓▓███▓████████████████
            # █▓▓█▓▓▓▓▓███████████████████▓▓▓▓▓▓▓▓▓██████▓▓███▓███████████████
            # █▓███▓████████████████▓▒░              ░▒▓██████████████████████
            # █▓▓▓▓██████████████▒      ░░░░░░░░░░░░     ▒▓███████████████████
            # █▓█▓████████████▓░    ░░░░░░░░░░░░░░░░░ ░░░  ░▓█████████████████
            # ██████████████▓    ░░▒▒▒▒▒░░ ░░░    ░░ ░ ░░░░  ░████████████████
            # █████████████▒  ░░░▒▒▒▒░░░░░░░░       ░   ░░░░   ████▓▓█████████
            # ▓▓██████████▒ ░░░░▒▓▒░▒▒░░   ░░░       ░ ░ ░░░░░  ███▓▓▓████████
            # ███▓███████▒ ▒▒▒░░▒▒▒▒░░░      ░          ░░░ ░░░  ███▓▓▓███████
            # ██████████▓ ▒▒░▒░▒░▒▒▒▒▒░▒░ ░░             ░░░░░ ░  ██▓▓▓███████
            # █████▓▓▓█▒ ▒▒░▒░░░░▒▒░░░░░▒░                ░ ░ ▒▒▒  ██▓▓███████
            # ▓▓▓▓▓▓▓█░ ▒▓░░▒░░▒▒▒▒▓░░░░░▒░░             ░ ░░▒▒▒▒░ ▒██▓█▓▓▓▓▓▓
            # ▓▓▓▓███▓ ▒▒▒░░░▒▒░░▒░▒▒░░   ░░░░░           ░░░▒░ ▒░▒ ███▓▓▓▓▓▓▓
            # ███████▓░▒▒▒▒▒▒░░░▒▒▒░░░░      ░           ░░░ ░░░▒▒░ ░██▓████▓▓
            # ▓▓█▓███▒▒▒▓▒▒▓░░▒░▒▒▒▒░░░░░ ░         ░   ░ ░░░░░░▒░░░ ██▓█████▓
            # ▒▒▓▓▓▓▓▓▒▓▓░░▓▒ ▒▒░▒▒▒▒▒░░                     ░░ ░░░▒░▒▓▓██████
            # ▒▒▓▓▓▓▓▓▒▒▒░▒▒▓░░░▒▒▒▒▒▒░                       ░░░░▒▒░▒▓▓▓▓▓▓▓▓
            # ▓▒▓▓▓▓▓▓▒▓░ ▒▒▒▓▒▒░░▒▒▒▒▒▒░▒▒▒▒▒▒▒▒▒▒▒░░░░░▒░▒░░░▒░▒▒▒░▓█▓▓▓▓▓▓▓
            # ▓▒▒▓▓▓▓▓▓▓▓░ ▒▒▒▓▒▓▒▒▒▒▒▒▒▒▒▓▓▓▓▓▓▓▓▓▒▒▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▓▓▓▓▓▓▓▓▓
            # ▓▓▓▓▓▓▓▓▓▓▓▓▒░▒▒▒░▒▒▓▒▒▒░░▒▓▓▓██▓▓▓░░░░░▒▒▒▓▓▒ ░▒▒▒▒▒▒▓▓▓▓▒▒▒▓▓▓
            # █▓█▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▓▓▓▒▒▒▓▓▓▓▒▒▒▓█▓   ░▓▓▒▒▓█▓▒░▒▒▒▒▓█▓█▓▓▓▓▓▓▓
            # █████▓▒▓▓▓▓▓▒▓▓▒▒▒▒▒▒▒▒▒▒▓▒░▒▓▒░░ ░▒▒  ░░░  ▓█▓▓▓▒▒▒▒█▓▒▒▒▓▓▓▓▓▒
            # █████▓▓▓█▓▓▓▓▒▓▓▓▒▒▒▒▒▒░▒▒░░░░   ░░░▒░  ▒ ░  ░ ░▒░░▒▓▓▓▒▒▒▒▒▒▒▒░
            # ████▓▓▓███▓▓▓▓▓▓▓▒▒▒▒░░  ▒▒░   ░░░░▒▒   ░▒░▒░  ░░ ░▓█▓▓▒▒▒▒░░▒▒▒
            # ███▓▓▓█████▓▓▓▒▒▓▒▒▒▒▒░░  ░ ░░▒░ ░▒▒▒    ▒░░▒░░   ▒▓▒▒▒░▒▒▒▒▓▓▓▒
            # ████▓███████▓▒▒▒░▒▒▓▓▓▒▒░░   ░   ▒▒▓██▒▒▓▓░  ░░░░▒▒░▒▒▒▒▒▓▒▓▒▓▒▒
            # ████████████▒░▒██░▒▓▓▓▓▓▒▒▒░░░░  ▒▓▒▓▓▓▒░▒▒░  ▒▒▒▓▒▒▒▒▓▒▒▓▓▓▒▒▒▒
            # ████▓▓▓▓▓▓▒▓▒  ▓▓  ▒▓▓▓▓▓▓▒▒▒░░░░░    ░ ░░░▒░░▒▒▒▒▒▒ ▒▓▒▒▒▒▒▒▒▒▒
            # ▓░░░░░░░▒▒▓▓▓  ▒█▒  ▒▒▓▒▒▒▒▒▒░░░░ ░░░   ░ ░ ▒░▒▒▒▒▒░░▒▓▒▒▒▒▒▒▒▓▒
            # ▒▒░░░▒▒▒▒▓▒▒▓▒░ ░▒▒▒▒▓▒▒▒▒▒▒▒▒▒▒▒▓▓▓▓▒▒▓▓▓▓▒░▒▒▒▒▒░░▒▓▒▒▒▒▒▒▒▓▒▒
            # ▓▒▒▒▓▓▓▓▓▒▒▒▒▒▓▓▒▓██▓▓▓▒▒▒▒▒░░▒▒▒▒░░░▒▒░░▒▒▓▒░░▒▓▓▓▒▓▓▒▒▒▒▒▒▒▒▒▒
            # ▓▒▓▓▓▓▒▒▒▒▒▒▒▒▒▒▓▓▒▓▓▓▓▓▒▒▒▒░░░░░░▒▒▒▒▒▒░░ ░▒░░▒▒▒▒▒▒▒▒▒▒▓▒▓▓▓▓▒
            # ▓▒▒▒▒▒▓▓▓▒▓▓▓▓▓▓▓▒▒▒▓▓▓▓▓▒▒▒░░░░░░░     ░░░░░▒▒▓▒▒▒▒▒▒▒▒▓▓▓▓▓▓▓▓
            # ▓▓▓▓▓▓▓▓▒▒▒▒▒▓▓▓▒▓▒▒▓▓▓▓▓▓▓▒▒▒░░░░░░     ░░▒▒▒▒▓▒▒▒▒▒▒▒▓▒▒▓▓▓▓▓▓
            # ▓▓▓▓▓▓▓▒▒▒▒▓▓▓▓▒▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒░░▒▒░░░▒▒▓▓▓▒▒█▓▒▓▒▒▒▓▓▒▒▓▓▓▓▓▓
            # █▓▓▓▓▒▒▓▓▓▓▓▓▓▓▓▒▓▓▓▓▓▓██▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓▓▓▒▒░█▓▓▓▓▓▒▒▒▒▒▒▓▓▓▓▓
            # ▓▓▓▒▒▒▒▒▓▓▓▓▓▒▓▓▓▒▒▒▒▒ ░▓▓▓▓▓▓▓▓▓██▓█▓▓▓▒▓▒░░░ ▓▓▒▓▒▒▒▒▒▒▒▒▒▓▓▓▒
            #
            #                         IN MEMORIAM
            #     tag_ids_to_trunkward_additional_implication_work_weight
            #
            
            # I am now moving to table row addition/subtraction. we'll try to move one row at a time and do the smallest amount of work
            
            # There are potential multi-row optimisations here to reduce total work amount. Stuff like reordering existing chains, reassigning siblings.
            # e.g. if sibling A->B moves to A->C, we now go:
            # rescind A->B sibling: remove A->B, add A->A implications
            # add A->C sibling: remove A->A, add A->C implications
            # However, multi-row tech requires mixing removes and adds, which means we again stray into Hell Logic Zone 3000. We'll put the thought off.
            
            # I can always remove a sibling row from actual and stay valid. this does not invalidate ideals in parents table
            # I can always remove a parent row from actual and stay valid
            
            # I know I can copy a parent to actual if the tags aren't in any pending removes
            # I know I can copy a sibling to actual if the tags aren't in any pending removes (I would if there were pending removes indicating merges or something, but there won't be!)
            
            # we will remove surplus rows from actual and then add needed rows
            
            # There may be multi-row optimisations here to reduce total work amount, I am not sure. Probably for stuff like reordering existing chains. It probably requires mixing removes and adds, which means we stray into hell logic mode, so we'll put the thought off.
            
            # If we need to remove 1,000 mappings and then add 500 to be correct, we'll be doing 1,500 total no matter the order we do them in. This 1,000/500 is not the sum of all the current rows' individual current estimated work.
            # When removing, the sum overestimates, when adding, the sum underestimates. The number of sibling/parent rows to change is obviously also the same.
            
            # When you remove a row, the other row estimates may stay as weighty, or they may get less. (e.g. removing sibling A->B makes the parent B->C easier to remove later)
            # When you add a row, the other row estimates may stay as weighty, or they may get more. (e.g. adding parent A->B makes adding the sibling b->B more difficult later on)
            
            # The main priority of this function is to reduce each piece of work time.
            # When removing, we can break down the large jobs by doing small jobs. So, by doing small jobs first, we reduce max job time.
            # However, if we try that strategy when adding, we actually increase max job time, as those delayed big jobs only have the option of staying the same or getting bigger! We get zoom speed and then clunk mode.
            # Therefore, when adding, to limit max work time for the whole migration, we want to actually choose the largest jobs first! That work has to be done, and it doesn't get easier!
            
            ( cache_ideal_tag_siblings_lookup_table_name, cache_actual_tag_siblings_lookup_table_name ) = ClientDBTagSiblings.GenerateTagSiblingsLookupCacheTableNames( tag_service_id )
            ( cache_ideal_tag_parents_lookup_table_name, cache_actual_tag_parents_lookup_table_name ) = ClientDBTagParents.GenerateTagParentsLookupCacheTableNames( tag_service_id )
            
            def GetWeightedSiblingRow( sibling_rows, index ):
                
                # when you change the sibling A->B in the _lookup table_:
                # you need to add/remove about A number of mappings for B and all it implies. the weight is: A * count( all the B->X implications )
                
                ideal_tag_ids = { ideal_tag_id for ( bad_tag_id, ideal_tag_id ) in sibling_rows }
                
                ideal_tag_ids_to_implies = self.modules_tag_display.GetTagsToImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, ideal_tag_ids )
                
                bad_tag_ids = { bad_tag_id for ( bad_tag_id, ideal_tag ) in sibling_rows }
                
                bad_tag_ids_to_count = self.modules_mappings_counts.GetCountsEstimate( ClientTags.TAG_DISPLAY_STORAGE, tag_service_id, self.modules_services.combined_file_service_id, bad_tag_ids, True, True )
                
                weight_and_rows = [ ( bad_tag_ids_to_count[ b ] * len( ideal_tag_ids_to_implies[ i ] ) + 1, ( b, i ) ) for ( b, i ) in sibling_rows ]
                
                weight_and_rows.sort()
                
                return weight_and_rows[ index ]
                
            
            def GetWeightedParentRow( parent_rows, index ):
                
                # when you change the parent A->B in the _lookup table_:
                # you need to add/remove mappings (of B) for all instances of A and all that implies it. the weight is: sum( all the X->A implications )
                
                child_tag_ids = { c for ( c, a ) in parent_rows }
                
                child_tag_ids_to_implied_by = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, child_tag_ids )
                
                all_child_tags = set( child_tag_ids )
                all_child_tags.update( itertools.chain.from_iterable( child_tag_ids_to_implied_by.values() ) )
                
                child_tag_ids_to_count = self.modules_mappings_counts.GetCountsEstimate( ClientTags.TAG_DISPLAY_STORAGE, tag_service_id, self.modules_services.combined_file_service_id, all_child_tags, True, True )
                
                weight_and_rows = [ ( sum( ( child_tag_ids_to_count[ implied_by ] for implied_by in child_tag_ids_to_implied_by[ c ] ) ), ( c, p ) ) for ( c, p ) in parent_rows ]
                
                weight_and_rows.sort()
                
                return weight_and_rows[ index ]
                
            
            # first up, the removees. what is in actual but not ideal
            
            some_removee_sibling_rows = HydrusData.SampleSetByGettingFirst( sibling_rows_to_remove, 20 )
            some_removee_parent_rows = HydrusData.SampleSetByGettingFirst( parent_rows_to_remove, 20 )
            
            possibly_affected_tag_ids = set()
            
            if len( some_removee_sibling_rows ) + len( some_removee_parent_rows ) > 0:
                
                smallest_sibling_weight = None
                smallest_sibling_row = None
                smallest_parent_weight = None
                smallest_parent_row = None
                
                if len( some_removee_sibling_rows ) > 0:
                    
                    ( smallest_sibling_weight, smallest_sibling_row ) = GetWeightedSiblingRow( some_removee_sibling_rows, 0 )
                    
                
                if len( some_removee_parent_rows ) > 0:
                    
                    ( smallest_parent_weight, smallest_parent_row ) = GetWeightedParentRow( some_removee_parent_rows, 0 )
                    
                
                if smallest_sibling_weight is not None and smallest_parent_weight is not None:
                    
                    if smallest_sibling_weight < smallest_parent_weight:
                        
                        smallest_parent_weight = None
                        smallest_parent_row = None
                        
                    else:
                        
                        smallest_sibling_weight = None
                        smallest_sibling_row = None
                        
                    
                
                if smallest_sibling_row is not None:
                    
                    # the only things changed here are those implied by or that imply one of these values
                    
                    ( a, b ) = smallest_sibling_row
                    
                    possibly_affected_tag_ids = { a, b }
                    
                    # when you delete a sibling, impliesA and impliedbyA should be subsets of impliesB and impliedbyB
                    # but let's do everything anyway, just in case of invalid cache or something
                    
                    possibly_affected_tag_ids.update( self.modules_tag_display.GetImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, a ) )
                    possibly_affected_tag_ids.update( self.modules_tag_display.GetImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, b ) )
                    possibly_affected_tag_ids.update( self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, a ) )
                    possibly_affected_tag_ids.update( self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, b ) )
                    
                    previous_chain_tag_ids_to_implied_by = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, possibly_affected_tag_ids )
                    
                    self._Execute( 'DELETE FROM {} WHERE bad_tag_id = ? AND ideal_tag_id = ?;'.format( cache_actual_tag_siblings_lookup_table_name ), smallest_sibling_row )
                    
                    after_chain_tag_ids_to_implied_by = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, possibly_affected_tag_ids )
                    
                    self.modules_tag_siblings.NotifySiblingDeleteRowSynced( tag_service_id, smallest_sibling_row )
                    
                
                if smallest_parent_row is not None:
                    
                    # the only things changed here are those implied by or that imply one of these values
                    
                    ( a, b ) = smallest_parent_row
                    
                    possibly_affected_tag_ids = { a, b }
                    
                    possibly_affected_tag_ids.update( self.modules_tag_display.GetImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, a ) )
                    possibly_affected_tag_ids.update( self.modules_tag_display.GetImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, b ) )
                    possibly_affected_tag_ids.update( self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, a ) )
                    possibly_affected_tag_ids.update( self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, b ) )
                    
                    previous_chain_tag_ids_to_implied_by = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, possibly_affected_tag_ids )
                    
                    self._Execute( 'DELETE FROM {} WHERE child_tag_id = ? AND ancestor_tag_id = ?;'.format( cache_actual_tag_parents_lookup_table_name ), smallest_parent_row )
                    
                    after_chain_tag_ids_to_implied_by = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, possibly_affected_tag_ids )
                    
                    self.modules_tag_parents.NotifyParentDeleteRowSynced( tag_service_id, smallest_parent_row )
                    
                
            else:
                
                # there is nothing to remove, so we'll now go for what is in ideal but not actual
                
                some_addee_sibling_rows = HydrusData.SampleSetByGettingFirst( sibling_rows_to_add, 20 )
                some_addee_parent_rows = HydrusData.SampleSetByGettingFirst( parent_rows_to_add, 20 )
                
                if len( some_addee_sibling_rows ) + len( some_addee_parent_rows ) > 0:
                    
                    largest_sibling_weight = None
                    largest_sibling_row = None
                    largest_parent_weight = None
                    largest_parent_row = None
                    
                    if len( some_addee_sibling_rows ) > 0:
                        
                        ( largest_sibling_weight, largest_sibling_row ) = GetWeightedSiblingRow( some_addee_sibling_rows, -1 )
                        
                    
                    if len( some_addee_parent_rows ) > 0:
                        
                        ( largest_parent_weight, largest_parent_row ) = GetWeightedParentRow( some_addee_parent_rows, -1 )
                        
                    
                    if largest_sibling_weight is not None and largest_parent_weight is not None:
                        
                        if largest_sibling_weight > largest_parent_weight:
                            
                            largest_parent_weight = None
                            largest_parent_row = None
                            
                        else:
                            
                            largest_sibling_weight = None
                            largest_sibling_row = None
                            
                        
                    
                    if largest_sibling_row is not None:
                        
                        # the only things changed here are those implied by or that imply one of these values
                        
                        ( a, b ) = largest_sibling_row
                        
                        possibly_affected_tag_ids = { a, b }
                        
                        possibly_affected_tag_ids.update( self.modules_tag_display.GetImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, a ) )
                        possibly_affected_tag_ids.update( self.modules_tag_display.GetImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, b ) )
                        possibly_affected_tag_ids.update( self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, a ) )
                        possibly_affected_tag_ids.update( self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, b ) )
                        
                        previous_chain_tag_ids_to_implied_by = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, possibly_affected_tag_ids )
                        
                        self._Execute( 'INSERT OR IGNORE INTO {} ( bad_tag_id, ideal_tag_id ) VALUES ( ?, ? );'.format( cache_actual_tag_siblings_lookup_table_name ), largest_sibling_row )
                        
                        after_chain_tag_ids_to_implied_by = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, possibly_affected_tag_ids )
                        
                        self.modules_tag_siblings.NotifySiblingAddRowSynced( tag_service_id, largest_sibling_row )
                        
                    
                    if largest_parent_row is not None:
                        
                        # the only things changed here are those implied by or that imply one of these values
                        
                        ( a, b ) = largest_parent_row
                        
                        possibly_affected_tag_ids = { a, b }
                        
                        possibly_affected_tag_ids.update( self.modules_tag_display.GetImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, a ) )
                        possibly_affected_tag_ids.update( self.modules_tag_display.GetImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, b ) )
                        possibly_affected_tag_ids.update( self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, a ) )
                        possibly_affected_tag_ids.update( self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, b ) )
                        
                        previous_chain_tag_ids_to_implied_by = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, possibly_affected_tag_ids )
                        
                        self._Execute( 'INSERT OR IGNORE INTO {} ( child_tag_id, ancestor_tag_id ) VALUES ( ?, ? );'.format( cache_actual_tag_parents_lookup_table_name ), largest_parent_row )
                        
                        after_chain_tag_ids_to_implied_by = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, possibly_affected_tag_ids )
                        
                        self.modules_tag_parents.NotifyParentAddRowSynced( tag_service_id, largest_parent_row )
                        
                    
                else:
                    
                    break
                    
                
            
            #
            
            tag_ids_to_delete_implied_by = collections.defaultdict( set )
            tag_ids_to_add_implied_by = collections.defaultdict( set )
            
            for tag_id in possibly_affected_tag_ids:
                
                previous_implied_by = previous_chain_tag_ids_to_implied_by[ tag_id ]
                after_implied_by = after_chain_tag_ids_to_implied_by[ tag_id ]
                
                to_delete = previous_implied_by.difference( after_implied_by )
                to_add = after_implied_by.difference( previous_implied_by )
                
                if len( to_delete ) > 0:
                    
                    tag_ids_to_delete_implied_by[ tag_id ] = to_delete
                    
                    all_tag_ids_altered.add( tag_id )
                    all_tag_ids_altered.update( to_delete )
                    
                
                if len( to_add ) > 0:
                    
                    tag_ids_to_add_implied_by[ tag_id ] = to_add
                    
                    all_tag_ids_altered.add( tag_id )
                    all_tag_ids_altered.update( to_add )
                    
                
            
            # now do the implications
            
            # if I am feeling very clever, I could potentially add tag_ids_to_migrate_implied_by, which would be an UPDATE
            # this would only work for tag_ids that have the same current implied by in actual and ideal (e.g. moving a tag sibling from A->B to B->A)
            # may be better to do this in a merged add/deleteimplication function that would be able to well detect this with 'same current implied' of count > 0 for that domain
            
            file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
            
            for file_service_id in file_service_ids:
                
                for ( tag_id, implication_tag_ids ) in tag_ids_to_delete_implied_by.items():
                    
                    self.modules_mappings_cache_specific_display.DeleteImplications( file_service_id, tag_service_id, implication_tag_ids, tag_id )
                    
                
                for ( tag_id, implication_tag_ids ) in tag_ids_to_add_implied_by.items():
                    
                    self.modules_mappings_cache_specific_display.AddImplications( file_service_id, tag_service_id, implication_tag_ids, tag_id )
                    
                
            
            for ( tag_id, implication_tag_ids ) in tag_ids_to_delete_implied_by.items():
                
                self.modules_mappings_cache_combined_files_display.DeleteImplications( tag_service_id, implication_tag_ids, tag_id )
                
            
            for ( tag_id, implication_tag_ids ) in tag_ids_to_add_implied_by.items():
                
                self.modules_mappings_cache_combined_files_display.AddImplications( tag_service_id, implication_tag_ids, tag_id )
                
            
            ( sibling_rows_to_add, sibling_rows_to_remove, parent_rows_to_add, parent_rows_to_remove, num_actual_rows, num_ideal_rows ) = self.modules_tag_display.GetApplicationStatus( tag_service_id )
            
        
        if len( all_tag_ids_altered ) > 0:
            
            self._regen_tags_managers_tag_ids.update( all_tag_ids_altered )
            
            self._CacheTagsSyncTags( tag_service_id, all_tag_ids_altered )
            
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_tag_display_sync_status', service_key )
            
        
        still_needs_work = len( sibling_rows_to_add ) + len( sibling_rows_to_remove ) + len( parent_rows_to_add ) + len( parent_rows_to_remove ) > 0
        
        return still_needs_work
        
    
    def _CacheTagsPopulate( self, file_service_id, tag_service_id, status_hook = None ):
        
        siblings_table_name = ClientDBTagSiblings.GenerateTagSiblingsLookupCacheTableName( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id )
        parents_table_name = ClientDBTagParents.GenerateTagParentsLookupCacheTableName( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id )
        
        queries = [
            self.modules_mappings_counts.GetQueryPhraseForCurrentTagIds( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id ),
            'SELECT DISTINCT bad_tag_id FROM {}'.format( siblings_table_name ),
            'SELECT ideal_tag_id FROM {}'.format( siblings_table_name ),
            'SELECT DISTINCT child_tag_id FROM {}'.format( parents_table_name ),
            'SELECT DISTINCT ancestor_tag_id FROM {}'.format( parents_table_name )
        ]
        
        full_query = '{};'.format( ' UNION '.join( queries ) )
        
        BLOCK_SIZE = 10000
        
        for ( group_of_tag_ids, num_done, num_to_do ) in HydrusDB.ReadLargeIdQueryInSeparateChunks( self._c, full_query, BLOCK_SIZE ):
            
            self.modules_tag_search.AddTags( file_service_id, tag_service_id, group_of_tag_ids )
            
            message = HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do )
            
            self._controller.frame_splash_status.SetSubtext( message )
            
            if status_hook is not None:
                
                status_hook( message )
                
            
        
        self.modules_db_maintenance.TouchAnalyzeNewTables()
        
    
    def _CacheTagsSyncTags( self, tag_service_id, tag_ids, just_these_file_service_ids = None ):
        
        if len( tag_ids ) == 0:
            
            return
            
        
        if just_these_file_service_ids is None:
            
            file_service_ids = list( self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES ) )
            
            file_service_ids.append( self.modules_services.combined_file_service_id )
            
        else:
            
            file_service_ids = just_these_file_service_ids
            
        
        chained_tag_ids = self.modules_tag_display.FilterChained( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, tag_ids )
        unchained_tag_ids = { tag_id for tag_id in tag_ids if tag_id not in chained_tag_ids }
        
        with self._MakeTemporaryIntegerTable( tag_ids, 'tag_id' ) as temp_tag_ids_table_name:
            
            with self._MakeTemporaryIntegerTable( unchained_tag_ids, 'tag_id' ) as temp_unchained_tag_ids_table_name:
                
                for file_service_id in file_service_ids:
                    
                    exist_in_tag_search_tag_ids = self.modules_tag_search.FilterExistingTagIds( file_service_id, tag_service_id, temp_tag_ids_table_name )
                    
                    exist_in_counts_cache_tag_ids = self.modules_mappings_counts.FilterExistingTagIds( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, temp_unchained_tag_ids_table_name  )
                    
                    should_have = chained_tag_ids.union( exist_in_counts_cache_tag_ids )
                    
                    should_not_have = unchained_tag_ids.difference( exist_in_counts_cache_tag_ids )
                    
                    should_add = should_have.difference( exist_in_tag_search_tag_ids )
                    should_delete = exist_in_tag_search_tag_ids.intersection( should_not_have )
                    
                    self.modules_tag_search.AddTags( file_service_id, tag_service_id, should_add )
                    self.modules_tag_search.DeleteTags( file_service_id, tag_service_id, should_delete )
                    
                
            
        
    
    def _CheckDBIntegrity( self ):
        
        prefix_string = 'checking db integrity: '
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        try:
            
            job_key.SetStatusTitle( prefix_string + 'preparing' )
            
            self._controller.pub( 'modal_message', job_key )
            
            num_errors = 0
            
            job_key.SetStatusTitle( prefix_string + 'running' )
            job_key.SetStatusText( 'errors found so far: ' + HydrusData.ToHumanInt( num_errors ) )
            
            db_names = [ name for ( index, name, path ) in self._Execute( 'PRAGMA database_list;' ) if name not in ( 'mem', 'temp', 'durable_temp' ) ]
            
            for db_name in db_names:
                
                for ( text, ) in self._Execute( 'PRAGMA ' + db_name + '.integrity_check;' ):
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit:
                        
                        job_key.SetStatusTitle( prefix_string + 'cancelled' )
                        job_key.SetStatusText( 'errors found: ' + HydrusData.ToHumanInt( num_errors ) )
                        
                        return
                        
                    
                    if text != 'ok':
                        
                        if num_errors == 0:
                            
                            HydrusData.Print( 'During a db integrity check, these errors were discovered:' )
                            
                        
                        HydrusData.Print( text )
                        
                        num_errors += 1
                        
                    
                    job_key.SetStatusText( 'errors found so far: ' + HydrusData.ToHumanInt( num_errors ) )
                    
                
            
        finally:
            
            job_key.SetStatusTitle( prefix_string + 'completed' )
            job_key.SetStatusText( 'errors found: ' + HydrusData.ToHumanInt( num_errors ) )
            
            HydrusData.Print( job_key.ToString() )
            
            job_key.Finish()
            
        
    
    def _CleanAfterJobWork( self ):
        
        self._after_job_content_update_jobs = []
        self._regen_tags_managers_hash_ids = set()
        self._regen_tags_managers_tag_ids = set()
        
        HydrusDB.HydrusDB._CleanAfterJobWork( self )
        
    
    def _ClearOrphanFileRecords( self ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        job_key.SetStatusTitle( 'clear orphan file records' )
        
        self._controller.pub( 'modal_message', job_key )
        
        orphans_found = False
        
        try:
            
            job_key.SetStatusText( 'looking for orphans' )
            
            jobs = [
                ( ( HC.LOCAL_FILE_DOMAIN, ), self.modules_services.combined_local_media_service_id, 'my files umbrella' ),
                ( ( HC.LOCAL_FILE_TRASH_DOMAIN, HC.COMBINED_LOCAL_MEDIA, HC.LOCAL_FILE_UPDATE_DOMAIN, ), self.modules_services.combined_local_file_service_id, 'local files umbrella' )
            ]
            
            for ( umbrella_components_service_types, umbrella_master_service_id, description ) in jobs:
                
                umbrella_components_service_ids = self.modules_services.GetServiceIds( umbrella_components_service_types )
                
                umbrella_components_hash_ids = set()
                
                for umbrella_components_service_id in umbrella_components_service_ids:
                    
                    umbrella_components_hash_ids.update( self.modules_files_storage.GetCurrentHashIdsList( umbrella_components_service_id ) )
                    
                
                umbrella_master_hash_ids = set( self.modules_files_storage.GetCurrentHashIdsList( umbrella_master_service_id ) )
                
                in_components_not_in_master = umbrella_components_hash_ids.difference( umbrella_master_hash_ids )
                in_master_not_in_components = umbrella_master_hash_ids.difference( umbrella_components_hash_ids )
                
                if job_key.IsCancelled():
                    
                    return
                    
                
                job_key.SetStatusText( 'deleting orphans' )
                
                if len( in_components_not_in_master ) > 0:
                    
                    orphans_found = True
                    
                    # these files were deleted from the umbrella service without being cleared from a specific file domain
                    # they are most likely deleted from disk
                    # pushing the master's delete call will flush from the components as well
                    
                    self._DeleteFiles( umbrella_master_service_id, in_components_not_in_master )
                    
                    # we spam this stuff since it won't trigger if the files don't exist on master!
                    self.modules_files_inbox.ArchiveFiles( in_components_not_in_master )
                    
                    for hash_id in in_components_not_in_master:
                        
                        self.modules_similar_files.StopSearchingFile( hash_id )
                        
                    
                    self.modules_files_maintenance_queue.CancelFiles( in_components_not_in_master )
                    
                    self.modules_hashes_local_cache.DropHashIdsFromCache( in_components_not_in_master )
                    
                    HydrusData.ShowText( 'Found and deleted {} files that were in components but not the master {}.'.format( HydrusData.ToHumanInt( len( in_components_not_in_master ) ), description ) )
                    
                
                if job_key.IsCancelled():
                    
                    return
                    
                
                if len( in_master_not_in_components ) > 0:
                    
                    orphans_found = True
                    
                    # these files were deleted from all specific services but not from the combined service
                    # I have only ever seen one example of this and am not sure how it happened
                    # in any case, the same 'delete combined' call will do the job
                    
                    self._DeleteFiles( umbrella_master_service_id, in_master_not_in_components )
                    
                    HydrusData.ShowText( 'Found and deleted {} files that were in the master {} but not it its components.'.format( HydrusData.ToHumanInt( len( in_master_not_in_components ) ), description ) )
                    
                
            
            if orphans_found:
                
                for service_id in self.modules_services.GetServiceIds( HC.LOCAL_FILE_SERVICES ):
                    
                    self._Execute( 'DELETE FROM service_info WHERE service_id = ?;', ( service_id, ) )
                    
                
            else:
                
                HydrusData.ShowText( 'No orphan file records found!' )
                
            
        finally:
            
            job_key.SetStatusText( 'done!' )
            
            job_key.Finish()
            
        
    
    def _ClearOrphanTables( self ):
        
        all_table_names = set()
        
        db_names = [ name for ( index, name, path ) in self._Execute( 'PRAGMA database_list;' ) if name not in ( 'mem', 'temp', 'durable_temp' ) ]
        
        for db_name in db_names:
            
            table_names = self._STS( self._Execute( 'SELECT name FROM {}.sqlite_master WHERE type = ?;'.format( db_name ), ( 'table', ) ) )
            
            if db_name != 'main':
                
                table_names = { '{}.{}'.format( db_name, table_name ) for table_name in table_names }
                
            
            all_table_names.update( table_names )
            
        
        all_surplus_table_names = set()
        
        for module in self._modules:
            
            surplus_table_names = module.GetSurplusServiceTableNames( all_table_names )
            
            all_surplus_table_names.update( surplus_table_names )
            
        
        if len( surplus_table_names ) == 0:
            
            HydrusData.ShowText( 'No orphan tables!' )
            
        
        for table_name in surplus_table_names:
            
            HydrusData.ShowText( 'Dropping ' + table_name )
            
            self._Execute( 'DROP table ' + table_name + ';' )
            
        
    
    def _CreateDB( self ):
        
        # main
        
        for module in self._modules:
            
            module.CreateInitialTables()
            module.CreateInitialIndices()
            
        
        # intentionally not IF NOT EXISTS here, to catch double-creation accidents early and on a good table
        self._Execute( 'CREATE TABLE version ( version INTEGER );' )
        
        #
        
        self._Execute( 'CREATE TABLE IF NOT EXISTS local_ratings ( service_id INTEGER, hash_id INTEGER, rating REAL, PRIMARY KEY ( service_id, hash_id ) );' )
        self._CreateIndex( 'local_ratings', [ 'hash_id' ] )
        self._CreateIndex( 'local_ratings', [ 'rating' ] )
        
        self._Execute( 'CREATE TABLE IF NOT EXISTS local_incdec_ratings ( service_id INTEGER, hash_id INTEGER, rating INTEGER, PRIMARY KEY ( service_id, hash_id ) );' )
        self._CreateIndex( 'local_incdec_ratings', [ 'hash_id' ] )
        self._CreateIndex( 'local_incdec_ratings', [ 'rating' ] )
        
        self._Execute( 'CREATE TABLE IF NOT EXISTS file_modified_timestamps ( hash_id INTEGER PRIMARY KEY, file_modified_timestamp INTEGER );' )
        self._CreateIndex( 'file_modified_timestamps', [ 'file_modified_timestamp' ] )
        
        self._Execute( 'CREATE TABLE IF NOT EXISTS options ( options TEXT_YAML );', )
        
        self._Execute( 'CREATE TABLE IF NOT EXISTS recent_tags ( service_id INTEGER, tag_id INTEGER, timestamp INTEGER, PRIMARY KEY ( service_id, tag_id ) );' )
        
        self._Execute( 'CREATE TABLE IF NOT EXISTS remote_thumbnails ( service_id INTEGER, hash_id INTEGER, PRIMARY KEY( service_id, hash_id ) );' )
        
        self._Execute( 'CREATE TABLE IF NOT EXISTS service_info ( service_id INTEGER, info_type INTEGER, info INTEGER, PRIMARY KEY ( service_id, info_type ) );' )
        
        self._Execute( 'CREATE TABLE IF NOT EXISTS statuses ( status_id INTEGER PRIMARY KEY, status TEXT UNIQUE );' )
        
        # inserts
        
        self.modules_files_physical_storage.Initialise()
        
        init_service_info = [
            ( CC.COMBINED_TAG_SERVICE_KEY, HC.COMBINED_TAG, 'all known tags' ),
            ( CC.COMBINED_FILE_SERVICE_KEY, HC.COMBINED_FILE, 'all known files' ),
            ( CC.COMBINED_DELETED_FILE_SERVICE_KEY, HC.COMBINED_DELETED_FILE, 'all deleted files' ),
            ( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, HC.COMBINED_LOCAL_FILE, 'all local files' ),
            ( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY, HC.COMBINED_LOCAL_MEDIA, 'all my files' ),
            ( CC.LOCAL_FILE_SERVICE_KEY, HC.LOCAL_FILE_DOMAIN, 'my files' ),
            ( CC.LOCAL_UPDATE_SERVICE_KEY, HC.LOCAL_FILE_UPDATE_DOMAIN, 'repository updates' ),
            ( CC.TRASH_SERVICE_KEY, HC.LOCAL_FILE_TRASH_DOMAIN, 'trash' ),
            ( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, HC.LOCAL_TAG, 'my tags' ),
            ( CC.DEFAULT_LOCAL_DOWNLOADER_TAG_SERVICE_KEY, HC.LOCAL_TAG, 'downloader tags' ),
            ( CC.LOCAL_BOORU_SERVICE_KEY, HC.LOCAL_BOORU, 'local booru' ),
            ( CC.LOCAL_NOTES_SERVICE_KEY, HC.LOCAL_NOTES, 'local notes' ),
            ( CC.DEFAULT_FAVOURITES_RATING_SERVICE_KEY, HC.LOCAL_RATING_LIKE, 'favourites' ),
            ( CC.CLIENT_API_SERVICE_KEY, HC.CLIENT_API_SERVICE, 'client api' )
        ]
        
        for ( service_key, service_type, name ) in init_service_info:
            
            dictionary = ClientServices.GenerateDefaultServiceDictionary( service_type )
            
            if service_key == CC.DEFAULT_FAVOURITES_RATING_SERVICE_KEY:
                
                from hydrus.client.metadata import ClientRatings
                
                dictionary[ 'shape' ] = ClientRatings.FAT_STAR
                
                like_colours = {}
                
                like_colours[ ClientRatings.LIKE ] = ( ( 0, 0, 0 ), ( 240, 240, 65 ) )
                like_colours[ ClientRatings.DISLIKE ] = ( ( 0, 0, 0 ), ( 200, 80, 120 ) )
                like_colours[ ClientRatings.NULL ] = ( ( 0, 0, 0 ), ( 191, 191, 191 ) )
                like_colours[ ClientRatings.MIXED ] = ( ( 0, 0, 0 ), ( 95, 95, 95 ) )
                
                dictionary[ 'colours' ] = list( like_colours.items() )
                
            
            self._AddService( service_key, service_type, name, dictionary )
            
        
        self._ExecuteMany( 'INSERT INTO yaml_dumps VALUES ( ?, ?, ? );', ( ( ClientDBSerialisable.YAML_DUMP_ID_IMAGEBOARD, name, imageboards ) for ( name, imageboards ) in ClientDefaults.GetDefaultImageboards() ) )
        
        new_options = ClientOptions.ClientOptions()
        
        new_options.SetSimpleDownloaderFormulae( ClientDefaults.GetDefaultSimpleDownloaderFormulae() )
        
        names_to_tag_filters = {}
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( 'diaper', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'gore', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'guro', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'scat', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'vore', HC.FILTER_BLACKLIST )
        
        names_to_tag_filters[ 'example blacklist' ] = tag_filter
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( '', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( ':', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'series:', HC.FILTER_WHITELIST )
        tag_filter.SetRule( 'creator:', HC.FILTER_WHITELIST )
        tag_filter.SetRule( 'studio:', HC.FILTER_WHITELIST )
        tag_filter.SetRule( 'character:', HC.FILTER_WHITELIST )
        
        names_to_tag_filters[ 'basic namespaces only' ] = tag_filter
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( ':', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'series:', HC.FILTER_WHITELIST )
        tag_filter.SetRule( 'creator:', HC.FILTER_WHITELIST )
        tag_filter.SetRule( 'studio:', HC.FILTER_WHITELIST )
        tag_filter.SetRule( 'character:', HC.FILTER_WHITELIST )
        
        names_to_tag_filters[ 'basic booru tags only' ] = tag_filter
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( 'title:', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'filename:', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'source:', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'booru:', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'url:', HC.FILTER_BLACKLIST )
        
        names_to_tag_filters[ 'exclude long/spammy namespaces' ] = tag_filter
        
        new_options.SetFavouriteTagFilters( names_to_tag_filters )
        
        self.modules_serialisable.SetJSONDump( new_options )
        
        list_of_shortcuts = ClientDefaults.GetDefaultShortcuts()
        
        for shortcuts in list_of_shortcuts:
            
            self.modules_serialisable.SetJSONDump( shortcuts )
            
        
        client_api_manager = ClientAPI.APIManager()
        
        self.modules_serialisable.SetJSONDump( client_api_manager )
        
        bandwidth_manager = ClientNetworkingBandwidth.NetworkBandwidthManager()
        
        bandwidth_manager.SetDirty()
        
        ClientDefaults.SetDefaultBandwidthManagerRules( bandwidth_manager )
        
        self.modules_serialisable.SetJSONDump( bandwidth_manager )
        
        domain_manager = ClientNetworkingDomain.NetworkDomainManager()
        
        ClientDefaults.SetDefaultDomainManagerData( domain_manager )
        
        self.modules_serialisable.SetJSONDump( domain_manager )
        
        session_manager = ClientNetworkingSessions.NetworkSessionManager()
        
        session_manager.SetDirty()
        
        self.modules_serialisable.SetJSONDump( session_manager )
        
        login_manager = ClientNetworkingLogin.NetworkLoginManager()
        
        ClientDefaults.SetDefaultLoginManagerScripts( login_manager )
        
        self.modules_serialisable.SetJSONDump( login_manager )
        
        favourite_search_manager = ClientSearch.FavouriteSearchManager()
        
        ClientDefaults.SetDefaultFavouriteSearchManagerData( favourite_search_manager )
        
        self.modules_serialisable.SetJSONDump( favourite_search_manager )
        
        tag_display_manager = ClientTagsHandling.TagDisplayManager()
        
        self.modules_serialisable.SetJSONDump( tag_display_manager )
        
        from hydrus.client.gui.lists import ClientGUIListManager
        
        column_list_manager = ClientGUIListManager.ColumnListManager()
        
        self.modules_serialisable.SetJSONDump( column_list_manager )
        
        self._Execute( 'INSERT INTO namespaces ( namespace_id, namespace ) VALUES ( ?, ? );', ( 1, '' ) )
        
        self._Execute( 'INSERT INTO version ( version ) VALUES ( ? );', ( HC.SOFTWARE_VERSION, ) )
        
        self._ExecuteMany( 'INSERT INTO json_dumps_named VALUES ( ?, ?, ?, ?, ? );', ClientDefaults.GetDefaultScriptRows() )
        
    
    def _DeleteFiles( self, service_id, hash_ids, only_if_current = False ):
        
        local_file_service_ids = self.modules_services.GetServiceIds( ( HC.LOCAL_FILE_DOMAIN, ) )
        
        # we go nuclear on the umbrella services, being very explicit to catch every possible problem
        
        if service_id == self.modules_services.combined_local_file_service_id:
            
            for local_file_service_id in local_file_service_ids:
                
                self._DeleteFiles( local_file_service_id, hash_ids, only_if_current = True )
                
            
            self._DeleteFiles( self.modules_services.combined_local_media_service_id, hash_ids, only_if_current = True )
            
            self._DeleteFiles( self.modules_services.local_update_service_id, hash_ids, only_if_current = True )
            self._DeleteFiles( self.modules_services.trash_service_id, hash_ids, only_if_current = True )
            
        
        if service_id == self.modules_services.combined_local_media_service_id:
            
            for local_file_service_id in local_file_service_ids:
                
                self._DeleteFiles( local_file_service_id, hash_ids, only_if_current = True )
                
            
        
        service = self.modules_services.GetService( service_id )
        
        service_type = service.GetServiceType()
        
        existing_hash_ids_to_timestamps = self.modules_files_storage.GetCurrentHashIdsToTimestamps( service_id, hash_ids )
        
        existing_hash_ids = set( existing_hash_ids_to_timestamps.keys() )
        
        service_info_updates = []
        
        # do delete outside, file repos and perhaps some other bananas situation can delete without ever having added
        
        now = HydrusData.GetNow()
        
        if service_type not in HC.FILE_SERVICES_WITH_NO_DELETE_RECORD:
            
            # make a deletion record
            
            if only_if_current:
                
                deletion_record_hash_ids = existing_hash_ids
                
            else:
                
                deletion_record_hash_ids = hash_ids
                
            
            if len( deletion_record_hash_ids ) > 0:
                
                insert_rows = [ ( hash_id, existing_hash_ids_to_timestamps[ hash_id ] if hash_id in existing_hash_ids_to_timestamps else None ) for hash_id in deletion_record_hash_ids ]
                
                num_new_deleted_files = self.modules_files_storage.RecordDeleteFiles( service_id, insert_rows )
                
                service_info_updates.append( ( num_new_deleted_files, service_id, HC.SERVICE_INFO_NUM_DELETED_FILES ) )
                
            
        
        if len( existing_hash_ids ) > 0:
            
            # remove them from the service
            
            pending_changed = self.modules_files_storage.RemoveFiles( service_id, existing_hash_ids )
            
            if pending_changed:
                
                self._cursor_transaction_wrapper.pub_after_job( 'notify_new_pending' )
                
            
            delta_size = self.modules_files_metadata_basic.GetTotalSize( existing_hash_ids )
            num_viewable_files = self.modules_files_metadata_basic.GetNumViewable( existing_hash_ids )
            num_existing_files_removed = len( existing_hash_ids )
            num_inbox = len( existing_hash_ids.intersection( self.modules_files_inbox.inbox_hash_ids ) )
            
            service_info_updates.append( ( -delta_size, service_id, HC.SERVICE_INFO_TOTAL_SIZE ) )
            service_info_updates.append( ( -num_viewable_files, service_id, HC.SERVICE_INFO_NUM_VIEWABLE_FILES ) )
            service_info_updates.append( ( -num_existing_files_removed, service_id, HC.SERVICE_INFO_NUM_FILES ) )
            service_info_updates.append( ( -num_inbox, service_id, HC.SERVICE_INFO_NUM_INBOX ) )
            
            # now do special stuff
            
            # if we maintain tag counts for this service, update
            
            if service_type in HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES:
                
                tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                
                with self._MakeTemporaryIntegerTable( existing_hash_ids, 'hash_id' ) as temp_hash_id_table_name:
                    
                    for tag_service_id in tag_service_ids:
                        
                        self.modules_mappings_cache_specific_storage.DeleteFiles( service_id, tag_service_id, existing_hash_ids, temp_hash_id_table_name )
                        
                    
                
            
            # update the combined deleted file service
            
            if service_type in HC.FILE_SERVICES_COVERED_BY_COMBINED_DELETED_FILE:
                
                now = HydrusData.GetNow()
                
                rows = [ ( hash_id, now ) for hash_id in existing_hash_ids ]
                
                self._AddFiles( self.modules_services.combined_deleted_file_service_id, rows )
                
            
            # if any files are no longer in any local file services, remove from the umbrella and send them to the trash
            
            if service_id in local_file_service_ids:
                
                hash_ids_still_in_another_service = set()
                
                other_local_file_service_ids = set( local_file_service_ids )
                other_local_file_service_ids.discard( service_id )
                
                hash_ids_still_in_another_service = self.modules_files_storage.FilterAllCurrentHashIds( existing_hash_ids, just_these_service_ids = other_local_file_service_ids )
                
                trashed_hash_ids = existing_hash_ids.difference( hash_ids_still_in_another_service )
                
                if len( trashed_hash_ids ) > 0:
                    
                    self._DeleteFiles( self.modules_services.combined_local_media_service_id, trashed_hash_ids )
                    
                    now = HydrusData.GetNow()
                    
                    delete_rows = [ ( hash_id, now ) for hash_id in trashed_hash_ids ]
                    
                    self._AddFiles( self.modules_services.trash_service_id, delete_rows )
                    
                
            
            # if we are deleting from repo updates, do a physical delete now
            
            if service_id == self.modules_services.local_update_service_id:
                
                self._DeleteFiles( self.modules_services.combined_local_file_service_id, existing_hash_ids )
                
            
            # if the files are being fully deleted, then physically delete them
            
            if service_id == self.modules_services.combined_local_file_service_id:
                
                self.modules_files_inbox.ArchiveFiles( existing_hash_ids )
                
                for hash_id in existing_hash_ids:
                    
                    self.modules_similar_files.StopSearchingFile( hash_id )
                    
                
                self.modules_files_maintenance_queue.CancelFiles( existing_hash_ids )
                
                self.modules_hashes_local_cache.DropHashIdsFromCache( existing_hash_ids )
                
            
        
        # push the info updates, notify
        
        self._ExecuteMany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', service_info_updates )
        
    
    def _DeletePending( self, service_key ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        service = self.modules_services.GetService( service_id )
        
        if service.GetServiceType() == HC.TAG_REPOSITORY:
            
            ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( service_id )
            
            pending_rescinded_mappings_ids = list( HydrusData.BuildKeyToListDict( self._Execute( 'SELECT tag_id, hash_id FROM ' + pending_mappings_table_name + ';' ) ).items() )
            
            petitioned_rescinded_mappings_ids = list( HydrusData.BuildKeyToListDict( self._Execute( 'SELECT tag_id, hash_id FROM ' + petitioned_mappings_table_name + ';' ) ).items() )
            
            self._UpdateMappings( service_id, pending_rescinded_mappings_ids = pending_rescinded_mappings_ids, petitioned_rescinded_mappings_ids = petitioned_rescinded_mappings_ids )
            
            self._Execute( 'DELETE FROM tag_sibling_petitions WHERE service_id = ?;', ( service_id, ) )
            self._Execute( 'DELETE FROM tag_parent_petitions WHERE service_id = ?;', ( service_id, ) )
            
        elif service.GetServiceType() in ( HC.FILE_REPOSITORY, HC.IPFS ):
            
            self.modules_files_storage.DeletePending( service_id )
            
        
        self._cursor_transaction_wrapper.pub_after_job( 'notify_new_pending' )
        self._cursor_transaction_wrapper.pub_after_job( 'notify_new_tag_display_application' )
        self._cursor_transaction_wrapper.pub_after_job( 'notify_new_force_refresh_tags_data' )
        
        self.pub_service_updates_after_commit( { service_key : [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_DELETE_PENDING ) ] } )
        
    
    def _DeleteService( self, service_id ):
        
        service = self.modules_services.GetService( service_id )
        
        service_key = service.GetServiceKey()
        service_type = service.GetServiceType()
        
        # for a long time, much of this was done with foreign keys, which had to be turned on especially for this operation
        # however, this seemed to cause some immense temp drive space bloat when dropping the mapping tables, as there seems to be a trigger/foreign reference check for every row to be deleted
        # so now we just blat all tables and trust in the Lord that we don't forget to add any new ones in future
        
        self._Execute( 'DELETE FROM local_ratings WHERE service_id = ?;', ( service_id, ) )
        self._Execute( 'DELETE FROM recent_tags WHERE service_id = ?;', ( service_id, ) )
        self._Execute( 'DELETE FROM service_info WHERE service_id = ?;', ( service_id, ) )
        
        self._DeleteServiceDropFilesTables( service_id, service_type )
        
        if service_type in HC.REPOSITORIES:
            
            self.modules_repositories.DropRepositoryTables( service_id )
            
        
        self._DeleteServiceDropMappingsTables( service_id, service_type )
        
        self.modules_services.DeleteService( service_id )
        
        service_update = HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_RESET )
        
        service_keys_to_service_updates = { service_key : [ service_update ] }
        
        self.pub_service_updates_after_commit( service_keys_to_service_updates )
        
    
    def _DeleteServiceDropFilesTables( self, service_id, service_type ):
        
        if service_type == HC.FILE_REPOSITORY:
            
            self._Execute( 'DELETE FROM remote_thumbnails WHERE service_id = ?;', ( service_id, ) )
            
        
        if service_type == HC.IPFS:
            
            self.modules_service_paths.ClearService( service_id )
            
        
        if service_type in HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES:
            
            self.modules_files_storage.DropFilesTables( service_id )
            
        
        if service_type in HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES:
            
            tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
            for tag_service_id in tag_service_ids:
                
                self.modules_mappings_cache_specific_storage.Drop( service_id, tag_service_id )
                
            
        
    
    def _DeleteServiceDropMappingsTables( self, service_id, service_type ):
        
        if service_type in HC.REAL_TAG_SERVICES:
            
            self.modules_mappings_storage.DropMappingsTables( service_id )
            
            self.modules_mappings_cache_combined_files_storage.Drop( service_id )
            
            file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
            
            for file_service_id in file_service_ids:
                
                self.modules_mappings_cache_specific_storage.Drop( file_service_id, service_id )
                
            
            interested_service_ids = set( self.modules_tag_display.GetInterestedServiceIds( service_id ) )
            
            interested_service_ids.discard( service_id ) # lmao, not any more!
            
            self.modules_tag_parents.Drop( service_id )
            
            self.modules_tag_siblings.Drop( service_id )
            
            if len( interested_service_ids ) > 0:
                
                self.modules_tag_display.RegenerateTagSiblingsAndParentsCache( only_these_service_ids = interested_service_ids )
                
            
            self.modules_tag_search.Drop( self.modules_services.combined_file_service_id, service_id )
            
            file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES )
            
            for file_service_id in file_service_ids:
                
                self.modules_tag_search.Drop( file_service_id, service_id )
                
            
        
        if service_type in HC.FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES:
            
            tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
            for tag_service_id in tag_service_ids:
                
                self.modules_tag_search.Drop( service_id, tag_service_id )
                
            
        
    
    def _DeleteServiceInfo( self, service_key = None, types_to_delete = None ):
        
        predicates = []
        
        if service_key is not None:
            
            service_id = self.modules_services.GetServiceId( service_key )
            
            predicates.append( 'service_id = {}'.format( service_id ) )
            
        
        if types_to_delete is not None:
            
            predicates.append( 'info_type IN {}'.format( HydrusData.SplayListForDB( types_to_delete ) ) )
            
        
        if len( predicates ) > 0:
            
            predicates_string = ' WHERE {}'.format( ' AND '.join( predicates ) )
            
        else:
            
            predicates_string = ''
            
        
        self._Execute( 'DELETE FROM service_info{};'.format( predicates_string ) )
        
        self._cursor_transaction_wrapper.pub_after_job( 'notify_new_pending' )
        
    
    def _DisplayCatastrophicError( self, text ):
        
        message = 'The db encountered a serious error! This is going to be written to the log as well, but here it is for a screenshot:'
        message += os.linesep * 2
        message += text
        
        HydrusData.DebugPrint( message )
        
        self._controller.SafeShowCriticalMessage( 'hydrus db failed', message )
        
    
    def _DoAfterJobWork( self ):
        
        for service_keys_to_content_updates in self._after_job_content_update_jobs:
            
            self._weakref_media_result_cache.ProcessContentUpdates( service_keys_to_content_updates )
            
            self._cursor_transaction_wrapper.pub_after_job( 'content_updates_gui', service_keys_to_content_updates )
            
        
        if len( self._regen_tags_managers_hash_ids ) > 0:
            
            hash_ids_to_do = self._weakref_media_result_cache.FilterFiles( self._regen_tags_managers_hash_ids )
            
            if len( hash_ids_to_do ) > 0:
                
                hash_ids_to_tags_managers = self._GetForceRefreshTagsManagers( hash_ids_to_do )
                
                self._weakref_media_result_cache.SilentlyTakeNewTagsManagers( hash_ids_to_tags_managers )
                
            
        
        if len( self._regen_tags_managers_tag_ids ) > 0:
            
            tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = self._regen_tags_managers_tag_ids )
            
            tags = { tag_ids_to_tags[ tag_id ] for tag_id in self._regen_tags_managers_tag_ids }
            
            hash_ids_to_do = self._weakref_media_result_cache.FilterFilesWithTags( tags )
            
            if len( hash_ids_to_do ) > 0:
                
                hash_ids_to_tags_managers = self._GetForceRefreshTagsManagers( hash_ids_to_do )
            
                self._weakref_media_result_cache.SilentlyTakeNewTagsManagers( hash_ids_to_tags_managers )
                
                self._cursor_transaction_wrapper.pub_after_job( 'refresh_all_tag_presentation_gui' )
                
            
        
        HydrusDB.HydrusDB._DoAfterJobWork( self )
        
    
    def _DuplicatesGetRandomPotentialDuplicateHashes(
        self,
        file_search_context_1: ClientSearch.FileSearchContext,
        file_search_context_2: ClientSearch.FileSearchContext,
        dupe_search_type: int,
        pixel_dupes_preference,
        max_hamming_distance
    ) -> typing.List[ bytes ]:
        
        db_location_context = self.modules_files_storage.GetDBLocationContext( file_search_context_1.GetLocationContext() )
        
        chosen_allowed_hash_ids = None
        chosen_preferred_hash_ids = None
        comparison_allowed_hash_ids = None
        comparison_preferred_hash_ids = None
        
        # first we get a sample of current potential pairs in the db, given our limiting search context
        
        with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_1:
            
            with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_2:
                
                if dupe_search_type == CC.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES:
                    
                    query_hash_ids_1 = set( self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1 ) )
                    query_hash_ids_2 = set( self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_2, temp_table_name_2 ) )
                    
                    # we are going to say our 'master' king for the pair(s) returned here is always from search 1
                    chosen_allowed_hash_ids = query_hash_ids_1
                    comparison_allowed_hash_ids = query_hash_ids_2
                    
                    table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSeparateSearchResults( temp_table_name_1, temp_table_name_2, pixel_dupes_preference, max_hamming_distance )
                    
                else:
                    
                    if file_search_context_1.IsJustSystemEverything() or file_search_context_1.HasNoPredicates():
                        
                        table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnEverythingSearchResults( db_location_context, pixel_dupes_preference, max_hamming_distance )
                        
                    else:
                        
                        query_hash_ids = set( self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1 ) )
                        
                        if dupe_search_type == CC.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH:
                            
                            chosen_allowed_hash_ids = query_hash_ids
                            comparison_allowed_hash_ids = query_hash_ids
                            
                            table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSearchResultsBothFiles( temp_table_name_1, pixel_dupes_preference, max_hamming_distance )
                            
                        else:
                            
                            # the master will always be one that matches the search, the comparison can be whatever
                            chosen_allowed_hash_ids = query_hash_ids
                            
                            table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSearchResults( db_location_context, temp_table_name_1, pixel_dupes_preference, max_hamming_distance )
                            
                        
                    
                
                # ok let's not use a set here, since that un-weights medias that appear a lot, and we want to see common stuff more often
                potential_media_ids = []
                
                # distinct important here for the search results table join
                for ( smaller_media_id, larger_media_id ) in self._Execute( 'SELECT DISTINCT smaller_media_id, larger_media_id FROM {};'.format( table_join ) ):
                    
                    potential_media_ids.append( smaller_media_id )
                    potential_media_ids.append( larger_media_id )
                    
                    if len( potential_media_ids ) >= 1000:
                        
                        break
                        
                    
                
                # now let's randomly select a file in these medias
                
                random.shuffle( potential_media_ids )
                
                chosen_media_id = None
                chosen_hash_id = None
                
                for potential_media_id in potential_media_ids:
                    
                    best_king_hash_id = self.modules_files_duplicates.GetBestKingId( potential_media_id, db_location_context, allowed_hash_ids = chosen_allowed_hash_ids, preferred_hash_ids = chosen_preferred_hash_ids )
                    
                    if best_king_hash_id is not None:
                        
                        chosen_media_id = potential_media_id
                        chosen_hash_id = best_king_hash_id
                        
                        break
                        
                    
                
                if chosen_hash_id is None:
                    
                    return []
                    
                
                # I used to do self.modules_files_duplicates.GetFileHashesByDuplicateType here, but that gets _all_ potentials in the db context, even with allowed_hash_ids doing work it won't capture pixel hashes or duplicate distance that we searched above
                # so, let's search and make the list manually!
                
                comparison_hash_ids = []
                
                # distinct important here for the search results table join
                matching_pairs = self._Execute( 'SELECT DISTINCT smaller_media_id, larger_media_id FROM {} AND ( smaller_media_id = ? OR larger_media_id = ? );'.format( table_join ), ( chosen_media_id, chosen_media_id ) ).fetchall()
                
                for ( smaller_media_id, larger_media_id ) in matching_pairs:
                    
                    if smaller_media_id == chosen_media_id:
                        
                        potential_media_id = larger_media_id
                        
                    else:
                        
                        potential_media_id = smaller_media_id
                        
                    
                    best_king_hash_id = self.modules_files_duplicates.GetBestKingId( potential_media_id, db_location_context, allowed_hash_ids = comparison_allowed_hash_ids, preferred_hash_ids = comparison_preferred_hash_ids )
                    
                    if best_king_hash_id is not None:
                        
                        comparison_hash_ids.append( best_king_hash_id )
                        
                    
                
                # might as well have some kind of order
                comparison_hash_ids.sort()
                
                results_hash_ids = [ chosen_hash_id ] + comparison_hash_ids
                
                return self.modules_hashes_local_cache.GetHashes( results_hash_ids )
                
            
        
    
    def _DuplicatesGetPotentialDuplicatePairsForFiltering( self, file_search_context_1: ClientSearch.FileSearchContext, file_search_context_2: ClientSearch.FileSearchContext, dupe_search_type: int, pixel_dupes_preference, max_hamming_distance, max_num_pairs: typing.Optional[ int ] = None ):
        
        if max_num_pairs is None:
            
            max_num_pairs = HG.client_controller.new_options.GetInteger( 'duplicate_filter_max_batch_size' )
            
        
        # we need to batch non-intersecting decisions here to keep it simple at the gui-level
        # we also want to maximise per-decision value
        
        # now we will fetch some unknown pairs
        
        db_location_context = self.modules_files_storage.GetDBLocationContext( file_search_context_1.GetLocationContext() )
        
        chosen_allowed_hash_ids = None
        chosen_preferred_hash_ids = None
        comparison_allowed_hash_ids = None
        comparison_preferred_hash_ids = None
        
        with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_1:
            
            with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_2:
                
                if dupe_search_type == CC.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES:
                    
                    query_hash_ids_1 = set( self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1 ) )
                    query_hash_ids_2 = set( self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_2, temp_table_name_2 ) )
                    
                    # we always want pairs where one is in one and the other is in the other, we don't want king-selection-trickery giving us a jpeg vs a jpeg
                    chosen_allowed_hash_ids = query_hash_ids_1
                    comparison_allowed_hash_ids = query_hash_ids_2
                    
                    table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSeparateSearchResults( temp_table_name_1, temp_table_name_2, pixel_dupes_preference, max_hamming_distance )
                    
                else:
                    
                    if file_search_context_1.IsJustSystemEverything() or file_search_context_1.HasNoPredicates():
                        
                        table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnEverythingSearchResults( db_location_context, pixel_dupes_preference, max_hamming_distance )
                        
                    else:
                        
                        query_hash_ids = set( self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1 ) )
                        
                        if dupe_search_type == CC.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH:
                            
                            # both chosen and comparison must be in the search, no king selection nonsense allowed
                            chosen_allowed_hash_ids = query_hash_ids
                            comparison_allowed_hash_ids = query_hash_ids
                            
                            table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSearchResultsBothFiles( temp_table_name_1, pixel_dupes_preference, max_hamming_distance )
                            
                        else:
                            
                            # the chosen must be in the search, but we don't care about the comparison as long as it is viewable
                            chosen_preferred_hash_ids = query_hash_ids
                            
                            table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSearchResults( db_location_context, temp_table_name_1, pixel_dupes_preference, max_hamming_distance )
                            
                        
                    
                
                # distinct important here for the search results table join
                result = self._Execute( 'SELECT DISTINCT smaller_media_id, larger_media_id, distance FROM {} LIMIT 2500;'.format( table_join ) ).fetchall()
                
            
        
        batch_of_pairs_of_media_ids = []
        seen_media_ids = set()
        
        distances_to_pairs = HydrusData.BuildKeyToListDict( ( ( distance, ( smaller_media_id, larger_media_id ) ) for ( smaller_media_id, larger_media_id, distance ) in result ) )
        
        distances = sorted( distances_to_pairs.keys() )
        
        # we want to preference pairs that have the smallest distance between them. deciding on more similar files first helps merge dupes before dealing with alts so reduces potentials more quickly
        for distance in distances:
            
            result_pairs_for_this_distance = distances_to_pairs[ distance ]
            
            # convert them into possible groups per each possible 'master hash_id', and value them
            
            master_media_ids_to_groups = collections.defaultdict( list )
            
            for pair in result_pairs_for_this_distance:
                
                ( smaller_media_id, larger_media_id ) = pair
                
                master_media_ids_to_groups[ smaller_media_id ].append( pair )
                master_media_ids_to_groups[ larger_media_id ].append( pair )
                
            
            master_hash_ids_to_values = collections.Counter()
            
            for ( media_id, pairs ) in master_media_ids_to_groups.items():
                
                # negative so we later serve up smallest groups first
                # we shall say for now that smaller groups are more useful to front-load because it lets us solve simple problems first
                master_hash_ids_to_values[ media_id ] = - len( pairs )
                
            
            # now let's add decision groups to our batch
            # we exclude hashes we have seen before in each batch so we aren't treading over ground that was implicitly solved by a previous decision in the batch
            
            for ( master_media_id, count ) in master_hash_ids_to_values.most_common():
                
                if master_media_id in seen_media_ids:
                    
                    continue
                    
                
                seen_media_ids_for_this_master_media_id = set()
                
                for pair in master_media_ids_to_groups[ master_media_id ]:
                    
                    ( smaller_media_id, larger_media_id ) = pair
                    
                    if smaller_media_id in seen_media_ids or larger_media_id in seen_media_ids:
                        
                        continue
                        
                    
                    seen_media_ids_for_this_master_media_id.add( smaller_media_id )
                    seen_media_ids_for_this_master_media_id.add( larger_media_id )
                    
                    batch_of_pairs_of_media_ids.append( pair )
                    
                    if len( batch_of_pairs_of_media_ids ) >= max_num_pairs:
                        
                        break
                        
                    
                
                seen_media_ids.update( seen_media_ids_for_this_master_media_id )
                
                if len( batch_of_pairs_of_media_ids ) >= max_num_pairs:
                    
                    break
                    
                
            
            if len( batch_of_pairs_of_media_ids ) >= max_num_pairs:
                
                break
                
            
        
        seen_hash_ids = set()
        
        batch_of_pairs_of_hash_ids = []
        
        if chosen_allowed_hash_ids == comparison_allowed_hash_ids and chosen_preferred_hash_ids == comparison_preferred_hash_ids:
            
            # which file was 'chosen' vs 'comparison' is irrelevant. the user is expecting to see a mix, so we want the best kings possible. this is probably 'system:everything' or similar
            
            for ( smaller_media_id, larger_media_id ) in batch_of_pairs_of_media_ids:
                
                best_smaller_king_hash_id = self.modules_files_duplicates.GetBestKingId( smaller_media_id, db_location_context, allowed_hash_ids = chosen_allowed_hash_ids, preferred_hash_ids = chosen_preferred_hash_ids )
                best_larger_king_hash_id = self.modules_files_duplicates.GetBestKingId( larger_media_id, db_location_context, allowed_hash_ids = chosen_allowed_hash_ids, preferred_hash_ids = chosen_preferred_hash_ids )
                
                if best_smaller_king_hash_id is not None and best_larger_king_hash_id is not None:
                    
                    batch_of_pairs_of_hash_ids.append( ( best_smaller_king_hash_id, best_larger_king_hash_id ) )
                    
                    seen_hash_ids.update( ( best_smaller_king_hash_id, best_larger_king_hash_id ) )
                    
                
            
        else:
            
            # we want to enforce that our pairs seem human. if the user said 'A is in search 1 and B is in search 2', we don't want king selection going funny and giving us two from 1
            # previously, we did this on media_ids on their own, but we have to do it in pairs. we choose the 'chosen' and 'comparison' of our pair and filter accordingly
            
            for ( smaller_media_id, larger_media_id ) in batch_of_pairs_of_media_ids:
                
                best_smaller_king_hash_id = self.modules_files_duplicates.GetBestKingId( smaller_media_id, db_location_context, allowed_hash_ids = chosen_allowed_hash_ids, preferred_hash_ids = chosen_preferred_hash_ids )
                best_larger_king_hash_id = self.modules_files_duplicates.GetBestKingId( larger_media_id, db_location_context, allowed_hash_ids = comparison_allowed_hash_ids, preferred_hash_ids = comparison_preferred_hash_ids )
                
                if best_smaller_king_hash_id is None or best_larger_king_hash_id is None:
                    
                    # ok smaller was probably the comparison, let's see if that produces a better king hash
                    
                    best_smaller_king_hash_id = self.modules_files_duplicates.GetBestKingId( smaller_media_id, db_location_context, allowed_hash_ids = comparison_allowed_hash_ids, preferred_hash_ids = comparison_preferred_hash_ids )
                    best_larger_king_hash_id = self.modules_files_duplicates.GetBestKingId( larger_media_id, db_location_context, allowed_hash_ids = chosen_allowed_hash_ids, preferred_hash_ids = chosen_preferred_hash_ids )
                    
                
                if best_smaller_king_hash_id is not None and best_larger_king_hash_id is not None:
                    
                    batch_of_pairs_of_hash_ids.append( ( best_smaller_king_hash_id, best_larger_king_hash_id ) )
                    
                    seen_hash_ids.update( ( best_smaller_king_hash_id, best_larger_king_hash_id ) )
                    
                
            
        
        media_results = self._GetMediaResults( seen_hash_ids )
        
        hash_ids_to_media_results = { media_result.GetHashId() : media_result for media_result in media_results }
        
        batch_of_pairs_of_media_results = [ ( hash_ids_to_media_results[ hash_id_a ], hash_ids_to_media_results[ hash_id_b ] ) for ( hash_id_a, hash_id_b ) in batch_of_pairs_of_hash_ids ]
        
        return batch_of_pairs_of_media_results
        
    
    def _DuplicatesGetPotentialDuplicatesCount( self, file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance ):
        
        db_location_context = self.modules_files_storage.GetDBLocationContext( file_search_context_1.GetLocationContext() )
        
        with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_1:
            
            with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_2:
                
                if dupe_search_type == CC.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES:
                    
                    self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1 )
                    self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_2, temp_table_name_2 )
                    
                    table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSeparateSearchResults( temp_table_name_1, temp_table_name_2, pixel_dupes_preference, max_hamming_distance )
                    
                else:
                    
                    if file_search_context_1.IsJustSystemEverything() or file_search_context_1.HasNoPredicates():
                        
                        table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnEverythingSearchResults( db_location_context, pixel_dupes_preference, max_hamming_distance )
                        
                    else:
                        
                        self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1 )
                        
                        if dupe_search_type == CC.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH:
                            
                            table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSearchResultsBothFiles( temp_table_name_1, pixel_dupes_preference, max_hamming_distance )
                            
                        else:
                            
                            table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSearchResults( db_location_context, temp_table_name_1, pixel_dupes_preference, max_hamming_distance )
                            
                        
                    
                
                # distinct important here for the search results table join
                ( potential_duplicates_count, ) = self._Execute( 'SELECT COUNT( * ) FROM ( SELECT DISTINCT smaller_media_id, larger_media_id FROM {} );'.format( table_join ) ).fetchone()
                
            
        
        return potential_duplicates_count
        
    
    def _DuplicatesSetDuplicatePairStatus( self, pair_info ):
        
        for ( duplicate_type, hash_a, hash_b, list_of_service_keys_to_content_updates ) in pair_info:
            
            if isinstance( list_of_service_keys_to_content_updates, dict ):
                
                list_of_service_keys_to_content_updates = [ list_of_service_keys_to_content_updates ]
                
            
            for service_keys_to_content_updates in list_of_service_keys_to_content_updates:
                
                self._ProcessContentUpdates( service_keys_to_content_updates )
                
            
            hash_id_a = self.modules_hashes_local_cache.GetHashId( hash_a )
            hash_id_b = self.modules_hashes_local_cache.GetHashId( hash_b )
            
            media_id_a = self.modules_files_duplicates.GetMediaId( hash_id_a )
            media_id_b = self.modules_files_duplicates.GetMediaId( hash_id_b )
            
            smaller_media_id = min( media_id_a, media_id_b )
            larger_media_id = max( media_id_a, media_id_b )
            
            # this shouldn't be strictly needed, but lets do it here anyway to catch unforeseen problems
            # it is ok to remove this even if we are just about to add it back in--this clears out invalid pairs and increases priority with distance 0
            self._Execute( 'DELETE FROM potential_duplicate_pairs WHERE smaller_media_id = ? AND larger_media_id = ?;', ( smaller_media_id, larger_media_id ) )
            
            if hash_id_a == hash_id_b:
                
                continue
                
            
            if duplicate_type in ( HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_ALTERNATE ):
                
                if duplicate_type == HC.DUPLICATE_FALSE_POSITIVE:
                    
                    alternates_group_id_a = self.modules_files_duplicates.GetAlternatesGroupId( media_id_a )
                    alternates_group_id_b = self.modules_files_duplicates.GetAlternatesGroupId( media_id_b )
                    
                    self.modules_files_duplicates.SetFalsePositive( alternates_group_id_a, alternates_group_id_b )
                    
                elif duplicate_type == HC.DUPLICATE_ALTERNATE:
                    
                    if media_id_a == media_id_b:
                        
                        king_hash_id = self.modules_files_duplicates.GetKingHashId( media_id_a )
                        
                        hash_id_to_remove = hash_id_b if king_hash_id == hash_id_a else hash_id_a
                        
                        self.modules_files_duplicates.RemoveMediaIdMember( hash_id_to_remove )
                        
                        media_id_a = self.modules_files_duplicates.GetMediaId( hash_id_a )
                        media_id_b = self.modules_files_duplicates.GetMediaId( hash_id_b )
                        
                        smaller_media_id = min( media_id_a, media_id_b )
                        larger_media_id = max( media_id_a, media_id_b )
                        
                    
                    self.modules_files_duplicates.SetAlternates( media_id_a, media_id_b )
                    
                
            elif duplicate_type in ( HC.DUPLICATE_BETTER, HC.DUPLICATE_WORSE, HC.DUPLICATE_SAME_QUALITY ):
                
                if duplicate_type == HC.DUPLICATE_WORSE:
                    
                    ( hash_id_a, hash_id_b ) = ( hash_id_b, hash_id_a )
                    ( media_id_a, media_id_b ) = ( media_id_b, media_id_a )
                    
                    duplicate_type = HC.DUPLICATE_BETTER
                    
                
                king_hash_id_a = self.modules_files_duplicates.GetKingHashId( media_id_a )
                king_hash_id_b = self.modules_files_duplicates.GetKingHashId( media_id_b )
                
                if duplicate_type == HC.DUPLICATE_BETTER:
                    
                    if media_id_a == media_id_b:
                        
                        if hash_id_b == king_hash_id_b:
                            
                            # user manually set that a > King A, hence we are setting a new king within a group
                            
                            self.modules_files_duplicates.SetKing( hash_id_a, media_id_a )
                            
                        
                    else:
                        
                        if hash_id_b != king_hash_id_b:
                            
                            # user manually set that a member of A is better than a non-King of B. remove b from B and merge it into A
                            
                            self.modules_files_duplicates.RemoveMediaIdMember( hash_id_b )
                            
                            media_id_b = self.modules_files_duplicates.GetMediaId( hash_id_b )
                            
                            # b is now the King of its new group
                            
                        
                        # a member of A is better than King B, hence B can merge into A
                        
                        self.modules_files_duplicates.MergeMedias( media_id_a, media_id_b )
                        
                    
                elif duplicate_type == HC.DUPLICATE_SAME_QUALITY:
                    
                    if media_id_a != media_id_b:
                        
                        a_is_king = hash_id_a == king_hash_id_a
                        b_is_king = hash_id_b == king_hash_id_b
                        
                        if not ( a_is_king or b_is_king ):
                            
                            # if neither file is the king, remove B from B and merge it into A
                            
                            self.modules_files_duplicates.RemoveMediaIdMember( hash_id_b )
                            
                            media_id_b = self.modules_files_duplicates.GetMediaId( hash_id_b )
                            
                            superior_media_id = media_id_a
                            mergee_media_id = media_id_b
                            
                        elif not a_is_king:
                            
                            # if one of our files is not the king, merge into that group, as the king of that is better than all of the other
                            
                            superior_media_id = media_id_a
                            mergee_media_id = media_id_b
                            
                        elif not b_is_king:
                            
                            superior_media_id = media_id_b
                            mergee_media_id = media_id_a
                            
                        else:
                            
                            # if both are king, merge into A
                            
                            superior_media_id = media_id_a
                            mergee_media_id = media_id_b
                            
                        
                        self.modules_files_duplicates.MergeMedias( superior_media_id, mergee_media_id )
                        
                    
                
            elif duplicate_type == HC.DUPLICATE_POTENTIAL:
                
                potential_duplicate_media_ids_and_distances = [ ( media_id_b, 0 ) ]
                
                self.modules_files_duplicates.AddPotentialDuplicates( media_id_a, potential_duplicate_media_ids_and_distances )
                
            
        
    
    def _FilterForFileDeleteLock( self, service_id, hash_ids ):
        
        # TODO: like in the MediaSingleton object, eventually extend this to the metadata conditional object
        
        if HG.client_controller.new_options.GetBoolean( 'delete_lock_for_archived_files' ):
            
            service = self.modules_services.GetService( service_id )
            
            if service.GetServiceType() in HC.LOCAL_FILE_SERVICES:
                
                hash_ids = set( hash_ids ).intersection( self.modules_files_inbox.inbox_hash_ids )
                
            
        
        return hash_ids
        
    
    def _FixLogicallyInconsistentMappings( self, tag_service_key = None ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        total_fixed = 0
        
        try:
            
            job_key.SetStatusTitle( 'fixing logically inconsistent mappings' )
            
            self._controller.pub( 'modal_message', job_key )
            
            if tag_service_key is None:
                
                tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                
            else:
                
                tag_service_ids = ( self.modules_services.GetServiceId( tag_service_key ), )
                
            
            for tag_service_id in tag_service_ids:
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'fixing {}'.format( tag_service_id )
                
                job_key.SetStatusText( message )
                
                time.sleep( 0.01 )
                
                ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( tag_service_id )
                
                #
                
                both_current_and_pending_mappings = list(
                    HydrusData.BuildKeyToSetDict(
                        self._Execute( 'SELECT tag_id, hash_id FROM {} CROSS JOIN {} USING ( tag_id, hash_id );'.format( pending_mappings_table_name, current_mappings_table_name ) )
                    ).items()
                )
                
                total_fixed += sum( ( len( hash_ids ) for ( tag_id, hash_ids ) in both_current_and_pending_mappings ) )
                
                self._UpdateMappings( tag_service_id, pending_rescinded_mappings_ids = both_current_and_pending_mappings )
                
                #
                
                both_deleted_and_petitioned_mappings = list(
                    HydrusData.BuildKeyToSetDict(
                        self._Execute( 'SELECT tag_id, hash_id FROM {} CROSS JOIN {} USING ( tag_id, hash_id );'.format( petitioned_mappings_table_name, deleted_mappings_table_name ) )
                    ).items()
                )
                
                total_fixed += sum( ( len( hash_ids ) for ( tag_id, hash_ids ) in both_deleted_and_petitioned_mappings ) )
                
                self._UpdateMappings( tag_service_id, petitioned_rescinded_mappings_ids = both_deleted_and_petitioned_mappings )
                
            
        finally:
            
            if total_fixed == 0:
                
                HydrusData.ShowText( 'No inconsistent mappings found!' )
                
            else:
                
                self._Execute( 'DELETE FROM service_info where info_type IN ( ?, ? );', ( HC.SERVICE_INFO_NUM_PENDING_MAPPINGS, HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS ) )
                
                self._controller.pub( 'notify_new_pending' )
                
                HydrusData.ShowText( 'Found {} bad mappings! They _should_ be deleted, and your pending counts should be updated.'.format( HydrusData.ToHumanInt( total_fixed ) ) )
                
            
            job_key.DeleteStatusText( 2 )
            
            job_key.SetStatusText( 'done!' )
            
            job_key.Finish()
            
            job_key.Delete( 5 )
            
        
    
    def _GenerateDBJob( self, job_type, synchronous, action, *args, **kwargs ):
        
        return JobDatabaseClient( job_type, synchronous, action, *args, **kwargs )
        
    
    def _GetBonedStats( self ):
        
        boned_stats = {}
        
        current_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_media_service_id, HC.CONTENT_STATUS_CURRENT )
        
        ( num_total, size_total ) = self._Execute( 'SELECT COUNT( hash_id ), SUM( size ) FROM {} CROSS JOIN files_info USING ( hash_id );'.format( current_files_table_name ) ).fetchone()
        ( num_inbox, size_inbox ) = self._Execute( 'SELECT COUNT( hash_id ), SUM( size ) FROM files_info NATURAL JOIN {} NATURAL JOIN file_inbox;'.format( current_files_table_name ) ).fetchone()
        
        if size_total is None:
            
            size_total = 0
            
        
        if size_inbox is None:
            
            size_inbox = 0
            
        
        deleted_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_media_service_id, HC.CONTENT_STATUS_DELETED )
        
        ( num_deleted, size_deleted ) = self._Execute( 'SELECT COUNT( hash_id ), SUM( size ) FROM {} CROSS JOIN files_info USING ( hash_id );'.format( deleted_files_table_name ) ).fetchone()
        
        if size_deleted is None:
            
            size_deleted = 0
            
        
        num_archive = num_total - num_inbox
        size_archive = size_total - size_inbox
        
        boned_stats[ 'num_inbox' ] = num_inbox
        boned_stats[ 'num_archive' ] = num_archive
        boned_stats[ 'num_deleted' ] = num_deleted
        boned_stats[ 'size_inbox' ] = size_inbox
        boned_stats[ 'size_archive' ] = size_archive
        boned_stats[ 'size_deleted' ] = size_deleted
        
        canvas_types_to_total_viewtimes = { canvas_type : ( views, viewtime ) for ( canvas_type, views, viewtime ) in self._Execute( 'SELECT canvas_type, SUM( views ), SUM( viewtime ) FROM file_viewing_stats GROUP BY canvas_type;' ) }
        
        if CC.CANVAS_PREVIEW not in canvas_types_to_total_viewtimes:
            
            canvas_types_to_total_viewtimes[ CC.CANVAS_PREVIEW ] = ( 0, 0 )
            
        
        if CC.CANVAS_MEDIA_VIEWER not in canvas_types_to_total_viewtimes:
            
            canvas_types_to_total_viewtimes[ CC.CANVAS_MEDIA_VIEWER ] = ( 0, 0 )
            
        
        total_viewtime = canvas_types_to_total_viewtimes[ CC.CANVAS_MEDIA_VIEWER ] + canvas_types_to_total_viewtimes[ CC.CANVAS_PREVIEW ]
        
        #
        
        earliest_import_time = 0
        
        current_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_media_service_id, HC.CONTENT_STATUS_CURRENT )
        
        result = self._Execute( 'SELECT MIN( timestamp ) FROM {};'.format( current_files_table_name ) ).fetchone()
        
        if result is not None and result[0] is not None:
            
            earliest_import_time = result[0]
            
        
        deleted_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_media_service_id, HC.CONTENT_STATUS_DELETED )
        
        result = self._Execute( 'SELECT MIN( original_timestamp ) FROM {};'.format( deleted_files_table_name ) ).fetchone()
        
        if result is not None and result[0] is not None:
            
            if earliest_import_time == 0:
                
                earliest_import_time = result[0]
                
            else:
                
                earliest_import_time = min( earliest_import_time, result[0] )
                
            
        
        if earliest_import_time > 0:
            
            boned_stats[ 'earliest_import_time' ] = earliest_import_time
            
        
        #
        
        boned_stats[ 'total_viewtime' ] = total_viewtime
        
        total_alternate_files = sum( ( count for ( alternates_group_id, count ) in self._Execute( 'SELECT alternates_group_id, COUNT( * ) FROM alternate_file_group_members GROUP BY alternates_group_id;' ) if count > 1 ) )
        total_duplicate_files = sum( ( count for ( media_id, count ) in self._Execute( 'SELECT media_id, COUNT( * ) FROM duplicate_file_members GROUP BY media_id;' ) if count > 1 ) )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
        
        db_location_context = self.modules_files_storage.GetDBLocationContext( location_context )
        
        table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnFileService( db_location_context )
        
        ( total_potential_pairs, ) = self._Execute( 'SELECT COUNT( * ) FROM ( SELECT DISTINCT smaller_media_id, larger_media_id FROM {} );'.format( table_join ) ).fetchone()
        
        boned_stats[ 'total_alternate_files' ] = total_alternate_files
        boned_stats[ 'total_duplicate_files' ] = total_duplicate_files
        boned_stats[ 'total_potential_pairs' ] = total_potential_pairs
        
        return boned_stats
        
    
    def _GetFileInfoManagers( self, hash_ids: typing.Collection[ int ], sorted = False ) -> typing.List[ ClientMediaManagers.FileInfoManager ]:
        
        ( cached_media_results, missing_hash_ids ) = self._weakref_media_result_cache.GetMediaResultsAndMissing( hash_ids )
        
        file_info_managers = [ media_result.GetFileInfoManager() for media_result in cached_media_results ]
        
        if len( missing_hash_ids ) > 0:
            
            missing_hash_ids_to_hashes = self.modules_hashes_local_cache.GetHashIdsToHashes( hash_ids = missing_hash_ids )
            
            with self._MakeTemporaryIntegerTable( missing_hash_ids, 'hash_id' ) as temp_table_name:
                
                # temp hashes to metadata
                hash_ids_to_info = { hash_id : ClientMediaManagers.FileInfoManager( hash_id, missing_hash_ids_to_hashes[ hash_id ], size, mime, width, height, duration, num_frames, has_audio, num_words ) for ( hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words ) in self._Execute( 'SELECT * FROM {} CROSS JOIN files_info USING ( hash_id );'.format( temp_table_name ) ) }
                
            
            # build it
            
            for hash_id in missing_hash_ids:
                
                if hash_id in hash_ids_to_info:
                    
                    file_info_manager = hash_ids_to_info[ hash_id ]
                    
                else:
                    
                    hash = missing_hash_ids_to_hashes[ hash_id ]
                    
                    file_info_manager = ClientMediaManagers.FileInfoManager( hash_id, hash )
                    
                
                file_info_managers.append( file_info_manager )
                
            
        
        if sorted:
            
            if len( hash_ids ) > len( file_info_managers ):
                
                hash_ids = HydrusData.DedupeList( hash_ids )
                
            
            hash_ids_to_file_info_managers = { file_info_manager.hash_id : file_info_manager for file_info_manager in file_info_managers }
            
            file_info_managers = [ hash_ids_to_file_info_managers[ hash_id ] for hash_id in hash_ids if hash_id in hash_ids_to_file_info_managers ]
            
        
        return file_info_managers
        
    
    def _GetFileInfoManagersFromHashes( self, hashes: typing.Collection[ bytes ], sorted: bool = False ) -> typing.List[ ClientMediaManagers.FileInfoManager ]:
        
        query_hash_ids = set( self.modules_hashes_local_cache.GetHashIds( hashes ) )
        
        file_info_managers = self._GetFileInfoManagers( query_hash_ids )
        
        if sorted:
            
            if len( hashes ) > len( query_hash_ids ):
                
                hashes = HydrusData.DedupeList( hashes )
                
            
            hashes_to_file_info_managers = { file_info_manager.hash : file_info_manager for file_info_manager in file_info_managers }
            
            file_info_managers = [ hashes_to_file_info_managers[ hash ] for hash in hashes if hash in hashes_to_file_info_managers ]
            
        
        return file_info_managers
        
    
    def _GetFileSystemPredicates( self, file_search_context: ClientSearch.FileSearchContext, force_system_everything = False ):
        
        location_context = file_search_context.GetLocationContext()
        
        system_everything_limit = 10000
        system_everything_suffix = ''
        
        predicates = []
        
        system_everythings = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING ) ]
        
        blank_pred_types = {
            ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS,
            ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT,
            ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS,
            ClientSearch.PREDICATE_TYPE_SYSTEM_HASH,
            ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE,
            ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS,
            ClientSearch.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER,
            ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS
        }
        
        if len( self.modules_services.GetServiceIds( HC.RATINGS_SERVICES ) ) > 0:
            
            blank_pred_types.add( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING )
            
        
        if location_context.IsAllKnownFiles():
            
            tag_service_key = file_search_context.GetTagContext().service_key
            
            if tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
                
                # this shouldn't happen, combined on both sides, but let's do our best anyway
                
                if force_system_everything or self._controller.new_options.GetBoolean( 'always_show_system_everything' ):
                    
                    predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING ) )
                    
                
            else:
                
                service_id = self.modules_services.GetServiceId( tag_service_key )
                
                service_type = self.modules_services.GetServiceType( service_id )
                
                info_type = HC.SERVICE_INFO_NUM_FILE_HASHES
                
                service_info = self._GetServiceInfoSpecific( service_id, service_type, { info_type }, calculate_missing = False )
                
                if info_type in service_info:
                    
                    num_everything = service_info[ info_type ]
                    
                    system_everythings.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING, count = ClientSearch.PredicateCount.STATICCreateCurrentCount( num_everything ) ) )
                    
                
            
        else:
            
            # specific file service(s)
            
            jobs = []
            
            jobs.extend( ( ( file_service_key, HC.CONTENT_STATUS_CURRENT ) for file_service_key in location_context.current_service_keys ) )
            jobs.extend( ( ( file_service_key, HC.CONTENT_STATUS_DELETED ) for file_service_key in location_context.deleted_service_keys ) )
            
            file_repo_preds = []
            inbox_archive_preds = []
            
            we_saw_a_file_repo = False
            
            for ( file_service_key, status ) in jobs:
                
                service_id = self.modules_services.GetServiceId( file_service_key )
                
                service_type = self.modules_services.GetServiceType( service_id )
                
                if service_type not in HC.FILE_SERVICES:
                    
                    continue
                    
                
                if status == HC.CONTENT_STATUS_CURRENT:
                    
                    service_info = self._GetServiceInfoSpecific( service_id, service_type, { HC.SERVICE_INFO_NUM_VIEWABLE_FILES, HC.SERVICE_INFO_NUM_INBOX } )
                    
                    num_everything = service_info[ HC.SERVICE_INFO_NUM_VIEWABLE_FILES ]
                    
                    system_everythings.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING, count = ClientSearch.PredicateCount.STATICCreateCurrentCount( num_everything ) ) )
                    
                    if location_context.IncludesDeleted():
                        
                        # inbox/archive and local/remote are too difficult to get good numbers for and merge for deleted, so we'll exclude if this is a mix
                        
                        continue
                        
                    
                    num_inbox = service_info[ HC.SERVICE_INFO_NUM_INBOX ]
                    num_archive = num_everything - num_inbox
                    
                    if service_type == HC.FILE_REPOSITORY:
                        
                        we_saw_a_file_repo = True
                        
                        num_local = self.modules_files_storage.GetNumLocal( service_id )
                        
                        num_not_local = num_everything - num_local
                        
                    else:
                        
                        num_local = num_everything
                        num_not_local = 0
                        
                    
                    file_repo_preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LOCAL, count = ClientSearch.PredicateCount.STATICCreateCurrentCount( num_local ) ) )
                    file_repo_preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, count = ClientSearch.PredicateCount.STATICCreateCurrentCount( num_not_local ) ) )
                    
                    num_archive = num_local - num_inbox
                    
                    inbox_archive_preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_INBOX, count = ClientSearch.PredicateCount.STATICCreateCurrentCount( num_inbox ) ) )
                    inbox_archive_preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVE, count = ClientSearch.PredicateCount.STATICCreateCurrentCount( num_archive ) ) )
                    
                elif status == HC.CONTENT_STATUS_DELETED:
                    
                    service_info = self._GetServiceInfoSpecific( service_id, service_type, { HC.SERVICE_INFO_NUM_DELETED_FILES } )
                    
                    num_everything = service_info[ HC.SERVICE_INFO_NUM_DELETED_FILES ]
                    
                    system_everythings.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING, count = ClientSearch.PredicateCount.STATICCreateCurrentCount( num_everything ) ) )
                    
                
            
            if we_saw_a_file_repo:
                
                predicates.extend( file_repo_preds )
                
            
            if len( inbox_archive_preds ) > 0:
                
                inbox_archive_preds = ClientSearch.MergePredicates( inbox_archive_preds )
                
                zero_counts = [ pred.GetCount().HasZeroCount() for pred in inbox_archive_preds ]
                
                if True in zero_counts and self._controller.new_options.GetBoolean( 'filter_inbox_and_archive_predicates' ):
                    
                    if False in zero_counts and location_context.IsOneDomain():
                        
                        # something is in here, but we are hiding, so let's inform system everything
                        useful_pred = list( ( pred for pred in inbox_archive_preds if pred.GetCount().HasNonZeroCount() ) )[0]
                        
                        if useful_pred.GetType() == ClientSearch.PREDICATE_TYPE_SYSTEM_INBOX:
                            
                            system_everything_suffix = 'all in inbox'
                            
                        else:
                            
                            system_everything_suffix = 'all in archive'
                            
                        
                    
                else:
                    
                    predicates.extend( inbox_archive_preds )
                    
                
            
            blank_pred_types.update( [
                ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE,
                ClientSearch.PREDICATE_TYPE_SYSTEM_TIME,
                ClientSearch.PREDICATE_TYPE_SYSTEM_DIMENSIONS,
                ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION,
                ClientSearch.PREDICATE_TYPE_SYSTEM_EMBEDDED_METADATA,
                ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO,
                ClientSearch.PREDICATE_TYPE_SYSTEM_NOTES,
                ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS,
                ClientSearch.PREDICATE_TYPE_SYSTEM_MIME,
                ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO
                ] )
            
        
        if len( system_everythings ) > 0:
            
            system_everythings = ClientSearch.MergePredicates( system_everythings )
            
            system_everything = list( system_everythings )[0]
            
            system_everything.SetCountTextSuffix( system_everything_suffix )
            
            num_everything = system_everything.GetCount().GetMinCount()
            
            if force_system_everything or ( num_everything <= system_everything_limit or self._controller.new_options.GetBoolean( 'always_show_system_everything' ) ):
                
                predicates.append( system_everything )
                
            
        
        predicates.extend( [ ClientSearch.Predicate( predicate_type ) for predicate_type in blank_pred_types ] )
        
        predicates = ClientSearch.MergePredicates( predicates )
        
        def sys_preds_key( s ):
            
            t = s.GetType()
            
            if t == ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING:
                
                return ( 0, 0 )
                
            elif t == ClientSearch.PREDICATE_TYPE_SYSTEM_INBOX:
                
                return ( 1, 0 )
                
            elif t == ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVE:
                
                return ( 2, 0 )
                
            elif t == ClientSearch.PREDICATE_TYPE_SYSTEM_LOCAL:
                
                return ( 3, 0 )
                
            elif t == ClientSearch.PREDICATE_TYPE_SYSTEM_NOT_LOCAL:
                
                return ( 4, 0 )
                
            else:
                
                return ( 5, s.ToString() )
                
            
        
        predicates.sort( key = sys_preds_key )
        
        return predicates
        
    
    def _GetForceRefreshTagsManagers( self, hash_ids, hash_ids_to_current_file_service_ids = None ):
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_table_name:
            
            self._AnalyzeTempTable( temp_table_name )
            
            return self._GetForceRefreshTagsManagersWithTableHashIds( hash_ids, temp_table_name, hash_ids_to_current_file_service_ids = hash_ids_to_current_file_service_ids )
            
        
    
    def _GetForceRefreshTagsManagersWithTableHashIds( self, hash_ids, hash_ids_table_name, hash_ids_to_current_file_service_ids = None ):
        
        if hash_ids_to_current_file_service_ids is None:
            
            hash_ids_to_current_file_service_ids = self.modules_files_storage.GetHashIdsToCurrentServiceIds( hash_ids_table_name )
            
        
        common_file_service_ids_to_hash_ids = self.modules_files_storage.GroupHashIdsByTagCachedFileServiceId( hash_ids, hash_ids_table_name, hash_ids_to_current_file_service_ids = hash_ids_to_current_file_service_ids )
        
        #
        
        tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
        
        storage_tag_data = []
        display_tag_data = []
        
        for ( common_file_service_id, batch_of_hash_ids ) in common_file_service_ids_to_hash_ids.items():
            
            if len( batch_of_hash_ids ) == len( hash_ids ):
                
                ( batch_of_storage_tag_data, batch_of_display_tag_data ) = self._GetForceRefreshTagsManagersWithTableHashIdsTagData( common_file_service_id, tag_service_ids, hash_ids_table_name )
                
            else:
                
                with self._MakeTemporaryIntegerTable( batch_of_hash_ids, 'hash_id' ) as temp_batch_hash_ids_table_name:
                    
                    ( batch_of_storage_tag_data, batch_of_display_tag_data ) = self._GetForceRefreshTagsManagersWithTableHashIdsTagData( common_file_service_id, tag_service_ids, temp_batch_hash_ids_table_name )
                    
                
            
            storage_tag_data.extend( batch_of_storage_tag_data )
            display_tag_data.extend( batch_of_display_tag_data )
            
        
        seen_tag_ids = { tag_id for ( hash_id, ( tag_service_id, status, tag_id ) ) in storage_tag_data }
        seen_tag_ids.update( ( tag_id for ( hash_id, ( tag_service_id, status, tag_id ) ) in display_tag_data ) )
        
        tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = seen_tag_ids )
        
        service_ids_to_service_keys = self.modules_services.GetServiceIdsToServiceKeys()
        
        hash_ids_to_raw_storage_tag_data = HydrusData.BuildKeyToListDict( storage_tag_data )
        hash_ids_to_raw_display_tag_data = HydrusData.BuildKeyToListDict( display_tag_data )
        
        hash_ids_to_tag_managers = {}
        
        for hash_id in hash_ids:
            
            # service_id, status, tag_id
            raw_storage_tag_data = hash_ids_to_raw_storage_tag_data[ hash_id ]
            
            # service_id -> ( status, tag )
            service_ids_to_storage_tag_data = HydrusData.BuildKeyToListDict( ( ( tag_service_id, ( status, tag_ids_to_tags[ tag_id ] ) ) for ( tag_service_id, status, tag_id ) in raw_storage_tag_data ) )
            
            service_keys_to_statuses_to_storage_tags = collections.defaultdict(
                HydrusData.default_dict_set,
                { service_ids_to_service_keys[ tag_service_id ] : HydrusData.BuildKeyToSetDict( status_and_tag ) for ( tag_service_id, status_and_tag ) in service_ids_to_storage_tag_data.items() }
            )
            
            # service_id, status, tag_id
            raw_display_tag_data = hash_ids_to_raw_display_tag_data[ hash_id ]
            
            # service_id -> ( status, tag )
            service_ids_to_display_tag_data = HydrusData.BuildKeyToListDict( ( ( tag_service_id, ( status, tag_ids_to_tags[ tag_id ] ) ) for ( tag_service_id, status, tag_id ) in raw_display_tag_data ) )
            
            service_keys_to_statuses_to_display_tags = collections.defaultdict(
                HydrusData.default_dict_set,
                { service_ids_to_service_keys[ tag_service_id ] : HydrusData.BuildKeyToSetDict( status_and_tag ) for ( tag_service_id, status_and_tag ) in service_ids_to_display_tag_data.items() }
            )
            
            tags_manager = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_storage_tags, service_keys_to_statuses_to_display_tags )
            
            hash_ids_to_tag_managers[ hash_id ] = tags_manager
            
        
        return hash_ids_to_tag_managers
        
    
    def _GetForceRefreshTagsManagersWithTableHashIdsTagData( self, common_file_service_id, tag_service_ids, hash_ids_table_name ):
        
        storage_tag_data = []
        display_tag_data = []
        
        for tag_service_id in tag_service_ids:
            
            statuses_to_table_names = self.modules_mappings_storage.GetFastestStorageMappingTableNames( common_file_service_id, tag_service_id )
            
            for ( status, mappings_table_name ) in statuses_to_table_names.items():
                
                # temp hashes to mappings
                storage_tag_data.extend( ( hash_id, ( tag_service_id, status, tag_id ) ) for ( hash_id, tag_id ) in self._Execute( 'SELECT hash_id, tag_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( hash_ids_table_name, mappings_table_name ) ) )
                
            
            if common_file_service_id != self.modules_services.combined_file_service_id:
                
                ( cache_current_display_mappings_table_name, cache_pending_display_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificDisplayMappingsCacheTableNames( common_file_service_id, tag_service_id )
                
                # temp hashes to mappings
                display_tag_data.extend( ( hash_id, ( tag_service_id, HC.CONTENT_STATUS_CURRENT, tag_id ) ) for ( hash_id, tag_id ) in self._Execute( 'SELECT hash_id, tag_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( hash_ids_table_name, cache_current_display_mappings_table_name ) ) )
                display_tag_data.extend( ( hash_id, ( tag_service_id, HC.CONTENT_STATUS_PENDING, tag_id ) ) for ( hash_id, tag_id ) in self._Execute( 'SELECT hash_id, tag_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( hash_ids_table_name, cache_pending_display_mappings_table_name ) ) )
                
            
        
        if common_file_service_id == self.modules_services.combined_file_service_id:
            
            # this is likely a 'all known files' query, which means we are in deep water without a cache
            # time to compute manually, which is semi hell mode, but not dreadful
            
            current_and_pending_storage_tag_data = [ ( hash_id, ( tag_service_id, status, tag_id ) ) for ( hash_id, ( tag_service_id, status, tag_id ) ) in storage_tag_data if status in ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING ) ]
            
            seen_service_ids_to_seen_tag_ids = HydrusData.BuildKeyToSetDict( ( ( tag_service_id, tag_id ) for ( hash_id, ( tag_service_id, status, tag_id ) ) in current_and_pending_storage_tag_data ) )
            
            seen_service_ids_to_tag_ids_to_implied_tag_ids = { tag_service_id : self.modules_tag_display.GetTagsToImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, tag_ids ) for ( tag_service_id, tag_ids ) in seen_service_ids_to_seen_tag_ids.items() }
            
            display_tag_data = []
            
            for ( hash_id, ( tag_service_id, status, tag_id ) ) in current_and_pending_storage_tag_data:
                
                display_tag_data.extend( ( ( hash_id, ( tag_service_id, status, implied_tag_id ) ) for implied_tag_id in seen_service_ids_to_tag_ids_to_implied_tag_ids[ tag_service_id ][ tag_id ] ) )
                
            
        
        return ( storage_tag_data, display_tag_data )
        
    
    def _GetMaintenanceDue( self, stop_time ):
        
        jobs_to_do = []
        
        # analyze
        
        names_to_analyze = self.modules_db_maintenance.GetTableNamesDueAnalysis()
        
        if len( names_to_analyze ) > 0:
            
            jobs_to_do.append( 'analyze ' + HydrusData.ToHumanInt( len( names_to_analyze ) ) + ' table_names' )
            
        
        similar_files_due = self.modules_similar_files.MaintenanceDue()
        
        if similar_files_due:
            
            jobs_to_do.append( 'similar files work' )
            
        
        return jobs_to_do
        
    
    def _GetMediaResults( self, hash_ids: typing.Iterable[ int ], sorted = False ):
        
        ( cached_media_results, missing_hash_ids ) = self._weakref_media_result_cache.GetMediaResultsAndMissing( hash_ids )
        
        if len( missing_hash_ids ) > 0:
            
            # get first detailed results
            
            missing_hash_ids_to_hashes = self.modules_hashes_local_cache.GetHashIdsToHashes( hash_ids = missing_hash_ids )
            
            with self._MakeTemporaryIntegerTable( missing_hash_ids, 'hash_id' ) as temp_table_name:
                
                # everything here is temp hashes to metadata
                
                hash_ids_to_info = { hash_id : ClientMediaManagers.FileInfoManager( hash_id, missing_hash_ids_to_hashes[ hash_id ], size, mime, width, height, duration, num_frames, has_audio, num_words ) for ( hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words ) in self._Execute( 'SELECT * FROM {} CROSS JOIN files_info USING ( hash_id );'.format( temp_table_name ) ) }
                
                (
                    hash_ids_to_current_file_service_ids_and_timestamps,
                    hash_ids_to_deleted_file_service_ids_and_timestamps,
                    hash_ids_to_pending_file_service_ids,
                    hash_ids_to_petitioned_file_service_ids
                ) = self.modules_files_storage.GetHashIdsToServiceInfoDicts( temp_table_name )
                
                hash_ids_to_urls = self.modules_url_map.GetHashIdsToURLs( hash_ids_table_name = temp_table_name )
                
                hash_ids_to_service_ids_and_filenames = self.modules_service_paths.GetHashIdsToServiceIdsAndFilenames( temp_table_name )
                
                hash_ids_to_local_star_ratings = HydrusData.BuildKeyToListDict( ( ( hash_id, ( service_id, rating ) ) for ( service_id, hash_id, rating ) in self._Execute( 'SELECT service_id, hash_id, rating FROM {} CROSS JOIN local_ratings USING ( hash_id );'.format( temp_table_name ) ) ) )
                hash_ids_to_local_incdec_ratings = HydrusData.BuildKeyToListDict( ( ( hash_id, ( service_id, rating ) ) for ( service_id, hash_id, rating ) in self._Execute( 'SELECT service_id, hash_id, rating FROM {} CROSS JOIN local_incdec_ratings USING ( hash_id );'.format( temp_table_name ) ) ) )
                
                hash_ids_to_local_ratings = collections.defaultdict( list )
                
                for ( hash_id, info_list ) in hash_ids_to_local_star_ratings.items():
                    
                    hash_ids_to_local_ratings[ hash_id ].extend( info_list )
                    
                
                for ( hash_id, info_list ) in hash_ids_to_local_incdec_ratings.items():
                    
                    hash_ids_to_local_ratings[ hash_id ].extend( info_list )
                    
                
                hash_ids_to_names_and_notes = self.modules_notes_map.GetHashIdsToNamesAndNotes( temp_table_name )
                
                hash_ids_to_file_viewing_stats = HydrusData.BuildKeyToListDict( ( ( hash_id, ( canvas_type, last_viewed_timestamp, views, viewtime ) ) for ( hash_id, canvas_type, last_viewed_timestamp, views, viewtime ) in self._Execute( 'SELECT hash_id, canvas_type, last_viewed_timestamp, views, viewtime FROM {} CROSS JOIN file_viewing_stats USING ( hash_id );'.format( temp_table_name ) ) ) )
                
                hash_ids_to_file_viewing_stats_managers = { hash_id : ClientMediaManagers.FileViewingStatsManager( file_viewing_stats ) for ( hash_id, file_viewing_stats ) in hash_ids_to_file_viewing_stats.items() }
                
                hash_ids_to_file_modified_timestamps = dict( self._Execute( 'SELECT hash_id, file_modified_timestamp FROM {} CROSS JOIN file_modified_timestamps USING ( hash_id );'.format( temp_table_name ) ) )
                
                hash_ids_to_domain_modified_timestamps = HydrusData.BuildKeyToListDict( ( ( hash_id, ( domain, timestamp ) ) for ( hash_id, domain, timestamp ) in self._Execute( 'SELECT hash_id, domain, file_modified_timestamp FROM {} CROSS JOIN file_domain_modified_timestamps USING ( hash_id ) CROSS JOIN url_domains USING ( domain_id );'.format( temp_table_name ) ) ) )
                
                hash_ids_to_archive_timestamps = self.modules_files_inbox.GetHashIdsToArchiveTimestamps( temp_table_name )
                
                hash_ids_to_local_file_deletion_reasons = self.modules_files_storage.GetHashIdsToFileDeletionReasons( temp_table_name )
                
                hash_ids_to_current_file_service_ids = { hash_id : [ file_service_id for ( file_service_id, timestamp ) in file_service_ids_and_timestamps ] for ( hash_id, file_service_ids_and_timestamps ) in hash_ids_to_current_file_service_ids_and_timestamps.items() }
                
                hash_ids_to_tags_managers = self._GetForceRefreshTagsManagersWithTableHashIds( missing_hash_ids, temp_table_name, hash_ids_to_current_file_service_ids = hash_ids_to_current_file_service_ids )
                
                has_exif_hash_ids = self.modules_files_metadata_basic.GetHasEXIFHashIds( temp_table_name )
                has_human_readable_embedded_metadata_hash_ids = self.modules_files_metadata_basic.GetHasHumanReadableEmbeddedMetadataHashIds( temp_table_name )
                has_icc_profile_hash_ids = self.modules_files_metadata_basic.GetHasICCProfileHashIds( temp_table_name )
                
            
            # build it
            
            service_ids_to_service_keys = self.modules_services.GetServiceIdsToServiceKeys()
            
            missing_media_results = []
            
            for hash_id in missing_hash_ids:
                
                tags_manager = hash_ids_to_tags_managers[ hash_id ]
                
                #
                
                current_file_service_keys_to_timestamps = { service_ids_to_service_keys[ service_id ] : timestamp for ( service_id, timestamp ) in hash_ids_to_current_file_service_ids_and_timestamps[ hash_id ] }
                
                deleted_file_service_keys_to_timestamps = { service_ids_to_service_keys[ service_id ] : ( timestamp, original_timestamp ) for ( service_id, timestamp, original_timestamp ) in hash_ids_to_deleted_file_service_ids_and_timestamps[ hash_id ] }
                
                pending_file_service_keys = { service_ids_to_service_keys[ service_id ] for service_id in hash_ids_to_pending_file_service_ids[ hash_id ] }
                
                petitioned_file_service_keys = { service_ids_to_service_keys[ service_id ] for service_id in hash_ids_to_petitioned_file_service_ids[ hash_id ] }
                
                inbox = hash_id in self.modules_files_inbox.inbox_hash_ids
                
                urls = hash_ids_to_urls[ hash_id ]
                
                service_ids_to_filenames = dict( hash_ids_to_service_ids_and_filenames[ hash_id ] )
                
                service_keys_to_filenames = { service_ids_to_service_keys[ service_id ] : filename for ( service_id, filename ) in service_ids_to_filenames.items() }
                
                timestamp_manager = ClientMediaManagers.TimestampManager()
                
                if hash_id in hash_ids_to_file_modified_timestamps:
                    
                    timestamp_manager.SetFileModifiedTimestamp( hash_ids_to_file_modified_timestamps[ hash_id ] )
                    
                
                if hash_id in hash_ids_to_domain_modified_timestamps:
                    
                    for ( domain, modified_timestamp ) in hash_ids_to_domain_modified_timestamps[ hash_id ]:
                        
                        timestamp_manager.SetDomainModifiedTimestamp( domain, modified_timestamp )
                        
                    
                
                if hash_id in hash_ids_to_archive_timestamps:
                    
                    timestamp_manager.SetArchivedTimestamp( hash_ids_to_archive_timestamps[ hash_id ] )
                    
                
                if hash_id in hash_ids_to_local_file_deletion_reasons:
                    
                    local_file_deletion_reason = hash_ids_to_local_file_deletion_reasons[ hash_id ]
                    
                else:
                    
                    local_file_deletion_reason = None
                    
                
                locations_manager = ClientMediaManagers.LocationsManager(
                    current_file_service_keys_to_timestamps,
                    deleted_file_service_keys_to_timestamps,
                    pending_file_service_keys,
                    petitioned_file_service_keys,
                    inbox = inbox,
                    urls = urls,
                    service_keys_to_filenames = service_keys_to_filenames,
                    timestamp_manager = timestamp_manager,
                    local_file_deletion_reason = local_file_deletion_reason
                )
                
                #
                
                service_keys_to_ratings = { service_ids_to_service_keys[ service_id ] : rating for ( service_id, rating ) in hash_ids_to_local_ratings[ hash_id ] }
                
                ratings_manager = ClientMediaManagers.RatingsManager( service_keys_to_ratings )
                
                #
                
                if hash_id in hash_ids_to_names_and_notes:
                    
                    names_to_notes = dict( hash_ids_to_names_and_notes[ hash_id ] )
                    
                else:
                    
                    names_to_notes = dict()
                    
                
                notes_manager = ClientMediaManagers.NotesManager( names_to_notes )
                
                #
                
                if hash_id in hash_ids_to_file_viewing_stats_managers:
                    
                    file_viewing_stats_manager = hash_ids_to_file_viewing_stats_managers[ hash_id ]
                    
                else:
                    
                    file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager.STATICGenerateEmptyManager()
                    
                
                #
                
                if hash_id in hash_ids_to_info:
                    
                    file_info_manager = hash_ids_to_info[ hash_id ]
                    
                else:
                    
                    hash = missing_hash_ids_to_hashes[ hash_id ]
                    
                    file_info_manager = ClientMediaManagers.FileInfoManager( hash_id, hash )
                    
                
                file_info_manager.has_exif = hash_id in has_exif_hash_ids
                file_info_manager.has_human_readable_embedded_metadata = hash_id in has_human_readable_embedded_metadata_hash_ids
                file_info_manager.has_icc_profile = hash_id in has_icc_profile_hash_ids
                
                missing_media_results.append( ClientMediaResult.MediaResult( file_info_manager, tags_manager, locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager ) )
                
            
            self._weakref_media_result_cache.AddMediaResults( missing_media_results )
            
            cached_media_results.extend( missing_media_results )
            
        
        media_results = cached_media_results
        
        if sorted:
            
            hash_ids_to_media_results = { media_result.GetHashId() : media_result for media_result in media_results }
            
            media_results = [ hash_ids_to_media_results[ hash_id ] for hash_id in hash_ids if hash_id in hash_ids_to_media_results ]
            
        
        return media_results
        
    
    def _GetMediaResultFromHash( self, hash ) -> ClientMediaResult.MediaResult:
        
        media_results = self._GetMediaResultsFromHashes( [ hash ] )
        
        return media_results[0]
        
    
    def _GetMediaResultsFromHashes( self, hashes: typing.Collection[ bytes ], sorted: bool = False ) -> typing.List[ ClientMediaResult.MediaResult ]:
        
        query_hash_ids = set( self.modules_hashes_local_cache.GetHashIds( hashes ) )
        
        media_results = self._GetMediaResults( query_hash_ids )
        
        if sorted:
            
            if len( hashes ) > len( query_hash_ids ):
                
                hashes = HydrusData.DedupeList( hashes )
                
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
            
            media_results = [ hashes_to_media_results[ hash ] for hash in hashes if hash in hashes_to_media_results ]
            
        
        return media_results
        
    
    def _GetNumsPending( self ):
        
        services = self.modules_services.GetServices( ( HC.TAG_REPOSITORY, HC.FILE_REPOSITORY, HC.IPFS ) )
        
        pendings = {}
        
        for service in services:
            
            service_key = service.GetServiceKey()
            service_type = service.GetServiceType()
            
            service_id = self.modules_services.GetServiceId( service_key )
            
            info_types = set()
            
            if service_type in ( HC.FILE_REPOSITORY, HC.IPFS ):
                
                info_types = { HC.SERVICE_INFO_NUM_PENDING_FILES, HC.SERVICE_INFO_NUM_PETITIONED_FILES }
                
            elif service_type == HC.TAG_REPOSITORY:
                
                info_types = { HC.SERVICE_INFO_NUM_PENDING_MAPPINGS, HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS, HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS, HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS, HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS, HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS }
                
            
            pendings[ service_key ] = self._GetServiceInfoSpecific( service_id, service_type, info_types )
            
        
        return pendings
        
    
    def _GetOptions( self ):
        
        result = self._Execute( 'SELECT options FROM options;' ).fetchone()
        
        if result is None:
            
            options = ClientDefaults.GetClientDefaultOptions()
            
            self._Execute( 'INSERT INTO options ( options ) VALUES ( ? );', ( options, ) )
            
        else:
            
            ( options, ) = result
            
            default_options = ClientDefaults.GetClientDefaultOptions()
            
            for key in default_options:
                
                if key not in options: options[ key ] = default_options[ key ]
                
            
        
        return options
        
    
    def _GetPending( self, service_key, content_types, ideal_weight = 100 ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        service = self.modules_services.GetService( service_id )
        
        service_type = service.GetServiceType()
        
        if service_type in HC.REPOSITORIES:
            
            account = service.GetAccount()
            
            client_to_server_update = HydrusNetwork.ClientToServerUpdate()
            
            if service_type == HC.TAG_REPOSITORY:
                
                if HC.CONTENT_TYPE_MAPPINGS in content_types:
                    
                    if account.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_CREATE ):
                        
                        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( service_id )
                        
                        pending_dict = HydrusData.BuildKeyToListDict( self._Execute( 'SELECT tag_id, hash_id FROM ' + pending_mappings_table_name + ' ORDER BY tag_id LIMIT ?;', ( ideal_weight, ) ) )
                        
                        pending_mapping_ids = list( pending_dict.items() )
                        
                        # dealing with a scary situation when (due to some bug) mappings are current and pending. they get uploaded, but the content update makes no changes, so we cycle infitely!
                        addable_pending_mapping_ids = self.modules_mappings_storage.FilterExistingUpdateMappings( service_id, pending_mapping_ids, HC.CONTENT_UPDATE_ADD )
                        
                        pending_mapping_weight = sum( ( len( hash_ids ) for ( tag_id, hash_ids ) in pending_mapping_ids ) )
                        addable_pending_mapping_weight = sum( ( len( hash_ids ) for ( tag_id, hash_ids ) in addable_pending_mapping_ids ) )
                        
                        if pending_mapping_weight != addable_pending_mapping_weight:
                            
                            message = 'Hey, while going through the pending tags to upload, it seemed some were simultaneously already in the \'current\' state. This looks like a bug.'
                            message += os.linesep * 2
                            message += 'Please run _database->check and repair->fix logically inconsistent mappings_. If everything seems good after that and you do not get this message again, you should be all fixed. If not, you may need to regenerate your mappings storage cache under the \'database\' menu. If that does not work, hydev would like to know about it!'
                            
                            HydrusData.ShowText( message )
                            
                            raise HydrusExceptions.VetoException( 'Logically inconsistent mappings detected!' )
                            
                        
                        for ( tag_id, hash_ids ) in pending_mapping_ids:
                            
                            tag = self.modules_tags_local_cache.GetTag( tag_id )
                            hashes = self.modules_hashes_local_cache.GetHashes( hash_ids )
                            
                            content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag, hashes ) )
                            
                            client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content )
                            
                        
                    
                    if account.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_PETITION ):
                        
                        petitioned_dict = HydrusData.BuildKeyToListDict( [ ( ( tag_id, reason_id ), hash_id ) for ( tag_id, hash_id, reason_id ) in self._Execute( 'SELECT tag_id, hash_id, reason_id FROM ' + petitioned_mappings_table_name + ' ORDER BY reason_id LIMIT ?;', ( ideal_weight, ) ) ] )
                        
                        petitioned_mapping_ids = list( petitioned_dict.items() )
                        
                        # dealing with a scary situation when (due to some bug) mappings are deleted and petitioned. they get uploaded, but the content update makes no changes, so we cycle infitely!
                        deletable_and_petitioned_mappings = self.modules_mappings_storage.FilterExistingUpdateMappings(
                            service_id,
                            [ ( tag_id, hash_ids ) for ( ( tag_id, reason_id ), hash_ids ) in petitioned_mapping_ids ],
                            HC.CONTENT_UPDATE_DELETE
                        )
                        
                        petitioned_mapping_weight = sum( ( len( hash_ids ) for ( tag_id, hash_ids ) in petitioned_mapping_ids ) )
                        deletable_petitioned_mapping_weight = sum( ( len( hash_ids ) for ( tag_id, hash_ids ) in deletable_and_petitioned_mappings ) )
                        
                        if petitioned_mapping_weight != deletable_petitioned_mapping_weight:
                            
                            message = 'Hey, while going through the petitioned tags to upload, it seemed some were simultaneously already in the \'deleted\' state. This looks like a bug.'
                            message += os.linesep * 2
                            message += 'Please run _database->check and repair->fix logically inconsistent mappings_. If everything seems good after that and you do not get this message again, you should be all fixed. If not, you may need to regenerate your mappings storage cache under the \'database\' menu. If that does not work, hydev would like to know about it!'
                            
                            HydrusData.ShowText( message )
                            
                            raise HydrusExceptions.VetoException( 'Logically inconsistent mappings detected!' )
                            
                        
                        for ( ( tag_id, reason_id ), hash_ids ) in petitioned_mapping_ids:
                            
                            tag = self.modules_tags_local_cache.GetTag( tag_id )
                            hashes = self.modules_hashes_local_cache.GetHashes( hash_ids )
                            
                            reason = self.modules_texts.GetText( reason_id )
                            
                            content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag, hashes ) )
                            
                            client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason )
                            
                        
                    
                
                if HC.CONTENT_TYPE_TAG_PARENTS in content_types:
                    
                    if account.HasPermission( HC.CONTENT_TYPE_TAG_PARENTS, HC.PERMISSION_ACTION_PETITION ):
                        
                        pending = self._Execute( 'SELECT child_tag_id, parent_tag_id, reason_id FROM tag_parent_petitions WHERE service_id = ? AND status = ? ORDER BY reason_id LIMIT 1;', ( service_id, HC.CONTENT_STATUS_PENDING ) ).fetchall()
                        
                        for ( child_tag_id, parent_tag_id, reason_id ) in pending:
                            
                            child_tag = self.modules_tags_local_cache.GetTag( child_tag_id )
                            parent_tag = self.modules_tags_local_cache.GetTag( parent_tag_id )
                            
                            reason = self.modules_texts.GetText( reason_id )
                            
                            content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag, parent_tag ) )
                            
                            client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason )
                            
                        
                        petitioned = self._Execute( 'SELECT child_tag_id, parent_tag_id, reason_id FROM tag_parent_petitions WHERE service_id = ? AND status = ? ORDER BY reason_id LIMIT ?;', ( service_id, HC.CONTENT_STATUS_PETITIONED, ideal_weight ) ).fetchall()
                        
                        for ( child_tag_id, parent_tag_id, reason_id ) in petitioned:
                            
                            child_tag = self.modules_tags_local_cache.GetTag( child_tag_id )
                            parent_tag = self.modules_tags_local_cache.GetTag( parent_tag_id )
                            
                            reason = self.modules_texts.GetText( reason_id )
                            
                            content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag, parent_tag ) )
                            
                            client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason )
                            
                        
                    
                
                if HC.CONTENT_TYPE_TAG_SIBLINGS in content_types:
                    
                    if account.HasPermission( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.PERMISSION_ACTION_PETITION ):
                        
                        pending = self._Execute( 'SELECT bad_tag_id, good_tag_id, reason_id FROM tag_sibling_petitions WHERE service_id = ? AND status = ? ORDER BY reason_id LIMIT ?;', ( service_id, HC.CONTENT_STATUS_PENDING, ideal_weight ) ).fetchall()
                        
                        for ( bad_tag_id, good_tag_id, reason_id ) in pending:
                            
                            bad_tag = self.modules_tags_local_cache.GetTag( bad_tag_id )
                            good_tag = self.modules_tags_local_cache.GetTag( good_tag_id )
                            
                            reason = self.modules_texts.GetText( reason_id )
                            
                            content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag, good_tag ) )
                            
                            client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason )
                            
                        
                        petitioned = self._Execute( 'SELECT bad_tag_id, good_tag_id, reason_id FROM tag_sibling_petitions WHERE service_id = ? AND status = ? ORDER BY reason_id LIMIT ?;', ( service_id, HC.CONTENT_STATUS_PETITIONED, ideal_weight ) ).fetchall()
                        
                        for ( bad_tag_id, good_tag_id, reason_id ) in petitioned:
                            
                            bad_tag = self.modules_tags_local_cache.GetTag( bad_tag_id )
                            good_tag = self.modules_tags_local_cache.GetTag( good_tag_id )
                            
                            reason = self.modules_texts.GetText( reason_id )
                            
                            content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag, good_tag ) )
                            
                            client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason )
                            
                        
                    
                
            elif service_type == HC.FILE_REPOSITORY:
                
                if HC.CONTENT_TYPE_FILES in content_types:
                    
                    if account.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_CREATE ):
                        
                        result = self.modules_files_storage.GetAPendingHashId( service_id )
                        
                        if result is not None:
                            
                            hash_id = result
                            
                            media_result = self._GetMediaResults( ( hash_id, ) )[ 0 ]
                            
                            return media_result
                            
                        
                    
                    if account.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_PETITION ):
                        
                        petitioned_rows = self.modules_files_storage.GetSomePetitionedRows( service_id )
                        
                        for ( reason_id, hash_ids ) in petitioned_rows:
                            
                            hashes = self.modules_hashes_local_cache.GetHashes( hash_ids )
                            
                            reason = self.modules_texts.GetText( reason_id )
                            
                            content = HydrusNetwork.Content( HC.CONTENT_TYPE_FILES, hashes )
                            
                            client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason )
                            
                        
                    
                
            
            if client_to_server_update.HasContent():
                
                return client_to_server_update
                
            
        elif service_type == HC.IPFS:
            
            result = self.modules_files_storage.GetAPendingHashId( service_id )
            
            if result is not None:
                
                hash_id = result
                
                media_result = self._GetMediaResults( ( hash_id, ) )[ 0 ]
                
                return media_result
                
            
            while True:
                
                result = self.modules_files_storage.GetAPetitionedHashId( service_id )
                
                if result is None:
                    
                    break
                    
                else:
                    
                    hash_id = result
                    
                    hash = self.modules_hashes_local_cache.GetHash( hash_id )
                    
                    try:
                        
                        multihash = self.modules_service_paths.GetServiceFilename( service_id, hash_id )
                        
                    except HydrusExceptions.DataMissing:
                        
                        # somehow this file exists in ipfs (or at least is petitioned), but there is no multihash.
                        # this is probably due to a legacy sync issue
                        # so lets just process that now and continue
                        # in future we'll have ipfs service sync to repopulate missing filenames
                        
                        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ) )
                        
                        service_keys_to_content_updates = { service_key : [ content_update ] }
                        
                        self._ProcessContentUpdates( service_keys_to_content_updates )
                        
                        continue
                        
                    
                    return ( hash, multihash )
                    
                
            
        
        return None
        
    
    def _GetPossibleAdditionalDBFilenames( self ):
        
        paths = HydrusDB.HydrusDB._GetPossibleAdditionalDBFilenames( self )
        
        paths.append( 'mpv.conf' )
        
        return paths
        
    
    def _GetRecentTags( self, service_key ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        # we could be clever and do LIMIT and ORDER BY in the delete, but not all compilations of SQLite have that turned on, so let's KISS
        
        tag_ids_to_timestamp = { tag_id : timestamp for ( tag_id, timestamp ) in self._Execute( 'SELECT tag_id, timestamp FROM recent_tags WHERE service_id = ?;', ( service_id, ) ) }
        
        def sort_key( key ):
            
            return tag_ids_to_timestamp[ key ]
            
        
        newest_first = list(tag_ids_to_timestamp.keys())
        
        newest_first.sort( key = sort_key, reverse = True )
        
        num_we_want = HG.client_controller.new_options.GetNoneableInteger( 'num_recent_tags' )
        
        if num_we_want == None:
            
            num_we_want = 20
            
        
        decayed = newest_first[ num_we_want : ]
        
        if len( decayed ) > 0:
            
            self._ExecuteMany( 'DELETE FROM recent_tags WHERE service_id = ? AND tag_id = ?;', ( ( service_id, tag_id ) for tag_id in decayed ) )
            
        
        sorted_recent_tag_ids = newest_first[ : num_we_want ]
        
        tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = sorted_recent_tag_ids )
        
        sorted_recent_tags = [ tag_ids_to_tags[ tag_id ] for tag_id in sorted_recent_tag_ids ]
        
        return sorted_recent_tags
        
    
    def _GetRelatedTagCountsForOneTag( self, tag_display_type, file_service_id, tag_service_id, search_tag_id, max_num_files_to_search, stop_time_for_finding_results = None ) -> typing.Tuple[ collections.Counter, bool ]:
        
        # a user provided the basic idea here
        
        # we are saying get me all the tags for all the hashes this tag has
        # specifying namespace is critical to increase search speed, otherwise we actually are searching all tags for tags
        # we also call this with single specific file domains to keep things fast
        
        # this table selection is hacky as anything, but simpler than GetMappingAndTagTables for now
        
        # this would be an ideal location to have a normal-acting cache of results
        # a two-table-per service-cross-reference thing with cache entry + a creation timestamp and the actual mappings. invalidate on age or some tag changes I guess
        # then here we'll poll the search tag to give results, invalidate old ones, then populate as needed and return
        # only cache what you finish though!
        
        mappings_table_names = []
        
        if file_service_id == self.modules_services.combined_file_service_id:
            
            ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( tag_service_id )
            
            mappings_table_names.extend( [ current_mappings_table_name, pending_mappings_table_name ] )
            
        else:
            
            if tag_display_type == ClientTags.TAG_DISPLAY_ACTUAL:
                
                ( cache_current_display_mappings_table_name, cache_pending_display_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
                
                mappings_table_names.extend( [ cache_current_display_mappings_table_name, cache_pending_display_mappings_table_name ] )
                
            else:
                
                statuses_to_table_names = self.modules_mappings_storage.GetFastestStorageMappingTableNames( file_service_id, tag_service_id )
                
                mappings_table_names.extend( [ statuses_to_table_names[ HC.CONTENT_STATUS_CURRENT ], statuses_to_table_names[ HC.CONTENT_STATUS_PENDING ] ] )
                
            
        
        # note we used to filter by namespace here and needed the tags table, but no longer. might come back one day, but might be more trouble than it is worth
        # tags_table_name = self.modules_tag_search.GetTagsTableName( file_service_id, tag_service_id )
        
        # while this searches pending and current tags, it does not cross-reference current and pending on the same file, oh well!
        
        cancelled_hook = None
        
        if stop_time_for_finding_results is not None:
            
            def cancelled_hook():
                
                return HydrusData.TimeHasPassedPrecise( stop_time_for_finding_results )
                
            
        
        results_dict = collections.Counter()
        
        we_stopped_early = False
        
        for mappings_table_name in mappings_table_names:
            
            # if we do the straight-up 'SELECT tag_id, COUNT( * ) FROM {} WHERE hash_id IN ( SELECT hash_id FROM {} WHERE tag_id = {} ) GROUP BY tag_id;
            # then this is not easily cancellable. since it is working by hash_id, it doesn't know any counts until it knows all of them and is finished
            # trying to break it into two with a temp integer table runs into the same issue or needs us to pull a bunch of ( tag_id, 1 ) counts
            # since we'll be grabbing tag_ids with 1 count anyway for cancel tech, let's count them ourselves and trust the overhead isn't killer
            
            # UPDATE: I added the ORDER BY RANDOM() LIMIT 1000 here as a way to better sample. We don't care about all results, we care about samples
            # Unfortunately I think I have to do the RANDOM, since non-random search will bias the sample to early files etc...
            # However this reduces the search space significantly, although I have to wangle some other numbers in the parent method
            
            # this may cause laggy cancel tech since I think the whole order by random has to be done before any results will come back, which for '1girl' is going to be millions of rows...
            # we'll see how it goes
            
            search_predicate = 'hash_id IN ( SELECT hash_id FROM {} WHERE tag_id = {} ORDER BY RANDOM() LIMIT {} )'.format( mappings_table_name, search_tag_id, max_num_files_to_search )
            
            query = 'SELECT tag_id FROM {} WHERE {};'.format( mappings_table_name, search_predicate )
            
            cursor = self._Execute( query )
            
            loop_of_results = self._STI( HydrusDB.ReadFromCancellableCursor( cursor, 1024, cancelled_hook = cancelled_hook ) )
            
            # counter can just take a list of gubbins like this
            results_dict.update( loop_of_results )
            
            if cancelled_hook():
                
                we_stopped_early = True
                
                break
                
            
        
        return ( results_dict, we_stopped_early )
        
    
    def _GetRelatedTags( self, file_service_key, tag_service_key, search_tags, max_time_to_take = 0.5, max_results = 100, concurrence_threshold = 0.04, search_tag_slices_weight_dict = None, result_tag_slices_weight_dict = None, other_tags_to_exclude = None ):
        
        # a user provided the basic idea here
        
        def get_weight_from_dict( tag, d ):
            
            if d is None:
                
                return 1.0
                
            
            ( n, s ) = HydrusTags.SplitTag( tag )
            
            if n in d:
                
                return d[ n ]
                
            else:
                
                return d[ ':' ]
                
            
        
        num_tags_searched = 0
        num_tags_to_search = 0
        num_skipped = 0
        
        stop_time_for_finding_results = HydrusData.GetNowPrecise() + ( max_time_to_take * 0.85 )
        
        search_tags = [ search_tag for search_tag in search_tags if get_weight_from_dict( search_tag, search_tag_slices_weight_dict ) != 0.0 ]
        
        if len( search_tags ) == 0:
            
            return ( num_tags_searched, num_tags_to_search, num_skipped, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, value = 'no search tags to work with!' ) ] )
            
        
        tag_display_type = ClientTags.TAG_DISPLAY_ACTUAL
        
        tag_service_id = self.modules_services.GetServiceId( tag_service_key )
        file_service_id = self.modules_services.GetServiceId( file_service_key )
        
        if tag_display_type == ClientTags.TAG_DISPLAY_ACTUAL:
            
            search_tags = self.modules_tag_siblings.GetIdeals( tag_display_type, tag_service_key, search_tags )
            
            # I had a thing here that added the parents, but it gave some whack results compared to what you expected
            
        
        search_tag_ids_to_search_tags = self.modules_tags_local_cache.GetTagIdsToTags( tags = search_tags )
        
        with self._MakeTemporaryIntegerTable( search_tag_ids_to_search_tags.keys(), 'tag_id' ) as temp_tag_id_table_name:
            
            search_tag_ids_to_total_counts = collections.Counter( { tag_id : abs( current_count ) + abs( pending_count ) for ( tag_id, current_count, pending_count ) in self.modules_mappings_counts.GetCountsForTags( tag_display_type, file_service_id, tag_service_id, temp_tag_id_table_name ) } )
            
        
        #
        
        # two things here:
        # 1
            # we don't really want to use '1girl' and friends as search tags here, since the search domain is so huge
            # so, we go for the smallest count tags first. they have interesting suggestions
        # 2
            # we have an options structure for value of namespace, so we'll do biggest numbers first
        
        search_tag_ids_flat_sorted_ascending = sorted( search_tag_ids_to_total_counts.items(), key = lambda row: ( - get_weight_from_dict( search_tag_ids_to_search_tags[ row[0] ], search_tag_slices_weight_dict ), row[1] ) )
        
        search_tags_sorted_ascending = []
        
        for ( search_tag_id, count ) in search_tag_ids_flat_sorted_ascending:
            
            # I had a negative count IRL, it was a busted A/C cache, caused heaps of trouble with later square root causing imaginary numbers!!!
            # Having count 0 here is only _supposed_ to happen if the user is asking about stuff they just pended in the dialog now, before hitting ok, or if they are searching local domain from only all known files content etc...
            if count <= 0:
                
                num_skipped += 1
                
                continue
                
            
            search_tag = search_tag_ids_to_search_tags[ search_tag_id ]
            
            search_tags_sorted_ascending.append( search_tag )
            
        
        num_tags_to_search = len( search_tags_sorted_ascending )
        
        if num_tags_to_search == 0:
            
            # all have count 0 or were filtered out by 0.0 weight
            
            return ( num_tags_searched, num_tags_to_search, num_skipped, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, value = 'no related tags found!' ) ] )
            
        
        #
        
        # max_num_files_to_search = 1000
        
        # 1000 gives us a decent sample mate, no matter the population size
        # we can probably go lower than this, or rather base it dynamically on the concurrence_threshold.
        # if a tag t has to have 0.04 out of n to match, then can't we figure out a sample size n that is 97% likely to catch t>=1 for the least likely qualifying t?
        #
        # hydev attempts to do stats here, potential ruh roh
        # what sample size do we need to have 97% liklihood of getting at least one of the least likely (how many draws of 1-in-25 to get at least one hit)
        # this is cumulative binomial probability, maybe, with success chance 0.04 and result X >= 1. what's the n for P(X>=1) = 0.97?
        # this is probably wrong and stupid, but whatever
        # for difficult values of X I think we need some inverse cumulative distribution function, which is beyond my expertise
        # but isn't p(X>=1) the same as 1 - P(X=0)? and chance of none happening is just (24/25)^n
        # (24/25)^n = 0.03
        # hydev last did this for real 19 years ago, but:
        # n = log( 0.03 ) / log( 0.96 ) = 86
        # 143 for 0.997
        # actually sounds about right?????
        # a secondary problem here is when we correct our scores later on, we've got some low 'count' counts causing some variance and spiky ranking, particularly at the bottom
        # figuring this out is a variance confidence problem, which is beyond me
        # to smooth them out, we'll just multiple our n a bit. ideally we'd pick an x in P(X>=x) large enough that the granular steps reduce variance
        # in the end we spent a bunch of brainpower rationalising a guess of 1,000 down to 500-odd, but at least there's a framework here to iterate on
        
        desired_confidence = 0.997
        chance_of_success = concurrence_threshold
        
        max_num_files_to_search = max( 50, int( math.ceil( math.log( 1 - desired_confidence ) / math.log( 1 - chance_of_success ) ) ) )
        
        magical_later_multiplication_smoothing_coefficient = 4
        
        max_num_files_to_search *= magical_later_multiplication_smoothing_coefficient
        
        search_tag_ids_to_tag_ids_to_matching_counts = {}
        
        for search_tag in search_tags_sorted_ascending:
            
            search_tag_id = self.modules_tags_local_cache.GetTagId( search_tag )
            
            ( tag_ids_to_matching_counts, it_stopped_early ) = self._GetRelatedTagCountsForOneTag( tag_display_type, file_service_id, tag_service_id, search_tag_id, max_num_files_to_search, stop_time_for_finding_results = stop_time_for_finding_results )
            
            if search_tag_id in tag_ids_to_matching_counts:
                
                del tag_ids_to_matching_counts[ search_tag_id ] # duh, don't recommend your 100% matching self
                
            
            search_tag_ids_to_tag_ids_to_matching_counts[ search_tag_id ] = tag_ids_to_matching_counts
            
            if it_stopped_early:
                
                break
                
            
            num_tags_searched += 1
            
        
        #
        
        # now let's filter stuff we don't want
        
        # we don't want to suggest ourselves
        tag_ids_to_exclude = set( search_tag_ids_to_search_tags.keys() )
        
        if other_tags_to_exclude is not None:
            
            # this is the list of all tags in the list, don't want them either
            other_tag_ideals = self.modules_tag_siblings.GetIdeals( tag_display_type, tag_service_key, other_tags_to_exclude )
            
            other_tag_ids = set( self.modules_tags_local_cache.GetTagIdsToTags( tags = other_tag_ideals ).keys() )
            
            tag_ids_to_exclude.update( other_tag_ids )
            
        
        for ( search_tag_id, parent_tag_ids ) in self.modules_tag_parents.GetTagsToAncestors( tag_display_type, tag_service_id, set( tag_ids_to_exclude ) ).items():
            
            # we don't want any of their parents either!
            tag_ids_to_exclude.update( parent_tag_ids )
            
        
        unfiltered_search_tag_ids_to_tag_ids_to_matching_counts = search_tag_ids_to_tag_ids_to_matching_counts
        
        search_tag_ids_to_tag_ids_to_matching_counts = {}
        
        for ( search_tag_id, unfiltered_tag_ids_to_matching_counts ) in unfiltered_search_tag_ids_to_tag_ids_to_matching_counts.items():
            
            tag_ids_to_matching_counts = {}
            
            for ( suggestion_tag_id, suggestion_matching_count ) in unfiltered_tag_ids_to_matching_counts.items():
                
                if suggestion_tag_id in tag_ids_to_exclude:
                    
                    continue
                    
                
                tag_ids_to_matching_counts[ suggestion_tag_id ] = suggestion_matching_count
                
            
            search_tag_ids_to_tag_ids_to_matching_counts[ search_tag_id ] = tag_ids_to_matching_counts
            
        
        #
        
        # ok we have a bunch of counts here for different search tags, so let's figure out some normalised scores and merge them all
        
        all_tag_ids = set()
        
        for tag_ids_to_matching_counts in search_tag_ids_to_tag_ids_to_matching_counts.values():
            
            all_tag_ids.update( tag_ids_to_matching_counts.keys() )
            
        
        all_tag_ids.difference_update( search_tag_ids_to_search_tags.keys() )
        
        with self._MakeTemporaryIntegerTable( all_tag_ids, 'tag_id' ) as temp_tag_id_table_name:
            
            tag_ids_to_total_counts = { tag_id : abs( current_count ) + abs( pending_count ) for ( tag_id, current_count, pending_count ) in self.modules_mappings_counts.GetCountsForTags( tag_display_type, file_service_id, tag_service_id, temp_tag_id_table_name ) }
            
        
        tag_ids_to_total_counts.update( search_tag_ids_to_total_counts )
        
        tag_ids_to_scores = collections.Counter()
        
        # the master score is: number matching mappings found / square_root( suggestion_tag_count * search_tag_count )
        #
        # the dude said it was mostly arbitrary but came from, I think, P-TAG: Large Scale Automatic Generation of Personalized Annotation TAGs for the Web
        # he said it could do with tuning, so we'll see how it goes, but overall I am happy with it
        #
        # UPDATE: Adding the 'max_num_files_to_search' thing above skews the score here, so we need to adjust it so our score and concurrence thresholds still work!
        
        for ( search_tag_id, tag_ids_to_matching_counts ) in search_tag_ids_to_tag_ids_to_matching_counts.items():
            
            if search_tag_id not in tag_ids_to_total_counts:
                
                continue
                
            
            search_tag_count = tag_ids_to_total_counts[ search_tag_id ]
            
            matching_count_multiplier = 1.0
            
            if search_tag_count > max_num_files_to_search:
                
                # had we searched everything, how much bigger would the results probably be?
                matching_count_multiplier = search_tag_count / max_num_files_to_search
                
            
            weight = get_weight_from_dict( search_tag_ids_to_search_tags[ search_tag_id ], search_tag_slices_weight_dict )
            
            for ( suggestion_tag_id, suggestion_matching_count ) in tag_ids_to_matching_counts.items():
                
                suggestion_matching_count *= matching_count_multiplier
                
                if suggestion_matching_count / search_tag_count < concurrence_threshold:
                    
                    # this result didn't turn up enough to be relevant
                    continue
                    
                
                if suggestion_tag_id not in tag_ids_to_total_counts:
                    
                    # probably a damaged A/C cache
                    continue
                    
                
                suggestion_tag_count = tag_ids_to_total_counts[ suggestion_tag_id ]
                
                score = suggestion_matching_count / ( ( abs( suggestion_tag_count ) * abs( search_tag_count ) ) ** 0.5 )
                
                if weight != 1.0:
                    
                    score *= weight
                    
                
                tag_ids_to_scores[ suggestion_tag_id ] += float( score )
                
            
        
        results_flat_sorted_descending = sorted( tag_ids_to_scores.items(), key = lambda row: row[1], reverse = True )
        
        tag_ids_to_scores = dict( results_flat_sorted_descending[ : max_results ] )
        
        #
        
        inclusive = True
        pending_count = 0
        
        tag_ids_to_full_counts = { tag_id : ( int( score * 1000 ), None, pending_count, None ) for ( tag_id, score ) in tag_ids_to_scores.items() }
        
        predicates = self.modules_tag_display.GeneratePredicatesFromTagIdsAndCounts( tag_display_type, tag_service_id, tag_ids_to_full_counts, inclusive )
        
        result_predicates = []
        
        for predicate in predicates:
            
            tag = predicate.GetValue()
            
            weight = get_weight_from_dict( tag, result_tag_slices_weight_dict )
            
            if weight == 0.0:
                
                continue
                
            
            if weight != 1.0:
                
                existing_count = predicate.GetCount()
                
                new_count = ClientSearch.PredicateCount( int( existing_count.min_current_count * weight ), 0, None, None )
                
                predicate.SetCount( new_count )
                
            
            result_predicates.append( predicate )
            
        
        return ( num_tags_searched, num_tags_to_search, num_skipped, result_predicates )
        
    
    def _GetRepositoryThumbnailHashesIDoNotHave( self, service_key ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        current_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT )
        
        needed_hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM {} NATURAL JOIN files_info WHERE mime IN {} EXCEPT SELECT hash_id FROM remote_thumbnails WHERE service_id = ?;'.format( current_files_table_name, HydrusData.SplayListForDB( HC.MIMES_WITH_THUMBNAILS ) ), ( service_id, ) ) )
        
        needed_hashes = []
        
        client_files_manager = HG.client_controller.client_files_manager
        
        for hash_id in needed_hash_ids:
            
            hash = self.modules_hashes_local_cache.GetHash( hash_id )
            
            if client_files_manager.LocklessHasThumbnail( hash ):
                
                self._Execute( 'INSERT OR IGNORE INTO remote_thumbnails ( service_id, hash_id ) VALUES ( ?, ? );', ( service_id, hash_id ) )
                
            else:
                
                needed_hashes.append( hash )
                
                if len( needed_hashes ) == 10000:
                    
                    return needed_hashes
                    
                
            
        
        return needed_hashes
        
    
    def _GetServiceInfo( self, service_key ):
        
        # TODO: move this to a clever module, and add a 'clear/recalc service info' func so I'm not doing that manually every time
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        service = self.modules_services.GetService( service_id )
        
        service_type = service.GetServiceType()
        
        if service_type in ( HC.COMBINED_LOCAL_FILE, HC.COMBINED_LOCAL_MEDIA, HC.LOCAL_FILE_DOMAIN, HC.LOCAL_FILE_UPDATE_DOMAIN, HC.FILE_REPOSITORY ):
            
            info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_VIEWABLE_FILES, HC.SERVICE_INFO_TOTAL_SIZE, HC.SERVICE_INFO_NUM_DELETED_FILES }
            
        elif service_type == HC.LOCAL_FILE_TRASH_DOMAIN:
            
            info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_VIEWABLE_FILES, HC.SERVICE_INFO_TOTAL_SIZE }
            
        elif service_type == HC.IPFS:
            
            info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_VIEWABLE_FILES, HC.SERVICE_INFO_TOTAL_SIZE }
            
        elif service_type == HC.LOCAL_TAG:
            
            info_types = { HC.SERVICE_INFO_NUM_FILE_HASHES, HC.SERVICE_INFO_NUM_TAGS, HC.SERVICE_INFO_NUM_MAPPINGS }
            
        elif service_type == HC.TAG_REPOSITORY:
            
            info_types = { HC.SERVICE_INFO_NUM_FILE_HASHES, HC.SERVICE_INFO_NUM_TAGS, HC.SERVICE_INFO_NUM_MAPPINGS, HC.SERVICE_INFO_NUM_DELETED_MAPPINGS }
            
        elif service_type in HC.RATINGS_SERVICES:
            
            info_types = { HC.SERVICE_INFO_NUM_FILE_HASHES }
            
        elif service_type == HC.LOCAL_BOORU:
            
            info_types = { HC.SERVICE_INFO_NUM_SHARES }
            
        else:
            
            info_types = set()
            
        
        service_info = self._GetServiceInfoSpecific( service_id, service_type, info_types )
        
        return service_info
        
    
    def _GetServiceInfoSpecific( self, service_id, service_type, info_types, calculate_missing = True ):
        
        info_types = set( info_types )
        
        results = { info_type : info for ( info_type, info ) in self._Execute( 'SELECT info_type, info FROM service_info WHERE service_id = ? AND info_type IN ' + HydrusData.SplayListForDB( info_types ) + ';', ( service_id, ) ) }
        
        if len( results ) != len( info_types ) and calculate_missing:
            
            info_types_hit = list( results.keys() )
            
            info_types_missed = info_types.difference( info_types_hit )
            
            for info_type in info_types_missed:
                
                info = None
                result = None
                
                save_it = True
                
                if service_type in HC.FILE_SERVICES:
                    
                    if info_type in ( HC.SERVICE_INFO_NUM_PENDING_FILES, HC.SERVICE_INFO_NUM_PETITIONED_FILES ):
                        
                        save_it = False
                        
                    
                    if info_type == HC.SERVICE_INFO_NUM_FILES:
                        
                        info = self.modules_files_storage.GetCurrentFilesCount( service_id )
                        
                    elif info_type == HC.SERVICE_INFO_NUM_VIEWABLE_FILES:
                        
                        info = self.modules_files_storage.GetCurrentFilesCount( service_id, only_viewable = True )
                        
                    elif info_type == HC.SERVICE_INFO_TOTAL_SIZE:
                        
                        info = self.modules_files_storage.GetCurrentFilesTotalSize( service_id )
                        
                    elif info_type == HC.SERVICE_INFO_NUM_DELETED_FILES:
                        
                        info = self.modules_files_storage.GetDeletedFilesCount( service_id )
                        
                    elif info_type == HC.SERVICE_INFO_NUM_PENDING_FILES:
                        
                        info = self.modules_files_storage.GetPendingFilesCount( service_id )
                        
                    elif info_type == HC.SERVICE_INFO_NUM_PETITIONED_FILES:
                        
                        info = self.modules_files_storage.GetPetitionedFilesCount( service_id )
                        
                    elif info_type == HC.SERVICE_INFO_NUM_INBOX:
                        
                        info = self.modules_files_storage.GetCurrentFilesInboxCount( service_id )
                        
                    
                elif service_type in HC.REAL_TAG_SERVICES:
                    
                    if info_type in ( HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS, HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS, HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS, HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS ):
                        
                        save_it = False
                        
                    
                    if info_type == HC.SERVICE_INFO_NUM_FILE_HASHES:
                        
                        info = self.modules_mappings_storage.GetCurrentFilesCount( service_id )
                        
                    elif info_type == HC.SERVICE_INFO_NUM_TAGS:
                        
                        info = self.modules_tag_search.GetTagCount( self.modules_services.combined_file_service_id, service_id )
                        
                    elif info_type == HC.SERVICE_INFO_NUM_MAPPINGS:
                        
                        info = self.modules_mappings_counts.GetTotalCurrentCount( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, service_id )
                        
                    elif info_type == HC.SERVICE_INFO_NUM_PENDING_MAPPINGS:
                        
                        # since pending is nearly always far smaller rowcount than current, if I pull this from a/c table, it is a HUGE waste of time and not faster than counting the raw table rows!
                        
                        info = self.modules_mappings_storage.GetPendingMappingsCount( service_id )
                        
                    elif info_type == HC.SERVICE_INFO_NUM_DELETED_MAPPINGS:
                        
                        # since pending is nearly always far smaller rowcount than current, if I pull this from a/c table, it is a HUGE waste of time and not faster than counting the raw table rows!
                        
                        info = self.modules_mappings_storage.GetDeletedMappingsCount( service_id )
                        
                    elif info_type == HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS:
                        
                        # since pending is nearly always far smaller rowcount than current, if I pull this from a/c table, it is a HUGE waste of time and not faster than counting the raw table rows!
                        
                        info = self.modules_mappings_storage.GetPetitionedMappingsCount( service_id )
                        
                    elif info_type == HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS:
                        
                        ( info, ) = self._Execute( 'SELECT COUNT( * ) FROM tag_sibling_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_PENDING ) ).fetchone()
                        
                    elif info_type == HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS:
                        
                        ( info, ) = self._Execute( 'SELECT COUNT( * ) FROM tag_sibling_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_PETITIONED ) ).fetchone()
                        
                    elif info_type == HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS:
                        
                        ( info, ) = self._Execute( 'SELECT COUNT( * ) FROM tag_parent_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_PENDING ) ).fetchone()
                        
                    elif info_type == HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS:
                        
                        ( info, ) = self._Execute( 'SELECT COUNT( * ) FROM tag_parent_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_PETITIONED ) ).fetchone()
                        
                    
                elif service_type in HC.STAR_RATINGS_SERVICES:
                    
                    if info_type == HC.SERVICE_INFO_NUM_FILE_HASHES:
                        
                        ( info, ) = self._Execute( 'SELECT COUNT( * ) FROM local_ratings WHERE service_id = ?;', ( service_id, ) ).fetchone()
                        
                    
                elif service_type == HC.LOCAL_RATING_INCDEC:
                    
                    if info_type == HC.SERVICE_INFO_NUM_FILE_HASHES:
                        
                        ( info, ) = self._Execute( 'SELECT COUNT( * ) FROM local_incdec_ratings WHERE service_id = ?;', ( service_id, ) ).fetchone()
                        
                    
                elif service_type == HC.LOCAL_BOORU:
                    
                    if info_type == HC.SERVICE_INFO_NUM_SHARES:
                        
                        ( info, ) = self._Execute( 'SELECT COUNT( * ) FROM yaml_dumps WHERE dump_type = ?;', ( ClientDBSerialisable.YAML_DUMP_ID_LOCAL_BOORU, ) ).fetchone()
                        
                    
                
                if info is None:
                    
                    info = 0
                    
                
                if save_it:
                    
                    self._Execute( 'INSERT INTO service_info ( service_id, info_type, info ) VALUES ( ?, ?, ? );', ( service_id, info_type, info ) )
                    
                
                results[ info_type ] = info
                
            
        
        return results
        
    
    def _GetSiteId( self, name ):
        
        result = self._Execute( 'SELECT site_id FROM imageboard_sites WHERE name = ?;', ( name, ) ).fetchone()
        
        if result is None:
            
            self._Execute( 'INSERT INTO imageboard_sites ( name ) VALUES ( ? );', ( name, ) )
            
            site_id = self._GetLastRowId()
            
        else:
            
            ( site_id, ) = result
            
        
        return site_id
        
    
    def _GetTrashHashes( self, limit = None, minimum_age = None ):
        
        if limit is None:
            
            limit_phrase = ''
            
        else:
            
            limit_phrase = ' LIMIT ' + str( limit )
            
        
        if minimum_age is None:
            
            age_phrase = ' ORDER BY timestamp ASC' # when deleting until trash is small enough, let's delete oldest first
            
        else:
            
            timestamp_cutoff = HydrusData.GetNow() - minimum_age
            
            age_phrase = ' WHERE timestamp < ' + str( timestamp_cutoff )
            
        
        current_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.trash_service_id, HC.CONTENT_STATUS_CURRENT )
        
        hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {}{}{};'.format( current_files_table_name, age_phrase, limit_phrase ) ) )
        
        hash_ids = self._FilterForFileDeleteLock( self.modules_services.trash_service_id, hash_ids )
        
        if HG.db_report_mode:
            
            message = 'When asked for '
            
            if limit is None:
                
                message += 'all the'
                
            else:
                
                message += 'at most ' + HydrusData.ToHumanInt( limit )
                
            
            message += ' trash files,'
            
            if minimum_age is not None:
                
                message += ' with minimum age ' + ClientData.TimestampToPrettyTimeDelta( timestamp_cutoff, just_now_threshold = 0 ) + ','
                
            
            message += ' I found ' + HydrusData.ToHumanInt( len( hash_ids ) ) + '.'
            
            HydrusData.ShowText( message )
            
        
        return self.modules_hashes_local_cache.GetHashes( hash_ids )
        
    
    def _ImportFile( self, file_import_job: ClientImportFiles.FileImportJob ):
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job starting db job' )
            
        
        file_import_options = file_import_job.GetFileImportOptions()
        
        destination_location_context = file_import_options.GetDestinationLocationContext()
        
        destination_location_context.FixMissingServices( ClientLocation.ValidLocalDomainsFilter )
        
        file_import_options.CheckReadyToImport()
        
        hash = file_import_job.GetHash()
        
        hash_id = self.modules_hashes_local_cache.GetHashId( hash )
        
        file_import_status = self.modules_files_metadata_rich.GetHashIdStatus( hash_id, prefix = 'file recognised by database' )
        
        if not file_import_status.AlreadyInDB():
            
            if HG.file_import_report_mode:
                
                HydrusData.ShowText( 'File import job adding new file' )
                
            
            ( size, mime, width, height, duration, num_frames, has_audio, num_words ) = file_import_job.GetFileInfo()
            
            if HG.file_import_report_mode:
                
                HydrusData.ShowText( 'File import job adding file info row' )
                
            
            self.modules_files_metadata_basic.AddFilesInfo( [ ( hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words ) ], overwrite = True )
            
            #
            
            perceptual_hashes = file_import_job.GetPerceptualHashes()
            
            if perceptual_hashes is not None:
                
                if HG.file_import_report_mode:
                    
                    HydrusData.ShowText( 'File import job associating perceptual_hashes' )
                    
                
                self.modules_similar_files.AssociatePerceptualHashes( hash_id, perceptual_hashes )
                
            
            if HG.file_import_report_mode:
                
                HydrusData.ShowText( 'File import job adding file to local file service' )
                
            
            #
            
            ( md5, sha1, sha512 ) = file_import_job.GetExtraHashes()
            
            self.modules_hashes.SetExtraHashes( hash_id, md5, sha1, sha512 )
            
            #
            
            self.modules_files_metadata_basic.SetHasEXIF( hash_id, file_import_job.HasEXIF() )
            self.modules_files_metadata_basic.SetHasHumanReadableEmbeddedMetadata( hash_id, file_import_job.HasHumanReadableEmbeddedMetadata() )
            self.modules_files_metadata_basic.SetHasICCProfile( hash_id, file_import_job.HasICCProfile() )
            
            #
            
            pixel_hash = file_import_job.GetPixelHash()
            
            if pixel_hash is None:
                
                self.modules_similar_files.ClearPixelHash( hash_id )
                
            else:
                
                pixel_hash_id = self.modules_hashes.GetHashId( pixel_hash )
                
                self.modules_similar_files.SetPixelHash( hash_id, pixel_hash_id )
                
            
            #
            
            file_modified_timestamp = file_import_job.GetFileModifiedTimestamp()
            
            self._Execute( 'REPLACE INTO file_modified_timestamps ( hash_id, file_modified_timestamp ) VALUES ( ?, ? );', ( hash_id, file_modified_timestamp ) )
            
            #
            
            file_info_manager = ClientMediaManagers.FileInfoManager( hash_id, hash, size, mime, width, height, duration, num_frames, has_audio, num_words )
            
            now = HydrusData.GetNow()
            
            for destination_file_service_key in destination_location_context.current_service_keys:
                
                destination_service_id = self.modules_services.GetServiceId( destination_file_service_key )
                
                self._AddFiles( destination_service_id, [ ( hash_id, now ) ] )
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, ( file_info_manager, now ) )
                
                self.pub_content_updates_after_commit( { destination_file_service_key : [ content_update ] } )
                
            
            #
            
            if file_import_options.AutomaticallyArchives():
                
                if HG.file_import_report_mode:
                    
                    HydrusData.ShowText( 'File import job archiving new file' )
                    
                
                self.modules_files_inbox.ArchiveFiles( ( hash_id, ) )
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, ( hash, ) )
                
                self.pub_content_updates_after_commit( { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] } )
                
            else:
                
                if HG.file_import_report_mode:
                    
                    HydrusData.ShowText( 'File import job inboxing new file' )
                    
                
                self.modules_files_inbox.InboxFiles( ( hash_id, ) )
                
            
            #
            
            if self._weakref_media_result_cache.HasFile( hash_id ):
                
                self._weakref_media_result_cache.DropMediaResult( hash_id, hash )
                
                self._controller.pub( 'new_file_info', { hash } )
                
            
            #
            
            file_import_status = ClientImportFiles.FileImportStatus( CC.STATUS_SUCCESSFUL_AND_NEW, hash, mime = mime )
            
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job done at db level, final status: {}'.format( file_import_status.ToString() ) )
            
        
        return file_import_status
        
    
    def _ImportUpdate( self, update_network_bytes, update_hash, mime ):
        
        try:
            
            HydrusSerialisable.CreateFromNetworkBytes( update_network_bytes )
            
        except:
            
            HydrusData.ShowText( 'Was unable to parse an incoming update!' )
            
            raise
            
        
        hash_id = self.modules_hashes_local_cache.GetHashId( update_hash )
        
        size = len( update_network_bytes )
        
        width = None
        height = None
        duration = None
        num_frames = None
        has_audio = None
        num_words = None
        
        client_files_manager = self._controller.client_files_manager
        
        client_files_manager.LocklessAddFileFromBytes( update_hash, mime, update_network_bytes )
        
        self.modules_files_metadata_basic.AddFilesInfo( [ ( hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words ) ], overwrite = True )
        
        now = HydrusData.GetNow()
        
        self._AddFiles( self.modules_services.local_update_service_id, [ ( hash_id, now ) ] )
        
    
    def _InitCaches( self ):
        
        # this occurs after db update, so is safe to reference things in there but also cannot be relied upon in db update
        
        HG.client_controller.frame_splash_status.SetText( 'preparing db caches' )
        
        HG.client_controller.frame_splash_status.SetSubtext( 'inbox' )
        
    
    def _InitExternalDatabases( self ):
        
        self._db_filenames[ 'external_caches' ] = 'client.caches.db'
        self._db_filenames[ 'external_mappings' ] = 'client.mappings.db'
        self._db_filenames[ 'external_master' ] = 'client.master.db'
        
    
    def _FilterInboxHashes( self, hashes: typing.Collection[ bytes ] ):
        
        hash_ids_to_hashes = self.modules_hashes_local_cache.GetHashIdsToHashes( hashes = hashes )
        
        inbox_hashes = { hash for ( hash_id, hash ) in hash_ids_to_hashes.items() if hash_id in self.modules_files_inbox.inbox_hash_ids }
        
        return inbox_hashes
        
    
    def _IsAnOrphan( self, test_type, possible_hash ):
        
        if self.modules_hashes.HasHash( possible_hash ):
            
            hash = possible_hash
            
            hash_id = self.modules_hashes_local_cache.GetHashId( hash )
            
            if test_type == 'file':
                
                orphan_hash_ids = self.modules_files_storage.FilterOrphanFileHashIds( ( hash_id, ) )
                
                return len( orphan_hash_ids ) == 1
                
            elif test_type == 'thumbnail':
                
                orphan_hash_ids = self.modules_files_storage.FilterOrphanThumbnailHashIds( ( hash_id, ) )
                
                return len( orphan_hash_ids ) == 1
                
            
        else:
            
            return True
            
        
    
    def _LoadModules( self ):
        
        self.modules_db_maintenance = ClientDBMaintenance.ClientDBMaintenance( self._c, self._db_dir, self._db_filenames )
        
        self._modules.append( self.modules_db_maintenance )
        
        self.modules_services = ClientDBServices.ClientDBMasterServices( self._c )
        
        self._modules.append( self.modules_services )
        
        self.modules_hashes = ClientDBMaster.ClientDBMasterHashes( self._c )
        
        self._modules.append( self.modules_hashes )
        
        self.modules_tags = ClientDBMaster.ClientDBMasterTags( self._c )
        
        self._modules.append( self.modules_tags )
        
        self.modules_urls = ClientDBMaster.ClientDBMasterURLs( self._c )
        
        self._modules.append( self.modules_urls )
        
        self.modules_texts = ClientDBMaster.ClientDBMasterTexts( self._c )
        
        self._modules.append( self.modules_texts )
        
        self.modules_serialisable = ClientDBSerialisable.ClientDBSerialisable( self._c, self._db_dir, self._cursor_transaction_wrapper, self.modules_services )
        
        self._modules.append( self.modules_serialisable )
        
        #
        
        self.modules_files_physical_storage = ClientDBFilesPhysicalStorage.ClientDBFilesPhysicalStorage( self._c, self._db_dir )
        
        self._modules.append( self.modules_files_physical_storage )
        
        self.modules_files_metadata_basic = ClientDBFilesMetadataBasic.ClientDBFilesMetadataBasic( self._c )
        
        self._modules.append( self.modules_files_metadata_basic )
        
        self.modules_files_viewing_stats = ClientDBFilesViewingStats.ClientDBFilesViewingStats( self._c )
        
        self._modules.append( self.modules_files_viewing_stats )
        
        #
        
        self.modules_url_map = ClientDBURLMap.ClientDBURLMap( self._c, self.modules_urls )
        
        self._modules.append( self.modules_url_map )
        
        self.modules_notes_map = ClientDBNotesMap.ClientDBNotesMap( self._c, self.modules_texts )
        
        self._modules.append( self.modules_notes_map )
        
        #
        
        self.modules_files_storage = ClientDBFilesStorage.ClientDBFilesStorage( self._c, self._cursor_transaction_wrapper, self.modules_services, self.modules_hashes, self.modules_texts )
        
        self._modules.append( self.modules_files_storage )
        
        #
        
        self.modules_files_inbox = ClientDBFilesInbox.ClientDBFilesInbox( self._c, self.modules_files_storage )
        
        self._modules.append( self.modules_files_inbox )
        
        #
        
        self.modules_mappings_counts = ClientDBMappingsCounts.ClientDBMappingsCounts( self._c, self.modules_services )
        
        self._modules.append( self.modules_mappings_counts )
        
        #
        
        self.modules_tags_local_cache = ClientDBDefinitionsCache.ClientDBCacheLocalTags( self._c, self.modules_tags, self.modules_services, self.modules_mappings_counts )
        
        self._modules.append( self.modules_tags_local_cache )
        
        self.modules_hashes_local_cache = ClientDBDefinitionsCache.ClientDBCacheLocalHashes( self._c, self.modules_hashes, self.modules_services, self.modules_files_storage )
        
        self._modules.append( self.modules_hashes_local_cache )
        
        #
        
        self.modules_service_paths = ClientDBServicePaths.ClientDBServicePaths( self._c, self.modules_services, self.modules_texts, self.modules_hashes_local_cache )
        
        self._modules.append( self.modules_service_paths )
        
        #
        
        self.modules_mappings_storage = ClientDBMappingsStorage.ClientDBMappingsStorage( self._c, self.modules_services )
        
        self._modules.append( self.modules_mappings_storage )
        
        #
        
        self.modules_files_metadata_rich = ClientDBFilesMetadataRich.ClientDBFilesMetadataRich( self._c, self.modules_services, self.modules_hashes, self.modules_files_metadata_basic, self.modules_files_storage, self.modules_hashes_local_cache, self.modules_url_map )
        
        self._modules.append( self.modules_files_metadata_rich )
        
        #
        
        self.modules_tag_siblings = ClientDBTagSiblings.ClientDBTagSiblings( self._c, self.modules_services, self.modules_tags, self.modules_tags_local_cache )
        
        self._modules.append( self.modules_tag_siblings )
        
        self.modules_tag_parents = ClientDBTagParents.ClientDBTagParents( self._c, self.modules_services, self.modules_tags_local_cache, self.modules_tag_siblings )
        
        self._modules.append( self.modules_tag_parents )
        
        self.modules_tag_display = ClientDBTagDisplay.ClientDBTagDisplay( self._c, self._cursor_transaction_wrapper, self.modules_services, self.modules_tags, self.modules_tags_local_cache, self.modules_tag_siblings, self.modules_tag_parents )
        
        self._modules.append( self.modules_tag_display )
        
        # when you do the mappings caches, storage and display, consider carefully how you want them slotting in here
        # don't rush into it
        
        self.modules_tag_search = ClientDBTagSearch.ClientDBTagSearch( self._c, self.modules_services, self.modules_tags, self.modules_tag_display, self.modules_tag_siblings, self.modules_mappings_counts )
        
        self._modules.append( self.modules_tag_search )
        
        self.modules_mappings_counts_update = ClientDBMappingsCountsUpdate.ClientDBMappingsCountsUpdate( self._c, self.modules_services, self.modules_mappings_counts, self.modules_tags_local_cache, self.modules_tag_display, self.modules_tag_search )
        
        self._modules.append( self.modules_mappings_counts_update )
        
        #
        
        self.modules_mappings_cache_combined_files_display = ClientDBMappingsCacheCombinedFilesDisplay.ClientDBMappingsCacheCombinedFilesDisplay( self._c, self.modules_services, self.modules_mappings_counts, self.modules_mappings_counts_update, self.modules_mappings_storage, self.modules_tag_display, self.modules_files_storage )
        
        self._modules.append( self.modules_mappings_cache_combined_files_display )
        
        self.modules_mappings_cache_combined_files_storage = ClientDBMappingsCacheCombinedFilesStorage.ClientDBMappingsCacheCombinedFilesStorage( self._c, self.modules_services, self.modules_mappings_counts, self.modules_mappings_counts_update, self.modules_mappings_cache_combined_files_display )
        
        self._modules.append( self.modules_mappings_cache_combined_files_storage )
        
        self.modules_mappings_cache_specific_display = ClientDBMappingsCacheSpecificDisplay.ClientDBMappingsCacheSpecificDisplay( self._c, self.modules_services, self.modules_mappings_counts, self.modules_mappings_counts_update, self.modules_mappings_storage, self.modules_tag_display )
        
        self._modules.append( self.modules_mappings_cache_specific_display )
        
        self.modules_mappings_cache_specific_storage = ClientDBMappingsCacheSpecificStorage.ClientDBMappingsCacheSpecificStorage( self._c, self.modules_services, self.modules_db_maintenance, self.modules_mappings_counts, self.modules_mappings_counts_update, self.modules_files_storage, self.modules_mappings_cache_specific_display )
        
        self._modules.append( self.modules_mappings_cache_specific_storage )
        
        #
        
        self.modules_similar_files = ClientDBSimilarFiles.ClientDBSimilarFiles( self._c, self.modules_services, self.modules_files_storage )
        
        self._modules.append( self.modules_similar_files )
        
        self.modules_files_duplicates = ClientDBFilesDuplicates.ClientDBFilesDuplicates( self._c, self.modules_files_storage, self.modules_hashes_local_cache, self.modules_similar_files )
        
        self._modules.append( self.modules_files_duplicates )
        
        #
        
        self.modules_files_maintenance_queue = ClientDBFilesMaintenanceQueue.ClientDBFilesMaintenanceQueue( self._c, self.modules_hashes_local_cache )
        
        self._modules.append( self.modules_files_maintenance_queue )
        
        #
        
        # how about a module for 'local file services', it can do various filtering
        
        self.modules_repositories = ClientDBRepositories.ClientDBRepositories( self._c, self._cursor_transaction_wrapper, self.modules_services, self.modules_files_storage, self.modules_files_metadata_basic, self.modules_hashes_local_cache, self.modules_tags_local_cache, self.modules_files_maintenance_queue )
        
        self._modules.append( self.modules_repositories )
        
        #
        
        self.modules_files_maintenance = ClientDBFilesMaintenance.ClientDBFilesMaintenance( self._c, self.modules_files_maintenance_queue, self.modules_hashes, self.modules_hashes_local_cache, self.modules_files_metadata_basic, self.modules_similar_files, self.modules_repositories, self._weakref_media_result_cache )
        
        self._modules.append( self.modules_files_maintenance )
        
        #
        
        self.modules_files_search_tags = ClientDBFilesSearch.ClientDBFilesSearchTags( self._c, self.modules_services, self.modules_tags, self.modules_files_storage, self.modules_mappings_counts, self.modules_tag_search )
        
        self._modules.append( self.modules_files_search_tags )
        
        self.modules_files_query = ClientDBFilesSearch.ClientDBFilesQuery(
            self._c,
            self.modules_services,
            self.modules_hashes,
            self.modules_tags,
            self.modules_files_metadata_basic,
            self.modules_files_viewing_stats,
            self.modules_url_map,
            self.modules_notes_map,
            self.modules_files_storage,
            self.modules_files_inbox,
            self.modules_mappings_counts,
            self.modules_hashes_local_cache,
            self.modules_tag_search,
            self.modules_similar_files,
            self.modules_files_duplicates,
            self.modules_files_search_tags
        )
        
        self._modules.append( self.modules_files_query )
        
    
    def _ManageDBError( self, job, e ):
        
        if isinstance( e, MemoryError ):
            
            HydrusData.ShowText( 'The client is running out of memory! Restart it ASAP!' )
            
        
        tb = traceback.format_exc()
        
        if 'malformed' in tb:
            
            HydrusData.ShowText( 'A database exception looked like it could be a very serious \'database image is malformed\' error! Unless you know otherwise, please shut down the client immediately and check the \'help my db is broke.txt\' under install_dir/db.' )
            
        
        if job.IsSynchronous():
            
            db_traceback = 'Database ' + tb
            
            first_line = str( type( e ).__name__ ) + ': ' + str( e )
            
            new_e = HydrusExceptions.DBException( e, first_line, db_traceback )
            
            job.PutResult( new_e )
            
        else:
            
            HydrusData.ShowException( e )
            
        
    
    def _MigrationClearJob( self, database_temp_job_name ):
        
        self._Execute( 'DROP TABLE {};'.format( database_temp_job_name ) )
        
    
    def _MigrationGetMappings( self, database_temp_job_name, file_service_key, tag_service_key, hash_type, tag_filter, content_statuses ):
        
        time_started_precise = HydrusData.GetNowPrecise()
        
        data = []
        
        file_service_id = self.modules_services.GetServiceId( file_service_key )
        tag_service_id = self.modules_services.GetServiceId( tag_service_key )
        
        statuses_to_table_names = self.modules_mappings_storage.GetFastestStorageMappingTableNames( file_service_id, tag_service_id )
        
        select_queries = []
        
        for content_status in content_statuses:
            
            table_name = statuses_to_table_names[ content_status ]
            
            select_query = 'SELECT tag_id FROM {} WHERE hash_id = ?;'.format( table_name )
            
            select_queries.append( select_query )
            
        
        we_should_stop = False
        
        while not we_should_stop:
            
            result = self._Execute( 'SELECT hash_id FROM {};'.format( database_temp_job_name ) ).fetchone()
            
            if result is None:
                
                break
                
            
            ( hash_id, ) = result
            
            self._Execute( 'DELETE FROM {} WHERE hash_id = ?;'.format( database_temp_job_name ), ( hash_id, ) )
            
            if hash_type == 'sha256':
                
                desired_hash = self.modules_hashes_local_cache.GetHash( hash_id )
                
            else:
                
                try:
                    
                    desired_hash = self.modules_hashes.GetExtraHash( hash_type, hash_id )
                    
                except HydrusExceptions.DataMissing:
                    
                    continue
                    
                
            
            tags = set()
            
            for select_query in select_queries:
                
                tag_ids = self._STL( self._Execute( select_query, ( hash_id, ) ) )
                
                tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = tag_ids )
                
                tags.update( tag_ids_to_tags.values() )
                
            
            if not tag_filter.AllowsEverything():
                
                tags = tag_filter.Filter( tags )
                
            
            if len( tags ) > 0:
                
                data.append( ( desired_hash, tags ) )
                
            
            we_should_stop = len( data ) >= 256 or ( len( data ) > 0 and HydrusData.TimeHasPassedPrecise( time_started_precise + 1.0 ) )
            
        
        return data
        
    
    def _MigrationGetPairs( self, database_temp_job_name, left_tag_filter, right_tag_filter ):
        
        time_started_precise = HydrusData.GetNowPrecise()
        
        data = []
        
        we_should_stop = False
        
        while not we_should_stop:
            
            result = self._Execute( 'SELECT left_tag_id, right_tag_id FROM {};'.format( database_temp_job_name ) ).fetchone()
            
            if result is None:
                
                break
                
            
            ( left_tag_id, right_tag_id ) = result
            
            self._Execute( 'DELETE FROM {} WHERE left_tag_id = ? AND right_tag_id = ?;'.format( database_temp_job_name ), ( left_tag_id, right_tag_id ) )
            
            left_tag = self.modules_tags_local_cache.GetTag( left_tag_id )
            
            if not left_tag_filter.TagOK( left_tag ):
                
                continue
                
            
            right_tag = self.modules_tags_local_cache.GetTag( right_tag_id )
            
            if not right_tag_filter.TagOK( right_tag ):
                
                continue
                
            
            data.append( ( left_tag, right_tag ) )
            
            we_should_stop = len( data ) >= 256 or ( len( data ) > 0 and HydrusData.TimeHasPassedPrecise( time_started_precise + 1.0 ) )
            
        
        return data
        
    
    def _MigrationStartMappingsJob( self, database_temp_job_name, file_service_key, tag_service_key, hashes, content_statuses ):
        
        file_service_id = self.modules_services.GetServiceId( file_service_key )
        
        self._Execute( 'CREATE TABLE IF NOT EXISTS durable_temp.{} ( hash_id INTEGER PRIMARY KEY );'.format( database_temp_job_name ) )
        
        if hashes is not None:
            
            hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
            
            self._ExecuteMany( 'INSERT INTO {} ( hash_id ) VALUES ( ? );'.format( database_temp_job_name ), ( ( hash_id, ) for hash_id in hash_ids ) )
            
        else:
            
            tag_service_id = self.modules_services.GetServiceId( tag_service_key )
            
            statuses_to_table_names = {}
            
            use_hashes_table = False
            
            if file_service_id == self.modules_services.combined_file_service_id:
                
                # if our tag service is the biggest, and if it basically accounts for all the hashes we know about, it is much faster to just use the hashes table
                
                our_results = self._GetServiceInfo( tag_service_key )
                
                our_num_files = our_results[ HC.SERVICE_INFO_NUM_FILE_HASHES ]
                
                other_services = [ service for service in self.modules_services.GetServices( HC.REAL_TAG_SERVICES ) if service.GetServiceKey() != tag_service_key ]
                
                other_num_files = []
                
                for other_service in other_services:
                    
                    other_results = self._GetServiceInfo( other_service.GetServiceKey() )
                    
                    other_num_files.append( other_results[ HC.SERVICE_INFO_NUM_FILE_HASHES ] )
                    
                
                if len( other_num_files ) == 0:
                    
                    we_are_big = True
                    
                else:
                    
                    we_are_big = our_num_files >= 0.75 * max( other_num_files )
                    
                
                if we_are_big:
                    
                    local_files_results = self._GetServiceInfo( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
                    
                    local_files_num_files = local_files_results[ HC.SERVICE_INFO_NUM_FILES ]
                    
                    if local_files_num_files > our_num_files:
                        
                        # probably a small local tags service, ok to pull from current_mappings
                        
                        we_are_big = False
                        
                    
                
                if we_are_big:
                    
                    use_hashes_table = True
                    
                
            
            if use_hashes_table:
                
                # this obviously just pulls literally all known files
                # makes migration take longer if the tag service does not cover many of these files, but saves huge startup time since it is a simple list
                select_subqueries = [ 'SELECT hash_id FROM hashes' ]
                
            else:
                
                statuses_to_table_names = self.modules_mappings_storage.GetFastestStorageMappingTableNames( file_service_id, tag_service_id )
                
                select_subqueries = []
                
                for content_status in content_statuses:
                    
                    table_name = statuses_to_table_names[ content_status ]
                    
                    select_subquery = 'SELECT DISTINCT hash_id FROM {}'.format( table_name )
                    
                    select_subqueries.append( select_subquery )
                    
                
            
            for select_subquery in select_subqueries:
                
                self._Execute( 'INSERT OR IGNORE INTO {} ( hash_id ) {};'.format( database_temp_job_name, select_subquery ) )
                
            
        
    
    def _MigrationStartPairsJob( self, database_temp_job_name, tag_service_key, content_type, content_statuses ):
        
        self._Execute( 'CREATE TABLE IF NOT EXISTS durable_temp.{} ( left_tag_id INTEGER, right_tag_id INTEGER, PRIMARY KEY ( left_tag_id, right_tag_id ) );'.format( database_temp_job_name ) )
        
        tag_service_id = self.modules_services.GetServiceId( tag_service_key )
        
        if content_type == HC.CONTENT_TYPE_TAG_PARENTS:
            
            source_table_names = [ 'tag_parents', 'tag_parent_petitions' ]
            left_column_name = 'child_tag_id'
            right_column_name = 'parent_tag_id'
            
        elif content_type == HC.CONTENT_TYPE_TAG_SIBLINGS:
            
            source_table_names = [ 'tag_siblings', 'tag_sibling_petitions' ]
            left_column_name = 'bad_tag_id'
            right_column_name = 'good_tag_id'
            
        
        for source_table_name in source_table_names:
            
            self._Execute( 'INSERT OR IGNORE INTO {} ( left_tag_id, right_tag_id ) SELECT {}, {} FROM {} WHERE service_id = ? AND status IN {};'.format( database_temp_job_name, left_column_name, right_column_name, source_table_name, HydrusData.SplayListForDB( content_statuses ) ), ( tag_service_id, ) )
            
        
    
    def _PerceptualHashesResetSearchFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        self.modules_similar_files.ResetSearch( hash_ids )
        
    
    def _PerceptualHashesSearchForPotentialDuplicates( self, search_distance, maintenance_mode = HC.MAINTENANCE_FORCED, job_key = None, stop_time = None, work_time_float = None ):
        
        time_started_float = HydrusData.GetNowFloat()
        
        num_done = 0
        still_work_to_do = True
        
        group_of_hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM shape_search_cache WHERE searched_distance IS NULL or searched_distance < ?;', ( search_distance, ) ).fetchmany( 10 ) )
        
        while len( group_of_hash_ids ) > 0:
        
            text = 'searching potential duplicates: {}'.format( HydrusData.ToHumanInt( num_done ) )
            
            HG.client_controller.frame_splash_status.SetSubtext( text )
            
            for ( i, hash_id ) in enumerate( group_of_hash_ids ):
                
                if work_time_float is not None and HydrusData.TimeHasPassedFloat( time_started_float + work_time_float ):
                    
                    return ( still_work_to_do, num_done )
                    
                
                if job_key is not None:
                    
                    ( i_paused, should_stop ) = job_key.WaitIfNeeded()
                    
                    if should_stop:
                        
                        return ( still_work_to_do, num_done )
                        
                    
                
                should_stop = HG.client_controller.ShouldStopThisWork( maintenance_mode, stop_time = stop_time )
                
                if should_stop:
                    
                    return ( still_work_to_do, num_done )
                    
                
                media_id = self.modules_files_duplicates.GetMediaId( hash_id )
                
                potential_duplicate_media_ids_and_distances = [ ( self.modules_files_duplicates.GetMediaId( duplicate_hash_id ), distance ) for ( duplicate_hash_id, distance ) in self.modules_similar_files.Search( hash_id, search_distance ) if duplicate_hash_id != hash_id ]
                
                self.modules_files_duplicates.AddPotentialDuplicates( media_id, potential_duplicate_media_ids_and_distances )
                
                self._Execute( 'UPDATE shape_search_cache SET searched_distance = ? WHERE hash_id = ?;', ( search_distance, hash_id ) )
                
                num_done += 1
                
            
            group_of_hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM shape_search_cache WHERE searched_distance IS NULL or searched_distance < ?;', ( search_distance, ) ).fetchmany( 10 ) )
            
        
        still_work_to_do = False
        
        return ( still_work_to_do, num_done )
        
    
    def _ProcessContentUpdates( self, service_keys_to_content_updates, publish_content_updates = True ):
        
        notify_new_downloads = False
        notify_new_pending = False
        notify_new_parents = False
        notify_new_siblings = False
        
        valid_service_keys_to_content_updates = {}
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            try:
                
                service_id = self.modules_services.GetServiceId( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            valid_service_keys_to_content_updates[ service_key ] = content_updates
            
            service = self.modules_services.GetService( service_id )
            
            service_type = service.GetServiceType()
            
            ultimate_mappings_ids = []
            ultimate_deleted_mappings_ids = []
            
            ultimate_pending_mappings_ids = []
            ultimate_pending_rescinded_mappings_ids = []
            
            ultimate_petitioned_mappings_ids = []
            ultimate_petitioned_rescinded_mappings_ids = []
            
            changed_sibling_tag_ids = set()
            changed_parent_tag_ids = set()
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                if service_type in HC.FILE_SERVICES:
                    
                    if data_type == HC.CONTENT_TYPE_FILES:
                        
                        if action == HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD:
                            
                            hashes = row
                            
                            if hashes is None:
                                
                                service_ids_to_nums_cleared = self.modules_files_storage.ClearLocalDeleteRecord()
                                
                            else:
                                
                                hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                                
                                service_ids_to_nums_cleared = self.modules_files_storage.ClearLocalDeleteRecord( hash_ids )
                                
                            
                            self._ExecuteMany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', ( ( -num_cleared, clear_service_id, HC.SERVICE_INFO_NUM_DELETED_FILES ) for ( clear_service_id, num_cleared ) in service_ids_to_nums_cleared.items() ) )
                            
                        elif action == HC.CONTENT_UPDATE_ADD:
                            
                            if service_type in HC.LOCAL_FILE_SERVICES or service_type == HC.FILE_REPOSITORY:
                                
                                ( file_info_manager, timestamp ) = row
                                
                                ( hash_id, hash, size, mime, width, height, duration, num_frames, has_audio, num_words ) = file_info_manager.ToTuple()
                                
                                self.modules_files_metadata_basic.AddFilesInfo( [ ( hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words ) ] )
                                
                            elif service_type == HC.IPFS:
                                
                                ( file_info_manager, multihash ) = row
                                
                                hash_id = file_info_manager.hash_id
                                
                                self.modules_service_paths.SetServiceFilename( service_id, hash_id, multihash )
                                
                                timestamp = HydrusData.GetNow()
                                
                            
                            self._AddFiles( service_id, [ ( hash_id, timestamp ) ] )
                            
                        else:
                            
                            hashes = row
                            
                            hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                            
                            if action == HC.CONTENT_UPDATE_ARCHIVE:
                                
                                self.modules_files_inbox.ArchiveFiles( hash_ids )
                                
                            elif action == HC.CONTENT_UPDATE_INBOX:
                                
                                self.modules_files_inbox.InboxFiles( hash_ids )
                                
                            elif action == HC.CONTENT_UPDATE_DELETE:
                                
                                actual_delete_hash_ids = self._FilterForFileDeleteLock( service_id, hash_ids )
                                
                                if len( actual_delete_hash_ids ) < len( hash_ids ):
                                    
                                    hash_ids = actual_delete_hash_ids
                                    
                                    hashes = self.modules_hashes_local_cache.GetHashes( hash_ids )
                                    
                                    content_update.SetRow( hashes )
                                    
                                
                                if service_type in ( HC.LOCAL_FILE_DOMAIN, HC.COMBINED_LOCAL_MEDIA, HC.COMBINED_LOCAL_FILE ):
                                    
                                    if content_update.HasReason():
                                        
                                        reason = content_update.GetReason()
                                        
                                        # let's be careful only to set deletion reasons on valid hash ids
                                        location_context = ClientLocation.LocationContext( current_service_keys = ( service_key, ) )
                                        
                                        reason_settable_hash_ids = self.modules_files_storage.FilterHashIds( location_context, hash_ids )
                                        
                                        if len( reason_settable_hash_ids ) > 0:
                                            
                                            self.modules_files_storage.SetFileDeletionReason( reason_settable_hash_ids, reason )
                                            
                                        
                                    
                                
                                if service_id == self.modules_services.trash_service_id:
                                    
                                    # shouldn't be called anymore, but just in case someone fidgets a trash delete with client api or something
                                    
                                    self._DeleteFiles( self.modules_services.combined_local_file_service_id, hash_ids )
                                    
                                elif service_id == self.modules_services.combined_local_media_service_id:
                                    
                                    for s_id in self.modules_services.GetServiceIds( ( HC.LOCAL_FILE_DOMAIN, ) ):
                                        
                                        self._DeleteFiles( s_id, hash_ids, only_if_current = True )
                                        
                                    
                                else:
                                    
                                    self._DeleteFiles( service_id, hash_ids )
                                    
                                
                            elif action == HC.CONTENT_UPDATE_UNDELETE:
                                
                                self._UndeleteFiles( service_id, hash_ids )
                                
                            elif action == HC.CONTENT_UPDATE_PEND:
                                
                                invalid_hash_ids = self.modules_files_storage.FilterHashIdsToStatus( service_id, hash_ids, HC.CONTENT_STATUS_CURRENT )
                                
                                valid_hash_ids = hash_ids.difference( invalid_hash_ids )
                                
                                self.modules_files_storage.PendFiles( service_id, valid_hash_ids )
                                
                                if service_key == CC.COMBINED_LOCAL_FILE_SERVICE_KEY:
                                    
                                    notify_new_downloads = True
                                    
                                else:
                                    
                                    notify_new_pending = True
                                    
                                
                            elif action == HC.CONTENT_UPDATE_PETITION:
                                
                                reason = content_update.GetReason()
                                
                                reason_id = self.modules_texts.GetTextId( reason )
                                
                                valid_hash_ids = self.modules_files_storage.FilterHashIdsToStatus( service_id, hash_ids, HC.CONTENT_STATUS_CURRENT )
                                
                                self.modules_files_storage.PetitionFiles( service_id, reason_id, valid_hash_ids )
                                
                                notify_new_pending = True
                                
                            elif action == HC.CONTENT_UPDATE_RESCIND_PEND:
                                
                                self.modules_files_storage.RescindPendFiles( service_id, hash_ids )
                                
                                if service_key == CC.COMBINED_LOCAL_FILE_SERVICE_KEY:
                                    
                                    notify_new_downloads = True
                                    
                                else:
                                    
                                    notify_new_pending = True
                                    
                                
                            elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                                
                                self.modules_files_storage.RescindPetitionFiles( service_id, hash_ids )
                                
                                notify_new_pending = True
                                
                            
                        
                    elif data_type == HC.CONTENT_TYPE_DIRECTORIES:
                        
                        if action == HC.CONTENT_UPDATE_ADD:
                            
                            ( hashes, dirname, note ) = row
                            
                            hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                            
                            result = self._Execute( 'SELECT SUM( size ) FROM files_info WHERE hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';' ).fetchone()
                            
                            if result is None:
                                
                                total_size = 0
                                
                            else:
                                
                                ( total_size, ) = result
                                
                            
                            self.modules_service_paths.SetServiceDirectory( service_id, hash_ids, dirname, total_size, note )
                            
                        elif action == HC.CONTENT_UPDATE_DELETE:
                            
                            dirname = row
                            
                            self.modules_service_paths.DeleteServiceDirectory( service_id, dirname )
                            
                        
                    elif data_type == HC.CONTENT_TYPE_URLS:
                        
                        if action == HC.CONTENT_UPDATE_ADD:
                            
                            ( urls, hashes ) = row
                            
                            hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                            
                            for ( hash_id, url ) in itertools.product( hash_ids, urls ):
                                
                                self.modules_url_map.AddMapping( hash_id, url )
                                
                            
                        elif action == HC.CONTENT_UPDATE_DELETE:
                            
                            ( urls, hashes ) = row
                            
                            hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                            
                            for ( hash_id, url ) in itertools.product( hash_ids, urls ):
                                
                                self.modules_url_map.DeleteMapping( hash_id, url )
                                
                            
                        
                    elif data_type == HC.CONTENT_TYPE_TIMESTAMP:
                        
                        ( timestamp_type, hash, data ) = row
                        
                        if timestamp_type == 'domain':
                            
                            if action == HC.CONTENT_UPDATE_ADD:
                                
                                ( domain, timestamp ) = data
                                
                                hash_id = self.modules_hashes_local_cache.GetHashId( hash )
                                domain_id = self.modules_urls.GetURLDomainId( domain )
                                
                                self.modules_files_metadata_basic.UpdateDomainModifiedTimestamp( hash_id, domain_id, timestamp )
                                
                            elif action == HC.CONTENT_UPDATE_SET:
                                
                                ( domain, timestamp ) = data
                                
                                hash_id = self.modules_hashes_local_cache.GetHashId( hash )
                                domain_id = self.modules_urls.GetURLDomainId( domain )
                                
                                self.modules_files_metadata_basic.SetDomainModifiedTimestamp( hash_id, domain_id, timestamp )
                                
                            elif action == HC.CONTENT_UPDATE_DELETE:
                                
                                domain = data
                                
                                hash_id = self.modules_hashes_local_cache.GetHashId( hash )
                                domain_id = self.modules_urls.GetURLDomainId( domain )
                                
                                self.modules_files_metadata_basic.ClearDomainModifiedTimestamp( hash_id, domain_id )
                                
                            
                        
                    elif data_type == HC.CONTENT_TYPE_FILE_VIEWING_STATS:
                        
                        if action == HC.CONTENT_UPDATE_ADVANCED:
                            
                            action = row
                            
                            if action == 'clear':
                                
                                self.modules_files_viewing_stats.ClearAllStats()
                                
                            
                        elif action == HC.CONTENT_UPDATE_ADD:
                            
                            ( hash, canvas_type, view_timestamp, views_delta, viewtime_delta ) = row
                            
                            hash_id = self.modules_hashes_local_cache.GetHashId( hash )
                            
                            self.modules_files_viewing_stats.AddViews( hash_id, canvas_type, view_timestamp, views_delta, viewtime_delta )
                            
                        elif action == HC.CONTENT_UPDATE_DELETE:
                            
                            hashes = row
                            
                            hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                            
                            self.modules_files_viewing_stats.ClearViews( hash_ids )
                            
                        
                    
                elif service_type in HC.REAL_TAG_SERVICES:
                    
                    if data_type == HC.CONTENT_TYPE_MAPPINGS:
                        
                        ( tag, hashes ) = row
                        
                        try:
                            
                            potentially_dirty_tag = tag
                            
                            tag = HydrusTags.CleanTag( potentially_dirty_tag )
                            
                            if tag != potentially_dirty_tag:
                                
                                content_update.SetRow( ( tag, hashes ) )
                                
                            
                            tag_id = self.modules_tags.GetTagId( tag )
                            
                        except HydrusExceptions.TagSizeException:
                            
                            content_update.SetRow( ( 'bad tag', set() ) )
                            
                            continue
                            
                        
                        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                        
                        display_affected = action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_RESCIND_PEND )
                        
                        if display_affected and publish_content_updates and self.modules_tag_display.IsChained( ClientTags.TAG_DISPLAY_ACTUAL, service_id, tag_id ):
                            
                            self._regen_tags_managers_hash_ids.update( hash_ids )
                            
                        
                        if action == HC.CONTENT_UPDATE_ADD:
                            
                            if not HG.client_controller.tag_display_manager.TagOK( ClientTags.TAG_DISPLAY_STORAGE, service_key, tag ):
                                
                                continue
                                
                            
                            ultimate_mappings_ids.append( ( tag_id, hash_ids ) )
                            
                        elif action == HC.CONTENT_UPDATE_DELETE:
                            
                            ultimate_deleted_mappings_ids.append( ( tag_id, hash_ids ) )
                            
                        elif action == HC.CONTENT_UPDATE_PEND:
                            
                            if not HG.client_controller.tag_display_manager.TagOK( ClientTags.TAG_DISPLAY_STORAGE, service_key, tag ):
                                
                                continue
                                
                            
                            ultimate_pending_mappings_ids.append( ( tag_id, hash_ids ) )
                            
                        elif action == HC.CONTENT_UPDATE_RESCIND_PEND:
                            
                            ultimate_pending_rescinded_mappings_ids.append( ( tag_id, hash_ids ) )
                            
                        elif action == HC.CONTENT_UPDATE_PETITION:
                            
                            reason = content_update.GetReason()
                            
                            reason_id = self.modules_texts.GetTextId( reason )
                            
                            ultimate_petitioned_mappings_ids.append( ( tag_id, hash_ids, reason_id ) )
                            
                        elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                            
                            ultimate_petitioned_rescinded_mappings_ids.append( ( tag_id, hash_ids ) )
                            
                        elif action == HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD:
                            
                            ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( service_id )
                            
                            self._ExecuteMany( 'DELETE FROM {} WHERE tag_id = ? AND hash_id = ?;'.format( deleted_mappings_table_name ), ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                            
                            self._Execute( 'DELETE FROM service_info WHERE service_id = ? AND info_type = ?;', ( service_id, HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ) )
                            
                            cache_file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
                            
                            for cache_file_service_id in cache_file_service_ids:
                                
                                ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( cache_file_service_id, service_id )
                                
                                self._ExecuteMany( 'DELETE FROM ' + cache_deleted_mappings_table_name + ' WHERE hash_id = ? AND tag_id = ?;', ( ( hash_id, tag_id ) for hash_id in hash_ids ) )
                                
                            
                        
                    elif data_type == HC.CONTENT_TYPE_TAG_PARENTS:
                        
                        if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                            
                            ( child_tag, parent_tag ) = row
                            
                            try:
                                
                                child_tag_id = self.modules_tags.GetTagId( child_tag )
                                
                                parent_tag_id = self.modules_tags.GetTagId( parent_tag )
                                
                            except HydrusExceptions.TagSizeException:
                                
                                continue
                                
                            
                            pairs = ( ( child_tag_id, parent_tag_id ), )
                            
                            if action == HC.CONTENT_UPDATE_ADD:
                                
                                self.modules_tag_parents.AddTagParents( service_id, pairs )
                                
                            elif action == HC.CONTENT_UPDATE_DELETE:
                                
                                self.modules_tag_parents.DeleteTagParents( service_id, pairs )
                                
                            
                            changed_parent_tag_ids.update( ( child_tag_id, parent_tag_id ) )
                            
                            if service_type == HC.TAG_REPOSITORY:
                                
                                notify_new_pending = True
                                
                            
                        elif action in ( HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_PETITION ):
                            
                            ( child_tag, parent_tag ) = row
                            
                            try:
                                
                                child_tag_id = self.modules_tags.GetTagId( child_tag )
                                
                                parent_tag_id = self.modules_tags.GetTagId( parent_tag )
                                
                            except HydrusExceptions.TagSizeException:
                                
                                continue
                                
                            
                            reason = content_update.GetReason()
                            
                            reason_id = self.modules_texts.GetTextId( reason )
                            
                            triples = ( ( child_tag_id, parent_tag_id, reason_id ), )
                            
                            if action == HC.CONTENT_UPDATE_PEND:
                                
                                self.modules_tag_parents.PendTagParents( service_id, triples )
                                
                            elif action == HC.CONTENT_UPDATE_PETITION:
                                
                                self.modules_tag_parents.PetitionTagParents( service_id, triples )
                                
                            
                            changed_parent_tag_ids.update( ( child_tag_id, parent_tag_id ) )
                            
                            if service_type == HC.TAG_REPOSITORY:
                                
                                notify_new_pending = True
                                
                            
                        elif action in ( HC.CONTENT_UPDATE_RESCIND_PEND, HC.CONTENT_UPDATE_RESCIND_PETITION ):
                            
                            ( child_tag, parent_tag ) = row
                            
                            try:
                                
                                child_tag_id = self.modules_tags.GetTagId( child_tag )
                                
                                parent_tag_id = self.modules_tags.GetTagId( parent_tag )
                                
                            except HydrusExceptions.TagSizeException:
                                
                                continue
                                
                            
                            pairs = ( ( child_tag_id, parent_tag_id ), )
                            
                            if action == HC.CONTENT_UPDATE_RESCIND_PEND:
                                
                                self.modules_tag_parents.RescindPendingTagParents( service_id, pairs )
                                
                            elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                                
                                self.modules_tag_parents.RescindPetitionedTagParents( service_id, pairs )
                                
                            
                            changed_parent_tag_ids.update( ( child_tag_id, parent_tag_id ) )
                            
                            if service_type == HC.TAG_REPOSITORY:
                                
                                notify_new_pending = True
                                
                            
                        
                        notify_new_parents = True
                        
                    elif data_type == HC.CONTENT_TYPE_TAG_SIBLINGS:
                        
                        if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                            
                            ( bad_tag, good_tag ) = row
                            
                            try:
                                
                                bad_tag_id = self.modules_tags.GetTagId( bad_tag )
                                
                                good_tag_id = self.modules_tags.GetTagId( good_tag )
                                
                            except HydrusExceptions.TagSizeException:
                                
                                continue
                                
                            
                            pairs = ( ( bad_tag_id, good_tag_id ), )
                            
                            if action == HC.CONTENT_UPDATE_ADD:
                                
                                self.modules_tag_siblings.AddTagSiblings( service_id, pairs )
                                
                            elif action == HC.CONTENT_UPDATE_DELETE:
                                
                                self.modules_tag_siblings.DeleteTagSiblings( service_id, pairs )
                                
                            
                            changed_sibling_tag_ids.update( ( bad_tag_id, good_tag_id ) )
                            
                            if service_type == HC.TAG_REPOSITORY:
                                
                                notify_new_pending = True
                                
                            
                        elif action in ( HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_PETITION ):
                            
                            ( bad_tag, good_tag ) = row
                            
                            try:
                                
                                bad_tag_id = self.modules_tags.GetTagId( bad_tag )
                                
                                good_tag_id = self.modules_tags.GetTagId( good_tag )
                                
                            except HydrusExceptions.TagSizeException:
                                
                                continue
                                
                            
                            reason = content_update.GetReason()
                            
                            reason_id = self.modules_texts.GetTextId( reason )
                            
                            triples = ( ( bad_tag_id, good_tag_id, reason_id ), )
                            
                            if action == HC.CONTENT_UPDATE_PEND:
                                
                                self.modules_tag_siblings.PendTagSiblings( service_id, triples )
                                
                            elif action == HC.CONTENT_UPDATE_PETITION:
                                
                                self.modules_tag_siblings.PetitionTagSiblings( service_id, triples )
                                
                            
                            changed_sibling_tag_ids.update( ( bad_tag_id, good_tag_id ) )
                            
                            if service_type == HC.TAG_REPOSITORY:
                                
                                notify_new_pending = True
                                
                            
                        elif action in ( HC.CONTENT_UPDATE_RESCIND_PEND, HC.CONTENT_UPDATE_RESCIND_PETITION ):
                            
                            ( bad_tag, good_tag ) = row
                            
                            try:
                                
                                bad_tag_id = self.modules_tags.GetTagId( bad_tag )
                                
                                good_tag_id = self.modules_tags.GetTagId( good_tag )
                                
                            except HydrusExceptions.TagSizeException:
                                
                                continue
                                
                            
                            pairs = ( ( bad_tag_id, good_tag_id ), )
                            
                            if action == HC.CONTENT_UPDATE_RESCIND_PEND:
                                
                                self.modules_tag_siblings.RescindPendingTagSiblings( service_id, pairs )
                                
                            elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                                
                                self.modules_tag_siblings.RescindPetitionedTagSiblings( service_id, pairs )
                                
                            
                            changed_sibling_tag_ids.update( ( bad_tag_id, good_tag_id ) )
                            
                            if service_type == HC.TAG_REPOSITORY:
                                
                                notify_new_pending = True
                                
                            
                        
                        notify_new_siblings = True
                        
                    
                elif service_type in HC.RATINGS_SERVICES:
                    
                    if action == HC.CONTENT_UPDATE_ADD:
                        
                        ( rating, hashes ) = row
                        
                        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                        
                        if service_type in HC.STAR_RATINGS_SERVICES:
                            
                            ratings_added = 0
                            
                            self._ExecuteMany( 'DELETE FROM local_ratings WHERE service_id = ? AND hash_id = ?;', ( ( service_id, hash_id ) for hash_id in hash_ids ) )
                            
                            ratings_added -= self._GetRowCount()
                            
                            if rating is not None:
                                
                                self._ExecuteMany( 'INSERT INTO local_ratings ( service_id, hash_id, rating ) VALUES ( ?, ?, ? );', [ ( service_id, hash_id, rating ) for hash_id in hash_ids ] )
                                
                                ratings_added += self._GetRowCount()
                                
                            
                            self._Execute( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', ( ratings_added, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
                            
                        elif service_type == HC.LOCAL_RATING_INCDEC:
                            
                            ratings_added = 0
                            
                            self._ExecuteMany( 'DELETE FROM local_incdec_ratings WHERE service_id = ? AND hash_id = ?;', ( ( service_id, hash_id ) for hash_id in hash_ids ) )
                            
                            ratings_added -= self._GetRowCount()
                            
                            if rating != 0:
                                
                                self._ExecuteMany( 'INSERT INTO local_incdec_ratings ( service_id, hash_id, rating ) VALUES ( ?, ?, ? );', [ ( service_id, hash_id, rating ) for hash_id in hash_ids ] )
                                
                                ratings_added += self._GetRowCount()
                                
                            
                            self._Execute( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', ( ratings_added, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
                            
                        
                    elif action == HC.CONTENT_UPDATE_ADVANCED:
                        
                        action = row
                        
                        if service_type in HC.STAR_RATINGS_SERVICES:
                            
                            if action == 'delete_for_deleted_files':
                                
                                deleted_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_file_service_id, HC.CONTENT_STATUS_DELETED )
                                
                                self._Execute( 'DELETE FROM local_ratings WHERE service_id = ? and hash_id IN ( SELECT hash_id FROM {} );'.format( deleted_files_table_name ), ( service_id, ) )
                                
                                ratings_deleted = self._GetRowCount()
                                
                                self._Execute( 'UPDATE service_info SET info = info - ? WHERE service_id = ? AND info_type = ?;', ( ratings_deleted, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
                                
                            elif action == 'delete_for_non_local_files':
                                
                                current_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_file_service_id, HC.CONTENT_STATUS_CURRENT )
                                
                                self._Execute( 'DELETE FROM local_ratings WHERE local_ratings.service_id = ? and hash_id NOT IN ( SELECT hash_id FROM {} );'.format( current_files_table_name ), ( service_id, ) )
                                
                                ratings_deleted = self._GetRowCount()
                                
                                self._Execute( 'UPDATE service_info SET info = info - ? WHERE service_id = ? AND info_type = ?;', ( ratings_deleted, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
                                
                            elif action == 'delete_for_all_files':
                                
                                self._Execute( 'DELETE FROM local_ratings WHERE service_id = ?;', ( service_id, ) )
                                
                                self._Execute( 'UPDATE service_info SET info = ? WHERE service_id = ? AND info_type = ?;', ( 0, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
                                
                            
                        elif service_type == HC.LOCAL_RATING_INCDEC:
                            
                            if action == 'delete_for_deleted_files':
                                
                                deleted_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_file_service_id, HC.CONTENT_STATUS_DELETED )
                                
                                self._Execute( 'DELETE FROM local_incdec_ratings WHERE service_id = ? and hash_id IN ( SELECT hash_id FROM {} );'.format( deleted_files_table_name ), ( service_id, ) )
                                
                                ratings_deleted = self._GetRowCount()
                                
                                self._Execute( 'UPDATE service_info SET info = info - ? WHERE service_id = ? AND info_type = ?;', ( ratings_deleted, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
                                
                            elif action == 'delete_for_non_local_files':
                                
                                current_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_file_service_id, HC.CONTENT_STATUS_CURRENT )
                                
                                self._Execute( 'DELETE FROM local_incdec_ratings WHERE local_incdec_ratings.service_id = ? and hash_id NOT IN ( SELECT hash_id FROM {} );'.format( current_files_table_name ), ( service_id, ) )
                                
                                ratings_deleted = self._GetRowCount()
                                
                                self._Execute( 'UPDATE service_info SET info = info - ? WHERE service_id = ? AND info_type = ?;', ( ratings_deleted, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
                                
                            elif action == 'delete_for_all_files':
                                
                                self._Execute( 'DELETE FROM local_incdec_ratings WHERE service_id = ?;', ( service_id, ) )
                                
                                self._Execute( 'UPDATE service_info SET info = ? WHERE service_id = ? AND info_type = ?;', ( 0, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
                                
                            
                        
                    
                elif service_type == HC.LOCAL_NOTES:
                    
                    if action == HC.CONTENT_UPDATE_SET:
                        
                        ( hash, name, note ) = row
                        
                        hash_id = self.modules_hashes_local_cache.GetHashId( hash )
                        
                        self.modules_notes_map.SetNote( hash_id, name, note )
                        
                    elif action == HC.CONTENT_UPDATE_DELETE:
                        
                        ( hash, name ) = row
                        
                        hash_id = self.modules_hashes_local_cache.GetHashId( hash )
                        
                        self.modules_notes_map.DeleteNote( hash_id, name )
                        
                    
                
            
            if len( ultimate_mappings_ids ) + len( ultimate_deleted_mappings_ids ) + len( ultimate_pending_mappings_ids ) + len( ultimate_pending_rescinded_mappings_ids ) + len( ultimate_petitioned_mappings_ids ) + len( ultimate_petitioned_rescinded_mappings_ids ) > 0:
                
                self._UpdateMappings( service_id, mappings_ids = ultimate_mappings_ids, deleted_mappings_ids = ultimate_deleted_mappings_ids, pending_mappings_ids = ultimate_pending_mappings_ids, pending_rescinded_mappings_ids = ultimate_pending_rescinded_mappings_ids, petitioned_mappings_ids = ultimate_petitioned_mappings_ids, petitioned_rescinded_mappings_ids = ultimate_petitioned_rescinded_mappings_ids )
                
                if service_type == HC.TAG_REPOSITORY:
                    
                    notify_new_pending = True
                    
                
            
            if len( changed_sibling_tag_ids ) > 0:
                
                self.modules_tag_display.NotifySiblingsChanged( service_id, changed_sibling_tag_ids )
                
            
            if len( changed_parent_tag_ids ) > 0:
                
                self.modules_tag_display.NotifyParentsChanged( service_id, changed_parent_tag_ids )
                
            
        
        if publish_content_updates:
            
            if notify_new_pending:
                
                self._cursor_transaction_wrapper.pub_after_job( 'notify_new_pending' )
                
            if notify_new_downloads:
                
                self._cursor_transaction_wrapper.pub_after_job( 'notify_new_downloads' )
                
            if notify_new_siblings or notify_new_parents:
                
                self._cursor_transaction_wrapper.pub_after_job( 'notify_new_tag_display_application' )
                
            
            self.pub_content_updates_after_commit( valid_service_keys_to_content_updates )
            
        
    
    def _ProcessRepositoryContent( self, service_key, content_hash, content_iterator_dict, content_types_to_process, job_key, work_time ):
        
        FILES_INITIAL_CHUNK_SIZE = 20
        MAPPINGS_INITIAL_CHUNK_SIZE = 50
        PAIR_ROWS_INITIAL_CHUNK_SIZE = 100
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        precise_time_to_stop = HydrusData.GetNowPrecise() + work_time
        
        num_rows_processed = 0
        
        if HC.CONTENT_TYPE_FILES in content_types_to_process:
            
            if 'new_files' in content_iterator_dict:
                
                has_audio = None # hack until we figure this out better
                
                i = content_iterator_dict[ 'new_files' ]
                
                for chunk in HydrusData.SplitIteratorIntoAutothrottledChunks( i, FILES_INITIAL_CHUNK_SIZE, precise_time_to_stop ):
                    
                    files_info_rows = []
                    files_rows = []
                    
                    for ( service_hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) in chunk:
                        
                        hash_id = self.modules_repositories.NormaliseServiceHashId( service_id, service_hash_id )
                        
                        files_info_rows.append( ( hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words ) )
                        
                        files_rows.append( ( hash_id, timestamp ) )
                        
                    
                    self.modules_files_metadata_basic.AddFilesInfo( files_info_rows )
                    
                    self._AddFiles( service_id, files_rows )
                    
                    num_rows_processed += len( files_rows )
                    
                    if HydrusData.TimeHasPassedPrecise( precise_time_to_stop ) or job_key.IsCancelled():
                        
                        return num_rows_processed
                        
                    
                
                del content_iterator_dict[ 'new_files' ]
                
            
            #
            
            if 'deleted_files' in content_iterator_dict:
                
                i = content_iterator_dict[ 'deleted_files' ]
                
                for chunk in HydrusData.SplitIteratorIntoAutothrottledChunks( i, FILES_INITIAL_CHUNK_SIZE, precise_time_to_stop ):
                    
                    service_hash_ids = chunk
                    
                    hash_ids = self.modules_repositories.NormaliseServiceHashIds( service_id, service_hash_ids )
                    
                    self._DeleteFiles( service_id, hash_ids )
                    
                    num_rows_processed += len( hash_ids )
                    
                    if HydrusData.TimeHasPassedPrecise( precise_time_to_stop ) or job_key.IsCancelled():
                        
                        return num_rows_processed
                        
                    
                
                del content_iterator_dict[ 'deleted_files' ]
                
            
        
        #
        
        if HC.CONTENT_TYPE_MAPPINGS in content_types_to_process:
            
            if 'new_mappings' in content_iterator_dict:
                
                i = content_iterator_dict[ 'new_mappings' ]
                
                for chunk in HydrusData.SplitMappingIteratorIntoAutothrottledChunks( i, MAPPINGS_INITIAL_CHUNK_SIZE, precise_time_to_stop ):
                    
                    mappings_ids = []
                    
                    num_rows = 0
                    
                    # yo, I can save time if I merge these ids so we only have one round of normalisation
                    
                    for ( service_tag_id, service_hash_ids ) in chunk:
                        
                        tag_id = self.modules_repositories.NormaliseServiceTagId( service_id, service_tag_id )
                        hash_ids = self.modules_repositories.NormaliseServiceHashIds( service_id, service_hash_ids )
                        
                        mappings_ids.append( ( tag_id, hash_ids ) )
                        
                        num_rows += len( service_hash_ids )
                        
                    
                    self._UpdateMappings( service_id, mappings_ids = mappings_ids )
                    
                    num_rows_processed += num_rows
                    
                    if HydrusData.TimeHasPassedPrecise( precise_time_to_stop ) or job_key.IsCancelled():
                        
                        return num_rows_processed
                        
                    
                
                del content_iterator_dict[ 'new_mappings' ]
                
            
            #
            
            if 'deleted_mappings' in content_iterator_dict:
                
                i = content_iterator_dict[ 'deleted_mappings' ]
                
                for chunk in HydrusData.SplitMappingIteratorIntoAutothrottledChunks( i, MAPPINGS_INITIAL_CHUNK_SIZE, precise_time_to_stop ):
                    
                    deleted_mappings_ids = []
                    
                    num_rows = 0
                    
                    for ( service_tag_id, service_hash_ids ) in chunk:
                        
                        tag_id = self.modules_repositories.NormaliseServiceTagId( service_id, service_tag_id )
                        hash_ids = self.modules_repositories.NormaliseServiceHashIds( service_id, service_hash_ids )
                        
                        deleted_mappings_ids.append( ( tag_id, hash_ids ) )
                        
                        num_rows += len( service_hash_ids )
                        
                    
                    self._UpdateMappings( service_id, deleted_mappings_ids = deleted_mappings_ids )
                    
                    num_rows_processed += num_rows
                    
                    if HydrusData.TimeHasPassedPrecise( precise_time_to_stop ) or job_key.IsCancelled():
                        
                        return num_rows_processed
                        
                    
                
                del content_iterator_dict[ 'deleted_mappings' ]
                
            
        
        #
        
        parents_or_siblings_changed = False
        
        try:
            
            if HC.CONTENT_TYPE_TAG_PARENTS in content_types_to_process:
                
                if 'new_parents' in content_iterator_dict:
                    
                    i = content_iterator_dict[ 'new_parents' ]
                    
                    for chunk in HydrusData.SplitIteratorIntoAutothrottledChunks( i, PAIR_ROWS_INITIAL_CHUNK_SIZE, precise_time_to_stop ):
                        
                        parent_ids = []
                        tag_ids = set()
                        
                        for ( service_child_tag_id, service_parent_tag_id ) in chunk:
                            
                            child_tag_id = self.modules_repositories.NormaliseServiceTagId( service_id, service_child_tag_id )
                            parent_tag_id = self.modules_repositories.NormaliseServiceTagId( service_id, service_parent_tag_id )
                            
                            tag_ids.add( child_tag_id )
                            tag_ids.add( parent_tag_id )
                            
                            parent_ids.append( ( child_tag_id, parent_tag_id ) )
                            
                        
                        self.modules_tag_parents.AddTagParents( service_id, parent_ids )
                        
                        self.modules_tag_display.NotifyParentsChanged( service_id, tag_ids )
                        
                        parents_or_siblings_changed = True
                        
                        num_rows_processed += len( parent_ids )
                        
                        if HydrusData.TimeHasPassedPrecise( precise_time_to_stop ) or job_key.IsCancelled():
                            
                            return num_rows_processed
                            
                        
                    
                    del content_iterator_dict[ 'new_parents' ]
                    
                
                #
                
                if 'deleted_parents' in content_iterator_dict:
                    
                    i = content_iterator_dict[ 'deleted_parents' ]
                    
                    for chunk in HydrusData.SplitIteratorIntoAutothrottledChunks( i, PAIR_ROWS_INITIAL_CHUNK_SIZE, precise_time_to_stop ):
                        
                        parent_ids = []
                        tag_ids = set()
                        
                        for ( service_child_tag_id, service_parent_tag_id ) in chunk:
                            
                            child_tag_id = self.modules_repositories.NormaliseServiceTagId( service_id, service_child_tag_id )
                            parent_tag_id = self.modules_repositories.NormaliseServiceTagId( service_id, service_parent_tag_id )
                            
                            tag_ids.add( child_tag_id )
                            tag_ids.add( parent_tag_id )
                            
                            parent_ids.append( ( child_tag_id, parent_tag_id ) )
                            
                        
                        self.modules_tag_parents.DeleteTagParents( service_id, parent_ids )
                        
                        self.modules_tag_display.NotifyParentsChanged( service_id, tag_ids )
                        
                        parents_or_siblings_changed = True
                        
                        num_rows = len( parent_ids )
                        
                        num_rows_processed += num_rows
                        
                        if HydrusData.TimeHasPassedPrecise( precise_time_to_stop ) or job_key.IsCancelled():
                            
                            return num_rows_processed
                            
                        
                    
                    del content_iterator_dict[ 'deleted_parents' ]
                    
                
            
            #
            
            if HC.CONTENT_TYPE_TAG_SIBLINGS in content_types_to_process:
                
                if 'new_siblings' in content_iterator_dict:
                    
                    i = content_iterator_dict[ 'new_siblings' ]
                    
                    for chunk in HydrusData.SplitIteratorIntoAutothrottledChunks( i, PAIR_ROWS_INITIAL_CHUNK_SIZE, precise_time_to_stop ):
                        
                        sibling_ids = []
                        tag_ids = set()
                        
                        for ( service_bad_tag_id, service_good_tag_id ) in chunk:
                            
                            bad_tag_id = self.modules_repositories.NormaliseServiceTagId( service_id, service_bad_tag_id )
                            good_tag_id = self.modules_repositories.NormaliseServiceTagId( service_id, service_good_tag_id )
                            
                            tag_ids.add( bad_tag_id )
                            tag_ids.add( good_tag_id )
                            
                            sibling_ids.append( ( bad_tag_id, good_tag_id ) )
                            
                        
                        self.modules_tag_siblings.AddTagSiblings( service_id, sibling_ids )
                        
                        self.modules_tag_display.NotifySiblingsChanged( service_id, tag_ids )
                        
                        parents_or_siblings_changed = True
                        
                        num_rows = len( sibling_ids )
                        
                        num_rows_processed += num_rows
                        
                        if HydrusData.TimeHasPassedPrecise( precise_time_to_stop ) or job_key.IsCancelled():
                            
                            return num_rows_processed
                            
                        
                    
                    del content_iterator_dict[ 'new_siblings' ]
                    
                
                #
                
                if 'deleted_siblings' in content_iterator_dict:
                    
                    i = content_iterator_dict[ 'deleted_siblings' ]
                    
                    for chunk in HydrusData.SplitIteratorIntoAutothrottledChunks( i, PAIR_ROWS_INITIAL_CHUNK_SIZE, precise_time_to_stop ):
                        
                        sibling_ids = []
                        tag_ids = set()
                        
                        for ( service_bad_tag_id, service_good_tag_id ) in chunk:
                            
                            bad_tag_id = self.modules_repositories.NormaliseServiceTagId( service_id, service_bad_tag_id )
                            good_tag_id = self.modules_repositories.NormaliseServiceTagId( service_id, service_good_tag_id )
                            
                            tag_ids.add( bad_tag_id )
                            tag_ids.add( good_tag_id )
                            
                            sibling_ids.append( ( bad_tag_id, good_tag_id ) )
                            
                        
                        self.modules_tag_siblings.DeleteTagSiblings( service_id, sibling_ids )
                        
                        self.modules_tag_display.NotifySiblingsChanged( service_id, tag_ids )
                        
                        parents_or_siblings_changed = True
                        
                        num_rows_processed += len( sibling_ids )
                        
                        if HydrusData.TimeHasPassedPrecise( precise_time_to_stop ) or job_key.IsCancelled():
                            
                            return num_rows_processed
                            
                        
                    
                    del content_iterator_dict[ 'deleted_siblings' ]
                    
                
            
        finally:
            
            if parents_or_siblings_changed:
                
                self._cursor_transaction_wrapper.pub_after_job( 'notify_new_tag_display_application' )
                
            
        
        self.modules_repositories.SetUpdateProcessed( service_id, content_hash, content_types_to_process )
        
        return num_rows_processed
        
    
    def _PushRecentTags( self, service_key, tags ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        if tags is None:
            
            self._Execute( 'DELETE FROM recent_tags WHERE service_id = ?;', ( service_id, ) )
            
        else:
            
            now = HydrusData.GetNow()
            
            tag_ids = [ self.modules_tags.GetTagId( tag ) for tag in tags ]
            
            self._ExecuteMany( 'REPLACE INTO recent_tags ( service_id, tag_id, timestamp ) VALUES ( ?, ?, ? );', ( ( service_id, tag_id, now ) for tag_id in tag_ids ) )
            
        
    
    def _Read( self, action, *args, **kwargs ):
        
        if action == 'autocomplete_predicates': result = self.modules_tag_search.GetAutocompletePredicates( *args, **kwargs )
        elif action == 'boned_stats': result = self._GetBonedStats( *args, **kwargs )
        elif action == 'client_files_locations': result = self.modules_files_physical_storage.GetClientFilesLocations( *args, **kwargs )
        elif action == 'deferred_physical_delete': result = self.modules_files_storage.GetDeferredPhysicalDelete( *args, **kwargs )
        elif action == 'duplicate_pairs_for_filtering': result = self._DuplicatesGetPotentialDuplicatePairsForFiltering( *args, **kwargs )
        elif action == 'file_duplicate_hashes': result = self.modules_files_duplicates.GetFileHashesByDuplicateType( *args, **kwargs )
        elif action == 'file_duplicate_info': result = self.modules_files_duplicates.GetFileDuplicateInfo( *args, **kwargs )
        elif action == 'file_hashes': result = self.modules_hashes.GetFileHashes( *args, **kwargs )
        elif action == 'file_history': result = self.modules_files_metadata_rich.GetFileHistory( *args, **kwargs )
        elif action == 'file_info_managers': result = self._GetFileInfoManagersFromHashes( *args, **kwargs )
        elif action == 'file_info_managers_from_ids': result = self._GetFileInfoManagers( *args, **kwargs )
        elif action == 'file_maintenance_get_job': result = self.modules_files_maintenance_queue.GetJob( *args, **kwargs )
        elif action == 'file_maintenance_get_job_counts': result = self.modules_files_maintenance_queue.GetJobCounts( *args, **kwargs )
        elif action == 'file_query_ids': result = self.modules_files_query.GetHashIdsFromQuery( *args, **kwargs )
        elif action == 'file_relationships_for_api': result = self.modules_files_duplicates.GetFileRelationshipsForAPI( *args, **kwargs )
        elif action == 'file_system_predicates': result = self._GetFileSystemPredicates( *args, **kwargs )
        elif action == 'filter_existing_tags': result = self.modules_mappings_counts_update.FilterExistingTags( *args, **kwargs )
        elif action == 'filter_hashes': result = self.modules_files_metadata_rich.FilterHashesByService( *args, **kwargs )
        elif action == 'force_refresh_tags_managers': result = self._GetForceRefreshTagsManagers( *args, **kwargs )
        elif action == 'gui_session': result = self.modules_serialisable.GetGUISession( *args, **kwargs )
        elif action == 'hash_ids_to_hashes': result = self.modules_hashes_local_cache.GetHashIdsToHashes( *args, **kwargs )
        elif action == 'hash_status': result = self.modules_files_metadata_rich.GetHashStatus( *args, **kwargs )
        elif action == 'have_hashed_serialised_objects': result = self.modules_serialisable.HaveHashedJSONDumps( *args, **kwargs )
        elif action == 'ideal_client_files_locations': result = self.modules_files_physical_storage.GetIdealClientFilesLocations( *args, **kwargs )
        elif action == 'inbox_hashes': result = self._FilterInboxHashes( *args, **kwargs )
        elif action == 'is_an_orphan': result = self._IsAnOrphan( *args, **kwargs )
        elif action == 'last_shutdown_work_time': result = self.modules_db_maintenance.GetLastShutdownWorkTime( *args, **kwargs )
        elif action == 'local_booru_share_keys': result = self.modules_serialisable.GetYAMLDumpNames( ClientDBSerialisable.YAML_DUMP_ID_LOCAL_BOORU )
        elif action == 'local_booru_share': result = self.modules_serialisable.GetYAMLDump( ClientDBSerialisable.YAML_DUMP_ID_LOCAL_BOORU, *args, **kwargs )
        elif action == 'local_booru_shares': result = self.modules_serialisable.GetYAMLDump( ClientDBSerialisable.YAML_DUMP_ID_LOCAL_BOORU )
        elif action == 'maintenance_due': result = self._GetMaintenanceDue( *args, **kwargs )
        elif action == 'media_predicates': result = self.modules_tag_display.GetMediaPredicates( *args, **kwargs )
        elif action == 'media_result': result = self._GetMediaResultFromHash( *args, **kwargs )
        elif action == 'media_results': result = self._GetMediaResultsFromHashes( *args, **kwargs )
        elif action == 'media_results_from_ids': result = self._GetMediaResults( *args, **kwargs )
        elif action == 'migration_get_mappings': result = self._MigrationGetMappings( *args, **kwargs )
        elif action == 'migration_get_pairs': result = self._MigrationGetPairs( *args, **kwargs )
        elif action == 'missing_repository_update_hashes': result = self.modules_repositories.GetRepositoryUpdateHashesIDoNotHave( *args, **kwargs )
        elif action == 'missing_thumbnail_hashes': result = self._GetRepositoryThumbnailHashesIDoNotHave( *args, **kwargs )
        elif action == 'num_deferred_file_deletes': result = self.modules_files_storage.GetDeferredPhysicalDeleteCounts()
        elif action == 'nums_pending': result = self._GetNumsPending( *args, **kwargs )
        elif action == 'options': result = self._GetOptions( *args, **kwargs )
        elif action == 'pending': result = self._GetPending( *args, **kwargs )
        elif action == 'random_potential_duplicate_hashes': result = self._DuplicatesGetRandomPotentialDuplicateHashes( *args, **kwargs )
        elif action == 'recent_tags': result = self._GetRecentTags( *args, **kwargs )
        elif action == 'repository_progress': result = self.modules_repositories.GetRepositoryProgress( *args, **kwargs )
        elif action == 'repository_update_hashes_to_process': result = self.modules_repositories.GetRepositoryUpdateHashesICanProcess( *args, **kwargs )
        elif action == 'serialisable': result = self.modules_serialisable.GetJSONDump( *args, **kwargs )
        elif action == 'serialisable_simple': result = self.modules_serialisable.GetJSONSimple( *args, **kwargs )
        elif action == 'serialisable_named': result = self.modules_serialisable.GetJSONDumpNamed( *args, **kwargs )
        elif action == 'serialisable_names': result = self.modules_serialisable.GetJSONDumpNames( *args, **kwargs )
        elif action == 'serialisable_names_to_backup_timestamps': result = self.modules_serialisable.GetJSONDumpNamesToBackupTimestamps( *args, **kwargs )
        elif action == 'service_directory': result = self.modules_service_paths.GetServiceDirectoryHashes( *args, **kwargs )
        elif action == 'service_directories': result = self.modules_service_paths.GetServiceDirectoriesInfo( *args, **kwargs )
        elif action == 'service_info': result = self._GetServiceInfo( *args, **kwargs )
        elif action == 'service_id': result = self.modules_services.GetServiceId( *args, **kwargs )
        elif action == 'services': result = self.modules_services.GetServices( *args, **kwargs )
        elif action == 'similar_files_maintenance_status': result = self.modules_similar_files.GetMaintenanceStatus( *args, **kwargs )
        elif action == 'related_tags': result = self._GetRelatedTags( *args, **kwargs )
        elif action == 'tag_display_application': result = self.modules_tag_display.GetApplication( *args, **kwargs )
        elif action == 'tag_display_maintenance_status': result = self._CacheTagDisplayGetApplicationStatusNumbers( *args, **kwargs )
        elif action == 'tag_parents': result = self.modules_tag_parents.GetTagParents( *args, **kwargs )
        elif action == 'tag_siblings': result = self.modules_tag_siblings.GetTagSiblings( *args, **kwargs )
        elif action == 'tag_siblings_all_ideals': result = self.modules_tag_siblings.GetTagSiblingsIdeals( *args, **kwargs )
        elif action == 'tag_display_decorators': result = self.modules_tag_display.GetUIDecorators( *args, **kwargs )
        elif action == 'tag_siblings_and_parents_lookup': result = self.modules_tag_display.GetSiblingsAndParentsForTags( *args, **kwargs )
        elif action == 'tag_siblings_lookup': result = self.modules_tag_siblings.GetTagSiblingsForTags( *args, **kwargs )
        elif action == 'trash_hashes': result = self._GetTrashHashes( *args, **kwargs )
        elif action == 'potential_duplicates_count': result = self._DuplicatesGetPotentialDuplicatesCount( *args, **kwargs )
        elif action == 'url_statuses': result = self.modules_files_metadata_rich.GetURLStatuses( *args, **kwargs )
        elif action == 'vacuum_data': result = self.modules_db_maintenance.GetVacuumData( *args, **kwargs )
        else: raise Exception( 'db received an unknown read command: ' + action )
        
        return result
        
    
    def _RecoverFromMissingDefinitions( self, content_type ):
        
        # this is not finished, but basics are there
        # remember this func uses a bunch of similar tech for the eventual orphan definition cleansing routine
        # we just have to extend modules functionality to cover all content tables and we are good to go
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            definition_column_name = 'hash_id'
            
        
        # eventually migrate this gubbins to cancellable async done in parts, which means generating, handling, and releasing the temp table name more cleverly
        
        # job presentation to UI
        
        all_tables_and_columns = []
        
        for module in self._modules:
            
            all_tables_and_columns.extend( module.GetTablesAndColumnsThatUseDefinitions( HC.CONTENT_TYPE_HASH ) )
            
        
        temp_all_useful_definition_ids_table_name = 'durable_temp.all_useful_definition_ids_{}'.format( os.urandom( 8 ).hex() )
        
        self._Execute( 'CREATE TABLE IF NOT EXISTS {} ( {} INTEGER PRIMARY KEY );'.format( temp_all_useful_definition_ids_table_name, definition_column_name ) )
        
        try:
            
            num_to_do = 0
            
            for ( table_name, column_name ) in all_tables_and_columns:
                
                query = 'INSERT OR IGNORE INTO {} ( {} ) SELECT DISTINCT {} FROM {};'.format(
                    temp_all_useful_definition_ids_table_name,
                    definition_column_name,
                    column_name,
                    table_name
                )
                
                self._Execute( query )
                
                num_to_do += self._GetRowCount()
                
            
            num_missing = 0
            num_recovered = 0
            
            batch_of_definition_ids = self._STL( self._Execute( 'SELECT {} FROM {} LIMIT 1024;'.format( definition_column_name, temp_all_useful_definition_ids_table_name ) ) )
            
            while len( batch_of_definition_ids ) > 1024:
                
                for definition_id in batch_of_definition_ids:
                    
                    if not self.modules_hashes.HasHashId( definition_id ):
                        
                        if content_type == HC.CONTENT_TYPE_HASH and self.modules_hashes_local_cache.HasHashId( definition_id ):
                            
                            hash = self.modules_hashes_local_cache.GetHash( definition_id )
                            
                            self._Execute( 'INSERT OR IGNORE INTO hashes ( hash_id, hash ) VALUES ( ?, ? );', ( definition_id, sqlite3.Binary( hash ) ) )
                            
                            HydrusData.Print( '{} {} had no master definition, but I was able to recover from the local cache'.format( definition_column_name, definition_id ) )
                            
                            num_recovered += 1
                            
                        else:
                            
                            HydrusData.Print( '{} {} had no master definition, it has been purged from the database!'.format( definition_column_name, definition_id ) )
                            
                            for ( table_name, column_name ) in all_tables_and_columns:
                                
                                self._Execute( 'DELETE FROM {} WHERE {} = ?;'.format( table_name, column_name ), ( definition_id, ) )
                                
                            
                            # tell user they will want to run clear orphan files, reset service cache info, and may need to recalc some autocomplete counts depending on total missing definitions
                            # I should clear service info based on content_type
                            
                            num_missing += 1
                            
                        
                    
                
                batch_of_definition_ids = self._Execute( 'SELECT {} FROM {} LIMIT 1024;'.format( definition_column_name, temp_all_useful_definition_ids_table_name ) )
                
            
        finally:
            
            self._Execute( 'DROP TABLE {};'.format( temp_all_useful_definition_ids_table_name ) )
            
        
    
    def _RegenerateLocalHashCache( self ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        try:
            
            job_key.SetStatusTitle( 'regenerating local hash cache' )
            
            self._controller.pub( 'modal_message', job_key )
            
            message = 'generating local hash cache'
            
            job_key.SetStatusText( message )
            self._controller.frame_splash_status.SetSubtext( message )
            
            self.modules_hashes_local_cache.Repopulate()
            
        finally:
            
            job_key.SetStatusText( 'done!' )
            
            job_key.Finish()
            
            job_key.Delete( 5 )
            
        
    
    def _RegenerateLocalTagCache( self ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        try:
            
            job_key.SetStatusTitle( 'regenerating local tag cache' )
            
            self._controller.pub( 'modal_message', job_key )
            
            message = 'generating local tag cache'
            
            job_key.SetStatusText( message )
            self._controller.frame_splash_status.SetSubtext( message )
            
            self.modules_tags_local_cache.Repopulate()
            
        finally:
            
            job_key.SetStatusText( 'done!' )
            
            job_key.Finish()
            
            job_key.Delete( 5 )
            
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_tag_display_application' )
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_force_refresh_tags_data' )
            
        
    
    def _RegenerateTagCacheSearchableSubtagMaps( self, tag_service_key = None ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        try:
            
            job_key.SetStatusTitle( 'regenerate tag fast search cache searchable subtag map' )
            
            self._controller.pub( 'modal_message', job_key )
            
            if tag_service_key is None:
                
                tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                
            else:
                
                tag_service_ids = ( self.modules_services.GetServiceId( tag_service_key ), )
                
            
            file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES )
            
            def status_hook( s ):
                
                job_key.SetStatusText( s, 2 )
                
            
            for ( file_service_id, tag_service_id ) in itertools.product( file_service_ids, tag_service_ids ):
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'repopulating specific cache {}_{}'.format( file_service_id, tag_service_id )
                
                job_key.SetStatusText( message )
                self._controller.frame_splash_status.SetSubtext( message )
                
                time.sleep( 0.01 )
                
                self.modules_tag_search.RegenerateSearchableSubtagMap( file_service_id, tag_service_id, status_hook = status_hook )
                
            
            for tag_service_id in tag_service_ids:
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'repopulating combined cache {}'.format( tag_service_id )
                
                job_key.SetStatusText( message )
                self._controller.frame_splash_status.SetSubtext( message )
                
                time.sleep( 0.01 )
                
                self.modules_tag_search.RegenerateSearchableSubtagMap( self.modules_services.combined_file_service_id, tag_service_id, status_hook = status_hook )
                
            
        finally:
            
            job_key.DeleteStatusText( 2 )
            
            job_key.SetStatusText( 'done!' )
            
            job_key.Finish()
            
            job_key.Delete( 5 )
            
        
    
    def _RegenerateTagCache( self, tag_service_key = None ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        try:
            
            job_key.SetStatusTitle( 'regenerating tag fast search cache' )
            
            self._controller.pub( 'modal_message', job_key )
            
            if tag_service_key is None:
                
                tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                
            else:
                
                tag_service_ids = ( self.modules_services.GetServiceId( tag_service_key ), )
                
            
            file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES )
            
            def status_hook( s ):
                
                job_key.SetStatusText( s, 2 )
                
            
            for ( file_service_id, tag_service_id ) in itertools.product( file_service_ids, tag_service_ids ):
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'generating specific cache {}_{}'.format( file_service_id, tag_service_id )
                
                job_key.SetStatusText( message )
                self._controller.frame_splash_status.SetSubtext( message )
                
                time.sleep( 0.01 )
                
                self.modules_tag_search.Drop( file_service_id, tag_service_id )
                
                self.modules_tag_search.Generate( file_service_id, tag_service_id )
                
                self._CacheTagsPopulate( file_service_id, tag_service_id, status_hook = status_hook )
                
            
            for tag_service_id in tag_service_ids:
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'generating combined cache {}'.format( tag_service_id )
                
                job_key.SetStatusText( message )
                self._controller.frame_splash_status.SetSubtext( message )
                
                time.sleep( 0.01 )
                
                self.modules_tag_search.Drop( self.modules_services.combined_file_service_id, tag_service_id )
                
                self.modules_tag_search.Generate( self.modules_services.combined_file_service_id, tag_service_id )
                
                self._CacheTagsPopulate( self.modules_services.combined_file_service_id, tag_service_id, status_hook = status_hook )
                
            
        finally:
            
            job_key.DeleteStatusText( 2 )
            
            job_key.SetStatusText( 'done!' )
            
            job_key.Finish()
            
            job_key.Delete( 5 )
            
        
    
    def _RegenerateTagDisplayMappingsCache( self, tag_service_key = None ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        try:
            
            job_key.SetStatusTitle( 'regenerating tag display mappings cache' )
            
            self._controller.pub( 'modal_message', job_key )
            
            if tag_service_key is None:
                
                tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                
            else:
                
                tag_service_ids = ( self.modules_services.GetServiceId( tag_service_key ), )
                
            
            file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
            
            for tag_service_id in tag_service_ids:
                
                # first off, we want to clear all the current siblings and parents so they will be reprocessed later
                # we'll also have to catch up the tag definition cache to account for this
                
                tag_ids_in_dispute = set()
                
                tag_ids_in_dispute.update( self.modules_tag_siblings.GetAllTagIds( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id ) )
                tag_ids_in_dispute.update( self.modules_tag_parents.GetAllTagIds( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id ) )
                
                self.modules_tag_siblings.ClearActual( tag_service_id )
                self.modules_tag_parents.ClearActual( tag_service_id )
                
                if len( tag_ids_in_dispute ) > 0:
                    
                    self._CacheTagsSyncTags( tag_service_id, tag_ids_in_dispute )
                    
                
            
            for ( file_service_id, tag_service_id ) in itertools.product( file_service_ids, tag_service_ids ):
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'generating specific display cache {}_{}'.format( file_service_id, tag_service_id )
                
                def status_hook_1( s: str ):
                    
                    job_key.SetStatusText( s, 2 )
                    self._controller.frame_splash_status.SetSubtext( '{} - {}'.format( message, s ) )
                    
                
                job_key.SetStatusText( message )
                self._controller.frame_splash_status.SetSubtext( message )
                
                status_hook_1( 'dropping old data' )
                
                self.modules_mappings_cache_specific_display.Drop( file_service_id, tag_service_id )
                
                self.modules_mappings_cache_specific_display.Generate( file_service_id, tag_service_id, populate_from_storage = True, status_hook = status_hook_1 )
                
            
            job_key.SetStatusText( '', 2 )
            self._controller.frame_splash_status.SetSubtext( '' )
            
            for tag_service_id in tag_service_ids:
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'generating combined display cache {}'.format( tag_service_id )
                
                def status_hook_2( s: str ):
                    
                    job_key.SetStatusText( s, 2 )
                    self._controller.frame_splash_status.SetSubtext( '{} - {}'.format( message, s ) )
                    
                
                job_key.SetStatusText( message )
                self._controller.frame_splash_status.SetSubtext( message )
                
                status_hook_2( 'dropping old data' )
                
                self.modules_mappings_cache_combined_files_display.Drop( tag_service_id )
                
                self.modules_mappings_cache_combined_files_display.Generate( tag_service_id, status_hook = status_hook_2 )
                
            
            job_key.SetStatusText( '', 2 )
            self._controller.frame_splash_status.SetSubtext( '' )
            
        finally:
            
            job_key.SetStatusText( 'done!' )
            
            job_key.Finish()
            
            job_key.Delete( 5 )
            
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_tag_display_application' )
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_force_refresh_tags_data' )
            
        
    
    def _RegenerateTagDisplayPendingMappingsCache( self, tag_service_key = None ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        try:
            
            job_key.SetStatusTitle( 'regenerating tag display pending mappings cache' )
            
            self._controller.pub( 'modal_message', job_key )
            
            if tag_service_key is None:
                
                tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                
            else:
                
                tag_service_ids = ( self.modules_services.GetServiceId( tag_service_key ), )
                
            
            file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
            
            for ( file_service_id, tag_service_id ) in itertools.product( file_service_ids, tag_service_ids ):
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'regenerating specific display cache pending {}_{}'.format( file_service_id, tag_service_id )
                
                def status_hook_1( s: str ):
                    
                    job_key.SetStatusText( s, 2 )
                    self._controller.frame_splash_status.SetSubtext( '{} - {}'.format( message, s ) )
                    
                
                job_key.SetStatusText( message )
                self._controller.frame_splash_status.SetSubtext( message )
                
                self.modules_mappings_cache_specific_display.RegeneratePending( file_service_id, tag_service_id, status_hook = status_hook_1 )
                
            
            job_key.SetStatusText( '', 2 )
            self._controller.frame_splash_status.SetSubtext( '' )
            
            for tag_service_id in tag_service_ids:
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'regenerating combined display cache pending {}'.format( tag_service_id )
                
                def status_hook_2( s: str ):
                    
                    job_key.SetStatusText( s, 2 )
                    self._controller.frame_splash_status.SetSubtext( '{} - {}'.format( message, s ) )
                    
                
                job_key.SetStatusText( message )
                self._controller.frame_splash_status.SetSubtext( message )
                
                self.modules_mappings_cache_combined_files_display.RegeneratePending( tag_service_id, status_hook = status_hook_2 )
                
            
            job_key.SetStatusText( '', 2 )
            self._controller.frame_splash_status.SetSubtext( '' )
            
        finally:
            
            job_key.SetStatusText( 'done!' )
            
            job_key.Finish()
            
            job_key.Delete( 5 )
            
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_force_refresh_tags_data' )
            
        
    
    def _RegenerateTagMappingsCache( self, tag_service_key = None ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        try:
            
            job_key.SetStatusTitle( 'regenerating tag mappings cache' )
            
            self._controller.pub( 'modal_message', job_key )
            
            if tag_service_key is None:
                
                tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                
            else:
                
                tag_service_ids = ( self.modules_services.GetServiceId( tag_service_key ), )
                
            
            file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
            tag_cache_file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES )
            
            for tag_service_id in tag_service_ids:
                
                self.modules_tag_siblings.ClearActual( tag_service_id )
                self.modules_tag_parents.ClearActual( tag_service_id )
                
            
            time.sleep( 0.01 )
            
            for ( file_service_id, tag_service_id ) in itertools.product( file_service_ids, tag_service_ids ):
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'generating specific cache {}_{}'.format( file_service_id, tag_service_id )
                
                job_key.SetStatusText( message )
                self._controller.frame_splash_status.SetSubtext( message )
                
                time.sleep( 0.01 )
                
                if file_service_id in tag_cache_file_service_ids:
                    
                    self.modules_tag_search.Drop( file_service_id, tag_service_id )
                    self.modules_tag_search.Generate( file_service_id, tag_service_id )
                    
                
                self.modules_mappings_cache_specific_storage.Drop( file_service_id, tag_service_id )
                
                self.modules_mappings_cache_specific_storage.Generate( file_service_id, tag_service_id )
                
                self._cursor_transaction_wrapper.CommitAndBegin()
                
            
            for tag_service_id in tag_service_ids:
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'generating combined cache {}'.format( tag_service_id )
                
                job_key.SetStatusText( message )
                self._controller.frame_splash_status.SetSubtext( message )
                
                time.sleep( 0.01 )
                
                self.modules_tag_search.Drop( self.modules_services.combined_file_service_id, tag_service_id )
                self.modules_tag_search.Generate( self.modules_services.combined_file_service_id, tag_service_id )
                
                self.modules_mappings_cache_combined_files_storage.Drop( tag_service_id )
                
                self.modules_mappings_cache_combined_files_storage.Generate( tag_service_id )
                
                self._cursor_transaction_wrapper.CommitAndBegin()
                
            
            if tag_service_key is None:
                
                message = 'generating local tag cache'
                
                job_key.SetStatusText( message )
                self._controller.frame_splash_status.SetSubtext( message )
                
                self.modules_tags_local_cache.Repopulate()
                
            
        finally:
            
            job_key.SetStatusText( 'done!' )
            
            job_key.Finish()
            
            job_key.Delete( 5 )
            
            HydrusData.ShowText( 'Now the mappings cache regen is done, you might want to restart the program.' )
            
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_tag_display_application' )
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_force_refresh_tags_data' )
            
        
    
    def _RegenerateTagParentsCache( self, only_these_service_ids = None ):
        
        if only_these_service_ids is None:
            
            tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
        else:
            
            tag_service_ids = only_these_service_ids
            
        
        # as siblings may have changed, parents may have as well
        self.modules_tag_parents.Regen( tag_service_ids )
        
        self._cursor_transaction_wrapper.pub_after_job( 'notify_new_tag_display_application' )
        
    
    def _RegenerateTagPendingMappingsCache( self, tag_service_key = None ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        try:
            
            job_key.SetStatusTitle( 'regenerating tag pending mappings cache' )
            
            self._controller.pub( 'modal_message', job_key )
            
            if tag_service_key is None:
                
                tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                
            else:
                
                tag_service_ids = ( self.modules_services.GetServiceId( tag_service_key ), )
                
            
            file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
            
            for ( file_service_id, tag_service_id ) in itertools.product( file_service_ids, tag_service_ids ):
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'regenerating specific cache pending {}_{}'.format( file_service_id, tag_service_id )
                
                def status_hook_1( s: str ):
                    
                    job_key.SetStatusText( s, 2 )
                    self._controller.frame_splash_status.SetSubtext( '{} - {}'.format( message, s ) )
                    
                
                job_key.SetStatusText( message )
                self._controller.frame_splash_status.SetSubtext( message )
                
                self.modules_mappings_cache_specific_storage.RegeneratePending( file_service_id, tag_service_id, status_hook = status_hook_1 )
                
            
            job_key.SetStatusText( '', 2 )
            self._controller.frame_splash_status.SetSubtext( '' )
            
            for tag_service_id in tag_service_ids:
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'regenerating combined cache pending {}'.format( tag_service_id )
                
                def status_hook_2( s: str ):
                    
                    job_key.SetStatusText( s, 2 )
                    self._controller.frame_splash_status.SetSubtext( '{} - {}'.format( message, s ) )
                    
                
                job_key.SetStatusText( message )
                self._controller.frame_splash_status.SetSubtext( message )
                
                self.modules_mappings_cache_combined_files_storage.RegeneratePending( tag_service_id, status_hook = status_hook_2 )
                
            
            job_key.SetStatusText( '', 2 )
            self._controller.frame_splash_status.SetSubtext( '' )
            
        finally:
            
            job_key.SetStatusText( 'done!' )
            
            job_key.Finish()
            
            job_key.Delete( 5 )
            
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_force_refresh_tags_data' )
            
        
    
    def _RepairDB( self, version ):
        
        # migrate most of this gubbins to the new modules system, and HydrusDB tbh!
        
        self._controller.frame_splash_status.SetText( 'checking database' )
        
        HydrusDB.HydrusDB._RepairDB( self, version )
        
        self._weakref_media_result_cache = ClientMediaResultCache.MediaResultCache()
        
        tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
        file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
        
        # caches
        
        tag_service_ids_we_have_regenned_storage_for = set()
        tag_service_ids_we_have_regenned_display_for = set()
        
        # mappings
        
        missing_service_pairs = self.modules_mappings_cache_specific_storage.GetMissingServicePairs()
        
        missing_tag_service_ids = { tag_service_id for ( file_service_id, tag_service_id ) in missing_service_pairs if tag_service_id not in tag_service_ids_we_have_regenned_storage_for }
        
        if len( missing_tag_service_ids ) > 0:
            
            missing_tag_service_ids = sorted( missing_tag_service_ids )
            
            message = 'On boot, some important tag mapping tables for the storage context were missing! You should have already had a notice about this. You may have had other problems earlier, but this particular problem is completely recoverable and results in no lost data. The relevant tables have been recreated and will now be repopulated. The services about to be worked on are:'
            message += os.linesep * 2
            message += os.linesep.join( ( str( t ) for t in missing_tag_service_ids ) )
            message += os.linesep * 2
            message += 'If you want to go ahead, click ok on this message and the client will fill these tables with the correct data. It may take some time. If you want to solve this problem otherwise, kill the hydrus process now.'
            
            BlockingSafeShowMessage( message )
            
            for tag_service_id in missing_tag_service_ids:
                
                tag_service_key = self.modules_services.GetServiceKey( tag_service_id )
                
                self._RegenerateTagMappingsCache( tag_service_key = tag_service_key )
                
                tag_service_ids_we_have_regenned_storage_for.add( tag_service_id )
                
                self.modules_db_maintenance.TouchAnalyzeNewTables()
                
                self._cursor_transaction_wrapper.CommitAndBegin()
                
            
        
        #
        
        missing_service_pairs = self.modules_mappings_cache_specific_display.GetMissingServicePairs()
        
        missing_tag_service_ids = { tag_service_id for ( file_service_id, tag_service_id ) in missing_service_pairs if tag_service_id not in tag_service_ids_we_have_regenned_storage_for and tag_service_id not in tag_service_ids_we_have_regenned_display_for }
        
        if len( missing_tag_service_ids ) > 0:
            
            missing_tag_service_ids = sorted( missing_tag_service_ids )
            
            message = 'On boot, some important tag mapping tables for the display context were missing! You should have already had a notice about this. You may have had other problems earlier, but this particular problem is completely recoverable and results in no lost data. The relevant tables have been recreated and will now be repopulated. The services about to be worked on are:'
            message += os.linesep * 2
            message += os.linesep.join( ( str( t ) for t in missing_tag_service_ids ) )
            message += os.linesep * 2
            message += 'If you want to go ahead, click ok on this message and the client will fill these tables with the correct data. It may take some time. If you want to solve this problem otherwise, kill the hydrus process now.'
            
            BlockingSafeShowMessage( message )
            
            for tag_service_id in missing_tag_service_ids:
                
                tag_service_key = self.modules_services.GetServiceKey( tag_service_id )
                
                self._RegenerateTagDisplayMappingsCache( tag_service_key = tag_service_key )
                
                tag_service_ids_we_have_regenned_display_for.add( tag_service_id )
                
                self.modules_db_maintenance.TouchAnalyzeNewTables()
                
                self._cursor_transaction_wrapper.CommitAndBegin()
                
            
        
        # autocomplete
        
        ( missing_storage_tag_count_service_pairs, missing_display_tag_count_service_pairs ) = self.modules_mappings_counts.GetMissingTagCountServicePairs()
        
        # unfortunately, for now, due to display maintenance being tag service wide, I can't regen individual lads here
        # maybe in future I can iterate all sibs/parents and just do it here and now with addimplication
        
        missing_tag_service_ids = { tag_service_id for ( file_service_id, tag_service_id ) in missing_storage_tag_count_service_pairs if tag_service_id not in tag_service_ids_we_have_regenned_storage_for }
        
        if len( missing_tag_service_ids ) > 0:
            
            missing_tag_service_ids = sorted( missing_tag_service_ids )
            
            message = 'On boot, some important tag count tables for the storage context were missing! You should have already had a notice about this. You may have had other problems earlier, but this particular problem is completely recoverable and results in no lost data. The relevant tables have been recreated and will now be repopulated. The services about to be worked on are:'
            message += os.linesep * 2
            message += os.linesep.join( ( str( t ) for t in missing_tag_service_ids ) )
            message += os.linesep * 2
            message += 'If you want to go ahead, click ok on this message and the client will fill these tables with the correct data. It may take some time. If you want to solve this problem otherwise, kill the hydrus process now.'
            
            BlockingSafeShowMessage( message )
            
            for tag_service_id in missing_tag_service_ids:
                
                tag_service_key = self.modules_services.GetService( tag_service_id ).GetServiceKey()
                
                self._RegenerateTagMappingsCache( tag_service_key = tag_service_key )
                
                tag_service_ids_we_have_regenned_storage_for.add( tag_service_id )
                
                self.modules_db_maintenance.TouchAnalyzeNewTables()
                
                self._cursor_transaction_wrapper.CommitAndBegin()
                
            
        
        #
        
        missing_tag_service_ids = { tag_service_id for ( file_service_id, tag_service_id ) in missing_display_tag_count_service_pairs if tag_service_id not in tag_service_ids_we_have_regenned_storage_for and tag_service_id not in tag_service_ids_we_have_regenned_display_for }
        
        if len( missing_tag_service_ids ) > 0:
            
            missing_tag_service_ids = sorted( missing_tag_service_ids )
            
            message = 'On boot, some important tag count tables for the display context were missing! You should have already had a notice about this. You may have had other problems earlier, but this particular problem is completely recoverable and results in no lost data. The relevant tables have been recreated and will now be repopulated. The services about to be worked on are:'
            message += os.linesep * 2
            message += os.linesep.join( ( str( t ) for t in missing_tag_service_ids ) )
            message += os.linesep * 2
            message += 'If you want to go ahead, click ok on this message and the client will fill these tables with the correct data. It may take some time. If you want to solve this problem otherwise, kill the hydrus process now.'
            
            BlockingSafeShowMessage( message )
            
            for tag_service_id in missing_tag_service_ids:
                
                tag_service_key = self.modules_services.GetService( tag_service_id ).GetServiceKey()
                
                self._RegenerateTagDisplayMappingsCache( tag_service_key = tag_service_key )
                
                tag_service_ids_we_have_regenned_display_for.add( tag_service_id )
                
                self.modules_db_maintenance.TouchAnalyzeNewTables()
                
                self._cursor_transaction_wrapper.CommitAndBegin()
                
            
        
        # tag search, this requires autocomplete and siblings/parents in place
        
        missing_tag_search_service_pairs = self.modules_tag_search.GetMissingTagSearchServicePairs()
        
        missing_tag_search_service_pairs = [ ( file_service_id, tag_service_id ) for ( file_service_id, tag_service_id ) in missing_tag_search_service_pairs if tag_service_id not in tag_service_ids_we_have_regenned_storage_for ]
        
        if len( missing_tag_search_service_pairs ) > 0:
            
            missing_tag_search_service_pairs = sorted( missing_tag_search_service_pairs )
            
            message = 'On boot, some important tag search tables were missing! You should have already had a notice about this. You may have had other problems earlier, but this particular problem is completely recoverable and results in no lost data. The relevant tables have been recreated and will now be repopulated. The service pairs about to be worked on are:'
            message += os.linesep * 2
            message += os.linesep.join( ( str( t ) for t in missing_tag_search_service_pairs ) )
            message += os.linesep * 2
            message += 'If you want to go ahead, click ok on this message and the client will fill these tables with the correct data. It may take some time. If you want to solve this problem otherwise, kill the hydrus process now.'
            
            BlockingSafeShowMessage( message )
            
            for ( file_service_id, tag_service_id ) in missing_tag_search_service_pairs:
                
                self.modules_tag_search.Drop( file_service_id, tag_service_id )
                self.modules_tag_search.Generate( file_service_id, tag_service_id )
                self._CacheTagsPopulate( file_service_id, tag_service_id )
                
                self.modules_db_maintenance.TouchAnalyzeNewTables()
                
                self._cursor_transaction_wrapper.CommitAndBegin()
                
            
        
        #
        
        new_options = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS )
        
        if new_options is None:
            
            message = 'On boot, your main options object was missing!'
            message += os.linesep * 2
            message += 'If you wish, click ok on this message and the client will re-add fresh options with default values. But if you want to solve this problem otherwise, kill the hydrus process now.'
            message += os.linesep * 2
            message += 'If you do not already know what caused this, it was likely a hard drive fault--either due to a recent abrupt power cut or actual hardware failure. Check \'help my db is broke.txt\' in the install_dir/db directory as soon as you can.'
            
            BlockingSafeShowMessage( message )
            
            new_options = ClientOptions.ClientOptions()
            
            new_options.SetSimpleDownloaderFormulae( ClientDefaults.GetDefaultSimpleDownloaderFormulae() )
            
            self.modules_serialisable.SetJSONDump( new_options )
            
        
        # an explicit empty string so we don't linger on 'checking database' if the next stage lags a bit on its own update. no need to give anyone heart attacks
        self._controller.frame_splash_status.SetText( '' )
        
    
    def _RepairInvalidTags( self, job_key: typing.Optional[ ClientThreading.JobKey ] = None ):
        
        invalid_tag_ids_and_tags = set()
        
        BLOCK_SIZE = 1000
        
        select_statement = 'SELECT tag_id FROM tags;'
        
        bad_tag_count = 0
        
        for ( group_of_tag_ids, num_done, num_to_do ) in HydrusDB.ReadLargeIdQueryInSeparateChunks( self._c, select_statement, BLOCK_SIZE ):
            
            if job_key is not None:
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'Scanning tags: {} - Bad Found: {}'.format( HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do ), HydrusData.ToHumanInt( bad_tag_count ) )
                
                job_key.SetStatusText( message )
                
            
            for tag_id in group_of_tag_ids:
                
                tag = self.modules_tags_local_cache.GetTag( tag_id )
                
                try:
                    
                    cleaned_tag = HydrusTags.CleanTag( tag )
                    
                    HydrusTags.CheckTagNotEmpty( cleaned_tag )
                    
                except:
                    
                    cleaned_tag = 'unrecoverable invalid tag'
                    
                
                if tag != cleaned_tag:
                    
                    invalid_tag_ids_and_tags.add( ( tag_id, tag, cleaned_tag ) )
                    
                    bad_tag_count += 1
                    
                
            
        
        file_service_ids = list( self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES ) )
        file_service_ids.append( self.modules_services.combined_file_service_id )
        
        tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
        
        for ( i, ( tag_id, tag, cleaned_tag ) ) in enumerate( invalid_tag_ids_and_tags ):
            
            if job_key is not None:
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'Fixing bad tags: {}'.format( HydrusData.ConvertValueRangeToPrettyString( i + 1, bad_tag_count ) )
                
                job_key.SetStatusText( message )
                
            
            # now find an entirely new namespace_id, subtag_id pair for this tag
            
            existing_tags = set()
            
            potential_new_cleaned_tag = cleaned_tag
            
            while self.modules_tags.TagExists( potential_new_cleaned_tag ):
                
                existing_tags.add( potential_new_cleaned_tag )
                
                potential_new_cleaned_tag = HydrusData.GetNonDupeName( cleaned_tag, existing_tags )
                
            
            cleaned_tag = potential_new_cleaned_tag
            
            ( namespace, subtag ) = HydrusTags.SplitTag( cleaned_tag )
            
            namespace_id = self.modules_tags.GetNamespaceId( namespace )
            subtag_id = self.modules_tags.GetSubtagId( subtag )
            
            self.modules_tags.UpdateTagId( tag_id, namespace_id, subtag_id )
            self.modules_tags_local_cache.UpdateTagInCache( tag_id, cleaned_tag )
            
            for ( file_service_id, tag_service_id ) in itertools.product( file_service_ids, tag_service_ids ):
                
                if self.modules_tag_search.HasTag( file_service_id, tag_service_id, tag_id ):
                    
                    self.modules_tag_search.DeleteTags( file_service_id, tag_service_id, ( tag_id, ) )
                    self.modules_tag_search.AddTags( file_service_id, tag_service_id, ( tag_id, ) )
                    
                
            
            try:
                
                HydrusData.Print( 'Invalid tag fixing: {} replaced with {}'.format( repr( tag ), repr( cleaned_tag ) ) )
                
            except:
                
                HydrusData.Print( 'Invalid tag fixing: Could not even print the bad tag to the log! It is now known as {}'.format( repr( cleaned_tag ) ) )
                
            
        
        if job_key is not None:
            
            if not job_key.IsCancelled():
                
                if bad_tag_count == 0:
                    
                    message = 'Invalid tag scanning: No bad tags found!'
                    
                else:
                    
                    message = 'Invalid tag scanning: {} bad tags found and fixed! They have been written to the log.'.format( HydrusData.ToHumanInt( bad_tag_count ) )
                    
                    self._cursor_transaction_wrapper.pub_after_job( 'notify_new_force_refresh_tags_data' )
                    
                
                HydrusData.Print( message )
                
                job_key.SetStatusText( message )
                
            
            job_key.Finish()
            
        
    
    def _RepopulateMappingsFromCache( self, tag_service_key = None, job_key = None ):
        
        BLOCK_SIZE = 10000
        
        num_rows_recovered = 0
        
        if tag_service_key is None:
            
            tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
        else:
            
            tag_service_ids = ( self.modules_services.GetServiceId( tag_service_key ), )
            
        
        for tag_service_id in tag_service_ids:
            
            service = self.modules_services.GetService( tag_service_id )
            
            name = service.GetName()
            
            ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( self.modules_services.combined_local_file_service_id, tag_service_id )
            
            ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( tag_service_id )
            
            current_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_file_service_id, HC.CONTENT_STATUS_CURRENT )
            
            select_statement = 'SELECT hash_id FROM {};'.format( current_files_table_name )
            
            for ( group_of_hash_ids, num_done, num_to_do ) in HydrusDB.ReadLargeIdQueryInSeparateChunks( self._c, select_statement, BLOCK_SIZE ):
                
                if job_key is not None:
                    
                    message = 'Doing "{}"\u2026: {}'.format( name, HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do ) )
                    message += os.linesep * 2
                    message += 'Total rows recovered: {}'.format( HydrusData.ToHumanInt( num_rows_recovered ) )
                    
                    job_key.SetStatusText( message )
                    
                    if job_key.IsCancelled():
                        
                        return
                        
                    
                
                with self._MakeTemporaryIntegerTable( group_of_hash_ids, 'hash_id' ) as temp_table_name:
                    
                    # temp hashes to mappings
                    insert_template = 'INSERT OR IGNORE INTO {} ( tag_id, hash_id ) SELECT tag_id, hash_id FROM {} CROSS JOIN {} USING ( hash_id );'
                    
                    self._Execute( insert_template.format( current_mappings_table_name, temp_table_name, cache_current_mappings_table_name ) )
                    
                    num_rows_recovered += self._GetRowCount()
                    
                    self._Execute( insert_template.format( deleted_mappings_table_name, temp_table_name, cache_deleted_mappings_table_name ) )
                    
                    num_rows_recovered += self._GetRowCount()
                    
                    self._Execute( insert_template.format( pending_mappings_table_name, temp_table_name, cache_pending_mappings_table_name ) )
                    
                    num_rows_recovered += self._GetRowCount()
                    
                
            
        
        if job_key is not None:
            
            job_key.SetStatusText( 'Done! Rows recovered: {}'.format( HydrusData.ToHumanInt( num_rows_recovered ) ) )
            
            job_key.Finish()
            
        
    
    def _RepopulateTagCacheMissingSubtags( self, tag_service_key = None ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        try:
            
            job_key.SetStatusTitle( 'repopulate tag fast search cache subtags' )
            
            self._controller.pub( 'modal_message', job_key )
            
            if tag_service_key is None:
                
                tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                
            else:
                
                tag_service_ids = ( self.modules_services.GetServiceId( tag_service_key ), )
                
            
            file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES )
            
            def status_hook( s ):
                
                job_key.SetStatusText( s, 2 )
                
            
            for ( file_service_id, tag_service_id ) in itertools.product( file_service_ids, tag_service_ids ):
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'repopulating specific cache {}_{}'.format( file_service_id, tag_service_id )
                
                job_key.SetStatusText( message )
                self._controller.frame_splash_status.SetSubtext( message )
                
                time.sleep( 0.01 )
                
                self.modules_tag_search.RepopulateMissingSubtags( file_service_id, tag_service_id )
                
            
            for tag_service_id in tag_service_ids:
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                message = 'repopulating combined cache {}'.format( tag_service_id )
                
                job_key.SetStatusText( message )
                self._controller.frame_splash_status.SetSubtext( message )
                
                time.sleep( 0.01 )
                
                self.modules_tag_search.RepopulateMissingSubtags( self.modules_services.combined_file_service_id, tag_service_id )
                
            
        finally:
            
            job_key.DeleteStatusText( 2 )
            
            job_key.SetStatusText( 'done!' )
            
            job_key.Finish()
            
            job_key.Delete( 5 )
            
        
    
    def _RepopulateTagDisplayMappingsCache( self, tag_service_key = None ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        try:
            
            job_key.SetStatusTitle( 'repopulating tag display mappings cache' )
            
            self._controller.pub( 'modal_message', job_key )
            
            if tag_service_key is None:
                
                tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                
            else:
                
                tag_service_ids = ( self.modules_services.GetServiceId( tag_service_key ), )
                
            
            file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
            
            for ( i, file_service_id ) in enumerate( file_service_ids ):
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                table_name = ClientDBFilesStorage.GenerateFilesTableName( file_service_id, HC.CONTENT_STATUS_CURRENT )
                
                for ( group_of_ids, num_done, num_to_do ) in HydrusDB.ReadLargeIdQueryInSeparateChunks( self._c, 'SELECT hash_id FROM {};'.format( table_name ), 1024 ):
                    
                    message = 'repopulating {} {}'.format( HydrusData.ConvertValueRangeToPrettyString( i + 1, len( file_service_ids ) ), HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do ) )
                    
                    job_key.SetStatusText( message )
                    self._controller.frame_splash_status.SetSubtext( message )
                    
                    with self._MakeTemporaryIntegerTable( group_of_ids, 'hash_id' ) as temp_hash_id_table_name:
                        
                        for tag_service_id in tag_service_ids:
                            
                            self.modules_mappings_cache_specific_storage.AddFiles( file_service_id, tag_service_id, group_of_ids, temp_hash_id_table_name )
                            self.modules_mappings_cache_specific_display.AddFiles( file_service_id, tag_service_id, group_of_ids, temp_hash_id_table_name )
                            
                        
                    
                
            
            job_key.SetStatusText( '', 2 )
            self._controller.frame_splash_status.SetSubtext( '' )
            
        finally:
            
            job_key.SetStatusText( 'done!' )
            
            job_key.Finish()
            
            job_key.Delete( 5 )
            
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_force_refresh_tags_data' )
            
        
    
    def _ReportOverupdatedDB( self, version ):
        
        message = 'This client\'s database is version {}, but the software is version {}! This situation only sometimes works, and when it does not, it can break things! If you are not sure what is going on, or if you accidentally installed an older version of the software to a newer database, force-kill this client in Task Manager right now. Otherwise, ok this dialog box to continue.'.format( HydrusData.ToHumanInt( version ), HydrusData.ToHumanInt( HC.SOFTWARE_VERSION ) )
        
        BlockingSafeShowMessage( message )
        
    
    def _ReportUnderupdatedDB( self, version ):
        
        message = 'This client\'s database is version {}, but the software is significantly later, {}! Trying to update many versions in one go can be dangerous due to bitrot. I suggest you try at most to only do 10 versions at once. If you want to try a big jump anyway, you should make sure you have a backup beforehand so you can roll back to it in case the update makes your db unbootable. If you would rather try smaller updates, or you do not have a backup, force-kill this client in Task Manager right now. Otherwise, ok this dialog box to continue.'.format( HydrusData.ToHumanInt( version ), HydrusData.ToHumanInt( HC.SOFTWARE_VERSION ) )
        
        BlockingSafeShowMessage( message )
        
    
    def _ResetRepository( self, service ):
        
        ( service_key, service_type, name, dictionary ) = service.ToTuple()
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        prefix = 'resetting ' + name
        
        job_key = ClientThreading.JobKey()
        
        try:
            
            job_key.SetStatusText( prefix + ': deleting service' )
            
            self._controller.pub( 'modal_message', job_key )
            
            self._DeleteService( service_id )
            
            job_key.SetStatusText( prefix + ': recreating service' )
            
            self._AddService( service_key, service_type, name, dictionary )
            
            self._cursor_transaction_wrapper.pub_after_job( 'notify_account_sync_due' )
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_pending' )
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_services_data' )
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_services_gui' )
            
            job_key.SetStatusText( prefix + ': done!' )
            
        finally:
            
            job_key.Finish()
            
        
    
    def _ResetRepositoryProcessing( self, service_key: bytes, content_types ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        service = self.modules_services.GetService( service_id )
        
        service_type = service.GetServiceType()
        
        prefix = 'resetting content'
        
        job_key = ClientThreading.JobKey()
        
        try:
            
            service_info_types_to_delete = []
            
            job_key.SetStatusText( '{}: calculating'.format( prefix ) )
            
            self._controller.pub( 'modal_message', job_key )
            
            # note that siblings/parents do not do a cachetags clear-regen because they only actually delete ideal, not actual
            
            if HC.CONTENT_TYPE_FILES in content_types:
                
                service_info_types_to_delete.extend( { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_VIEWABLE_FILES, HC.SERVICE_INFO_TOTAL_SIZE, HC.SERVICE_INFO_NUM_DELETED_FILES } )
                
                self._Execute( 'DELETE FROM remote_thumbnails WHERE service_id = ?;', ( service_id, ) )
                
                if service_type in HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES:
                    
                    self.modules_files_storage.ClearFilesTables( service_id, keep_pending = True )
                    
                
                if service_type in HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES:
                    
                    tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                    
                    for tag_service_id in tag_service_ids:
                        
                        self.modules_mappings_cache_specific_storage.Clear( service_id, tag_service_id, keep_pending = True )
                        
                        if service_type in HC.FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES:
                            
                            # not clear since siblings and parents can contribute
                            self.modules_tag_search.Drop( service_id, tag_service_id )
                            self.modules_tag_search.Generate( service_id, tag_service_id )
                            self._CacheTagsPopulate( service_id, tag_service_id )
                            
                        
                    
                
            
            if HC.CONTENT_TYPE_MAPPINGS in content_types:
                
                service_info_types_to_delete.extend( { HC.SERVICE_INFO_NUM_FILE_HASHES, HC.SERVICE_INFO_NUM_TAGS, HC.SERVICE_INFO_NUM_MAPPINGS, HC.SERVICE_INFO_NUM_DELETED_MAPPINGS } )
                
                if service_type in HC.REAL_TAG_SERVICES:
                    
                    self.modules_mappings_storage.ClearMappingsTables( service_id )
                    
                    self.modules_mappings_cache_combined_files_storage.Clear( service_id, keep_pending = True )
                    
                    self.modules_tag_search.Drop( self.modules_services.combined_file_service_id, service_id )
                    self.modules_tag_search.Generate( self.modules_services.combined_file_service_id, service_id )
                    self._CacheTagsPopulate( self.modules_services.combined_file_service_id, service_id )
                    
                    file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
                    tag_cache_file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES )
                    
                    for file_service_id in file_service_ids:
                        
                        self.modules_mappings_cache_specific_storage.Clear( file_service_id, service_id, keep_pending = True )
                        
                        if file_service_id in tag_cache_file_service_ids:
                            
                            # not clear since siblings and parents can contribute
                            self.modules_tag_search.Drop( file_service_id, service_id )
                            self.modules_tag_search.Generate( file_service_id, service_id )
                            self._CacheTagsPopulate( file_service_id, service_id )
                            
                        
                    
                
            
            if HC.CONTENT_TYPE_TAG_PARENTS in content_types:
                
                self._Execute( 'DELETE FROM tag_parents WHERE service_id = ?;', ( service_id, ) )
                self._Execute( 'DELETE FROM tag_parent_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_PETITIONED ) )
                
                ( cache_ideal_tag_parents_lookup_table_name, cache_actual_tag_parents_lookup_table_name ) = ClientDBTagParents.GenerateTagParentsLookupCacheTableNames( service_id )
                
                # do not delete from actual!
                self._Execute( 'DELETE FROM {};'.format( cache_ideal_tag_parents_lookup_table_name ) )
                
            
            if HC.CONTENT_TYPE_TAG_SIBLINGS in content_types:
                
                self._Execute( 'DELETE FROM tag_siblings WHERE service_id = ?;', ( service_id, ) )
                self._Execute( 'DELETE FROM tag_sibling_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_PETITIONED ) )
                
                ( cache_ideal_tag_siblings_lookup_table_name, cache_actual_tag_siblings_lookup_table_name ) = ClientDBTagSiblings.GenerateTagSiblingsLookupCacheTableNames( service_id )
                
                self._Execute( 'DELETE FROM {};'.format( cache_ideal_tag_siblings_lookup_table_name ) )
                
            
            #
            
            job_key.SetStatusText( '{}: recalculating'.format( prefix ) )
            
            if HC.CONTENT_TYPE_TAG_PARENTS in content_types or HC.CONTENT_TYPE_TAG_SIBLINGS in content_types:
                
                interested_service_ids = set( self.modules_tag_display.GetInterestedServiceIds( service_id ) )
                
                if len( interested_service_ids ) > 0:
                    
                    self.modules_tag_display.RegenerateTagSiblingsAndParentsCache( only_these_service_ids = interested_service_ids )
                    
                
            
            self._ExecuteMany( 'DELETE FROM service_info WHERE service_id = ? AND info_type = ?;', ( ( service_id, info_type ) for info_type in service_info_types_to_delete ) )
            
            self.modules_repositories.ReprocessRepository( service_key, content_types )
            
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_services_data' )
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_services_gui' )
            
            job_key.SetStatusText( prefix + ': done!' )
            
        finally:
            
            job_key.Finish()
            
        
    
    def _ResyncTagMappingsCacheFiles( self, tag_service_key = None ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        try:
            
            job_key.SetStatusTitle( 'resyncing tag mappings cache files' )
            
            self._controller.pub( 'modal_message', job_key )
            
            if tag_service_key is None:
                
                tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                
            else:
                
                tag_service_ids = ( self.modules_services.GetServiceId( tag_service_key ), )
                
            
            problems_found = False
            
            file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
            
            for file_service_id in file_service_ids:
                
                file_service_key = self.modules_services.GetServiceKey( file_service_id )
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( file_service_key )
                
                for tag_service_id in tag_service_ids:
                    
                    message = 'resyncing caches for {}_{}'.format( file_service_id, tag_service_id )
                    
                    job_key.SetStatusText( message )
                    self._controller.frame_splash_status.SetSubtext( message )
                    
                    if job_key.IsCancelled():
                        
                        break
                        
                    
                    ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
                    
                    hash_ids_in_this_cache = self._STS( self._Execute( 'SELECT DISTINCT hash_id FROM {};'.format( cache_current_mappings_table_name ) ) )
                    hash_ids_in_this_cache.update( self._STL( self._Execute( 'SELECT DISTINCT hash_id FROM {};'.format( cache_current_mappings_table_name ) ) ) )
                    
                    hash_ids_in_this_cache_and_in_file_service = self.modules_files_storage.FilterHashIds( location_context, hash_ids_in_this_cache )
                    
                    # for every file in cache, if it is not in current files, remove it
                    
                    hash_ids_in_this_cache_but_not_in_file_service = hash_ids_in_this_cache.difference( hash_ids_in_this_cache_and_in_file_service )
                    
                    if len( hash_ids_in_this_cache_but_not_in_file_service ) > 0:
                        
                        problems_found = True
                        
                        HydrusData.ShowText( '{} surplus files in {}_{}!'.format( HydrusData.ToHumanInt( len( hash_ids_in_this_cache_but_not_in_file_service ) ), file_service_id, tag_service_id ) )
                        
                        with self._MakeTemporaryIntegerTable( hash_ids_in_this_cache_but_not_in_file_service, 'hash_id' ) as temp_hash_id_table_name:
                            
                            self.modules_mappings_cache_specific_storage.DeleteFiles( file_service_id, tag_service_id, hash_ids_in_this_cache_but_not_in_file_service, temp_hash_id_table_name )
                            
                        
                    
                    # for every file in current files, if it is not in cache, add it
                    
                    hash_ids_in_file_service = set( self.modules_files_storage.GetCurrentHashIdsList( file_service_id ) )
                    
                    hash_ids_in_file_service_and_not_in_cache = hash_ids_in_file_service.difference( hash_ids_in_this_cache )
                    
                    ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( tag_service_id )
                    
                    with self._MakeTemporaryIntegerTable( hash_ids_in_file_service_and_not_in_cache, 'hash_id' ) as temp_hash_id_table_name:
                        
                        hash_ids_in_file_service_and_not_in_cache_that_have_tags = self._STS( self._Execute( 'SELECT hash_id FROM {} WHERE EXISTS ( SELECT 1 FROM {} WHERE {}.hash_id = {}.hash_id );'.format( temp_hash_id_table_name, current_mappings_table_name, current_mappings_table_name, temp_hash_id_table_name ) ) )
                        hash_ids_in_file_service_and_not_in_cache_that_have_tags.update( self._STL( self._Execute( 'SELECT hash_id FROM {} WHERE EXISTS ( SELECT 1 FROM {} WHERE {}.hash_id = {}.hash_id );'.format( temp_hash_id_table_name, current_mappings_table_name, current_mappings_table_name, temp_hash_id_table_name ) ) ) )
                        
                    
                    if len( hash_ids_in_file_service_and_not_in_cache_that_have_tags ) > 0:
                        
                        problems_found = True
                        
                        HydrusData.ShowText( '{} missing files in {}_{}!'.format( HydrusData.ToHumanInt( len( hash_ids_in_file_service_and_not_in_cache_that_have_tags ) ), file_service_id, tag_service_id ) )
                        
                        with self._MakeTemporaryIntegerTable( hash_ids_in_file_service_and_not_in_cache_that_have_tags, 'hash_id' ) as temp_hash_id_table_name:
                            
                            self.modules_mappings_cache_specific_storage.AddFiles( file_service_id, tag_service_id, hash_ids_in_file_service_and_not_in_cache_that_have_tags, temp_hash_id_table_name )
                            
                        
                    
                
            
            if not problems_found:
                
                HydrusData.ShowText( 'All checks ok--no desynced mapping caches!' )
                
            
        finally:
            
            job_key.SetStatusText( 'done!' )
            
            job_key.Finish()
            
            job_key.Delete( 5 )
            
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_tag_display_application' )
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_force_refresh_tags_data' )
            
        
    
    def _SaveDirtyServices( self, dirty_services ):
        
        # if allowed to save objects
        
        self._SaveServices( dirty_services )
        
    
    def _SaveServices( self, services ):
        
        for service in services:
            
            self.modules_services.UpdateService( service )
            
        
    
    def _SaveOptions( self, options ):
        
        try:
            
            self._Execute( 'UPDATE options SET options = ?;', ( options, ) )
            
        except:
            
            HydrusData.Print( 'Failed options save dump:' )
            HydrusData.Print( options )
            
            raise
            
        
        self._cursor_transaction_wrapper.pub_after_job( 'notify_new_options' )
        
    
    def _SetPassword( self, password ):
        
        if password is not None:
            
            password_bytes = bytes( password, 'utf-8' )
            
            password = hashlib.sha256( password_bytes ).digest()
            
        
        self._controller.options[ 'password' ] = password
        
        self._SaveOptions( self._controller.options )
        
    
    def _UndeleteFiles( self, service_id, hash_ids ):
        
        if service_id in ( self.modules_services.combined_local_file_service_id, self.modules_services.combined_local_media_service_id, self.modules_services.trash_service_id ):
            
            service_ids_to_do = self.modules_services.GetServiceIds( ( HC.LOCAL_FILE_DOMAIN, ) )
            
        else:
            
            service_ids_to_do = ( service_id, )
            
        
        for service_id_to_do in service_ids_to_do:
            
            rows = self.modules_files_storage.GetUndeleteRows( service_id_to_do, hash_ids )
            
            if len( rows ) > 0:
                
                self._AddFiles( service_id_to_do, rows )
                
            
        
    
    def _UpdateDB( self, version ):
        
        self._controller.frame_splash_status.SetText( 'updating db to v' + str( version + 1 ) )
        
        if version == 470:
            
            ( result, ) = self._Execute( 'SELECT sql FROM sqlite_master WHERE name = ?;', ( 'file_viewing_stats', ) ).fetchone()
            
            if 'preview_views' in result:
                
                self._controller.frame_splash_status.SetSubtext( 'reworking file viewing stats' )
                
                self._Execute( 'ALTER TABLE file_viewing_stats RENAME TO file_viewing_stats_old;' )
                
                self._Execute( 'CREATE TABLE IF NOT EXISTS file_viewing_stats ( hash_id INTEGER, canvas_type INTEGER, last_viewed_timestamp INTEGER, views INTEGER, viewtime INTEGER, PRIMARY KEY ( hash_id, canvas_type ) );' )
                self._CreateIndex( 'file_viewing_stats', [ 'last_viewed_timestamp' ] )
                self._CreateIndex( 'file_viewing_stats', [ 'views' ] )
                self._CreateIndex( 'file_viewing_stats', [ 'viewtime' ] )
                
                self._Execute( 'INSERT INTO file_viewing_stats SELECT hash_id, ?, ?, preview_views, preview_viewtime FROM file_viewing_stats_old;', ( CC.CANVAS_PREVIEW, None ) )
                self._Execute( 'INSERT INTO file_viewing_stats SELECT hash_id, ?, ?, media_views, media_viewtime FROM file_viewing_stats_old;', ( CC.CANVAS_MEDIA_VIEWER, None ) )
                
                self.modules_db_maintenance.AnalyzeTable( 'file_viewing_stats' )
                
                self._Execute( 'DROP TABLE file_viewing_stats_old;' )
                
            
        
        if version == 472:
            
            try:
                
                from hydrus.client.gui import ClientGUIShortcuts
                
                main_gui = self.modules_serialisable.GetJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET, dump_name = 'main_gui' )
                
                palette_shortcut = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'P' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] )
                palette_command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_COMMAND_PALETTE )
                
                result = main_gui.GetCommand( palette_shortcut )
                
                if result is None:
                    
                    main_gui.SetCommand( palette_shortcut, palette_command )
                    
                    self.modules_serialisable.SetJSONDump( main_gui )
                    
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'The new palette shortcut failed to set! This is not super important, but hydev would be interested in seeing the error that was printed to the log.'
                
                self.pub_initial_message( message )
                
            
        
        if version == 473:
            
            result = self._Execute( 'SELECT 1 FROM sqlite_master WHERE name = ?;', ( 'archive_timestamps', ) ).fetchone()
            
            if result is None:
                
                self._Execute( 'CREATE TABLE IF NOT EXISTS archive_timestamps ( hash_id INTEGER PRIMARY KEY, archived_timestamp INTEGER );' )
                self._CreateIndex( 'archive_timestamps', [ 'archived_timestamp' ] )
                
            
            try:
                
                location_context = ClientLocation.LocationContext( current_service_keys = ( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ) )
                
                db_location_context = self.modules_files_storage.GetDBLocationContext( location_context )
                
                operator = '>'
                num_relationships = 0
                dupe_type = HC.DUPLICATE_POTENTIAL
                
                dupe_hash_ids = self.modules_files_duplicates.GetHashIdsFromDuplicateCountPredicate( db_location_context, operator, num_relationships, dupe_type )
                
                with self._MakeTemporaryIntegerTable( dupe_hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                    
                    hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN files_info USING ( hash_id ) WHERE mime IN {};'.format( temp_hash_ids_table_name, HydrusData.SplayListForDB( ( HC.IMAGE_GIF, HC.IMAGE_PNG, HC.IMAGE_TIFF ) ) ), ) )
                    
                    self.modules_files_maintenance_queue.AddJobs( hash_ids, ClientFiles.REGENERATE_FILE_DATA_JOB_PIXEL_HASH )
                    
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Some pixel hash regen scheduling failed to set! This is not super important, but hydev would be interested in seeing the error that was printed to the log.'
                
                self.pub_initial_message( message )
                
            
        
        if version == 474:
            
            try:
                
                # ok we have improved apng detection now, so let's efficiently guess which of our pngs could be apngs for rescan
                # IRL data of some 2-frame (i.e. minimal inaccuracy) apngs: 1.16MB @ 908x1,214 and 397KB @ 500x636, which for a single frame calculation is bitrates of 1.08 bits/pixel and 1.28 bits/pixel
                # most apngs are going to be above this fake 1-frame bitrate
                # as an aside, IRL data of some chunky pngs give about 2.5 bits/pixel, efficient screenshots and monochome tend to be around 0.2
                # real apngs divided by number of frames tend to be around 0.05 to 0.2 to 1.0
                # so, let's pull all the pngs with bitrate over 0.85 and schedule them for rescan
                
                table_join = self.modules_files_storage.GetTableJoinLimitedByFileDomain( self.modules_services.combined_local_file_service_id, 'files_info', HC.CONTENT_STATUS_CURRENT )
                
                hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM {} WHERE mime = ? AND size / ( width * height ) > ?;'.format( table_join ), ( HC.IMAGE_PNG, 0.85 ) ) )
                
                self.modules_files_maintenance_queue.AddJobs( hash_ids, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_METADATA )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Some apng regen scheduling failed to set! This is not super important, but hydev would be interested in seeing the error that was printed to the log.'
                
                self.pub_initial_message( message )
                
            
            try:
                
                table_join = self.modules_files_storage.GetTableJoinLimitedByFileDomain( self.modules_services.combined_local_file_service_id, 'files_info', HC.CONTENT_STATUS_CURRENT )
                
                hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM {} WHERE mime = ?;'.format( table_join ), ( HC.AUDIO_M4A, ) ) )
                
                self.modules_files_maintenance_queue.AddJobs( hash_ids, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_METADATA )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Some mp4 regen scheduling failed to set! This is not super important, but hydev would be interested in seeing the error that was printed to the log.'
                
                self.pub_initial_message( message )
                
            
            try:
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                domain_manager.OverwriteDefaultParsers( ( 'deviant art file extended_fetch parser', ) )
                
                #
                
                from hydrus.client.networking import ClientNetworkingContexts
                
                sank_network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, 'sankakucomplex.com' )
                
                network_contexts_to_custom_header_dicts = domain_manager.GetNetworkContextsToCustomHeaderDicts()
                
                if sank_network_context in network_contexts_to_custom_header_dicts:
                    
                    custom_header_dict = network_contexts_to_custom_header_dicts[ sank_network_context ]
                    
                    if 'User-Agent' in custom_header_dict:
                        
                        ( header, verified, reason ) = custom_header_dict[ 'User-Agent' ]
                        
                        if header == 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0':
                            
                            header = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
                            
                            custom_header_dict[ 'User-Agent' ] = ( header, verified, reason )
                            
                            domain_manager.SetNetworkContextsToCustomHeaderDicts( network_contexts_to_custom_header_dicts )
                            
                        
                    
                
                #
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some parsers failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 475:
            
            result = self._Execute( 'SELECT 1 FROM sqlite_master WHERE name = ?;', ( 'file_domain_modified_timestamps', ) ).fetchone()
            
            if result is None:
                
                self._Execute( 'CREATE TABLE IF NOT EXISTS file_domain_modified_timestamps ( hash_id INTEGER, domain_id INTEGER, file_modified_timestamp INTEGER, PRIMARY KEY ( hash_id, domain_id ) );' )
                self._CreateIndex( 'file_domain_modified_timestamps', [ 'file_modified_timestamp' ] )
                
            
        
        if version == 476:
            
            try:
                
                # fixed apng duration calculation
                
                table_join = self.modules_files_storage.GetTableJoinLimitedByFileDomain( self.modules_services.combined_local_file_service_id, 'files_info', HC.CONTENT_STATUS_CURRENT )
                
                hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM {} WHERE mime = ?;'.format( table_join ), ( HC.IMAGE_APNG, ) ) )
                
                self.modules_files_maintenance_queue.AddJobs( hash_ids, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_METADATA )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Some apng regen scheduling failed to set! This is not super important, but hydev would be interested in seeing the error that was printed to the log.'
                
                self.pub_initial_message( message )
                
            
            try:
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                domain_manager.OverwriteDefaultParsers( ( 'nitter tweet parser', 'nitter tweet parser (video from koto.reisen)' ) )
                
                #
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some parsers failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 478:
            
            try:
                
                # transparent webp regen
                
                table_join = self.modules_files_storage.GetTableJoinLimitedByFileDomain( self.modules_services.combined_local_file_service_id, 'files_info', HC.CONTENT_STATUS_CURRENT )
                
                hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM {} WHERE mime = ?;'.format( table_join ), ( HC.IMAGE_WEBP, ) ) )
                
                self.modules_files_maintenance_queue.AddJobs( hash_ids, ClientFiles.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Some webp regen scheduling failed to set! This is not super important, but hydev would be interested in seeing the error that was printed to the log.'
                
                self.pub_initial_message( message )
                
            
        
        if version == 480:
            
            try:
                
                from hydrus.client.gui.canvas import ClientGUIMPV
                
                if ClientGUIMPV.MPV_IS_AVAILABLE and HC.PLATFORM_LINUX:
                    
                    new_options = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS )
                    
                    show_message = False
                    
                    for mime in ( HC.IMAGE_GIF, HC.VIDEO_MP4, HC.AUDIO_MP3 ):
                        
                        ( media_show_action, media_start_paused, media_start_with_embed ) = new_options.GetMediaShowAction( mime )
                        
                        if media_show_action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE:
                            
                            show_message = True
                            
                        
                    
                    if show_message:
                        
                        message = 'Hey, you are a Linux user and seem to have MPV support but you are not set to use MPV for one or more filetypes. If you know all about this, no worries, ignore this message. But if you are a long-time Linux user, you may have been reverted to the native hydrus renderer many releases ago due to stability worries. If you did not know hydrus supports audio now, please check the filetype options under _options->media_ and give mpv a go!'
                        
                        self.pub_initial_message( message )
                        
                    
                
            except:
                
                pass
                
            
        
        if version == 481:
            
            try:
                
                new_options = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS )
                
                old_options = self._GetOptions()
                
                new_options.SetInteger( 'thumbnail_cache_size', old_options[ 'thumbnail_cache_size' ] )
                new_options.SetInteger( 'image_cache_size', old_options[ 'fullscreen_cache_size' ] )
                
                new_options.SetBoolean( 'pause_export_folders_sync', old_options[ 'pause_export_folders_sync' ] )
                new_options.SetBoolean( 'pause_import_folders_sync', old_options[ 'pause_import_folders_sync' ] )
                new_options.SetBoolean( 'pause_repo_sync', old_options[ 'pause_repo_sync' ] )
                new_options.SetBoolean( 'pause_subs_sync', old_options[ 'pause_subs_sync' ] )
                
                self.modules_serialisable.SetJSONDump( new_options )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Updating some cache sizes and pause states to a new options structure failed! This is not super important, but hydev would be interested in seeing the error that was printed to the log. Also check _options->speed and memory_ for your thumbnail/image cache sizes, and your subs/repository/import folder/export folder pause status.'
                
                self.pub_initial_message( message )
                
            
        
        if version == 482:
            
            self._Execute( 'UPDATE services SET service_type = ? WHERE service_key = ?;', ( HC.LOCAL_FILE_UPDATE_DOMAIN, sqlite3.Binary( CC.LOCAL_UPDATE_SERVICE_KEY ) ) )
            
            try:
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                domain_manager.OverwriteDefaultParsers( [
                    'nijie view popup parser',
                    'deviant art file extended_fetch parser'
                ] )
                
                #
                
                domain_manager.OverwriteDefaultURLClasses( [
                    'mega.nz file or folder',
                    'mega.nz file',
                    'mega.nz folder (alt format)',
                    'mega.nz folder'
                ] )
                
                #
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some parsers failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 485:
            
            result = self._Execute( 'SELECT service_id FROM services WHERE service_type = ?;', ( HC.COMBINED_LOCAL_MEDIA, ) ).fetchone()
            
            if result is None:
                
                warning_ptr_text = 'After looking at your database, I think this will be quick, maybe a couple minutes at most.'
                
                nums_mappings = self._STL( self._Execute( 'SELECT info FROM service_info WHERE info_type = ?;', ( HC.SERVICE_INFO_NUM_MAPPINGS, ) ) )
                
                if len( nums_mappings ) > 0:
                    
                    we_ptr = max( nums_mappings ) > 1000000000
                    
                    if we_ptr:
                        
                        result = self._Execute( 'SELECT info FROM service_info WHERE info_type = ? AND service_id = ?;', ( HC.SERVICE_INFO_NUM_FILES, self.modules_services.combined_local_file_service_id ) ).fetchone()
                        
                        if result is not None:
                            
                            ( num_files, ) = result
                            
                            warning_ptr_text = 'For most users, this update works at about 25-100k files per minute, so with {} files I expect it to take ~{} minutes for you.'.format( HydrusData.ToHumanInt( num_files ), max( 1, int( num_files / 60000 ) ) )
                            
                        else:
                            
                            we_ptr = False
                            
                        
                    
                else:
                    
                    we_ptr = False
                    
                
                message = 'Your database is going to calculate some new data so it can refer to multiple local services more efficiently. It could take a while.'
                message += os.linesep * 2
                message += warning_ptr_text
                message += os.linesep * 2
                message += 'If you do not have the time at the moment, please force kill the hydrus process now. Otherwise, continue!'
                
                BlockingSafeShowMessage( message )
                
                client_caches_path = os.path.join( self._db_dir, 'client.caches.db' )
                
                expected_space_needed = os.path.getsize( client_caches_path ) // 4
                
                try:
                    
                    HydrusDBBase.CheckHasSpaceForDBTransaction( self._db_dir, expected_space_needed )
                    
                except Exception as e:
                    
                    message = 'Hey, this update is going to expand your database cache. It requires some free space, but I think there is a problem and I am not sure it can be done safely. I recommend you kill the hydrus process now and free up some space. If you think the check is mistaken, click ok and it will try anyway. Full error:'
                    message += os.linesep * 2
                    message += str( e )
                    
                    BlockingSafeShowMessage( message )
                    
                
                self._controller.frame_splash_status.SetText( 'creating "all my files" virtual service' )
                self._controller.frame_splash_status.SetSubtext( 'gathering current file records' )
                
                self._cursor_transaction_wrapper.Commit()
                
                self._Execute( 'PRAGMA journal_mode = TRUNCATE;' )
                
                self._cursor_transaction_wrapper.BeginImmediate()
                
                dictionary = ClientServices.GenerateDefaultServiceDictionary( HC.COMBINED_LOCAL_MEDIA )
                
                self._AddService( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY, HC.COMBINED_LOCAL_MEDIA, 'all my files', dictionary )
                
                self._UnloadModules()
                
                self._LoadModules()
                
                # services module is now aware of the new guy
                
                # note we do not have to populate the mappings cache--we just have to add files naturally!
                
                # current files
                
                all_media_hash_ids = set()
                
                for service_id in self.modules_services.GetServiceIds( ( HC.LOCAL_FILE_DOMAIN, ) ):
                    
                    all_media_hash_ids.update( self.modules_files_storage.GetCurrentHashIdsList( service_id ) )
                    
                
                num_to_do = len( all_media_hash_ids )
                
                BLOCK_SIZE = 500
                
                for ( i, block_of_hash_ids ) in enumerate( HydrusData.SplitIteratorIntoChunks( all_media_hash_ids, BLOCK_SIZE ) ):
                    
                    block_of_hash_ids_to_timestamps = self.modules_files_storage.GetCurrentHashIdsToTimestamps( self.modules_services.combined_local_file_service_id, block_of_hash_ids )
                    
                    rows = list( block_of_hash_ids_to_timestamps.items() )
                    
                    self._AddFiles( self.modules_services.combined_local_media_service_id, rows )
                    
                    self._controller.frame_splash_status.SetSubtext( 'making current file records: {}'.format( HydrusData.ConvertValueRangeToPrettyString( i * BLOCK_SIZE, num_to_do ) ) )
                    
                
                # deleted files
                
                self._controller.frame_splash_status.SetSubtext( 'gathering deleted file records' )
                
                all_media_hash_ids = set()
                
                hash_ids_to_deletion_timestamps = {}
                
                for service_id in self.modules_services.GetServiceIds( ( HC.LOCAL_FILE_DOMAIN, ) ):
                    
                    deleted_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_file_service_id, HC.CONTENT_STATUS_DELETED )
                    
                    results = self._Execute( 'SELECT hash_id, timestamp FROM {};'.format( deleted_files_table_name ) ).fetchall()
                    
                    for ( hash_id, timestamp ) in results:
                        
                        all_media_hash_ids.add( hash_id )
                        
                        if timestamp is not None:
                            
                            if hash_id in hash_ids_to_deletion_timestamps:
                                
                                hash_ids_to_deletion_timestamps[ hash_id ] = max( timestamp, hash_ids_to_deletion_timestamps[ hash_id ] )
                                
                            else:
                                
                                hash_ids_to_deletion_timestamps[ hash_id ] = timestamp
                                
                            
                        
                    
                
                deleted_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_file_service_id, HC.CONTENT_STATUS_DELETED )
                
                hash_ids_to_original_timestamps = dict( self._Execute( 'SELECT hash_id, original_timestamp FROM {};'.format( deleted_files_table_name ) ) )
                
                current_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_file_service_id, HC.CONTENT_STATUS_CURRENT )
                
                hash_ids_to_original_timestamps.update( dict( self._Execute( 'SELECT hash_id, timestamp FROM {};'.format( current_files_table_name ) ) ) )
                
                deleted_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_media_service_id, HC.CONTENT_STATUS_DELETED )
                
                num_to_do = len( all_media_hash_ids )
                
                for ( i, hash_id ) in enumerate( all_media_hash_ids ):
                    
                    # no need to fake the service info number updates--that will calculate from raw on next review services open
                    
                    if hash_id not in hash_ids_to_deletion_timestamps:
                        
                        timestamp = None
                        
                    else:
                        
                        timestamp = hash_ids_to_deletion_timestamps[ hash_id ]
                        
                    
                    if hash_id not in hash_ids_to_original_timestamps:
                        
                        continue
                        
                    else:
                        
                        original_timestamp = hash_ids_to_original_timestamps[ hash_id ]
                        
                    
                    self._Execute( 'INSERT OR IGNORE INTO {} ( hash_id, timestamp, original_timestamp ) VALUES ( ?, ?, ? );'.format( deleted_files_table_name ), ( hash_id, timestamp, original_timestamp ) )
                    
                    if i % 500 == 0:
                        
                        self._controller.frame_splash_status.SetSubtext( 'making deleted file records: {}'.format( HydrusData.ConvertValueRangeToPrettyString( i, num_to_do ) ) )
                        
                    
                
                self._cursor_transaction_wrapper.Commit()
                
                self._Execute( 'PRAGMA journal_mode = {};'.format( HG.db_journal_mode ) )
                
                self._cursor_transaction_wrapper.BeginImmediate()
                
                self._controller.frame_splash_status.SetSubtext( '' )
                
            
        
        if version == 486:
            
            file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
            
            tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
            for ( file_service_id, tag_service_id ) in itertools.product( file_service_ids, tag_service_ids ):
                
                # some users still have a few of these floating around, they are not needed
                
                suffix = '{}_{}'.format( file_service_id, tag_service_id )
                
                cache_files_table_name = 'external_caches.specific_files_cache_{}'.format( suffix )
                
                result = self._Execute( 'SELECT 1 FROM external_caches.sqlite_master WHERE name = ?;', ( cache_files_table_name.split( '.', 1 )[1], ) ).fetchone()
                
                if result is None:
                    
                    continue
                    
                
                self._Execute( 'DROP TABLE {};'.format( cache_files_table_name ) )
                
            
        
        if version == 488:
            
            # clearing up some garbo 1970-01-01 timestamps that got saved
            self._Execute( 'DELETE FROM file_domain_modified_timestamps WHERE file_modified_timestamp < ?;', ( 86400 * 7, ) )
            
            #
            
            # mysterious situation where repo updates domain had some ghost files that were not in all local files!
            
            hash_ids_in_repo_updates = set( self.modules_files_storage.GetCurrentHashIdsList( self.modules_services.local_update_service_id ) )
            
            hash_ids_in_all_files = self.modules_files_storage.FilterHashIds( ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_SERVICE_KEY ), hash_ids_in_repo_updates )
            
            orphan_hash_ids = hash_ids_in_repo_updates.difference( hash_ids_in_all_files )
            
            if len( orphan_hash_ids ) > 0:
                
                hash_ids_to_timestamps = self.modules_files_storage.GetCurrentHashIdsToTimestamps( self.modules_services.local_update_service_id, orphan_hash_ids )
                
                rows = list( hash_ids_to_timestamps.items() )
                
                self.modules_files_storage.AddFiles( self.modules_services.combined_local_file_service_id, rows )
                
            
            # turns out ffmpeg was detecting some updates as mpegs, so this wasn't always working right!
            self.modules_files_maintenance_queue.AddJobs( hash_ids_in_repo_updates, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_METADATA )
            
            self._Execute( 'DELETE FROM service_info WHERE service_id = ?;', ( self.modules_services.local_update_service_id, ) )
            
        
        if version == 490:
            
            try:
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                domain_manager.OverwriteDefaultParsers( ( '4chan-style thread api parser', ) )
                
                #
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some downloader objects failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 496:
            
            try:
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                domain_manager.OverwriteDefaultParsers( ( 'hentai foundry file page parser', ) )
                
                #
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some downloader objects failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 497:
            
            try:
                
                file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES )
                
                # updating some borked enums that were overwriting tag enums
                for service_id in file_service_ids:
                    
                    self._Execute( 'UPDATE service_info SET info_type = ? WHERE service_id = ? AND info_type = ?', ( HC.SERVICE_INFO_NUM_PENDING_FILES, service_id, 15 ) )
                    self._Execute( 'UPDATE service_info SET info_type = ? WHERE service_id = ? AND info_type = ?', ( HC.SERVICE_INFO_NUM_PETITIONED_FILES, service_id, 16 ) )
                    
                
                tag_service_ids = self.modules_services.GetServiceIds( HC.ALL_TAG_SERVICES )
                
                # moving 'file count' to 'file hash count'
                for service_id in tag_service_ids:
                    
                    self._Execute( 'UPDATE service_info SET info_type = ? WHERE service_id = ? AND info_type = ?', ( HC.SERVICE_INFO_NUM_FILE_HASHES, service_id, HC.SERVICE_INFO_NUM_FILES ) )
                    
                
                rating_service_ids = self.modules_services.GetServiceIds( HC.RATINGS_SERVICES )
                
                # moving 'file count' to 'file hash count'
                for service_id in rating_service_ids:
                    
                    self._Execute( 'UPDATE service_info SET info_type = ? WHERE service_id = ? AND info_type = ?', ( HC.SERVICE_INFO_NUM_FILE_HASHES, service_id, HC.SERVICE_INFO_NUM_FILES ) )
                    
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some cached numbers failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 498:
            
            try:
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                domain_manager.RenameGUG( 'twitter syndication profile lookup (limited)', 'twitter syndication profile lookup' )
                domain_manager.RenameGUG( 'twitter syndication profile lookup (limited) (with replies)', 'twitter syndication profile lookup (with replies)' )
                
                domain_manager.OverwriteDefaultGUGs( ( 'twitter syndication list lookup', 'twitter syndication likes lookup', 'twitter syndication collection lookup' ) )
                
                domain_manager.OverwriteDefaultParsers( ( 'twitter syndication api profile parser', 'twitter syndication api tweet parser' ) )
                
                domain_manager.OverwriteDefaultURLClasses( (
                    'twitter list',
                    'twitter syndication api collection',
                    'twitter syndication api likes (user_id)',
                    'twitter syndication api likes',
                    'twitter syndication api list (list_id)',
                    'twitter syndication api list (screen_name and slug)',
                    'twitter syndication api list (user_id and slug)',
                    'twitter syndication api profile (user_id)',
                    'twitter syndication api profile',
                    'twitter syndication api tweet',
                    'twitter tweet'
                ) )
                
                #
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some downloader objects failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
            try:
                
                new_options = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS )
                
                new_options.SetInteger( 'video_buffer_size', new_options.GetInteger( 'video_buffer_size_mb' ) * 1024 * 1024 )
                
                self.modules_serialisable.SetJSONDump( new_options )
                
            except:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update the video buffer option value failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 500:
            
            try:
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                domain_manager.OverwriteDefaultURLClasses( (
                    'deviant art file page',
                ) )
                
                #
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some downloader objects failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 502:
            
            try:
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                domain_manager.OverwriteDefaultURLClasses( (
                    'deviant art embedded video player',
                ) )
                
                domain_manager.OverwriteDefaultParsers( (
                    'deviant art file page parser',
                    'deviantart backend video embed parser'
                ) )
                
                #
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some downloader objects failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 503:
            
            try:
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                # no longer supported, they nuked the open api
                
                domain_manager.DeleteGUGs( (
                    'deviant art tag search',
                ) )
                
                #
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some downloader objects failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 504:
            
            try:
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                domain_manager.OverwriteDefaultURLClasses( (
                    'furry.booru.org file page',
                    'furry.booru.org gallery page',
                    'twitter tweet',
                    'twitter syndication api tweet-result'
                ) )
                
                domain_manager.OverwriteDefaultParsers( (
                    'twitter syndication api tweet parser',
                    'gelbooru 0.1.11 file page parser'
                ) )
                
                #
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some downloader objects failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
            try:
                
                table_join = self.modules_files_storage.GetTableJoinLimitedByFileDomain( self.modules_services.combined_local_file_service_id, 'files_info', HC.CONTENT_STATUS_CURRENT )
                
                self._controller.frame_splash_status.SetSubtext( 'scheduling files for embedded metadata scan' )
                
                result = self._Execute( 'SELECT 1 FROM sqlite_master WHERE name = ?;', ( 'has_exif', ) ).fetchone()
                
                if result is None:
                    
                    self._Execute( 'CREATE TABLE IF NOT EXISTS main.has_exif ( hash_id INTEGER PRIMARY KEY );' )
                    
                    hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM {} WHERE mime IN {};'.format( table_join, HydrusData.SplayListForDB( HC.FILES_THAT_CAN_HAVE_EXIF ) ) ) )
                    
                    self.modules_files_maintenance_queue.AddJobs( hash_ids, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_HAS_EXIF )
                    
                
                result = self._Execute( 'SELECT 1 FROM sqlite_master WHERE name = ?;', ( 'has_human_readable_embedded_metadata', ) ).fetchone()
                
                if result is None:
                    
                    self._Execute( 'CREATE TABLE IF NOT EXISTS main.has_human_readable_embedded_metadata ( hash_id INTEGER PRIMARY KEY );' )
                    
                    hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM {} WHERE mime IN {};'.format( table_join, HydrusData.SplayListForDB( HC.FILES_THAT_CAN_HAVE_HUMAN_READABLE_EMBEDDED_METADATA ) ) ) )
                    
                    self.modules_files_maintenance_queue.AddJobs( hash_ids, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_HAS_HUMAN_READABLE_EMBEDDED_METADATA )
                    
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to schedule image files for embedded metadata maintenance failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 508:
            
            try:
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                domain_manager.RenameGUG( 'twitter syndication collection lookup', 'twitter collection lookup' )
                domain_manager.RenameGUG( 'twitter syndication likes lookup', 'twitter likes lookup' )
                domain_manager.RenameGUG( 'twitter syndication list lookup', 'twitter list lookup' )
                domain_manager.RenameGUG( 'twitter syndication profile lookup', 'twitter profile lookup' )
                domain_manager.RenameGUG( 'twitter syndication profile lookup (with replies)', 'twitter profile lookup (with replies)' )
                
                #
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some downloader objects failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 509:
            
            try:
                
                new_options = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS )
                
                from hydrus.client.importing.options import NoteImportOptions
                
                duplicate_content_merge_options = new_options.GetDuplicateContentMergeOptions( HC.DUPLICATE_BETTER )
                
                duplicate_content_merge_options.SetSyncNotesAction( HC.CONTENT_MERGE_ACTION_COPY )
                
                note_import_options = NoteImportOptions.NoteImportOptions()
                
                note_import_options.SetIsDefault( False )
                note_import_options.SetGetNotes( True )
                note_import_options.SetExtendExistingNoteIfPossible( True )
                note_import_options.SetConflictResolution( NoteImportOptions.NOTE_IMPORT_CONFLICT_RENAME )
                
                duplicate_content_merge_options.SetSyncNoteImportOptions( note_import_options )
                
                new_options.SetDuplicateContentMergeOptions( HC.DUPLICATE_BETTER, duplicate_content_merge_options )
                
                duplicate_content_merge_options = new_options.GetDuplicateContentMergeOptions( HC.DUPLICATE_SAME_QUALITY )
                
                duplicate_content_merge_options.SetSyncNotesAction( HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE )
                
                note_import_options = NoteImportOptions.NoteImportOptions()
                
                note_import_options.SetIsDefault( False )
                note_import_options.SetGetNotes( True )
                note_import_options.SetExtendExistingNoteIfPossible( True )
                note_import_options.SetConflictResolution( NoteImportOptions.NOTE_IMPORT_CONFLICT_RENAME )
                
                duplicate_content_merge_options.SetSyncNoteImportOptions( note_import_options )
                
                new_options.SetDuplicateContentMergeOptions( HC.DUPLICATE_SAME_QUALITY, duplicate_content_merge_options )
                
                self.modules_serialisable.SetJSONDump( new_options )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Updating your duplicate metadata merge options for the new note-merge support failed! This is not super important, but hydev would be interested in seeing the error that was printed to the log.'
                
                self.pub_initial_message( message )
                
            
        
        if version == 513:
            
            try:
                
                self._controller.frame_splash_status.SetSubtext( 'cleaning some surplus records' )
                
                # clear deletion record wasn't purging on 'all my files'
                
                all_my_deleted_hash_ids = set( self.modules_files_storage.GetDeletedHashIdsList( self.modules_services.combined_local_media_service_id ) )
                
                all_local_current_hash_ids = self.modules_files_storage.GetCurrentHashIdsList( self.modules_services.combined_local_file_service_id )
                all_local_deleted_hash_ids = self.modules_files_storage.GetDeletedHashIdsList( self.modules_services.combined_local_file_service_id )
                
                erroneous_hash_ids = all_my_deleted_hash_ids.difference( all_local_current_hash_ids ).difference( all_local_deleted_hash_ids )
                
                if len( erroneous_hash_ids ) > 0:
                    
                    service_ids_to_nums_cleared = self.modules_files_storage.ClearLocalDeleteRecord( erroneous_hash_ids )
                    
                    self._ExecuteMany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', ( ( -num_cleared, clear_service_id, HC.SERVICE_INFO_NUM_DELETED_FILES ) for ( clear_service_id, num_cleared ) in service_ids_to_nums_cleared.items() ) )
                    
                
            except:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to clean up some bad delete records failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
            try:
                
                def ask_what_to_do_twitter_stuff():
                    
                    message = 'Twitter removed their old API that we were using, breaking all the old downloaders! I am going to delete your old twitter downloaders and add a new limited one that can only get the first ~20 tweets of a profile. Make sure to check your subscriptions are linked to it, and you might want to speed up their check times! OK?'
                    
                    from hydrus.client.gui import ClientGUIDialogsQuick
                    
                    result = ClientGUIDialogsQuick.GetYesNo( None, message, title = 'Swap to new twitter downloader?', yes_label = 'do it', no_label = 'do not do it, I need to keep the old broken stuff' )
                    
                    return result == QW.QDialog.Accepted
                    
                
                do_twitter_stuff = self._controller.CallBlockingToQt( None, ask_what_to_do_twitter_stuff )
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                domain_manager.OverwriteDefaultParsers( [
                    'danbooru file page parser - get webm ugoira',
                    'deviant art file page parser',
                    'pixiv file page api parser'
                ] )
                
                if do_twitter_stuff:
                    
                    domain_manager.DeleteGUGs( [
                        'twitter collection lookup',
                        'twitter likes lookup',
                        'twitter list lookup'
                    ] )
                    
                    url_classes = domain_manager.GetURLClasses()
                    
                    deletee_url_class_names = [ url_class.GetName() for url_class in url_classes if url_class.GetName() == 'twitter list' or url_class.GetName().startswith( 'twitter syndication api' ) ]
                    
                    domain_manager.DeleteURLClasses( deletee_url_class_names )
                    
                    # we're going to leave the one spare non-overwritten parser in place
                    
                    #
                    
                    domain_manager.OverwriteDefaultGUGs( [
                        'twitter profile lookup',
                        'twitter profile lookup (with replies)'
                    ] )
                    
                    domain_manager.OverwriteDefaultURLClasses( [
                        'twitter tweet (i/web/status)',
                        'twitter tweet',
                        'twitter syndication api tweet-result',
                        'twitter syndication api timeline-profile'
                    ] )
                    
                    domain_manager.OverwriteDefaultParsers( [
                        'twitter syndication api timeline-profile parser',
                        'twitter syndication api tweet parser'
                    ] )
                    
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some downloader objects failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 514:
            
            try:
                
                new_options = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS )
                
                if not new_options.GetBoolean( 'show_related_tags' ):
                    
                    new_options.SetBoolean( 'show_related_tags', True )
                    
                    self.modules_serialisable.SetJSONDump( new_options )
                    
                    message = 'Hey, I made it so your manage tags dialog shows the updated "related tags" suggestion column (showing it is the new default). If you do not like it, turn it off again under _options->tag suggestions_, thanks!'
                    
                    self.pub_initial_message( message )
                    
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update your options to show related tags failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
            try:
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                domain_manager.OverwriteDefaultParsers( [
                    'sankaku file page parser',
                    'pixiv file page api parser'
                ] )
                
                #
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some downloader objects failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 515:
            
            try:
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                domain_manager.OverwriteDefaultParsers( [
                    'deviant art file page parser'
                ] )
                
                #
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some downloader objects failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 518:
            
            result = self._Execute( 'SELECT 1 FROM sqlite_master WHERE name = ?;', ( 'local_incdec_ratings', ) ).fetchone()
            
            if result is None:
                
                self._Execute( 'CREATE TABLE IF NOT EXISTS local_incdec_ratings ( service_id INTEGER, hash_id INTEGER, rating INTEGER, PRIMARY KEY ( service_id, hash_id ) );' )
                self._CreateIndex( 'local_incdec_ratings', [ 'hash_id' ] )
                self._CreateIndex( 'local_incdec_ratings', [ 'rating' ] )
                
            
        
        if version == 519:
            
            try:
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                domain_manager.OverwriteDefaultParsers( [
                    'deviant art file page parser'
                ] )
                
                domain_manager.OverwriteDefaultURLClasses( [
                    'deviant art file (login-only redirect)',
                    'deviant art file (original quality) (alt)',
                    'deviant art file (original quality)',
                    'deviant art resized file (low quality)',
                    'deviant art resized file (medium quality)'
                ] )
                
                #
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some downloader objects failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        if version == 520:
            
            try:
                
                domain_manager = self.modules_serialisable.GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
                
                domain_manager.Initialise()
                
                #
                
                domain_manager.OverwriteDefaultParsers( [
                    'pixiv file page api parser'
                ] )
                
                #
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
                #
                
                self.modules_serialisable.SetJSONDump( domain_manager )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                message = 'Trying to update some downloader objects failed! Please let hydrus dev know!'
                
                self.pub_initial_message( message )
                
            
        
        self._controller.frame_splash_status.SetTitleText( 'updated db to v{}'.format( HydrusData.ToHumanInt( version + 1 ) ) )
        
        self._Execute( 'UPDATE version SET version = ?;', ( version + 1, ) )
        
    
    def _UpdateMappings( self, tag_service_id, mappings_ids = None, deleted_mappings_ids = None, pending_mappings_ids = None, pending_rescinded_mappings_ids = None, petitioned_mappings_ids = None, petitioned_rescinded_mappings_ids = None ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( tag_service_id )
        
        if mappings_ids is None: mappings_ids = []
        if deleted_mappings_ids is None: deleted_mappings_ids = []
        if pending_mappings_ids is None: pending_mappings_ids = []
        if pending_rescinded_mappings_ids is None: pending_rescinded_mappings_ids = []
        if petitioned_mappings_ids is None: petitioned_mappings_ids = []
        if petitioned_rescinded_mappings_ids is None: petitioned_rescinded_mappings_ids = []
        
        mappings_ids = self.modules_mappings_storage.FilterExistingUpdateMappings( tag_service_id, mappings_ids, HC.CONTENT_UPDATE_ADD )
        deleted_mappings_ids = self.modules_mappings_storage.FilterExistingUpdateMappings( tag_service_id, deleted_mappings_ids, HC.CONTENT_UPDATE_DELETE )
        pending_mappings_ids = self.modules_mappings_storage.FilterExistingUpdateMappings( tag_service_id, pending_mappings_ids, HC.CONTENT_UPDATE_PEND )
        pending_rescinded_mappings_ids = self.modules_mappings_storage.FilterExistingUpdateMappings( tag_service_id, pending_rescinded_mappings_ids, HC.CONTENT_UPDATE_RESCIND_PEND )
        petitioned_mappings_ids = self.modules_mappings_storage.FilterExistingUpdateMappings( tag_service_id, petitioned_mappings_ids, HC.CONTENT_UPDATE_PETITION )
        petitioned_rescinded_mappings_ids = self.modules_mappings_storage.FilterExistingUpdateMappings( tag_service_id, petitioned_rescinded_mappings_ids, HC.CONTENT_UPDATE_RESCIND_PETITION )
        
        tag_ids_to_filter_chained = { tag_id for ( tag_id, hash_ids ) in itertools.chain.from_iterable( ( mappings_ids, deleted_mappings_ids, pending_mappings_ids, pending_rescinded_mappings_ids ) ) }
        
        chained_tag_ids = self.modules_tag_display.FilterChained( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, tag_ids_to_filter_chained )
        
        file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
        
        change_in_num_mappings = 0
        change_in_num_deleted_mappings = 0
        change_in_num_pending_mappings = 0
        change_in_num_petitioned_mappings = 0
        change_in_num_files = 0
        
        hash_ids_lists = ( hash_ids for ( tag_id, hash_ids ) in itertools.chain.from_iterable( ( mappings_ids, pending_mappings_ids ) ) )
        hash_ids_being_added = { hash_id for hash_id in itertools.chain.from_iterable( hash_ids_lists ) }
        
        hash_ids_lists = ( hash_ids for ( tag_id, hash_ids ) in itertools.chain.from_iterable( ( deleted_mappings_ids, pending_rescinded_mappings_ids ) ) )
        hash_ids_being_removed = { hash_id for hash_id in itertools.chain.from_iterable( hash_ids_lists ) }
        
        hash_ids_being_altered = hash_ids_being_added.union( hash_ids_being_removed )
        
        filtered_hashes_generator = self.modules_mappings_cache_specific_storage.GetFilteredHashesGenerator( file_service_ids, tag_service_id, hash_ids_being_altered )
        
        self._Execute( 'CREATE TABLE IF NOT EXISTS mem.temp_hash_ids ( hash_id INTEGER );' )
        
        self._ExecuteMany( 'INSERT INTO temp_hash_ids ( hash_id ) VALUES ( ? );', ( ( hash_id, ) for hash_id in hash_ids_being_altered ) )
        
        pre_existing_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM temp_hash_ids WHERE EXISTS ( SELECT 1 FROM {} WHERE hash_id = temp_hash_ids.hash_id );'.format( current_mappings_table_name ) ) )
        
        num_files_added = len( hash_ids_being_added.difference( pre_existing_hash_ids ) )
        
        change_in_num_files += num_files_added
        
        # BIG NOTE:
        # after testing some situations, it makes nicest logical sense to interleave all cache updates into the loops
        # otherwise, when there are conflicts due to sheer duplication or the display system applying two tags at once with the same implications, we end up relying on an out-of-date/unsynced (in cache terms) specific cache for combined etc...
        # I now extend this to counts, argh. this is not great in overhead terms, but many optimisations rely on a/c counts now, and the fallback is the combined storage ac count cache
        
        if len( mappings_ids ) > 0:
            
            for ( tag_id, hash_ids ) in mappings_ids:
                
                if tag_id in chained_tag_ids:
                    
                    self.modules_mappings_cache_combined_files_display.AddMappingsForChained( tag_service_id, tag_id, hash_ids )
                    
                
                self._ExecuteMany( 'DELETE FROM ' + deleted_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_deleted_deleted = self._GetRowCount()
                
                self._ExecuteMany( 'DELETE FROM ' + pending_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_pending_deleted = self._GetRowCount()
                
                self._ExecuteMany( 'INSERT OR IGNORE INTO ' + current_mappings_table_name + ' VALUES ( ?, ? );', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_current_inserted = self._GetRowCount()
                
                change_in_num_deleted_mappings -= num_deleted_deleted
                change_in_num_pending_mappings -= num_pending_deleted
                change_in_num_mappings += num_current_inserted
                
                self.modules_mappings_counts_update.UpdateCounts( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, num_current_inserted, - num_pending_deleted ) ] )
                
                if tag_id not in chained_tag_ids:
                    
                    self.modules_mappings_counts_update.UpdateCounts( ClientTags.TAG_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, num_current_inserted, - num_pending_deleted ) ] )
                    
                
                self.modules_mappings_cache_specific_storage.AddMappings( tag_service_id, tag_id, hash_ids, filtered_hashes_generator )
                
            
        
        if len( deleted_mappings_ids ) > 0:
            
            for ( tag_id, hash_ids ) in deleted_mappings_ids:
                
                if tag_id in chained_tag_ids:
                    
                    self.modules_mappings_cache_combined_files_display.DeleteMappingsForChained( tag_service_id, tag_id, hash_ids )
                    
                
                self._ExecuteMany( 'DELETE FROM ' + current_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_current_deleted = self._GetRowCount()
                
                self._ExecuteMany( 'DELETE FROM ' + petitioned_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_petitions_deleted = self._GetRowCount()
                
                self._ExecuteMany( 'INSERT OR IGNORE INTO ' + deleted_mappings_table_name + ' VALUES ( ?, ? );', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_deleted_inserted = self._GetRowCount()
                
                change_in_num_mappings -= num_current_deleted
                change_in_num_petitioned_mappings -= num_petitions_deleted
                change_in_num_deleted_mappings += num_deleted_inserted
                
                self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, num_current_deleted, 0 ) ] )
                
                if tag_id not in chained_tag_ids:
                    
                    self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, num_current_deleted, 0 ) ] )
                    
                
                self.modules_mappings_cache_specific_storage.DeleteMappings( tag_service_id, tag_id, hash_ids, filtered_hashes_generator )
                
            
        
        if len( pending_mappings_ids ) > 0:
            
            for ( tag_id, hash_ids ) in pending_mappings_ids:
                
                if tag_id in chained_tag_ids:
                    
                    self.modules_mappings_cache_combined_files_display.PendMappingsForChained( tag_service_id, tag_id, hash_ids )
                    
                
                self._ExecuteMany( 'INSERT OR IGNORE INTO ' + pending_mappings_table_name + ' VALUES ( ?, ? );', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_pending_inserted = self._GetRowCount()
                
                change_in_num_pending_mappings += num_pending_inserted
                
                self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, 0, num_pending_inserted ) ] )
                
                if tag_id not in chained_tag_ids:
                    
                    self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, 0, num_pending_inserted ) ] )
                    
                
                self.modules_mappings_cache_specific_storage.PendMappings( tag_service_id, tag_id, hash_ids, filtered_hashes_generator )
                
            
        
        if len( pending_rescinded_mappings_ids ) > 0:
            
            for ( tag_id, hash_ids ) in pending_rescinded_mappings_ids:
                
                if tag_id in chained_tag_ids:
                    
                    self.modules_mappings_cache_combined_files_display.RescindPendingMappingsForChained( tag_service_id, tag_id, hash_ids )
                    
                
                self._ExecuteMany( 'DELETE FROM ' + pending_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_pending_deleted = self._GetRowCount()
                
                change_in_num_pending_mappings -= num_pending_deleted
                
                self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, 0, num_pending_deleted ) ] )
                
                if tag_id not in chained_tag_ids:
                    
                    self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, 0, num_pending_deleted ) ] )
                    
                
                self.modules_mappings_cache_specific_storage.RescindPendingMappings( tag_service_id, tag_id, hash_ids, filtered_hashes_generator )
                
            
        
        #
        
        post_existing_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM temp_hash_ids WHERE EXISTS ( SELECT 1 FROM {} WHERE hash_id = temp_hash_ids.hash_id );'.format( current_mappings_table_name ) ) )
        
        self._Execute( 'DROP TABLE temp_hash_ids;' )
        
        num_files_removed = len( pre_existing_hash_ids.intersection( hash_ids_being_removed ).difference( post_existing_hash_ids ) )
        
        change_in_num_files -= num_files_removed
        
        for ( tag_id, hash_ids, reason_id ) in petitioned_mappings_ids:
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO ' + petitioned_mappings_table_name + ' VALUES ( ?, ?, ? );', [ ( tag_id, hash_id, reason_id ) for hash_id in hash_ids ] )
            
            num_petitions_inserted = self._GetRowCount()
            
            change_in_num_petitioned_mappings += num_petitions_inserted
            
        
        for ( tag_id, hash_ids ) in petitioned_rescinded_mappings_ids:
            
            self._ExecuteMany( 'DELETE FROM ' + petitioned_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
            
            num_petitions_deleted = self._GetRowCount()
            
            change_in_num_petitioned_mappings -= num_petitions_deleted
            
        
        service_info_updates = []
        
        if change_in_num_mappings != 0: service_info_updates.append( ( change_in_num_mappings, tag_service_id, HC.SERVICE_INFO_NUM_MAPPINGS ) )
        if change_in_num_deleted_mappings != 0: service_info_updates.append( ( change_in_num_deleted_mappings, tag_service_id, HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ) )
        if change_in_num_pending_mappings != 0: service_info_updates.append( ( change_in_num_pending_mappings, tag_service_id, HC.SERVICE_INFO_NUM_PENDING_MAPPINGS ) )
        if change_in_num_petitioned_mappings != 0: service_info_updates.append( ( change_in_num_petitioned_mappings, tag_service_id, HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS ) )
        if change_in_num_files != 0: service_info_updates.append( ( change_in_num_files, tag_service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
        
        if len( service_info_updates ) > 0: self._ExecuteMany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', service_info_updates )
        
    
    def _UpdateServerServices( self, admin_service_key, serverside_services, service_keys_to_access_keys, deletee_service_keys ):
        
        admin_service_id = self.modules_services.GetServiceId( admin_service_key )
        
        admin_service = self.modules_services.GetService( admin_service_id )
        
        admin_credentials = admin_service.GetCredentials()
        
        ( host, admin_port ) = admin_credentials.GetAddress()
        
        #
        
        current_service_keys = self.modules_services.GetServiceKeys()
        
        for serverside_service in serverside_services:
            
            service_key = serverside_service.GetServiceKey()
            
            if service_key in current_service_keys:
                
                service_id = self.modules_services.GetServiceId( service_key )
                
                service = self.modules_services.GetService( service_id )
                
                credentials = service.GetCredentials()
                
                upnp_port = serverside_service.GetUPnPPort()
                
                if upnp_port is None:
                    
                    port = serverside_service.GetPort()
                    
                    credentials.SetAddress( host, port )
                    
                else:
                    
                    credentials.SetAddress( host, upnp_port )
                    
                
                service.SetCredentials( credentials )
                
                self.modules_services.UpdateService( service )
                
            else:
                
                if service_key in service_keys_to_access_keys:
                    
                    service_type = serverside_service.GetServiceType()
                    name = serverside_service.GetName()
                    
                    service = ClientServices.GenerateService( service_key, service_type, name )
                    
                    access_key = service_keys_to_access_keys[ service_key ]
                    
                    credentials = service.GetCredentials()
                    
                    upnp_port = serverside_service.GetUPnPPort()
                    
                    if upnp_port is None:
                        
                        port = serverside_service.GetPort()
                        
                        credentials.SetAddress( host, port )
                        
                    else:
                        
                        credentials.SetAddress( host, upnp_port )
                        
                    
                    credentials.SetAccessKey( access_key )
                    
                    service.SetCredentials( credentials )
                    
                    ( service_key, service_type, name, dictionary ) = service.ToTuple()
                    
                    self._AddService( service_key, service_type, name, dictionary )
                    
                
            
        
        for service_key in deletee_service_keys:
            
            try:
                
                self.modules_services.GetServiceId( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            self._DeleteService( service_id )
            
        
        self._cursor_transaction_wrapper.pub_after_job( 'notify_account_sync_due' )
        self._cursor_transaction_wrapper.pub_after_job( 'notify_new_services_data' )
        self._cursor_transaction_wrapper.pub_after_job( 'notify_new_services_gui' )
        self._cursor_transaction_wrapper.pub_after_job( 'notify_new_pending' )
        
    
    def _UpdateServices( self, services ):
        
        current_service_keys = self.modules_services.GetServiceKeys()
        
        future_service_keys = { service.GetServiceKey() for service in services }
        
        for service_key in current_service_keys:
            
            if service_key not in future_service_keys:
                
                service_id = self.modules_services.GetServiceId( service_key )
                
                self._DeleteService( service_id )
                
            
        
        for service in services:
            
            service_key = service.GetServiceKey()
            
            if service_key in current_service_keys:
                
                self.modules_services.UpdateService( service )
                
            else:
                
                ( service_key, service_type, name, dictionary ) = service.ToTuple()
                
                self._AddService( service_key, service_type, name, dictionary )
                
            
        
        self._cursor_transaction_wrapper.pub_after_job( 'notify_account_sync_due' )
        self._cursor_transaction_wrapper.pub_after_job( 'notify_new_services_data' )
        self._cursor_transaction_wrapper.pub_after_job( 'notify_new_services_gui' )
        self._cursor_transaction_wrapper.pub_after_job( 'notify_new_pending' )
        
    
    def _Vacuum( self, names: typing.Collection[ str ], maintenance_mode = HC.MAINTENANCE_FORCED, stop_time = None, force_vacuum = False ):
        
        ok_names = []
        
        for name in names:
            
            db_path = os.path.join( self._db_dir, self._db_filenames[ name ] )
            
            try:
                
                HydrusDB.CheckCanVacuumCursor( db_path, self._c )
                
            except Exception as e:
                
                if not self._have_printed_a_cannot_vacuum_message:
                    
                    HydrusData.Print( 'Cannot vacuum "{}": {}'.format( db_path, e ) )
                    
                    self._have_printed_a_cannot_vacuum_message = True
                    
                
                continue
                
            
            if self._controller.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ):
                
                return
                
            
            ok_names.append( name )
            
        
        if len( ok_names ) == 0:
            
            HydrusData.ShowText( 'A call to vacuum was made, but none of those databases could be vacuumed! Maybe drive free space is tight and/or recently changed?' )
            
            return
            
        
        job_key_pubbed = False
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetStatusTitle( 'database maintenance - vacuum' )
        
        self._CloseDBConnection()
        
        try:
            
            for name in ok_names:
                
                time.sleep( 1 )
                
                try:
                    
                    db_path = os.path.join( self._db_dir, self._db_filenames[ name ] )
                    
                    if not job_key_pubbed:
                        
                        self._controller.pub( 'modal_message', job_key )
                        
                        job_key_pubbed = True
                        
                    
                    self._controller.frame_splash_status.SetText( 'vacuuming ' + name )
                    job_key.SetStatusText( 'vacuuming ' + name )
                    
                    started = HydrusData.GetNowPrecise()
                    
                    HydrusDB.VacuumDB( db_path )
                    
                    time_took = HydrusData.GetNowPrecise() - started
                    
                    HydrusData.Print( 'Vacuumed ' + db_path + ' in ' + HydrusData.TimeDeltaToPrettyTimeDelta( time_took ) )
                    
                except Exception as e:
                    
                    HydrusData.Print( 'vacuum failed:' )
                    
                    HydrusData.ShowException( e )
                    
                    text = 'An attempt to vacuum the database failed.'
                    text += os.linesep * 2
                    text += 'If the error is not obvious, please contact the hydrus developer.'
                    
                    HydrusData.ShowText( text )
                    
                    self._InitDBConnection()
                    
                    return
                    
                
            
            job_key.SetStatusText( 'cleaning up' )
            
        finally:
            
            self._InitDBConnection()
            
            self.modules_db_maintenance.RegisterSuccessfulVacuum( name )
            
            job_key.SetStatusText( 'done!' )
            
            job_key.Finish()
            
            job_key.Delete( 10 )
            
        
    
    def _Write( self, action, *args, **kwargs ):
        
        result = None
        
        if action == 'analyze': self.modules_db_maintenance.AnalyzeDueTables( *args, **kwargs )
        elif action == 'associate_repository_update_hashes': self.modules_repositories.AssociateRepositoryUpdateHashes( *args, **kwargs )
        elif action == 'backup': self._Backup( *args, **kwargs )
        elif action == 'clear_deferred_physical_delete': self.modules_files_storage.ClearDeferredPhysicalDelete( *args, **kwargs )
        elif action == 'clear_false_positive_relations': self.modules_files_duplicates.ClearAllFalsePositiveRelationsFromHashes( *args, **kwargs )
        elif action == 'clear_false_positive_relations_between_groups': self.modules_files_duplicates.ClearFalsePositiveRelationsBetweenGroupsFromHashes( *args, **kwargs )
        elif action == 'clear_orphan_file_records': self._ClearOrphanFileRecords( *args, **kwargs )
        elif action == 'clear_orphan_tables': self._ClearOrphanTables( *args, **kwargs )
        elif action == 'content_updates': self._ProcessContentUpdates( *args, **kwargs )
        elif action == 'cull_file_viewing_statistics': self.modules_files_viewing_stats.CullFileViewingStatistics( *args, **kwargs )
        elif action == 'db_integrity': self._CheckDBIntegrity( *args, **kwargs )
        elif action == 'delete_imageboard': self.modules_serialisable.DeleteYAMLDump( ClientDBSerialisable.YAML_DUMP_ID_IMAGEBOARD, *args, **kwargs )
        elif action == 'delete_local_booru_share': self.modules_serialisable.DeleteYAMLDump( ClientDBSerialisable.YAML_DUMP_ID_LOCAL_BOORU, *args, **kwargs )
        elif action == 'delete_pending': self._DeletePending( *args, **kwargs )
        elif action == 'delete_serialisable_named': self.modules_serialisable.DeleteJSONDumpNamed( *args, **kwargs )
        elif action == 'delete_service_info': self._DeleteServiceInfo( *args, **kwargs )
        elif action == 'delete_potential_duplicate_pairs': self.modules_files_duplicates.DeleteAllPotentialDuplicatePairs( *args, **kwargs )
        elif action == 'dirty_services': self._SaveDirtyServices( *args, **kwargs )
        elif action == 'dissolve_alternates_group': self.modules_files_duplicates.DissolveAlternatesGroupIdFromHashes( *args, **kwargs )
        elif action == 'dissolve_duplicates_group': self.modules_files_duplicates.DissolveMediaIdFromHashes( *args, **kwargs )
        elif action == 'duplicate_pair_status': self._DuplicatesSetDuplicatePairStatus( *args, **kwargs )
        elif action == 'duplicate_set_king': self.modules_files_duplicates.SetKingFromHash( *args, **kwargs )
        elif action == 'file_maintenance_add_jobs': self.modules_files_maintenance_queue.AddJobs( *args, **kwargs )
        elif action == 'file_maintenance_add_jobs_hashes': self.modules_files_maintenance_queue.AddJobsHashes( *args, **kwargs )
        elif action == 'file_maintenance_cancel_jobs': self.modules_files_maintenance_queue.CancelJobs( *args, **kwargs )
        elif action == 'file_maintenance_clear_jobs': self.modules_files_maintenance.ClearJobs( *args, **kwargs )
        elif action == 'fix_logically_inconsistent_mappings': self._FixLogicallyInconsistentMappings( *args, **kwargs )
        elif action == 'ideal_client_files_locations': self.modules_files_physical_storage.SetIdealClientFilesLocations( *args, **kwargs )
        elif action == 'import_file': result = self._ImportFile( *args, **kwargs )
        elif action == 'import_update': self._ImportUpdate( *args, **kwargs )
        elif action == 'local_booru_share': self.modules_serialisable.SetYAMLDump( ClientDBSerialisable.YAML_DUMP_ID_LOCAL_BOORU, *args, **kwargs )
        elif action == 'maintain_hashed_serialisables': result = self.modules_serialisable.MaintainHashedStorage( *args, **kwargs )
        elif action == 'maintain_similar_files_search_for_potential_duplicates': result = self._PerceptualHashesSearchForPotentialDuplicates( *args, **kwargs )
        elif action == 'maintain_similar_files_tree': self.modules_similar_files.MaintainTree( *args, **kwargs )
        elif action == 'migration_clear_job': self._MigrationClearJob( *args, **kwargs )
        elif action == 'migration_start_mappings_job': self._MigrationStartMappingsJob( *args, **kwargs )
        elif action == 'migration_start_pairs_job': self._MigrationStartPairsJob( *args, **kwargs )
        elif action == 'process_repository_content': result = self._ProcessRepositoryContent( *args, **kwargs )
        elif action == 'process_repository_definitions': result = self.modules_repositories.ProcessRepositoryDefinitions( *args, **kwargs )
        elif action == 'push_recent_tags': self._PushRecentTags( *args, **kwargs )
        elif action == 'regenerate_local_hash_cache': self._RegenerateLocalHashCache( *args, **kwargs )
        elif action == 'regenerate_local_tag_cache': self._RegenerateLocalTagCache( *args, **kwargs )
        elif action == 'regenerate_similar_files': self.modules_similar_files.RegenerateTree( *args, **kwargs )
        elif action == 'regenerate_searchable_subtag_maps': self._RegenerateTagCacheSearchableSubtagMaps( *args, **kwargs )
        elif action == 'regenerate_tag_cache': self._RegenerateTagCache( *args, **kwargs )
        elif action == 'regenerate_tag_display_mappings_cache': self._RegenerateTagDisplayMappingsCache( *args, **kwargs )
        elif action == 'regenerate_tag_display_pending_mappings_cache': self._RegenerateTagDisplayPendingMappingsCache( *args, **kwargs )
        elif action == 'regenerate_tag_mappings_cache': self._RegenerateTagMappingsCache( *args, **kwargs )
        elif action == 'regenerate_tag_parents_cache': self._RegenerateTagParentsCache( *args, **kwargs )
        elif action == 'regenerate_tag_pending_mappings_cache': self._RegenerateTagPendingMappingsCache( *args, **kwargs )
        elif action == 'regenerate_tag_siblings_and_parents_cache': self.modules_tag_display.RegenerateTagSiblingsAndParentsCache( *args, **kwargs )
        elif action == 'register_shutdown_work': self.modules_db_maintenance.RegisterShutdownWork( *args, **kwargs )
        elif action == 'repopulate_mappings_from_cache': self._RepopulateMappingsFromCache( *args, **kwargs )
        elif action == 'repopulate_tag_cache_missing_subtags': self._RepopulateTagCacheMissingSubtags( *args, **kwargs )
        elif action == 'repopulate_tag_display_mappings_cache': self._RepopulateTagDisplayMappingsCache( *args, **kwargs )
        elif action == 'relocate_client_files': self.modules_files_physical_storage.RelocateClientFiles( *args, **kwargs )
        elif action == 'remove_alternates_member': self.modules_files_duplicates.RemoveAlternateMemberFromHashes( *args, **kwargs )
        elif action == 'remove_duplicates_member': self.modules_files_duplicates.RemoveMediaIdMemberFromHashes( *args, **kwargs )
        elif action == 'remove_potential_pairs': self.modules_files_duplicates.RemovePotentialPairsFromHashes( *args, **kwargs )
        elif action == 'repair_client_files': self.modules_files_physical_storage.RepairClientFiles( *args, **kwargs )
        elif action == 'repair_invalid_tags': self._RepairInvalidTags( *args, **kwargs )
        elif action == 'reprocess_repository': self.modules_repositories.ReprocessRepository( *args, **kwargs )
        elif action == 'reset_repository': self._ResetRepository( *args, **kwargs )
        elif action == 'reset_repository_processing': self._ResetRepositoryProcessing( *args, **kwargs )
        elif action == 'reset_potential_search_status': self._PerceptualHashesResetSearchFromHashes( *args, **kwargs )
        elif action == 'resync_tag_mappings_cache_files': self._ResyncTagMappingsCacheFiles( *args, **kwargs )
        elif action == 'save_options': self._SaveOptions( *args, **kwargs )
        elif action == 'serialisable': self.modules_serialisable.SetJSONDump( *args, **kwargs )
        elif action == 'serialisable_atomic': self.modules_serialisable.SetJSONComplex( *args, **kwargs )
        elif action == 'serialisable_simple': self.modules_serialisable.SetJSONSimple( *args, **kwargs )
        elif action == 'serialisables_overwrite': self.modules_serialisable.OverwriteJSONDumps( *args, **kwargs )
        elif action == 'set_password': self._SetPassword( *args, **kwargs )
        elif action == 'set_repository_update_hashes': self.modules_repositories.SetRepositoryUpdateHashes( *args, **kwargs )
        elif action == 'schedule_repository_update_file_maintenance': self.modules_repositories.ScheduleRepositoryUpdateFileMaintenance( *args, **kwargs )
        elif action == 'sync_tag_display_maintenance': result = self._CacheTagDisplaySync( *args, **kwargs )
        elif action == 'tag_display_application': self.modules_tag_display.SetApplication( *args, **kwargs )
        elif action == 'update_server_services': self._UpdateServerServices( *args, **kwargs )
        elif action == 'update_services': self._UpdateServices( *args, **kwargs )
        elif action == 'vacuum': self._Vacuum( *args, **kwargs )
        else: raise Exception( 'db received an unknown write command: ' + action )
        
        return result
        
    
    def pub_content_updates_after_commit( self, service_keys_to_content_updates ):
        
        self._after_job_content_update_jobs.append( service_keys_to_content_updates )
        
    
    def pub_initial_message( self, message ):
        
        self._initial_messages.append( message )
        
    
    def pub_service_updates_after_commit( self, service_keys_to_service_updates ):
        
        self._cursor_transaction_wrapper.pub_after_job( 'service_updates_data', service_keys_to_service_updates )
        self._cursor_transaction_wrapper.pub_after_job( 'service_updates_gui', service_keys_to_service_updates )
        
    
    def publish_status_update( self ):
        
        self._controller.pub( 'set_status_bar_dirty' )
        
    
    def GetInitialMessages( self ):
        
        return self._initial_messages
        
    
    def RestoreBackup( self, path ):
        
        for filename in self._db_filenames.values():
            
            HG.client_controller.frame_splash_status.SetText( filename )
            
            source = os.path.join( path, filename )
            dest = os.path.join( self._db_dir, filename )
            
            if os.path.exists( source ):
                
                HydrusPaths.MirrorFile( source, dest )
                
            else:
                
                # if someone backs up with an older version that does not have as many db files as this version, we get conflict
                # don't want to delete just in case, but we will move it out the way
                
                HydrusPaths.MergeFile( dest, dest + '.old' )
                
            
        
        additional_filenames = self._GetPossibleAdditionalDBFilenames()
        
        for additional_filename in additional_filenames:
            
            source = os.path.join( path, additional_filename )
            dest = os.path.join( self._db_dir, additional_filename )
            
            if os.path.exists( source ):
                
                HydrusPaths.MirrorFile( source, dest )
                
            
        
        HG.client_controller.frame_splash_status.SetText( 'media files' )
        
        client_files_source = os.path.join( path, 'client_files' )
        client_files_default = os.path.join( self._db_dir, 'client_files' )
        
        if os.path.exists( client_files_source ):
            
            HydrusPaths.MirrorTree( client_files_source, client_files_default )
            
        
    
