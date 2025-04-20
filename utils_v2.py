import io
import re
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, 
    Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class PDFGenerator:
    def __init__(self):
        self.buffer = io.BytesIO()
        self.page_size = letter
        
        # Register Montserrat fonts (fallback to Helvetica)
        try:
            pdfmetrics.registerFont(TTFont('Montserrat-Regular', 'Montserrat-Regular.ttf'))
            pdfmetrics.registerFont(TTFont('Montserrat-Bold', 'Montserrat-Bold.ttf'))
            self.font_regular = 'Montserrat-Regular'
            self.font_bold = 'Montserrat-Bold'
        except:
            self.font_regular = 'Helvetica'
            self.font_bold = 'Helvetica-Bold'
        
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=self.page_size,
            leftMargin=72,
            rightMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        self.styles = getSampleStyleSheet()
        self.setup_styles()
        self.story = []
    
    def setup_styles(self):
        """Define all the styles needed for the document"""
        # Cover Title Style
        self.cover_title_style = ParagraphStyle(
            'CoverMainTitleStyle',
            parent=self.styles['Heading1'],
            fontSize=28,
            leading=34,
            alignment=1,  # CENTER
            spaceAfter=12,
            fontName=self.font_bold,
            textColor=colors.HexColor('#2c3e50')
        )
        
        # Cover Subtitle Style
        self.cover_subtitle_style = ParagraphStyle(
            'CoverProductTitleStyle',
            parent=self.styles['Heading1'],
            fontSize=24,
            leading=30,
            alignment=1, 
            spaceAfter=36,
            fontName=self.font_bold,
            textColor=colors.HexColor('#3498db')
        )
        
        # Section Heading Style
        self.heading_style = ParagraphStyle(
            'HeadingStyle',
            parent=self.styles['Heading2'],
            fontSize=20,
            leading=26,
            spaceBefore=24,
            spaceAfter=12,
            fontName=self.font_bold,
            textColor=colors.HexColor('#2c3e50')
        )
        
        # Subheading Style
        self.subheading_style = ParagraphStyle(
            'SubheadingStyle',
            parent=self.styles['Heading3'],
            fontSize=16,
            leading=22,
            spaceBefore=16,
            spaceAfter=8,
            fontName=self.font_bold,
            textColor=colors.HexColor('#3498db')
        )
        
        # Normal Paragraph Style
        self.normal_style = ParagraphStyle(
            'NormalStyle',
            parent=self.styles['Normal'],
            fontSize=14,
            leading=18,
            spaceBefore=6,
            spaceAfter=8,
            alignment=0,  # LEFT
            fontName=self.font_regular,
            textColor=colors.HexColor('#34495e')
        )
        
        # Bullet List Style
        self.bullet_style = ParagraphStyle(
            'BulletStyle',
            parent=self.styles['Normal'],
            fontSize=14,
            leading=18,
            leftIndent=24,
            spaceBefore=6,
            spaceAfter=4,
            fontName=self.font_regular,
            textColor=colors.HexColor('#34495e'),
            bulletFontName=self.font_bold,
            bulletFontSize=14,
            bulletIndent=12
        )
        
        # TOC Title Style
        self.toc_title_style = ParagraphStyle(
            'TOCTitleStyle',
            parent=self.styles['Heading1'],
            fontSize=24,
            leading=30,
            alignment=1,  # CENTER
            spaceBefore=36,
            spaceAfter=36,
            fontName=self.font_bold,
            textColor=colors.HexColor('#2c3e50')
        )
        
        # TOC Heading Style
        self.toc_heading_style = ParagraphStyle(
            'TOCHeadingStyle',
            parent=self.styles['Heading2'],
            fontSize=15,
            leading=24,
            spaceBefore=24,
            spaceAfter=12,
            fontName=self.font_regular,
            textColor=colors.HexColor('#2c3e50')
        )
        
        # TOC Subheading Style
        self.toc_subheading_style = ParagraphStyle(
            'TOCSubheadingStyle',
            parent=self.styles['Heading3'],
            fontSize=16,
            leading=22,
            spaceBefore=12,
            spaceAfter=8,
            fontName=self.font_bold,
            textColor=colors.HexColor('#3498db')
        )
        self.footer_company_style = ParagraphStyle(
            'FooterCompanyStyle',
            parent=self.styles['Heading2'],
            fontSize=18,
            leading=24,
            alignment=1,  # CENTER
            spaceAfter=12,
            fontName=self.font_bold,
            textColor=colors.HexColor('#2c3e50')
        )
        
        # Footer Contact Style
        self.footer_contact_style = ParagraphStyle(
            'FooterContactStyle',
            parent=self.styles['Normal'],
            fontSize=14,
            leading=18,
            alignment=1,  # CENTER
            spaceBefore=6,
            fontName=self.font_regular,
            textColor=colors.HexColor('#34495e')
        )
    
    def create_cover_page(self,project_name):
        """Create a cover page matching the second image's format"""
        print("Cover of pages-----------------------------------------------")
        cover_elements = []
        
        cover_elements.append(Paragraph("Product Requirements Document", 
                                    self.cover_title_style))
        
        cover_elements.append(Paragraph(project_name, 
                                    self.cover_subtitle_style))
        
        cover_elements.append(Spacer(1, 100))
        
        if hasattr(self, 'Codehub LLP'):
            cover_elements.append(Paragraph("Codehub LLP", 
                                        self.footer_company_style))
        
        return cover_elements
    
    def create_toc_page(self, content):
        """Create a clean table of contents page"""
        print("Table of content-----------------------------------------------")
        self.story.append(Paragraph("Table of Contents", self.toc_title_style))
        
        # Extract headings from content
        headings = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Match section headings
            heading_match = re.match(r'\*\*(\d+)\.\s+(.*?)\*\*', line)
            if heading_match:
                headings.append((heading_match.group(1), heading_match.group(2), 'heading'))
            
            # Match bullet points that look like subheadings
            elif line.startswith('* ') and len(line.split()) <= 5 and not line.endswith('.'):
                headings.append((None, line[2:].strip(), 'subheading'))
        
        # Add TOC entries
        for num, title, typ in headings:
            if typ == 'heading':
                self.story.append(Paragraph(f"{num}. {title}", self.toc_heading_style))
            
        
        self.story.append(PageBreak())
    
    def parse_content(self, content):
        """Parse the content and add it to the story with proper formatting"""
        lines = content.split('\n')
        bullet_items = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Handle section headings
            heading_match = re.match(r'\*\*(\d+)\.\s+(.*?)\*\*', line)
            if heading_match:
                # Add any pending bullet list first
                if bullet_items:
                    self.story.append(self._create_bullet_list(bullet_items))
                    bullet_items = []
                
                self.story.append(Paragraph(
                    f"{heading_match.group(1)}. {heading_match.group(2)}", 
                    self.heading_style
                ))
                continue
                
            # Handle bullet points
            if line.startswith('* '):
                bullet_items.append(line[2:].strip())
                continue
                
            # Handle subheadings
            if len(line.split()) <= 5 and line.endswith(':'):
                # Add any pending bullet list first
                if bullet_items:
                    self.story.append(self._create_bullet_list(bullet_items))
                    bullet_items = []
                
                self.story.append(Paragraph(line, self.subheading_style))
                continue
                
            # Regular paragraph - add any pending bullet list first
            if bullet_items:
                self.story.append(self._create_bullet_list(bullet_items))
                bullet_items = []
            
            self.story.append(Paragraph(line, self.normal_style))
            self.story.append(Spacer(1, 0.1 * inch))
        
        # Add any remaining bullet items
        if bullet_items:
            self.story.append(self._create_bullet_list(bullet_items))
    
    def _create_bullet_list(self, items):
        """Helper method to create a bullet list from items"""
        flowables = []
        for item in items:
            flowables.append(Paragraph(item, self.bullet_style))
        
        return ListFlowable(
            flowables,
            bulletType='bullet',
            bulletColor='#3498db',
            leftIndent=24,
            bulletOffsetY=2,
            spaceBefore=6,
            spaceAfter=8
        )
    
    def add_company_footer(self):
        """Add company information on the last page"""
        self.story.append(PageBreak())
        self.story.append(Spacer(1, 3 * inch))
        self.story.append(Paragraph("Codehub LLP", self.footer_company_style))
        self.story.append(Paragraph("For Further Inquiry Please Contact: helloworld@gmail.com", 
                                  self.footer_contact_style))
        
    def generate(self, content, project_name=None):
        """Generate the PDF document"""
        if project_name is None:
            project_name = self.extract_project_name(content)
        
        self.story.extend(self.create_cover_page(project_name))
        self.create_toc_page(content)
        self.parse_content(content)
        self.add_company_footer()
        self.doc.build(self.story)
        self.buffer.seek(0)
        return self.buffer
    
    def extract_project_name(self, content):
        """Extract the project name from the content"""
        match = re.search(r"Product Requirements Document.*?for\s+(.*?)\*\*", content, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return "Project Requirements Document"