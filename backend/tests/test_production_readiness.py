"""
Production Readiness Test Suite
Validates all critical fixes and production requirements
"""
import os
import pytest
import json
from pathlib import Path


class TestDependencies:
    """Test that all required dependencies are installed."""
    
    def test_build123d_available(self):
        """Critical: build123d CAD kernel must be available."""
        try:
            import build123d
            assert build123d is not None
        except ImportError:
            pytest.fail("build123d not installed - CRITICAL dependency")
    
    def test_langchain_available(self):
        """Critical: LangChain for agent pipeline."""
        try:
            import langchain
            from langgraph.graph import StateGraph
            assert langchain is not None
            assert StateGraph is not None
        except ImportError:
            pytest.fail("langchain/langgraph not installed - CRITICAL")
    
    def test_fastapi_available(self):
        """Critical: FastAPI for backend API."""
        try:
            import fastapi
            assert fastapi is not None
        except ImportError:
            pytest.fail("fastapi not installed - CRITICAL")
    
    def test_trimesh_available(self):
        """Required: Trimesh for geometry validation."""
        try:
            import trimesh
            assert trimesh is not None
        except ImportError:
            pytest.fail("trimesh not installed")


class TestConfiguration:
    """Test configuration and environment settings."""
    
    def test_config_loads(self):
        """Config must load without errors."""
        from config import get_settings
        settings = get_settings()
        assert settings is not None
    
    def test_cors_origins_configurable(self):
        """CORS origins must be configurable."""
        from config import get_settings
        settings = get_settings()
        assert hasattr(settings, 'cors_origins')
        assert hasattr(settings, 'get_cors_origins')
        origins = settings.get_cors_origins()
        assert isinstance(origins, list)
    
    def test_dev_mode_controls_cors(self):
        """Dev mode should affect CORS behavior."""
        from config import get_settings
        settings = get_settings()
        
        # In dev mode, should allow wildcard
        if settings.dev_mode:
            assert settings.get_cors_origins() == ["*"]


class TestCadExecutor:
    """Test CAD code executor security and functionality."""
    
    def test_ast_validation_function_exists(self):
        """AST validation must be implemented."""
        from cad.executor import validate_code_ast
        assert callable(validate_code_ast)
    
    def test_ast_validation_detects_forbidden_imports(self):
        """Must block dangerous imports."""
        from cad.executor import validate_code_ast
        
        # Test forbidden import
        bad_code = "import os\nimport subprocess"
        result = validate_code_ast(bad_code)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    def test_ast_validation_allows_safe_code(self):
        """Must allow safe CAD code."""
        from cad.executor import validate_code_ast
        
        safe_code = """
from build123d import *
box = Box(10, 10, 10)
result = box
"""
        result = validate_code_ast(safe_code)
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_executor_wrapper_has_restricted_open(self):
        """Executor wrapper must restrict file operations."""
        from cad.executor import EXECUTOR_WRAPPER
        assert "safe_open" in EXECUTOR_WRAPPER
        assert "PermissionError" in EXECUTOR_WRAPPER


class TestDatabaseMigrations:
    """Test Alembic migrations are properly configured."""
    
    def test_alembic_ini_exists(self):
        """Alembic config must exist."""
        alembic_ini = Path(__file__).parent.parent / "alembic.ini"
        assert alembic_ini.exists(), "alembic.ini missing"
    
    def test_alembic_env_exists(self):
        """Alembic environment must exist."""
        env_py = Path(__file__).parent.parent / "alembic" / "env.py"
        assert env_py.exists(), "alembic/env.py missing"
    
    def test_initial_migration_exists(self):
        """Initial migration must exist."""
        versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
        migrations = list(versions_dir.glob("*.py"))
        py_migrations = [m for m in migrations if m.name != "__pycache__"]
        assert len(py_migrations) > 0, "No migration files found"


class TestApiEndpoints:
    """Test API endpoint configuration."""
    
    def test_health_endpoint_exists(self):
        """Health check endpoint must exist."""
        from main import app
        routes = [route.path for route in app.routes]
        assert "/api/health" in routes
    
    def test_cors_middleware_configured(self):
        """CORS middleware must be properly configured."""
        from main import app
        middleware_types = [type(m).__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_types


class TestDockerConfiguration:
    """Test Docker build configuration."""
    
    def test_frontend_dockerfile_exists(self):
        """Frontend Dockerfile must exist for production builds."""
        dockerfile = Path(__file__).parent.parent.parent / "frontend" / "Dockerfile"
        assert dockerfile.exists(), "Frontend Dockerfile missing"
    
    def test_backend_dockerignore_exists(self):
        """Backend .dockerignore must exist for build optimization."""
        dockerignore = Path(__file__).parent.parent / ".dockerignore"
        assert dockerignore.exists(), "Backend .dockerignore missing"
    
    def test_frontend_dockerignore_exists(self):
        """Frontend .dockerignore must exist for build optimization."""
        dockerignore = Path(__file__).parent.parent.parent / "frontend" / ".dockerignore"
        assert dockerignore.exists(), "Frontend .dockerignore missing"


class TestDocumentation:
    """Test production documentation exists."""
    
    def test_production_md_exists(self):
        """PRODUCTION.md deployment guide must exist."""
        prod_md = Path(__file__).parent.parent.parent / "PRODUCTION.md"
        assert prod_md.exists(), "PRODUCTION.md missing"
    
    def test_fixes_md_exists(self):
        """FIXES.md summary must exist."""
        fixes_md = Path(__file__).parent.parent.parent / "FIXES.md"
        assert fixes_md.exists(), "FIXES.md missing"
    
    def test_env_example_has_cors_origins(self):
        """ENV example must document CORS_ORIGINS."""
        env_example = Path(__file__).parent.parent.parent / ".env.example"
        content = env_example.read_text()
        assert "CORS_ORIGINS" in content


class TestAgentPipeline:
    """Test agent graph and state configuration."""
    
    def test_agent_graph_exists(self):
        """CAD agent graph must be importable."""
        from agents.graph import cad_graph
        assert cad_graph is not None
    
    def test_agent_state_typed(self):
        """Agent state must be properly typed."""
        from agents.state import AgentState
        assert AgentState is not None
        # Check key fields exist
        annotations = AgentState.__annotations__
        assert "design_id" in annotations
        assert "user_prompt" in annotations
        assert "cad_code" in annotations


@pytest.mark.integration
class TestProductionIntegration:
    """Integration tests for production deployment."""
    
    def test_can_import_all_critical_modules(self):
        """All critical modules must import without errors."""
        modules = [
            "main",
            "config",
            "db.models",
            "db.base",
            "agents.graph",
            "agents.state",
            "cad.executor",
            "api.routes.design",
        ]
        
        for module in modules:
            try:
                __import__(module)
            except ImportError as e:
                pytest.fail(f"Failed to import {module}: {e}")
    
    def test_database_models_have_cascade_deletes(self):
        """Database models must have proper cascade deletes."""
        from db.models import Design, AgentLog, ExportArtifact
        
        # Check Design has cascade relationships
        design_relationships = Design.__mapper__.relationships
        assert "agent_logs" in design_relationships
        assert "export_artifacts" in design_relationships


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
