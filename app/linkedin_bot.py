import os
import time
from pathlib import Path

import requests
from datetime import datetime
import json
import sys
from bs4 import BeautifulSoup

sys.path.append(os.path.join(os.path.dirname(sys.path[0])))

import app.config as cfg
import app.utils as utils


timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

log = utils.get_log(os.path.basename(__file__))

post_lock = False



def post_to_linkedin(text, image, origin=None):
    log.debug(f"Entering: post_to_linkedin(<TEXT>, {image}, {origin} )")
    ## origin: personal post or company post -> Setting the author
    ## company post is the default

    if origin is None:
        origin = cfg.post_as

    if origin.lower() == "company":
        curn = get_company_urn()
        company_page_id = curn.rsplit(":", 1)[-1]
        author = f"urn:li:organization:{company_page_id}"
    
    if origin.lower() == "personal": 
        purn = get_person_urn()
        person_id = purn.rsplit(":", 1)[-1]
        author = f"urn:li:person:{person_id}"

    log.info(f"Post as {origin} - {author}")

    ## prepare image for linkedin
    asset_urn, upload_url = register_image_upload(author)
    
    ## upload to linkedin
    log.info(f"uploading Image {image} as asset {asset_urn}")
    upload_image_bytes(upload_url, image)

    resp, link = post_linkedin_api(text, asset_urn, author)
    return resp, link





def register_image_upload(owner):
    log.debug(f"Entering: register_image_upload( {owner} )")
    asset_api = "https://api.linkedin.com/v2/assets?action=registerUpload"
    headers = {"Authorization": f"Bearer {cfg.linkedin_token}", "X-Restli-Protocol-Version": "2.0.0"}
    payload = {
                "registerUploadRequest": {
                    "recipes": [
                        "urn:li:digitalmediaRecipe:feedshare-image"
                    ],
                    #"owner": f"urn:li:person:{person_id}",
                    "owner": f"{owner}",
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }
                    ]
                }
            }
    r = requests.post(asset_api, headers=headers, json=payload)
    r.raise_for_status()
    j = r.json()
    return j["value"]["asset"], j["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    





def get_image_path(file):
    path, file = os.path.split(file)
    file_path = f"{os.getcwd()}/content/images/{file}"
    log.debug("Imagefile: {file_path}")
    return file_path




def upload_image_bytes(upload_url, image_path):
    log.debug(f"Entering: upload_image_bytes( {upload_url}, {image_path} )")
    file_path = get_image_path(image_path)


    if not os.path.exists(file_path):
        log.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
        exit()

    with open(file_path, 'rb') as f:
        headers = {
            "Authorization": f"Bearer {cfg.linkedin_token}"
        }
        if not cfg.demo:
            response = requests.put(upload_url, headers=headers, data=f)
        else:
            log.warning(f"Demo Mode ist {cfg.demo}- otherwise an image would be uploaded to LI (Faking response now)")
            log.debug(f"\nCalling LinkedIn API : requests.put({upload_url}, {headers}, {f})\n\n")
            response = Fake_response(status_code="220")
            
        # Check the response
        log.info(f"Image {file_path} uploaded to:{upload_url}   - with code: {response.status_code}")
        log.debug(response.text)




## create a Fake Object to return Fake responses from API
class Fake_response:
    def __init__(self, status=None, status_code=None, text=None):
        self.status = status
        self.status_code = status_code
        jText = {"text": text, "id": "Fake123"}
        self.text = json.dumps(jText)



# --- LinkedIn Posting ---
def post_linkedin_api(text, asset_urn, author):
    log.info("Start post to linkedin")
    """Post in LinkedIn hochladen"""
    api_url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {"Authorization": f"Bearer {cfg.linkedin_token}", "X-Restli-Protocol-Version": "2.0.0"}

    payload = {
        "author": f"{author}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "description": {
                            "text": f"{cfg.alt_image}"
                        },
                        "media": f"{asset_urn}",
                        "title": {
                            "text": f"{cfg.alt_image}"
                        }
                    }
                ]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    
    if not cfg.demo:
        r = requests.post(url=api_url, headers=headers, json=payload)
    else:
        log.warning(f"Demo Mode is {cfg.demo} - otherwise the posting would be placed at LI now (Faking response now)")
        r = Fake_response(status_code = 221, text = "Fake response from LinkedIn")
        link = "https://www.linkedin.com"

    log.debug(f"Sending Post to LI now by requests.post(url={api_url}, headers=<headers>, json=<payload>)")
    log.debug(f"LinkedIn Response: {r.status_code} - {r.text}")

    if r.status_code <= 220:
        data = json.loads(r.text)
        urn = data["id"]
        id = urn.split(":")[-1]
        company_urn = get_company_urn()
        #link = f"https://www.linkedin.com/feed/update/urn:li:activity:{id}"
        link = f"https://www.linkedin.com/company/{company_urn}/admin/dashboard/"
        log.info("post send to linkedin")
    
    return r.status_code, link




def web_post_existing_html(file):
    log.info(f"Web interaction: posting now file {file}")
    try:
        resp, link = post_existing_html(file)
        return resp, link
    except Exception as e:
        log.error(f"Error during posting of existing html file: {e}")
        return False, None




