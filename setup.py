from setuptools import setup

setup(name='strom',
      version='0.1',
      description='A stream/pipeline-centric data processing tool',
      url='http://github.com/32leaves/strom.py',
      author='Christian Weichel',
      author_email='info@32leav.es',
      license='MIT',
      packages=['strom'],
      zip_safe=False,
      entry_points={
          'console_scripts': ['strom=strom.command_line:main'],
      },
      install_requires=['pandas', 'svgwrite'])


