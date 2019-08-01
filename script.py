import requests
import re
import json
import shutil
import os
import html
import argparse
import logging
import zipfile


def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))


def make_request(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(
            "ERROR: Something happened", response.status_code, response.text
        )
    return response


def download_file(url, destination):
    with requests.get(url, stream=True) as r:
        with open(destination, "wb") as f:
            shutil.copyfileobj(r.raw, f)

    return destination


def create_course_folder(course_title):
    try:
        os.makedirs(f"./{course_title}")
    except FileExistsError:
        pass


def get_course_title(data):
    course_title = re.search("<title>(.*)</title>", data)
    course_title = course_title.group(1)
    return html.unescape(course_title)


def log(text):
    logging.info(text)


def process_playlist(url, job_id=1):
    logging.basicConfig(
        level=logging.INFO,
        filename=f"{job_id}.log",
        filemode="a",
        format="%(levelname)s - %(message)s",
    )

    response = make_request(url)

    course_title = get_course_title(response.text)
    create_course_folder(course_title)

    result = re.search(
        '<script id="app-data" type="application/json">(.*)</script>', response.text
    )
    json_data = result.group(1)
    json_data = json.loads(json_data)

    for clip in json_data["clips"]:
        clip_config_url = clip["config"]
        response = make_request(clip_config_url)

        config_data = json.loads(response.text)
        video_title = config_data["video"]["title"]

        max_width = 0
        url = None
        for video in config_data["request"]["files"]["progressive"]:
            if video["width"] > max_width:
                max_width = video["width"]
                url = video["url"]

        download_file(url, os.path.join(f"./{course_title}", f"{video_title}.mp4"))
        log(f"Downloaded {course_title}: {video_title}")

    zipf = zipfile.ZipFile(f"{course_title}.zip", "w", zipfile.ZIP_DEFLATED)
    zipdir(f"./{course_title}/", zipf)
    zipf.close()
    # Move to static folder


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        help="vimeo embed playlist. Example: https://vimeo.com/showcase/6106917/embed",
        required=True,
    )
    args = parser.parse_args()
    process_playlist(args.url)


if __name__ == "__main__":
    main()
    # example: "https://vimeo.com/showcase/6106917/embed"

# API extension:

# POST /vimeo-scraper/ {"url": "https://vimeo.com/showcase/6106917/embed" }
# returns { job_id: 2 }
# Triggers celery task

# GET /logs/2
# returns logs

# Chrome extension
# Click to get the vimeo embed
# POST
# GET
# Final link with all files to download
