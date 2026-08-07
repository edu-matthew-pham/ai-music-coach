import instrument_detector


def test_model_is_not_loaded_on_import():
    """
    Importing the module must stay cheap.

    This guards the lazy loading: if the pipeline is ever
    moved back to the top of instrument_detector.py, this
    test fails and the whole suite slows down again.
    """

    assert instrument_detector._instrument_classifier is None


def test_detect_instrument_ignores_missing_audio():
    """
    No recording means no classification, so the model
    should never be loaded in this case.
    """

    assert instrument_detector.detect_instrument(None) == []
    assert instrument_detector._instrument_classifier is None
