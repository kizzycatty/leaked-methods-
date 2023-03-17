
import discord, json, requests, os, httpx, base64, time, datetime
from discord import option
from colorama import Fore, init

settings = json.load(open("settings.json", encoding="utf-8"))
bot = discord.Bot(intents=discord.Intents.all(), debug_guilds=[int(settings['guildId'])])

cardstart = "485953"

#@bot.slash_command()
# DEPRECATED IN FAVOR OF SLASH COMMANDS
async def help(ctx):
    em = discord.Embed(title='Hydra Boost commands list', description='Can only be used by admins!', color=0xe91e63)
    em.add_field(name='Boost a Server',value='`hb-boost <server invite> <number of boosts *even only*>`', inline=False)
    em.add_field(name='View the Stock',value='`hb-stock`', inline=False)
    em.add_field(name='Admin Someone',value='`hb-admin <user>`', inline=False)
    em.add_field(name='Whitelist Someone',value='`hb-whitelist <user>`', inline=False)
    em.add_field(name='Check the Tokens',value='`hb-checktokens`', inline=False)
    em.add_field(name='Check User Perms',value='`hb-checkperms (user)`', inline=False)
    em.add_field(name='Change the activity',value='`hb-activity <something>`', inline=False)
    return await ctx.respond(embed=em)


@bot.event
async def on_ready():
    if not cardstart == "485953":
        raise SystemExit
    print('Bot ready')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=settings['botStatus']))

def isAdmin(ctx):
    return str(ctx.author.id) in settings["botAdminId"]


def isWhitelisted(ctx):
    return str(ctx.author.id) in settings["botWhitelistedId"]

@bot.event
async def on_message(message):
    if message.guild is None and message.author != bot.user and message.content.startswith('restock\n') and isWhitelisted(message):
        with open('tokens.txt', 'a') as f:
            f.write(message.content.replace('restock\n',''))
        await message.channel.send('Restocked!')

def removeToken(token: str):
    with open('tokens.txt', "r") as f:
        Tokens = f.read().split("\n")
        for t in Tokens:
            if len(t) < 5 or t == token:
                Tokens.remove(t)
        open("tokens.txt", "w").write("\n".join(Tokens))
    with open('used.txt', 'a') as f:
        f.write(token+'\n')


