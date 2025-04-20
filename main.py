from datetime import datetime
import re, uuid, json, os
from dotenv import load_dotenv
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from groq import Groq
from prompt import system_prompt
from utils_v2 import PDFGenerator

# Load env variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# FastAPI app
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LLM client
client = Groq(api_key=GROQ_API_KEY)

# In-memory state
conversation_state = {}

class RequirementsData(BaseModel):
    session_id: str
    project_name: str
    requirements: str

def extract_json_block(text: str) -> Optional[dict]:
    """Extract JSON block from text."""
    try:
        match = re.search(r'\{[\s\S]*?\}', text)
        if match:
            return json.loads(match.group())
    except json.JSONDecodeError:
        return None

def get_prd_prompt(project_name: str) -> str:
    return f"""
You are a senior Product Manager at Codehub LLP. Generate a COMPLETE Product Requirements Document (PRD) for **{project_name}**...

(keep the rest of your prompt here unchanged)
    """

@app.post("/generate_prd/")
async def project_requirements(request: RequirementsData):
    session_id = request.session_id
    project_name = request.project_name
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
            pdf_buffer = PDFGenerator().generate(prd_content,project_name=request.project_name)
            
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
        pdf_buffer = PDFGenerator().generate(reply)

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