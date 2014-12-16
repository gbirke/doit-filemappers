from setuptools import setup, find_packages

setup(name='doit-filemappers',
      version='0.1',
      description='File mappers as task generators for the DoIt automation library',
      url='http://github.com/storborg/funniest',
      author='Gabriel Birke',
      author_email='gabriel.birke@gmail.com',
      license='MIT',
      install_requires = ['doit', 'pathlib'],
      tests_require = ['mock', 'pytest'],
      packages = find_packages()
)

