#!/usr/bin/python
#-*-coding:utf-8-*-

__author__ = 'hadoop'

from logging import config, getLogger
from flup.server.fcgi_fork import WSGIServer

import fcntl
import urlparse
import urllib
import json
import os
import sys

RESOURCE = "~/workspace/work/weixinKeyCollector/"
config.fileConfig('log.conf')
log = getLogger('weixin')

def parseQueryString(query):
    if not query: return  {}

    paramDict = {}
    for param in query.split('&'):
        try:
            key, value = param.split('=')
            if value:
                paramDict[key.lower()] = value
        except ValueError:
            pass
    return paramDict


class Request(object):

    def __init__(self, environ):
        self.environ     = environ
        self.method      = environ.get('REQUEST_METHOD', "")
        self.GET         = parseQueryString(environ.get('QUERY_STRING', ""))
        self.queryString = environ.get('QUERY_STRING','')
        self.serverName  = environ.get('SERVER_NAME', '')
        self.serverPort  = environ.get('SERVER_PORT', '')
        self.remoteHost  = environ.get('REMOTE_ADDR', '')
        self.refer       = environ.get('HTTP_REFERER','')

def sendmsg():
    os.system("ssh hadoop@172.16.100.150 \"bash /home/hadoop/contact_by_sms.sh\"")

# 从文件中读取key
def getkey():
    res = {}
    fd = open("KEY", 'rb')
    line = fd.readline()
    fd.close()


    log.debug(line)

    if line:
        try:
            fd = open("KEY", 'wb')
            fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
            fd.truncate()
            fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
            fd.close()
        except Exception, e:
            log.error(e.message)

    return line

# 从链接中分析出 uin , key.
def parsekey(url):
    try:
        if url:
            rurl = urlparse.urlparse(url)
            if rurl.netloc == "mp.weixin.qq.com":
                qs = urlparse.parse_qs(rurl.query)
                if qs.has_key('key'):
                    res = dict((key,value[0]) for (key, value) in qs.items())
                    log.info("Get a new key. %s." % repr(res))
                    return res
                else:
                    log.debug("%s, has not a valid key." %url)
                    return {}
    except Exception, e:
        log.error(e.message)
        return {}

def application(env, start_response):
    path = env['PATH_INFO']

    if path == r'/getkey':
        #request = Request(env)
        output = getkey()
        log.info(repr(output))

        status = '200 OK'
        response_headers = [('Content-type', 'text/plain'),
                            ('Content_Length', str(len(output)))]

        start_response(status, response_headers)
        return [output]

    elif path == '/weixin/gzhlogo.png':
        log.debug("%s" %repr(env))
        #log.debug("There are keys %s." %repr(env.keys()))

        request = Request(env)
        if request.refer:
            log.info(request.refer)
            query = parsekey(request.refer)

            try:
                if query.has_key('uin') and query.has_key('key'):
                    # 写入数据.加锁.
                    try:
                        fd = open("KEY", 'wb')
                        fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
                        fd.write(json.dumps(query))
                        fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
                        fd.close()
                    except Exception, e:
                        log.error(e.message)
            except Exception, e:
                log.debug(e.message)
        # N\A , 为了代码整齐.
        else:
            pass

        try:
            fd = open("gzhlogo.png", 'rb')
            output = fd.read()
            log.debug("Read a image, size is %s." %len(output))
            fd.close()
        except Exception, e:
            log.debug(e.message)

        status = '200 OK'
        response_headers = [('Content-type', 'image/png'),
                            ('Content_Length', str(len(output)))]

        start_response(status, response_headers)
        return [output]
    else:
        status = '404 Not Found'
        response_headers = [('Content-type', 'text/plain'),
                            ('Content-Length', str(len(status)))]
        start_response(status, response_headers)
        return [status]

if __name__ == '__main__':
    bindaddress = ('127.0.0.1', 9999)
    options = {
        'minSpare': 5,
        'maxSpare': 20,
        'maxChildren': 50,
    }

    WSGIServer(application, bindAddress=bindaddress, **options).run()