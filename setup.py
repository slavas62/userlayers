from distutils.core import setup

setup(
    name='userlayers',
    version='0.0.1',
    packages=['userlayers'],
    long_description=open('README.md').read(),
    install_requires=[
        'django-mutant == 0.1.2',
        'django-tastypie >= 0.12.0'
    ],
)
