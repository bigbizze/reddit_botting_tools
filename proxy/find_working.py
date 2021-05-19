import math
import multiprocessing as mp
from concurrent.futures.thread import ThreadPoolExecutor
from multiprocessing.queues import Queue
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

from proxy.socks_proxy import ProxyRequest
from scrape.create_accounts import get_new_webdriver


def get_webdriver_at_reddit(*args):
    address, address_status_queue = args[0]
    driver = None
    try:
        driver = get_new_webdriver(address, _headless=True)
        driver.get(r"https://www.reddit.com/account/register/")
        driver.find_element_by_class_name("neterror")
    except NoSuchElementException:
        try:
            driver.find_element_by_css_selector(r"body > div > main > div:nth-child(1) > div > div.Step__content > form > h1")
            driver.implicitly_wait(45)
            address_status_queue.put({"address": address, "is_working": True})
            try:
                driver.close()
            except WebDriverException:
                pass
            return
        except NoSuchElementException:
            pass
    except (TimeoutException, WebDriverException):
        pass
    address_status_queue.put({"address": address, "is_working": False})
    if driver is not None:
        try:
            driver.close()
        except WebDriverException:
            pass


def proc_do(max_workers, _addresses, address_status_queue: Queue):
    _addresses = zip(_addresses, [address_status_queue for _ in range(len(_addresses))])
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(get_webdriver_at_reddit, _addresses))
    address_status_queue.put("DONE")


def get_results(num_procs, num_proxies, address_status_queue: Queue):
    working = []
    broken = []
    num_finished = 0
    addresses_finished = 0
    while True:
        res = address_status_queue.get(block=True)
        if addresses_finished % (num_proxies // 100) == 0:
            print(f"{addresses_finished / num_proxies * 100}%")
        addresses_finished += 1
        if res == "DONE":
            num_finished += 1
            if num_finished == num_procs:
                with open("working_proxies.txt", "w") as fp:
                    fp.write("\n".join(working))
                with open("broken_proxies.txt", "w") as fp:
                    fp.write("\n".join(broken))
                print("Finished!")
                exit(0)
        elif isinstance(res, dict) and "is_working" in res:
            if res["is_working"]:
                working.append(res["address"])
            else:
                broken.append(res["address"])


def find_working_proxies():
    """ Find proxies in lists which work & connect to reddit in a reasonable amount of time
    """
    num_cpu = 2
    num_threads_per_cpu = 12
    pr = ProxyRequest()
    proxies = [x.address for x in pr.handler.proxies]
    divisor = math.ceil(len(proxies) / num_cpu)
    queue = mp.Queue()
    get_webdriver_at_reddit((proxies[0], queue))
    procs = [
        mp.Process(target=get_results, args=(num_cpu, len(proxies), queue,))
    ]
    for i in range(num_cpu):
        procs.append(mp.Process(target=proc_do, args=(num_threads_per_cpu, proxies[i * divisor: (i + 1) * divisor], queue,)))
    [x.start() for x in procs]
    [x.join() for x in procs]
    # queue.put("DONE")
    [x.close() for x in procs]


if __name__ == '__main__':

    find_working_proxies()









