from pptx.util import Inches

class InfographicEngine:

    @staticmethod
    def add_image(
        slide,
        image_path
    ):

        slide.shapes.add_picture(
            image_path,
            Inches(1),
            Inches(2),
            width=Inches(8)
        )
