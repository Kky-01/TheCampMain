from flask import Flask, request, render_template
import requests
import json

app = Flask(__name__)

# 네이버 API 정보
CLIENT_ID = "su5gJdNyBtu6noZspgWM"
CLIENT_SECRET = "ogs0nGP4BZ"

# 네이버 쇼핑 검색 API 요청 함수
def search_naver_shopping(query):
    url = "https://openapi.naver.com/v1/search/shop.json"  # ✅ URL 확인
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET,
        "Content-Type": "application/json",
        "Accept": "application/json"  # ✅ 401 오류 해결을 위해 추가
    }
    params = {
        "query": query,
        "display": 10,  # 최대 10개 결과 표시
        "sort": "sim"   # 관련도순 정렬
    }

    # ✅ 반드시 GET 요청으로 보내야 함
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        print("🔍 API 응답 데이터:", json.dumps(data, indent=4, ensure_ascii=False))  # 응답 확인
        return data["items"]
    else:
        print(f"❌ 네이버 API 오류! 상태 코드: {response.status_code}, 응답: {response.text}")
        return None

# 웹 페이지 (사용자가 검색할 수 있는 폼 제공)
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        query = request.form["query"]  # 사용자가 입력한 검색어
        results = search_naver_shopping(query)  # 네이버 API에서 검색

        print(f"🔍 검색어: {query}, 결과 개수: {len(results) if results else 0}")  # 검색어와 결과 개수 출력
        return render_template("na.html", query=query, results=results)

    return render_template("na.html", query=None, results=None)

if __name__ == "__main__":
    app.run(debug=False)  # ✅ Debug Mode 비활성화
