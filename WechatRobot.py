#!/usr/bin/env python
# coding=utf-8

from Wechat import wechat
import sys
import time
import MySQLdb
reload(sys)
sys.setdefaultencoding('utf-8')

def checkIn(self,message):
    CurrentTime = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    NickName = self.getContactFromChatGroup(message['Speaker'], EncryChatRoomId = message['toUser'])
    try:
        db = MySQLdb.connect('******','*******','******','******')
        cur = db.cursor()
        cur.execute('select * from Qiandao where nickname = \'%s\''%(NickName))
        rows = cur.fetchall()
        lenth = len(rows)
        if lenth > 0:
            if str(rows[lenth-1][1])[:10] == str(CurrentTime[:10]):
                return '%s 今天在%s已经签过到了！' %(NickName, str(rows[lenth-1][1]))
            else:
                number = rows[lenth-1][2]
                sql = "insert into Qiandao values('%s', '%s', %d)" % (NickName, CurrentTime, number+1)
                cur.execute(sql)
        else:
                sql = "insert into Qiandao values('%s', '%s', %d)" % (NickName, CurrentTime, 1)
                cur.execute(sql)
        db.commit()
    except MySQLdb.Error, e:
        print 'Cannot connect to the database:%s'%(e.args[1])
        return '%s %s 签到失败。。。'%(CurrentTime, NickName)
    return '%s %s 已经成功签到啦~'%(CurrentTime, NickName)

def f(self):
    while self.messagesQueue.empty() == False:
        message = self.messagesQueue.get()
        print 'Message accepted!'
        print 'Newmessage:'+message['Content'].encode('utf-8')+' From:'+message['toUser'].encode('utf-8')
        content = message['Content']
        if content == '/help':
            self.sendMessage(message['toUser'], message = '测试中，目前只有/help指令~')
        elif content == '/qd' and message['ChatGroup']:
            self.sendMessage(message['toUser'], message = checkIn(self, message))
if __name__ == '__main__':
    wechat.menuList = ['/help','/justforyou','/qd']
    wechat.menu = f
    w = wechat()
