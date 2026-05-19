import os
import setuptools
import shutil

import lib


def setup() -> None:
    with open('requirements.txt') as text_file:
        requirements = text_file.read().splitlines()

    version = lib.__version__

    setuptools.setup(
        packages=setuptools.find_packages(),
        install_requires=requirements,
        python_requires='>=3.10.0',
        include_package_data=True,
        author='UranLajci',
        version=version,
        name='lib',
    )

    build_path = '../ethno-balkan-app/build/'
    if os.path.exists(build_path):
        shutil.rmtree(build_path)

    egg_info_path = '../ethno-balkan-app/lib.egg-info'
    if os.path.exists(egg_info_path):
        shutil.rmtree(egg_info_path)


if __name__ == '__main__':
    setup()
   