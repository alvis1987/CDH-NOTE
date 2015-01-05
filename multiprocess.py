# -*- coding: utf-8 -*-
import urllib
import sys
import time
import re
import datetime
from multiprocessing import Pool,Lock ,Manager

def gettoday():
    return str(datetime.date.today())

def getprevious(date):
    return str(datetime.datetime.strptime(date,"%Y-%m-%d")-datetime.timedelta(days=1))[0:10]

def getappinfo():
    app_info = {}
    f = open("/opt/caldata/versionInfo/app_info.txt" , "r")
    for line in f:
        linelist = line.split("\t")
        [app , id , name , version] = linelist
        try:
            version = int(version)
        except Exception,e:
            version = 0
        app_info[app] = [version , name , id]
    f.close()
    return app_info

class nginxParser:
    def __init__(self , url):
        self.L = re.split("\"|\s|\?|\[|\]" , url)
        #[self.imei , self.applist , self.t , length , action] = ["" , "" , self.L[8] , len(self.L) , self.L[9].split("/")[-1]]
        [self.imei , self.applist  , length ] = [""  ,  ""  ,  len(self.L)]
        try:
            self.t = self.L[8]
            action = self.L[9].split("/")[-1]
            if action == "detectGamesUpdate" :
                if self.t == "GET":
                    property = self.L[10].split("&")
                else:
                    property = self.L[13].split("&")
                for item in property:
                    if item[:4] == "imei":
                        self.imei = item.split("=")[1]
                    if item[:7] == "content":
                        self.applist = urllib.unquote(item.split("=")[1])
        except Exception,e:
            print e

    def getimei(self):
        return self.imei

    def getapplist(self):
        try:
            result = [[item.split(":")[0] , item.split(":")[1]] for item in self.applist.split(";")]
        except Exception,e:
            result = []
        return result


def getpath(date):
    pathlist = []
    for server in [3,4]:
        for number in range(0,24,1):
            if number < 10:
                path = "/opt/caldata/versionInfo/0%d/gamecenter_access.log_%s-0%d.log"%(server , date , number)
            else:
                path = "/opt/caldata/versionInfo/0%d/gamecenter_access.log_%s-%d.log"%(server ,date , number)
            pathlist.append(path)
    return pathlist



#获取装机用户安装应用大于或等于商店版本号的用户。
def userupversion(date , app_info ,updateInfo):
    result = {}
    for app in updateInfo:
        [total , up] = [0 , 0]
        if app in app_info:
            try:
                current_version = int(app_info[app][0])
                [name , id] = [app_info[app][1] , app_info[app][2]]
            except Exception,e:
                print "int cast error!"
            for imei in updateInfo[app]:
                total += 1
                try:
                    if int(updateInfo[app][imei]) >= current_version:
                        up += 1
                except Exception,e:
                    print "int cast error 2!"
            result[app] = [ id , name , str(total) , str(up)]
    f = open("/opt/caldata/versionInfo/result/todayup%s"%date , "w")
    for app in result:
        f.write("\t".join([app] + result[app]) + "\n")
    f.close()

#昨日装机用户中，升级版本的比例 ,及升级版本高于vivo商店版本的数量
def appupdateratio(date , app_info , Y_updateInfo ,T_updateInfo):
    in_result = {}
    out_result = {}
    for app in Y_updateInfo:
        if app not in T_updateInfo:
            continue
        [total , dif_total , dif_store] = [0 , 0 , 0 ]
        if app in app_info:
            [name , id] = [app_info[app][1] , app_info[app][2]]
            for imei in  Y_updateInfo[app]:
                if imei in T_updateInfo[app]:
                    total += 1
                    try:
                        if  int(Y_updateInfo[app][imei]) < int(T_updateInfo[app][imei]):
                            dif_total += 1
                            if int(T_updateInfo[app][imei]) > int(app_info[app][0]):
                                dif_store += 1
                    except Exception,e:
                        print "int cast error in appupdateratio"
            in_result[app] = [name , id , str(total)  , str(dif_total) ,str(dif_store)]
        else:
            for imei in  Y_updateInfo[app]:
                if imei in T_updateInfo[app]:
                    total += 1
                    try:
                        if  int(Y_updateInfo[app][imei]) < int(T_updateInfo[app][imei]):
                            dif_total += 1
                    except Exception,e:
                        print "int cast error in appupdateratio"
                        print T_updateInfo[app][imei] , Y_updateInfo[app][imei]
            out_result[app] = ["none" , "none" , str(total) , str(dif_total)]
    f1 = open("/opt/caldata/versionInfo/result/appupdatein%s"%date , "w")
    f2 = open("/opt/caldata/versionInfo/result/appupdateout%s"%date , "w")
    for app in in_result:
        f1.write("\t".join([app] + in_result[app]) + "\n")
    for app in out_result:
        f2.write("\t".join([app] + out_result[app]) + "\n")
    f1.close()
    f2.close()



