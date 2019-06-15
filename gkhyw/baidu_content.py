# -*- coding: utf-8 -*-
from bluextracter.extractor import Extractor    # 不用管提示
import hashlib
from threading import Thread
from queue import Queue
import requests
import re
import random
import itertools


headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36"}


def get_baidu_url(word, retries=2):
    """
    获取百度json前50的结果
    :param word:要获取的词
    :param retries:请求失败重试次数
    :return:排名url
    """
    url = "https://www.baidu.com/s"
    params = {
        'ie': 'utf-8',
        'wd': word,
        'tn': 'json',
        'rn': 50
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
    except Exception as e:
        print('{} Download Error: {}'.format(word, e))
        data = None
        if retries > 0:
            return get_baidu_url(word, retries -1)
    else:
        try:
            datas = resp.json()
        except Exception as e:
            print('{} Download Json Datas Error: {}'.format(word, e))
            data = None
            if retries > 0:
                return get_baidu_url(word, retries -1)
    try:
        for data in datas.get('feed').get('entry')[:-1]:
            yield data.get('url')
    except Exception:
        return None


def get_content(url, score_limit=1000, word_limit=500, retries=2):
    """
    通过bluextracter自动获取内容
    :param url: 需要获取内容的url
    :param score_limit: 目标分数
    :param word_limit: 文字内容数量
    :param retries: 请求失败重试次数
    :return: 内容
    """
    try:
        resp = requests.get(url, headers=headers, timeout=15)
    except requests.RequestException as err:
        print("{} download error: {}".format(url, err))
        html = None
        if retries > 0:
            return get_content(url, score_limit, word_limit, retries - 1)
    else:
        html = resp.text
        encoding = 'utf-8'
        encoding_re = re.findall('<meta.*?charset="?([\w-]*)".*>', html, re.I) # 获取编码
        if encoding_re:
            encoding = encoding_re[0]
        resp.encoding = encoding
        html = resp.text
    if html:
        ex = Extractor()
        ex.extract(url, html)
        content = ex.format_text
        score = ex.score
        words = ex.text_count
        if score < score_limit or words < word_limit:
            # 如果得分和字数少于目标数量则返回空
            return None
        return clean_tag(content)    # 返回内容

def md5_convert(string):
    """
    计算字符串md5值
    :param string: 输入字符串
    :return: 字符串md5
    """
    m = hashlib.md5()
    m.update(string.encode())
    return m.hexdigest()


def clean_tag(content):
    """
    清除html标签中非p标签
    :param content: 需要处理的HTML正文
    :return: 清除标签后的HTML正文
    """
    body = ''
    content = re.sub(r'<(?!p|/p|img|br/|strong|/strong)[^<>]*?>', '', content).strip()  # 替换标签中非p、img及/p开始的所有<>里面的标签为空
    # 通过|分割标签,只替换()括号中的内容，?!是正向否定预查。
    content = re.sub(r'<p[^>]*?>', '<p>', content)  # 替换p标签属性中的所有属性
    content = re.sub(r'<strong[^>]*?>', '<strong>', content)  # 替换strong标签属性中的所有属性
    results = re.findall(r'(<p>.*?</p>)', content)[1:-1]
    for row in results:
        if row == '<p></p>':
            continue
        body += row
    # 处理images标签
    images = re.findall(r'(<img.*?>)', body, re.S | re.I)  # 提取img标签进行处理
    for img in images:
        src = re.search(r'src="(.*?)"', img, re.I | re.S).group(1) if re.search(r'(src=".*?")', img, re.I | re.S) else ""  # 提取图片地址
        try:
            resp = requests.get(src)
        except Exception:
            new_img = None
        else:
            img_content = resp.content
            img_name = md5_convert(src)  # 通过md5唯一值生成图片名称
            with open('images/%s.jpg' % img_name, 'wb') as f:
                f.write(img_content)
            new_img = '<img src="images/%s.jpg" />' % (img_name)    # 重新组合img标签
        if new_img:
            body = re.sub(img, new_img, body)    # 如果成功获取病下载了替换原来的img标签
    return body


if __name__ == "__main__":
    word ='民间个人无抵押贷款的优缺点'   # 获取内容的关键词
    results_list = []  # 内容临时存放列表
    """获取百度搜索关键词json结果排除百度、知乎等大站后,同时排除字数小于500且内容得分小于1000的内容结果前10"""
    for url in get_baidu_url(word):
        if 'baidu.com' in url or 'zhihu.com' in url or 'sina.com.cn' in url or 'sohu.com' in url or 'tianya.cn' in url:
            continue
        datas = get_content(url)    # 获取内容
        if datas:
            if len(results_list) <= 3:
                # 如果获取内容的数量小于或等于3
                results_list.append(datas)  # 则将内容存放到内容列表中
            else:
                break   # 如果大于10则跳出循环
    if len(results_list) <= 3:
        # 如果内容数量大于或小于3次
        content_list = random.sample(results_list, random.randint(2, 3))
        # 则随机获取2到3个内容结果
        print(''.join(content_list))    # 将内容结果进行组合,得到最终内容
    else:
        print(''.join(results_list))