async def runboost(ctx, invite: str, amount: int):
    if amount % 2 != 0:
        amount += 1
    print(amount)
    tokens = get_all_tokens("tokens.txt")
    all_data = []
    tokens_checked = 0
    actually_valid = 0
    boosts_done = 0
    await ctx.send(embed=discord.Embed(title='Checking tokens...'))
    for token in tokens:
        s, headers = get_headers(token)
        profile = validate_token(s, headers)
        tokens_checked += 1

        if profile != False:
            boost_data = requests.get(f"https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots", headers={'Authorization': token})
            jsx = json.loads(boost_data.text)
            co=0
            for i in jsx:
                
                if i['cooldown_ends_at'] == None:
                    co+=1
                else:
                    expr = datetime.datetime.strptime(i['cooldown_ends_at'],'%Y-%m-%dT%H:%M:%S.%f%z')
                    timeTill = expr - datetime.datetime.now(datetime.timezone.utc)
                    timeTill = str(timeTill).split('.')[0]
                    if '-' in timeTill:
                        co+=1
            if co != 2:
                print(f"{Fore.RED} > {Fore.WHITE}{profile} Cooldown detected!")
            actually_valid += 1
            data_piece = [s, token, headers, profile]
            all_data.append(data_piece)
            print(f"{Fore.GREEN} > {Fore.WHITE}{profile}")
        else:
            pass
        if actually_valid-2 == amount/2:
            break
    capTasks = []
    solutions = []
    msg = await ctx.send(embed=discord.Embed(title='Solving Captcha',description='Waiting for output...', color=0xe67e22))
    for i in range(int(amount/2)):
        createTask = httpx.post("https://api.capmonster.cloud/createTask", json={
                        "clientKey": settings["capmonsterKey"],
                        "task": {
                            "type": "HCaptchaTaskProxyless",
                            "websiteURL": "https://discord.com/channels/@me",
                            "websiteKey": '4c672d35-0701-42b2-88c3-78380b0db560'
                        }
                    }).json()["taskId"]
        print(f"Captcha Task: {createTask}")
        capTasks.append(createTask)
    for task in capTasks:
        getResults = {}
        getResults["status"] = "processing"
        while getResults["status"] == "processing":
            print('Waiting on cap...')
            getResults = httpx.post("https://api.capmonster.cloud/getTaskResult", json={
                "clientKey": settings["capmonsterKey"],
                "taskId": task
            }).json()
            time.sleep(0.3)
    
        solution = getResults["solution"]["gRecaptchaResponse"]
        solutions.append(solution)
        print(f"Received {task}")
    await msg.edit(embed=discord.Embed(title='Solving Captcha',description=f'Captcha Solved! Got {len(solutions)} solution(s)', color=0x2ecc71))
    for data in all_data:
        if boosts_done >= amount:
            return
        s, token, headers, profile = get_items(data)
        boost_data = s.get(f"https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots", headers=headers)
        if boost_data.status_code == 200:
            if len(boost_data.json()) != 0:
                solution = solutions[0]
                
                join_outcome, server_id, server_name = await do_join_server(ctx, s, token, headers, profile, invite, solution)
                solutions.pop(0)
                token_boosts = 0
                if join_outcome:
                    for boost in boost_data.json():

                        if boosts_done >= amount:
                            removeToken(token)
                            return
                        boost_id = boost["id"]
                        bosted = do_boost(s, token, headers, profile, server_id, boost_id)
                        if bosted:
                            print(f"{Fore.GREEN} > {Fore.WHITE}{profile} {Fore.MAGENTA}BOOSTED {Fore.WHITE}{server_name}")
                            boosts_done += 1
                            token_boosts += 1
                        else:
                            print(f"{Fore.GREEN} > {Fore.WHITE}{profile} {Fore.RED}ERROR BOOSTING {Fore.WHITE}{server_name}")
                    removeToken(token)
                    if token_boosts == 2:
                    	await ctx.send(embed=discord.Embed(title='Sucessful Boost!', description=f'{profile} boosted {server_name} twice!', color=0xEB459E))
                    else:
                        await ctx.send(embed=discord.Embed(title='Failed Boost!', description=f'{profile} could not boosted {server_name}!', color=0xe74c3c))
                else:
                    print(f"{Fore.RED} > {Fore.WHITE}{profile} {Fore.RED}Error joining {invite}")

            else:
                removeToken(token)
                print(f"{Fore.GREEN} > {Fore.WHITE}{profile} {Fore.RED}NO NITRO ON TOKEN!")

@bot.slash_command(description='Check all the tokens')
async def checktokens(ctx):
    if not isWhitelisted(ctx):
        return await ctx.respond("*Only whitelisted users can use this command.*")
    await ctx.respond(embed=discord.Embed(title='Checking tokens...'))
    tokens = get_all_tokens("tokens.txt")
    tokens_checked = 0
    actually_valid = 0
    on_co = 0
    is_boosting = 0
    invalid = 0
    for token in tokens:
        s, headers = get_headers(token)
        profile = validate_token(s, headers)
        tokens_checked += 1
        
        if profile != False:
            boost_data = requests.get(f"https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots", headers={'Authorization': token})
            jsx = json.loads(boost_data.text)
            co=0
            jr=0
            for i in jsx:
                
                if i['cooldown_ends_at'] == None:
                    co+=1
                else:
                    expr = datetime.datetime.strptime(i['cooldown_ends_at'],'%Y-%m-%dT%H:%M:%S.%f%z')
                    timeTill = expr - datetime.datetime.now(datetime.timezone.utc)
                    timeTill = str(timeTill).split('.')[0]
                    if '-' in timeTill:
                        co+=1 
                if i['premium_guild_subscription']:
                    jr+=1
            if co != 2:
                print(f"{Fore.RED} > {Fore.WHITE}{profile} Cooldown detected!")
                on_co += 1
            else:
                actually_valid += 1
            if jr ==2:
                is_boosting+=1
            print(f"{Fore.GREEN} > {Fore.WHITE}{profile}")
        else:
            invalid += 1
    await ctx.edit(embed=discord.Embed(title='Checking Finished',color=0x7289da).add_field(name='Results',value=f'Checked `{tokens_checked}` tokens\nAble to boost: `{actually_valid-is_boosting}`\nIs already boosting: `{is_boosting}`\nOn Cooldown: `{on_co}`\nInvalid: `{invalid}`'))
