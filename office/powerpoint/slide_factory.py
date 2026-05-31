from pptx.util import Pt


class SlideFactory:

    @staticmethod
    def title_slide(
        prs,
        slide_data
    ):

        slide_layout = prs.slide_layouts[0]

        slide = prs.slides.add_slide(
            slide_layout
        )

        title = slide.shapes.title

        subtitle = slide.placeholders[1]

        title.text = slide_data["title"]

        subtitle.text = slide_data["subtitle"]

        title.text_frame.paragraphs[0].font.size = Pt(30)

    @staticmethod
    def bullet_slide(
        prs,
        slide_data
    ):

        slide_layout = prs.slide_layouts[1]

        slide = prs.slides.add_slide(
            slide_layout
        )

        title = slide.shapes.title

        title.text = slide_data["title"]

        body = slide.placeholders[1]

        tf = body.text_frame

        bullets = slide_data["bullets"]

        tf.text = bullets[0]

        for bullet in bullets[1:]:

            p = tf.add_paragraph()

            p.text = bullet
