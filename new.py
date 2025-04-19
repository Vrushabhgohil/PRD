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
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    ListFlowable,
    ListItem,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.units import inch
from prompt import system_prompt
from utils import PDFGenerator

load_dotenv()
app = FastAPI()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# In-memory storage (you can later replace with Redis or DB)
conversation_state = {}


class RequirementsData(BaseModel):
    session_id: str
    requirements: str


conversation_state = {}

# Progress tracker per session
session_progress = {}

# PRD Sections in order


def generate_pdf(content):
    """Generate a PDF from the given content"""
    generator = PDFGenerator()
    return generator.generate(content)


conversation_state = {}
ready_to_generate = {}

@app.post("/project_requirements/")
async def project_requirements(request: RequirementsData):
    session_id = request.session_id
    user_input = request.requirements.strip()

    # Initialize session if not exists
    if session_id not in conversation_state:
        conversation_state[session_id] = {}

    # Get the current session state
    session_data = conversation_state[session_id]

    # Find the last unanswered section
    for section, question in prd_sections:
        if section not in session_data:
            session_data[section] = user_input
            break

    # Find next missing section
    for section, question in prd_sections:
        if not session_data.get(section):
            return {
                "status": "awaiting_more_info",
                "message": f"**{section}**\n{question}"
            }

    # If all data is filled, build full context
    full_context = "\n\n".join(f"**{section}**\n{response}" for section, response in session_data.items())

    # Include system/company context in the system prompt
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": full_context}
        ],
        temperature=0.7,
        max_tokens=8192,
    )

    reply = response.choices[0].message.content.strip()

    # Generate PDF
    pdf_buffer = generate_pdf(reply)

    # Extract name
    project_name = "project_requirements"
    match = re.search(r"Product Requirements Document:?\s*([^\n]+)", reply)
    if match:
        project_name = match.group(1).strip().lower().replace(" ", "_")

    # Clean up session
    del conversation_state[session_id]

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={project_name}_prd_{datetime.now().strftime('%Y%m%d')}.pdf"
        },
    )


@app.get("/")
async def root():
    return {"message": "Product Requirements Document (PRD) Generator API"}


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