@bot.slash_command(description='Whitelist someone')
@option('user', type=discord.Member, description='User to whitelist')
async def whitelist(ctx, user):
    if not isAdmin(ctx):
        return await ctx.respond("*Only Bot Admins can use this command.*")

    settings["botWhitelistedId"].append(str(user.id))
    json.dump(settings, open("settings.json", "w", encoding="utf-8"), indent=4)

    return await ctx.respond(f"*{user.mention} has been whitelisted.*")
@bot.slash_command(description='Admin someone')
@option('user', type=discord.Member, description='User to admin')
async def admin(ctx, user):
    if not isAdmin(ctx):
        return await ctx.respond("*Only Bot Admins can use this command.*")

    settings["botAdminId"].append(str(user.id))
    json.dump(settings, open("settings.json", "w", encoding="utf-8"), indent=4)

    return await ctx.respond(f"*{user.mention} has been added to the admin list.*")

@bot.slash_command(description='Check the current stock')
async def stock(ctx):
    if not isWhitelisted(ctx):
        return await ctx.respond("*Only whitelisted users can use this command.*")
    rawstock = len(open('tokens.txt', encoding='utf-8').read().splitlines())
    return await ctx.respond(embed=discord.Embed(
        title='Current Nitro Stock', description=f"*Current Nitro Tokens Stock:* `{rawstock}`\n*which is* `{rawstock*2}` *boosts*", color=0xEB459E))

@bot.slash_command(description='Check the bot perms of an user')
@option('user', type=discord.Member, description='The user to check perms of',default=None)
async def checkperms(ctx, user):
    if not user:
        user = ctx.author
    resString = ''
    if str(user.id) in settings['botWhitelistedId']:
        resString = "*User is whitelisted*\n"
    if str(user.id) in settings['botAdminId']:
        resString = resString + "*User is admin*\n"
    if not str(user.id) in settings['botWhitelistedId'] and not str(user.id) in settings['botAdminId']:
        resString = "*User does not have any bot perms*"
    await ctx.respond(resString)
@bot.slash_command(description='Set the bot activity')
@option('act', description='The name of the activity')
async def activity(ctx, act):
    if not isWhitelisted(ctx):
        return await ctx.respond("*Only whitelisted users can use this command.*")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=act))
    settings['botStatus'] = act
    with open('settings.json', 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)
    await ctx.respond('Done!')

@bot.slash_command(description='Instructions on how to restock')
async def restock(ctx):
    if not isWhitelisted(ctx):
        return await ctx.respond("*Only whitelisted users can use this command.*")
    await ctx.respond('To restock, dm me the tokens in such a way: say `restock`, then make a line with shift+enter and put in the tokens. Must be one message and each token must be on a seperate line')

@bot.slash_command(description='Get the payment methods')
async def pay(ctx):
    eme = discord.Embed(title='Payment Methods', description='When buying, pay to these payment methods', color=0xEB459E)
    eme.add_field(name='Paypal', value=settings['paypalLink'])
    eme.add_field(name='Cashapp', value=settings['cashappId'])
    await ctx.respond(embed=eme)

