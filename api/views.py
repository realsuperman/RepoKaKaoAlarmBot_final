import MySQLdb
from rest_framework.views import APIView
from rest_framework.response import Response
from . import githubApi
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json, requests
from datetime import datetime, timedelta
from urllib import parse

class UserView(APIView):
    def post(self, request):
        id = request.POST.get('id','')
        fav_repository = request.POST.get('fav_repository','')
        nick_name = 'shchoi'
        type = 'kakao'
        branch = request.POST.get('branch', '')
        try:
            conn = None
            if len(id) == 0:
                raise Exception('아이디는 비어 있으면 안됩니다.')
            if len(fav_repository) == 0:
                raise Exception('관심 레파지토리는 비어 있으면 안됩니다.')
            if len(type) == 0:
                raise Exception('타입은 비어 있으면 안됩니다.')
            if len(branch) == 0:
                raise Exception('브랜치명은 비어 있으면 안됩니다.')
            #conn = MySQLdb.connect(user='seonghun', password='db20192455', db='seonghun$repoalarm',host='seonghun.mysql.pythonanywhere-services.com',charset='utf8')
            conn = MySQLdb.connect(user='root', password='1234', db='open_source', charset='utf8')
            curs = conn.cursor()

            sql = "SELECT DATE_FORMAT(NOW(),'%Y%m%d%H%i%s');"
            curs.execute(sql)
            result = curs.fetchall()

            code = githubApi.getRepositoryInfo(fav_repository, branch ,0);  # url parser를 통해 git api 주소를 가지고 온다.
            if code[0] == 404:
                raise Exception('정상적이지 않은 레파지토리명 입니다')
            git_create_at = code[0]
            git_updated_at = code[1]
            git_api_address = code[2]
            fav_repository = fav_repository+"/branches/"+branch
            sql = "INSERT INTO repository (fav_repository,git_api_address,git_created_at,git_updated_at,created_at,updated_at) " \
                  "VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE UPDATED_AT = %s"
            curs.execute(sql, (fav_repository, git_api_address, git_create_at, git_updated_at, result, result, result))
            sql = "INSERT INTO user (id,fav_repository,nick_name,type,created_at,updated_at,user_get_date) VALUES (%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE UPDATED_AT = %s,NICK_NAME=%s,TYPE=%s,user_get_date=%s"
            curs.execute(sql, (id, fav_repository, nick_name, type, result, result, git_updated_at ,result,nick_name,type,git_updated_at))

            conn.commit()
            return Response("정상적으로 api 호출 완료", status=200)
        except Exception as e:
            if conn != None:
                conn.rollback()
            return Response(str(e), status=404)
        finally:
            if conn != None:
                conn.close()

    def get(self,request):
        id = request.GET.get('id','')
        fav_repository = request.GET.get('fav_repository','')
        nick_name = request.GET.get('nick_name', '')
        type = request.GET.get('type', '')
        branch = request.GET.get('branch', '')

        try:
            if len(id) == 0:
                raise Exception('아이디는 비어 있으면 안됩니다.')
            if len(fav_repository) == 0:
                raise Exception('관심 레파지토리는 비어 있으면 안됩니다.')
            if len(branch) == 0:
                raise Exception('브랜치명은 비어 있으면 안됩니다.')
            type = 'kakao';
            nick_name='shchoi';
            json = batch(id,fav_repository,nick_name,type,branch)
            return Response(json, status=200)
        except Exception as e:
            return Response("error", status=404)

