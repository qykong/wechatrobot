#!/usr/bin/env python
# coding=utf-8

import requests
import os
import time
import re
import sys
import json
import Queue
reload(sys)
sys.setdefaultencoding("utf-8")

class wechat:
    deviceId = 'e000000000000000'
    s = requests.Session()
    groupChatList = []
    messagesQueue = Queue.Queue()
    menuList = []
    QRImagePath = os.getcwd() + '/qrcode.jpg'

    def __init__(self):
        print 'Trying to login wechat...'
        self.retry = 0
        self.maxtrying = 1000
        if self.getUUID() == False:
            print 'Failed to get UUID.'
        else:
            print 'Successfully got UUID'

            self.showQR()
            time.sleep(1)
            while self.waitForLogin() != '200':
                pass
            if sys.platform == 'darwin':
                os.system('rm %s'%(self.QRImagePath))
            if self.login() == False:
                print 'Cannot login...'
            else:
                print 'Successful login!'

                if self.webwxinit() == False:
                    print 'Cannot initial...'
                else:
                    print 'Initial successed!'
                    while 1:
                        k = self.syncCheck()
                        if k == -1:
                            print 'sync error!'
                            break
                        elif k == 2 or 7:
                            if self.getNewMessages():
                                self.menu()

    def getUUID(self):
        url = 'https://login.weixin.qq.com/jslogin'
        params = {
                    'appid': 'wx782c26e4c19acffb',
                    'fun': 'new',
                    'lang': 'zh_CN',
                    '_': int(time.time()*1000),

        }
        self.headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:43.0) Gecko/20100101 Firefox/43.0'}
        try:
            r = self.s.get(url, headers = self.headers, params = params)
        except:
            print 'getUUID error,retrying...'
            self.retry+=1
            if self.retry < self.maxtrying:
                return self.getUUID()
            else:
                print 'Too many attempts...'
                exit()
        items = re.findall('ndow.QRLogin.code = (.*?); window.QRLogin.uuid = "(.*?)"', r.text, re.S)
        self.code = items[0][0]
        self.uuid = items[0][1]
        if self.code == '200':
            return True
        else:
            return False

    def showQR(self):
        QRurl = 'https://login.weixin.qq.com/qrcode/' + self.uuid
        params = {
                    't': 'webwx',
                    '_': int(time.time()*1000),
        }
        r = self.s.get(QRurl, headers = self.headers, params = params)
        self.tip = 1
        if sys.platform == 'darwin':
            f = open(self.QRImagePath, 'wb')
            f.write(r.content)
            f.close()
            os.system('open %s'%(self.QRImagePath))
        print 'Please scan the QRImage!'

    def waitForLogin(self):
        self.startTime = int(time.time()*1000)
        url = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s' % (self.tip, self.uuid,self.startTime)
        r = self.s.get(url, headers = self.headers)
        pm = re.search('window.code=(.*?);', r.text, re.S)

        code = pm.group(1)
        if code == '201':
            if self.tip ==1:
                print 'OK, Please click the button to confirm.'
                self.tip = 0
        elif code == '200':
            print 'Login...'
            pm = re.search('window.redirect_uri="(.*?)";', r.text,re.S)
            self.redirect_uri = pm.group(1) + '&fun=new'
            self.base_url = self.redirect_uri[:self.redirect_uri.rfind('/')]
        elif code == '408':
            pass
        return code

    def login(self):
        r = self.s.get(self.redirect_uri, headers = self.headers)
        items = re.findall('<error><ret>0</ret><message>OK</message><skey>(.*?)</skey><wxsid>(.*?)</wxsid><wxuin>(.*?)</wxuin><pass_ticket>(.*?)</pass_ticket><isgrayscale>1</isgrayscale></error>',r.text,re.S)
        self.skey = items[0][0]
        self.wxsid = items[0][1]
        self.wxuin = items[0][2]
        self.pass_ticket = items[0][3]
        if self.skey == '' or self.wxsid == '' or self.wxuin == '' or self.pass_ticket == '' :
            return False
        self.BaseRequest = {
            'Uin': self.wxuin,
            'Sid': self.wxsid,
            'Skey': self.skey,
            'DeviceID': self.deviceId,
        }
        return True

    def webwxinit(self):
        url = self.base_url + '/webwxinit?r=%s' % (int(time.time()*1000))
        playload = {
             'BaseRequest':self.BaseRequest
        }
        self.headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:43.0) Gecko/20100101 Firefox/43.0','Content-Type':'application/json;charset=UTF-8'}
        r = self.s.post(url, headers = self.headers, json = playload)
        r.encoding = 'utf-8'
        dic = r.json()
        ret = dic['BaseResponse']['Ret']
        if ret > 0 :
            return False
        self.getNewSynKey(dic)
        self.MyName = dic['User']['UserName']
        self.ContactList = dic['ContactList']
        for item in dic['ContactList']:
            if item['UserName'].find('@@') != -1:
                self.groupChatList.append(item)
        return True

    def getNewSynKey(self, dic):
        synckeyCount = dic['SyncKey']['Count']
        self.syncKeyList = dic['SyncKey']
        self.SyncKey = ''
        for i in range(synckeyCount):
            self.SyncKey = self.SyncKey + str(dic['SyncKey']['List'][i]['Key'])+ '_' + str(dic['SyncKey']['List'][i]['Val'])
            if i < synckeyCount-1:
                self.SyncKey = self.SyncKey + '|'

    def getContact(self):
        url = self.base_url + '/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' % (self.pass_ticket, self.skey, int(time.time()*1000))
        r = self.s.get(url, headers = self.headers)
        r.encoding = 'utf-8'
        dic = r.json()
        self.MemberList = dic['MemberList']
        if dic['BaseResponse']['Ret'] != 0:
            return False
        return True

    def getContactFromChatGroup(self, UserName, EncryChatRoomId):
        url = self.base_url + '/webwxbatchgetcontact?'
        postData = {
            'BaseRequest' : self.BaseRequest,
            'Count' : 1,
            'List' : [
                {
                    'EncryChatRoomId' : EncryChatRoomId,
                    'UserName' : UserName
                }
            ]
        }
        params = {
            'lang' : 'zh_CN',
            'pass_ticket' : self.pass_ticket,
            'r' : int(time.time()*1000),
            'type' : 'ex'
        }
        try:
            r = self.s.post(url, headers = self.headers, params = params, json = postData)
        except:
            print 'Cannot get contact from chat group, retrying...'
            self.retry+=1
            if self.retry < self.maxtrying:
                return self.getContactFromChatGroup(UserName, EncryChatRoomId = EncryChatRoomId)
            else:
                print 'Too many attempts'
                exit()
        r.encoding = 'utf-8'
        return r.json()['ContactList'][0]['NickName']

    def syncCheck(self):
        num = re.search('https://wx(.*?).qq.com',self.base_url)
        url = 'https://webpush'+num.group(1)+'.weixin.qq.com/cgi-bin/mmwebwx-bin'+ '/synccheck?'
        self.startTime = self.startTime + 1
        params = {
            'r' : int(time.time()*1000),
            'skey' : self.skey,
            'sid' : self.wxsid,
            'uin' : self.wxuin,
            'deviceid' : self.deviceId,
            'synckey' : self.SyncKey,
            '_' : self.startTime
        }
        try:
            r = self.s.get(url, headers = self.headers, params = params)
        except:
            print 'Cannot synccheck, retrying...'
            self.retry+=1
            if self.retry < self.maxtrying:
                return self.syncCheck()
            else:
                print 'Too many attempts...'
                exit()
        items = re.findall('window.synccheck={retcode:"(.*?)",selector:"(.*?)"}', r.text, re.S)
        if items[0][0] != '0':
            self.retry+=1
            if self.retry < self.maxtrying:
                return self.syncCheck()
            else:
                print 'Too many attempts...'
                exit()
        return int(items[0][1])

    def getNewMessages(self):
        flag = False
        url = self.base_url + '/webwxsync?'
        getMessagesRequest = {
            'BaseRequest' : self.BaseRequest,
            'SyncKey' : self.syncKeyList,
            'rr' : int(time.time()*1000)
        }
        params = {
            'sid' : self.wxsid,
            'skey' : self.skey,
            'pass_ticket' : self.pass_ticket,
            'lang' : 'zh_CN'
        }

        try:
            r = self.s.post(url, headers = self.headers, params = params, json = getMessagesRequest)
        except:
            print 'Cannot get Newmessages, retrying...'
            self.retry+=1
            if self.retry < self.maxtrying:
                return self.getNewMessages()
            else:
                print 'Too many attempts...'
                exit()
        r.encoding = 'utf-8'
        dic = r.json()
        self.getNewSynKey(dic)

        if dic['AddMsgCount'] > 0:
            print dic['AddMsgCount']
            for k in range(dic['AddMsgCount']):
                chatgroup = False
                speaker = ''
                fromUser = dic['AddMsgList'][k]['FromUserName']
                if fromUser == self.MyName:
                    continue
                content = dic['AddMsgList'][k]['Content']
                if fromUser[0] == '@' and fromUser[1] == '@' and content[0] == '@':
                    chatgroup = True
                    print content
                    pm = re.findall('(.*):<br/>(.*)', content, re.S)
                    speaker = pm[0][0]
                    content = pm[0][1]
                if content in self.menuList:
                    flag = True
                    self.messagesQueue.put({
                        'Content': content,
                        'toUser': fromUser,
                        'ChatGroup' : chatgroup,
                        'Speaker' : speaker
                    })
        return flag

    def sendMessage(self, toUser, message):
        url = self.base_url + '/webwxsendmsg?'
        params = {
            'lang' : 'zh_CN',
            'pass_ticket' : self.pass_ticket
        }
        Id = int(time.time()*10000000)
        sendRequest = {
            'BaseRequest' : self.BaseRequest,
            'Msg' : {
                'ClientMsgId' : '%s'%(Id),
                'Content' : message,
                'FromUserName' : self.MyName,
                'LocalID' : '%s'%(Id),
                'ToUserName' : toUser,
                'Type' : 1
            }
        }
        print message
        r = self.s.post(url, headers = self.headers, params = params, data = json.dumps(sendRequest, ensure_ascii=False).encode('utf-8'))
        print r.text
        self.getNewMessages()
