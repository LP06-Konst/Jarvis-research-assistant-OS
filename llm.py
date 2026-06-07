"""
LLM Integration Module for Jarvis Research OS
Uses Google AI Studio (Gemini) for AI responses
"""

import os
import json
from typing import Dict, Any, Optional, List

# Check if API key is available
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

def is_configured() -> bool:
    """Check if LLM is properly configured"""
    return bool(GOOGLE_API_KEY)

def generate_response(prompt: str, context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Generate AI response using Gemini.
    
    Args:
        prompt: The user's prompt/command
        context: Optional context (project state, existing concepts, etc.)
    
    Returns:
        Dict with response text and metadata
    """
    if not is_configured():
        return {
            "text": "AI not configured. Set GOOGLE_API_KEY environment variable.",
            "error": "missing_api_key",
            "fallback": True
        }
    
    try:
        import urllib.request
        import urllib.error
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
        
        # Build context-rich prompt
        system_prompt = """You are Jarvis, a dialectical research assistant. 
For each command, provide:
1. Understanding - what the user wants to do
2. Rationale - why this makes sense theoretically
3. Pressure points - potential tensions or issues
4. Suggestions - alternative approaches or considerations

Be precise, warm, and intellectually rigorous."""

        full_prompt = f"{system_prompt}\n\nUser: {prompt}"
        if context:
            context_str = json.dumps(context, indent=2)
            full_prompt += f"\n\nProject Context:\n{context_str}"
        
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1000
            }
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        
        return {
            "text": text,
            "model": "gemini-1.5-flash",
            "success": True
        }
        
    except urllib.error.HTTPError as e:
        error_body = json.loads(e.read().decode("utf-8")) if e.fp else {}
        return {
            "text": f"API error: {e.code}",
            "error": error_body.get("error", {}).get("message", str(e)),
            "fallback": True
        }
    except Exception as e:
        return {
            "text": f"LLM error: {str(e)}",
            "error": str(e),
            "fallback": True
        }

def parse_command_intent(command: str) -> Dict[str, Any]:
    """
    Use AI to parse user command into structured intent.
    
    Args:
        command: Natural language command from user
    
    Returns:
        Dict with intent type and extracted entities
    """
    if not is_configured():
        return _fallback_parse(command)
    
    try:
        import urllib.request
        
        prompt = f"""Parse this research command into structured intent:
Command: "{command}"

Return JSON with:
- intent: CREATE_CONCEPT | ADD_EDGE | CREATE_PIVOT | ARCHIVE_PIVOT | SEARCH | ANALYSIS | OTHER
- entities: extracted names, topics, parameters
- confidence: 0-1 how certain the parsing is

Return ONLY valid JSON, no markdown."""
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 200}
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
        
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        
        # Parse JSON from response
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        
        return json.loads(text)
        
    except Exception as e:
        return _fallback_parse(command)

def _fallback_parse(command: str) -> Dict[str, Any]:
    """Fallback pattern-based parsing when AI unavailable"""
    command_lower = command.lower()
    
    if "add concept" in command_lower or "new concept" in command_lower:
        return {"intent": "CREATE_CONCEPT", "entities": {"name": command.replace("add concept", "").replace("new concept", "").strip()}}
    elif "add node" in command_lower or "new node" in command_lower:
        return {"intent": "CREATE_NODE", "entities": {"name": command.replace("add node", "").replace("new node", "").strip()}}
    elif "add edge" in command_lower or "connect" in command_lower:
        return {"intent": "ADD_EDGE", "entities": {}}
    elif "create pivot" in command_lower or "new pivot" in command_lower:
        return {"intent": "CREATE_PIVOT", "entities": {"question": command.replace("create pivot", "").replace("new pivot", "").strip()}}
    elif "search" in command_lower or "find" in command_lower:
        return {"intent": "SEARCH", "entities": {"query": command}}
    else:
        return {"intent": "OTHER", "entities": {}}

def generate_rationale(intent: str, entities: Dict, project_context: Optional[Dict] = None) -> str:
    """
    Generate rationale for why a proposed change makes sense.
    """
    if not is_configured():
        return _fallback_rationale(intent, entities)
    
    try:
        import urllib.request
        
        context_str = json.dumps(project_context, indent=2) if project_context else "No prior context"
        
        prompt = f"""Generate a brief rationale for this research action:
Intent: {intent}
Entities: {json.dumps(entities, indent=2)}
Context: {context_str}

Keep rationale to 2-3 sentences. Be dialectical - consider tensions and alternatives."""
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 150}
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
        
        return result["candidates"][0]["content"]["parts"][0]["text"]
        
    except Exception:
        return _fallback_rationale(intent, entities)

def _fallback_rationale(intent: str, entities: Dict) -> str:
    """Fallback rationale when AI unavailable"""
    rationales = {
        "CREATE_CONCEPT": f"Adding '{entities.get('name', 'new concept')}' expands your conceptual landscape.",
        "CREATE_NODE": f"Creating node for '{entities.get('name', 'new node')}' adds to your research graph.",
        "ADD_EDGE": "Connecting concepts creates relationships that structure your thinking.",
        "CREATE_PIVOT": f"New pivot on '{entities.get('question', 'research question')}' opens research direction.",
        "SEARCH": "Search reveals patterns and connections in your sources.",
        "OTHER": "This action shapes your research trajectory."
    }
    return rationales.get(intent, "This action modifies your research state.")