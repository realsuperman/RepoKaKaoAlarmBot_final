import MySQLdb,threading,time,requests,json
from api.githubApi import getRepositoryInfo
from datetime import datetime, timedelta

def batch():
    print("깃 허브쪽 배치 프로그램이 돌고 있습니다.")  # 배치 프로그램이 돌고 있다는 로그남김 log
    try:
        conn = None
        #conn = MySQLdb.connect(user='seonghun', password='db20192455', db='seonghun$default',host='seonghun.mysql.pythonanywhere-services.com', charset='utf8')
        conn = MySQLdb.connect(user='root', password='1234', db='open_source', charset='utf8')
        curs = conn.cursor()

        sql = "SELECT GIT_API_ADDRESS,FAV_REPOSITORY,GIT_UPDATED_AT FROM repository;"
        curs.execute(sql)
        result = curs.fetchall()

        sql = "SELECT DATE_FORMAT(NOW(),'%Y%m%d%H%i%s');"
        curs.execute(sql)
        time = curs.fetchall()

        for i in result:
            dataList = getRepositoryInfo(i[0], None , 1)
            if dataList[0] == 404:
                raise Exception('GITHUB API 호출할때 문제가 생겼습니다.')
            if dataList[1] != i[2]:  # dataList[1]은 깃 업데이트날, i[2]은 db상 저장된 깃 업데이트날

                sql = "UPDATE repository SET GIT_UPDATED_AT=%s,UPDATED_AT=%s WHERE FAV_REPOSITORY = %s"
                curs.execute(sql, (dataList[1], time, i[1]))

                sql = "SELECT b.id,b.nick_name,b.type,a.git_api_address,a.fav_repository,b.user_get_date FROM repository a LEFT JOIN user b ON a.fav_repository = b.fav_repository WHERE a.fav_repository=%s";
                curs.execute(sql, [i[1]])

                result2 = curs.fetchall()
                for j in result2:
                    str = j[3]
                    index = str.find('branches')
                    url = str[:index]+"commits"
                    branch = str[str.find('branches/'):]
                    branch = branch[branch.find('/'):].replace('/','')

                    if j[2] == 'kakao' :
                        print("카카오를 할 것")
                    else : # 나머지 케이스는 텔레그램
                        date = datetime.strptime(i[2], '%Y-%m-%dT%H:%M:%SZ') + timedelta(seconds=+1)
                        timestampStr = date.strftime("%Y-%m-%dT%H:%M:%SZ")
                        content = requests.get(url,headers={'Authorization':'token 6f6d00c786cd3662b25716bf6c6fb6a2084f401d'},params={'sha':branch,'since':timestampStr})
                        jsonObject = json.loads(content.content)
                        telegram(j[0],j[1],j[4],j[5],dataList[1],jsonObject,conn) # 이 부분 수정 필요
        conn.commit()
    except Exception as e:
        raise Exception('GITHUB API 호출할때 문제가 생겼습니다.')
    finally:
        if conn != None:
            conn.close()

def telegram(id,nick_name,fav_repository,user_date,updated_date,json,conn) : # 데이터 업데이트를 한다. 텔레그램의 경우 그리고 api를 쏜다.
    output_dict = None;
    curs = conn.cursor()
    print(json)
    if json!=[] :
        date = datetime.strptime(user_date, '%Y-%m-%dT%H:%M:%SZ') + timedelta(seconds=+0)
        timestampStr = date.strftime("%Y-%m-%dT%H:%M:%SZ")
        json = [json for json in json if json['commit']['committer']['date'] > timestampStr]


        sql = "UPDATE user SET user_get_date=%s,updated_at=(SELECT DATE_FORMAT(NOW(),'%%Y%%m%%d%%H%%i%%s')) WHERE id = %s AND type='telegram' AND fav_repository=%s"
        curs.execute(sql,(updated_date,id,fav_repository))
    print(json)
    
    date = json[0].get("commit").get("committer").get("date")
    name = json[0].get("commit").get("committer").get("name")
    email = json[0].get("commit").get("committer").get("email")
    msg = json[0].get("commit").get("message")
    url = json[0].get("html_url")

    params = {
        "id" : id,
        "nick_name" : nick_name,
        "date" : date,
        "name" : name,
        "email" : email,
        "msg" : msg,
        "url" : url
    }
    print(id)
    print(nick_name)
    print(date)
    print(name)
    print(email)
    print(msg)
    print(url)
    
    url = "https://alarm-bot-repo.herokuapp.com/api/"

    res = requests.get(url, params=params)
    print(res)

#while True:    # while에 True를 지정하면 무한 루프
#    batch()
#    time.sleep(30)
batch()