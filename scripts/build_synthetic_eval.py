"""Fixed 20 tuning / 10 held-out synthetic intake fixtures, before retrieval runs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# split, caseType, statement, desiredNextStep, expected IDs, type tags
ROWS = [
 ("compare","CIVIL","지인에게 빌려준 돈을 못 받았습니다. 차용증은 없습니다.","계좌 이체와 대화를 준비하고 싶습니다.",["G01"],["의역"]),
 ("compare","CIVIL","임대차 계약이 끝났는데 보증금을 돌려받지 못했습니다.","열쇠 인도와 반환 요청 기록을 정리하고 싶습니다.",["G02"],["법률 용어"]),
 ("compare","CIVIL","주문한 제품과 다른 물건이 와서 반품했는데 환불이 없습니다.","주문 내역과 반품 확인을 모으려 합니다.",["G03"],["의역"]),
 ("compare","CRIMINAL","중고 판매자에게 송금한 뒤 연락이 끊겼습니다.","거래 사기 의심 자료를 정리하려 합니다.",["G04"],["의역"]),
 ("compare","CRIMINAL","인터넷에 저를 가리키는 비방 글이 올라왔습니다.","모욕과 명예훼손 상담 전 게시글을 보관하려 합니다.",["G05"],["법률 용어"]),
 ("compare","CRIMINAL","이미 고소장을 냈는데 빠진 날짜와 대화가 있습니다.","보충 진술과 추가 자료를 정리하려 합니다.",["G06"],["법률 용어"]),
 ("compare","FAMILY","별거 중이고 생활비와 자녀 돌봄에 의견 차이가 있습니다.","이혼 상담 전에 생활 기록을 모으려 합니다.",["G07"],["의역"]),
 ("compare","FAMILY","가족 사망 뒤 남은 재산과 빚을 잘 모릅니다.","상속 상담에 필요한 목록을 만들려 합니다.",["G08"],["법률 용어"]),
 ("compare","OTHER","일한 달의 급여 일부가 들어오지 않았습니다.","미지급 임금과 근무표를 준비하려 합니다.",["G09"],["의역"]),
 ("compare","OTHER","기관에서 통지서를 받았는데 내용이 이해되지 않습니다.","이의 상담 전 수령일과 첨부 자료를 확인하려 합니다.",["G10"],["법률 용어"]),
 ("compare","CIVIL","합성 연락처 010-0000-0000, 돈을 빌려주고 일부만 돌려받았습니다.","남은 대여금 계산 자료를 준비합니다.",["G01"],["합성 PII","법률 용어"]),
 ("compare","CIVIL","합성 이메일 example@example.invalid, 집을 비우는데 수리비 공제로 다툽니다.","보증금 반환 상담 자료를 알고 싶습니다.",["G02"],["합성 PII","의역"]),
 ("compare","CRIMINAL","댓글 화면이 지워질까 걱정됩니다. 여러 사람이 보는 글입니다.","비방 표현의 전체 맥락을 보관하고 싶습니다.",["G05"],["의역"]),
 ("compare","OTHER","급여 명세서와 입금액이 서로 다릅니다.","임금 지급 차이를 월별로 정리하고 싶습니다.",["G09"],["의역"]),
 ("compare","OTHER","오늘 저녁 김치찌개 요리법을 알려 주세요.","재료와 조리 순서가 필요합니다.",[],["무근거"]),
 ("compare","OTHER","달에서 지구까지 우주선 비행 시간을 계산해 주세요.","연료량 공식이 필요합니다.",[],["무근거"]),
 ("compare","CIVIL","해외 특허 출원 명세서 작성과 심사 대응을 알고 싶습니다.","특허 청구항 작성 방법이 필요합니다.",[],["무근거","법률 용어"]),
 ("compare","FAMILY","여권 재발급과 관광 비자 신청 자료를 알고 싶습니다.","해외 여행을 준비합니다.",[],["무근거"]),
 ("compare","CRIMINAL","저작권 음악 라이선스 사용료 산정이 궁금합니다.","공연 계약을 검토하려 합니다.",[],["무근거","법률 용어"]),
 ("compare","OTHER","합성 이메일 nobody@example.invalid, GPU 오버클럭이 궁금합니다.","게임 성능을 높이고 싶습니다.",[],["무근거","합성 PII"]),
 ("holdout","CIVIL","친구가 갚기로 한 금액 중 일부만 갚았습니다.","차용 메모와 송금 내역을 묶고 싶습니다.",["G01"],["의역"]),
 ("holdout","CRIMINAL","물품 대금을 보냈는데 배송 약속 후 판매 계정이 사라졌습니다.","온라인 거래 신고 전 남길 자료가 궁금합니다.",["G04"],["의역"]),
 ("holdout","FAMILY","헤어져 살고 있고 아이를 돌보는 일정이 불분명합니다.","이혼 상담 질문을 정리하고 싶습니다.",["G07"],["의역"]),
 ("holdout","FAMILY","상속 재산 중 채무가 있는지 확인하지 못했습니다.","가족 관계와 재산 자료를 정리하려 합니다.",["G08"],["법률 용어"]),
 ("holdout","OTHER","행정 통지 발송일과 받은 날이 다릅니다.","이의 제기 상담에 가져갈 문서가 궁금합니다.",["G10"],["법률 용어"]),
 ("holdout","CIVIL","합성 연락처 010-0000-0000, 판매 조건과 실제 물품이 달라 반송했습니다.","환불 요청 경위를 정리하고 싶습니다.",["G03"],["합성 PII","의역"]),
 ("holdout","OTHER","재즈 피아노 화성 진행을 추천해 주세요.","연습 악보가 필요합니다.",[],["무근거"]),
 ("holdout","CIVIL","조세 조약에 따른 국제 이중과세 조정이 궁금합니다.","세금 계산 사례가 필요합니다.",[],["무근거","법률 용어"]),
 ("holdout","CRIMINAL","블록체인 합의 알고리즘 코드를 작성해 주세요.","분산 원장 성능을 비교합니다.",[],["무근거"]),
 ("holdout","OTHER","합성 이메일 sample@example.invalid, 토마토 수경 재배를 시작합니다.","양액 비율을 알고 싶습니다.",[],["무근거","합성 PII"]),
]


def main():
    records = [{"questionId": f"Q{i:02d}", "split": split,
                "intake": {"clientName": "합성 학습 인물", "caseType": case,
                           "coreStatement": statement, "desiredNextStep": step},
                "tags": tags, "expectedDocumentIds": expected}
               for i, (split, case, statement, step, expected, tags) in enumerate(ROWS, 1)]
    file = ROOT / "fixtures/rag/evaluation.json"
    file.write_text(json.dumps(records, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"Wrote {len(records)} synthetic DTO records: compare 20 / holdout 10")


if __name__ == "__main__":
    main()
