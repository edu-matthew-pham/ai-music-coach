
import gradio as gr
from gradio_musicmixer import MusicMixer


example = MusicMixer().example_value()

demo = gr.Interface(
    lambda x:x,
    MusicMixer(),  # interactive version of your component
    MusicMixer(),  # static version of your component
    # examples=[[example]],  # uncomment this line to view the "example version" of your component
)


if __name__ == "__main__":
    demo.launch()
