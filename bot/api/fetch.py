import re
from typing import Dict, List, Optional

from bot.api.parser import Parser, response_profile_complete
from bot.colors import red
from bot.constants import LANGS

from requests_html import AsyncHTMLSession

async def search_rootme_user_all_langs(username: str) -> List[Dict[str, str]]:
    all_users = []
    for lang in LANGS:
        content = await Parser.extract_rootme_profile(username, lang)
        if content is None:
            continue
        content = content[0]
        all_users += list(content.values())
    return all_users

async def search_rootme_user_challenges(username: str) :
    url = f"https://www.root-me.org/{username}?inc=score"

    session = AsyncHTMLSession()

    async def get_profile():
        
        r = await session.get(url)
        data = {}
        
        data['score'] = r.html.xpath("/html/body/div[1]/div/div[2]/main/div/div/div/div/div[2]/div[1]/div[1]/span/text()")[0].split("\xa0")[0][1:]
        data['ranking'] = r.html.xpath("/html/body/div[1]/div/div[2]/main/div/div/div/div/div[2]/div[1]/div[2]/span")[0].text
        data['rank'] = r.html.xpath("/html/body/div[1]/div/div[2]/main/div/div/div/div/div[2]/div[1]/div[3]/span")[0].text
        
        categories_list = r.html.xpath("/html/body/div/div/div[2]/main/div/div/div/div/div[2]")[0].find("div")
    
        categories = {}
    
        for x in categories_list:
            category = x.find('div')[0]
            try : 
                title = category.find('h4')[0].text.split('\n')[1]
                categories[title] = {"percentage" : category.find('h4')[0].text.split('\n')[0]}
                points, _, completion   = category.find("span")[1].text.split('\xa0')
                categories[title]['points'] = points
                categories[title]['completion'] = completion
                categories[title]['challenges'] = {}
                challenges = category.find("ul")[0].find('li')
                for challenge in challenges : 
                    categories[title]['challenges'][challenge.text[2:]] = {'completed' : True if challenge.text[0] == 'o' else False}
                    categories[title]['challenges'][challenge.text[2:]]['points'] = challenge.find('a')[0].attrs['title'].split(' ')[0]
            except : 
                pass
        data['challenges'] = categories
        return data
    return session.run(get_profile)[0]


async def search_rootme_user(username: str) -> Optional[List]:
    result_id_user = re.findall(r'-(\d+)$', username)
    if result_id_user:
        id_user = int(result_id_user[0])
        content = await Parser.extract_rootme_profile_complete(id_user)
        real_username = '-'.join(username.split('-')[:-1])
        if content is not None and content['nom'] != real_username:  # content might be None if score = 0
            return None
        all_users = await search_rootme_user_all_langs(real_username)
        if not all_users:
            return None
        if id_user not in [int(user['id_auteur']) for user in all_users]:
            return None
        #  username = real_username
        all_users = [user for user in all_users if user['id_auteur'] == str(id_user)]
    else:
        all_users = await search_rootme_user_all_langs(username)
        if not all_users:
            return None
    all_users_complete = []
    for user in all_users:
        user_data = await Parser.extract_rootme_profile_complete(user['id_auteur'])
        if user_data is not None:
            all_users_complete.append(dict(
                id_user=int(user['id_auteur']),
                username=user_data['nom'],
                score=int(user_data['score']),
                number_challenge_solved=len(user_data['validations'])
            ))
        else:  # user exists but score is equal to zero
            all_users_complete.append(dict(
                id_user=int(user['id_auteur']),
                username=user['nom'],
                score=0,
                number_challenge_solved=0
            ))
    all_users_complete = sorted(all_users_complete, key=lambda x: int(x['score']), reverse=True)
    return all_users_complete


async def get_challenges(lang: str):
    return await Parser.extract_challenges(lang)


async def get_all_challenges():
    result = []
    page_num = -50
    result_by_page = [{}, {"rel":"next", "href":"..."}]
    while result_by_page[-1]['rel'] == 'next':
        page_num += 50
        result_by_page = await Parser.extract_challenges_by_page(page_num)
        result += list(result_by_page[0].values())
    return result


async def get_solved_challenges(id_user: int) -> Optional[response_profile_complete]:
    solved_challenges_data = await Parser.extract_rootme_profile_complete(id_user)
    if solved_challenges_data is None:
        red(f'Error trying to fetch solved challenges.')
        return None
    return solved_challenges_data['validations']


def get_diff(solved_user1, solved_user2):
    if solved_user1 == solved_user2:
        return None, None
    test1 = list(map(lambda x: x['id_challenge'], solved_user1))
    test2 = list(map(lambda x: x['id_challenge'], solved_user2))
    user1_diff = list(filter(lambda x: x['id_challenge'] not in test2, solved_user1))[::-1]
    user2_diff = list(filter(lambda x: x['id_challenge'] not in test1, solved_user2))[::-1]
    return user1_diff, user2_diff
