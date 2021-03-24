from setuptools import setup, find_packages

setup(
    name='userlayers',
    version='1.0.0',
    packages=find_packages(),
    long_description=open('README.md').read(),
    install_requires=[
        'django-polymodels == 1.4.1',
        'django-mutant == 0.2',
        'django-tastypie >= 0.13.3',
        'transliterate == 1.7.3',
        'vectortools == 0.0.7',
        'shapeutils == 0.0.1',
    ],
    dependency_links = [
##        'https://bitbucket.org/lighter/shape-utils/get/e0b5af9.zip#egg=shapeutils-0.0.1',
        'https://bitbucket.org/slavas/shape-utils/get/master.zip#egg=shapeutils-0.0.1',
    ],
)
