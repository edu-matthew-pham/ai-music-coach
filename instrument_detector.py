# instrument_detector.py

import numpy as np
import librosa


MODEL_NAME = (
    "Bhaveen/"
    "epoch_musical_instruments_identification_2"
)


# Loading the model is relatively expensive, so we delay it
# until the first time an instrument is actually classified.
# Importing this module stays cheap, which keeps the test
# suite fast and lets it run without downloading anything.
_instrument_classifier = None


def get_classifier():
    """
    Load the pretrained model on first use, then reuse it.
    """

    global _instrument_classifier

    if _instrument_classifier is None:

        # Imported here rather than at the top of the file so
        # that torch is only loaded when it is really needed.
        from transformers import pipeline

        _instrument_classifier = pipeline(
            "audio-classification",
            model=MODEL_NAME
        )

    return _instrument_classifier


def prepare_audio(
    sound,
    sample_rate,
    target_sample_rate=16000
):
    """
    Prepare recorded audio for the pretrained model.

    The model expects mono audio sampled at 16 kHz.
    """

    # Stereo -> mono
    if sound.ndim > 1:
        sound = sound.mean(axis=1)

    sound = sound.astype(float)

    # Normalise values.
    largest_value = np.max(np.abs(sound))

    if largest_value > 0:
        sound = sound / largest_value

    # Convert to the sample rate expected by the model.
    if sample_rate != target_sample_rate:

        sound = librosa.resample(
            sound,
            orig_sr=sample_rate,
            target_sr=target_sample_rate
        )

    # Use the first three seconds.
    maximum_samples = (
        target_sample_rate * 3
    )

    sound = sound[:maximum_samples]

    return sound.astype(np.float32)


def detect_instrument(audio):
    """
    Classify the instrument in a Gradio recording.

    Returns the three highest predictions.
    """

    if audio is None:
        return []

    sample_rate, sound = audio

    sound = prepare_audio(
        sound,
        sample_rate
    )

    classifier = get_classifier()

    results = classifier(
        sound,
        top_k=3
    )

    return results