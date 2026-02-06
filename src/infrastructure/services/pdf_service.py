"""
PDF Export Service
"""

import os
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.ports.export_port import ExportPort
from utils.logger import get_logger

logger = get_logger(__name__)


class PdfService(ExportPort):
    """PDF 내보내기 서비스"""

    def __init__(self, font_path: str | None = None):
        self._register_font(font_path)

    def _register_font(self, font_path: str | None = None) -> None:
        """한글 폰트 등록 (NanumGothic)"""
        try:
            # OS별 폰트 경로 시도
            if not font_path:
                possible_paths = [
                    "C:/Windows/Fonts/NanumGothic.ttf",
                    "C:/Windows/Fonts/malgun.ttf",  # 맑은 고딕
                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                    "/usr/share/fonts/truetype/noto/NotoSansCJKkr-Regular.otf",
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        font_path = path
                        break

            if font_path:
                font_name = "KoreanFont"
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                self.font_name = font_name
            else:
                logger.warning("한글 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다.")
                self.font_name = "Helvetica"

        except Exception as e:
            logger.error(f"폰트 등록 실패: {e}")
            self.font_name = "Helvetica"

    def export(self, data: dict[str, Any], output_path: str) -> str:
        """분석 결과를 PDF로 생성"""
        try:
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18,
            )

            story = []
            styles = getSampleStyleSheet()

            # 커스텀 스타일 정의
            title_style = ParagraphStyle(
                "Title",
                parent=styles["Heading1"],
                fontName=self.font_name,
                fontSize=24,
                spaceAfter=30,
                alignment=1,  # Center
            )

            heading_style = ParagraphStyle(
                "Heading",
                parent=styles["Heading2"],
                fontName=self.font_name,
                fontSize=16,
                spaceBefore=20,
                spaceAfter=10,
                textColor=colors.HexColor("#2C3E50"),
            )

            body_style = ParagraphStyle(
                "Body",
                parent=styles["Normal"],
                fontName=self.font_name,
                fontSize=10,
                leading=16,
            )

            # 1. 제목
            product_name = data.get("product", {}).get("name", "제품 분석 보고서")
            story.append(Paragraph(f"{product_name} 마케팅 전략", title_style))
            story.append(
                Paragraph(
                    f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style
                )
            )
            story.append(Spacer(1, 20))

            # 2. 페르소나 분석
            story.append(Paragraph("🎯 타겟 페르소나", heading_style))
            target = data.get("analysis", {}).get("target_audience", {})
            if target:
                story.append(
                    Paragraph(f"주요 타겟: {target.get('primary', '-')}", body_style)
                )
                story.append(
                    Paragraph(
                        f"페인 포인트: {', '.join(target.get('pain_points', []))}",
                        body_style,
                    )
                )
                story.append(
                    Paragraph(
                        f"니즈/욕구: {', '.join(target.get('desires', []))}", body_style
                    )
                )
            story.append(Spacer(1, 10))

            # 3. 훅 (Hook) 전략
            story.append(Paragraph("🎣 바이럴 훅 (Hooks)", heading_style))
            hooks = data.get("analysis", {}).get("hook_suggestions", [])
            for idx, hook in enumerate(hooks, 1):
                story.append(Paragraph(f"{idx}. {hook}", body_style))
            story.append(Spacer(1, 10))

            # 4. Pain & Gain Points
            story.append(Paragraph("💡 Pain & Gain Points", heading_style))

            # 테이블 데이터 구성
            pains = data.get("metrics", {}).get("pain_points", [])
            gains = data.get("metrics", {}).get("gain_points", [])

            table_data = [["Pain Points (불편함)", "Gain Points (기대효과)"]]
            max_len = max(len(pains), len(gains))

            for i in range(max_len):
                p_text = pains[i]["keyword"] if i < len(pains) else ""
                g_text = gains[i]["keyword"] if i < len(gains) else ""
                table_data.append([p_text, g_text])

            table = Table(table_data, colWidths=[200, 200])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6E6E6")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, -1), self.font_name),
                        ("FONTSIZE", (0, 0), (-1, 0), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 20))

            # 5. X-Algorithm 핵심 인사이트 (추가)
            insights = data.get("metrics", {}).get("top_insights", [])
            if insights:
                story.append(Paragraph("🧠 X-Algorithm 핵심 인사이트", heading_style))
                story.append(
                    Paragraph(
                        "인공지능이 분석한 실제 잠재 고객의 주요 발화 내용과 인게이지먼트 예측 결과입니다.",
                        body_style,
                    )
                )
                story.append(Spacer(1, 10))

                for idx, insight in enumerate(insights, 1):
                    score = insight.get("score", 0)
                    content = insight.get("content", "")
                    features = insight.get("features", {})
                    keywords = ", ".join(features.get("keywords", [])[:3])

                    insight_text = (
                        f"<b>[{idx}] (Score: {score:.2f})</b><br/>"
                        f"내용: \"{content}\"<br/>"
                        f"핵심 키워드: {keywords}<br/>"
                        f"구매 의도: {features.get('purchase_intent', 0):.1f} | "
                        f"바이럴 잠재력: {features.get('reply_inducing', 0):.1f}"
                    )
                    story.append(Paragraph(insight_text, body_style))
                    story.append(Spacer(1, 10))

            doc.build(story)
            logger.info(f"PDF 생성 완료: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"PDF 생성 실패: {e}")
            raise e
