import io
import re
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY


class PDFGenerator:
    # Class-level constants for section patterns and titles
    SECTION_PATTERNS = [
        (r"1\.\s+Introduction(.*?)(?=2\.\s+Goals|$)", "1"),
        (r"2\.\s+Goals and Objectives(.*?)(?=3\.\s+User|$)", "2"),
        (r"3\.\s+User Personas and Roles(.*?)(?=4\.\s+Functional|$)", "3"),
        (r"4\.\s+Functional Requirements(.*?)(?=5\.\s+Non-Functional|$)", "4"),
        (r"5\.\s+Non-Functional Requirements(.*?)(?=6\.\s+User Interface|$)", "5"),
        (r"6\.\s+User Interface.*?Considerations(.*?)(?=7\.\s+Data|$)", "6"),
        (r"7\.\s+Data Requirements(.*?)(?=8\.\s+System|$)", "7"),
        (r"8\.\s+System Architecture(.*?)(?=9\.\s+Release|$)", "8"),
        (r"9\.\s+Release Criteria(.*?)(?=10\.\s+Timeline|$)", "9"),
        (r"10\.\s+Timeline(.*?)(?=11\.\s+Team|$)", "10"),
        (r"11\.\s+Team Structure(.*?)(?=12\.\s+User Stories|$)", "11"),
        (r"12\.\s+User Stories(.*?)(?=13\.\s+Cost|$)", "12"),
        (r"13\.\s+Open Issues(.*?)(?=15\.\s+Appendix|$)", "14"),
        (r"14\.\s+Appendix(.*?)(?=16\.\s+Points|$)", "15"),
        (r"15\.\s+Points Requiring(.*?)$", "16"),
    ]

    SECTION_TITLES = {
        "1": "Introduction",
        "2": "Goals and Objectives",
        "3": "User Personas and Roles",
        "4": "Functional Requirements",
        "5": "Non-Functional Requirements",
        "6": "User Interface (UI) / User Experience (UX) Considerations",
        "7": "Data Requirements",
        "8": "System Architecture & Technical Considerations",
        "9": "Release Criteria & Success Metrics",
        "10": "Timeline & Milestones",
        "11": "Team Structure",
        "12": "User Stories",
        "13": "Open Issues & Future Considerations",
        "14": "Appendix",
        "15": "Points Requiring Further Clarification",
    }

    TOC_ENTRIES = [
        "Introduction",
        "Goals and Objectives",
        "User Personas and Roles",
        "Functional Requirements",
        "Non-Functional Requirements",
        "User Interface (UI) / User Experience (UX) Considerations",
        "Data Requirements",
        "System Architecture & Technical Considerations",
        "Release Criteria & Success Metrics",
        "Timeline & Milestones",
        "Team Structure",
        "User Stories",
        "Open Issues & Future Considerations",
        "Appendix",
        "Points Requiring Further Clarification",
    ]

    def __init__(self):
        self.buffer = io.BytesIO()
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            margins=72,  # All margins the same
        )
        self.styles = self._setup_styles()
        self.story = []

    def _setup_styles(self):
        """Define all the styles needed for the document"""
        styles = getSampleStyleSheet()
        
        # Base style configurations
        base_title_config = {
            "alignment": TA_LEFT,
            "spaceAfter": 12,
            "fontName": "Helvetica-Bold",
        }
        
        base_heading_config = {
            "spaceAfter": 6,
            "textColor": colors.black,
            "fontName": "Helvetica-Bold",
        }
        
        # Create styles
        styles.add(ParagraphStyle(
            "TitleStyle",
            parent=styles["Heading1"],
            fontSize=18,
            **base_title_config
        ))
        
        styles.add(ParagraphStyle(
            "SubtitleStyle",
            parent=styles["Heading2"],
            fontSize=16,
            **base_title_config
        ))
        
        styles.add(ParagraphStyle(
            "HeadingStyle",
            parent=styles["Heading2"],
            fontSize=14,
            spaceBefore=18,
            **base_heading_config
        ))
        
        styles.add(ParagraphStyle(
            "SubheadingStyle",
            parent=styles["Heading3"],
            fontSize=12,
            spaceBefore=12,
            **base_heading_config
        ))
        
        styles.add(ParagraphStyle(
            "NormalStyle",
            parent=styles["Normal"],
            fontSize=11,
            spaceBefore=6,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
        ))
        
        styles.add(ParagraphStyle(
            "BulletStyle",
            parent=styles["Normal"],
            fontSize=11,
            spaceBefore=0,
            spaceAfter=3,
            leftIndent=20,
            bulletIndent=10,
        ))
        
        styles.add(ParagraphStyle(
            "TOCStyle",
            parent=styles["Normal"],
            fontSize=12,
            spaceBefore=3,
            spaceAfter=3,
            fontName="Helvetica",
        ))
        
        return styles

    def create_cover_page(self, project_name):
        """Create the cover page with title and date"""
        self.story.extend([
            Paragraph("Product Requirements Document:", self.styles["TitleStyle"]),
            Paragraph(project_name, self.styles["SubtitleStyle"]),
            Spacer(1, 0.2 * inch),
            Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y')}", 
                     self.styles["NormalStyle"]),
            Spacer(1, inch)
        ])

    def create_table_of_contents(self):
        """Create the table of contents"""
        self.story.extend([
            Paragraph("Table of Contents", self.styles["SubtitleStyle"]),
            Spacer(1, 0.2 * inch),
            *[Paragraph(f"{i+1}. {entry}", self.styles["TOCStyle"]) 
              for i, entry in enumerate(self.TOC_ENTRIES)]
        ])

    def extract_project_name(self, content):
        """Extract the project name from the content"""
        match = re.search(r"Product Requirements Document:?\s*([^\n]+)", content)
        return match.group(1).strip() if match else "Project Requirements Document"

    def parse_and_add_content(self, content):
        """Parse the content and add it to the story with proper formatting"""
        sections = self._extract_sections(content)

        for section_num, section_content in sections.items():
            section_title = self._get_section_title(section_num, section_content)
            self.story.append(
                Paragraph(f"{section_num}. {section_title}", self.styles["HeadingStyle"])
            )

            subsections = self._extract_subsections(section_content)

            if not subsections:
                clean_content = self._clean_section_content(section_content)
                if clean_content:
                    self._add_content_with_formatting(clean_content)
            else:
                for sub_num, sub_content in subsections.items():
                    sub_title = self._get_subsection_title(sub_num, sub_content)
                    self.story.append(
                        Paragraph(
                            f"{section_num}.{sub_num} {sub_title}",
                            self.styles["SubheadingStyle"],
                        )
                    )
                    clean_content = self._clean_subsection_content(sub_content)
                    if clean_content:
                        self._add_content_with_formatting(clean_content)

            self.story.append(Spacer(1, 0.3 * inch))

    def _extract_sections(self, content):
        """Extract main sections from content using regex"""
        sections = {}
        for pattern, section_num in self.SECTION_PATTERNS:
            match = re.search(pattern, content, re.DOTALL)
            sections[section_num] = (
                match.group(0) if match 
                else f"{section_num}. {self.SECTION_TITLES.get(section_num, f'Section {section_num}')}"
            )
        return sections

    def _extract_subsections(self, section_content):
        """Extract subsections from a section content"""
        matches = re.finditer(r"(\d+)\.(\d+)\s+(.*?)(?=\d+\.\d+|\Z)", section_content, re.DOTALL)
        return {m.group(2): m.group(0) for m in matches}

    def _get_section_title(self, section_num, content):
        """Extract the title of a section"""
        match = re.search(r"\d+\.\s+(.*?)(?=\n|\Z)", content)
        return match.group(1).strip() if match else self.SECTION_TITLES.get(section_num, f"Section {section_num}")

    def _get_subsection_title(self, subsection_num, content):
        """Extract the title of a subsection"""
        match = re.search(r"\d+\.\d+\s+(.*?)(?=\n|\Z)", content)
        return match.group(1).strip() if match else f"Subsection {subsection_num}"

    def _clean_section_content(self, content):
        """Remove the section title from content"""
        match = re.search(r"\d+\.\s+.*?\n(.*)", content, re.DOTALL)
        if match:
            return match.group(1).strip()
        lines = content.split("\n", 1)
        return lines[1].strip() if len(lines) > 1 else ""

    def _clean_subsection_content(self, content):
        """Remove the subsection title from content"""
        match = re.search(r"\d+\.\d+\s+.*?\n(.*)", content, re.DOTALL)
        if match:
            return match.group(1).strip()
        lines = content.split("\n", 1)
        return lines[1].strip() if len(lines) > 1 else ""

    def _add_content_with_formatting(self, content):
        """Add content with proper formatting (bullet points, etc.)"""
        if "FR01" in content or "ID | Requirement" in content:
            self._add_functional_requirements_table(content)
            return

        if content.strip().startswith("-") or "\n-" in content:
            self._add_bullet_points(content)
        else:
            self._add_paragraphs(content)

    def _add_bullet_points(self, content):
        """Helper method to add bullet point content"""
        items = []
        current_text = None
        
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("-"):
                if current_text is not None:
                    items.append(ListItem(Paragraph(current_text, self.styles["BulletStyle"])))
                current_text = line[1:].strip()
            elif current_text is not None:
                current_text += " " + line
            else:
                self.story.append(Paragraph(line, self.styles["NormalStyle"]))

        if current_text is not None:
            items.append(ListItem(Paragraph(current_text, self.styles["BulletStyle"])))

        if items:
            self.story.append(ListFlowable(items, bulletType="bullet", start=None))

    def _add_paragraphs(self, content):
        """Helper method to add regular paragraphs"""
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        self.story.extend(Paragraph(p, self.styles["NormalStyle"]) for p in paragraphs)

    def _add_functional_requirements_table(self, content):
        """Parse and add a table for functional requirements"""
        rows = [["ID", "Requirement Description", "Priority", "Dependencies"]]
        
        for line in content.split("\n"):
            line = line.strip()
            if (line.startswith("FR") or line.startswith("ID")) and "|" in line:
                if line.startswith("ID"):
                    continue  # Skip header row
                cells = [cell.strip() for cell in line.split("|")]
                if len(cells) >= 4:
                    rows.append(cells[:4])

        if len(rows) == 1:  # Only header row
            rows.append(["FR01", "Placeholder requirement", "High", "-"])

        table = Table(rows, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))

        self.story.append(table)

    def generate(self, content):
        """Generate the PDF"""
        project_name = self.extract_project_name(content)
        
        self.create_cover_page(project_name)
        self.create_table_of_contents()
        self.story.append(PageBreak())
        self.parse_and_add_content(content)
        
        self.doc.build(self.story)
        self.buffer.seek(0)
        return self.buffer