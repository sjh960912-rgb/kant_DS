"""
이상치_목록_판정.csv 상위 건(중앙값대비(배) 내림차순)에 대해
공공데이터포털 "산지공판장 경락가격정보" API(OrgPriceJointMarketService.getJointMarketPriceList)로
실제 거래 여부를 조회하고, 외부확인결과 컬럼을 채운 새 CSV를 저장한다.

실행 전 준비물:
  - 환경변수 API_KEY 에 data.go.kr 일반 인증키(디코딩된 값) 설정
  - pip install requests

사용법:
  API_KEY="발급받은키" python scripts/verify_outliers.py 입력.csv 출력.csv [확인할건수]

주의:
  - 이 스크립트는 네트워크가 막힌 환경에서 작성되어 실제 API 호출 테스트를 하지 못했다.
  - 먼저 TOP_N=1 로 한 건만 돌려서 응답이 기대한 구조로 오는지, jmrktCd/delngDe 매칭이
    맞는지 확인한 뒤 전체로 넓히는 것을 권장한다.
"""
import csv
import os
import sys
import time
import datetime as dt
import xml.etree.ElementTree as ET
import requests

BASE_URL = "https://apis.data.go.kr/B552895/openapi/service/OrgPriceJointMarketService/getJointMarketPriceList"
SLEEP_SECONDS = 1
NUM_OF_ROWS = 500  # 공판장+일자 하나에 거래 건수가 이보다 많으면 페이징 추가 필요


def daterange(period_str):
    start_s, end_s = [s.strip() for s in period_str.split("~")]
    start = dt.datetime.strptime(start_s, "%Y-%m-%d").date()
    end = dt.datetime.strptime(end_s, "%Y-%m-%d").date()
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)


def parse_response(raw_text, content_type):
    """JSON 또는 XML 응답 모두 처리해서 item dict 리스트를 반환한다."""
    items = []
    result_code, result_msg = None, None
    text = raw_text.strip()
    if text.startswith("{"):
        import json
        data = json.loads(text)
        body = data.get("response", {}).get("body", {})
        header = data.get("response", {}).get("header", {})
        result_code = header.get("resultCode")
        result_msg = header.get("resultMsg")
        raw_items = body.get("items")
        if isinstance(raw_items, dict):
            raw_items = raw_items.get("item", [])
        if isinstance(raw_items, dict):
            raw_items = [raw_items]
        items = raw_items or []
    else:
        root = ET.fromstring(text)
        header = root.find("header")
        if header is not None:
            result_code = (header.findtext("resultCode") or "").strip()
            result_msg = (header.findtext("resultMsg") or "").strip()
        for item_el in root.findall(".//items/item"):
            items.append({child.tag: (child.text or "") for child in item_el})
    return result_code, result_msg, items


def fetch_day(service_key, jmrkt_cd, delng_de):
    """특정 공판장코드 + 경락일자(YYYYMMDD)의 전체 거래 품목 레코드를 가져온다."""
    all_items = []
    page_no = 1
    while True:
        params = {
            "ServiceKey": service_key,
            "numOfRows": NUM_OF_ROWS,
            "pageNo": page_no,
            "delngDe": delng_de,
            "jmrktCd": jmrkt_cd,
            "_type": "json",
        }
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        result_code, result_msg, items = parse_response(resp.text, resp.headers.get("Content-Type", ""))
        if result_code not in (None, "0000", "00"):
            raise RuntimeError(f"API error {result_code}: {result_msg} (raw={resp.text[:300]})")
        all_items.extend(items)
        time.sleep(SLEEP_SECONDS)
        if len(items) < NUM_OF_ROWS:
            break
        page_no += 1
    return all_items


def matches_species(item, species_cd, item_cd):
    new_sp = (item.get("stdSpciesNewCode") or "").strip()
    old_sp = (item.get("stdSpciesCode") or "").strip()
    new_it = (item.get("stdPrdlstNewCode") or "").strip()
    old_it = (item.get("stdPrdlstCode") or "").strip()
    if species_cd and species_cd in (new_sp, old_sp):
        return True
    if item_cd and item_cd in (new_it, old_it) and not (new_sp or old_sp):
        return True
    return False


def verify_row(service_key, row):
    jmrkt_cd = row["공판장코드"].strip()
    species_cd = row["품종코드"].strip()
    item_cd = species_cd[:4] if len(species_cd) >= 4 else ""

    total_qty = 0.0
    total_amt = 0.0
    matched_days = 0
    errors = []

    for d in daterange(row["조회기간"]):
        delng_de = d.strftime("%Y%m%d")
        try:
            items = fetch_day(service_key, jmrkt_cd, delng_de)
        except Exception as e:
            errors.append(f"{delng_de}:{e}")
            continue
        for it in items:
            if not matches_species(it, species_cd, item_cd):
                continue
            try:
                qty = float(it.get("delngQy") or 0)
                price = float(it.get("sbidPric") or 0)
            except ValueError:
                continue
            total_qty += qty
            total_amt += qty * price
            matched_days += 1

    if matched_days == 0:
        status = "조회 안 됨"
        evidence = "해당 기간/공판장/품종 조합으로 조회된 거래 레코드 없음"
        if errors:
            evidence += f" (API 오류 {len(errors)}건: {errors[:3]})"
        return status, evidence

    api_avg_price = total_amt / total_qty if total_qty else 0
    csv_qty = float(row["총반입량(kg)"] or 0)
    csv_avg_price = float(row["평균가(원/kg)"] or 0)

    qty_close = csv_qty > 0 and abs(total_qty - csv_qty) / csv_qty <= 0.1
    price_close = csv_avg_price > 0 and abs(api_avg_price - csv_avg_price) / csv_avg_price <= 0.1

    if qty_close and price_close:
        status = "일치(실제 거래)"
    else:
        status = "불일치(오류 가능성)"

    evidence = (
        f"API 반입량={total_qty:.2f}kg(CSV {csv_qty}), "
        f"API 평균가={api_avg_price:.1f}원/kg(CSV {csv_avg_price})"
    )
    if errors:
        evidence += f" / API 오류 {len(errors)}건"
    return status, evidence


def select_target_rows(rows, top_n):
    def rank_key(r):
        try:
            return float(r["중앙값대비(배)"])
        except (KeyError, ValueError):
            return 0.0

    if rows and "확인순위" in rows[0]:
        targeted = [r for r in rows if (r.get("확인순위") or "").strip() == "1"]
        if targeted:
            return targeted[:top_n]
    return sorted(rows, key=rank_key, reverse=True)[:top_n]


def main():
    if len(sys.argv) < 3:
        print("사용법: python verify_outliers.py 입력.csv 출력.csv [확인할건수=5]")
        sys.exit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]
    top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    service_key = os.environ.get("API_KEY")
    if not service_key:
        print("환경변수 API_KEY가 설정되어 있지 않습니다.")
        sys.exit(1)

    with open(input_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = [r for r in reader if r.get("시점")]

    targets = select_target_rows(rows, top_n)
    target_keys = {id(r) for r in targets}

    out_fieldnames = fieldnames + ["외부확인결과"]
    results = []
    for row in rows:
        new_row = dict(row)
        if id(row) in target_keys:
            print(f"조회 중: {row['시점']} {row['공판장명']} {row['품목명']}/{row['품종명']}...")
            status, evidence = verify_row(service_key, row)
            new_row["외부확인결과"] = f"{status} | {evidence}"
            print(f"  -> {status} | {evidence}")
        else:
            new_row["외부확인결과"] = ""
        results.append(new_row)

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"완료: {output_path}")


if __name__ == "__main__":
    main()
