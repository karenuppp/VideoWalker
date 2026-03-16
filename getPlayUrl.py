"""CMS get play URL helper (manual debug script)."""

import hashlib
import requests
from requests.auth import HTTPDigestAuth


def get_play_url(cms_url: str, camera_id: str, username: str, password: str, play_type: str = "live"):
    md5_password = hashlib.md5(password.encode()).hexdigest().lower()
    url = f"{cms_url}/cms/rest/GetPlayUrl/{camera_id}"
    params = {"Type": play_type}

    response = requests.get(
        url,
        params=params,
        auth=HTTPDigestAuth(username, md5_password),
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    try:
        result = get_play_url(
            cms_url="http://10.1.1.1:8031",
            camera_id="123456789012345",
            username="admin",
            password="123456",
            play_type="live",
        )
        print(f"播放链接: {result.get('PlayUrl')}")
        print(f"控制链接: {result.get('ControlUrl')}")
    except Exception as exc:
        print(f"请求失败: {exc}")
