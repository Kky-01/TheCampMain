from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import requests
import os
import re  # 정규식 활용
from difflib import get_close_matches  # 유사 단어 찾기

app = Flask(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyAFtCtB_ZfuRKTF8NiNP5lz-5C3WNVuGUk")  # 실제 API 키 입력 필요
genai.configure(api_key=GOOGLE_API_KEY)

CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "sVLg7QDsZXmBjyWgunV5")  # 실제 값 입력 필요
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "'9_KNpe6xDN")  # 실제 값 입력 필요

# 사전에 등록된 상품 키워드 리스트 (오타 보정용)
COMMON_PRODUCTS = ["아이폰", "갤럭시", "노트북", "맥북", "에어팟", "게이밍 노트북", "갤럭시 워치", "아이패드"]

# 네이버 쇼핑 API 호출
def search_naver_shopping(query):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET,
    }
    params = {
        "query": query,
        "display": 3,
        "sort": "asc",
    }
    response = requests.get(url, headers=headers, params=params)

    print(f"[DEBUG] 네이버 API 응답 코드: {response.status_code}")
    
    if response.status_code == 200:
        return response.json().get("items", [])
    else:
        print(f"네이버 API 호출 실패: {response.status_code}, {response.text}")  # 디버깅 로그
        return None

# 상품 검색을 위한 키워드 정제 함수
def extract_product_name(user_message):
    # '최저가', '가격' 등의 단어 제거
    clean_message = re.sub(r"(최저가|가격|알려줘|추천해줘|어때)", "", user_message, flags=re.IGNORECASE).strip()
    return clean_message

# 오타 자동 보정 함수
def correct_spelling(user_input):
    words = user_input.split()
    corrected_words = []

    for word in words:
        # 사전에 있는 단어와 비교하여 가장 가까운 단어 찾기
        match = get_close_matches(word, COMMON_PRODUCTS, n=1, cutoff=0.7)
        if match:
            corrected_words.append(match[0])  # 가장 유사한 단어로 교체
        else:
            corrected_words.append(word)  # 수정할 단어가 없으면 그대로 사용

    return " ".join(corrected_words)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_message = request.json.get("message")
        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        # 검색어 정제 및 오타 보정
        product_query = extract_product_name(user_message)
        corrected_query = correct_spelling(product_query)

        print(f"[DEBUG] 입력된 검색어: {product_query} → 보정된 검색어: {corrected_query}")

        # AI 기본 응답 설정
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(user_message)

        response_text = response.text if hasattr(response, "text") else "죄송합니다. 답변을 생성할 수 없습니다."

        # 최저가 검색 요청인지 확인
        if "최저가" in user_message or "가격" in user_message:
            items = search_naver_shopping(corrected_query)
            if items:
                product_results = [
                    {
                        "title": re.sub("<.*?>", "", item["title"]),  # HTML 태그 제거
                        "price": f"{item['lprice']}원",
                        "link": item["link"],
                        "image": item["image"],
                    }
                    for item in items
                ]
                return jsonify({
                    "response": f"🔍 '{corrected_query}' 최저가 검색 결과입니다!",
                    "products": product_results
                }), 200
            else:
                response_text = f"😢 '{corrected_query}'에 대한 검색 결과가 없습니다. 검색어를 확인해 주세요."

        return jsonify({"response": response_text}), 200

    except Exception as e:
        print(f"에러 발생: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