def batch(id,fav_repository,nick_name,type,branch):
    try:
        conn = None
        fav_repository = fav_repository + "/branches/" + branch
        #conn = MySQLdb.connect(user='seonghun', password='db20192455', db='seonghun$repoalarm',host='seonghun.mysql.pythonanywhere-services.com', charset='utf8')
        conn = MySQLdb.connect(user='root', password='1234', db='open_source', charset='utf8')
        curs = conn.cursor()
        sql = "SELECT a.git_api_address,a.fav_repository,b.user_get_date FROM repository a inner join user b on a.fav_repository = b.fav_repository WHERE b.id=%s AND b.type=%s AND b.fav_repository=%s";
        curs.execute(sql, (id,type,fav_repository))
        result = curs.fetchall()

        sql = "SELECT DATE_FORMAT(NOW(),'%Y%m%d%H%i%s');"
        curs.execute(sql)
        time = curs.fetchall()

        for i in result: # 사실 포문 쓰는게 이상하긴 함(1건만 항상 나오므로..)
            dataList = githubApi.getRepositoryInfo(i[0], None , 1)
            if dataList[0] == 404:
                raise Exception('GITHUB API 호출할때 문제가 생겼습니다.')
            sql = "SELECT b.id,b.nick_name,b.type,a.git_api_address,a.fav_repository FROM repository a inner join user b on a.fav_repository = b.fav_repository WHERE b.id=%s AND b.type=%s AND b.fav_repository=%s";
            curs.execute(sql, (id,type,fav_repository))
            result = curs.fetchall()
            for j in result: # 사실 포문 쓰는게 이상하긴 함(1건만 항상 나오므로..)
                sql = "UPDATE user SET user_get_date=(select concat(concat(concat(left(UTC_TIMESTAMP(),10),'T'),(select substring(UTC_TIMESTAMP(),12))),'Z')) WHERE id=%s AND type=%s AND fav_repository=%s"
                curs.execute(sql, (id, type, fav_repository))
                conn.commit()

                str = j[3]
                index = str.find('branches')
                url = str[:index]+"commits"
                branch = str[str.find('branches/'):]
                branch = branch[branch.find('/'):].replace('/','')
                date = datetime.strptime(i[2], '%Y-%m-%dT%H:%M:%SZ') + timedelta(seconds=+1)
                timestampStr = date.strftime("%Y-%m-%dT%H:%M:%SZ")
                content = requests.get(url,headers={'Authorization':'token 6f6d00c786cd3662b25716bf6c6fb6a2084f401d'},params={'sha':branch,'since':timestampStr})
                jsonObject = json.loads(content.content)
                return jsonObject
                #telegram(j[0],j[1],j[4],jsonObject) # 이 부분 수정 필요
    except Exception as e:
        print(e)
        raise Exception('GITHUB API 호출할때 문제가 생겼습니다.')
    finally:
        if conn != None:
            conn.close()

# 프론트에게 레포 관련 정보들을 전달하는 api
class GetRepoInfo (APIView) :
    def get (self, request) :
        try :
            # parameter로 id, repo 가져옴
            id = request.query_params.get('id', '')
            repo = request.query_params.get('repo', '')

            fav_repository = 'https://github.com/' + id + '/' + repo

            branch_lists = []

            index = fav_repository.find('github')
            url = fav_repository[index:]
            index = url.find("/")
            url_repos = "https://api.github.com/repos"+url[index:]
            url_branches = "https://api.github.com/repos"+url[index:]+"/branches"

            # github api에서 정보 가져옴
            content_repos = requests.get(url_repos, headers={'Authorization': 'token 6f6d00c786cd3662b25716bf6c6fb6a2084f401d'})
            jsonObject_repos = json.loads(content_repos.content)

            avatar_url = jsonObject_repos.get("owner").get("avatar_url")
            name = jsonObject_repos.get("name")
            created_at = jsonObject_repos.get("created_at")
            updated_at = jsonObject_repos.get("updated_at")
            stargazers_count = jsonObject_repos.get("stargazers_count")
            forks = jsonObject_repos.get("forks")
            owner = jsonObject_repos.get("owner").get("login")

            content_branches = requests.get(url_branches, headers={'Authorization': 'token 6f6d00c786cd3662b25716bf6c6fb6a2084f401d'})
            jsonObject_branches = json.loads(content_branches.content)
            json_size = len(jsonObject_branches)

            for i in range(1, int(json_size)+1):
                branch_lists.append(jsonObject_branches[i-1].get("name"))

            context = {"avatar_url" : avatar_url, "name" : name, "created_at" : created_at, "updated_at" : updated_at, "stargazers_count" : stargazers_count,  "forks" : forks, "branch_lists" : branch_lists, "owner" : owner}

            return Response(context, status=200)    

        except Exception as e:
            return Response(str(e), status=404)  

class SendAlias (APIView) :
    def get (self, request) :
        try : 
            id = request.query_params.get('id', '')
        
            repoList = []

            conn = None
            conn = MySQLdb.connect(user='seonghun', password='db20192455', db='seonghun$repoalarm',host='seonghun.mysql.pythonanywhere-services.com', charset='utf8')
            curs = conn.cursor()

            sql = 'SELECT nick_name FROM user WHERE id = %s;'
            curs.execute(sql, [id])
            result = curs.fetchall()

            for i in result :
                repoList.append(i[0])
            
            jsonAlias = {"alias" : repoList}

            return Response(jsonAlias, status=200)
            
        except Exception as e :
            return Response(str(e), status=404)

