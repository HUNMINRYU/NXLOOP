"""
Notion Export Service
"""

from typing import Any, cast

import requests

from core.ports.export_port import ExportPort
from utils.logger import get_logger

logger = get_logger(__name__)


class NotionService(ExportPort):
    """Notion 내보내기 서비스"""

    NOTION_API_URL = "https://api.notion.com/v1"

    def __init__(self, api_key: str, database_id: str | None = None):
        self._api_key = api_key
        self._database_id = database_id
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    def is_configured(self) -> bool:
        """설정 확인"""
        return bool(self._api_key)

    def export(self, data: dict[str, Any], output_path: str | None = None) -> str:
        """분석 결과를 Notion 페이지로 생성"""
        if not self.is_configured():
            raise ValueError("Notion API Key is not configured")

        report_type = data.get("report_type")
        try:
            # 리포트 타입(예: 모델 평가) 분기 지원
            if report_type == "ctr_offline_eval":
                return self._export_ctr_offline_eval(data)

            # 1. 페이지 콘텐츠 구성
            product_name = data.get("product", {}).get("name", "제품 분석 보고서")
            analysis = data.get("analysis", {})
            meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
            children = []

            # 제목 및 개요
            children.append(self._create_header_block(f"{product_name} 마케팅 전략"))
            children.append(
                self._create_callout_block(
                    "Nexloop 자동 분석 리포트",
                    lines=[
                        f"task_id: {meta.get('task_id', '-') }",
                        f"executed_at: {meta.get('executed_at', '-') }",
                        f"duration_seconds: {meta.get('duration_seconds', 0)}",
                        f"upload_status: {meta.get('upload_status', '-') }",
                        f"ai_stages_used: {', '.join(meta.get('ai_stages_used') or [])}",
                    ],
                    emoji="🤖",
                )
            )
            upload_errors = meta.get("upload_errors") or []
            if upload_errors:
                children.append(
                    self._create_callout_block(
                        "업로드 오류(요약)",
                        lines=[str(e) for e in upload_errors[:5]],
                        emoji="⚠️",
                    )
                )

            # 파이프라인 통계(처리량/필터링/선정)
            metrics = data.get("metrics", {}) if isinstance(data.get("metrics"), dict) else {}
            pm = metrics.get("pipeline_metrics") if isinstance(metrics.get("pipeline_metrics"), dict) else None
            if pm:
                children.append(self._create_subheader_block("📊 파이프라인 처리 통계"))
                children.append(
                    self._create_callout_block(
                        "처리 건수 요약",
                        lines=[
                            f"original_count: {pm.get('original_count', 0)}",
                            f"removed_count: {pm.get('removed_count', pm.get('total_filtered', 0))}",
                            f"after_filter_count: {pm.get('after_filter_count', 0)}",
                            f"selected_count: {pm.get('selected_count', pm.get('result_count', 0))}",
                            f"selection_rate_of_original: {pm.get('selection_rate_of_original', pm.get('selection_rate', 0.0))}",
                            f"selection_rate_of_filtered: {pm.get('selection_rate_of_filtered', 0.0)}",
                            f"throughput_per_sec: {pm.get('throughput_per_sec', 0.0)}",
                        ],
                        emoji="📈",
                    )
                )

            # 타겟 오디언스
            children.append(self._create_subheader_block("🎯 타겟 페르소나"))
            target = analysis.get("target_audience", {})
            if isinstance(target, dict):
                children.append(
                    self._create_paragraph_block(
                        f"Main Target: {target.get('primary', '-')}"
                    )
                )
                children.append(
                    self._create_paragraph_block(
                        f"Sub Target: {target.get('secondary', '-')}"
                    )
                )

            # Pain Points (Dict 처리 강화)
                pain_points = target.get("pain_points", [])
                if pain_points:
                    children.append(self._create_paragraph_block("Pain Points:", bold=True))
                    for pt in pain_points:
                        text = pt
                        if isinstance(pt, dict):
                            text = f"{pt.get('pain')} (🗣️ \"{pt.get('source_quote')}\" )"
                        children.append(self._create_bullet_block(str(text)))
            else:
                children.append(self._create_paragraph_block(str(target)))

            # 훅 (Hooks)
            children.append(self._create_subheader_block("🎣 바이럴 훅 (Hooks)"))
            for hook in analysis.get("hook_suggestions", []):
                h_text = hook.get('hook') if isinstance(hook, dict) else str(hook)
                children.append(self._create_number_block(h_text))

            # 핵심 가치 / Differentiators
            children.append(self._create_subheader_block("💎 핵심 차별화 요소"))
            differentiators = analysis.get("competitor_analysis", {}).get(
                "differentiators", []
            )
            if not differentiators:
                differentiators = analysis.get("unique_selling_point", [])

            if isinstance(differentiators, list):
                for diff in differentiators:
                    children.append(self._create_bullet_block(str(diff)))
            else:
                children.append(self._create_paragraph_block(str(differentiators)))

            # 인사이트
            children.append(self._create_subheader_block("💡 주요 인사이트"))
            summary = analysis.get("summary", "")
            if summary:
                children.append(self._create_quote_block(summary))
            insights = analysis.get("insights") or []
            if isinstance(insights, list) and insights:
                children.append(self._create_paragraph_block("인사이트 목록:", bold=True))
                for item in insights[:20]:
                    if item:
                        children.append(self._create_bullet_block(str(item)))

            # 파이프라인 동작 설명(데모/시연용)
            children.append(self._create_subheader_block("🧩 파이프라인 설명(요약)"))
            children.append(
                self._create_toggle_block(
                    "데이터 수집은 무엇을 수집하나?",
                    [
                        self._create_paragraph_block(
                            "YouTube/네이버 등 채널에서 제목/설명/댓글/반응(좋아요/조회 등)과 같은 실시간 신호를 수집합니다. "
                            "수집 단계에서 중복/스팸/무의미 데이터를 제거해 이후 단계의 노이즈를 줄입니다."
                        )
                    ],
                )
            )
            children.append(
                self._create_toggle_block(
                    "시장 동향 수집은 무엇을 의미하나?",
                    [
                        self._create_paragraph_block(
                            "동일 카테고리에서 최근에 반응이 커지는 주제/키워드/포맷(예: 훅 문구 패턴, 썸네일 구성)을 "
                            "요약해 전략 생성의 입력으로 사용합니다."
                        )
                    ],
                )
            )
            children.append(
                self._create_toggle_block(
                    "임베딩(Embedding) 요청은 왜 필요한가?",
                    [
                        self._create_paragraph_block(
                            "텍스트를 벡터로 바꿔 '의미 유사도'를 계산하기 위해 사용합니다. "
                            "이를 통해 중복 후보를 제거하고(다양성 확보), 유사한 성공 사례를 찾아 점수화할 수 있습니다."
                        )
                    ],
                )
            )
            children.append(
                self._create_toggle_block(
                    "xalgo는 무엇인가?",
                    [
                        self._create_paragraph_block(
                            "xalgo는 후보를 수집한 뒤, 전처리/하이드레이션/스코어링/다양성/선정 단계를 거쳐 "
                            "성과 가능성이 높은 후보만 남기는 랭킹 파이프라인입니다. "
                            "로그에는 xalgo_source, xalgo_pre_filter, xalgo_hydration, xalgo_scoring, xalgo_diversity, xalgo_selection 단계가 기록됩니다."
                        )
                    ],
                )
            )
            children.append(
                self._create_toggle_block(
                    "pdwell / pshare / paction은 무엇인가?",
                    [
                        self._create_paragraph_block(
                            "pdwell: 시청/체류 확률(머무를 가능성), pshare: 공유 확률, paction: 구매/클릭 등 행동 확률을 의미합니다. "
                            "현재 구현에서는 모델/룰 기반 점수로 표현될 수 있으며, 각 점수는 '왜 그렇게 나왔는지' 근거를 breakdown으로 함께 남기는 것이 목표입니다."
                        )
                    ],
                )
            )
            children.append(
                self._create_toggle_block(
                    "rag_ingest_pipeline는 무엇인가?",
                    [
                        self._create_paragraph_block(
                            "파이프라인 산출물(인사이트/전략/크리에이티브)을 문서화해 검색 가능한 지식 베이스로 적재(RAG 인덱싱)하는 단계입니다. "
                            "이후 유사 케이스 검색이나 설명 가능한 리포트 생성에 활용합니다."
                        )
                    ],
                )
            )

            # [NEW] 생성된 콘텐츠 (미디어)
            gen_content = data.get("generated_content", {}) if isinstance(data.get("generated_content"), dict) else {}
            selected_outputs = data.get("selected_outputs", {}) if isinstance(data.get("selected_outputs"), dict) else {}
            has_media = False

            # 선택(채택)된 산출물 요약
            if selected_outputs:
                children.append(self._create_subheader_block("✅ 채택된 산출물 (Selected Outputs)"))
                for kind, info in selected_outputs.items():
                    if not isinstance(info, dict):
                        continue
                    url = info.get("url")
                    who = info.get("selected_by", "unknown")
                    at = info.get("selected_at", "")
                    if url and isinstance(url, str) and url.startswith("http"):
                        children.append(self._create_paragraph_block(f"{kind}: {url}"))
                        children.append(self._create_paragraph_block(f"selected_by: {who} · {at}"))

            # 썸네일 이미지
            thumb_url = gen_content.get("thumbnail_url")
            if thumb_url and thumb_url.startswith("http"):
                if not has_media:
                    children.append(self._create_subheader_block("🎨 생성된 크리에이티브"))
                    has_media = True
                children.append(self._create_paragraph_block("썸네일 미리보기:", bold=True))
                children.append(self._create_image_block(thumb_url))

            # 다중 썸네일
            multi_thumbnails = gen_content.get("multi_thumbnails") or []
            if isinstance(multi_thumbnails, list) and multi_thumbnails:
                if not has_media:
                    children.append(self._create_subheader_block("🎨 생성된 크리에이티브"))
                    has_media = True
                children.append(self._create_paragraph_block("썸네일 후보들:", bold=True))
                for idx, item in enumerate(multi_thumbnails, start=1):
                    if not isinstance(item, dict):
                        continue
                    url = item.get("url")
                    style = item.get("style") or item.get("style_key") or ""
                    if url and isinstance(url, str) and url.startswith("http"):
                        title = f"#{idx} {style}".strip()
                        children.append(self._create_subheader3_block(title or f"#{idx}"))
                        children.append(self._create_image_block(url))

            # 비디오
            video_url = gen_content.get("video_url")
            if video_url and video_url.startswith("http"):
                if not has_media:
                    children.append(self._create_subheader_block("🎨 생성된 크리에이티브"))
                    has_media = True
                children.append(self._create_paragraph_block("마케팅 비디오:", bold=True))
                children.append(self._create_video_block(video_url))
                children.append(self._create_bookmark_block(video_url))

            if has_media:
                children.append(
                    self._create_callout_block(
                        "미디어 링크는 signed URL일 수 있어 만료될 수 있습니다.",
                        lines=["만료 시 Nexloop에서 재생성/리프레시한 URL로 다시 내보내세요."],
                        emoji="⏳",
                    )
                )

            # [NEW] SNS 마케팅 소재
            sns_posts = gen_content.get("social_posts") or gen_content.get("sns_posts")
            if sns_posts and isinstance(sns_posts, dict):
                children.append(self._create_subheader_block("📱 SNS 마케팅 소재"))

                for platform, content in sns_posts.items():
                    platform_name = platform.upper()
                    item_text = f"{platform_name} 포스팅 초안"

                    # 내용 파싱
                    body_text = ""
                    if isinstance(content, dict):
                        # 제목이 있으면 추가 (블로그 등)
                        if "title" in content:
                            body_text += f"제목: {content['title']}\n\n"

                        # 본문/캡션
                        body_parts = [
                            content.get("caption", ""),
                            content.get("body", ""),
                            content.get("content", "")
                        ]
                        # 비어있지 않은 첫 번째 값 사용
                        main_text = next((t for t in body_parts if t), str(content))
                        body_text += main_text

                        # 해시태그 처리
                        hashtags = content.get("hashtags")
                        if hashtags:
                            if isinstance(hashtags, list):
                                body_text += "\n\n" + " ".join(hashtags)
                            else:
                                body_text += "\n\n" + str(hashtags)
                    else:
                        body_text = str(content)

                    # 토글 블록 생성
                    # 주의: Notion API 제약상 토글 내부 콘텐츠는 별도 API 호출이 필요할 수 있으나,
                    # 페이지 생성(Create Page) 시에는 children 중첩이 허용됨.
                    toggle_children = [self._create_paragraph_block(body_text)]
                    children.append(self._create_toggle_block(item_text, toggle_children))

            # 2. Notion 페이지 생성
            if self._database_id:
                parent = {"database_id": self._database_id}
                # ... (DB Title Fetch Logic preserved)
                db_resp = requests.get(
                    f"{self.NOTION_API_URL}/databases/{self._database_id}",
                    headers=self._headers,
                )
                if not db_resp.ok:
                    raise Exception(f"Notion DB Fetch Error: {db_resp.text}")
                db_data = db_resp.json()
                title_prop = None
                for name, prop in db_data.get("properties", {}).items():
                    if prop.get("type") == "title":
                        title_prop = name
                        break
                if not title_prop:
                    title_prop = "Name" # Fallback

                properties = cast(dict[str, Any], {
                    title_prop: {
                        "title": [{"text": {"content": f"{product_name} 리포트"}}]
                    }
                })
            elif output_path:
                parent = {"page_id": output_path}
                properties = {
                    "title": [{"text": {"content": f"{product_name} 리포트"}}]
                }
            else:
                # DB 또는 Page ID 미설정
                raise ValueError("Database ID or Page ID is required")

            response = requests.post(
                f"{self.NOTION_API_URL}/pages",
                headers=self._headers,
                json={
                    "parent": parent,
                    "properties": properties,
                    "children": children,
                },
            )
            if not response.ok:
                raise Exception(f"Notion API Error: {response.text}")

            result = response.json()
            page_url = result.get("url", "")
            logger.info(f"Notion 페이지 생성 완료: {page_url}")
            return page_url

        except Exception as e:
            logger.error(f"Notion 내보내기 실패: {e}")
            raise

    def _export_ctr_offline_eval(self, data: dict[str, Any]) -> str:
        """CTR 오프라인 학습/평가 리포트를 Notion DB에 저장."""
        if not self._database_id:
            raise ValueError("Notion Database ID is required")

        meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
        report = data.get("report", {}) if isinstance(data.get("report"), dict) else {}

        report_date = str(meta.get("report_date") or report.get("report_date") or "unknown")
        generated_at = str(meta.get("generated_at") or report.get("generated_at") or "")
        artifact_gcs_path = meta.get("artifact_gcs_path")

        children: list[dict[str, Any]] = []
        children.append(self._create_header_block(f"CTR Offline Eval ({report_date})"))
        children.append(
            self._create_callout_block(
                "오프라인 학습/평가 리포트 (승인 분류 + 실측 CTR 회귀)",
                lines=[
                    f"report_date: {report_date}",
                    f"generated_at: {generated_at}",
                    f"artifact_gcs_path: {artifact_gcs_path or '-'}",
                ],
                emoji="📈",
            )
        )

        ds = report.get("dataset_counts") if isinstance(report.get("dataset_counts"), dict) else {}
        children.append(self._create_subheader_block("🧾 Dataset"))
        for k, v in (ds or {}).items():
            children.append(self._create_bullet_block(f"{k}: {v}"))

        cls = report.get("classification") if isinstance(report.get("classification"), dict) else {}
        base = report.get("baseline") if isinstance(report.get("baseline"), dict) else {}
        children.append(self._create_subheader_block("✅ Classification (Approval)"))
        if cls.get("error"):
            children.append(self._create_callout_block("분류 평가 실패", [str(cls.get("error"))], emoji="⚠️"))
        else:
            lines = [
                f"precision: {cls.get('precision')}",
                f"recall: {cls.get('recall')}",
                f"f1: {cls.get('f1')}",
                f"roc_auc: {cls.get('roc_auc')}",
                f"n_samples: {cls.get('n_samples')}",
                f"n_runs: {cls.get('n_runs')}",
            ]
            children.append(self._create_callout_block("요약", lines, emoji="📌"))

        if base:
            children.append(self._create_paragraph_block("Baseline:", bold=True))
            children.append(
                self._create_bullet_block(
                    f"top1_hit_rate: {base.get('top1_hit_rate')} (runs={base.get('runs')})"
                )
            )

        reg = report.get("regression") if isinstance(report.get("regression"), dict) else {}
        children.append(self._create_subheader_block("📉 Regression (Actual CTR)"))
        if reg.get("error"):
            children.append(self._create_callout_block("회귀 평가 실패", [str(reg.get("error"))], emoji="⚠️"))
        else:
            lines = [
                f"mae: {reg.get('mae')}",
                f"rmse: {reg.get('rmse')}",
                f"n_samples: {reg.get('n_samples')}",
            ]
            children.append(self._create_callout_block("요약", lines, emoji="📌"))

        if artifact_gcs_path and isinstance(artifact_gcs_path, str):
            children.append(self._create_subheader_block("📦 Artifact"))
            children.append(self._create_bookmark_block(artifact_gcs_path))

        # DB 타이틀 프로퍼티 이름 조회
        db_resp = requests.get(
            f"{self.NOTION_API_URL}/databases/{self._database_id}",
            headers=self._headers,
        )
        if not db_resp.ok:
            raise Exception(f"Notion DB Fetch Error: {db_resp.text}")
        db_data = db_resp.json()
        title_prop = None
        for name, prop in db_data.get("properties", {}).items():
            if prop.get("type") == "title":
                title_prop = name
                break
        if not title_prop:
            title_prop = "Name"

        response = requests.post(
            f"{self.NOTION_API_URL}/pages",
            headers=self._headers,
            json={
                "parent": {"database_id": self._database_id},
                "properties": cast(
                    dict[str, Any],
                    {
                        title_prop: {
                            "title": [{"text": {"content": f"CTR Offline Eval {report_date}"}}]
                        }
                    },
                ),
                "children": children,
            },
        )
        if not response.ok:
            raise Exception(f"Notion API Error: {response.text}")

        result = response.json()
        page_url = result.get("url", "")
        logger.info("Notion 페이지 생성 완료(CTR Offline Eval): %s", page_url)
        return page_url

    # --- Block Builders ---
    def _create_header_block(self, text):
        return {
            "object": "block",
            "type": "heading_1",
            "heading_1": {"rich_text": [{"type": "text", "text": {"content": text}}]},
        }

    def _create_subheader_block(self, text):
        return {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]},
        }

    def _create_subheader3_block(self, text):
        return {
            "object": "block",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"type": "text", "text": {"content": str(text)}}]},
        }

    def _create_paragraph_block(self, text, bold=False):
        # 텍스트 길이 제한 처리 (Notion API: 2000자)
        safe_text = str(text)
        if len(safe_text) > 2000:
            safe_text = safe_text[:1997] + "..."

        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": safe_text},
                        "annotations": {"bold": bold},
                    }
                ]
            },
        }

    def _create_bullet_block(self, text):
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": str(text)}}]
            },
        }

    def _create_number_block(self, text):
        return {
            "object": "block",
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [{"type": "text", "text": {"content": str(text)}}]
            },
        }

    def _create_quote_block(self, text):
        return {
            "object": "block",
            "type": "quote",
            "quote": {"rich_text": [{"type": "text", "text": {"content": str(text)}}]},
        }

    def _create_callout_block(self, title: str, lines: list[str] | None = None, emoji: str = "💡"):
        body = title
        if lines:
            body += "\n" + "\n".join(f"- {line}" for line in lines if line)
        return {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": body}}],
                "icon": {"emoji": emoji},
            },
        }

    def _create_image_block(self, url):
        return {
            "object": "block",
            "type": "image",
            "image": {
                "type": "external",
                "external": {"url": url}
            }
        }

    def _create_video_block(self, url):
        return {
            "object": "block",
            "type": "video",
            "video": {
                "type": "external",
                "external": {"url": url}
            }
        }

    def _create_bookmark_block(self, url: str):
        return {
            "object": "block",
            "type": "bookmark",
            "bookmark": {
                "url": url,
            },
        }

    def _create_toggle_block(self, text, children=None):
        block = {
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{"type": "text", "text": {"content": str(text)}}]
            }
        }
        if children:
            block["children"] = children
        return block
