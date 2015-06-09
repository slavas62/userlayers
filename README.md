# Installation #

Install app:

```
pip install ssh://hg@bitbucket.org/ololoteam/userlayers
```

Add apps to INSTALLED_APPS:

```
INSTALLED_APPS += (
    'mutant',
    'mutant.contrib.boolean',
    'mutant.contrib.numeric',
    'mutant.contrib.text',
    'mutant.contrib.geo',
    
    'userlayers',
)
```

Add to urls.py:

```
url(r'^userlayers/', include('userlayers.urls')),
```