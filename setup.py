from setuptools import setup

requirements = list()
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

readme = str()
with open('README.md') as f:
    readme = f.read()

setup(name='Telemirror',

      # PEP 440 -- Version Identification and Dependency Specification
      version='0.0.1',

      # Project description
      description='Telegram bot channel mirroring app',
      long_description=readme,

      # Author details
      author='khoben',
      author_email='extless@gmail.com',

      # Project details
      url='https://github.com/khoben/telemirror',
      license="GNU v3",

      # Project dependencies
      install_requires=requirements,
      )
