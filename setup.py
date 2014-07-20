from setuptools import setup, find_packages
from codecs import open # To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='obmtool',
    version='1.0.0',
    description='Automates Thunderbird+Lightning+OBM Connector setup',
    long_description=long_description,
    url='http://github.com/kewisch/lightning-connector-automation',
    author='Philipp Kewisch',
    author_email='pkewisch@linagora.com',
    license='MPL2',
    keywords='automation build tools OBM Thunderbird Lightning',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
    packages=['obmtool'],
    install_requires=[
        'M2Crypto',
        'iniparse',
        'mozrunner',
        'mozprofile',
        'mozversion',
        'mozmill',
        'virtualenv'
    ],

    package_data={ 'sample': ['obmtoolrc'] },
    entry_points={ 'console_scripts': [ 'obmtool=obmtool.app:main' ] },
)
