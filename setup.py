from setuptools import setup, find_packages

setup(
    name='userlayers',
    version='0.0.1',
    packages=find_packages(),
    long_description=open('README.md').read(),
    install_requires=[
        'django-mutant == 0.1.2',
        'django-polymodels==1.2.3',
        'django-tastypie >=0.12.0, <0.13.0',
        'transliterate == 1.7.3',
        'vectortools == 0.0.1',
        'shapeutils == 0.0.1',
    ],
    dependency_links = [
        'https://bitbucket.org/lighter/vectortools/get/dc38815.zip#egg=vectortools-0.0.1',
        'https://bitbucket.org/lighter/shape-utils/get/eec0952.zip#egg=shapeutils-0.0.1',
    ],
)
