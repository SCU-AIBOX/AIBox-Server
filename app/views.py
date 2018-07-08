from app import app
from config import BASE_DIR, MODEL_DIR, MONGO_URI
from flask import jsonify, request
from app.modules.domain_matcher.matcher import Matcher
from app.modules.domain_chatbot.chatbot import Chatbot
from threading import Timer
import os
import pymongo
import time
import threading

matcher = Matcher()
matcher.load_rule_data(os.path.join(BASE_DIR, 'domain_matcher/rule'))
matcher.load_word2vec_model(os.path.join(MODEL_DIR, "20180320all_model.bin"))
print(matcher.rule_data)

# 連進MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client['aiboxdb']
print('success connect to mongodb.')

# 登出倒數計時方法
times = 30 # global倒數var
def logout_timeout():
    global times
    print('start logout timeout thread !')
    print('登出倒數', times, '秒')
    while times != 0:
        time.sleep(1)
        times = times - 1
        if times == 0:
            try:
                user_collect = db['users']
                user_collect.update_many({}, {'$set':{'is_login': False}})
                print('登出成功!')
            except:
                print('登出錯誤!')
                
                

@app.route('/api/login', methods=['POST'])
def login():
    # 收到的專屬語
    user_nickname = request.json['user_nickname']
    
    # 查看資料庫是否有此專屬語
    collect = db['users']
    has_nick_name = collect.find_one({'nickname': user_nickname})
    
    if has_nick_name is None:
        resp = {
            'status': 404,
            'result': '',
            'msg': '沒有此專屬語'
        }
        return jsonify(resp)
    else:
        resp = {
            'status': 200,
            'result': has_nick_name,
            'msg': '登入成功'
        }
        
        # 紀錄登入狀況
        login_collect = db['login']
        login_collect.update({'_id': 0},{'$set':{"is_login": True, "user_nickname": user_nickname}})
        return jsonify(resp)

    
@app.route('/api/logout', methods=['POST'])
def logout():

    login_collect = db['login']
    login_collect.update({'_id': 0}, {'$set':{'is_login': False, 'user_nickname': ''}})
    
    resp = {
        'status': 200,
        'result': '',
        'msg': '登出成功'
    }
    
    return jsonify(resp)


@app.route('/api/checkLogin', methods=['POST'])
def checkLogin():
    login_collect = db['login']
    login_doc = login_collect.find_one({'_id': 0})
    print(login_doc['is_login'])
    
    if login_doc['is_login'] is True:
        return login_doc['user_nickname']
    else:
        return 'not login'

    
@app.route('/api/chatbot', methods=['POST'])
def chatbot_resp():

    flag = request.json['flag']
    if flag == '':
        flag = None

    sentence = request.json['response']
    print(flag)

    # 去db找，是否有此專屬語
    # 有則登入，無則聽沒
    login_collect = db['login']
    user_collect = db['users']
    has_user_nickname_doc = user_collect.find_one({'nickname': sentence})
    
    login_doc = login_collect.find_one({'_id': 0})
    user_nickname = login_doc['user_nickname'] # 登入中的user的nickname
    
    if has_user_nickname_doc is None:
        print('沒有此nickname逆')
        print('user_nickname:', user_nickname)

        # 分析語意
        domain_score = matcher.match_domain(sentence, user_nickname=user_nickname, flag=flag)
        print(domain_score)
        # 根據domain_score，做相對應的回覆
        chat = Chatbot(domain_score, flag=flag)
        message = chat.response_word()
        return message
    else:
        login_collect.update({'_id': 0}, {'$set': {'is_login': True, "user_nickname": has_user_nickname_doc['nickname']}})
        print(user_nickname)
        resp = {
            'flag': '',
            'response': '登入成功'
        }
        
        # 登出倒數
        # 是否為登入狀態，並計時倒數
#        t = threading.Thread(target=logout_timeout, name='logoutTimeoutThread')
#        t.start()
        
        return jsonify(resp)

    