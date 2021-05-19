# reddit_account_automation_tools

```
pip install -r requirements.txt
```

The only thing functioning so far is create_accounts.py, which autonomously creates reddit accounts.
Make ".env-example" ".env" and enter the relevant details, you don't need a temp-mail.org API key, however with one it will verify the email of accounts. You do however need an API key from https://anti-captcha.com/ for obvious reasons.

If none of the proxies in "working_proxies.txt" currently work, you can run ./proxy/find_working.py to parse ones which are from the ~400 or so in socks5.csv & socks5_2.csv, alternatively you can add your own to ./proxy/proxy_files/working_proxies.txt.

I wrote this in a few hours and have not tested it thoroughly yet fwiw.

You'll need Python 3.9 unless you want to edit all of the walrus operator uses.
