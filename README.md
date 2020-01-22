# authenticated_resource_locator

Describes a way to specify access to a remote resource, supporting many methods, and including auth data, and all that within a single string.

## Format

```
[methodName,methodDest,authType,authData]
```

For example:

HTTP GET with Basic Auth: `[https,my.corpwebsite.com/resourdata,basic,myusername:mypassword]`

Access using Authentication bearer: `[https,my.corpwebsite.com/resourdata,bearer,bfuihferhf8erh7ubhfey7g3y4bfurbfhrb]`

Access using Authentication token: `[https,my.corpwebsite.com/resourdata,token,bfuihferhf8erh7ubhfey7g3y4bfurbfhrb]`

Google Cloud Storage: `[gcs,my-bucket-name/some-blob-prefix,gaia,base64(GCP_SERVICE_KEY)]`

You can also omit the auth components to just describe a method: `[https,my.corpwebsite.com/resourdata]`

## Return Value
The return value is a generator of tuples (fileName, fileData).

If pointing to a single file via HTTP for example, only one tuple will be
generated. However if pointing to a git repo, a zip or tar file, all the
files will be generated where fileName will be a complete path from the
source.

## Example

```python
resource = "[https,example.com/my-resource,basic,my-user,my-password]
with AuthenticatedResourceLocator( resource ) as r:
    for fileName, fileData in r:
        print( "Got file: %s\n" % ( fileName, ) )
        print( fileData )
```