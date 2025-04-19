from datetime import datetime
import re
import uuid
from dotenv import load_dotenv
import os
import json
from fastapi.responses import StreamingResponse
import uvicorn
from groq import Groq
from pydantic import BaseModel
from fastapi import FastAPI
from typing import Optional, List
from prompt import system_prompt
from utils import PDFGenerator

load_dotenv()
app = FastAPI()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# In-memory storage (you can later replace with Redis or DB)
conversation_state = {}

class RequirementsData(BaseModel):
    session_id : str
    requirements: str

# def system_prompt():
#     return """
#     You are a smart technical assistant designed to help project managers and clients plan software systems.

#     Behavior:
#     - First, check if you have all the required information. Do not make assumptions.
#     - If information is missing, ask ONLY ONE question to get the next important detail.
#     - If all data is available, suggest multiple technology options for:
#         * Frontend (e.g., React, Vue)
#         * Backend (e.g., FastAPI, Node.js)
#         * Database (e.g., PostgreSQL, MongoDB)
#     - Also suggest:
#         * Panels/modules (Admin Panel, User Panel, Vendor Panel)
#         * User roles and permissions
#         * Estimated team resources: UI/UX, frontend, backend, DB, QA

#     Respond in one of two formats:

#     1. If more data is needed:
#     {
#       "status": "incomplete",
#       "next_question": "What type of project is it? (e.g., web app, mobile app)"
#     }

#     2. If everything is ready:
#     {
#       "status": "complete",
#       "suggested_technologies": {
#         "frontend": [],
#         "backend": [],
#         "database": []
#       },
#       "panels": [],
#       "roles": {},
#       "resource_estimate": {
#         "ui_ux_designers": 0,
#         "frontend_devs": 0,
#         "backend_devs": 0,
#         "db_engineers": 0,
#         "qa_testers": 0
#       },
#       "follow_up": "Would you like me to proceed based on this information, or do you want to modify anything?"
#     }

#     Only return valid JSON.
#     """





def extract_json_block(text: str) -> Optional[dict]:
    try:
        match = re.search(r'\{[\s\S]*?\}', text)
        if match:
            return json.loads(match.group())
    except json.JSONDecodeError:
        pass
    return None


def generate_pdf(content):
    """Generate a PDF from the given content"""
    generator = PDFGenerator()
    return generator.generate(content)


@app.post("/project_requirements/")
async def project_requirements(request: RequirementsData):
    session_id = request.session_id
    user_input = request.requirements

    # Load or initialize conversation
    if session_id not in conversation_state:
        conversation_state[session_id] = [
            {"role": "system", "content": system_prompt()}
        ]
    conversation = conversation_state[session_id]

    # Add user input
    conversation.append({"role": "user", "content": user_input})

    # Call Groq API
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=conversation,
        temperature=0.7,
        max_tokens=2048,
    )

    reply = response.choices[0].message.content.strip()
    print("RAW MODEL RESPONSE:", reply)  # Optional: for debugging

    conversation.append({"role": "assistant", "content": reply})
    
    # Extract JSON
    reply_dict = extract_json_block(reply)
    
    if reply_dict:
        status = reply_dict.get("status", "unknown")    
        if status == "awaiting_more_info":
            return {
                "status": status,
                "next_question": reply_dict.get("next_question", "No follow-up question found."),
                "missing_sections": reply_dict.get("missing_sections", []),
                "session_id": session_id
            }
        elif status == "ready":
            # Generate full PRD with explicit formatting instructions
            prd_prompt = """
Based on our conversation, please generate a complete Product Requirements Document (PRD) with the following sections:

1. Introduction
2. Goals and Objectives
3. User Personas and Roles
4. Functional Requirements
5. Non-Functional Requirements
6. User Interface (UI) / User Experience (UX) Considerations
7. Data Requirements
8. System Architecture & Technical Considerations
9. Release Criteria & Success Metrics
10. Timeline & Milestones
11. Team Structure
12. User Stories
13. Cost Estimation
14. Open Issues & Future Considerations
15. Appendix
16. Points Requiring Further Clarification

For each section:
- Include the numbered header (e.g., "1. Introduction")
- Provide detailed content based on our discussion
- Make sure each section has at least 2-3 paragraphs of relevant content

Format the document with "Product Requirements Document: [Project Name]" at the top.
"""
            
            # Add the PRD generation prompt to the conversation
            conversation.append({"role": "user", "content": prd_prompt})
            
            # Call Groq API again to get the full PRD
            full_prd_response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=conversation,
                temperature=0.7,
                max_tokens=4096,  # Increase token limit for full document
            )
            
            prd_content = full_prd_response.choices[0].message.content.strip()
            print("FULL PRD CONTENT:", prd_content[:200])  # Print first 200 chars for debugging
            
            # Generate PDF from the full PRD content
            pdf_buffer = generate_pdf(prd_content)
            
            # Extract name
            project_name = "project_requirements"
            match = re.search(r"Product Requirements Document:?\s*([^\n]+)", prd_content)
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
        else:
            return {
                "raw_reply": reply,
                "session_id": session_id
            }
    else:   
        # This is the original flow - for backward compatibility
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