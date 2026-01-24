"""Tests for model imports and table names."""


def test_models_import():
    from app.models.document import Document, SourceType, Language
    from app.models.token import Token, BreakType
    from app.models.session import ReadingSession

    assert Document.__tablename__ == "documents"
    assert Token.__tablename__ == "tokens"
    assert ReadingSession.__tablename__ == "sessions"
    assert SourceType.PASTE.value == "paste"
    assert Language.ENGLISH.value == "en"
    assert BreakType.PARAGRAPH.value == "paragraph"
