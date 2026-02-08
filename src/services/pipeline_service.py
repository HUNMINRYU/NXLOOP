"""
파이프라인 서비스
전체 마케팅 파이프라인 오케스트레이션
"""

import asyncio
import random
import time
from collections.abc import Callable
from datetime import datetime

from core.exceptions import PipelineError
from core.interfaces import IStorageService
from core.models import (
    CollectedData,
    GeneratedContent,
    PipelineConfig,
    PipelineProgress,
    PipelineResult,
    PipelineStep,
    UploadStatus,
)
from core.prompts import (  # noqa: F401
    marketing_prompts,
    prompt_registry,
    social_media_prompts,
)
from services.data_collection_service import DataCollectionService
from services.history_service import HistoryService
from services.marketing_service import MarketingService
from services.rag_ingestion_service import RagIngestionService
from services.social_service import SocialMediaService
from services.thumbnail_service import THUMBNAIL_STYLES, ThumbnailService
from services.video_service import VideoService
from utils.gcs_store import (
    build_gcs_prefix,
    detect_image_ext,
    detect_video_ext,
    gcs_url_for,
)
from utils.logger import (
    get_logger,
    log_error,
    log_info,
    log_input_data,
    log_output_data,
    log_pipeline_progress,
    log_product_context,
    log_separator,
    log_stage_end,
    log_stage_fail,
    # 한글 상세 로깅 함수들
    log_stage_start,
    log_success,
    log_summary_box,
    log_timing,
    log_warning,
)

logger = get_logger(__name__)


