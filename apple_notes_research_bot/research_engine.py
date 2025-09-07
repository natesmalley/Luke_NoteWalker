"""
Multi-provider AI research engine
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import anthropic
from openai import OpenAI
from .config import Config

logger = logging.getLogger(__name__)

@dataclass
class ResearchResult:
    """Result from research operation"""
    provider: str
    content: str
    success: bool
    error: Optional[str] = None
    tokens_used: int = 0

class ResearchEngine:
    """Conducts multi-perspective research using Claude and OpenAI"""
    
    def __init__(self, config: Config):
        self.config = config
        self.anthropic_client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.openai_client = OpenAI(api_key=config.openai_api_key)
        
        # Initialize multi-agent system for enhanced research
        from .multi_agent_system import MultiAgentResearchSystem
        self.multi_agent_system = MultiAgentResearchSystem(config)
        
        # Research prompts by category
        self.category_prompts = {
            'software': """
                Research this software development topic: "{content}"
                
                Provide:
                1. Current best practices and modern approaches
                2. Code examples or implementation patterns
                3. Common pitfalls and how to avoid them
                4. Recommended tools, libraries, or frameworks
                5. Performance and security considerations
                
                Focus on practical, actionable information for 2024-2025.
            """,
            
            'ai': """
                Research this AI/ML topic: "{content}"
                
                Provide:
                1. Current state-of-the-art approaches
                2. Practical implementation considerations
                3. Available models, tools, and frameworks
                4. Cost and performance trade-offs
                5. Ethical considerations and best practices
                
                Include recent developments and future trends.
            """,
            
            'building': """
                Research this building/construction topic: "{content}"
                
                Provide:
                1. Materials needed and cost estimates
                2. Step-by-step process or techniques
                3. Required tools and equipment
                4. Safety considerations and regulations
                5. Common mistakes to avoid
                
                Include practical tips for DIY implementation.
            """,
            
            'lifestyle': """
                Research this lifestyle topic: "{content}"
                
                Provide:
                1. Specific recommendations with details
                2. Cost considerations and value
                3. Timing and availability information
                4. Alternatives and variations
                5. Tips for best experience
                
                Focus on current, local, and practical options.
            """,
            
            'productivity': """
                Research this productivity topic: "{content}"
                
                Provide:
                1. Evidence-based techniques and methods
                2. Tools and apps that can help
                3. Implementation strategies
                4. Common obstacles and solutions
                5. Metrics for measuring improvement
                
                Emphasize actionable, sustainable approaches.
            """,
            
            'general': """
                Research this topic: "{content}"
                
                Provide comprehensive, accurate information including:
                1. Key facts and context
                2. Current best information available
                3. Practical applications or implications
                4. Reliable sources or references
                5. Related topics to explore
                
                Focus on clarity and usefulness.
            """
        }
    
    def _should_use_multi_agent(self, content: str, category: str) -> bool:
        """Determine if content warrants multi-agent research"""
        
        # Check for multi-domain indicators
        multi_domain_keywords = [
            'security leaders', 'meeting with', 'partnership', 'collaboration',
            'provide customers', 'trusted place', '10k', 'ceo letter', 
            'github forge', 'open source initiative', 'dashboards', 'parsers',
            'business analysis', 'financial analysis', 'investor', 'enterprise'
        ]
        
        content_lower = content.lower()
        keyword_matches = sum(1 for keyword in multi_domain_keywords if keyword in content_lower)
        
        # Use multi-agent for complex, multi-domain research
        return (
            keyword_matches >= 3 or  # Multiple domain keywords
            len(content) > 200 or    # Substantial content
            'meeting' in content_lower or  # Meeting preparation
            any(indicator in content_lower for indicator in ['partnership', 'collaboration', 'enterprise'])
        )
    
    async def research(self, content: str, category: str, 
                       research_approach: Optional[str] = None) -> Dict[str, ResearchResult]:
        """Conduct research using appropriate method (single or multi-agent)"""
        
        # Check if content warrants multi-agent research
        if self._should_use_multi_agent(content, category):
            logger.info("Using multi-agent research system for complex query")
            return await self._conduct_multi_agent_research(content)
        
        # Use traditional single-agent research for simpler queries
        logger.info("Using traditional research approach")
        return await self._conduct_traditional_research(content, category, research_approach)
    
    async def _conduct_multi_agent_research(self, content: str) -> Dict[str, ResearchResult]:
        """Conduct research using the multi-agent system"""
        try:
            multi_result = await self.multi_agent_system.research(content)
            
            if not multi_result.success:
                # Fallback to traditional research if multi-agent fails
                logger.warning("Multi-agent research failed, falling back to traditional method")
                return await self._conduct_traditional_research(content, 'general', None)
            
            # Convert multi-agent result to ResearchResult format
            research_results = {}
            
            # Create a comprehensive result from multi-agent synthesis
            research_results['multi_agent'] = ResearchResult(
                provider='multi_agent',
                content=multi_result.synthesized_response,
                success=True,
                tokens_used=multi_result.total_tokens_used
            )
            
            # Add individual agent results as additional perspectives
            for domain, agent_result in multi_result.agent_results.items():
                if agent_result.success:
                    formatted_content = f"""
FINDINGS:
{agent_result.findings}

KEY INSIGHTS:
{chr(10).join('• ' + insight for insight in agent_result.key_insights)}

RECOMMENDATIONS:
{chr(10).join('• ' + rec for rec in agent_result.actionable_recommendations)}