def get_posting_data(file_path):
    
    """ 
    read the file and returns all information as one dict
    Expects a full qualified path to the file
    Optional is an Array with elements to read
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

        content_dict = {}

        # Creation time
        c_time = ""
        c_time = soup.select_one(".timestamp").get_text(strip=True)
        content_dict.update({"c_time":c_time})

        # Confirmed-Flag auslesen
        confirmed = "No"
        confirmed_span = soup.find("span", {"class": "confirmed"})
        confirmed = confirmed_span.text.strip()
        content_dict.update({"confirmed":confirmed})

        # origin auslesen -> wird zu author
        origin = cfg.post_as
        origin_span = soup.find("span", {"class": "origin"})
        origin = origin_span.text.strip()
        content_dict.update({"origin":origin})

        # Text lesen
        text = ""
        text_span = soup.find("div", {"class": "post-text"})
        text = text_span.text.strip()
        content_dict.update({"text":text})

        # image finden
        image = ""
        img_span = soup.find("img", {"class": "post-image"})
        image = img_span.get("src")
        content_dict.update({"image":image})

        # hashtags lesen
        hashtags = ""
        hash_span = soup.find("div", {"class": "hashtags"})
        hastags = hash_span.text.strip()
        content_dict.update({"hastags":hashtags})

        # Post-Logs (Liste von dicts mit platform & timestamp)
        logs = []
        meta_section = soup.find("section", {"class": "posting-meta"})
        if meta_section:
            for log in meta_section.find_all("div", {"class": "post-log"}):
                platform = log.find("span", {"class": "platform"}).get_text(strip=True) if log.find("span", {"class": "platform"}) else None
                timestamp = log.find("span", {"class": "timestamp"}).get_text(strip=True) if log.find("span", {"class": "timestamp"}) else None
                logs.append({"platform": platform, "timestamp": timestamp})
        content_dict.update({"logs":logs})


        # Schedules lesen
        schedules = utils.get_schedules_from_post(file_path)
        content_dict.update({"schedules":schedules})

        return content_dict






# --- Einen vorhandenen HTML-Post posten ---
def post_existing_html(file_path):
    log.debug(f"Entering: post_existing_html( {file_path} )")

    global post_lock
    if post_lock == True:
        log.debug("post existing html in progress. wait a second...")
        time.sleep(2)
        post_existing_html(file_path)

    post_lock = True

    data = get_posting_data(file_path)

    origin = data["origin"]
    text = data["text"]
    confirmed = data["confirmed"]
    img_url = data["image"]

    if confirmed != "Yes":
        log.warning(f"This post is not confirmed as of now! Cannot post before - {file_path}")
        post_lock = False
        return 500, None
    else:
        log.debug(f"Calling post_to_linkedin(<TEXT>, {img_url}, {origin})")
        resp, link = post_to_linkedin(text, img_url, origin)
        print ("Response from post_existing_html: ", resp)

        platform = "linkedin"
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        add_post_log(file_path, platform, timestamp)
        post_lock = False
        return resp, link





def add_post_log(file_path, platform, timestamp):
    """
    Fügt in das Post-HTML einen neuen <div class="post-log">-Eintrag ein.
    add_post_log(file_path, platform, timestamp)
    Falls das <section class="posting-meta"> nicht existiert, wird es erzeugt.
    """
    log.debug(f"Adding post-log to {file_path}")
    if not os.path.exists(file_path):
        log.error(f"File {file_path} does not exist")
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    soup, span = add_post_log_span(soup, platform, timestamp)
    
    log.info(f"new post-log in {file_path}")
    # Datei zurückschreiben
    with open(file_path, "w", encoding="utf-8") as f:
        log.debug(f"writing to file {f}")
        f.write(str(soup))



def add_post_log_span(soup: BeautifulSoup, platform=None, timestamp=None):
    if not platform:
        platform = "linkedin"

    if not timestamp:
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        
    #soup = BeautifulSoup(html, "html.parser")
    # Falls meta-Section fehlt → neu anlegen
    meta_section = soup.find("section", {"class": "posting-meta"})
    if not meta_section:
        meta_section = soup.new_tag("section", attrs={"class": "posting-meta", "style": "display:none;"})
        soup.body.append(meta_section)

    # Neuen Log-Eintrag erstellen
    post_log = soup.new_tag("div", attrs={"class": "post-log"})

    span_platform = soup.new_tag("span", attrs={"class": "platform"})
    span_platform.string = platform
    post_log.append(span_platform)

    span_timestamp = soup.new_tag("span", attrs={"class": "timestamp"})
    span_timestamp.string = timestamp
    post_log.append(span_timestamp)

    meta_section.append(post_log)

    return soup, meta_section
    



def get_person_urn():
    url = "https://api.linkedin.com/v2/me"
    headers = {"Authorization": f"Bearer {cfg.linkedin_token}", "X-Restli-Protocol-Version": "2.0.0"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        person_urn = data.get("id")
        log.debug(f"LinkedIn Person URN: {person_urn}")
        return f"urn:li:person:{person_urn}"
    else:
        log.error(f"Fehler:  {response.status_code} -- {response.text}")
        return None
    






def get_company_urn():
    url = "https://api.linkedin.com/v2/organizationalEntityAcls?q=roleAssignee&role=ADMINISTRATOR"
    headers = {"Authorization": f"Bearer {cfg.linkedin_token}", "X-Restli-Protocol-Version": "2.0.0"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        #urn = data.get("organizationalTarget")
        urn = data['elements'][0]['organizationalTarget']
        log.debug(f"LinkedIn Company URN: {urn}")
        return f"{urn}"
    else:
        log.error(f"Fehler:  {response.status_code} -- {response.text}")
        return None
    