class PipelineService:
    """파이프라인 오케스트레이션 서비스"""

    def __init__(
        self,
        data_collection_service: DataCollectionService,
        marketing_service: MarketingService,
        thumbnail_service: ThumbnailService,
        video_service: VideoService,
        storage_service: IStorageService,
        history_service: HistoryService,
        social_media_service: SocialMediaService,
        rag_ingestion_service: RagIngestionService | None = None,
    ) -> None:
        self._collector = data_collection_service
        self._marketing = marketing_service
        self._thumbnail = thumbnail_service
        self._video = video_service
        self._storage = storage_service
        self._history = history_service
        self._social = social_media_service
        self._rag_ingestion = rag_ingestion_service

    async def execute(
        self,
        product: dict,
        config: PipelineConfig,
        progress_callback: Callable[[PipelineProgress], None] | None = None,
    ) -> PipelineResult:
        """파이프라인 실행"""
        # ===== 🚀 파이프라인 시작 - 입력 데이터 로깅 =====
        log_separator("double")
        log_stage_start("파이프라인 실행", f"제품: {product.get('name', 'N/A')}")
        log_product_context(product)
        log_input_data("설정 - 썸네일 생성", config.generate_thumbnail)
        log_input_data("설정 - 비디오 생성", config.generate_video)
        log_input_data("설정 - SNS 포스팅 생성", config.generate_social)
        log_input_data("설정 - GCS 업로드", config.upload_to_gcs)
        log_separator("single")

        start_time = time.time()

        progress = PipelineProgress()
        progress.configure_steps(config)
        collected_data = CollectedData()
        generated_content = GeneratedContent()
        strategy: dict = {}
        upload_status = UploadStatus.SKIPPED
        upload_errors: list[str] = []
        upload_enabled = config.upload_to_gcs
        prompt_log: dict[str, dict[str, str]] = {}
        audit_trail: list[dict[str, str]] = [
            {
                "action": "created",
                "by": "system",
                "at": datetime.now().isoformat(),
            }
        ]

        if upload_enabled and not self._storage.health_check():
            log_warning("GCS health check failed - skipping upload.")
            upload_status = UploadStatus.FAILED
            upload_errors.append("GCS health check failed")
            upload_enabled = False

        def record_prompt(name: str) -> None:
            try:
                template = prompt_registry.get(name)
            except KeyError:
                return
            prompt_log[name] = {"version": template.version}

        def update_progress(step: PipelineStep, message: str = "") -> None:
            progress.update(step, message)
            log_pipeline_progress(
                step_number=list(PipelineStep).index(step) + 1,
                total_steps=len(PipelineStep),
                step_name=step.name,
                status=message or "진행중"
            )
            if progress_callback:
                progress_callback(progress)

        try:
            # ===== Step 1: 데이터 수집 =====
            log_stage_start("Step 1: 데이터 수집", "YouTube, 네이버, 시장 트렌드 분석")
            log_input_data("제품명", product.get("name"))
            log_input_data("카테고리", product.get("category"))

            update_progress(PipelineStep.DATA_COLLECTION, "데이터 수집 시작")
            collected_data = await self._collector.collect_all_data_async(
                product=product,
                config=config,
                progress_callback=update_progress,
            )

            # 수집 결과 로깅
            log_output_data("YouTube 동영상 수집", f"{len(collected_data.youtube_videos)}개")
            log_output_data("핵심 인사이트", f"{len(collected_data.top_insights or [])}개")
            log_stage_end("Step 1: 데이터 수집", f"총 {len(collected_data.youtube_videos)}개 데이터 수집")

            # ===== Step 2: 마케팅 전략 생성 =====
            log_stage_start("Step 2: 마케팅 전략 생성", "AI 기반 전략 분석")
            log_input_data("수집된 인사이트", collected_data.top_insights[:3] if collected_data.top_insights else [])

            update_progress(PipelineStep.STRATEGY_GENERATION, "마케팅 전략 생성 중...")
            record_prompt("marketing.analysis")
            # NOTE: 현재 실행 환경에서 `asyncio.to_thread()`/`run_in_executor()`가 정상 동작하지 않는
            # 문제가 있어, 동기 호출로 처리합니다.
            strategy = self._marketing.generate_strategy(
                product=product,
                collected_data=collected_data,
            )

            # 전략 결과 로깅
            log_output_data("훅 문구 제안", strategy.get("hook_suggestions", [])[:3])
            log_output_data("타겟 오디언스", strategy.get("target_audience", "N/A"))
            log_output_data("추천 스타일", strategy.get("style", "N/A"))
            log_stage_end("Step 2: 마케팅 전략 생성", f"훅 {len(strategy.get('hook_suggestions', []))}개 생성")

            # ===== Step 3-5: 병렬 콘텐츠 생성 =====
            log_stage_start("Step 3-5: 콘텐츠 병렬 생성", "SNS 포스팅 + 썸네일 + 비디오 동시 생성")

            async def run_social():
                if config.generate_social:
                    log_info("    🔹 [SNS 포스팅] 생성 시작...")
                    log_input_data("SNS - 제품", product.get("name"))
                    log_input_data("SNS - 인사이트 수", len(collected_data.top_insights or []))
                    update_progress(
                        PipelineStep.SOCIAL_GENERATION, "SNS 포스팅 생성 중..."
                    )
                    try:
                        record_prompt("social.media.posts")
                        posts = await self._social.generate_posts(
                            product=product,
                            strategy=strategy,
                            top_insights=collected_data.top_insights,
                        )
                        strategy["social_posts"] = posts
                        log_output_data("SNS - 생성된 포스팅 수", len(posts) if posts else 0)
                        log_info("    ✅ [SNS 포스팅] 생성 완료")
                    except Exception as e:
                        log_error(f"    ❌ [SNS 포스팅] 생성 실패: {e}")
                        log_stage_fail("SNS 포스팅 생성", str(e))

            async def run_thumbnail():
                if config.generate_thumbnail:
                    log_info("    🔹 [썸네일] 생성 시작...")
                    log_input_data("썸네일 - 멀티 생성 모드", config.generate_multi_thumbnails)
                    log_input_data("썸네일 - 생성 개수", config.thumbnail_count)
                    update_progress(
                        PipelineStep.THUMBNAIL_CREATION, "썸네일 생성 중..."
                    )
                    if config.generate_multi_thumbnails:
                        if config.thumbnail_styles:
                            styles = config.thumbnail_styles[: config.thumbnail_count]
                        else:
                            all_styles = list(THUMBNAIL_STYLES.keys())
                            n = min(config.thumbnail_count, len(all_styles))
                            styles = random.sample(all_styles, n)

                        log_input_data("썸네일 - 선택된 스타일", styles)
                        thumbnails = self._thumbnail.generate_from_strategy(
                            product=product,
                            strategy=strategy,
                            count=config.thumbnail_count,
                            styles=styles,
                        )
                        generated_content.multi_thumbnails = thumbnails
                        if thumbnails:
                            generated_content.thumbnail_data = thumbnails[0].get(
                                "image"
                            )
                        log_output_data("썸네일 - 생성 완료", f"{len(thumbnails or [])}개")
                    else:
                        hooks = strategy.get("hook_suggestions", [])
                        # 훅 텍스트 안전 추출 (Dict/Str 처리)
                        first_hook = hooks[0] if hooks else None
                        if isinstance(first_hook, dict):
                            hook_text = first_hook.get("hook", f"{product.get('name', '제품')}!")
                        else:
                            hook_text = str(first_hook) if first_hook else f"{product.get('name', '제품')}!"
                        log_input_data("썸네일 - 훅 텍스트", hook_text)
                        thumbnail = self._thumbnail.generate(
                            product=product,
                            hook_text=hook_text,
                        )
                        generated_content.thumbnail_data = thumbnail
                        log_output_data("썸네일 - 이미지 크기", f"{len(thumbnail or b'')} bytes")
                    log_info("    ✅ [썸네일] 생성 완료")

            async def run_video():
                if config.generate_video:
                    log_info("    🔹 [비디오] 생성 시작...")
                    log_input_data("비디오 - 길이", f"{config.video_duration}초")
                    log_input_data("비디오 - 듀얼 페이즈 모드", config.video_dual_phase_beta)
                    update_progress(PipelineStep.VIDEO_GENERATION, "비디오 생성 중...")
                    video_mode = "single"
                    phase2_prompt = None
                    enable_dual_phase_beta = False

                    if config.video_dual_phase_beta:
                        video_mode = "dual"
                        enable_dual_phase_beta = True
                        category = product.get("category", "product")
                        phase2_prompt = (
                            "Freeze frame hero shot of a premium "
                            f"{category} on a clean studio background. "
                            "Soft light leaks, slow zoom in, subtle CTA text."
                        )
                        log_input_data("비디오 - Phase2 프롬프트", phase2_prompt[:50])

                    video_result = self._video.generate_marketing_video(
                        product=product,
                        strategy=strategy,
                        duration_seconds=config.video_duration,
                        mode=video_mode,
                        phase2_prompt=phase2_prompt,
                        enable_dual_phase_beta=enable_dual_phase_beta,
                    )

                    if isinstance(video_result, bytes):
                        generated_content.video_bytes = video_result
                        log_output_data("비디오 - 파일 크기", f"{len(video_result):,} bytes")
                    else:
                        generated_content.video_url = video_result
                        log_output_data("비디오 - GCS URL", video_result[:80] if video_result else "N/A")
                    log_info("    ✅ [비디오] 생성 완료")

            # Run parallel tasks
            await asyncio.gather(run_social(), run_thumbnail(), run_video())
            log_stage_end("Step 3-5: 콘텐츠 병렬 생성", "모든 콘텐츠 생성 완료")

            # ===== Step 6: GCS 업로드 =====
            if upload_enabled:
                log_stage_start("Step 6: GCS 업로드", "생성된 콘텐츠를 클라우드에 저장")
                update_progress(PipelineStep.UPLOAD, "Uploading to GCS...")
                upload_status, upload_errors = self._upload_to_gcs(
                    product=product,
                    config=config,
                    collected_data=collected_data,
                    strategy=strategy,
                    generated_content=generated_content,
                )
                log_output_data("업로드 상태", upload_status.value if hasattr(upload_status, 'value') else upload_status)
                if upload_errors:
                    log_output_data("업로드 오류", upload_errors)
                log_stage_end("Step 6: GCS 업로드", f"상태: {upload_status}")

            # ===== 🎉 파이프라인 완료 - 최종 요약 =====
            update_progress(PipelineStep.COMPLETED, "파이프라인 완료!")
            duration = time.time() - start_time
            self._last_duration = duration

            # 최종 요약 박스 출력
            summary_items = [
                f"✅ 제품: {product.get('name', 'N/A')}",
                f"📊 수집된 데이터: YouTube {len(collected_data.youtube_videos or [])}개",
                f"💡 생성된 훅 문구: {len(strategy.get('hook_suggestions', []))}개",
                f"🖼️ 썸네일: {'생성됨' if generated_content.thumbnail_data else '건너뜀'}",
                f"🎬 비디오: {'생성됨' if generated_content.video_bytes or generated_content.video_url else '건너뜀'}",
                f"📱 SNS 포스팅: {len(strategy.get('social_posts', []))}개",
                f"☁️ GCS 업로드: {upload_status}",
                f"⏱️ 총 소요 시간: {duration:.2f}초",
            ]
            log_summary_box("파이프라인 실행 결과 요약", summary_items)

            log_success(f"파이프라인 실행 완료 (소요 시간: {duration:.2f}초)")
            log_timing("Pipeline Execution", duration * 1000)
            log_separator("double")

            result = PipelineResult(
                success=True,
                product_name=product.get("name", ""),
                config=config,
                collected_data=collected_data,
                strategy=strategy,
                generated_content=generated_content,
                prompt_log=prompt_log,
                approval_status="draft",
                audit_trail=audit_trail,
                upload_status=upload_status,
                upload_errors=upload_errors,
                duration_seconds=duration,
                pipeline_metrics=collected_data.pipeline_metrics if collected_data else None,
            )

            # 히스토리 저장
            try:
                save_path = self._history.save_result(result)
                log_info(f"    💾 히스토리 저장: {save_path}")
            except Exception as e:
                log_error(f"    ⚠️ 히스토리 저장 실패: {e}")


            if self._rag_ingestion:
                try:
                    self._rag_ingestion.ingest_pipeline_result(result)
                except Exception as e:
                    logger.error(f"RAG ingestion failed: {e}")

            return result

        except Exception as e:
            # ===== ❌ 파이프라인 실패 =====
            log_stage_fail("파이프라인 실행", str(e))
            log_error(f"    ⚠️ 오류 상세: {type(e).__name__}: {e}")
            update_progress(PipelineStep.FAILED, str(e))
            duration = time.time() - start_time
            self._last_duration = duration

            # 실패 요약
            summary_items = [
                f"❌ 제품: {product.get('name', 'N/A')}",
                f"⚠️ 오류 유형: {type(e).__name__}",
                f"📝 오류 메시지: {str(e)[:80]}",
                f"⏱️ 실패까지 소요 시간: {duration:.2f}초",
            ]
            log_summary_box("파이프라인 실패 요약", summary_items)
            log_separator("double")

            result = PipelineResult(
                success=False,
                product_name=product.get("name", ""),
                config=config,
                collected_data=collected_data,
                strategy=strategy,
                generated_content=generated_content,
                prompt_log=prompt_log,
                approval_status="draft",
                audit_trail=audit_trail,
                upload_status=upload_status,
                upload_errors=upload_errors,
                error_message=str(e),
                duration_seconds=duration,
                pipeline_metrics=collected_data.pipeline_metrics if collected_data else None,
            )

            # 실패 결과도 저장
            try:
                self._history.save_result(result)
                log_info("    💾 실패 기록 저장 완료")
            except Exception as save_err:
                log_error(f"    ⚠️ 실패 기록 저장 실패: {save_err}")

            return result

    def execute_data_collection_only(
        self,
        product: dict,
        config: PipelineConfig,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> CollectedData:
        """데이터 수집만 실행"""
        logger.info(f"데이터 수집 시작: {product.get('name', 'N/A')}")
        try:
            collected_data = self._collector.collect_all_data(
                product=product,
                config=config,
            )
            return collected_data

        except Exception as e:
            logger.error(f"데이터 수집 실패: {e}")
            raise PipelineError(
                f"데이터 수집 실패: {e}",
                original_error=e,
            ) from e

    def _upload_to_gcs(
        self,
        product: dict,
        config: PipelineConfig,
        collected_data: CollectedData,
        strategy: dict,
        generated_content: GeneratedContent,
    ) -> tuple[UploadStatus, list[str]]:
        """GCS upload (auto bucket creation)."""
        prefix = build_gcs_prefix(product, "pipeline")
        storage = self._storage
        errors: list[str] = []
        total_uploads = 0

        if collected_data:
            total_uploads += 1
            try:
                storage.upload(
                    data=collected_data.model_dump(),
                    path=f"{prefix}/collected_data.json",
                    content_type="application/json",
                )
            except Exception as e:
                log_error(f"GCS collected_data upload failed: {e}")
                errors.append(f"collected_data.json: {e}")

        if strategy:
            total_uploads += 1
            try:
                storage.upload(
                    data=strategy,
                    path=f"{prefix}/strategy.json",
                    content_type="application/json",
                )
            except Exception as e:
                log_error(f"GCS strategy upload failed: {e}")
                errors.append(f"strategy.json: {e}")

        if generated_content.thumbnail_data and not generated_content.multi_thumbnails:
            total_uploads += 1
            try:
                ext = detect_image_ext(generated_content.thumbnail_data)
                thumb_path = f"{prefix}/thumbnail{ext}"
                storage.upload(
                    data=generated_content.thumbnail_data,
                    path=thumb_path,
                    content_type="image/png" if ext == ".png" else "image/jpeg",
                )
                generated_content.thumbnail_url = gcs_url_for(storage, thumb_path)
            except Exception as e:
                log_error(f"GCS thumbnail upload failed: {e}")
                errors.append(f"thumbnail{ext}: {e}")

        if generated_content.multi_thumbnails:
            for idx, item in enumerate(generated_content.multi_thumbnails):
                image_bytes = item.get("image") or item.get("image_bytes")
                if not image_bytes:
                    continue
                total_uploads += 1
                try:
                    ext = detect_image_ext(image_bytes)
                    style_key = (item.get("style") or "thumb").replace(" ", "_")[:20]
                    multi_path = f"{prefix}/thumbnail_{idx + 1}_{style_key}{ext}"
                    storage.upload(
                        data=image_bytes,
                        path=multi_path,
                        content_type="image/png" if ext == ".png" else "image/jpeg",
                    )
                    item["url"] = gcs_url_for(storage, multi_path)
                except Exception as e:
                    log_error(f"GCS thumbnail #{idx + 1} upload failed: {e}")
                    errors.append(f"thumbnail_{idx + 1}{ext}: {e}")

        if generated_content.video_bytes:
            total_uploads += 1
            try:
                ext = detect_video_ext(generated_content.video_bytes)
                video_path = f"{prefix}/video{ext}"
                storage.upload(
                    data=generated_content.video_bytes,
                    path=video_path,
                    content_type="video/mp4"
                    if ext == ".mp4"
                    else "application/octet-stream",
                )
                generated_content.video_url = gcs_url_for(storage, video_path)
            except Exception as e:
                log_error(f"GCS video upload failed: {e}")
                errors.append(f"video{ext}: {e}")

        metadata = {
            "product": product,
            "config": config.model_dump()
            if hasattr(config, "model_dump")
            else dict(config),
            "duration_seconds": getattr(self, "_last_duration", None),
            "thumbnail_url": generated_content.thumbnail_url,
            "video_url": generated_content.video_url,
        }
        total_uploads += 1
        try:
            storage.upload(
                data=metadata,
                path=f"{prefix}/metadata.json",
                content_type="application/json",
            )
        except Exception as e:
            log_error(f"GCS metadata upload failed: {e}")
            errors.append(f"metadata.json: {e}")

        if total_uploads == 0:
            return UploadStatus.SKIPPED, []
        if not errors:
            return UploadStatus.SUCCESS, []
        if len(errors) < total_uploads:
            return UploadStatus.PARTIAL, errors
        return UploadStatus.FAILED, errors
