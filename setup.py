import os
from setuptools import setup, find_packages


def get_here(file: str):
    # return os.path.abspath(os.path.dirname(__file__))
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), file)


def get_long_description():
    readme = get_here('README.md')
    if os.path.isfile(readme):
        with open(readme, 'r') as f:
            return f.read()
    return ''


def get_name():
    return 'satorisynapse'


def get_version():
    return '0.1.2'


def get_requirements():
    requirements = get_here('requirements.txt')
    if os.path.isfile(requirements):
        with open(requirements, 'r') as f:
            return f.read().splitlines()
    return []


if __name__ == '__main__':
    setup(
        name=get_name(),
        version=get_version(),
        description='satorisynapse contains domain model and apis for the Satori Network',
        long_description=get_long_description(),
        long_description_content_type="text/markdown",
        # packages=[get_name()] + [f'{get_name()}.{p}' for p in find_packages(
        #    where=get_name())],
        packages=find_packages(),
        install_requires=get_requirements(),
        dependency_links=[
            'git+https://github.com/SatoriNetwork/python-evrmorelib.git#egg=python-evrmorelib'
        ],
        python_requires='>=3.7',
        author='Jordan Miller',
        author_email="jordan@satorinet.io",
        url=f'https://github.com/SatoriNetwork/{get_name()}',
        download_url=f'https://github.com/SatoriNetwork/{get_name()}',
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: Apache Software License",
            "Operating System :: OS Independent",
        ],
        entry_points={
            "console_scripts": [
                f"{get_name()} = {get_name()}.cli:main",
            ]
        },
    )
