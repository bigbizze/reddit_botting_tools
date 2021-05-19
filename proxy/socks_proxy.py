import os
import random
import time
from fake_useragent import UserAgent
import datetime
from typing import Optional, List

ua = UserAgent()


class ProxyAddress:
    def __init__(self, address: str):
        self.address: str = address
        self.last_health_issue: Optional[datetime.datetime] = None
        self.health_issues = 0
        self._available_time: Optional[datetime.datetime] = None
        self.socks_address = self.make_socks_address()

    def report_health_issue(self):
        self.last_health_issue = datetime.datetime.now()
        sleep_for = self.health_issues if self.health_issues < 10 else 10
        self._available_time = self.last_health_issue + datetime.timedelta(minutes=sleep_for)
        self.health_issues += 1

    def is_available(self):
        if self._available_time is None:
            return True
        elif datetime.datetime.now() > self._available_time:
            self._available_time = None
            return True
        return False

    def make_socks_address(self) -> str:
        return self.address


def make_proxy_address(proxy: List[str]) -> ProxyAddress:
    return ProxyAddress(
        proxy[0]
    )


def load_proxies(path: str):
    with open(f"{os.path.dirname(__file__)}/{path}", "r", encoding="utf-8") as fp:
        data = [make_proxy_address([y.replace('"', "") for y in x.split(",")]) for x in fp.read().split("\n")]
    return data


def load_available_proxies() -> List[ProxyAddress]:
    if not os.path.exists(rf"{os.path.dirname(__file__)}/proxy_files/working_proxies.txt"):
        raise Exception("No file {}, run \"./proxy/find_working.py\"!".format(rf"{os.path.dirname(__file__)}/proxy_files/working_proxies.txt"))
    with open(rf"{os.path.dirname(__file__)}/proxy_files/working_proxies.txt") as fq:
        data = list(reversed([ProxyAddress(x) for x in fq.read().split("\n")]))
    data = data[1:] + [data[0]]
    return data


class ProxyRequestHandler:
    def __init__(self):
        self.proxies: List[ProxyAddress] = load_available_proxies()
        self.num_proxies = len(self.proxies)
        self.i = random.randint(0, self.num_proxies)

    def some_available(self):
        for proxy in self.proxies:
            if proxy.is_available():
                return True
        return False

    def _get_next_idx(self):
        next_i = self.i + 1
        if next_i >= self.num_proxies:
            next_i = 0
        self.i = next_i if next_i < self.num_proxies else 0
        return self.i

    def get_next_proxy(self):
        proxy = self.proxies[self._get_next_idx()]
        if proxy.is_available():
            return proxy


class ProxyRequest:
    def __init__(self):
        self.handler = ProxyRequestHandler()

    def proxy(self):
        proxy = None
        while proxy is None:
            proxy = self.handler.get_next_proxy()
            if proxy is None:
                time.sleep(1)
        return proxy

    def get_socks_address(self):
        while not self.handler.some_available():
            print("Sleeping because none available...")
            time.sleep(30)
        proxy = self.proxy()
        while not proxy.is_available():
            proxy.report_health_issue()
            time.sleep(0.1)
            proxy = self.proxy()

        return proxy.socks_address
