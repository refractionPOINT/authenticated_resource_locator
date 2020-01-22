import gevent
import gevent.pool

import base64
import json
import tempfile
import requests
from requests.auth import HTTPBasicAuth
import tarfile
import zipfile
import google.cloud.storage
from google.oauth2 import service_account

class AuthenticatedResourceLocator( object ):
    _supportedMethods = {
        'http' : set( (
            'basic',
            'bearer',
            'token',
            'otx',
        ) ),
        'https' : set( (
            'basic',
            'bearer',
            'token',
            'otx',
        ) ),
        'gcs' : set( (
            'gaia',
        ) ),
        'github' : set( (
            'token',
        ) ),
    }

    def __init__( self, arlString, maxSize = None, maxConcurrent = 5 ):
        self._arlString = arlString
        self._maxSize = maxSize
        self._maxConcurrent = maxConcurrent

        self._methodCallbacks = {
            'http' : self._doHttp,
            'https' : self._doHttp,
            'gcs' : self._doGcs,
            'github' : self._doGithub,
        }

        self._methodName = None
        self._methodDest = None
        self._authType = None
        self._authData = None

        # This is a shortcut for backwards compatibility.
        if self._arlString.startswith( 'https://' ):
            self._methodName = 'https'
            self._methodDest = self._arlString
        else:
            # Proper parsing of the format.
            if not self._arlString.startswith( '[' ) and self._arlString.endswith( ']' ):
                raise SyntaxError( "Invalid ARL string, must start with https:// or be a valid [ARL].")
            info = [ x.strip() for x in self._arlString[ 1 : -1 ].split( ',' ) ]
            if len( info ) != 4 and len( info ) != 2:
                raise SyntaxError( "Invalid number of components in ARL, should be 2 or 4." )
            self._methodName = info[ 0 ].lower()
            self._methodDest = info[ 1 ]
            if 4 == len( info ):
                self._authType = info[ 2 ].lower()
                self._authData = info[ 3 ]

        if self._methodName not in self._supportedMethods:
            raise NotImplementedError( "Method %s not supported." % ( self._methodName, ) )

        if self._authType is not None and self._authType not in self._supportedMethods[ self._methodName ]:
            raise NotImplementedError( "Auth type not supported: %s." % ( self._authType, ) )

    def __iter__( self ):
        return self._methodCallbacks[ self._methodName ]()

    def _getTempFile( self ):
        # The temp files get deleted on close (or GC).
        return tempfile.NamedTemporaryFile( mode = 'r+b' )

    def _parallelExec( self, f, objects, timeout = None, maxConcurrent = None ):
        def _retExecOrExc( f, o, timeout ):
            try:
                if timeout is None:
                    return f( o )
                else:
                    with gevent.Timeout( timeout ):
                        return f( o )
            except ( Exception, gevent.Timeout ) as e:
                return e

        g = gevent.pool.Pool( size = maxConcurrent )
        return g.imap_unordered( lambda o: _retExecOrExc( f, o, timeout ), objects )

    def __enter__( self ):
        return self

    def __exit__( self, type, value, traceback ):
        return

    def _doHttp( self ):
        fullUrl = self._methodDest
        if 'http' == self._methodName and not fullUrl.startswith( "http://" ):
            fullUrl = "http://%s" % ( fullUrl, )
        if 'https' == self._methodName and not fullUrl.startswith( "https://" ):
            fullUrl = "https://%s" % ( fullUrl, )

        if self._authType is None:
            response = requests.get( fullUrl )
        elif 'basic' == self._authType:
            userName, password = self._authData.split( ':' )
            response = requests.get( fullUrl, auth = HTTPBasicAuth( userName, password ) )
        elif 'bearer' == self._authType:
            response = requests.get( fullUrl, headers = { 'Authorization' : "bearer %s" % ( self._authData, ) } )
        elif 'token' == self._authType:
            response = requests.get( fullUrl, headers = { 'Authorization' : "token %s" % ( self._authData, ) } )
        elif 'otx' == self._authType:
            response = requests.get( fullUrl, headers = { 'X-OTX-API-KEY' : self._authData } )
        else:
            raise NotImplementedError( "Auth %s not supported." % ( self._authType, ) )

        response.raise_for_status()

        hFile = self._getTempFile()

        nTotal = 0
        for data in response.iter_content( 1024 * 512 ):
            hFile.write( data )
            nTotal += len( data )
            if self._maxSize is not None and nTotal > self._maxSize:
                raise RuntimeError( "Maximum resource size reached." )

        hFile.flush()
        hFile.seek( 0 )

        for fileName, fileContent in self._multiplexContent( hFile ):
            yield ( '%s%s' % ( fullUrl, fileName if fileName is not None else '' ), fileContent )

    def _doGcs( self ):
        if 'gaia' == self._authType:
            try:
                creds = base64.b64decode( self._authData )
            except:
                raise SyntaxError( "Gaia auth data should be base64 encoded." )
            try:
                creds = json.loads( creds )
            except:
                raise SyntaxError( "Gaia auth data should be a JSON." )
            creds = service_account.Credentials.from_service_account_info( creds )
        else:
            raise NotImplementedError( "Auth %s not supported." % ( self._authType, ) )

        client = google.cloud.storage.Client( credentials = creds )

        # Normalize the bucket + path for simplicity.
        bucketPath = self._methodDest
        if '/' not in bucketPath:
            bucketPath += '/'
        bucketName, bucketPath = bucketPath.split( '/', 1 )

        bucket = client.bucket( bucketName )

        blobs = [ _ for _ in bucket.list_blobs( prefix = bucketPath ) ]

        if self._maxSize is not None:
            for blob in blobs:
                if blob.size > self._maxSize:
                    raise RuntimeError( "Maximum resource size reached." )

        if 1 == len( blobs ):
            # We will multiplex potential archive files only
            # if they were requested directly, otherwise we assume
            # the user wanted all the file referenced.
            hFile = self._getTempFile()
            blobs[ 0 ].download_to_file( hFile )
            for fileName, fileContent in self._multiplexContent( hFile ):
                yield ( '%s%s' % ( self._methodDest, fileName if fileName is not None else '', ), fileContent )
        else:
            def _downloadBlob( blob ):
                return ( blob.path, blob.download_as_string() )

            for result in self._parallelExec( _downloadBlob, blobs, maxConcurrent = self._maxConcurrent ):
                if isinstance( result, Exception ):
                    raise result
                yield result

    def _doGithub( self ):
        repoParams = ''
        if '?' in self._methodDest:
            newRoot, repoParams = self._methodDest.split( '?', 2 )
            self._methodDest = newRoot
            repoParams = '?' + repoParams
        components = self._methodDest.split( '/', 2 )
        if 2 == len( components ):
            repoOwner, repoName = components
            repoPath = ''
        elif 3 == len( components ):
            repoOwner, repoName, repoPath = components
        else:
            raise SyntaxError( 'Github destination should be "repoOwner/repoName" or "repoOwner/repoName/repoSubDir".')

        if repoPath.endswith( '/' ):
            repoPath = repoPath[ 0 : -1 ]

        fullUrl = 'https://api.github.com/repos/%s/%s/contents/' % ( repoOwner, repoName )

        headers = None
        if self._authType is None:
            pass
        elif 'token' == self._authType:
            headers = { 'Authorization' : "token %s" % ( self._authData, ) }
        else:
            raise NotImplementedError( "Auth %s not supported." % ( self._authType, ) )

        def _listAllGithubFiles( subPath, allPaths, repoParams ):
            thisUrl = '%s%s%s%s' % ( fullUrl, '/' if subPath != '' else '', subPath, repoParams )
            response = requests.get( thisUrl, headers = headers )
            response.raise_for_status()

            files = response.json()

            # If the listing path was a single file
            # we normalize it.
            if isinstance( files, dict ):
                files = [ files ]

            # Recurse as needed.
            for f in files:
                if 'dir' == f[ 'type' ]:
                    _listAllGithubFiles( f[ 'path' ], allPaths, repoParams )
                elif 'file' == f[ 'type' ] and 0 != f[ 'size' ]:
                    if self._maxSize is not None and f[ 'size' ] > self._maxSize:
                        raise RuntimeError( "Maximum resource size reached." )
                    allPaths.append( ( f[ 'path' ], f[ 'download_url' ] ) )

        allPaths = []
        _listAllGithubFiles( repoPath, allPaths, repoParams )

        def _downloadFile( filePath, fileUrl ):
            hFile = self._getTempFile()

            response = requests.get( fileUrl, headers = headers )
            response.raise_for_status()

            for data in response.iter_content( 1024 * 512 ):
                hFile.write( data )

            hFile.flush()
            hFile.seek( 0 )

            return ( filePath, hFile )

        for result in self._parallelExec( lambda x: _downloadFile( x[ 0 ], x[ 1 ] ), allPaths, maxConcurrent = self._maxConcurrent ):
            if isinstance( result, Exception ):
                raise result

            filePath, hFile = result

            for fileName, fileContent in self._multiplexContent( hFile ):
                # We explode archives through multiplexing here too
                # so we generate a new subpath to report.
                yield ( '%s%s' % ( filePath, fileName if fileName is not None else '', ), fileContent )

    def _multiplexContent( self, hFile ):
        # Start testing different formats.
        hFile.seek( 0 )
        if tarfile.is_tarfile( hFile.name ):
            try:
                with tarfile.open( fileobj = hFile ) as f:
                    for member in f.getmembers():
                        # We only care about files.
                        if not member.isfile():
                            continue
                        yield ( '/' + member.name, f.extractfile( member ).read() )
            except:
                raise
            return

        hFile.seek( 0 )
        if zipfile.is_zipfile( hFile ):
            try:
                with zipfile.ZipFile( hFile ) as f:
                    for fileName in f.namelist():
                        # We only care about files.
                        if f.getinfo( fileName ).is_dir():
                            continue
                        yield ( '/' + fileName, f.read( fileName ) )
            except:
                raise
            return

        # All auto-detection failed, we assume
        # it's just a blob of data.
        hFile.seek( 0 )
        yield ( None, hFile.read() )