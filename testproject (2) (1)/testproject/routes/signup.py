from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from database import db, User

signup_bp = Blueprint('signup_bp', __name__)

@signup_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        name = request.form.get('name')
        phone = request.form.get('phone')
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('이미 존재하는 아이디입니다.')
            return redirect(url_for('signup_bp.signup'))
        
        new_user = User(username=username, email=email, password=generate_password_hash(password, method='sha256'), name=name, phone=phone)
        db.session.add(new_user)
        db.session.commit()
        
        flash('회원가입이 완료되었습니다. 로그인해주세요.')
        return redirect(url_for('auth_bp.login'))
    
    return render_template('signup.html')