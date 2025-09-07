"""
Multi-Agent Research System for Apple Notes Research Bot

This system provides specialized research agents for different domains:
- SecurityResearchAgent: Security, compliance, risk analysis
- TechnicalResearchAgent: Infrastructure, open source tools, GitHub
- BusinessResearchAgent: Financial analysis, 10K reports, executive communications
- PartnershipResearchAgent: Sales, partnership opportunities, collaboration

Key features:
- Question extraction and classification from user notes
- Context-aware prompting for each domain
- Synthesis of results across multiple agents
- Sales/partnership talking points generation
"""

import json
import logging
import asyncio
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import anthropic
from openai import OpenAI
from .config import Config

logger = logging.getLogger(__name__)

@dataclass
class ExtractedQuestion:
    """A question extracted from user's note"""
    text: str
    domain: str
    priority: int  # 1-5, 5 being highest
    context: str  # Additional context for the question
    requires_synthesis: bool = True  # Whether this needs multi-agent synthesis

@dataclass
class AgentResearchResult:
    """Result from a specific research agent"""
    agent_name: str
    domain: str
    questions_addressed: List[str]
    findings: str
    key_insights: List[str]
    actionable_recommendations: List[str]
    talking_points: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    sources_referenced: List[str] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None
    tokens_used: int = 0

@dataclass
class MultiAgentResearchResult:
    """Complete research result from multi-agent system"""
    original_note: str
    extracted_questions: List[ExtractedQuestion]
    agent_results: Dict[str, AgentResearchResult]
    synthesized_response: str
    executive_summary: str
    next_actions: List[str]
    meeting_talking_points: List[str]
    total_tokens_used: int = 0
    success: bool = True

