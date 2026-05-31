import os
import webbrowser
from pathlib import Path


class VideoGenerator:

    async def generate(self, prompt):

        try:

            html_file = Path(
                "video/veo_player.html"
            ).absolute()

            html_content = html_file.read_text(
                encoding="utf-8"
            )

            html_content = html_content.replace(
                "</body>",
                f"""
                <script>
                localStorage.setItem(
                    'marvis_prompt',
                    {repr(prompt)}
                );
                </script>
                </body>
                """
            )

            temp_file = Path(
                "video/veo_temp.html"
            )

            temp_file.write_text(
                html_content,
                encoding="utf-8"
            )

            webbrowser.open(
                temp_file.absolute().as_uri()
            )

            return (
                "Opening Veo 3.1 in browser..."
            )

        except Exception as e:

            return f"Video Error: {e}"