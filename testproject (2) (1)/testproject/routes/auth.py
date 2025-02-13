from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# OAuth 설정
KAKAO_CLIENT_ID = "1b69e627c9483630f2081681f6cad76e"
NAVER_CLIENT_ID = "vAKV7oVZWM6lQk_x7fXw"
NAVER_CLIENT_SECRET = "UmuvQPfTHO"

KAKAO_REDIRECT_URI = "http://127.0.0.1:5000/auth/kakao/callback"
NAVER_REDIRECT_URI = "http://127.0.0.1:5000/auth/naver/callback"

# 데이터베이스 모델 (회원 정보 저장)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            flash('아이디 또는 비밀번호를 확인해주세요.')
            return redirect(url_for('login'))

        login_user(user, remember=remember)
        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        # 중복 아이디 체크
        user = User.query.filter_by(username=username).first()
        if user:
            flash('이미 존재하는 아이디입니다.')
            return redirect(url_for('signup'))

        # 새 사용자 추가
        new_user = User(username=username, email=email, password=generate_password_hash(password, method='sha256'))
        db.session.add(new_user)
        db.session.commit()

        # ✅ 회원가입 후 자동 로그인
        login_user(new_user)

        # ✅ 회원가입 후 메인 페이지로 리디렉트
        return redirect(url_for('index'))

    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# 네이버 로그인
@app.route('/naver_login')
def naver_login():
    return redirect(f"https://nid.naver.com/oauth2.0/authorize?response_type=code&client_id={NAVER_CLIENT_ID}&redirect_uri={NAVER_REDIRECT_URI}&state=RANDOM_STATE")

@app.route('/auth/naver/callback')
def naver_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    token_response = requests.post(
        "https://nid.naver.com/oauth2.0/token",
        data={
            "grant_type": "authorization_code",
            "client_id": NAVER_CLIENT_ID,
            "client_secret": NAVER_CLIENT_SECRET,
            "code": code,
            "state": state
        }
    ).json()

    access_token = token_response.get("access_token")

    user_info = requests.get(
        "https://openapi.naver.com/v1/nid/me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    if user_info.get("resultcode") == "00":
        user_data = user_info.get("response", {})
        session['user'] = {
            'name': user_data.get('name', '네이버 사용자'),
            'provider': 'naver'
        }
    return redirect(url_for('index'))

# 카카오 로그인
@app.route('/kakao_login')
def kakao_login():
    return redirect(f"https://kauth.kakao.com/oauth/authorize?response_type=code&client_id={KAKAO_CLIENT_ID}&redirect_uri={KAKAO_REDIRECT_URI}")

@app.route('/auth/kakao/callback')
def kakao_callback():
    code = request.args.get("code")

    token_response = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": KAKAO_CLIENT_ID,
            "redirect_uri": KAKAO_REDIRECT_URI,
            "code": code
        }
    ).json()

    access_token = token_response.get("access_token")

    user_info = requests.get(
        "https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    if user_info:
        session['user'] = {
            'name': user_info.get('properties', {}).get('nickname', '카카오 사용자'),
            'provider': 'kakao'
        }
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