# id와 nick_name에 해당하는 레포 전달해주는 api
class SendGitInfo (APIView) :
    def get (self, request) :
        try :
            id = request.query_params.get('id', '')
            nick_name = request.query_params.get('nick_name', '')

            repo_url = []
            repo_branch = []

            conn = None
            conn = MySQLdb.connect(user='seonghun', password='db20192455', db='seonghun$repoalarm',host='seonghun.mysql.pythonanywhere-services.com', charset='utf8')
            curs = conn.cursor()

            sql = 'SELECT fav_repository FROM user WHERE id = %s and nick_name = %s;'
            curs.execute(sql, (id, nick_name))
            result = curs.fetchall()

            for i in result :
                index = i[0].find('branches')-1
                repo_url = i[0][:index]
                index = i[0].rfind('/')+1
                repo_branch = i[0][index:]

            json_git = {"repoUrl" : repo_url, "repoBranch" : repo_branch}
            return Response(json_git, status=200)

        except Exception as e :
            return Response(str(e), status=404)


# id에 해당하는 nick_name목록 전달
def sendList (kakao_id) :
    try : 
        repoList = []

        conn = None
        conn = MySQLdb.connect(user='seonghun', password='db20192455', db='seonghun$repoalarm',host='seonghun.mysql.pythonanywhere-services.com', charset='utf8')
        curs = conn.cursor()

        sql = 'SELECT nick_name FROM user WHERE id = %s;'
        curs.execute(sql, [kakao_id])
        result = curs.fetchall()

        for i in result :
            repoList.append(i[0])

        return repoList

    except Exception as e :
        return print(str(e))

# id와 nick_name에 해당하는 레포 전달
def returnGit (id, nick_name) :
    try : 
        conn = None
        conn = MySQLdb.connect(user='seonghun', password='db20192455', db='seonghun$repoalarm',host='seonghun.mysql.pythonanywhere-services.com', charset='utf8')
        curs = conn.cursor()

        sql = 'SELECT fav_repository FROM user WHERE id = %s and nick_name = %s;'
        curs.execute(sql, (id, nick_name))
        result = curs.fetchall()

        for i in result :
            index = i[0].find('branches')-1
            repo_url = i[0][:index]
            index = i[0].rfind('/')+1
            repo_branch = i[0][index:]
        
        return repo_url, repo_branch

    except Exception as e :
        return print(str(e))

def insertDb (id, fav_repository, type, nick_name, branch) :
    try:
        conn = None
        if len(id) == 0:
            raise Exception('아이디는 비어 있으면 안됩니다.')
        if len(fav_repository) == 0:
            raise Exception('관심 레파지토리는 비어 있으면 안됩니다.')
        if len(nick_name) == 0:
            raise Exception('별명은 비어 있으면 안됩니다.')
        if len(type) == 0:
            raise Exception('타입은 비어 있으면 안됩니다.')
        if len(branch) == 0:
            raise Exception('브랜치명은 비어 있으면 안됩니다.')
        conn = MySQLdb.connect(user='seonghun', password='db20192455', db='seonghun$repoalarm',host='seonghun.mysql.pythonanywhere-services.com',charset='utf8')
        #conn = MySQLdb.connect(user='root', password='1234', db='open_source', charset='utf8')
        curs = conn.cursor()

        sql = "SELECT DATE_FORMAT(NOW(),'%Y%m%d%H%i%s');"
        curs.execute(sql)
        result = curs.fetchall()

        code = githubApi.getRepositoryInfo(fav_repository, branch ,0);  # url parser를 통해 git api 주소를 가지고 온다.
        if code[0] == 404:
            raise Exception('정상적이지 않은 레파지토리명 입니다')
        git_create_at = code[0]
        git_updated_at = code[1]
        git_api_address = code[2]
        fav_repository = fav_repository+"/branches/"+branch
        sql = "INSERT INTO repository (fav_repository,git_api_address,git_created_at,git_updated_at,created_at,updated_at) " \
                "VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE UPDATED_AT = %s"
        curs.execute(sql, (fav_repository, git_api_address, git_create_at, git_updated_at, result, result, result))

        sql = "INSERT INTO user (id,fav_repository,nick_name,type,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE UPDATED_AT = %s,NICK_NAME=%s,TYPE=%s"
        curs.execute(sql, (id, fav_repository, nick_name, type, result, result, result,nick_name,type))

        conn.commit()
        return print("github API 호출 성공")

    except Exception as e:
        if conn != None:
            conn.rollback()
        return print(str(e))
        
    finally:
        if conn != None:
            conn.close()

##########################################################################################kakao

