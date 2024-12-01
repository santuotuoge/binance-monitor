import random
import re
from datetime import datetime
import time

from playwright.async_api import async_playwright  # 使用异步版本
import asyncio

import requests

from app import SendMsg

count = 0
a = 0
# 定义多个代理 IP 信息
proxies = [

    {
        "ip": "127.0.0.1",
        "port": "8080",
        "username": "",
        "password": ""
    },
    # 添加更多代理...
]

# 设置请求头
headers = {

    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}

api_url = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=48&pageNo=1&pageSize=20"


processed_article_ids = set()


# 打印时加上时间戳
def log_with_time(message):
    """打印带时间戳的消息"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{current_time}: {message}")


# https://www.binance.com/en/support/announcement/binance-futures-will-launch-usd%E2%93%A2-margined-goatusdt-perpetual-contract-with-up-to-75x-leverage-ff1a4c64f1aa4fef870adc7ef802d700?hl=en

# 初始化时获取现有的文章ID
def initialize_processed_articles():
    """初始化时获取当前所有文章ID，避免启动时提醒已有文章"""
    try:
        response = requests.get(api_url)
        data = response.json()

        if data["code"] == "000000" and data["data"]:
            articles = data["data"]["catalogs"][0]["articles"]

            for article in articles:
                article_id = article["id"]
                # 记录当前已有的所有文章ID，启动时不做提醒
                processed_article_ids.add(article_id)

        log_with_time("Initialization complete. Monitoring new articles...")

    except Exception as e:
        log_with_time(f"Error during initialization: {e}")


# https://www.binance.com/en/support/announcement/d16d96c136154680a6373225d592bca1"

async def get_binace_token(proxy, url):
    token_ca = "ca:"
    try:
        async with async_playwright() as p:  # 使用 async_playwright 代替 sync_playwright
            if proxy["ip"] != "127.0.0.1":
                browser = await p.chromium.launch(
                    headless=True,
                    # 启动无头浏览器
                    proxy={
                        "server": f"http://{proxy['ip']}:{proxy['port']}",
                        "username": proxy['username'],
                        "password": proxy['password']
                    }
                )
            else:
                browser = await p.chromium.launch(
                    headless=True,
                )

            page = await browser.new_page()  # 新建页面
            await page.goto(url, timeout=100000)  # 访问网站

            # 获取页面内容
            content = await page.locator("div#support_article").text_content()
            # 获取标题中括号内的内容
            pairs = re.findall(r'\((.*?)\)', await page.title())
            pairs.append("Notes")

            # 查找包含 32-64 个字符的字母数字组合的地址

            contract_address = re.findall(r"[A-Za-z0-9]{32,64}", content)
            if contract_address:
                # 过滤出包含字母和数字的地址
                contract_address = [
                    addr for addr in contract_address
                    if re.search(r"[A-Za-z]", addr) and re.search(r"[0-9]", addr)
                ]

                # 替换 pairs 中的内容
                for i in range(len(contract_address)):
                    for pair in pairs:
                        contract_address[i] = contract_address[i].replace(pair, "")
                        print(contract_address[i])
                    token_ca += contract_address[i] + "  "

                print("Found contract address:", contract_address)

            await browser.close()  # 关闭浏览器
    except Exception as e:
        log_with_time(f"Error fetching or processing data: {e}")
    return token_ca


def get_articles(proxy):
    ip = proxy["ip"]
    port = proxy["port"]
    username = proxy["username"]
    password = proxy["password"]
    proxy_url = f"http://{username}:{password}@{ip}:{port}"

    # 获取币安上币公告
    response = requests.get(api_url, proxies={"http": proxy_url}, headers=headers)
    print(proxy)
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " response:" + str(response.status_code))
    if response.status_code == 429:
        time.sleep(1)
    data = response.json()

    if data["code"] == "000000" and data["data"]:
        articles = data["data"]["catalogs"][0]["articles"]
        for article in articles:
            article_id = article["id"]
            title = article["title"]
            # 如果文章ID之前没有处理过，并且标题中包含 "Launchpool"
            # 记录已处理过的文章ID
            html_content = ""
            # print(processed_article_ids)
            if article_id not in processed_article_ids:
                print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "start  新上币 article_id ：" + str(article_id))

                processed_article_ids.add(article_id)
                if "Will" in title:
                    data_title = "新上代币"
                    url_address = "https://www.binance.com/en/support/announcement/" + article["code"]
                    print(url_address)
                    # 提取合约地址
                    html_content = asyncio.run(get_binace_token(url=url_address, proxy=proxies[0]))
                    print(html_content)
                else:
                    html_content += title
                data = {
                    "group": "CEX",
                    "title": title,
                    "level": "timeSensitive",
                    "isArchive": "1",
                    "body": datetime.now().strftime("%d %H:%M:%S") + "\n" + html_content
                }

                asyncio.run(SendMsg(data=data, apiKey="your_key"))  # tt



if __name__ == '__main__':
    initialize_processed_articles()

    while (True):
        get_articles(proxies[random.randrange(0, (len(proxies) - 1))])

