import hashlib
import re
import time
from dataclasses import dataclass
from typing import Optional, List, Any

import requests

from config import TEMP_MAIL_API_KEY
from sqlite.sqlite_stuff import SqliteCursor, ADD_STATS_ROW


@dataclass
class CreatedAt:
    milliseconds: Optional[int] = None


@dataclass
class ID:
    oid: Optional[str] = None


@dataclass
class MailAttachments:
    attachment: Optional[List[Any]] = None


@dataclass
class TempMailResponse:
    id: Optional[ID] = None
    created_at: Optional[CreatedAt] = None
    mail_id: Optional[str] = None
    mail_address_id: Optional[str] = None
    mail_from: Optional[str] = None
    mail_subject: Optional[str] = None
    mail_preview: Optional[str] = None
    mail_text_only: Optional[str] = None
    mail_text: Optional[str] = None
    mail_html: Optional[str] = None
    mail_timestamp: Optional[float] = None
    mail_attachments_count: Optional[int] = None
    mail_attachments: Optional[MailAttachments] = None

    def __init__(self, s):
        self.__dict__ = s


def make_temp_mail(s) -> List[TempMailResponse]:
    return [TempMailResponse(x) for x in s]


get_verify_reg = re.compile(r"(?<=Verify Email Address\n\[).*?ref_source=email", flags=re.DOTALL)


def get_allowed_domains():
    response = requests.request("GET", f"https://privatix-temp-mail-v1.p.rapidapi.com/request/domains/", headers={
        'x-rapidapi-key': TEMP_MAIL_API_KEY,
        'x-rapidapi-host': "privatix-temp-mail-v1.p.rapidapi.com"
    })
    _domains = response.json()
    i = 0
    while True:
        yield _domains[i]
        i = i if i < len(_domains) - 1 else 0


domains = get_allowed_domains()


def dont_overuse_temp_mail():
    with SqliteCursor() as cursor:
        state = {
            "num_remaining": 100 - SqliteCursor.get_temp_mail_api_remaining(cursor),
            "lowest_depth_retries": 0
        }

    if state["num_remaining"] <= 0:
        return None

    def update_table(n_requests: int):
        with SqliteCursor() as _cursor:
            for _ in range(n_requests):
                _cursor.execute(ADD_STATS_ROW)

    def _dont_overuse_temp_mail(fn):
        def _inner(*args, **kwargs):
            state["num_remaining"] -= 1
            if not state["num_remaining"] > 0:
                return None
            state["lowest_depth_retries"] = args[0] if len(args) > 0 else 0
            res = fn(*args, **kwargs)
            if len(args) == 0:
                update_table(state["lowest_depth_retries"] + 1)
            return res
        return _inner

    return _dont_overuse_temp_mail


def temp_mail(r_id: str):
    email_address = f"{r_id}{next(domains)}"
    sometimes_wrapper = dont_overuse_temp_mail()
    if sometimes_wrapper is None:
        print("No temp mail api requests remaining! Skipping verify.")
        return email_address, None

    @sometimes_wrapper
    def _temp_main(retries=0, max_attempts=5):
        if retries == max_attempts:
            return None
        digest = hashlib.md5(email_address.encode('utf-8')).hexdigest()
        response = requests.request("GET", f"https://privatix-temp-mail-v1.p.rapidapi.com/request/mail/id/{digest}/", headers={
            'x-rapidapi-key': TEMP_MAIL_API_KEY,
            'x-rapidapi-host': "privatix-temp-mail-v1.p.rapidapi.com"
        })
        res_json = response.json()
        if not res_json or isinstance(res_json, dict) and "error" in res_json.keys():
            time.sleep(retries * 10)
            return _temp_main(retries + 1, max_attempts)
        mail_list = make_temp_mail(res_json)
        for item in mail_list:
            if match := re.search(get_verify_reg, item.mail_text):
                return match.group()
        raise Exception("No verify link found!")

    return email_address, _temp_main

