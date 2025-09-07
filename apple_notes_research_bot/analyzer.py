"""
Content analysis for determining research worthiness
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import anthropic
from .config import Config

logger = logging.getLogger(__name__)

@dataclass 
class AnalysisResult:
    """Result of content analysis"""
    should_research: bool
    confidence: float
    reasoning: str
    category: str
    research_approach: Optional[str] = None
    multi_domain: bool = False
    domains_involved: List[str] = None
    
    def __post_init__(self):
        if self.domains_involved is None:
            self.domains_involved = []

class ContentAnalyzer:
    """Analyzes note content to determine if research is needed"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        
        # Category keywords for quick filtering
        self.category_keywords = {
            'software': ['python', 'javascript', 'api', 'framework', 'code', 'programming', 
                        'database', 'backend', 'frontend', 'deploy', 'github', 'repository'],
            'ai': ['ai', 'ml', 'machine learning', 'llm', 'neural', 'gpt', 'claude',
                  'deep learning', 'nlp', 'computer vision'],
            'building': ['build', 'construction', 'materials', 'diy', 'deck', 'renovation',
                        'repair', 'tools', 'blueprint'],
            'lifestyle': ['date', 'restaurant', 'activity', 'weekend', 'event', 'entertainment',
                         'travel', 'food', 'hobby'],
            'productivity': ['productivity', 'workflow', 'efficiency', 'todo', 'task',
                           'organize', 'schedule', 'time management', 'focus'],
            'security': ['security', 'compliance', 'risk', 'audit', 'governance', 'privacy',
                        'cybersecurity', 'threat', 'vulnerability', 'encryption'],
            'business': ['10k', '10-k', 'financial', 'revenue', 'earnings', 'ceo letter',
                        'investor', 'market', 'strategy', 'partnership', 'enterprise'],
            'technical': ['infrastructure', 'platform', 'architecture', 'devops', 'cloud',
                         'integration', 'microservices', 'dashboards', 'parsers', 'alerts'],
            'partnership': ['partnership', 'collaboration', 'alliance', 'customer', 'client',
                           'vendor', 'supplier', 'relationship', 'meeting', 'sales']
        }
        
        # Multi-domain indicators for enhanced research
        self.multi_domain_indicators = [
            'meeting with', 'security leaders', 'partnership', 'collaboration',
            'github forge', 'open source initiative', 'trusted place',
            'provide customers', 'share and consume', 'dashboards parsers alerts',
            '10k and ceo letters', 'business analysis', 'enterprise'
        ]
    
    async def analyze(self, content: str) -> AnalysisResult:
        """Analyze content to determine if research is needed"""
        
        # Quick check for very short notes
        if len(content.strip()) < 10:
            return AnalysisResult(
                should_research=False,
                confidence=1.0,
                reasoning="Note too short for meaningful research",
                category="none"
            )
        
        # Quick keyword-based category detection
        initial_category = self._detect_category_keywords(content.lower())
        
        # Use AI for deeper analysis
        try:
            analysis_prompt = f"""
            Analyze this note to determine if it needs research:
            "{content}"
            
            Consider these research domains:
            - Security: cybersecurity, compliance, risk management, governance
            - Technical: infrastructure, GitHub/open source tools, APIs, platforms
            - Business: financial analysis, 10-K reports, market research, executive communications
            - Partnership: collaboration opportunities, sales, vendor relationships
            - Software: development, programming, technical implementation
            - AI/ML: data science, emerging technologies, machine learning
            - Building: construction, DIY projects, home improvement
            - Lifestyle: entertainment, activities, personal interests
            - Productivity: time management, organization, workflow optimization
            
            Determine if this note:
            1. Is asking a question or seeking information
            2. Is planning something that needs research (especially meetings or partnerships)
            3. Contains topics that would benefit from external research
            4. Involves multiple domains (security + technical + business + partnership)
            5. Is just a personal note/reminder that doesn't need research
            
            Special attention for:
            - Meeting preparation needs
            - Partnership/collaboration discussions
            - Enterprise/business analysis requirements
            - Multi-domain research needs
            
            Return JSON with this exact structure:
            {{
                "should_research": true/false,
                "confidence": 0.0-1.0,
                "reasoning": "brief explanation",
                "category": "security|technical|business|partnership|software|ai|building|lifestyle|productivity|general|none",
                "research_approach": "how to research this effectively (if should_research is true)",
                "multi_domain": true/false,
                "domains_involved": ["list", "of", "relevant", "domains"]
            }}
            
            Be selective - only recommend research for notes that clearly need external information.
            Personal notes, reminders, completed thoughts don't need research.
            """
            
            response = self.client.messages.create(
                model=self.config.claude_analysis_model,
                max_tokens=self.config.max_analysis_tokens,
                temperature=0.3,
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            # Extract and parse JSON response
            response_text = response.content[0].text
            
            # Clean up response to get JSON
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0]
            elif "{" in response_text and "}" in response_text:
                # Find JSON object in response
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                json_str = response_text[start:end]
            else:
                json_str = response_text
            
            analysis_data = json.loads(json_str.strip())
            
            # Validate and clean the response
            result = AnalysisResult(
                should_research=bool(analysis_data.get('should_research', False)),
                confidence=float(analysis_data.get('confidence', 0.5)),
                reasoning=analysis_data.get('reasoning', 'No reasoning provided'),
                category=analysis_data.get('category', initial_category or 'general'),
                research_approach=analysis_data.get('research_approach'),
                multi_domain=bool(analysis_data.get('multi_domain', False)),
                domains_involved=analysis_data.get('domains_involved', [])
            )
            
            # Apply confidence threshold
            if result.confidence < self.config.research_confidence_threshold:
                result.should_research = False
                result.reasoning += f" (Below confidence threshold of {self.config.research_confidence_threshold})"
            
            logger.debug(f"Analysis result: {result}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            # Fallback to keyword-based decision
            return self._fallback_analysis(content, initial_category)
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return self._fallback_analysis(content, initial_category)
    
    def _detect_category_keywords(self, content_lower: str) -> Optional[str]:
        """Quick category detection based on keywords"""
        category_scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        return None
    
    def _fallback_analysis(self, content: str, category: Optional[str]) -> AnalysisResult:
        """Fallback analysis when AI is unavailable"""
        # Simple heuristics
        question_indicators = ['?', 'how to', 'what is', 'best', 'should i', 'need to']
        research_indicators = ['research', 'find out', 'look up', 'ideas for', 'options for']
        
        content_lower = content.lower()
        
        has_question = any(indicator in content_lower for indicator in question_indicators)
        has_research_need = any(indicator in content_lower for indicator in research_indicators)
        
        should_research = has_question or has_research_need
        confidence = 0.6 if should_research else 0.8
        
        return AnalysisResult(
            should_research=should_research and confidence >= self.config.research_confidence_threshold,
            confidence=confidence,
            reasoning="Fallback heuristic analysis (AI unavailable)",
            category=category or 'general',
            research_approach="General web research" if should_research else None
        )
    
    def is_personal_note(self, content: str) -> bool:
        """Quick check if this is a personal note that shouldn't be researched"""
        personal_indicators = [
            'reminder:', 'todo:', 'note to self:', 'remember to',
            'meeting with', 'call with', 'talked to', 'met with'
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in personal_indicators)