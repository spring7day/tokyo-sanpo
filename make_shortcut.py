#!/usr/bin/env python3
"""iOS 단축어(.shortcut) 생성기 — 서명 없는 plist.

구성 (액션 6개)
  1) 텍스트    : 기본 프롬프트. 나중에 여기만 고치면 된다
  2) 현재 위치 가져오기
  3) 텍스트    : 1)의 결과 + "지금 내 위치" + 2)의 위치
  4) URL 인코드
  5) 텍스트    : https://claude.ai/new?q= + 4)의 결과
  6) URL 열기

'위치 세부사항 가져오기'를 일부러 넣지 않았다. 위치 객체를 텍스트에 끼우면
단축어가 알아서 주소 문자열로 바꿔주므로 액션이 하나 줄고 실패 지점도 준다.
"""
import plistlib
import sys
import uuid

OBJ = "￼"  # OBJECT REPLACEMENT CHARACTER — 변수가 들어갈 자리

BASE_PROMPT = (
    "도쿄 혼자 여행 중이야.\n"
    "답변은 밖에서 폰으로 보니까 짧게 해줘. "
    "장소나 위치를 언급할 때는 구글맵 링크를 하이퍼링크로 같이 달아줘."
)


def uid():
    return str(uuid.uuid4()).upper()


def token_string(parts):
    """parts: 문자열 또는 (uuid, 출력이름) 튜플의 리스트 → WFTextTokenString"""
    s = ""
    attachments = {}
    for p in parts:
        if isinstance(p, str):
            s += p
        else:
            out_uuid, out_name = p
            attachments["{%d, 1}" % len(s)] = {
                "Type": "ActionOutput",
                "OutputUUID": out_uuid,
                "OutputName": out_name,
            }
            s += OBJ
    return {
        "Value": {"string": s, "attachmentsByRange": attachments},
        "WFSerializationType": "WFTextTokenString",
    }


def action(identifier, params):
    return {
        "WFWorkflowActionIdentifier": identifier,
        "WFWorkflowActionParameters": params,
    }


def build():
    u_prompt, u_loc, u_full, u_enc, u_url = (uid() for _ in range(5))

    actions = [
        # 1) 기본 프롬프트 — 나중에 고칠 곳
        action("is.workflow.actions.gettext", {
            "UUID": u_prompt,
            "WFTextActionText": BASE_PROMPT,
        }),
        # 2) 현재 위치
        action("is.workflow.actions.getcurrentlocation", {
            "UUID": u_loc,
        }),
        # 3) 합치기
        action("is.workflow.actions.gettext", {
            "UUID": u_full,
            "WFTextActionText": token_string([
                (u_prompt, "텍스트"),
                "\n\n지금 내 위치\n",
                (u_loc, "현재 위치"),
                "\n",
            ]),
        }),
        # 4) URL 인코드
        action("is.workflow.actions.urlencode", {
            "UUID": u_enc,
            "WFEncodeMode": "Encode",
            "WFInput": token_string([(u_full, "텍스트")]),
        }),
        # 5) 최종 URL
        action("is.workflow.actions.gettext", {
            "UUID": u_url,
            "WFTextActionText": token_string([
                "https://claude.ai/new?q=",
                (u_enc, "URL 인코딩된 텍스트"),
            ]),
        }),
        # 6) 열기
        action("is.workflow.actions.openurl", {
            "WFInput": token_string([(u_url, "텍스트")]),
        }),
    ]

    return {
        "WFWorkflowClientVersion": "2605.0.5",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowIcon": {
            "WFWorkflowIconGlyphNumber": 59446,        # 위치 핀 계열
            "WFWorkflowIconStartColor": 3679049984,    # 주황
        },
        "WFWorkflowImportQuestions": [],
        "WFWorkflowTypes": ["NCWidget", "WatchKit"],
        "WFWorkflowInputContentItemClasses": [
            "WFAppStoreAppContentItem", "WFArticleContentItem",
            "WFContactContentItem", "WFDateContentItem",
            "WFEmailAddressContentItem", "WFGenericFileContentItem",
            "WFImageContentItem", "WFiTunesProductContentItem",
            "WFLocationContentItem", "WFDCMapsLinkContentItem",
            "WFAVAssetContentItem", "WFPDFContentItem",
            "WFPhoneNumberContentItem", "WFRichTextContentItem",
            "WFSafariWebPageContentItem", "WFStringContentItem",
            "WFURLContentItem",
        ],
        "WFWorkflowActions": actions,
    }


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "ask-claude-here.shortcut"
    wf = build()
    with open(out, "wb") as f:
        plistlib.dump(wf, f, fmt=plistlib.FMT_BINARY)
    # 검증: 다시 읽어 구조 확인
    with open(out, "rb") as f:
        back = plistlib.load(f)
    assert len(back["WFWorkflowActions"]) == 6
    ids = [a["WFWorkflowActionIdentifier"] for a in back["WFWorkflowActions"]]
    print(f"{out} 생성 · 액션 {len(ids)}개")
    for i, a in enumerate(ids, 1):
        print(f"  {i}. {a}")
    # 변수 연결이 살아있는지
    links = 0
    for a in back["WFWorkflowActions"]:
        for v in a["WFWorkflowActionParameters"].values():
            if isinstance(v, dict) and v.get("WFSerializationType") == "WFTextTokenString":
                links += len(v["Value"].get("attachmentsByRange", {}))
    print(f"변수 연결 {links}개")