class QuestionExtractor:
    """Extracts and classifies questions from user notes"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        
        # Domain classification patterns
        self.domain_patterns = {
            'security': [
                'security', 'compliance', 'risk', 'vulnerability', 'audit', 'governance',
                'privacy', 'data protection', 'cybersecurity', 'threat', 'incident',
                'regulations', 'standards', 'certification', 'encryption', 'authentication'
            ],
            'technical': [
                'github', 'open source', 'infrastructure', 'api', 'integration', 'platform',
                'architecture', 'deployment', 'devops', 'cloud', 'microservices',
                'dashboards', 'parsers', 'alerts', 'searches', 'forge', 'repository'
            ],
            'business': [
                '10k', '10-k', 'financial', 'revenue', 'earnings', 'quarterly', 'annual',
                'ceo letter', 'investor', 'shareholder', 'market', 'competition', 'strategy',
                'growth', 'profitability', 'valuation', 'performance', 'outlook'
            ],
            'partnership': [
                'partnership', 'collaboration', 'alliance', 'joint venture', 'customer',
                'client', 'vendor', 'supplier', 'integration', 'relationship', 'meeting',
                'sales', 'opportunity', 'proposal', 'negotiation', 'contract'
            ]
        }
    
    async def extract_questions(self, note_content: str) -> List[ExtractedQuestion]:
        """Extract and classify questions from note content"""
        
        extraction_prompt = f"""
        Analyze this note and extract specific research questions that need investigation:

        NOTE CONTENT:
        "{note_content}"

        Extract questions across these domains:
        1. SECURITY: Security posture, compliance, risk management, governance
        2. TECHNICAL: Infrastructure, GitHub/open source tools, technical capabilities
        3. BUSINESS: Financial analysis, market position, executive communications
        4. PARTNERSHIP: Sales opportunities, collaboration potential, relationship building

        For each question found, determine:
        - The specific research question
        - Which domain it belongs to
        - Priority level (1-5, 5 being critical for the user's goals)
        - Additional context that would help research
        - Whether it needs synthesis with other domains

        Return JSON array with this structure:
        [
            {{
                "text": "What is their current security compliance status?",
                "domain": "security",
                "priority": 4,
                "context": "Meeting with security leaders about partnership",
                "requires_synthesis": true
            }}
        ]

        Focus on actionable research questions that would help the user succeed in their stated goals.
        Extract 3-8 specific questions maximum.
        """
        
        try:
            response = self.client.messages.create(
                model=self.config.claude_analysis_model,
                max_tokens=1000,
                temperature=0.3,
                messages=[{"role": "user", "content": extraction_prompt}]
            )
            
            response_text = response.content[0].text
            
            # Extract JSON from response
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                questions_data = json.loads(json_str)
                
                return [
                    ExtractedQuestion(
                        text=q.get('text', ''),
                        domain=q.get('domain', 'general'),
                        priority=q.get('priority', 3),
                        context=q.get('context', ''),
                        requires_synthesis=q.get('requires_synthesis', True)
                    )
                    for q in questions_data
                    if q.get('text')  # Only include questions with text
                ]
            else:
                logger.error("Could not find JSON array in response")
                return self._fallback_extraction(note_content)
                
        except Exception as e:
            logger.error(f"Question extraction failed: {e}")
            return self._fallback_extraction(note_content)
    
    def _fallback_extraction(self, note_content: str) -> List[ExtractedQuestion]:
        """Fallback question extraction using pattern matching"""
        questions = []
        
        # Simple pattern matching for common question structures
        question_patterns = [
            r'what (is|are|do|does|can).*?\?',
            r'how (do|does|can|should).*?\?',
            r'which.*?\?',
            r'where.*?\?',
            r'when.*?\?',
            r'why.*?\?'
        ]
        
        for pattern in question_patterns:
            matches = re.findall(pattern, note_content.lower(), re.IGNORECASE)
            for match in matches[:3]:  # Limit to 3 per pattern
                domain = self._classify_domain(match)
                questions.append(ExtractedQuestion(
                    text=match,
                    domain=domain,
                    priority=3,
                    context="Extracted from note content",
                    requires_synthesis=True
                ))
        
        # If no questions found, create generic research task
        if not questions:
            domain = self._classify_domain(note_content)
            questions.append(ExtractedQuestion(
                text=f"Research information about the topics mentioned in the note",
                domain=domain,
                priority=3,
                context="General research needed",
                requires_synthesis=False
            ))
        
        return questions
    
    def _classify_domain(self, text: str) -> str:
        """Classify text into research domain"""
        text_lower = text.lower()
        domain_scores = {}
        
        for domain, keywords in self.domain_patterns.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        return 'business'  # Default to business for corporate research

class BaseResearchAgent(ABC):
    """Base class for specialized research agents"""
    
    def __init__(self, config: Config):
        self.config = config
        self.anthropic_client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.openai_client = OpenAI(api_key=config.openai_api_key)
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def domain(self) -> str:
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        pass
    
    @abstractmethod
    def get_research_prompt_template(self) -> str:
        pass
    
    async def research(self, questions: List[ExtractedQuestion], 
                      company_context: str) -> AgentResearchResult:
        """Conduct research for assigned questions"""
        
        # Filter questions for this agent's domain
        relevant_questions = [q for q in questions if q.domain == self.domain]
        
        if not relevant_questions:
            return AgentResearchResult(
                agent_name=self.agent_name,
                domain=self.domain,
                questions_addressed=[],
                findings="No relevant questions for this domain",
                key_insights=[],
                actionable_recommendations=[],
                success=False,
                error="No questions assigned to this agent"
            )
        
        question_texts = [q.text for q in relevant_questions]
        research_prompt = self.get_research_prompt_template().format(
            questions='\n'.join(f"- {q}" for q in question_texts),
            company_context=company_context
        )
        
        try:
            response = self.anthropic_client.messages.create(
                model=self.config.claude_research_model,
                max_tokens=self.config.max_research_tokens,
                temperature=0.7,
                system=self.get_system_prompt(),
                messages=[{"role": "user", "content": research_prompt}]
            )
            
            content = response.content[0].text
            
            # Parse the structured response
            result = self._parse_research_response(content, question_texts)
            result.agent_name = self.agent_name
            result.domain = self.domain
            
            # Estimate tokens
            result.tokens_used = len(research_prompt.split()) + len(content.split())
            
            return result
            
        except Exception as e:
            logger.error(f"{self.agent_name} research failed: {e}")
            return AgentResearchResult(
                agent_name=self.agent_name,
                domain=self.domain,
                questions_addressed=question_texts,
                findings="Research failed due to API error",
                key_insights=[],
                actionable_recommendations=[],
                success=False,
                error=str(e)
            )
    
    def _parse_research_response(self, content: str, questions: List[str]) -> AgentResearchResult:
        """Parse structured research response"""
        
        # Try to extract structured sections
        sections = {
            'findings': self._extract_section(content, 'FINDINGS', 'KEY INSIGHTS'),
            'insights': self._extract_section(content, 'KEY INSIGHTS', 'RECOMMENDATIONS'),
            'recommendations': self._extract_section(content, 'RECOMMENDATIONS', 'TALKING POINTS'),
            'talking_points': self._extract_section(content, 'TALKING POINTS', None)
        }
        
        # Convert sections to lists where appropriate
        insights = self._text_to_list(sections.get('insights', ''))
        recommendations = self._text_to_list(sections.get('recommendations', ''))
        talking_points = self._text_to_list(sections.get('talking_points', ''))
        
        return AgentResearchResult(
            agent_name="",  # Will be set by caller
            domain="",      # Will be set by caller
            questions_addressed=questions,
            findings=sections.get('findings', content[:1000]),  # Fallback to first 1000 chars
            key_insights=insights,
            actionable_recommendations=recommendations,
            talking_points=talking_points,
            confidence_score=0.8,  # Default confidence
            success=True
        )
    
    def _extract_section(self, content: str, start_marker: str, 
                        end_marker: Optional[str]) -> str:
        """Extract section content between markers"""
        start_idx = content.find(start_marker)
        if start_idx == -1:
            return ""
        
        start_idx += len(start_marker)
        
        if end_marker:
            end_idx = content.find(end_marker, start_idx)
            if end_idx != -1:
                return content[start_idx:end_idx].strip()
        
        return content[start_idx:].strip()
    
    def _text_to_list(self, text: str) -> List[str]:
        """Convert bullet-point text to list"""
        if not text:
            return []
        
        lines = text.split('\n')
        items = []
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('•') or line.startswith('-') or 
                        line.startswith('*') or line[0].isdigit()):
                # Remove bullet points and numbers
                clean_line = re.sub(r'^[•\-\*0-9\.)\s]+', '', line).strip()
                if clean_line:
                    items.append(clean_line)
        
        return items[:10]  # Limit to 10 items

class SecurityResearchAgent(BaseResearchAgent):
    """Specialized agent for security, compliance, and risk research"""
    
    @property
    def agent_name(self) -> str:
        return "SecurityResearchAgent"
    
    @property
    def domain(self) -> str:
        return "security"
    
    def get_system_prompt(self) -> str:
        return """You are a cybersecurity and compliance expert with deep knowledge of:
- Enterprise security frameworks (NIST, ISO 27001, SOC 2)
- Regulatory compliance (GDPR, SOX, HIPAA, PCI-DSS)
- Risk management and threat assessment
- Security governance and policies
- Incident response and business continuity
- Data protection and privacy regulations

Focus on practical, actionable security insights that support business partnerships and sales discussions."""
    
    def get_research_prompt_template(self) -> str:
        return """Research these security-related questions about the company:

QUESTIONS:
{questions}

COMPANY CONTEXT:
{company_context}

Provide a comprehensive security analysis structured as follows:

FINDINGS:
[Detailed findings about their security posture, compliance status, recent incidents, certifications, etc.]

KEY INSIGHTS:
• [Security strength/weakness #1]
• [Compliance status insight]
• [Risk factor assessment]
• [Security leadership insights]

RECOMMENDATIONS:
• [Actionable recommendation for partnership discussions]
• [Security considerations for collaboration]
• [Risk mitigation strategies]

TALKING POINTS:
• [Key security talking points for meetings]
• [Questions to ask their security team]
• [Partnership security benefits to highlight]

Focus on information that would be valuable for partnership discussions with their security leaders."""

class TechnicalResearchAgent(BaseResearchAgent):
    """Specialized agent for technical infrastructure and open source research"""
    
    @property
    def agent_name(self) -> str:
        return "TechnicalResearchAgent"
    
    @property
    def domain(self) -> str:
        return "technical"
    
    def get_system_prompt(self) -> str:
        return """You are a senior technical architect and open source expert with expertise in:
- Cloud infrastructure and platforms (AWS, Azure, GCP)
- DevOps and CI/CD pipelines
- Open source governance and strategy
- GitHub enterprise and repository management
- API architectures and microservices
- Observability and monitoring platforms
- Developer tools and productivity platforms

Focus on technical capabilities that enable successful partnerships and asset sharing."""
    
    def get_research_prompt_template(self) -> str:
        return """Research these technical questions about the company:

QUESTIONS:
{questions}

COMPANY CONTEXT:
{company_context}

Provide a comprehensive technical analysis structured as follows:

FINDINGS:
[Detailed findings about their tech stack, infrastructure, open source usage, GitHub presence, developer tools, etc.]

KEY INSIGHTS:
• [Technical architecture insights]
• [Open source adoption and contribution patterns]
• [Developer tooling and platform usage]
• [Integration capabilities and APIs]

RECOMMENDATIONS:
• [Technical integration opportunities]
• [Open source collaboration strategies]
• [Platform compatibility considerations]
• [Asset sharing technical requirements]

TALKING POINTS:
• [Technical benefits of partnership]
• [Specific GitHub/open source discussion points]
• [Integration and platform compatibility topics]
• [Developer productivity enhancement opportunities]

Focus on technical information that supports discussions about GitHub forge, dashboards, parsers, alerts, and other technical assets."""

class BusinessResearchAgent(BaseResearchAgent):
    """Specialized agent for business, financial, and strategic research"""
    
    @property
    def agent_name(self) -> str:
        return "BusinessResearchAgent"
    
    @property
    def domain(self) -> str:
        return "business"
    
    def get_system_prompt(self) -> str:
        return """You are a business analyst and financial expert with expertise in:
- Financial statement analysis (10-K, 10-Q reports)
- Executive communications and strategy
- Market positioning and competitive analysis
- Business model evaluation
- Growth strategies and initiatives
- Mergers, acquisitions, and partnerships
- Investor relations and shareholder communications

Focus on business insights that inform partnership strategy and value proposition development."""
    
    def get_research_prompt_template(self) -> str:
        return """Research these business questions about the company:

QUESTIONS:
{questions}

COMPANY CONTEXT:
{company_context}

Provide a comprehensive business analysis structured as follows:

FINDINGS:
[Detailed findings from 10-K reports, CEO letters, earnings calls, strategic initiatives, financial performance, etc.]

KEY INSIGHTS:
• [Financial performance and trends]
• [Strategic priorities and initiatives]
• [Market position and competitive advantages]
• [Leadership vision and direction]

RECOMMENDATIONS:
• [Partnership alignment opportunities]
• [Value proposition development strategies]
• [Business case development approaches]
• [Executive engagement strategies]

TALKING POINTS:
• [Business value discussion points]
• [Strategic alignment opportunities]
• [Financial and operational benefits]
• [Executive-level conversation starters]

Focus on business intelligence that supports high-level partnership discussions and demonstrates strategic value."""

class PartnershipResearchAgent(BaseResearchAgent):
    """Specialized agent for partnership, sales, and collaboration research"""
    
    @property
    def agent_name(self) -> str:
        return "PartnershipResearchAgent"
    
    @property
    def domain(self) -> str:
        return "partnership"
    
    def get_system_prompt(self) -> str:
        return """You are a partnership development and sales expert with expertise in:
- Strategic partnership development
- Enterprise sales and relationship building
- Collaboration models and frameworks
- Value proposition development
- Competitive analysis and positioning
- Customer success and adoption strategies
- Ecosystem development and platform partnerships

Focus on partnership opportunities, relationship building strategies, and collaborative value creation."""
    
    def get_research_prompt_template(self) -> str:
        return """Research these partnership-related questions about the company:

QUESTIONS:
{questions}

COMPANY CONTEXT:
{company_context}

Provide a comprehensive partnership analysis structured as follows:

FINDINGS:
[Detailed findings about their partnership history, collaboration preferences, vendor relationships, customer base, etc.]

KEY INSIGHTS:
• [Partnership strategy and preferences]
• [Decision-making processes and stakeholders]
• [Existing ecosystem and vendor relationships]
• [Customer needs and pain points]

RECOMMENDATIONS:
• [Partnership approach and positioning]
• [Relationship building strategies]
• [Value proposition customization]
• [Pilot project opportunities]

TALKING POINTS:
• [Partnership benefits and value drivers]
• [Competitive differentiation points]
• [Success stories and case studies to reference]
• [Next steps and follow-up actions]

Focus on information that enables successful partnership development and long-term collaboration."""

class MultiAgentResearchSystem:
    """Orchestrates research across multiple specialized agents"""
    
    def __init__(self, config: Config):
        self.config = config
        self.question_extractor = QuestionExtractor(config)
        
        # Initialize specialized agents
        self.agents = {
            'security': SecurityResearchAgent(config),
            'technical': TechnicalResearchAgent(config),
            'business': BusinessResearchAgent(config),
            'partnership': PartnershipResearchAgent(config)
        }
        
        self.synthesizer = anthropic.Anthropic(api_key=config.anthropic_api_key)
    
    async def research(self, note_content: str) -> MultiAgentResearchResult:
        """Conduct multi-agent research on note content"""
        
        # Step 1: Extract questions and classify by domain
        logger.info("Extracting questions from note...")
        questions = await self.question_extractor.extract_questions(note_content)
        
        if not questions:
            return MultiAgentResearchResult(
                original_note=note_content,
                extracted_questions=[],
                agent_results={},
                synthesized_response="No research questions could be extracted from the note.",
                executive_summary="Unable to identify research requirements.",
                next_actions=[],
                meeting_talking_points=[],
                success=False
            )
        
        logger.info(f"Extracted {len(questions)} questions across domains: {set(q.domain for q in questions)}")
        
        # Step 2: Run research agents in parallel
        logger.info("Running specialized research agents...")
        research_tasks = []
        active_domains = set(q.domain for q in questions)
        
        for domain in active_domains:
            if domain in self.agents:
                task = self.agents[domain].research(questions, note_content)
                research_tasks.append((domain, task))
        
        # Execute research tasks
        agent_results = {}
        total_tokens = 0
        
        for domain, task in research_tasks:
            try:
                result = await task
                agent_results[domain] = result
                total_tokens += result.tokens_used
                
                if result.success:
                    logger.info(f"✅ {result.agent_name} completed successfully")
                else:
                    logger.warning(f"⚠️ {result.agent_name} failed: {result.error}")
            except Exception as e:
                logger.error(f"Agent {domain} failed: {e}")
                agent_results[domain] = AgentResearchResult(
                    agent_name=f"{domain.title()}ResearchAgent",
                    domain=domain,
                    questions_addressed=[q.text for q in questions if q.domain == domain],
                    findings="Research failed",
                    key_insights=[],
                    actionable_recommendations=[],
                    success=False,
                    error=str(e)
                )
        
        # Step 3: Synthesize results
        logger.info("Synthesizing multi-agent research results...")
        synthesis_result = await self._synthesize_results(
            note_content, questions, agent_results
        )
        
        return MultiAgentResearchResult(
            original_note=note_content,
            extracted_questions=questions,
            agent_results=agent_results,
            synthesized_response=synthesis_result['response'],
            executive_summary=synthesis_result['executive_summary'],
            next_actions=synthesis_result['next_actions'],
            meeting_talking_points=synthesis_result['talking_points'],
            total_tokens_used=total_tokens + synthesis_result.get('synthesis_tokens', 0),
            success=len([r for r in agent_results.values() if r.success]) > 0
        )
    
    async def _synthesize_results(self, note_content: str, 
                                 questions: List[ExtractedQuestion],
                                 agent_results: Dict[str, AgentResearchResult]) -> Dict[str, Any]:
        """Synthesize results from multiple agents into a coherent response"""
        
        # Filter successful results
        successful_results = {k: v for k, v in agent_results.items() if v.success}
        
        if not successful_results:
            return {
                'response': "Research could not be completed due to agent failures.",
                'executive_summary': "Unable to complete research.",
                'next_actions': ["Retry research with different approach"],
                'talking_points': [],
                'synthesis_tokens': 0
            }
        
        # Prepare synthesis prompt
        agent_findings = []
        for domain, result in successful_results.items():
            agent_findings.append(f"""
{result.agent_name.upper()} FINDINGS:
Questions Addressed: {', '.join(result.questions_addressed)}

Findings:
{result.findings}

Key Insights:
{chr(10).join('• ' + insight for insight in result.key_insights)}

Recommendations:
{chr(10).join('• ' + rec for rec in result.actionable_recommendations)}

Talking Points:
{chr(10).join('• ' + point for point in result.talking_points)}
""")
        
        synthesis_prompt = f"""
        Synthesize these multi-agent research results into a comprehensive response for the user.

        ORIGINAL USER NOTE:
        {note_content}

        EXTRACTED RESEARCH QUESTIONS:
        {chr(10).join('• ' + q.text + f' (Priority: {q.priority}, Domain: {q.domain})' for q in questions)}

        RESEARCH FINDINGS FROM SPECIALIZED AGENTS:
        {''.join(agent_findings)}

        Create a comprehensive synthesis with these sections:

        EXECUTIVE SUMMARY:
        [2-3 paragraph summary of key findings and implications]

        DETAILED FINDINGS:
        [Synthesized findings organized by topic, not by agent]

        KEY INSIGHTS:
        • [Cross-domain insight #1]
        • [Cross-domain insight #2]
        • [Strategic insight #3]

        ACTIONABLE RECOMMENDATIONS:
        • [Immediate action #1]
        • [Strategic action #2]
        • [Partnership development action #3]

        MEETING TALKING POINTS:
        • [Key discussion point for security leaders]
        • [Technical collaboration opportunity]
        • [Business value proposition]
        • [Partnership development angle]

        NEXT STEPS:
        • [Specific next action #1]
        • [Follow-up research needed #2]
        • [Meeting preparation task #3]

        Focus on creating actionable intelligence that directly supports the user's goals as stated in their note.
        """
        
        try:
            response = self.synthesizer.messages.create(
                model=self.config.claude_analysis_model,
                max_tokens=2000,
                temperature=0.5,
                messages=[{"role": "user", "content": synthesis_prompt}]
            )
            
            synthesis_content = response.content[0].text
            synthesis_tokens = len(synthesis_prompt.split()) + len(synthesis_content.split())
            
            # Parse the synthesis response
            parsed = self._parse_synthesis_response(synthesis_content)
            parsed['synthesis_tokens'] = synthesis_tokens
            
            return parsed
            
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            # Fallback to concatenated results
            return self._fallback_synthesis(successful_results)
    
    def _parse_synthesis_response(self, content: str) -> Dict[str, Any]:
        """Parse structured synthesis response"""
        
        sections = {
            'executive_summary': self._extract_section_content(content, 'EXECUTIVE SUMMARY', 'DETAILED FINDINGS'),
            'response': content,  # Full response
            'next_actions': self._extract_list_content(content, 'NEXT STEPS'),
            'talking_points': self._extract_list_content(content, 'MEETING TALKING POINTS')
        }
        
        # Clean up executive summary
        if not sections['executive_summary']:
            sections['executive_summary'] = content[:500] + "..." if len(content) > 500 else content
        
        return sections
    
    def _extract_section_content(self, content: str, start_marker: str, 
                                end_marker: Optional[str]) -> str:
        """Extract content between section markers"""
        start_idx = content.find(start_marker)
        if start_idx == -1:
            return ""
        
        start_idx += len(start_marker)
        
        if end_marker:
            end_idx = content.find(end_marker, start_idx)
            if end_idx != -1:
                return content[start_idx:end_idx].strip()
        
        return content[start_idx:].strip()
    
    def _extract_list_content(self, content: str, section_marker: str) -> List[str]:
        """Extract list items from a section"""
        section_content = self._extract_section_content(content, section_marker, None)
        if not section_content:
            return []
        
        lines = section_content.split('\n')
        items = []
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('•') or line.startswith('-') or 
                        line.startswith('*') or line[0].isdigit()):
                clean_line = re.sub(r'^[•\-\*0-9\.)\s]+', '', line).strip()
                if clean_line:
                    items.append(clean_line)
        
        return items[:10]  # Limit to reasonable number
    
    def _fallback_synthesis(self, results: Dict[str, AgentResearchResult]) -> Dict[str, Any]:
        """Fallback synthesis when AI synthesis fails"""
        
        # Concatenate key findings
        all_findings = []
        all_insights = []
        all_recommendations = []
        all_talking_points = []
        
        for result in results.values():
            if result.findings:
                all_findings.append(f"{result.agent_name}: {result.findings[:200]}...")
            all_insights.extend(result.key_insights[:3])
            all_recommendations.extend(result.actionable_recommendations[:3])
            all_talking_points.extend(result.talking_points[:3])
        
        response = f"""
RESEARCH SUMMARY:
{' '.join(all_findings)}

KEY INSIGHTS:
{chr(10).join('• ' + insight for insight in all_insights)}

RECOMMENDATIONS:
{chr(10).join('• ' + rec for rec in all_recommendations)}

TALKING POINTS:
{chr(10).join('• ' + point for point in all_talking_points)}
"""
        
        return {
            'response': response,
            'executive_summary': "Multi-agent research completed with findings from " + 
                               ", ".join(r.agent_name for r in results.values()),
            'next_actions': ["Review detailed findings", "Prepare for discussions"],
            'talking_points': all_talking_points[:8],
            'synthesis_tokens': 0
        }