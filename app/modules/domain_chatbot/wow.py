import os
import json
import pymongo
import datetime
import app.modules.logger.logging as log
from app.modules.domain_chatbot.user import User
from config import BASE_DIR, LOG_DIR, MONGO_URI, client

class Wow:

    # 讀取wow.json的模板並收集word
    def __init__(self, word_domain, flag):
        self.flag = flag
        self.word_domain = word_domain

        with open(os.path.join(BASE_DIR, 'domain_chatbot/template/wow.json'), 'r', encoding='UTF-8') as input:
            self.template = json.load(input)

        self.collect_data()

    # 當處於回覆流程中，將word填入location.json模板中
    def collect_data(self):
        if self.word_domain is not None and self.flag is not None:
            if self.flag == 'wow_init':
                magic_location = ['老人共餐', '友善餐廳', '長照中心', '餐廳', '旅館', '運動中心', '銀髮友好站', '美術館', '樂齡中心']
                for data in self.word_domain:
                    if data['domain'] in magic_location:
                        self.template['魔術地點'] = data['word']
                        self.template['區域'] = 'x' # 明確地點不用區域
                    if data['domain'] == '打電話':
                        self.template['打電話'] = 'o'
                    if data['domain'] == '魔術地點':
                        self.template['魔術地點'] = data['word']
                        self.template['打電話'] = 'x'
                    if data['domain'] == '城市':
                        self.template['區域'] = data['word']
            else:
                if self.flag == 'wow_region':
                    for data in self.word_domain:
                        if data['domain'] == '城市':
                            self.template['區域'] = data['word']
                                
        with open(os.path.join(BASE_DIR, 'domain_chatbot/template/wow.json'), 'w',encoding='UTF-8') as output:
            json.dump(self.template, output, indent=4, ensure_ascii=False)

    # 根據缺少的word，回覆相對應的response
    def response(self):
        content = {}
        
        if self.template['區域'] == '':
            content['flag'] = 'wow_region'
            content['response'] = self.template['區域回覆']
            self.store_conversation(content['response'])
        else:
            if self.template['打電話'] == 'o':
                content['flag'] = 'wow_done'
                content['response'] = self.template['打電話回覆']
                # self.store_database()
                self.clean_template()
                self.store_conversation(content['response'])
            else:
                content['flag'] = 'wow_done'
                content['response'] = self.template['完成回覆']
                # self.store_database()
                self.clean_template()
                self.store_conversation(content['response'])

        return json.dumps(content, ensure_ascii=False)

    # 地點上傳至資料庫
    def store_database(self):
        logger = log.Logging('wow:store_database')
        logger.run(LOG_DIR)
        try:
            db = client['aiboxdb']
            collect = db['location']

            database_template = {
                '_id': collect.count() + 1,
                'location': self.template['地點'],
                'region': self.template['區域'],
                'number': self.template['數字'],
                'unit': self.template['單位'],
                'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            collect.insert_one(database_template)
            logger.debug_msg('successfully store to database')

            # location lock
            location_lock_collect = db['location_lock']
            location_lock_collect.update({'_id': 0}, {'$set':{'lock': True, 'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}})
            
        except ConnectionError as err:
            logger.error_msg(err)

    # 清除wow.json的欄位內容
    def clean_template(self):
        for key in dict(self.template).keys():
            if '回覆' not in key:
                self.template[key] = ''

        with open(os.path.join(BASE_DIR, 'domain_chatbot/template/wow.json'), 'w', encoding='UTF-8') as output:
            json.dump(self.template, output, indent=4, ensure_ascii=False)

    # 上傳對話紀錄至資料庫
    def store_conversation(self, response):
        User.store_conversation(response)