# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import re
import scrapy
import hashlib
from itemadapter import ItemAdapter
from scrapy.pipelines.images import ImagesPipeline
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError


class CastoramaParserPipeline:
    def __init__(self):
        client = MongoClient('127.0.0.1', 27017)
        self.mongobase = client['castorama']

    def process_item(self, item, spider):
        collection = self.mongobase[spider.query]

        item['characteristics'] = self.parse_characteristics(item)
        item['_id'] = item['photos'][0]['checksum']


        try:
            collection.insert_one(item)
        except DuplicateKeyError:
            return None

        return item

    def parse_characteristics(self, item):
        """для характеристик"""

        chars = []

        flag = True
        for line in item['characteristics']:
            if re.findall(r'\w', line):
                try:
                    inp = int(re.search(r'\b.*\b', line)[0])
                except ValueError:
                    try:
                        inp = float(re.search(r'\b.*\b', line)[0])
                    except ValueError:
                        inp = re.search(r'\b.*\b', line)[0]

                if flag:
                    chars.append([inp])
                    flag = False
                else:
                    chars[-1].append(inp)
                    flag = True

        return chars


class CastoramaPhotosPipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        if item['photos']:
            for img in item['photos']:
                try:
                    yield scrapy.Request(img)
                except Exception as e:
                    print(e)

    def item_completed(self, results, item, info):
        item['photos'] = [itm[1] for itm in results if itm[0]]

        return item

    def file_path(self, request, response=None, info=None, *, item=None):
        image_hash = hashlib.shake_256(request.url.encode()).hexdigest(5)
        title = item['title'].split(' ')[0]
        image_filename = f'full/{title}/{image_hash}_{image_hash[3]}.jpg'

        return image_filename
