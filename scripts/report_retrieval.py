"""Recompute saved evaluation metrics only; no model, search, tuning or confirm rerun."""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.rag.evaluation import metrics
from app.rag.schemas import Evidence

SET_NAMES = {"compare":"비교20", "holdout":"확인10"}


def rejection_analysis(report, frozen):
    """Explain saved decisions only; never fit thresholds or execute retrieval."""
    if frozen["thresholds"] != report["thresholds"]:
        raise ValueError("Frozen thresholds do not match saved evaluation")
    lines = []
    for qid, mode in (("Q22","vector"),("Q21","lex"),("Q23","lex")):
        row = next(r for r in report["rows"] if r["questionId"]==qid)
        top = row[mode]["allDocumentScores"]
        first, second = top[0], top[1] if len(top)>1 else None
        gap = first["score"]-second["score"] if second else None
        rule = frozen["thresholds"][mode]
        positives = [r for r in report["rows"] if r["split"]=="compare" and r["expectedDocumentIds"]]
        min_top = min((r[mode]["allDocumentScores"][0]["score"],r["questionId"]) for r in positives)
        pairs = [r for r in positives if len(r[mode]["allDocumentScores"])>1]
        min_gap = min((r[mode]["allDocumentScores"][0]["score"]-r[mode]["allDocumentScores"][1]["score"],
                       r["questionId"]) for r in pairs)
        absolute_ok = first["score"] >= rule["tau_abs"]
        gap_ok = gap is not None and gap >= rule["tau_gap"]
        reason = []
        if not absolute_ok:
            reason.append("절대값 조건 미달")
        if mode=="vector" and not gap_ok:
            reason.append("간격 조건 미달")
        if row[mode]["status"] != "BELOW_THRESHOLD" or not reason:
            raise ValueError("Saved rejection is inconsistent with its frozen gate")
        lines += ["",f"### {qid} {mode} 거절 분석", "",
            f"- 세트: {SET_NAMES[row['split']]}. 질문 유형: {', '.join(row['tags'])}. 정답 문서: {', '.join(row['expectedDocumentIds'])}.",
            f"- 1위: {first['document_id']} / 점수 `{first['score']}`. 2위: " +
            (f"{second['document_id']} / 점수 `{second['score']}`." if second else "없음(저장된 검색 결과가 1문서)."),
            f"- 절대값: top1 `{first['score']}` {'>=' if absolute_ok else '<'} tau_abs `{rule['tau_abs']}` → {'통과' if absolute_ok else '미달'}."]
        if mode=="vector":
            lines.append(f"- 간격: gap `{gap}` {'>=' if gap_ok else '<'} tau_gap `{rule['tau_gap']}` → {'통과' if gap_ok else '미달'}.")
        else:
            lines.append(f"- 간격: {'`'+str(gap)+'`' if gap is not None else '계산 불가(2위 없음)'}. tau_gap 저장값 `{rule['tau_gap']}`; lex는 간격 조건을 적용하지 않음.")
        lines += [f"- 비교20 근거 {len(positives)}문항의 최저 top1: `{min_top[0]}` ({min_top[1]}). "
                  f"{qid} top1은 이 값보다 {'높음' if first['score']>min_top[0] else '낮음' if first['score']<min_top[0] else '같음'}.",
                  f"- 비교20 근거의 최저 gap: `{min_gap[0]}` ({min_gap[1]}, 2문서 이상 반환된 {len(pairs)}문항 기준). " +
                  (f"{qid} gap은 이 값보다 {'낮음' if gap<min_gap[0] else '높음' if gap>min_gap[0] else '같음'}." if gap is not None else f"{qid}는 2위가 없어 gap 비교 불가."),
                  f"- 거절 조건: {', '.join(reason)}. " +
                  ("정답이 1위여도 근거 판정 gate를 통과하지 못함." if first['document_id'] in row['expectedDocumentIds'] else "정답 문서를 찾지 못한 순위 실패도 동반됨."),
                  "", "확인 결과로 재조정하지 않음. 60문항 이상에서 다시 보정할 후보."]
    return lines


