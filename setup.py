import codecs
try:
    from setuptools import setup, find_packages
    extra_setup = dict(
        zip_safe=True,
        install_requires=[
            "PyYAML>=3.0",
            "Sphinx>=1.3",
            "Docutils",
            "sphinx-autobuild",
            "readthedocs-sphinx-ext",
            "recommonmark",
        ],
    )
except ImportError:
    from distutils.core import setup
    extra_setup = dict(
        requires=[
            "PyYAML (>=3.0)",
            "Sphinx (>=1.3)",
            "Docutils",
            "sphinx-autobuild",
            "readthedocs-sphinx-ext",
            "recommonmark",
        ]
    )

setup(
    name='readthedocs-build',
    version='1.0.0',
    author='Eric Holscher',
    author_email='eric@ericholscher.com',
    url='https://readthedocs.org',
    license='MIT',
    description='Build infrastructure for Read the Docs',
    packages=find_packages(),
    include_package_data=True,
    long_description=codecs.open("README.rst", "r", "utf-8").read(),
    entry_points={
        'console_scripts': [
            'readthedocs-build=legacy_cli:run_main',
            'rtd-build=legacy_cli:run_main',
            'rtfd-build=legacy_cli:run_main',
        ]
    },
    **extra_setup
)
