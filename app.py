from flask          import Flask, render_template, jsonify, request, redirect, url_for
from pymongo        import MongoClient
import datetime
from datetime       import datetime, timedelta

import jwt
import hashlib

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = "./static/profile_pics"

SECRET_KEY = 'jinsooenujinjungeun'

client = MongoClient('52.78.71.76', 27017, username="test", password="test")
db = client.db_eat_cloud

# 토큰 확인
@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        if not token_receive:
            return render_template('mainpage.html')
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        user_info = db.users.find_one({"username": payload["id"]})
        return render_template('mainpage.html', user_info=user_info)

    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))

# 로그인
@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)

@app.route('/sign_in', methods=['POST'])
def sign_in():
    # 로그인
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
         'id': username_receive,
         'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,                               # 아이디
        "password": password_hash,                                  # 비밀번호
        "profile_name": username_receive,                           # 프로필 이름 기본값은 아이디
        "profile_pic": "",                                          # 프로필 사진 파일 이름
        "profile_pic_real": "profile_pics/profile_placeholder.png", # 프로필 사진 기본 이미지
        "profile_info": ""                                          # 프로필 한 마디
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})


@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})

@app.route('/main', methods=["GET"])
def mainpage():
    all_store = list(db.store.find({}, {'_id': False}))
    return jsonify({"all_store": all_store})


@app.route('/search', methods=["GET"])
def search():
    area = request.args.get("area")
    menu = request.args.get("menu")
    visit = request.args.get("visit")
    search = list(db.store.find({"seoul_qu": area, "poplular_menu": menu, "purpose": visit}, {"_id": False}))
    return jsonify({"search": search})


@app.route('/store', methods=["GET"])
def store():
    title    = request.args.get("title")
    stores   = list(db.store.find({"title": title}, {"_id": False}))
    reviews  = list(db.reviews.find({"store": title}, {"_id": False}))
    return render_template('detail.html',stores = stores, reviews = reviews)


# 리뷰 남기기
@app.route('/post', methods=['POST'])
def posting():
    db.reviews.drop()
    token_receive = request.cookies.get('mytoken')

    try:
        payload        = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        user_info      = db.users.find_one({"username": payload["id"]})
        review_receive = request.form['review_give']
        store          = request.form["store"]
        now            = datetime.now()
        time           = now.strftime('%Y년 %m월 %d일 %H시 %M분')
        if len(review_receive) < 5:
            return jsonify({"msg" : "리뷰를 5자이상 달아주세요"})
        doc = {
            'review': review_receive,
            'store': store,
            'user': user_info,
            'time': time
        }
        db.reviews.insert_one(doc)
        return jsonify({'msg': '리뷰를 저장했습니다.'})

    except jwt.ExpiredSignatureError:
        return jsonify({'msg': '로그인 시간이 만료됐습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'msg': "로그인 해주세요"})


# 리뷰 보여주기
@app.route('/review', methods=['GET'])
def read_review():
    store = request.args.get("store")
    reviews = list(db.reviews.find({"store": store}, {'_id': False}))
    return render_template('detail.html',reviews = reviews)


# 좋아요 업데이트
@app.route('/like', methods=['POST'])
def like():

    token_receive = request.cookies.get('mytoken')

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        store = request.form['store']
        user_info = db.like.find_one({"user": payload["id"], "store" : store})

        if user_info is None:
            db.like.insert_one({
                    "like"  : 1,
                    "store" : store,
                    "user"  : payload["id"]
            }, {"_id" : False})

        else:
            return jsonify({"msg" : "이미 좋아요 하였습니다"})
        return jsonify({"like" : db.like.count()})

    except jwt.ExpiredSignatureError:
        return jsonify({'msg': '로그인 시간이 만료됐습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'msg': "로그인 해주세요"})

@app.route('/show', methods=['GET'])
def show():
    store = request.args.get("store")
    likes = list(db.like.find({"store" : store}, {"_id" : False}))

    if not likes:
        like = 0
    else:
        like = len(likes)

    return jsonify({"like" : like})


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