def recompute(report):
    rows = []
    for stored in report["rows"]:
        row = {k:v for k,v in stored.items() if k not in {"lex","vector"}}
        for mode in ("lex","vector"):
            row[mode] = {"top":[Evidence(**e) for e in stored[mode]["allDocumentScores"]],
                         "searchMs":stored[mode]["searchMs"]}
        rows.append(row)
    output = {}
    for split in ("compare","holdout"):
        subset = [r for r in rows if r["split"]==split]
        output[split] = {mode:metrics(subset,mode,report["thresholds"][mode]) for mode in ("lex","vector")}
    output["byTag"] = {tag:{split:{mode:metrics([r for r in rows if r["split"]==split and tag in r["tags"]],
            mode,report["thresholds"][mode]) for mode in ("lex","vector")}
            for split in ("compare","holdout")} for tag in ("의역","법률 용어","합성 PII","무근거")}
    return output


def write_report(report, target):
    frozen = json.loads((ROOT/"docs/evidence/B02b/frozen_thresholds.json").read_text(encoding="utf-8"))
    recalculated = recompute(report)
    if recalculated != report["metrics"]:
        raise ValueError("Stored metrics do not match per-query evidence")
    text = ["# B02b — 실제 E5 × memvid 검색 평가", "",
        "2026-11-06 · 합성 자료만 · CPU float32 · 실제 E5·실제 memvid. API/생성 모델 연결 없음.", "",
        "이 문서는 `retrieval_eval.json`의 질문별 결과에서 다시 계산했습니다. 모델이나 확인 세트 검색을 재실행하지 않습니다.", "",
        "## 문서 단위 검색 순위", "",
        "| 세트 | 방식 | Hit@1 | Hit@3 | 근거 질문 분모 |", "|---|---|---|---|---|"]
    for split, label in SET_NAMES.items():
        for mode in ("lex","vector"):
            value = recalculated[split][mode]
            text.append(f"| {label} | {mode} | {value['Hit@1']['fraction']} | {value['Hit@3']['fraction']} | {value['evidenceQuestions']} |")
    text += ["", "Hit는 관련성 gate 적용 전 순위입니다. 근거 문서 중 청크 최고점으로 상위 3문서를 고릅니다. 정답 문서 집합과 하나 이상 겹치면 hit입니다. 무작위 3/10은 10문서·정답1개·균등 비복원 추출의 이론 기준선입니다.", "",
        "## 근거 판정 혼동표 (개수)", "",
        "| 세트 | 방식 | 근거 있음→수용 | 근거 있음→거절 | 무근거→수용 | 무근거→거절 |", "|---|---|---|---|---|---|"]
    for split in ("compare","holdout"):
        for mode in ("lex","vector"):
            c = recalculated[split][mode]["confusionCounts"]
            text.append(f"| {SET_NAMES[split]} | {mode} | {c['evidence_accepted']} | {c['evidence_rejected']} | {c['noEvidence_accepted']} | {c['noEvidence_rejected']} |")
    text += ["", "## 유형별 결과 (태그 중복 가능)", "",
        "| 유형 | 세트 | 방식 | Hit@1 | Hit@3 | 근거 거절 | 무근거 오수용 |", "|---|---|---|---|---|---|---|"]
    for tag in ("의역","법률 용어","합성 PII","무근거"):
        for split in ("compare","holdout"):
            for mode in ("lex","vector"):
                value = recalculated["byTag"][tag][split][mode]
                c = value["confusionCounts"]
                text.append(f"| {tag} | {SET_NAMES[split]} | {mode} | {value['Hit@1']['fraction']} | {value['Hit@3']['fraction']} | {c['evidence_rejected']} | {c['noEvidence_accepted']} |")
    text += ["", "## 지연", "",
        "| 세트 | 방식 | 검색 평균 ms | 검색 p95 ms | 질문 임베딩 평균 ms | 질문 임베딩 p95 ms |", "|---|---|---|---|---|---|"]
    for split in ("compare","holdout"):
        times = sorted(r["queryEmbeddingMs"] for r in report["rows"] if r["split"]==split)
        for mode in ("lex","vector"):
            latency = recalculated[split][mode]["searchLatencyMs"]
            # Lex queries do not need an embedding; report N/A instead of charging
            # the E5 evaluation overhead to the lex baseline.
            mean = f"{sum(times)/len(times):.3f}" if mode=="vector" else "N/A"
            p95 = f"{times[math.ceil(.95*len(times))-1]:.3f}" if mode=="vector" else "N/A"
            text.append(f"| {SET_NAMES[split]} | {mode} | {latency['mean']:.3f} | {latency['p95']:.3f} | {mean} | {p95} |")
    text += ["", "검색 시간에는 모델 초기 로딩을 포함하지 않습니다. E5는 CPU 4 threads, 문서 batch2·질문 batch1, float32입니다. 문서30개 encode는 embedding_documents.json, 모델 로딩 시간은 각 embedding JSON에 별도 기록했습니다. p95는 nearest-rank입니다.", "",
        "## 실패·주의할 질문", "",
        "| ID | 세트 | 방식 | 관찰 |", "|---|---|---|---|"]
    for row in report["rows"]:
        if not row["hasEvidence"]:
            continue
        for mode in ("lex","vector"):
            top = row[mode]["top3"]
            observations = []
            if not top or top[0]["document_id"] not in row["expectedDocumentIds"]:
                observations.append("top1 정답 아님")
            if not set(e["document_id"] for e in top)&set(row["expectedDocumentIds"]):
                observations.append("top3 정답 없음")
            if row[mode]["status"] != "OK":
                observations.append("관련성 gate에서 근거 없음 판정")
            if observations:
                text.append(f"| {row['questionId']} | {SET_NAMES[row['split']]} | {mode} | {' / '.join(observations)} |")
    text += rejection_analysis(report, frozen)
    text += ["", "## 고정 조건과 한계", "",
        "- 모델: intfloat/multilingual-e5-large-instruct / revision 274baa43b0e13e37fafa6428dbc7938e62e5c439. 질문 instruction 있음, 문서에는 없음. 최종 길이를 검사하며 조용히 truncate하지 않습니다.",
        "- 비교20만으로 임계값을 고정하고 frozen_thresholds.json SHA를 confirm_once.json에 기록한 뒤 확인10을 1회 검색했습니다. 확인 결과를 본 재조정은 없습니다.",
        "- lex는 라벨·마스크·연산자 토큰을 제외하고 OR 결합합니다. 형태소 분석 없음. vector는 query 문자열을 비우고 명시적 sem+외부 벡터로 호출합니다. native score는 코사인 원값이 아닙니다.",
        "- 8개 이하의 put_many에 opts enable_embedding=False를 명시합니다. 30개 전수·자기 top1 검증 후에만 포인터를 변경했습니다. index_activation.json 참조.",
        "- 최초 암묵적 float16 CPU 실행은 정규화 검사에 실패했습니다. 실패 로그를 보존하고 float32 명시로 재실행했습니다. 확인 세트 사용 전의 수정입니다.",
        "- worker 프로세스 상한 180초, timeout일 때만 batch1로 1회 재시도합니다. Windows는 worker 트리를 종료한 뒤 재시도합니다. 이번 성공한 float32 실행에 timeout은 없었습니다.",
        "- Python socket/DNS 차단, HF_HUB_OFFLINE=1, MEMVID_TELEMETRY=0. Rust의 모든 syscall을 OS firewall로 차단했다는 증거는 아닙니다.",
        "- 작은 합성 코퍼스와 동일 작성자의 평가이므로 일반 한국어·실제 법률 상담 성능을 보장하지 않습니다. 모델 간 비교나 Llama 생성 평가도 아닙니다.",
        "", "재계산: `.\\rag-runtime\\.venv\\Scripts\\python.exe scripts/report_retrieval.py`. 검색·확인 세트를 재실행하지 않고 저장된 결과에서 표를 만듭니다."]
    target.write_text("\n".join(text)+"\n",encoding="utf-8")
    print(json.dumps({k:recalculated[k] for k in ("compare","holdout")},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    report = json.loads((ROOT/"docs/evidence/B02b/retrieval_eval.json").read_text(encoding="utf-8"))
    write_report(report,ROOT/"docs/evidence/B02b/README.md")
