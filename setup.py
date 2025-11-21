"""
setup.py

This file tells pip/setuptools how to install this repository as a Python package.

We moved all importable code under:
    src/xplain_package/

So we MUST:
1) tell setuptools that packages live in "src/"  -> package_dir={"": "src"}
2) search for packages inside "src/"            -> find_packages("src")

If we don't do this, pip installs nothing importable,
and you get: ModuleNotFoundError: No module named 'xplain_package'
"""

import os
from setuptools import setup, find_packages

# ------------------------------------------------------------
# 1) Read requirements from requirements files (same as before)
# ------------------------------------------------------------
requirements = []

# Runtime requirements
if os.path.isfile("requirements.txt"):
    with open("requirements.txt") as f:
        content = f.readlines()
    # Keep only normal pip lines (ignore git+ lines)
    requirements.extend([x.strip() for x in content if x.strip() and "git+" not in x])

# Dev requirements
if os.path.isfile("requirements_dev.txt"):
    with open("requirements_dev.txt") as f:
        content = f.readlines()
    requirements.extend([x.strip() for x in content if x.strip() and "git+" not in x])

# ------------------------------------------------------------
# 2) Setup configuration
# ------------------------------------------------------------
setup(
    # Name that pip will install
    name="xplain_package",

    # Version (can bump later)
    version="0.0.1",

    # Short description (optional)
    description="Xplain X-ray captioning inference package",

    # IMPORTANT: our packages are inside src/
    package_dir={"": "src"},

    # IMPORTANT: find packages only inside src/
    packages=find_packages("src"),

    # Install dependencies read above
    install_requires=requirements,

    # Tests live in tests/
    test_suite="tests",

    # Include non-python files if you add MANIFEST.in later
    include_package_data=True,

    # Ensures safe installs
    zip_safe=False,
)
