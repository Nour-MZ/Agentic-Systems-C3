from business_agent import create_gradio_app
import os

if __name__ == "__main__":
    app = create_gradio_app()
    app.launch(
        server_name="0.0.0.0" if os.getenv("SPACE_ID") else "127.0.0.1",
        server_port=int(os.getenv("PORT", 7860)),
        share=True
    )