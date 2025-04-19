from dotenv import load_dotenv
import os
import uvicorn
import io
import re
from datetime import datetime
from groq import Groq
from pydantic import BaseModel
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any, Tuple
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, ListFlowable, ListItem
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.units import inch

load_dotenv()
app = FastAPI()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# In-memory storage (you can later replace with Redis or DB)
conversation_state = {}

class RequirementsData(BaseModel):
    session_id: str
    requirements: str

def system_prompt():
    return """
    You are an expert project analyst and technical writer. Your task is to generate a detailed Product Requirements Document (PRD) based on the user's input. Structure your response as a formal PRD with the following EXACT format:

    Product Requirements Document: [Project Name]

    1. Introduction
       1.1 Purpose
       [Purpose content here]
       1.2 Scope
       [Scope content here]
       1.3 Target Audience
       [Target audience content here]
       1.4 Definitions & Glossary
       [Definitions and glossary content here]

    2. Goals and Objectives
       2.1 Business Goals
       [Business goals content here - use bullet points]
       2.2 User Goals
       [User goals content here - use bullet points]
       2.3 Non-Goals
       [Non-goals content here - use bullet points]

    3. User Personas and Roles
       3.1 Key User Types
       [User types content here]
       3.2 Role-Based Access Control
       [Role-based access control content here]

    4. Functional Requirements
       [Create a table with columns: ID, Requirement Description, Priority, Dependencies]
       [Use format ID: FR01, FR02, etc.]

    5. Non-Functional Requirements
       5.1 Performance
       [Performance requirements content here]
       5.2 Scalability
       [Scalability requirements content here]
       5.3 Reliability & Availability
       [Reliability and availability content here]
       5.4 Security
       [Security requirements content here]
       5.5 Usability
       [Usability requirements content here]
       5.6 Maintainability
       [Maintainability requirements content here]
       5.7 Compliance
       [Compliance requirements content here]

    6. User Interface (UI) / User Experience (UX) Considerations
       6.1 Entry Points & User Flow
       [Entry points and user flow content here]
       6.2 Core Experience
       [Core experience content here]
       6.3 UI/UX Highlights
       [UI/UX highlights content here]
       6.4 Handling Edge Cases
       [Edge cases content here]

    7. Data Requirements
       7.1 Data Sources
       [Data sources content here]
       7.2 Data Storage
       [Data storage content here]
       7.3 Data Privacy & Security
       [Data privacy and security content here]

    8. System Architecture & Technical Considerations
       8.1 Architecture Style
       [Architecture style content here]
       8.2 Integration Points
       [Integration points content here]
       8.3 Technology Stack
       [Technology stack content here]
       8.4 Potential Challenges
       [Potential challenges content here]

    9. Release Criteria & Success Metrics
       9.1 Release Criteria
       [Release criteria content here]
       9.2 Success Metrics
       User-Centric:
       [User-centric metrics content here - use bullet points with specific percentages]
       Business:
       [Business metrics content here - use bullet points with specific percentages]
       Technical:
       [Technical metrics content here - use bullet points with specific percentages]

    10. Timeline & Milestones
        [Timeline content here]

    11. Team Structure
        [Team structure content here]

    12. User Stories
        [User stories content here]

    13. Cost Estimation
        13.1 Assumptions
        [Assumptions content here]
        13.2 Development Cost
        [Development cost content here]
        13.3 Running Costs
        [Running costs content here]
        13.4 Third-Party Costs
        [Third-party costs content here]

    14. Open Issues & Future Considerations
        [Open issues and future considerations content here]

    15. Appendix
        [Appendix content here]

    16. Points Requiring Further Clarification
        [Points requiring further clarification content here]

    IMPORTANT FORMATTING INSTRUCTIONS:
    1. Use EXACTLY this section numbering (1., 1.1, etc.)
    2. Include all 16 main sections and all subsections exactly as above
    3. For bullet points, use a dash (-) at the beginning of the line
    4. For the functional requirements table, use this format:
       ID | Requirement Description | Priority | Dependencies
       FR01 | [Description] | High/Medium/Low | [Dependencies]
    5. Make sure all section headers are clearly marked with their numbers
    6. Use specific details, numbers, and metrics throughout the document
    7. Be comprehensive but concise in each section

    For the PROJECT TITLE at the top, create a clear, concise title based on the user's requirements.
    """

