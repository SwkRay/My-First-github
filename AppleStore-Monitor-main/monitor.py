# -*- coding: UTF-8 –*-
"""
@Author: LennonChin
@Contact: i@coderap.com
@Date: 2021-10-19
"""

import sys
import os
import random
import datetime
import requests
import json
import time
import hmac
import hashlib
import base64
import urllib.parse


class Utils:

    @staticmethod
    def time_title(message):
        return "[{}] {}".format(datetime.datetime.now().strftime('%H:%M:%S'), message)

    @staticmethod
    def log(message):
        print(Utils.time_title(message))

    @staticmethod
    def send_message(notification_configs, message, **kwargs):
        if len(message) == 0:
            return

        # Wrapper for exception caught
        def invoke(func, configs):
            try:
                func(configs, message, **kwargs)
            except Exception as err:
                Utils.log(err)

        # DingTalk message
        invoke(Utils.send_dingtalk_message, notification_configs["dingtalk"])

        # Bark message
        invoke(Utils.send_bark_message, notification_configs["bark"])

        # Telegram message
        invoke(Utils.send_telegram_message, notification_configs["telegram"])

    @staticmethod
    def send_dingtalk_message(dingtalk_configs, message, **kwargs):
        if len(dingtalk_configs["access_token"]) == 0 or len(dingtalk_configs["secret_key"]) == 0:
            return

        timestamp = str(round(time.time() * 1000))
        secret_enc = dingtalk_configs["secret_key"].encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, dingtalk_configs["secret_key"])
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

        headers = {
            'Content-Type': 'application/json'
        }

        params = {
            "access_token": dingtalk_configs["access_token"],
            "timestamp": timestamp,
            "sign": sign
        }

        content = {
            "msgtype": "text" if "message_type" not in kwargs else kwargs["message_type"],
            "text": {
                "content": message
            }
        }

        response = requests.post("https://oapi.dingtalk.com/robot/send", headers=headers, params=params, json=content)
        Utils.log("Dingtalk送出消息狀態：{}".format(response.status_code))

    @staticmethod
    def send_telegram_message(telegram_configs, message, **kwargs):
        if len(telegram_configs["bot_token"]) == 0 or len(telegram_configs["chat_id"]) == 0:
            return

        headers = {
            'Content-Type': 'application/json'
        }

        proxies = {
            "https": telegram_configs["http_proxy"],
        }

        content = {
            "chat_id": telegram_configs["chat_id"],
            "text": message
        }

        url = "https://api.telegram.org/bot{}/sendMessage".format(telegram_configs["bot_token"])
        response = requests.post(url, headers=headers, proxies=proxies, json=content)
        Utils.log("Telegram送出消息狀態：{}".format(response.status_code))

    @staticmethod
    def send_bark_message(bark_configs, message, **kwargs):
        if len(bark_configs["url"]) == 0:
            return

        url = "{}/{}".format(bark_configs["url"], urllib.parse.quote(message, safe=""))
        response = requests.post(url, params=bark_configs["query_parameters"])
        Utils.log("Bark送出消息狀態：{}".format(response.status_code))


