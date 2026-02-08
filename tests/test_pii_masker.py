"""
PII 마스킹 유틸리티 테스트
"""

import pytest

from utils.pii_masker import PIIType, contains_pii, detect_pii, mask_pii


class TestDetectPII:
    """PII 탐지 기능 테스트"""

    def test_phone_number_010(self):
        """한국 휴대전화 번호 탐지"""
        matches = detect_pii("연락처: 010-1234-5678")
        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.PHONE
        assert matches[0].original == "010-1234-5678"

    def test_phone_number_02(self):
        """서울 지역번호 전화번호 탐지"""
        matches = detect_pii("사무실: 02-123-4567")
        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.PHONE

    def test_email_address(self):
        """이메일 주소 탐지"""
        matches = detect_pii("문의: test@example.com")
        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.EMAIL
        assert matches[0].original == "test@example.com"

    def test_resident_id(self):
        """주민등록번호 탐지"""
        matches = detect_pii("주민번호: 901225-1234567")
        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.RESIDENT_ID

    def test_card_number(self):
        """신용카드 번호 탐지"""
        matches = detect_pii("카드: 1234-5678-9012-3456")
        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.CARD_NUMBER

    def test_ip_address(self):
        """IP 주소 탐지"""
        matches = detect_pii("서버 IP: 192.168.1.100")
        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.IP_ADDRESS

    def test_no_pii(self):
        """PII가 없는 텍스트"""
        matches = detect_pii("이 제품 정말 좋아요! 추천합니다.")
        assert len(matches) == 0

    def test_empty_text(self):
        """빈 텍스트"""
        matches = detect_pii("")
        assert len(matches) == 0

    def test_multiple_pii(self):
        """여러 PII가 포함된 텍스트"""
        text = "연락처: 010-1234-5678, 이메일: user@test.com"
        matches = detect_pii(text)
        assert len(matches) == 2
        types = {m.pii_type for m in matches}
        assert PIIType.PHONE in types
        assert PIIType.EMAIL in types


class TestMaskPII:
    """PII 마스킹 기능 테스트"""

    def test_mask_phone(self):
        """전화번호 마스킹"""
        result = mask_pii("연락처: 010-1234-5678")
        assert "010-1234-5678" not in result.masked_text
        assert result.has_pii is True
        assert result.pii_count == 1

    def test_mask_email(self):
        """이메일 마스킹"""
        result = mask_pii("이메일: admin@nexloop.ai")
        assert "admin@nexloop.ai" not in result.masked_text
        assert "***@***.***" in result.masked_text

    def test_no_pii_unchanged(self):
        """PII 없으면 원본 유지"""
        text = "이 제품 정말 좋아요!"
        result = mask_pii(text)
        assert result.masked_text == text
        assert result.has_pii is False
        assert result.pii_count == 0

    def test_mask_preserves_context(self):
        """마스킹 후 주변 텍스트 유지"""
        result = mask_pii("배송 문의는 010-9876-5432로 전화주세요")
        assert "배송 문의는" in result.masked_text
        assert "전화주세요" in result.masked_text
        assert "010-9876-5432" not in result.masked_text

    def test_empty_text(self):
        """빈 텍스트 처리"""
        result = mask_pii("")
        assert result.masked_text == ""
        assert result.has_pii is False


class TestContainsPII:
    """빠른 PII 확인 테스트"""

    def test_contains_phone(self):
        assert contains_pii("전화: 010-1111-2222") is True

    def test_no_pii(self):
        assert contains_pii("안녕하세요") is False
