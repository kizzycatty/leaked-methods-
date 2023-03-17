from flask import request
from capmonster_python import HCaptchaTask
import yaml, threading, flask, requests, httpx
import time
from colorama import Fore
from discord_webhook import DiscordWebhook

class sellix_api:
    app = flask.Flask(__name__)

    def __init__(self) -> None:
        self.done = 0
        self.session = httpx.Client()
        self.config = yaml.load(open("config.yml", 'r'), Loader=yaml.FullLoader)
        self.orders = []
        self.capmonster = self.config["crapmonster_key"]

        self.__14__ = self.config.get("14_boosts")
        self.__8__ = self.config.get("8_boosts")
        self.__4__ = self.config.get("4_boosts")
        self.__custom__ = self.config.get("custom_amount")

        self.bioner = self.config.get("bio")
        self.usener = self.config.get("guild_nick")

        self.cbio = bool(self.config["change_bio"])
        self.cuser = bool(self.config["change_server_nick"])
    
        self.products = {
            self.__14__: 14,
            self.__8__: 8,
            self.__4__: 4,
            self.__custom__: "custom"
        }
    def logging(content: str, status: bool):
        timess = time.strftime("%H:%M:%S")
        status = f"({Fore.GREEN}+{Fore.RESET}) " if status else f"({Fore.RED}-{Fore.RESET}) "
        print(f"{Fore.RESET}[{timess}] {status}{content}{Fore.RESET}")

    @app.route("/sellix", methods=["GET", "POST"])
    def boosts(self):
        data = request.json
        if data in self.orders:    
            pass
        elif data not in self.orders:
            threading.Thread(target=self.start, args=[data]).start()
            self.orders.append(data)
        return '{"status": "received"}', 200

    def start(self, data):
        self.order_ID = data["data"]["uniqid"]
        self.product = data["data"]["product_title"]
        self.email = data["data"]["customer_email"]
        self.quantity = data["data"]["quantity"]
        self.name_2 = self.config["user_field_name"]
        self.user = data["data"]["custom_fields"][self.name_2]
        try:
            self.name = self.config["field_name"]
            if data["event"] == "order:paid":
                look = data["data"]["product_id"]
                self.amount = self.products[str(look)]
                if amount == "custom":
                    amount = data["data"]["quantity"]
                self.invite = data["data"]["custom_fields"][self.name].replace("https://discord.gg/", "")

            INVITE = self.invite.replace("//", "")
            if "/invite/" in INVITE:
                INVITE = INVITE.split("/invite/")[1]
            elif "/" in INVITE:
                INVITE = INVITE.split("/")[1]
            self.logging(f"Boosting {INVITE} x{amount} times", True)
            go = time.time()
            self.boost(INVITE, amount)
            end = time.time()
            time_went = round(end - go, 5)
            webhook = DiscordWebhook(url=self.config["webhook_boost_logs"], content=f'Thank you for purchasing <@{int(self.user)}>!\n Ive finished boosting your server x{self.done} times in {time_went}s')
            webhook.execute()
        except:
            self.logging(f"New Sell: {self.product} | Amount: {self.quantity}", False)
        
    def remove(self, token: str):
        with open(f'tokens.txt', "r") as f:
            Tokens = f.read().split("\n")
            for t in Tokens:
                if len(t) < 5 or t == token:
                    Tokens.remove(t)
            open(f'tokens.txt', "w").write("\n".join(Tokens))

    def boost(self, invite: str, amount: int):
        self.done = 0
        self.invite = invite
        for token in open('tokens.txt', 'r').read().splitlines():
            if self.done >= amount:
                return
            self.headers = self.get_headers(token)
            boost_data = self.session.get(f"https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots", headers=self.headers)
            if boost_data.status_code == 200:
                if len(boost_data.json()) != 0:
                    joined = self.join(invite)
                    if joined:
                        self.logging(f"Joined server: {token}", True)
                        for boost in boost_data.json():
                            if self.done >= amount:
                                self.remove(token)
                            boost_id = boost["id"]
                            bosted = self.do_boost(boost_id)
                            if bosted:
                                self.logging(f"Successfully Boosted: {token}", True)
                                self.done += 1
                            else:
                                self.logging(f"Boost Used Or some other error: {token}", False)
                        if self.cbio:
                            self.change_bio()
                        if self.cuser:
                            self.change_guild_name()    
                        self.remove(token)
                    else:   
                        self.logging(f"Error Joining: {token}", False)
                else:
                    self.remove(token)
                    self.logging(f"Token Doesnt have nitro: {token}", False)

    def get_cookies(self):
        s = requests.Session()
        s.get("https://discord.com")
        cookies = s.cookies.get_dict()
        __dcfduid = cookies.get("__dcfduid")
        __sdcfduid = cookies.get("__sdcfduid")
        self.logging(f"Fetched Cookies: ({__dcfduid[:20]}), ({__sdcfduid[:20]})", True)
        s.close()
        return __dcfduid, __sdcfduid

    def get_fingerprint(self):
        data = self.session.get("https://discord.com/api/v9/experiments")
        fingerprint = data.json()['fingerprint']
        self.logging(f"Got Fingerprint: ({fingerprint})", True)
        return fingerprint


    def get_headers(self, token):
        __dcfduid, __sdcfduid = self.get_cookies()
        headers = {
                'accept': '*/*',
                'accept-encoding': 'gzip, deflate',
                'accept-language': 'en-GB',
                'authorization': token,
                'content-type': 'application/json',
                'origin': 'https://discord.com',
                'referer': 'https://discord.com/channels/@me',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'cookie': f'__dcfduid={__dcfduid}; __sdcfduid={__sdcfduid}; locale=en-GB',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/0.1.9 Chrome/83.0.4103.122 Electron/9.4.4 Safari/537.36',
                'x-debug-options': 'bugReporterEnabled',
                'x-fingerprint': self.get_fingerprint(),
                'x-context-properties': 'eyJsb2NhdGlvbiI6IlVzZXIgUHJvZmlsZSJ9',
                'x-super-properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjAuMS45Iiwib3NfdmVyc2lvbiI6IjEwLjAuMTc3NjMiLCJvc19hcmNoIjoieDY0Iiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiY2xpZW50X2J1aWxkX251bWJlciI6OTM1NTQsImNsaWVudF9ldmVudF9zb3VyY2UiOm51bGx9',
                'te': 'trailers',
            }
        return headers

    def solve(self, sitekey):
        cap = HCaptchaTask(self.capmonster)
        task = cap.create_task("https://discord.com/channels/@me", sitekey)
        for i in range(10):
            try:
                solution = cap.get_task_result(task)["gRecaptchaResponse"]
                self.logging(f"Solved Captcha: ({solution[:75]}...)", True)
                break
            except TypeError:
                continue
        return solution

    def join(self, invite):
        self.headers["content-type"] = 'application/json'
        r = self.session.post(f"https://discord.com/api/v9/invites/{invite}", headers=self.headers, json={})
        if r.status_code == 200:
            self.guild_id = r.json()["guild"]["id"]
            join_outcome = True
        if "captcha_sitekey" in r.text:
            sitekey = r.json()['captcha_sitekey']
            solution = self.solve(sitekey)
            r = self.session.post(f"https://discord.com/api/v9/invites/{invite}", headers=self.headers, json={"captcha_key": solution})
            if r.status_code == 200:
                self.guild_id = r.json()["guild"]["id"]
                join_outcome = True
            else:
                self.logging(r.text, False)
            
        return join_outcome

    def do_boost(self, boost_id):
        boost_data = {"user_premium_guild_subscription_slot_ids": [boost_id]}
        boosted = self.session.put(f"https://discord.com/api/v9/guilds/{self.guild_id}/premium/subscriptions", json=boost_data, headers=self.headers)
        if boosted.status_code == 201:
            return True
        else:
            return False

    def change_bio(self):
        r = self.session.patch("https://discord.com/api/v9/users/@me", headers=self.headers, json = {'bio': self.bioner})
        if r.status_code == 200:
            self.logging(f"Renamed Bio to {self.bioner}", True)
        else:
            self.logging(f"Couldn't rename bio: {r.json()}", False)

    def change_guild_name(self):
        r = self.session.patch(f"https://discord.com/api/v9/guilds/{self.guild_id}/members/@me", headers=self.headers, json={"nick": self.usener})
        if r.status_code == 200:
            self.logging(f"Renamed user to {self.usener}", True)
        else:
            self.logging(f"Couldn't rename user: {r.json()}", False)

    app.run(host="0.0.0.0", port="6969", debug=True)