def fillInfo(updateUser , updateInfo):
    #确定文件路径列表
    pathlist = ["/opt/caldata/versionInfo/test/%d"%num  for num in range(48)]

    start = time.time()
    for path in pathlist:
        taskstart = time.time()
        print "read file in the path:%s"%path
        f = open(path , "r")
        for line in f:
            imei , app , version = line.split("\t")
            updateUser.add(imei)
            if app not in updateInfo:
                updateInfo[app]={}
                updateInfo[app][imei] = version
            else:
                updateInfo[app][imei] = version
        print "finsh read current file , time cost %d"%(time.time() - taskstart)
        f.close()
    print "read job time cost %d"%(time.time() - start)



def writesplitresult(dic):
    path , num , lock = dic
    f = open(path , "r")
    out = open("/opt/caldata/versionInfo/test/%d"%num , "w")
    lock.acquire()
    print "current extract info from the file in path :%s"%path
    lock.release()
    start = time.time()
    result = []
    count = 0
    for line in f:
        record = nginxParser(line)
        [imei , applist ] = [record.getimei() , record.getapplist()]
        if applist:
            result.extend(["\t".join([imei] + app) + "\n" for app in applist])
            count += 1
            if count > 10000:
                out.writelines(result)
                count = 0
                result = []
    out.writelines(result)
    f.close()
    out.close()
    lock.acquire()
    print "write path: %d the extracted info , time cost: %d"%(num , time.time() -start)
    lock.release()

def multiprocesswrite(pathlist):
    start = time.time()
    print "initiate multiprocessing  write job....."
    p = Pool(processes=16)
    lock = Manager().Lock()
    args = [(pathlist[i] , i , lock) for i in range(len(pathlist))]
    r = p.map(writesplitresult , args)
    p.close()
    p.join()
    print "multiprocessing write job  finish , cost total time %d minutes"%((time.time() - start)/60)

def main(date):
    job_start = time.time()
    print "job starting ..... \ncurrent time is: %s"%(str(datetime.datetime.now()))

    #获取商店里的应用版本信息。
    app_info = getappinfo()
    #初始化搜集昨天信息的容器
    [Y_updateUser , Y_updateInfo ] = [set() , {} ]
    #初始化搜集今天信息的容器
    [T_updateUser , T_updateInfo ] = [set() , {} ]

    #多进程抽取任务所需信息并写入指定文件，之后读入
    #@.1 操作前一天的数据
    multiprocesswrite(getpath(getprevious(date)))
    fillInfo(Y_updateUser ,Y_updateInfo )

    #@.1 操作当日数据
    multiprocesswrite(getpath(date))
    fillInfo(T_updateUser ,T_updateInfo)

    #输出上传列表用户数后，清空用户，释放内存
    f = open("/opt/caldata/versionInfo/result/usernum%s"%date , "w")
    try:
        f.write("今天用户数:%d , 昨天用户数：%d ,两天都上传应用的用户数：%d"%(len(T_updateUser),len(Y_updateUser),
            len(Y_updateUser&T_updateUser)))
        Y_updateUser = set()
        T_updateUser = set()
    except Exception,e:
        print "user count error:" ,e
    f.close()


    #昨日装机版本升级
    try:
        appupdateratio(date , app_info , Y_updateInfo , T_updateInfo)
    except Exception,e:
        print "version update ratio error",e

    #今日装机中高版本的用户占比
    userupversion(date , app_info , T_updateInfo)

    print "job finished ! current time is %s"%(str(datetime.datetime.now()))
    print "job cost time total %d minutes"%((time.time() - job_start)/60)

if __name__ ==  "__main__":
    today = gettoday()
    date = getprevious(today)
    main(date)

