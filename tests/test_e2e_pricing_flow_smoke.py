from __future__ import annotations

import contextlib
import os
import subprocess
import tempfile
import time
import urllib.request

import pytest


def _wait_http_ok(
    url: str,
    *,
    proc: subprocess.Popen[bytes] | None = None,
    log_path: str | None = None,
    timeout_s: float = 60.0,
) -> None:
    start = time.time()
    last_err: Exception | None = None
    while time.time() - start < timeout_s:
        if proc is not None and proc.poll() is not None:
            log_tail = ""
            tail = ""
            if log_path and os.path.exists(log_path):
                try:
                    with open(log_path, encoding="utf-8", errors="replace") as f:
                        lines = f.read().splitlines()
                    tail = "\n".join(lines[-120:])
                    log_tail = f"\n\n--- next dev logs (tail) ---\n{tail}\n"
                except Exception:
                    # 로그는 디버깅용 보조 수단이므로, 읽기 실패는 무시한다.
                    log_tail = ""

            # 일부 샌드박스/CI 환경에서는 포트 listen이 금지될 수 있다.
            tail_lower = tail.lower()
            if "listen eperm" in tail_lower or "operation not permitted" in tail_lower:
                pytest.skip(
                    "실행 환경에서 포트 listen이 허용되지 않아 프론트 E2E 스모크를 실행할 수 없습니다."
                )
            raise AssertionError(
                f"Next dev 서버 프로세스가 조기 종료되었습니다. url={url}, exit_code={proc.returncode}{log_tail}"
            )
        try:
            with urllib.request.urlopen(url, timeout=2.0) as res:  # noqa: S310
                if 200 <= res.status < 300:
                    return
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(0.4)
    raise AssertionError(f"서버 준비 대기 timeout: {url} (last_err={last_err})")


def _fetch_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10.0) as res:  # noqa: S310
        raw = res.read()
    return raw.decode("utf-8", errors="replace")


def test_pricing_page_smoke_renders_and_has_upgrade_links() -> None:
    """
    브라우저 없이도 가능한 최소 E2E 스모크:
    - Next dev 서버 기동
    - /pricing 렌더링 성공(200)
    - PRO/BUSINESS 결제 링크가 HTML에 포함
    """
    if os.environ.get("NEXLOOP_RUN_FRONTEND_E2E") != "1":
        pytest.skip("NEXLOOP_RUN_FRONTEND_E2E=1 일 때만 프론트 E2E 스모크를 실행합니다.")

    # 랜덤 포트는 환경에 따라 소켓/바인딩 제약 및 레이스가 생길 수 있어 고정 포트로 단순화한다.
    # 필요하면 NEXLOOP_FRONTEND_PORT로 오버라이드한다.
    port = int(os.environ.get("NEXLOOP_FRONTEND_PORT", "3100"))

    env = os.environ.copy()
    env["NEXT_PUBLIC_API_URL"] = ""
    env["NEXT_PUBLIC_DISABLE_CHATBOT"] = "true"
    env["NEXT_PUBLIC_STRIPE_PRO_PAYMENT_LINK"] = "https://example.com/pay/pro"
    env["NEXT_PUBLIC_STRIPE_BUSINESS_PAYMENT_LINK"] = "https://example.com/pay/business"

    with tempfile.TemporaryDirectory(prefix="nexloop-frontend-e2e-") as tmp:
        # distDir lock 충돌 방지: 로컬에서 next dev가 떠 있어도 테스트는 독립적으로 실행된다.
        env["NEXLOOP_NEXT_DIST_DIR"] = os.path.join(".next-e2e", str(port))

        log_path = os.path.join(tmp, "next-dev.log")
        with open(log_path, "wb") as log_fp:
            proc = subprocess.Popen(  # noqa: S603
                # hostname을 강제로 127.0.0.1로 맞춰, /pricing health check가 흔들리지 않게 한다.
                ["npm", "run", "dev", "--", "-p", str(port), "--hostname", "127.0.0.1"],
                cwd="frontend",
                env=env,
                stdout=log_fp,
                stderr=subprocess.STDOUT,
            )
            try:
                base = f"http://127.0.0.1:{port}"
                _wait_http_ok(f"{base}/pricing", proc=proc, log_path=log_path, timeout_s=180.0)
                html = _fetch_text(f"{base}/pricing")
                assert "요금제" in html
                assert 'href="https://example.com/pay/pro"' in html
                assert 'href="https://example.com/pay/business"' in html
            finally:
                proc.terminate()
                with contextlib.suppress(Exception):
                    proc.wait(timeout=20)
