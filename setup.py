from setuptools import setup, find_packages


setup(
    name='mub',
    version='0.0.1',
    author='yupix',
    description='',
    packages=find_packages(),
    install_requires=['mi.py @ git+https://github.com/yupix/Mi.py.git'],
    entry_points={
        'console_scripts': [
            'mub=mub.cli:main',
        ]
    }

)
