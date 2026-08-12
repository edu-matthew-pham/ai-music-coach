
import gradio as gr
from gradio_testonly import TestOnly


example = TestOnly().example_value()

demo = gr.Interface(
    lambda x:x,
    TestOnly(),  # interactive version of your component
    TestOnly(),  # static version of your component
    # examples=[[example]],  # uncomment this line to view the "example version" of your component
)


if __name__ == "__main__":
    demo.launch()
