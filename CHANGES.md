### 1.0.53

* temporary removal of timeouts in POST requests

### 1.0.52

* Better coordinate handling and transforming

### 1.0.51

* Fixed bug in query parameters NED cone search

### 1.0.50

* Improved log messages for exceptions/errors
* Check SIMBAD identifiers supplied for validity

### 1.0.49
 
* Updated adsmutils requirement

### 1.0.48
 
* Enabled JSON stdout logging and HTTP connection pool

### 1.0.47

* bugfix: Github issue 78 (trailing spaces in object names)

### 1.0.46

* bugfix in returned data processing

### 1.0.45

* Update of HTTP status codes for nedsrv errors

### 1.0.44

* For cone search, limit the potential number of objects returned

### 1.0.43

* Unittest coverage improvement
* Cone search support

### 1.0.42

* Maintenance release (bug in error message)

### 1.0.41

* Maintenance release (improved unittest coverage)

### 1.0.40

* Some minor bug fixes to deal with pathological erroneous queries

### 1.0.39

* Implementation of new query parsing method using the luqum (LUcene QUery Manipolator) module
  * luqum credentials: developed by Jurismarchés (https://github.com/jurismarches/luqum)
  * License: GNU General Public License v3.0
  * the module has been adapted to be compatible with Python 2.7
* The luqum module is used to create a query tree from the Solr query string to identify the object: modifiers
* This fixes the bug that e.g. "object:Andromeda OR abs:Andromeda" gets translated into "simbid:123 OR 0:123"
* Enhancement: an object: query is now translated into an OR of simbid:, nedid: and abs: queries, with
  database:astronomy as restriction

### 1.0.38

* Fix of incorrect urls in log messages

### 1.0.37

* Nedsrv endpoint: provide info when 500 is thrown

### 1.0.36

* Unittest coverage improvement and code cleanup

### 1.0.35

* Integration of NED into object search

### 1.0.34

* Bugfix for nedsrv endpoint

### 1.0.33

* Endpoint 'classic' renamed to 'nedsrv'

### 1.0.32

* Fix of mime-type for ASCII output. Add filtering by month.

### 1.0.31

* additional output format and filters for "Classic" endpoint

### 1.0.30

* remove dependency on astroquery

### 1.0.29

* endpoint to support ADS Classic NED query

### 1.0.28

* update of query sent to SIMBAD TAP (no uppercasing)

### 1.0.27

* specify version for adsmutils in requirements.txt

### 1.0.26

* Special User Agent string for external requests

### 1.0.25

* No more local caching 

### 1.0.24

* More code cleanup

### 1.0.23

* Code cleanup and waffle implementation

### 1.0.22

* Undo the replacement of spaces with underscores in identifiers

### 1.0.21

* App instantiation through ADSFlask (ADSMicroserviceUtils)

### 1.0.20

* Unittesting using py.test
* Renamed app directory from 'service' to 'object_service'
* Separate dev-requirements.txt
* Removed unused client.py
* Code cleanup

### 1.0.19

* Implementation of data retrieval to support NED facet

### 1.0.18

* Update requirements.txt (versioning) + cleanup

### 1.0.17

* fix of Github issue 38: catch ReadTimeout exceptions

### 1.0.16

* logging of URL TAP service used

### 1.0.15

* more detailed logging

### 1.0.14

* timeout exception implemented for SIMBAD requests

### 1.0.13

* small update

### 1.0.12

* Update of logfile name, making use of ENVIRONMENT variable

### 1.0.11

* Fixed bug Github29 (allowing for more complex nested operator queries)

### 1.0.10

* Fixed bug Github27

### 1.0.9

* Fixed bug Github24

### 1.0.8

* deal with format of BBB requests in case of query input

### 1.0.7

* cleanup and allow query as input

### 1.0.6

* for identifier query, output dictionary has identifiers as keys

### 1.0.5

* process top level facets properly

### 1.0.4

* addition of facets as allowed input type (Github 15)

### 1.0.3

* bug fix (Github issue 10) and cleanup of SIMBAD module

### 1.0.2

* refactor of SIMBAD object search to facilitate integration in front-end

### 1.0.1

* unittests for SIMBAD services

### 1.0.0

* initial version
* only support for SIMBAD object queries