TALKING POINTS:
{chr(10).join('• ' + point for point in agent_result.talking_points)}
"""
                    research_results[f'{domain}_agent'] = ResearchResult(
                        provider=f'{domain}_agent',
                        content=formatted_content,
                        success=True,
                        tokens_used=agent_result.tokens_used
                    )
            
            return research_results
            
        except Exception as e:
            logger.error(f"Multi-agent research failed: {e}")
            # Fallback to traditional research
            return await self._conduct_traditional_research(content, 'general', None)
    
    async def _conduct_traditional_research(self, content: str, category: str, 
                                          research_approach: Optional[str] = None) -> Dict[str, ResearchResult]:
        """Conduct traditional research using existing method"""
        
        # Select appropriate prompt template
        prompt_template = self.category_prompts.get(
            category, 
            self.category_prompts['general']
        )
        
        # Add custom research approach if provided
        if research_approach:
            prompt = prompt_template.format(content=content)
            prompt += f"\n\nResearch Approach: {research_approach}"
        else:
            prompt = prompt_template.format(content=content)
        
        # Run research in parallel if configured
        if self.config.parallel_research:
            results = await asyncio.gather(
                self._research_claude(prompt, category),
                self._research_openai(prompt, category),
                return_exceptions=True
            )
            
            # Process results
            research_results = {}
            for i, provider in enumerate(['claude', 'openai']):
                if isinstance(results[i], Exception):
                    logger.error(f"{provider} research failed: {results[i]}")
                    research_results[provider] = ResearchResult(
                        provider=provider,
                        content="",
                        success=False,
                        error=str(results[i])
                    )
                else:
                    research_results[provider] = results[i]
        else:
            # Sequential research
            research_results = {}
            
            claude_result = await self._research_claude(prompt, category)
            research_results['claude'] = claude_result
            
            # Add delay for rate limiting
            await asyncio.sleep(self.config.rate_limit_delay)
            
            openai_result = await self._research_openai(prompt, category)
            research_results['openai'] = openai_result
        
        return research_results
    
    async def _research_claude(self, prompt: str, category: str) -> ResearchResult:
        """Research using Claude"""
        try:
            # Add category-specific system prompts
            system_prompts = {
                'software': "You are an expert software engineer with deep knowledge of modern development practices.",
                'ai': "You are an AI/ML specialist with expertise in current models and techniques.",
                'building': "You are a construction expert with practical DIY experience.",
                'lifestyle': "You are a lifestyle consultant with local knowledge and creative ideas.",
                'productivity': "You are a productivity expert focused on evidence-based methods.",
                'general': "You are a knowledgeable research assistant providing accurate information."
            }
            
            system_prompt = system_prompts.get(category, system_prompts['general'])
            
            response = self.anthropic_client.messages.create(
                model=self.config.claude_research_model,
                max_tokens=self.config.max_research_tokens,
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            # Estimate tokens (rough approximation)
            tokens_used = len(prompt.split()) + len(content.split())
            
            return ResearchResult(
                provider="claude",
                content=content,
                success=True,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            logger.error(f"Claude research error: {e}")
            return ResearchResult(
                provider="claude",
                content="",
                success=False,
                error=str(e)
            )
    
    async def _research_openai(self, prompt: str, category: str) -> ResearchResult:
        """Research using OpenAI"""
        try:
            # Add category-specific system prompts
            system_prompts = {
                'software': "You are an expert software engineer providing practical development advice.",
                'ai': "You are an AI researcher with expertise in practical ML applications.",
                'building': "You are a construction professional with hands-on experience.",
                'lifestyle': "You are a lifestyle expert with creative and practical suggestions.",
                'productivity': "You are a productivity coach focused on sustainable improvements.",
                'general': "You are a helpful research assistant providing comprehensive information."
            }
            
            system_prompt = system_prompts.get(category, system_prompts['general'])
            
            # Run in executor to make it async
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.openai_client.chat.completions.create(
                    model=self.config.openai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.config.max_research_tokens,
                    temperature=0.7
                )
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            return ResearchResult(
                provider="openai",
                content=content,
                success=True,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            logger.error(f"OpenAI research error: {e}")
            return ResearchResult(
                provider="openai",
                content="",
                success=False,
                error=str(e)
            )
    
    async def synthesize_results(self, results: Dict[str, ResearchResult]) -> str:
        """Synthesize multiple research results into a coherent summary"""
        
        # Filter successful results
        successful_results = {
            provider: result 
            for provider, result in results.items() 
            if result.success and result.content
        }
        
        if not successful_results:
            return "Research could not be completed due to API errors."
        
        if len(successful_results) == 1:
            # Only one provider succeeded
            provider, result = list(successful_results.items())[0]
            return f"Research from {provider.upper()}:\n\n{result.content}"
        
        # Both providers succeeded - create a synthesis
        try:
            claude_content = successful_results.get('claude', ResearchResult('', '', False)).content
            openai_content = successful_results.get('openai', ResearchResult('', '', False)).content
            
            synthesis_prompt = f"""
            Synthesize these two research perspectives into a unified summary:
            
            PERSPECTIVE 1 (Claude):
            {claude_content}
            
            PERSPECTIVE 2 (OpenAI):
            {openai_content}
            
            Create a coherent summary that:
            1. Highlights key points both agree on
            2. Notes any important differences in perspective
            3. Provides the most actionable recommendations
            4. Maintains all specific details (names, numbers, steps)
            
            Format as a clean, organized summary without mentioning the sources.
            """
            
            response = self.anthropic_client.messages.create(
                model=self.config.claude_analysis_model,
                max_tokens=1000,
                temperature=0.3,
                messages=[{"role": "user", "content": synthesis_prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Failed to synthesize results: {e}")
            # Fallback to showing both perspectives
            return self._format_dual_perspective(successful_results)