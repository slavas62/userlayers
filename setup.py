from setuptools import setup, find_packages

setup(
    name='userlayers',
    version='1.0.0',
    packages=find_packages(),
    long_description=open('README.md').read(),
    install_requires=[
        'django-polymodels == 1.4.1',
        'django-mutant == 0.2',
        'django-tastypie >= 0.13.0',
        'transliterate == 1.7.3',
        'vectortools == 0.0.6',
        'shapeutils == 1.0.0',
    ],
    dependency_links = [
        'https://github.com/slavas62/shape-utils/archive/master.zip#egg=shapeutils-1.0.0',
    ],
)