@bot.slash_command(description='Calculate')
@option('statement', description='The statement to solve')
async def calc(ctx, statement: str):
    var = statement
    var = var.replace('x','*').replace('^','**')
    if ';' in var:
        return await ctx.respond('Not a valid statement')
    try:
        result = eval(var)
    except Exception as e:
        print(e)
        return await ctx.respond('I cannot solve that!')
    await ctx.respond(f'{var} = {result}')

@bot.slash_command(description='Boost a server')
@option('invitecode', description='The server to boost')
@option('amount', description='Amount of boosts to send')
async def boost(ctx, invitecode: str,
                amount: int):
    if not isAdmin(ctx):
        return await ctx.respond("*Only Bot Admins can use this command.*")

    em = discord.Embed(title='Started', color=16776960)
    await ctx.respond(embed=em)

    INVITE = invitecode.replace("//", "")
    if "/invite/" in INVITE:
        INVITE = INVITE.split("/invite/")[1]

    elif "/" in INVITE:
        INVITE = INVITE.split("/")[1]
    print(INVITE)
    dataabotinvite = httpx.get(f"https://discord.com/api/v9/invites/{INVITE}").text
    if '{"message": "Unknown Invite", "code": 10006}' in dataabotinvite:
        print(f"{Fore.RED}discord.gg/{INVITE} is invalid")
        return await ctx.channel.send(embed=discord.Embed(title="The Invite link you provided is invalid!", color=0xe74c3c))
    else:
        print(f"{Fore.GREEN}discord.gg/{INVITE} appears to be a valid server")

    await runboost(ctx.channel, INVITE, amount)


    em = discord.Embed(title='Finished!',color=3066993)
    await ctx.channel.send(embed=em)


def get_super_properties():
    properties = '''{"os":"Windows","browser":"Chrome","device":"","system_locale":"en-GB","browser_user_agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36","browser_version":"95.0.4638.54","os_version":"10","referrer":"","referring_domain":"","referrer_current":"","referring_domain_current":"","release_channel":"stable","client_build_number":102113,"client_event_source":null}'''
    properties = base64.b64encode(properties.encode()).decode()
    return properties


def get_fingerprint(s):
    try:
        fingerprint = s.get(f"https://discord.com/api/v9/experiments", timeout=5).json()["fingerprint"]
        return fingerprint
    except Exception as e:
        print(e)
        return "Error"


def get_cookies(s, url):
    try:
        cookieinfo = s.get(url, timeout=5).cookies
        dcf = str(cookieinfo).split('__dcfduid=')[1].split(' ')[0]
        sdc = str(cookieinfo).split('__sdcfduid=')[1].split(' ')[0]
        return dcf, sdc
    except:
        return "", ""


def get_proxy():
    return None  # can change if problems occur


def get_headers(token):
    while True:
        s = httpx.Client(proxies=get_proxy())
        dcf, sdc = get_cookies(s, "https://discord.com/")
        fingerprint = get_fingerprint(s)
        if fingerprint != "Error":  # Making sure i get both headers
            break

    super_properties = get_super_properties()
    headers = {
        'authority': 'discord.com',
        'method': 'POST',
        'path': '/api/v9/users/@me/channels',
        'scheme': 'https',
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate',
        'accept-language': 'en-US',
        'authorization': token,
        'cookie': f'__dcfduid={dcf}; __sdcfduid={sdc}',
        'origin': 'https://discord.com',
        'sec-ch-ua': '"Google Chrome";v="95", "Chromium";v="95", ";Not A Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36',

        'x-debug-options': 'bugReporterEnabled',
        'x-fingerprint': fingerprint,
        'x-super-properties': super_properties,
    }

    return s, headers


def find_token(token):
    if ':' in token:
        token_chosen = None
        tokensplit = token.split(":")
        for thing in tokensplit:
            if '@' not in thing and '.' in thing and len(
                    thing) > 30:  # trying to detect where the token is if a user pastes email:pass:token (and we dont know the order)
                token_chosen = thing
                break
        if token_chosen == None:
            print(f"Error finding token", Fore.RED)
            return None
        else:
            return token_chosen


    else:
        return token


