# app/education/erp/__init__.py
"""
ERP AI Education Module

Provides AI-generated educational content about Exposure & Response Prevention (ERP)
therapy for OCD patients.

Components:
- models: Database model for caching generated education
- router: API endpoints for generating and retrieving education
- service: Business logic for education generation
- graph: LangGraph workflow for content generation
- schemas: Pydantic models for request/response validation
"""
