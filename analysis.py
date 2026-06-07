"""
AI Analysis Module for Jarvis Research OS
Handles dialectical reasoning and content analysis
"""

import json
import re
from typing import Dict, Any, List, Optional
from rag import semantic_search, analyze_document_structure, extract_key_concepts


class DialecticalAnalyzer:
    """AI analyzer with dialectical reasoning approach"""
    
    def __init__(self):
        self.analysis_depth_levels = {
            "surface": "Basic observation without deeper interpretation",
            "contextual": "Understanding how this fits broader research",
            "critical": "Questioning assumptions and implications",
            "synthetic": "Connecting across sources and concepts"
        }
    
    def analyze_content(self, query: str, project_id: Optional[str] = None, depth: str = "contextual") -> Dict[str, Any]:
        """Analyze content using RAG + dialectical reasoning"""
        
        # Get relevant context from vector store
        context_results = semantic_search(query, project_id=project_id, top_k=5)
        
        if not context_results:
            return self._generate_synthetic_response(query, [])
        
        # Build context for analysis
        context_text = "\n\n".join([
            f"[Page {r['page']}]: {r['text'][:300]}..." 
            for r in context_results
        ])
        
        # Perform dialectical analysis
        analysis = self._dialectical_analysis(query, context_text, depth)
        
        # Generate dialectical response
        dialectical_response = self._generate_dialectical_response(query, context_results)
        
        return {
            "analysis": analysis,
            "context": context_text,
            "relevant_sources": [r['source_id'] for r in context_results],
            "dialectical_response": dialectical_response
        }
    
    def _dialectical_analysis(self, query: str, context: str, depth: str) -> str:
        """Generate dialectical analysis of content"""
        
        # Extract key themes from context
        themes = extract_key_concepts(context + " " + query)[:5]
        
        if depth == "surface":
            return f"Based on the context: {themes[0] if themes else 'research topic'} appears relevant. Consider exploring this further."
        
        elif depth == "contextual":
            connections = self._find_connections(context)
            return f"This relates to: {', '.join(themes[:3])}. {connections}"
        
        elif depth == "critical":
            assumptions = self._identify_assumptions(context)
            counter_args = self._generate_counterarguments(context)
            return f"Key themes: {', '.join(themes[:3])}. {assumptions}. {counter_args}"
        
        else:  # synthetic
            cross_refs = self._find_cross_references(context)
            return f"Synthesis: {', '.join(themes[:4])}. {cross_refs}"
    
    def _find_connections(self, text: str) -> str:
        """Find connections between concepts in text"""
        concepts = extract_key_concepts(text)[:5]
        if len(concepts) < 2:
            return "Multiple concepts interconnected."
        return f"These connect through shared theoretical foundations."
    
    def _identify_assumptions(self, text: str) -> str:
        """Identify key assumptions in the content"""
        # Simple heuristic - look for claims that could be challenged
        assumptions = []
        
        # Check for common assumption patterns
        if re.search(r'\b(?:shows|proves|demonstrates|indicates|suggests)\b', text, re.I):
            assumptions.append("Implicit causality claims")
        if re.search(r'\b(?:always|never|must|should|necessary)\b', text, re.I):
            assumptions.append("Overgeneralization patterns")
        if re.search(r'\b(?:we|one|this study|researchers)\b', text, re.I):
            assumptions.append("Perspective-specific framing")
        
        if assumptions:
            return f"Potential assumptions: {'; '.join(assumptions[:2])}"
        return "Core assumptions require further examination."
    
    def _generate_counterarguments(self, text: str) -> str:
        """Generate potential counterarguments"""
        return "Consider: What evidence might challenge this? What alternative interpretations exist?"
    
    def _find_cross_references(self, text: str) -> str:
        """Find cross-references between different parts of research"""
        concepts = extract_key_concepts(text)
        if len(concepts) > 3:
            return f"Cross-cutting themes: {concepts[0]} relates to {concepts[2]} through {concepts[1]}"
        return "Multiple thematic connections identified across sources."
    
    def _generate_dialectical_response(self, query: str, sources: List[Dict]) -> Dict[str, Any]:
        """Generate dialectical response with pressure points and suggestions"""
        
        analysis_text = self._dialectical_analysis(query, "\n".join(s[:500] for s in [s['text'] for s in sources]), "critical")
        
        # Generate pressure points
        pressure_points = [
            "What assumption does this embed?",
            "What would be the counter-argument?",
            "How does this fit the overall research arc?",
            "What evidence is missing or unstated?",
            "Whose perspective is being centered?"
        ]
        
        # Generate suggestions based on query type
        query_lower = query.lower()
        
        if 'analyze' in query_lower:
            suggestions = [
                "Consider how this relates to your current pivots",
                "Check for existing concepts that might connect",
                "Think about the theoretical implications"
            ]
        elif 'summarize' in query_lower:
            suggestions = [
                "Identify the core thesis being presented",
                "Note any competing interpretations",
                "Consider the methodology used"
            ]
        elif 'compare' in query_lower:
            suggestions = [
                "Look for structural similarities",
                "Note key differences in approach",
                "Consider what each perspective emphasizes"
            ]
        elif 'extract' in query_lower:
            suggestions = [
                "Focus on actionable insights",
                "Note the context of each finding",
                "Consider implications for your research"
            ]
        else:
            suggestions = [
                "Explore related concepts in your graph",
                "Consider uploading relevant sources for deeper analysis",
                "Think about how this advances your research goals"
            ]
        
        return {
            "analysis": analysis_text,
            "pressure_points": pressure_points[:3],
            "suggestions": suggestions[:3]
        }
    
    def _generate_synthetic_response(self, query: str, sources: List[Dict]) -> Dict[str, Any]:
        """Generate response when no sources found"""
        return {
            "analysis": f"Analyzing: {query}",
            "context": "No sources found. Upload research documents for deeper analysis.",
            "relevant_sources": [],
            "dialectical_response": {
                "analysis": "I need more context. Upload PDFs or connect sources to enable full analysis.",
                "pressure_points": [
                    "What specific aspect would you like to explore?",
                    "Do you have relevant sources to analyze?",
                    "What research question are you pursuing?"
                ],
                "suggestions": [
                    "Upload PDF documents for processing",
                    "Add research links to your library",
                    "Describe the specific analysis you need"
                ]
            }
        }