@csrf_exempt
def barcode(request):
    answer = ((request.body).decode('utf-8'))
    return_json_str = json.loads(answer)
    return_str_skill = return_json_str['action']['name']
    return_str_git = return_json_str['action']['detailParams']['barcode']['value']
    return_str_id = return_json_str['userRequest']['user']['properties']['plusfriendUserKey']

    return_str_git_barcodeData = json.loads(return_str_git)

    temp = str(return_str_git_barcodeData)

    index = temp.find('\'')
    temp = temp.replace(temp[index], "\"", 1)
    index = temp.find('\'')
    temp = temp.replace(temp[index], "\"", 1)
    index = temp.find('\'')
    temp = temp.replace(temp[index], "", 1)
    index = temp.find('\'')
    temp = temp.replace(temp[index], "", 1)

    return_str_git_barcodeData = json.loads(temp)

    return_str_git_url = return_str_git_barcodeData['barcodeData']['url']
    return_str_type = return_str_git_barcodeData['barcodeData']['type']
    return_str_alias = return_str_git_barcodeData['barcodeData']['alias']
    return_str_branch = return_str_git_barcodeData['barcodeData']['branch']

    return_str_alias = parse.unquote(return_str_alias)

    insertDb(return_str_id, return_str_git_url, return_str_type, return_str_alias, return_str_branch)
    
    if return_str_skill == '바코드':
        return JsonResponse({
            'version': "2.0",
            'template': {
                'outputs': [{
                    'simpleText': {
                        'text': f"[{return_str_alias}] 등록 완료!"
                    }
                }],
            }
        })

@csrf_exempt
def repoList(request):
    answer = ((request.body).decode('utf-8'))
    return_json_str=json.loads(answer)
    return_str_skill=return_json_str['action']['name']
    return_str_id=return_json_str['userRequest']['user']['properties']['plusfriendUserKey']

    repoList_arr=sendList(return_str_id)
    return_str_repoList="등록하신 레포 목록입니다.\n"

    for i in range(0,len(repoList_arr),1):
        return_str_repoList=return_str_repoList+str(i+1)+". "+repoList_arr[i]
        if(i<len(repoList_arr)-1):
            return_str_repoList+="\n"

    if return_str_skill == '레포리스트':
        return JsonResponse({
            'version': "2.0",
            'template': {
                'outputs': [{
                    'simpleText': {
                        'text': f"{return_str_repoList}"
                    }
                }],
                'quickReplies':[{
                    'label': '입력하기',
                    'action': 'message',
                }]
            }
        })

def changeKST(ISO):
    yyyymmdd, time = ISO.split('T')
    yyyy, mm, dd = yyyymmdd.split('-')
    hour, minute, second = time.split(':')
    second,Z = second.split('Z')
    hour=int(hour)+9
    if hour>=24:
        hour-=24
    hour=str(hour)
    #KST = yyyy + "년" + mm + "월" + dd + "일 " + hour + "시" + minute + "분" + second + "초"
    KST = yyyymmdd + " " + hour + ":" + minute + ":" + second
    return KST

@csrf_exempt
def repoStatus(request):
    answer = ((request.body).decode('utf-8'))
    return_json_str = json.loads(answer)
    return_str_skill = return_json_str['action']['name']
    return_str_id = return_json_str['userRequest']['user']['properties']['plusfriendUserKey']
    repoList_arr = sendList(return_str_id)
    
    return_str_repoAlias = int(return_json_str['action']['detailParams']['repoAlias']['value'])
    return_str_git_url, return_str_git_branch = returnGit(return_str_id,repoList_arr[return_str_repoAlias-1])

    res = batch(return_str_id, return_str_git_url, repoList_arr[return_str_repoAlias-1], 'kakao', return_str_git_branch)

    return_str_text=res

    if res == []:
        return_str_text = "해당 레포 업데이트 사항이 없습니다"

    elif res == None:
        return_str_text = "해당 레포 업데이트 사항이 없습니다"

    else :
        ISO = res[0].get("commit").get("committer").get("date")
        KST = changeKST(ISO)
        return_str_text = f"[{repoList_arr[return_str_repoAlias-1]}] 최근 커밋 이력입니다.\n"
        return_str_text = return_str_text + "날짜 : " + KST + "\n"
        return_str_text = return_str_text + "이름 : " + res[0].get("commit").get("committer").get("name") + "\n"
        return_str_text = return_str_text + "이메일 : " + res[0].get("commit").get("committer").get("email") + "\n"
        return_str_text = return_str_text + "커밋메세지 : " + res[0].get("commit").get("message") + "\n"
        return_str_text = return_str_text + "주소 : " + res[0].get("html_url")

    if return_str_skill == '레포상태':
        return JsonResponse({
            'version': "2.0",
            'template': {
                'outputs': [{
                    'simpleText': {
                        'text': f"{return_str_text}"
                    }
                }],
            }
        })
