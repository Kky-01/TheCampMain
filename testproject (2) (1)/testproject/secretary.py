import re
import json
import google.generativeai as genai

def handle_shopping_secretary_mode(user_message, search_naver_shopping, format_price):
    try:
        # 1. LLM으로 필요한 품목 분석
        parsed = parse_shopping_request_with_llm(user_message)
        items = parsed.get("items", [])
        price_limit = parsed.get("price_limit")
        
        if not items:
            return [{"response": "필요한 품목을 파악하지 못했습니다."}]
            
        # 2. 초기 응답
        responses = [{"response": f"필요한 품목을 찾았습니다: {', '.join(items)}"}]
        
        # 3. 플랫폼별 검색
        platforms = ["G마켓", "11번가", "쿠팡"]
        valid_baskets = []  
        
        for platform in platforms:
            basket_items = []
            total_price = 0
            
            for item in items:
                found_items = search_platform_items(platform, item, price_limit, search_naver_shopping)
                if found_items:
                    sorted_items = sorted(found_items, key=lambda x: x["price"])
                    item_info = sorted_items[0]
                    
                    if price_limit is None or total_price + item_info["price"] <= price_limit:
                        basket_items.append(item_info)
                        total_price += item_info["price"]
            
            if len(basket_items) == len(items) and (price_limit is None or total_price <= price_limit):
                basket = {
                    "platform": platform,
                    "items": basket_items,
                    "total_price": total_price
                }
                valid_baskets.append(basket)
        
        if valid_baskets:
            valid_baskets.sort(key=lambda x: x["total_price"])
            all_baskets_html = ""
            for basket in valid_baskets:
                all_baskets_html += generate_platform_basket_html(basket, format_price)
                
            responses.append({
                "response": f"""
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6 max-h-[calc(100vh-200px)] overflow-y-auto">
                    {all_baskets_html}
                </div>
                """,
                "html": True
            })
        else:
            responses.append({
                "response": f"죄송합니다. {format_price(price_limit) if price_limit else ''} 이내로 모든 상품을 찾지 못했습니다."
            })
            
        return responses
        
    except Exception as e:
        print("쇼핑비서 모드 오류:", e)
        return [{"response": "처리 중 오류가 발생했습니다."}]

def parse_shopping_request_with_llm(user_message):
    try:
        model = genai.GenerativeModel("gemini-pro")
        prompt = f"""
        사용자의 요청을 분석해 필요한 품목 리스트와 가격 제한을 추출하세요.
        결과는 다음 형식의 JSON으로 반환하세요:
        {{
          "items": ["필요한 품목1", "필요한 품목2", ...],
          "price_limit": 가격제한(없으면 null)
        }}
        
        예시1) 
        입력: "김치찌개 재료가 필요해"
        출력: {{"items": ["김치", "돼지고기", "두부", "대파", "마늘", "고춧가루"], "price_limit": null}}
        
        예시2)
        입력: "겨울철 스키장 룩을 50만원 내로 맞추고 싶어"
        출력: {{"items": ["스키복", "스키바지", "스키장갑", "스키고글", "방한내의"], "price_limit": 500000}}
        
        실제 입력: {user_message}
        """
        resp = model.generate_content(prompt)
        result = resp.text.strip()
        return json.loads(result)
    except Exception as e:
        print("LLM 분석 오류:", e)
        return {"items": [], "price_limit": None}

def search_platform_items(platform, item_name, price_limit, search_naver_shopping):
    try:
        items = search_naver_shopping(
            f"{platform} {item_name}", 
            {"max": price_limit} if price_limit else None
        )
        
        platform_keywords = {
            "11번가": ["11번가", "11ST", "11STREET"],
            "G마켓": ["G마켓", "지마켓", "GMARKET"],
            "쿠팡": ["쿠팡", "COUPANG"]
        }
        
        keywords = platform_keywords.get(platform, [platform])
        platform_items = [
            item for item in items 
            if any(kw.lower() in item["mall_name"].lower() for kw in keywords)
        ]
        
        return platform_items[:1] if platform_items else []
    except Exception as e:
        print(f"{platform} 검색 오류:", e)
        return []

def generate_platform_basket_html(basket, format_price):
    platform = basket["platform"]
    items = basket["items"]
    total_price = basket["total_price"]
    
    items_html = ""
    for item in items:
        items_html += f"""
        <div class="shopping-basket-item">
            <a href="{item['link']}" target="_blank" class="flex items-center flex-1">
                <img src="{item['image']}" class="w-16 h-16 object-cover rounded" alt="{item['title']}"/>
                <div class="ml-3 flex-1">
                    <div class="text-sm font-medium">{item['title']}</div>
                    <div class="text-[#FF6B6B] font-bold mt-1">{format_price(item['price'])}</div>
                </div>
            </a>
        </div>
        """
    
    return f"""
    <div class="shopping-basket-card">
        <div class="shopping-basket-header">
            <div class="text-lg font-bold">{platform}</div>
            <div class="text-sm text-gray-500">총 {len(items)}개 상품</div>
        </div>
        <div class="shopping-basket-items">
            {items_html}
        </div>
        <div class="p-4 bg-gray-50 flex items-center justify-between">
            <span>총 금액</span>
            <span class="text-lg font-bold text-[#FF6B6B]">{format_price(total_price)}</span>
        </div>
    </div>
    """