def generate_node_suggestions(project_id: str, existing_nodes: List[Dict]) -> List[Dict[str, Any]]:
    """Generate node suggestions based on project content and existing graph"""
    
    if not existing_nodes:
        return []
    
    # Analyze existing node content
    existing_concepts = set()
    for node in existing_nodes:
        concepts = extract_key_concepts(node.get('name', '') + ' ' + node.get('description', ''))
        existing_concepts.update(concepts)
    
    # Find related concepts from vector store
    related_suggestions = []
    collection = get_vector_collection() if 'get_vector_collection' in dir(__import__('rag')) else None
    
    if collection:
        try:
            for concept in list(existing_concepts)[:3]:
                results = semantic_search(concept, project_id=project_id, top_k=3)
                for r in results:
                    text_concepts = extract_key_concepts(r['text'])
                    for tc in text_concepts:
                        if tc not in existing_concepts and len(tc) > 4:
                            related_suggestions.append({
                                "name": tc.title(),
                                "status": "concept",
                                "reason": f"Related to {concept}",
                                "source": r['source_id']
                            })
        except:
            pass
    
    # Deduplicate and limit
    seen = set()
    unique_suggestions = []
    for s in related_suggestions:
        if s['name'].lower() not in seen:
            seen.add(s['name'].lower())
            unique_suggestions.append(s)
    
    return unique_suggestions[:5]


def create_node_from_analysis(analysis_result: Dict[str, Any], query: str) -> Dict[str, Any]:
    """Create a new node from analysis results"""
    
    concepts = extract_key_concepts(query)
    main_concept = concepts[0].title() if concepts else query.title()
    
    return {
        "name": main_concept,
        "status": "concept",
        "description": analysis_result.get('analysis', '')[:200],
        "type": "analysis",
        "related_sources": analysis_result.get('relevant_sources', []),
        "key_insights": extract_key_concepts(analysis_result.get('analysis', ''))[:5]
    }


def suggest_edges(nodes: List[Dict], threshold: float = 0.6) -> List[Dict[str, str]]:
    """Suggest edges between nodes based on content similarity"""
    
    edges = []
    
    for i, node1 in enumerate(nodes):
        for node2 in nodes[i+1:]:
            text1 = node1.get('name', '') + ' ' + node1.get('description', '')
            text2 = node2.get('name', '') + ' ' + node2.get('description', '')
            
            if len(text1) < 5 or len(text2) < 5:
                continue
            
            try:
                from rag import compute_similarity
                similarity = compute_similarity(text1, text2)
                
                if similarity >= threshold:
                    edges.append({
                        "source": node1['id'],
                        "target": node2['id'],
                        "weight": similarity,
                        "type": "semantic"
                    })
            except:
                pass
    
    return edges


def analyze_proposal_impact(proposal: Dict[str, Any], current_state: Dict) -> Dict[str, Any]:
    """Analyze the potential impact of a proposal on the research graph"""
    
    changes = proposal.get('changes', [])
    
    impact = {
        "adds_nodes": 0,
        "adds_edges": 0,
        "removes_nodes": 0,
        "removes_edges": 0,
        "affects_sources": [],
        "risks": [],
        "benefits": []
    }
    
    for change in changes:
        change_type = change.get('type', '')
        
        if change_type == 'add_node':
            impact['adds_nodes'] += 1
            impact['benefits'].append(f"New concept: {change.get('name', 'Unknown')}")
        
        elif change_type == 'add_edge':
            impact['adds_edges'] += 1
        
        elif change_type == 'delete_node':
            impact['removes_nodes'] += 1
        
        elif change_type == 'link_source':
            impact['affects_sources'].append(change.get('source_id', ''))
    
    # Check for potential risks
    if impact['adds_nodes'] > 3:
        impact['risks'].append("Many nodes being added - consider spacing out changes")
    
    if impact['removes_nodes'] > 0:
        impact['risks'].append("Deleting nodes will remove their connections")
    
    return impact


# Singleton instance
analyzer = DialecticalAnalyzer()


def get_analyzer():
    """Get the singleton analyzer instance"""
    return analyzer


# Helper to avoid circular import
def get_vector_collection():
    from rag import get_vector_collection as _get_col, check_ml_available
    if not check_ml_available():
        return None
    return _get_col()