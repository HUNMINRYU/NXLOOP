from infrastructure.services.notion_service import NotionService


def test_create_toggle_block_children_are_nested_under_toggle() -> None:
    service = NotionService(api_key="dummy")
    child = service._create_paragraph_block("hello")

    block = service._create_toggle_block("title", [child])

    assert block["type"] == "toggle"
    assert "children" not in block
    assert block["toggle"]["children"] == [child]
