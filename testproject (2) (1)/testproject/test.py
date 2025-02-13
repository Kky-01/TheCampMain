import re
import urllib.parse
import requests
import json
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import google.generativeai as genai

# ====== 설정 ======
GOOGLE_API_KEY = "AIzaSyAFtCtB_ZfuRKTF8NiNP5lz-5C3WNVuGUk"
NAVER_CLIENT_ID = 'sVLg7QDsZXmBjyWgunV5'
NAVER_CLIENT_SECRET = '9_KNpe6xDN'

genai.configure(api_key=GOOGLE_API_KEY)
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 이미 있다면 그대로 두세요
app.config['SESSION_PERMANENT'] = False  # 세션 만료 설정
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # 세션 지속 시간 설정
#######################
# 간단 유틸 함수들
#######################
def clean_html(text):
    import re
    text = re.sub('<.*?>', '', text)
    text = text.replace('&quot;', '"').replace('&amp;', '&')
    return text

def format_price(price):
    try:
        if price >= 10000:
            man = price//10000
            rem = price % 10000
            if rem > 0:
                return f"{man}만 {rem:,}원"
            return f"{man}만원"
        return f"{price:,}원"
    except:
        return str(price)+"원"

#######################
# (1) 랜딩 페이지
#######################
@app.route("/")
def landing():
    # 첫 화면(큰 검색창)
    # -> templates/landing.html
    return render_template("landing.html")

@app.route("/search")
def search_page():
    # 두 번째 화면(왼쪽 챗 + 오른쪽 상품)
    # -> templates/search.html
    return render_template("search.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 로그인 성공 시
        if username and password:
            # 세션에 사용자 정보 저장
            session['user'] = {'name': username}
            return redirect(url_for('landing'))
        else:
            return "로그인 실패", 401

    return render_template("login.html")

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        # 회원가입 기본 로직 (실제 DB 저장 로직 필요)
        if username and password and email:
            return redirect(url_for('login'))
        else:
            return "회원가입 실패", 400

    return render_template("signup.html")

@app.route('/logout')
def logout():
    # 세션에서 사용자 정보 제거
    session.pop('user', None)
    return redirect(url_for('landing'))

# 나머지 기존 코드 (검색, 챗봇 등) 그대로 유지
# ...
def extract_price_range(text):
    """사용자 메시지에서 가격대, 최저가 등 간단 추출"""
    try:
        match = re.search(r'(\d+)만원대', text)
        if match:
            base = int(match.group(1))
            return {"min":base*10000, "max":(base+10)*10000 -1, "display":f"{base}만원대"}
        return None
    except:
        return None

def search_naver_shopping(query, price_range=None):
    """네이버 쇼핑 API"""
    try:
        sort_option = "sim"
        if price_range and price_range.get("sort")=="price_asc":
            sort_option = "asc"
        url = f"https://openapi.naver.com/v1/search/shop.json?query={urllib.parse.quote(query)}&display=20&sort={sort_option}"
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
        }
        resp = requests.get(url, headers=headers)
        if resp.status_code!=200:
            return []
        items = resp.json().get("items",[])
        
        filtered = []
        for it in items:
            try:
                price = int(it["lprice"])
                # 가격대 필터
                if price_range:
                    if price_range.get("min") and price<price_range["min"]:
                        continue
                    if price_range.get("max") and price>price_range["max"]:
                        continue
                title_clean = clean_html(it["title"])
                # 중복 제거
                if not any(clean_html(x["title"])==title_clean for x in filtered):
                    it["price"] = price
                    it["formatted_price"] = format_price(price)
                    it["title"] = title_clean
                    it["mall_name"] = it.get("mallName","")
                    it["link"] = it["link"]
                    it["image"] = it["image"]
                    filtered.append(it)
            except:
                pass
        return filtered
    except:
        return []

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "").strip()
    mode = data.get("mode", "helper")  # 기본값은 helper
    
    if not user_message:
        return jsonify([{"response": "메시지를 입력하세요."}])
    
    if mode == "helper":
        # 기존 도우미 모드 로직 그대로 유지
        price_range = extract_price_range(user_message)
        keywords = [user_message]
        found_items = []
        responses = []
        
        for kw in keywords:
            items = search_naver_shopping(kw, price_range)
            if items:
                found_items.extend(items)
                for it in items:
                    product_html = f"""
                    <div class="product-card">
                        <button class="bookmark-btn">
                            <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
                            </svg>
                        </button>
                        <div class="product-image-container">
                            <img src="{it['image']}" alt="{it['title']}" class="product-image"/>
                        </div>
                        <div class="product-info">
                            <div class="product-meta">{it.get('mall_name','판매처 정보 없음')}</div>
                            <h3 class="product-title">{it['title']}</h3>
                            <div class="product-price">{it['formatted_price']}</div>
                            <div class="product-recommendation">추천 상품</div>
                            <div class="mt-4">
                                <a href="{it['link']}" target="_blank"
                                   class="block w-full text-center bg-[#FF9999] hover:bg-[#FF6B6B] text-white py-2 px-4 rounded-md transition-colors">
                                   제품 보기
                                </a>
                            </div>
                        </div>
                    </div>
                    """
                    responses.append({"response": product_html, "html": True})
        
        if found_items:
            minp = min(x["price"] for x in found_items)
            maxp = max(x["price"] for x in found_items)
            summary = f"💡 {format_price(minp)}~{format_price(maxp)} 범위의 상품을 찾았어요."
            responses.insert(0, {"response": summary})
        else:
            responses.append({"response": "😅 조건에 맞는 상품을 찾지 못했어요."})
        
        return jsonify(responses)
        
    elif mode == "shopping":
        # 쇼핑비서 모드는 secretary.py에서 처리
        from secretary import handle_shopping_secretary_mode
        responses = handle_shopping_secretary_mode(user_message, search_naver_shopping, format_price)
        return jsonify(responses)
    else:
        return jsonify([{"response": "지원하지 않는 모드입니다."}])

if __name__ == "__main__":
    app.run(debug=True, port=5000)