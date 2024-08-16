from arl import AuthenticatedResourceLocator as ARL

def test_httpsWithTar():
    testArl = "[https,api.github.com/repos/refractionPOINT/sigma_rules/tarball/0.2.0]"
    nElemFound = 0
    with ARL( testArl ) as r:
        for fileName, fileContent in r:
            assert( fileName )
            assert( 0 != len( fileContent ) )
            nElemFound += 1
    assert( 0 != nElemFound )

def test_httpsWithZip():
    testArl = "[https,api.github.com/repos/refractionPOINT/sigma_rules/zipball/0.2.0]"
    nElemFound = 0
    with ARL( testArl ) as r:
        for fileName, fileContent in r:
            assert( fileName )
            assert( 0 != len( fileContent ) )
            nElemFound += 1
    assert( 0 != nElemFound )

def test_straightFile():
    testArl = "[https,https://raw.githubusercontent.com/refractionPOINT/sigma_rules/master/README.md]"
    nElemFound = 0
    with ARL( testArl ) as r:
        for fileName, fileContent in r:
            assert( fileName )
            assert( 0 != len( fileContent ) )
            nElemFound += 1
    assert( 1 == nElemFound )

def test_straightFileCompat():
    testArl = "https://raw.githubusercontent.com/refractionPOINT/sigma_rules/master/README.md"
    nElemFound = 0
    with ARL( testArl ) as r:
        for fileName, fileContent in r:
            assert( fileName )
            assert( 0 != len( fileContent ) )
            nElemFound += 1
    assert( 1 == nElemFound )

def test_maxSizeBad():
    testArl = "https://raw.githubusercontent.com/refractionPOINT/sigma_rules/master/README.md"
    nElemFound = 0
    try:
        with ARL( testArl, maxSize = 5 ) as r:
            for fileName, fileContent in r:
                nElemFound += 1
    except:
        pass
    assert( 0 == nElemFound )

def test_maxSizeGood():
    testArl = "https://raw.githubusercontent.com/refractionPOINT/sigma_rules/master/README.md"
    nElemFound = 0
    try:
        with ARL( testArl, maxSize = 1024 ) as r:
            for fileName, fileContent in r:
                nElemFound += 1
    except:
        pass
    assert( 1 == nElemFound )

# def test_httpsWithTarTokenAuth():
#     testArl = "[https,api.github.com/repos/refractionPOINT/replicant_sigma/tarball/0.1.9,token,2548a8...]"
#     nElemFound = 0
#     with ARL( testArl ) as r:
#         for fileName, fileContent in r:
#             assert( fileName )
#             assert( 0 != len( fileContent ) )
#             nElemFound += 1
#     assert( 0 != nElemFound )

# def test_httpsWithGcs():
#     testArl = "[gcs,lc-sensor-builds/4.17.2/alpine.tar.gz,gaia,ewogICJ0e...]"
#     nElemFound = 0
#     with ARL( testArl ) as r:
#         for fileName, fileContent in r:
#             assert( fileName )
#             assert( 0 != len( fileContent ) )
#             nElemFound += 1
#     assert( 0 != nElemFound )

def test_githubRootNoAuth():
    testArl = "[github,refractionPOINT/python-limacharlie]"
    nElemFound = 0
    with ARL( testArl ) as r:
        for fileName, fileContent in r:
            assert( fileName )
            assert( 0 != len( fileContent ) )
            nElemFound += 1
    assert( 0 != nElemFound )

def test_githubSubdirNoAuth():
    testArl = "[github,refractionPOINT/sigma/rules/windows/builtin]"
    nElemFound = 0
    with ARL( testArl ) as r:
        for fileName, fileContent in r:
            assert( fileName )
            assert( 0 != len( fileContent ) )
            nElemFound += 1
    assert( 0 != nElemFound )

def test_githubSigleFileNoAuth():
    testArl = "[github,refractionPOINT/sigma/README.md]"
    nElemFound = 0
    with ARL( testArl ) as r:
        for fileName, fileContent in r:
            assert( fileName )
            assert( 0 != len( fileContent ) )
            nElemFound += 1
    assert( 1 == nElemFound )

# def test_githubAuth():
# with open('<INSERT SSH KEY PATH', 'r') as file:
#        data = file.read()
#    testArl = "[github,refractionPOINT/go-limacharlie,ssh,%s]" % (data)
#     nElemFound = 0
#     with ARL( testArl ) as r:
#         for fileName, fileContent in r:
#             assert( fileName )
#             assert( 0 != len( fileContent ) )
#             nElemFound += 1
#     assert( 0 != nElemFound )

def test_githubBranch():
    testArl = "[github,refractionPOINT/sigma/lc-rules/windows_sysmon/?ref=lc-rules]"
    nElemFound = 0
    with ARL( testArl ) as r:
        for fileName, fileContent in r:
            assert( fileName )
            assert( 0 != len( fileContent ) )
            nElemFound += 1
    assert( 0 != nElemFound )
