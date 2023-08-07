from enum import Enum, auto
import platform
import re
import subprocess
import hashlib

class Platform(Enum):
    LINUX = auto()
    WINDOWS = auto()
    MACOS = auto()
    DOCKER = auto()

    def deserialize(plat: str):
        if plat == 'Linux':
            return Platform.LINUX
        elif plat == 'Darwin':
            return Platform.MACOS
        elif plat == 'Windows':
            return Platform.WINDOWS

        return Platform.DOCKER

def get_device_identifier(username: str):
    match Platform.deserialize(platform.system()):
        case Platform.LINUX:
            pass
        case Platform.MACOS:
            device_info = subprocess.run(
                ['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
                check=True,
                capture_output=True,
                text=True,
            )
            machine_id = re.search(r'\"IOPlatformUUID\" = \"([A-Z0-9-]+)\"', device_info.stdout).group(1)
        case Platform.WINDOWS:
            pass
        case Platform.DOCKER:
            pass

    return hashlib.sha256(f'{username}-{machine_id}').hexdigest()
