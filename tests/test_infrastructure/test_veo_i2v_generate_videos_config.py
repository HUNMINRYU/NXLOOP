from PIL import Image


def test_veo_generate_videos_config_uses_reference_images_for_i2v():
    """GenerateVideosConfig가 지원하는 필드가 바뀌어도(I2V) 깨지지 않게 방어한다.

    현재 google-genai는 `reference_images`를 사용한다.
    """
    from google.genai.types import GenerateVideosConfig

    img = Image.new("RGB", (16, 16), color=(255, 0, 0))

    # prod 코드에서 사용하는 구성과 동일한 형태로 생성 가능해야 한다.
    cfg = GenerateVideosConfig(
        reference_images=[img],
        aspect_ratio="9:16",
        output_gcs_uri="gs://dummy/videos_i2v/20260210/",
        duration_seconds=8,
        generate_audio=True,
        number_of_videos=1,
        negative_prompt="watermarks, text, subtitles, low quality",
        person_generation="allow_adult",
    )

    assert cfg.duration_seconds == 8

