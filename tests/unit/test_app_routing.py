from xiliu.routing import recognize_intent, select_execution


def test_import_and_classification_use_registered_fast_service_workflow():
    for task in (
        "分别做成卡片收录进知识库",
        "将这两个网站导入 Inbox 并归类",
        "Save this link to my knowledge library",
        "把 https://example.com/a 保存到知识库",
        "将这两个链接存入 Knowledge",
        "把 https://example.com/a 收藏到知识库",
    ):
        assert select_execution(recognize_intent(task, model=object())) == "app_executor"
