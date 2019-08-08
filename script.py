import requests
import json
import shutil
import os
import argparse
import logging
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


def make_request(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_3) AppleWebKit/604.5.6 (KHTML, like Gecko) Version/11.0.3 Safari/604.5.6"
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
    course_path = f"./downloads/{course_title}"
    try:
        os.makedirs(course_path)
    except FileExistsError:
        pass
    return course_path


def login(driver, login_url, username, password):
    print("Logging into the domain")
    driver.get(login_url)
    driver.find_element_by_id("iump_login_username").send_keys(username)
    driver.find_element_by_id("iump_login_password").send_keys(password)
    driver.find_element_by_xpath('//*[@id="ihc_login_form"]/div[6]/input').click()
    print("Logging successful")


def get_app_data_script(driver, url):
    driver.get(url)
    wait(driver, 30).until(
        EC.frame_to_be_available_and_switch_to_it(
            driver.find_element_by_xpath(
                "/html/body/div[1]/div[4]/div[2]/div/div/div[3]/div[1]/div/div/div/div/div/iframe"
            )
        )
    )
    wait(driver, 30).until(EC.presence_of_element_located((By.ID, "app-data")))
    data = driver.find_element_by_id("app-data")
    response = data.get_attribute("innerHTML")
    driver.close()
    return response


def process_playlist(url, login_url=None, username=None, password=None):
    options = Options()
    options.headless = False
    driver = webdriver.Firefox(options=options)
    if login_url and username and password:
        login(driver, login_url, username, password)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    json_data = get_app_data_script(driver, url)

    json_data = json.loads(json_data)
    course_title = json_data["playlist_data"]["title"]
    course_path = create_course_folder(course_title)

    if not json_data["clips"]:
        logging.error("No clips")
        return

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

        download_file(url, os.path.join(course_path, f"{video_title}.mp4"))
        logging.info(f"Downloaded {course_title}: {video_title}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Url with embed vimeo playlist", required=True)
    parser.add_argument("--login-url", help="", required=False)
    parser.add_argument("--password", help="Password", required=False)
    parser.add_argument("--username", help="Username", required=False)
    args = parser.parse_args()
    process_playlist(args.url, args.login_url, args.username, args.password)


if __name__ == "__main__":
    main()
