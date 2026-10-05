import os
import requests

BASE_URL = "https://apis.data.go.kr/B552895/openapi/service/OrgPriceJointMarketService/getJointMarketPriceList"

service_key = os.environ["API_KEY"]

base_params = {
    "ServiceKey": service_key,
    "numOfRows": 20,
    "pageNo": 1,
    "delngDe": "20210412",   # 조회기간(2021-04-11~04-20) 안의 하루
    "jmrktCd": "4058200313",  # 1번 건 공판장코드
}

trials = [
    ("기본(XML, _type 없음)", dict(base_params)),
    ("JSON 요청 (_type=json)", {**base_params, "_type": "json"}),
    ("JSON 요청 (type=json)", {**base_params, "type": "json"}),
]

for label, params in trials:
    print("=" * 60)
    print(label)
    resp = requests.get(BASE_URL, params=params, timeout=15)
    print("요청 URL:", resp.url)
    print("HTTP 상태코드:", resp.status_code)
    print("응답 원문(앞 1500자):")
    print(resp.text[:1500])
    print()
