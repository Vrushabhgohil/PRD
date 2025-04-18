import uuid
from dotenv import load_dotenv
import os
import uvicorn
from groq import Groq
from pydantic import BaseModel
from fastapi import FastAPI
from typing import Optional, List
from prompt import system_prompt
load_dotenv()
app = FastAPI()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# In-memory storage (you can later replace with Redis or DB)
conversation_state = {}

class RequirementsData(BaseModel):
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

@app.post("/project_requirements/")
async def project_requirements(request: RequirementsData):
    session_id = str(uuid.uuid4())
    user_input = request.requirements

    # Load previous messages from conversation memory
    if session_id not in conversation_state:
        conversation_state[session_id] = [
            {"role": "system", "content": system_prompt()}
        ]

    conversation = conversation_state[session_id]
    conversation.append({"role": "user", "content": user_input})

    # Call Groq API
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=conversation,
        temperature=0.7,
        max_tokens=2048,
    )

    reply = response.choices[0].message.content.strip()
    print("client: ",user_input)
    print("Developer: ",reply)
    # Store assistant message for memory
    conversation.append({"role": "assistant", "content": reply})

    return {
        "response": reply,
        "session_id": session_id
    }

if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