class AppleStoreMonitor:
    headers = {
        'sec-ch-ua': '"Google Chrome";v="93", " Not;A Brand";v="99", "Chromium";v="93"',
        'Referer': 'https://www.apple.com.cn/store',
        'DNT': '1',
        'sec-ch-ua-mobile': '?0',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
        'sec-ch-ua-platform': '"macOS"',
    }

    def __init__(self):
        self.count = 1

    @staticmethod
    def config():
        """
        進行各類操作
        """
        products = json.load(open('products.json', encoding='utf-8'))

        configs = {
            "selected_products": {},
            "selected_area": "",
            "exclude_stores": [],
            "notification_configs": {
                "dingtalk": {
                    "access_token": "",
                    "secret_key": ""
                },
                "telegram": {
                    "bot_token": "",
                    "chat_id": "",
                    "http_proxy": ""
                },
                "bark": {
                    "url": "",
                    "query_parameters": {
                        "url": None,
                        "isArchive": None,
                        "group": None,
                        "icon": None,
                        "automaticallyCopy": None,
                        "copy": None
                    }
                }
            },
            "scan_interval": 30,
            "alert_exception": False
        }

        while True:
            # chose product type
            print('--------------------')
            for index, item in enumerate(products):
                print('[{}] {}'.format(index, item))
            product_type = list(products)[int(input('選擇要查的型號：'))]

            # chose product classification
            print('--------------------')
            for index, (key, value) in enumerate(products[product_type].items()):
                print('[{}] {}'.format(index, key))
            product_classification = list(products[product_type])[int(input('選擇要查的型號子類：'))]

            # chose product classification
            print('--------------------')
            for index, (key, value) in enumerate(products[product_type][product_classification].items()):
                print('[{}] {}'.format(index, value))
            product_model = list(products[product_type][product_classification])[int(input('選擇要查的IPHONE型號：'))]

            configs["selected_products"][product_model] = (
                product_classification, products[product_type][product_classification][product_model])

            print('--------------------')
            if len(input('是否增加更產品[Enter繼續添加，非Enter鍵退出]：')) != 0:
                break

        # config area
        print('選擇預約地址：')
        url_param = ['state', 'city', 'district']
        choice_params = {}
        param_dict = {}
        for step, param in enumerate(url_param):
            print('請稍後...{}/{}'.format(step + 1, len(url_param)))
            response = requests.get("https://www.apple.com.cn/shop/address-lookup", headers=AppleStoreMonitor.headers,
                                    params=choice_params)
            result_param = json.loads(response.text)['body'][param]
            if type(result_param) is dict:
                result_data = result_param['data']
                print('--------------------')
                for index, item in enumerate(result_data):
                    print('[{}] {}'.format(index, item['value']))
                input_index = int(input('請選擇區號：'))
                choice_result = result_data[input_index]['value']
                param_dict[param] = choice_result
                choice_params[param] = param_dict[param]
            else:
                choice_params[param] = result_param

        print('正在載入網絡資源...')
        response = requests.get("https://www.apple.com.cn/shop/address-lookup", headers=AppleStoreMonitor.headers,
                                params=choice_params)
        selected_area = json.loads(response.text)['body']['provinceCityDistrict']
        configs["selected_area"] = selected_area

        print('--------------------')
        print("選擇預約地址是：{}，載入預約地止周圍直營店...".format(selected_area))

        store_params = {
            "location": selected_area,
            "parts.0": list(configs["selected_products"].keys())[0]
        }
        response = requests.get("https://www.apple.com.cn/shop/fulfillment-messages",
                                headers=AppleStoreMonitor.headers, params=store_params)

        stores = json.loads(response.text)['body']["content"]["pickupMessage"]["stores"]
        for index, store in enumerate(stores):
            print("[{}] {}，地址：{}".format(index, store["storeName"], store["retailStore"]["address"]["street"]))

        exclude_stores_indexes = input('排除無需監測的直營店，輸入序號输[直接Enter代表全部監測，多個店序號以空格分隔]：').strip().split()
        if len(exclude_stores_indexes) != 0:
            print("已選擇的無需監測直店：{}".format("，".join(list(map(lambda i: stores[int(i)]["storeName"], exclude_stores_indexes)))))
            configs["exclude_stores"] = list(map(lambda i: stores[int(i)]["storeNumber"], exclude_stores_indexes))

        print('--------------------')
        # config notification configurations
        notification_configs = configs["notification_configs"]

        # config dingtalk notification
        dingtalk_access_token = input('输入釘釘機器人Access Token[如不配置直接Enter即可]：')
        dingtalk_secret_key = input('输入釘釘機器人Secret Key[如不配置直接Enter即可]：')

        # write dingtalk configs
        notification_configs["dingtalk"]["access_token"] = dingtalk_access_token
        notification_configs["dingtalk"]["secret_key"] = dingtalk_secret_key

        # config telegram notification
        print('--------------------')
        telegram_chat_id = input('输入Telegram机器人Chat ID[如不配置直接Enter即可]：')
        telegram_bot_token = input('输入Telegram机器人Token[如不配置直接Enter即可]：')
        telegram_http_proxy = input('输入Telegram HTTP代理地址[如不配置直接Enter即可]：')

        # write telegram configs
        notification_configs["telegram"]["chat_id"] = telegram_chat_id
        notification_configs["telegram"]["bot_token"] = telegram_bot_token
        notification_configs["telegram"]["http_proxy"] = telegram_http_proxy

        # config bark notification
        print('--------------------')
        bark_url = input('输入Bark URL[如不配置直接Enter即可]：')

        # write dingtalk configs
        notification_configs["bark"]["url"] = bark_url

        # 輸入掃瞄間隔時間
        print('--------------------')
        configs["scan_interval"] = int(input('输入掃瞄間隔時間[以秒為單位，默認為30秒，如不配置直接Enter即可]：') or 30)

        # 是否對異常進行警告
        print('--------------------')
        configs["alert_exception"] = (input('是否在程序異常時發出通知[Y/n，默認為n]：').lower().strip() or "n") == "y"

        with open('apple_store_monitor_configs.json', 'w') as file:
            json.dump(configs, file, indent=2)
            print('--------------------')
            print("掃瞄配置己生成，並已寫入到{}文件中\n请使用 python {} start 命令始動監測".format(file.name, os.path.abspath(__file__)))

    def start(self):
        """
        開始監測
        """
        configs = json.load(open('apple_store_monitor_configs.json', encoding='utf-8'))
        selected_products = configs["selected_products"]
        selected_area = configs["selected_area"]
        exclude_stores = configs["exclude_stores"]
        notification_configs = configs["notification_configs"]
        scan_interval = configs["scan_interval"]
        alert_exception = configs["alert_exception"]

        products_info = []
        for index, product_info in enumerate(selected_products.items()):
            products_info.append("【{}】{}".format(index, " ".join(product_info[1])))
        message = "準備開始監測，商品信息如下：\n{}\n取貨區域：{}\n掃瞄頻次：{}秒/次".format("\n".join(products_info), selected_area,
                                                                   scan_interval)
        Utils.log(message)
        Utils.send_message(notification_configs, message)

        params = {
            "location": selected_area,
            "mt": "regular",
        }

        code_index = 0
        product_codes = selected_products.keys()
        for product_code in product_codes:
            params["parts.{}".format(code_index)] = product_code
            code_index += 1

        # 上次整點通知時間
        last_exactly_time = -1
        while True:
            available_list = []
            tm_hour = time.localtime(time.time()).tm_hour
            try:
                # 更新請求時間
                params["_"] = int(time.time() * 1000)

                response = requests.get("https://www.apple.com.cn/shop/fulfillment-messages",
                                        headers=AppleStoreMonitor.headers,
                                        params=params)

                json_result = json.loads(response.text)
                stores = json_result['body']['content']['pickupMessage']['stores']
                Utils.log(
                    '-------------------- 第{}次掃瞄 --------------------'.format(
                        self.count + 1))
                for item in stores:
                    store_name = item['storeName']
                    if item["storeNumber"] in exclude_stores:
                        print("【{}：已排除】".format(store_name))
                        continue
                    print("{:-<100}".format("【{}】".format(store_name)))
                    for product_code in product_codes:
                        pickup_search_quote = item['partsAvailability'][product_code]['pickupSearchQuote']
                        pickup_display = item['partsAvailability'][product_code]['pickupDisplay']
                        store_pickup_product_title = item['partsAvailability'][product_code]['storePickupProductTitle']
                        print('\t【{}】{}'.format(pickup_search_quote, store_pickup_product_title))
                        if pickup_search_quote == '今天可取貨' or pickup_display != 'unavailable':
                            available_list.append((store_name, product_code, store_pickup_product_title))

                if len(available_list) > 0:
                    messages = []
                    print("命中貨源，請注意 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                    Utils.log("以下直營店預約可用：")
                    for item in available_list:
                        messages.append("【{}】 {}".format(item[0], item[2]))
                        print("【{}】{}".format(item[0], item[2]))
                    print("命中貨源，請注意 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

                    Utils.send_message(notification_configs,
                                       Utils.time_title(
                                           "第{}次掃瞄到直營店有貨，信息如下：\n{}".format(self.count, "\n".join(messages))))

            except Exception as err:
                Utils.log(err)
                # 6:00 ~ 23:00才发送异常消息
                if alert_exception and 6 <= tm_hour <= 23:
                    Utils.send_message(notification_configs,
                                       Utils.time_title("第{}次掃瞄到出現異常：{}".format(self.count, repr(err))))

            if len(available_list) == 0:
                interval = max(random.randint(int(scan_interval / 2), scan_interval * 2), 5)
                Utils.log('{}秒後進行第{}次嘗試...'.format(interval, self.count))

                # 整点通知，用于阶段性检测应用是否正常
                if last_exactly_time != tm_hour and (6 <= tm_hour <= 23):
                    Utils.send_message(notification_configs,
                                       Utils.time_title("已掃瞄{}次，掃瞄程序運作正常".format(self.count)))
                    last_exactly_time = tm_hour
                time.sleep(interval)
            else:
                time.sleep(5)

            # 次数自增
            self.count += 1


if __name__ == '__main__':
    args = sys.argv

    if len(args) != 2:
        print("""
        Usage: python {} <option>
        option can be:
        \tconfig: pre config of products or notification
        \tstart: start to monitor
        """.format(args[0]))
        exit(1)

    if args[1] == "config":
        AppleStoreMonitor.config()

    if args[1] == "start":
        AppleStoreMonitor().start()
