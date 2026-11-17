# -*- coding: utf-8 -*-
"""보조금24(행정안전부 대한민국 공공서비스(혜택) 정보) 수집 -> data/benefits.json

API: https://api.odcloud.kr/api/gov24/v3 (공공데이터포털 15113968, 자동승인)
- serviceList: 목록+요약 (지원대상·선정기준·지원내용·신청방법·신청기한 포함)
- serviceDetail: 구비서류·문의처·온라인신청URL·법령 (서비스ID로 병합)
인증: 환경변수 DATA_GO_KR_KEY (serviceKey 쿼리 파라미터)

안전장치 (jobs-site 2026-11-10 사고 교훈): 수집이 실패하거나 건수가 직전의
50% 미만이면 직전 data/benefits.json을 유지하고 종료한다 (빈 데이터로 덮지 않음).
"""
import json, os, sys, time, urllib.request, urllib.parse, datetime

KEY = os.environ.get("DATA_GO_KR_KEY", "")
BASE = "https://api.odcloud.kr/api/gov24/v3"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "data", "benefits.json")
PER_PAGE = 1000


def call(op, page):
    q = urllib.parse.urlencode({"serviceKey": KEY, "page": page, "perPage": PER_PAGE, "returnType": "JSON"})
    req = urllib.request.Request(f"{BASE}/{op}?{q}", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    if isinstance(d, dict) and d.get("code", 0) not in (0, None) and "data" not in d:
        raise RuntimeError(f"{op} API 오류: {d.get('code')} {d.get('msg')}")
    return d


def fetch_all(op):
    first = call(op, 1)
    total = int(first.get("totalCount") or 0)
    rows = list(first.get("data") or [])
    pages = (total + PER_PAGE - 1) // PER_PAGE
    for p in range(2, pages + 1):
        d = call(op, p)
        rows += list(d.get("data") or [])
        time.sleep(0.2)
    return rows, total


def main():
    if not KEY:
        print("DATA_GO_KR_KEY 없음", file=sys.stderr); sys.exit(1)
    prev = []
    if os.path.exists(OUT):
        try:
            prev = json.load(open(OUT, encoding="utf-8")).get("data") or []
        except Exception:
            prev = []
    try:
        lst, total = fetch_all("serviceList")
        det, _ = fetch_all("serviceDetail")
    except Exception as ex:
        print(f"수집 실패, 직전 데이터 유지: {ex}", file=sys.stderr)
        if prev:
            return
        sys.exit(1)
    if total and len(lst) < total * 0.9:
        print(f"목록 수집 부족 ({len(lst)}/{total}), 직전 데이터 유지", file=sys.stderr)
        if prev:
            return
        sys.exit(1)
    if prev and len(lst) < len(prev) * 0.5:
        print(f"건수 급감 ({len(lst)} < 직전 {len(prev)}의 50%), 직전 데이터 유지", file=sys.stderr)
        return
    detmap = {d.get("서비스ID"): d for d in det if d.get("서비스ID")}
    items = []
    for r in lst:
        sid = r.get("서비스ID")
        if not sid:
            continue
        d = detmap.get(sid) or {}
        laws = " ".join(x for x in [d.get("법령"), d.get("자치법규"), d.get("행정규칙")] if x)
        items.append({
            "id": sid,
            "name": r.get("서비스명") or "",
            "summary": r.get("서비스목적요약") or "",
            "target": r.get("지원대상") or "",
            "criteria": r.get("선정기준") or "",
            "content": r.get("지원내용") or "",
            "how": r.get("신청방법") or "",
            "deadline": r.get("신청기한") or "",
            "url": r.get("상세조회URL") or "",
            "org": r.get("소관기관명") or "",
            "org_type": r.get("소관기관유형") or "",
            "dept": r.get("부서명") or "",
            "views": int(r.get("조회수") or 0),
            "user_type": r.get("사용자구분") or "",
            "support_type": r.get("지원유형") or "",
            "field": r.get("서비스분야") or "",
            "apply_org": r.get("접수기관") or "",
            "tel": r.get("전화문의") or "",
            "docs": d.get("구비서류") or "",
            "online_url": d.get("온라인신청사이트URL") or "",
            "law": laws,
            "updated": r.get("수정일시") or "",
        })
    payload = {"sample": False, "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
               "sources": ["행정안전부 대한민국 공공서비스(혜택) 정보 (공공데이터포털)"],
               "data": items}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(payload, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"collected {len(items)} (list total {total}, detail {len(det)})")


if __name__ == "__main__":
    main()
