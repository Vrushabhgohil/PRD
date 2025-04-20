# utils.py (Fixed and Updated)
import io
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import inch


class PDFGenerator:
    def __init__(self):
        self.buffer = io.BytesIO()
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=35,
            leftMargin=35,
            topMargin=35,
            bottomMargin=35
        )
        self.styles = getSampleStyleSheet()
        self.story = []
        self._project_name = ""
        self.setup_styles()

    def setup_styles(self):
        self.title_style = ParagraphStyle(
            name="TitleStyle",
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=20
        )

        self.subtitle_style = ParagraphStyle(
            name="SubtitleStyle",
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            spaceAfter=20
        )

        self.heading_style = ParagraphStyle(
            name="HeadingStyle",
            fontSize=14,
            leading=18,
            spaceBefore=12,
            spaceAfter=6,
            underlineWidth=1,
            alignment=TA_JUSTIFY
        )

        self.normal_style = ParagraphStyle(
            name="NormalStyle",
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY
        )

        self.bullet_style = ParagraphStyle(
            name="BulletStyle",
            parent=self.normal_style,
            bulletFontName='Helvetica',
            bulletFontSize=10,
            leftIndent=20
        )

    def extract_project_name(self, content: str) -> str:
        # Tries to extract the project name from the introduction or first line
        match = re.search(r'#\s*Product Requirements Document.*?\n+##\s*Introduction\s+(.*?)\n', content, re.DOTALL | re.IGNORECASE)
        if match:
            intro_text = match.group(1).strip()
            # Try to find a name within quotes or a capitalized phrase
            name_match = re.search(r'"([^"]+)"|([A-Z][\w\s]+)', intro_text)
            if name_match:
                return name_match.group(1) or name_match.group(2)
        return "Unnamed Project"

    def create_cover_page(self):
        self.story.append(Spacer(1, 0.75 * inch))
        self.story.append(Paragraph("Product Requirements Document", self.title_style))
        self.story.append(Paragraph(self._project_name, self.subtitle_style))
        self.story.append(Spacer(1, 0.5 * inch))

        date_style = ParagraphStyle(
            'DateStyle',
            parent=self.normal_style,
            alignment=TA_CENTER
        )
        self.story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d')}", date_style))
        self.story.append(PageBreak())

    def parse_markdown_content(self, content: str):
        self._project_name = self.extract_project_name(content)
        self.create_cover_page()

        # Split sections based on markdown H2 headers
        sections = re.split(r'(?=\n##\s)', content.strip())

        for section in sections:
            if not section.strip():
                continue

            header_match = re.match(r'\n##\s+(.*?)\n', section)
            if header_match:
                header = header_match.group(1).strip()
                self.story.append(Paragraph(header, self.heading_style))
                content_start = header_match.end()
            else:
                content_start = 0

            section_content = section[content_start:].strip()
            self.process_section_content(section_content)

    def process_section_content(self, content: str):
        lines = content.split('\n')
        current_paragraph = []
        bullet_items = []

        for line in lines:
            line = line.strip()

            if not line:
                if current_paragraph:
                    self.story.append(Paragraph(' '.join(current_paragraph), self.normal_style))
                    current_paragraph = []
                continue

            if line.startswith(('- ', '* ')):
                if current_paragraph:
                    self.story.append(Paragraph(' '.join(current_paragraph), self.normal_style))
                    current_paragraph = []

                bullet_items.append(
                    ListItem(Paragraph(line[2:].strip(), self.bullet_style))
                )
            else:
                if bullet_items:
                    self.story.append(ListFlowable(
                        bullet_items,
                        bulletType='bullet',
                        leftIndent=20,
                        bulletIndent=10
                    ))
                    bullet_items = []
                current_paragraph.append(line)

        # Final flush
        if bullet_items:
            self.story.append(ListFlowable(
                bullet_items,
                bulletType='bullet',
                leftIndent=20,
                bulletIndent=10
            ))

        if current_paragraph:
            self.story.append(Paragraph(' '.join(current_paragraph), self.normal_style))

    def add_page_number(self, canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        page_num_text = f"Page {doc.page}"
        canvas.drawCentredString(0.5 * A4[0], 0.75 * inch, page_num_text)
        canvas.restoreState()

    def generate(self, content: str):
        """Generate PDF from markdown-like content string"""
        try:
            self.buffer = io.BytesIO()
            self.story = []
            self.parse_markdown_content(content)
            self.doc.build(self.story, onFirstPage=self.add_page_number, onLaterPages=self.add_page_number)
            self.buffer.seek(0)
            return self.buffer
        except Exception as e:
            print(f"Error generating PDF: {str(e)}")
            raise
