from utils.logger import log_info


def test_log_info_accepts_format_args():
    # logging 기본 스타일("...%d", arg) 호출이 깨지지 않아야 한다.
    log_info("numbers: %d %d %d", 1, 2, 3)

