# app/education/fear_ladder/__init__.py
"""
Fear Ladder AI Education Module

This module provides AI-generated educational content about fear ladders
(exposure hierarchies) in ERP therapy for OCD.

Components:
- models: Database model for caching generated education
- router: API endpoints for generating and retrieving education
- service: Business logic for education generation
- graph: LangGraph workflow for content generation
- schemas: Pydantic models for request/response validation
"""
