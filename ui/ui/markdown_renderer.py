import markdown

class MarkdownRenderer:

    @staticmethod
    def render(text):

        return markdown.markdown(text)
