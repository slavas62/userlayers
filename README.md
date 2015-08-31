# Installation #

Install app:

```
pip install ssh://hg@bitbucket.org/ololoteam/userlayers
```

Add apps to INSTALLED_APPS:

```
INSTALLED_APPS += (
    'mutant',
    'userlayers',
)
```

Add to urls.py:

```
url(r'^userlayers/', include('userlayers.urls')),
```

# Usage #

Let's create table "foo" with fields: "display_name" (text), "value" (integer), "is_ok" (boolean):
```
curl --dump-header - -H "Content-Type: application/json" -X POST --data '{"name": "foo", "fields": [{"name": "display_name", "type": "text"}, {"name": "value", "type": "integer"}, {"name": "is_ok", "type": "boolean"}]}' http://localhost:8000/userlayers/api/v1/tables/
```

Response:
```
HTTP/1.0 201 CREATED
Date: Tue, 09 Jun 2015 16:53:05 GMT
Server: WSGIServer/0.1 Python/2.7.8
Vary: Accept
X-Frame-Options: SAMEORIGIN
Content-Type: text/html; charset=utf-8
Location: http://localhost:8000/userlayers/api/v1/tables/36/
```

Row creation for table "foo":
```
curl --dump-header - -H "Content-Type: application/json" -X POST --data '{"display_name": "foo", "value": 99, "is_ok": false, "geometry": {"type":"Polygon", "coordinates":[[[37.44, 55.65], [37.60, 55.96], [37.80, 55.66], [37.44, 55.65]]]}}' http://localhost:8000/userlayers/api/v1/tablesdata/36/data/ 
```

Response:
```
HTTP/1.0 201 CREATED
Date: Tue, 09 Jun 2015 16:58:12 GMT
Server: WSGIServer/0.1 Python/2.7.8
Vary: Accept
X-Frame-Options: SAMEORIGIN
Content-Type: text/html; charset=utf-8
Location: http://localhost:8000/userlayers/api/v1/tablesdata/36/data/1/
```

Get "foo" rows:
```
curl -H "Content-Type: application/json" http://localhost:8000/userlayers/api/v1/tablesdata/36/data/
```

Result:
```
{"meta": {"limit": 20, "next": null, "offset": 0, "previous": null, "total_count": 1}, "objects": [{"display_name": "foo", "geometry": {"coordinates": [[[37.44, 55.65], [37.6, 55.96], [37.8, 55.66], [37.44, 55.65]]], "type": "Polygon"}, "id": 1, "is_ok": false, "resource_uri": "/userlayers/api/v1/tablesdata/36/data/1/", "value": "99"}]}
```
