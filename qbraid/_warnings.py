"""
Module for emitting and disabling warnings at top level.

"""
import warnings

import urllib3


def _warn_new_version(local: str, api: str) -> bool:
    """Returns True if you should warn user about updated package version,
    False otherwise."""

    local_vlst = local.split('.')
    api_vlst = api.split('.')

    check_patch = lambda x: int(local_vlst[x]) < int(api_vlst[x])
    
    for i in range(3):
        if check_patch(i):
            return True
    return False


def _check_version():
    """Emits UserWarning if updated package version exists in qBraid API
    compared to local copy."""

    from ._version import __version__ as version_local
    from .api.session import QbraidSession

    session = QbraidSession()
    version_api = session.get("/public/lab/get-sdk-version", params={}).json()

    if _warn_new_version(version_local, version_api):
        warnings.warn(
            f"You are using qbraid version {version_local}; however, version {version_api} is available. "
            f"To avoid compatibility issues, consider upgrading by uninstalling and reinstalling the qBraid-SDK environment.",
            UserWarning,
        )


warnings.filterwarnings("ignore", category=SyntaxWarning)
warnings.filterwarnings("ignore", category=UserWarning, message="Setuptools is replacing distutils")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_check_version()