class PDFGenerator:
    def __init__(self):
        self.buffer = io.BytesIO()
        self.doc = SimpleDocTemplate(
            self.buffer, 
            pagesize=A4, 
            rightMargin=72, 
            leftMargin=72, 
            topMargin=72, 
            bottomMargin=72
        )
        self.styles = getSampleStyleSheet()
        self.story = []
        self.setup_styles()
        
    def setup_styles(self):
        """Define all the styles needed for the document"""
        self.title_style = ParagraphStyle(
            'TitleStyle',
            parent=self.styles['Heading1'],
            fontSize=18,
            alignment=TA_LEFT,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        
        self.subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=self.styles['Heading2'],
            fontSize=16,
            alignment=TA_LEFT,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        
        self.heading_style = ParagraphStyle(
            'HeadingStyle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=18,
            spaceAfter=6,
            textColor=colors.black,
            fontName='Helvetica-Bold'
        )
        
        self.subheading_style = ParagraphStyle(
            'SubheadingStyle',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        
        self.normal_style = ParagraphStyle(
            'NormalStyle',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=6,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        )
        
        self.bullet_style = ParagraphStyle(
            'BulletStyle',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=0,
            spaceAfter=3,
            leftIndent=20,
            bulletIndent=10
        )
        
        self.toc_style = ParagraphStyle(
            'TOCStyle',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceBefore=3,
            spaceAfter=3,
            fontName='Helvetica'
        )
        
    def create_cover_page(self, project_name):
        """Create the cover page with title and date"""
        self.story.append(Paragraph("Product Requirements Document:", self.title_style))
        self.story.append(Paragraph(project_name, self.subtitle_style))
        self.story.append(Spacer(1, 0.2 * inch))
        
        date_str = datetime.now().strftime("%B %d, %Y")
        self.story.append(Paragraph(f"Generated on: {date_str}", self.normal_style))
        self.story.append(Spacer(1, inch))
        
    def create_table_of_contents(self):
        """Create the table of contents"""
        self.story.append(Paragraph("Table of Contents", self.subtitle_style))
        self.story.append(Spacer(1, 0.2 * inch))
        
        toc_entries = [
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
            "Cost Estimation",
            "Open Issues & Future Considerations",
            "Appendix",
            "Points Requiring Further Clarification"
        ]
        
        for i, entry in enumerate(toc_entries, 1):
            self.story.append(Paragraph(f"{i}. {entry}", self.toc_style))
        
    def extract_project_name(self, content):
        """Extract the project name from the content"""
        match = re.search(r"Product Requirements Document:?\s*([^\n]+)", content)
        if match:
            return match.group(1).strip()
        else:
            return "Project Requirements Document"
    
    def parse_and_add_content(self, content):
        """Parse the content and add it to the story with proper formatting"""
        # First extract main sections using regex
        sections = self.extract_sections(content)
        
        for section_num, section_content in sections.items():
            # Add main section header
            section_title = self.get_section_title(section_num, section_content)
            self.story.append(Paragraph(f"{section_num}. {section_title}", self.heading_style))
            
            # Extract and add subsections
            subsections = self.extract_subsections(section_content)
            
            # If there are no subsections, add the content directly
            if not subsections:
                # Clean the content (remove the title)
                clean_content = self.clean_section_content(section_content)
                if clean_content:
                    self.add_content_with_formatting(clean_content)
            else:
                # Add each subsection
                for subsection_num, subsection_content in subsections.items():
                    subsection_title = self.get_subsection_title(subsection_num, subsection_content)
                    self.story.append(Paragraph(f"{section_num}.{subsection_num} {subsection_title}", 
                                              self.subheading_style))
                    
                    # Clean the subsection content
                    clean_content = self.clean_subsection_content(subsection_content)
                    if clean_content:
                        self.add_content_with_formatting(clean_content)
            
            # Add spacer after each main section
            self.story.append(Spacer(1, 0.3 * inch))
                
    def extract_sections(self, content):
        """Extract main sections from content using regex"""
        sections = {}
        # Look for patterns like "1. Introduction", "2. Goals and Objectives", etc.
        section_patterns = [
            (r'1\.\s+Introduction(.*?)(?=2\.\s+Goals|$)', '1'),
            (r'2\.\s+Goals and Objectives(.*?)(?=3\.\s+User|$)', '2'),
            (r'3\.\s+User Personas and Roles(.*?)(?=4\.\s+Functional|$)', '3'),
            (r'4\.\s+Functional Requirements(.*?)(?=5\.\s+Non-Functional|$)', '4'),
            (r'5\.\s+Non-Functional Requirements(.*?)(?=6\.\s+User Interface|$)', '5'),
            (r'6\.\s+User Interface.*?Considerations(.*?)(?=7\.\s+Data|$)', '6'),
            (r'7\.\s+Data Requirements(.*?)(?=8\.\s+System|$)', '7'),
            (r'8\.\s+System Architecture(.*?)(?=9\.\s+Release|$)', '8'),
            (r'9\.\s+Release Criteria(.*?)(?=10\.\s+Timeline|$)', '9'),
            (r'10\.\s+Timeline(.*?)(?=11\.\s+Team|$)', '10'),
            (r'11\.\s+Team Structure(.*?)(?=12\.\s+User Stories|$)', '11'),
            (r'12\.\s+User Stories(.*?)(?=13\.\s+Cost|$)', '12'),
            (r'13\.\s+Cost Estimation(.*?)(?=14\.\s+Open|$)', '13'),
            (r'14\.\s+Open Issues(.*?)(?=15\.\s+Appendix|$)', '14'),
            (r'15\.\s+Appendix(.*?)(?=16\.\s+Points|$)', '15'),
            (r'16\.\s+Points Requiring(.*?)$', '16'),
        ]
        
        for pattern, section_num in section_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                sections[section_num] = match.group(0)
            else:
                # If section not found, create a placeholder
                sections[section_num] = f"{section_num}. {self.get_default_section_title(section_num)}"
                
        return sections
    
    def get_default_section_title(self, section_num):
        """Get default section title if not found"""
        titles = {
            '1': 'Introduction',
            '2': 'Goals and Objectives',
            '3': 'User Personas and Roles',
            '4': 'Functional Requirements',
            '5': 'Non-Functional Requirements',
            '6': 'User Interface (UI) / User Experience (UX) Considerations',
            '7': 'Data Requirements',
            '8': 'System Architecture & Technical Considerations',
            '9': 'Release Criteria & Success Metrics',
            '10': 'Timeline & Milestones',
            '11': 'Team Structure',
            '12': 'User Stories',
            '13': 'Cost Estimation',
            '14': 'Open Issues & Future Considerations',
            '15': 'Appendix',
            '16': 'Points Requiring Further Clarification'
        }
        return titles.get(section_num, f"Section {section_num}")
            
    def extract_subsections(self, section_content):
        """Extract subsections from a section content"""
        subsections = {}
        
        # Look for patterns like "1.1 Purpose", "1.2 Scope", etc.
        subsection_pattern = r'(\d+)\.(\d+)\s+(.*?)(?=\d+\.\d+|\Z)'
        matches = re.finditer(subsection_pattern, section_content, re.DOTALL)
        
        for match in matches:
            section_num = match.group(1)
            subsection_num = match.group(2)
            subsection_content = match.group(0)
            subsections[subsection_num] = subsection_content
            
        return subsections
    
    def get_section_title(self, section_num, content):
        """Extract the title of a section"""
        pattern = r'\d+\.\s+(.*?)(?=\n|\Z)'
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()
        else:
            return self.get_default_section_title(section_num)
    
    def get_subsection_title(self, subsection_num, content):
        """Extract the title of a subsection"""
        pattern = r'\d+\.\d+\s+(.*?)(?=\n|\Z)'
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()
        else:
            return f"Subsection {subsection_num}"
    
    def clean_section_content(self, content):
        """Remove the section title from content"""
        pattern = r'\d+\.\s+.*?\n(.*)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        else:
            # If we can't find the pattern, just return everything after the first line
            lines = content.split('\n', 1)
            if len(lines) > 1:
                return lines[1].strip()
            return ""
    
    def clean_subsection_content(self, content):
        """Remove the subsection title from content"""
        pattern = r'\d+\.\d+\s+.*?\n(.*)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        else:
            # If we can't find the pattern, just return everything after the first line
            lines = content.split('\n', 1)
            if len(lines) > 1:
                return lines[1].strip()
            return ""
    
    def add_content_with_formatting(self, content):
    # Check if this is a functional requirements table (Section 4)
        if "FR01" in content or "ID | Requirement" in content:
            self.add_functional_requirements_table(content)
            return
            
        # Process bullet points
        if content.strip().startswith("-") or "\n-" in content:
            items = []
            current_text = None
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('-'):
                    # It's a new bullet point
                    if current_text is not None:
                        # Add the previous bullet point before starting a new one
                        items.append(ListItem(Paragraph(current_text, self.bullet_style)))
                    current_text = line[1:].strip()  # Start new bullet point
                elif current_text is not None:  # Continuation of a bullet point
                    # Append to the current bullet point text
                    current_text += " " + line
                else:  # Regular text before any bullet points
                    self.story.append(Paragraph(line, self.normal_style))
                    
            # Add the last bullet point if it exists
            if current_text is not None:
                items.append(ListItem(Paragraph(current_text, self.bullet_style)))
                
            if items:
                self.story.append(ListFlowable(items, bulletType='bullet', start=None))
        else:
            # Regular paragraph
            paragraphs = content.split('\n\n')
            for p in paragraphs:
                if p.strip():
                    self.story.append(Paragraph(p.strip(), self.normal_style))
    
    def add_functional_requirements_table(self, content):
        """Parse and add a table for functional requirements"""
        # Simple table extraction - in a real implementation, you'd want more robust parsing
        rows = []
        header_row = ['ID', 'Requirement Description', 'Priority', 'Dependencies']
        rows.append(header_row)
        
        # Extract table rows
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("FR") and "|" in line:
                # It's a table row
                cells = [cell.strip() for cell in line.split('|')]
                if len(cells) >= 4:
                    rows.append(cells[:4])  # Take the first 4 cells
            elif line.startswith("ID") and "|" in line:
                # Skip the header row as we've already added it
                continue
        
        # If we found no data rows, add a placeholder
        if len(rows) == 1:
            rows.append(['FR01', 'Placeholder requirement', 'High', '-'])
        
        # Create the table
        table = Table(rows, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        self.story.append(table)
    
    def generate(self, content):
        """Generate the PDF"""
        # Extract project name
        project_name = self.extract_project_name(content)
        
        # Create cover page
        self.create_cover_page(project_name)
        
        # Create table of contents
        self.create_table_of_contents()
        
        # Add page break after TOC
        self.story.append(PageBreak())
        
        # Parse and add content
        self.parse_and_add_content(content)
        
        # Build the PDF
        self.doc.build(self.story)
        
        # Reset buffer position to the beginning
        self.buffer.seek(0)
        return self.buffer

def generate_pdf(content):
    """Generate a PDF from the given content"""
    generator = PDFGenerator()
    return generator.generate(content)

@app.post("/project_requirements/")
async def project_requirements(request: RequirementsData):
    session_id = request.session_id
    user_input = request.requirements
    
    # Load previous messages from conversation memory
    if session_id not in conversation_state:
        conversation_state[session_id] = [
            {"role": "system", "content": system_prompt()}
        ]
    
    conversation = conversation_state[session_id]
    conversation.append({"role": "user", "content": user_input})
    
    # Call Groq API with more tokens to ensure complete response
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=conversation,
        temperature=0.7,
        max_tokens=8192,  # Increased for comprehensive PRD
    )
    
    reply = response.choices[0].message.content.strip()
    
    # Store assistant message for memory
    conversation.append({"role": "assistant", "content": reply})
    
    # Generate PDF
    pdf_buffer = generate_pdf(reply)
    
    # Get project name for filename
    project_name = "project_requirements"
    match = re.search(r"Product Requirements Document:?\s*([^\n]+)", reply)
    if match:
        project_name = match.group(1).strip().lower().replace(" ", "_")
    
    # Return PDF as a downloadable file
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={project_name}_prd_{datetime.now().strftime('%Y%m%d')}.pdf"}
    )

@app.get("/")
async def root():
    return {"message": "Product Requirements Document (PRD) Generator API"}

if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)