def get_all_tokens(filename):
    all_tokens = []
    with open(filename, 'r') as f:
        for line in f.readlines():
            token = line.strip()
            token = find_token(token)
            if token != None:
                all_tokens.append(token)

    return all_tokens


def validate_token(s, headers):
    check = s.get(f"https://discord.com/api/v9/users/@me", headers=headers)

    if check.status_code == 200:
        profile_name = check.json()["username"]
        profile_discrim = check.json()["discriminator"]
        profile_of_user = f"{profile_name}#{profile_discrim}"
        return profile_of_user
    else:
        return False


def do_member_gate(s, token, headers, profile, invite, server_id):
    outcome = False
    try:
        member_gate = s.get(
            f"https://discord.com/api/v9/guilds/{server_id}/member-verification?with_guild=false&invite_code={invite}",
            headers=headers)
        if member_gate.status_code != 200:
            return outcome
        accept_rules_data = member_gate.json()
        accept_rules_data["response"] = "true"

        # del headers["content-length"] #= str(len(str(accept_rules_data))) #Had too many problems
        # del headers["content-type"] # = 'application/json'  ^^^^

        accept_member_gate = s.put(f"https://discord.com/api/v9/guilds/{server_id}/requests/@me", headers=headers,
                                   json=accept_rules_data)
        if accept_member_gate.status_code == 201:
            outcome = True

    except:
        pass

    return outcome


async def do_join_server(ctx, s, token, headers, profile, invite, solution):
    join_outcome = False;
    server_id = None
    try:
        # headers["content-length"] = str(len(str(server_join_data)))
        headers["content-type"] = 'application/json'

        for i in range(15):
            try:

                join_server = s.post(f"https://discord.com/api/v9/invites/{invite}", headers=headers, json={
                    "captcha_key": solution
                })

                break
            except Exception as e:
                print(e)
        server_invite = invite
        if join_server.status_code == 200:
            join_outcome = True
            server_name = join_server.json()["guild"]["name"]
            server_id = join_server.json()["guild"]["id"]
            print(f"{Fore.GREEN} > {Fore.WHITE}{profile} {Fore.GREEN}> {Fore.WHITE}{server_invite}")
        elif join_server.status_code == 429:
            print('RATE LIMITED!')
            await ctx.respond(embed=discord.Embed(title='The bot is being rate limited!', description='Please contact the owner!', color=0xe74c3c))
            return False
        else:
            print(join_server.text)
    except:
        pass

    return join_outcome, server_id, server_name


def do_boost(s, token, headers, profile, server_id, boost_id):
    boost_data = {"user_premium_guild_subscription_slot_ids": [f"{boost_id}"]}
    headers["content-length"] = str(len(str(boost_data)))
    headers["content-type"] = 'application/json'

    boosted = s.put(f"https://discord.com/api/v9/guilds/{server_id}/premium/subscriptions", json=boost_data,
                    headers=headers)
    if boosted.status_code == 201:
        return True
    else:
        return False


def get_invite():
    while True:
        print(f"{Fore.CYAN}Server invite?", end="")
        invite = input(" > ").replace("//", "")

        if "/invite/" in invite:
            invite = invite.split("/invite/")[1]

        elif "/" in invite:
            invite = invite.split("/")[1]

        dataabotinvite = httpx.get(f"https://discord.com/api/v9/invites/{invite}").text

        if '{"message": "Unknown Invite", "code": 10006}' in dataabotinvite:
            print(f"{Fore.RED}discord.gg/{invite} is invalid")
        else:
            print(f"{Fore.GREEN}discord.gg/{invite} appears to be a valid server")
            break

    return invite


def get_items(item):
    s = item[0]
    token = item[1]
    headers = item[2]
    profile = item[3]
    return s, token, headers, profile
try:
    bot.run(settings["botToken"])
except:
    print('something happend!')