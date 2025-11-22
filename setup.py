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

IMPORTANT DESIGN RULE (for stability):
- Runtime deps (Docker / FastAPI / inference) go in requirements.txt
- Dev deps (notebooks, linting, tests, etc.) go in requirements_dev.txt
- setup.py must NEVER install dev deps by default.
"""

import os
from setuptools import setup, find_packages


# ------------------------------------------------------------
# Helper: read a requirements file safely
# ------------------------------------------------------------
def read_requirements(path: str):
    """
    Read a requirements file and return a clean list of deps.

    We ignore:
    - empty lines
    - comments (# ...)
    - recursive includes (-r otherfile.txt)
    - git+ installs (not needed for our case)
    """
    reqs = []

    if not os.path.isfile(path):
        return reqs

    with open(path, "r") as f:
        for line in f:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Skip comments
            if line.startswith("#"):
                continue

            # Skip recursive includes
            if line.startswith("-r"):
                continue

            # Skip git installs
            if "git+" in line:
                continue

            reqs.append(line)

    return reqs


# ------------------------------------------------------------
# 1) Read runtime + dev requirements separately
# ------------------------------------------------------------

# These are the ONLY deps installed when someone runs:
#   pip install .
runtime_requirements = read_requirements("requirements.txt")

# These are OPTIONAL deps, installed only when someone runs:
#   pip install ".[dev]"
dev_requirements = read_requirements("requirements_dev.txt")


# ------------------------------------------------------------
# 2) Setup configuration
# ------------------------------------------------------------
setup(
    # Name that pip will install
    name="xplain_package",

    # Version (bump later if needed)
    version="0.0.1",

    # Short description (optional)
    description="Xplain X-ray captioning inference package",

    # IMPORTANT: our packages are inside src/
    package_dir={"": "src"},

    # IMPORTANT: find packages only inside src/
    packages=find_packages("src"),

    # ✅ Runtime-only dependencies
    install_requires=runtime_requirements,

    # ✅ Optional dev dependencies
    extras_require={
        "dev": dev_requirements
    },

    # Tests live in tests/
    test_suite="tests",

    # Include non-python files if you add MANIFEST.in later
    include_package_data=True,

    # Ensures safe installs
    zip_safe=False,
)
