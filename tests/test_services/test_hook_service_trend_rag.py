import pytest


class _RagClientReturnsCoroutine:
    async def search(self, query: str, max_results: int = 2):
        async def _inner():
            return [{"title": "t", "snippet": "s"}]

        # 버그 케이스: await search() 결과가 다시 coroutine으로 나오는 상황
        return _inner()


class _FakeGemini:
    async def generate_text_async(self, prompt: str) -> str:
        # 훅 생성은 이 테스트의 대상이 아니므로 최소 응답만 반환
        return "1) 테스트 훅 🙂\n2) 테스트 훅 🙂\n3) 테스트 훅 🙂"


@pytest.mark.asyncio
async def test_generate_trend_hooks_handles_coroutine_search_results():
    from services.hook_service import HookService

    svc = HookService()
    svc._gemini = _FakeGemini()

    product = {"name": "p", "category": "c", "benefit": "b"}
    hooks = await svc.generate_trend_hooks(
        product=product,
        count=3,
        rag_client=_RagClientReturnsCoroutine(),
        length="short",
    )

    assert isinstance(hooks, list)

