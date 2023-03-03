import os
import requests
from tqdm import tqdm
from agavepy import Agave

ag = Agave.restore()


def download_file(filepath, dirpath):
    rsp = ag.files.download(
        systemId="designsafe.storage.published", filePath=filepath
    )
    if isinstance(rsp, dict):
        raise ValueError(f"Failed to download: {filepath}")
    if not os.path.isdir(dirpath):
        os.makedirs(dirpath)
    with open(os.path.join(dirpath, os.path.basename(filepath)), "wb") as f:
        try:
            for block in rsp.iter_content(4096):
                if not block:
                    break
                f.write(block)
        except Exception as e:
            raise e
    return True


def download_project(projectId):
    url = f"https://designsafe-ci.org/api/projects/publication/{projectId}"

    payload = ""
    headers = ""

    response = requests.get(url, data=payload, headers=headers)
    response_json = response.json()

    files_info = dict()
    for i, event in enumerate(response_json["eventsList"]):
        files_info[i] = {
            "title": event["value"]["title"],
            "files": event["fileObjs"],
        }

    for event, data in tqdm(files_info.items()):
        dirpath = f"{projectId}/{data['title']}"
        for file in tqdm(data["files"], leave=False):
            filepath = f"{projectId}/{file['path']}"
            download_file(filepath, dirpath)

    return


projectId = "PRJ-3484"
download_project(projectId)
