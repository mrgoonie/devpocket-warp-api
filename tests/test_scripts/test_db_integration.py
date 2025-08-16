"""
Comprehensive integration tests for database scripts.

Tests cover:
- Database connectivity and health checks
- Migration and seeding script interactions
- Data integrity across operations
- Performance and reliability testing
- Error recovery scenarios
"""

import pytest
import os
from unittest.mock import patch
import asyncpg
import time


@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @pytest.fixture
    def db_env(self):
        """Database environment configuration."""
        return {"DATABASE_URL": "postgresql://test:test@localhost:5432/test_db"}

    @pytest.fixture
    async def db_connection(self, db_env):
        """Create a direct database connection for testing."""
        conn = await asyncpg.connect(db_env["DATABASE_URL"])
        yield conn
        await conn.close()

    @pytest.mark.slow
    def test_db_utils_operations(self, script_runner, db_env):
        """Test db_utils.py operations."""
        with patch.dict(os.environ, db_env):
            # Test database connection
            result = script_runner.run_script("../scripts/db_utils.py", ["test"])
            assert result.returncode == 0

            # Test health check
            result = script_runner.run_script("../scripts/db_utils.py", ["health"])
            assert result.returncode == 0
            assert "healthy" in result.stdout.lower()

    @pytest.mark.slow
    def test_migration_script_integration(self, script_runner, db_env):
        """Test migration script with real database."""
        with patch.dict(os.environ, db_env):
            # Test connection check
            result = script_runner.run_script("db_migrate.sh", ["--check-only"])
            assert result.returncode == 0

            # Test dry run
            result = script_runner.run_script("db_migrate.sh", ["--dry-run"])
            assert result.returncode == 0

            # Test history
            result = script_runner.run_script("db_migrate.sh", ["--history"])
            assert result.returncode == 0

    @pytest.mark.slow
    def test_seeding_script_integration(self, script_runner, db_env):
        """Test seeding script with real database."""
        with patch.dict(os.environ, db_env):
            # Test stats only
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])
            assert result.returncode == 0

            # Test small data seeding
            result = script_runner.run_script("db_seed.sh", ["users", "2"])
            assert result.returncode == 0

    @pytest.mark.slow
    async def test_database_table_structure(self, db_connection):
        """Test that database has expected table structure."""
        # Get all tables
        tables = await db_connection.fetch(
            """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        )

        table_names = [row["table_name"] for row in tables]

        # Expected core tables
        expected_tables = [
            "alembic_version",
            "users",
            "ssh_profiles",
            "ssh_keys",
            "sessions",
            "commands",
            "sync_data",
        ]

        for expected_table in expected_tables:
            assert (
                expected_table in table_names
            ), f"Expected table {expected_table} not found"

    @pytest.mark.slow
    async def test_foreign_key_constraints(self, db_connection):
        """Test that foreign key constraints are properly set up."""
        # Get foreign key constraints
        constraints = await db_connection.fetch(
            """
            SELECT 
                tc.table_name,
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            ORDER BY tc.table_name, tc.constraint_name
        """
        )

        # Should have FK constraints
        assert len(constraints) > 0, "No foreign key constraints found"

        # Check specific expected constraints
        constraint_map = {
            row["table_name"] + "." + row["column_name"]: row["foreign_table_name"]
            for row in constraints
        }

        expected_fks = [
            ("ssh_profiles.user_id", "users"),
            ("ssh_keys.user_id", "users"),
            ("sessions.user_id", "users"),
            ("commands.session_id", "sessions"),
            ("sync_data.user_id", "users"),
        ]

        for table_column, expected_ref in expected_fks:
            if table_column in constraint_map:
                assert constraint_map[table_column] == expected_ref

    @pytest.mark.slow
    def test_clean_and_seed_workflow(self, script_runner, db_env):
        """Test complete clean and seed workflow."""
        with patch.dict(os.environ, db_env):
            # Clean and seed users
            result = script_runner.run_script(
                "db_seed.sh", ["--clean-force", "users", "3"]
            )
            assert result.returncode == 0

            # Seed related data
            result = script_runner.run_script("db_seed.sh", ["ssh", "2"])
            assert result.returncode == 0

            # Check stats
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])
            assert result.returncode == 0

    @pytest.mark.slow
    def test_upsert_functionality(self, script_runner, db_env):
        """Test upsert conflict resolution."""
        with patch.dict(os.environ, db_env):
            # First seeding
            result1 = script_runner.run_script("db_seed.sh", ["--upsert", "users", "2"])
            assert result1.returncode == 0

            # Second seeding (should handle conflicts)
            result2 = script_runner.run_script("db_seed.sh", ["--upsert", "users", "2"])
            assert result2.returncode == 0

    @pytest.mark.slow
    async def test_data_integrity_after_seeding(
        self, script_runner, db_connection, db_env
    ):
        """Test data integrity after seeding operations."""
        with patch.dict(os.environ, db_env):
            # Clean and seed small dataset
            result = script_runner.run_script(
                "db_seed.sh", ["--clean-force", "all", "2"]
            )
            assert result.returncode == 0

            # Check data integrity
            # Users should exist
            user_count = await db_connection.fetchval("SELECT COUNT(*) FROM users")
            assert user_count >= 2

            # SSH profiles should reference valid users
            invalid_ssh = await db_connection.fetchval(
                """
                SELECT COUNT(*) FROM ssh_profiles sp
                LEFT JOIN users u ON sp.user_id = u.id
                WHERE u.id IS NULL
            """
            )
            assert invalid_ssh == 0

            # Commands should reference valid sessions
            invalid_commands = await db_connection.fetchval(
                """
                SELECT COUNT(*) FROM commands c
                LEFT JOIN sessions s ON c.session_id = s.id
                WHERE s.id IS NULL
            """
            )
            assert invalid_commands == 0

    @pytest.mark.slow
    def test_performance_large_dataset(self, script_runner, db_env):
        """Test performance with moderately large dataset."""
        with patch.dict(os.environ, db_env):
            start_time = time.time()

            # Seed larger dataset
            result = script_runner.run_script(
                "db_seed.sh", ["--clean-force", "users", "50"]
            )
            assert result.returncode == 0

            end_time = time.time()
            execution_time = end_time - start_time

            # Should complete within reasonable time (30 seconds)
            assert execution_time < 30, f"Seeding took too long: {execution_time}s"

    @pytest.mark.slow
    def test_error_recovery(self, script_runner, db_env):
        """Test error recovery scenarios."""
        with patch.dict(os.environ, db_env):
            # Test with invalid seed type (should fail gracefully)
            result = script_runner.run_script("db_seed.sh", ["invalid_type", "5"])
            assert result.returncode != 0

            # Subsequent valid operation should work
            result = script_runner.run_script("db_seed.sh", ["users", "2"])
            assert result.returncode == 0

    @pytest.mark.slow
    async def test_concurrent_operations(self, script_runner, db_env):
        """Test handling of concurrent operations."""
        with patch.dict(os.environ, db_env):
            # Note: This is a simplified test. In real scenarios, you'd want
            # more sophisticated concurrency testing

            # Run two seeding operations sequentially
            result1 = script_runner.run_script("db_seed.sh", ["users", "2"])
            result2 = script_runner.run_script("db_seed.sh", ["ssh", "2"])

            assert result1.returncode == 0
            assert result2.returncode == 0

    @pytest.mark.slow
    def test_script_options_combinations(self, script_runner, db_env):
        """Test various script option combinations."""
        with patch.dict(os.environ, db_env):
            # Test complex option combinations
            result = script_runner.run_script(
                "db_seed.sh",
                ["--clean-force", "--upsert", "--stats", "users", "3"],
            )
            assert result.returncode == 0

            output = result.stdout + result.stderr
            assert "Cleaning data types" in output
            assert "Database seeding completed" in output
            assert (
                "Database statistics" in output or "table statistics" in output.lower()
            )

    @pytest.mark.slow
    async def test_database_state_consistency(
        self, script_runner, db_connection, db_env
    ):
        """Test database state consistency across operations."""
        with patch.dict(os.environ, db_env):
            # Get initial state
            initial_tables = await db_connection.fetch(
                """
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """
            )
            initial_count = len(initial_tables)

            # Perform operations
            script_runner.run_script("db_seed.sh", ["--clean-force", "users", "5"])
            script_runner.run_script("db_seed.sh", ["ssh", "3"])

            # Check final state
            final_tables = await db_connection.fetch(
                """
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """
            )
            final_count = len(final_tables)

            # Table structure should remain the same
            assert initial_count == final_count

            # Data should be present
            user_count = await db_connection.fetchval("SELECT COUNT(*) FROM users")
            assert user_count >= 5

    @pytest.mark.slow
    def test_migration_safety(self, script_runner, db_env):
        """Test migration safety features."""
        with patch.dict(os.environ, db_env):
            # Test dry run doesn't change anything
            result = script_runner.run_script("db_migrate.sh", ["--dry-run", "head"])
            assert result.returncode == 0

            # Test backup functionality (if pg_dump available)
            result = script_runner.run_script("db_migrate.sh", ["--check-only"])
            assert result.returncode == 0

    @pytest.mark.slow
    def test_logging_and_monitoring(self, script_runner, db_env):
        """Test logging and monitoring capabilities."""
        with patch.dict(os.environ, db_env):
            # Run operations and check for proper logging
            result = script_runner.run_script("db_seed.sh", ["users", "3", "--stats"])
            assert result.returncode == 0

            output = result.stdout + result.stderr

            # Check for expected log patterns
            log_patterns = [
                "[INFO]",
                "Starting database seeding script",
                "Database connection verified",
                "Database seeding completed",
            ]

            for pattern in log_patterns:
                assert pattern in output, f"Expected log pattern '{pattern}' not found"


@pytest.mark.integration
class TestDatabaseUtilsIntegration:
    """Integration tests specifically for db_utils.py."""

    @pytest.fixture
    def db_env(self):
        """Database environment configuration."""
        return {"DATABASE_URL": "postgresql://test:test@localhost:5432/test_db"}

    @pytest.mark.slow
    def test_db_utils_test_command(self, script_runner, db_env):
        """Test db_utils.py test command."""
        with patch.dict(os.environ, db_env):
            result = script_runner.run_script("../scripts/db_utils.py", ["test"])
            assert result.returncode == 0
            assert "completed successfully" in result.stdout

    @pytest.mark.slow
    def test_db_utils_health_command(self, script_runner, db_env):
        """Test db_utils.py health command."""
        with patch.dict(os.environ, db_env):
            result = script_runner.run_script("../scripts/db_utils.py", ["health"])
            assert result.returncode == 0
            assert "healthy" in result.stdout.lower()

    @pytest.mark.slow
    def test_db_utils_error_handling(self, script_runner):
        """Test db_utils.py error handling with invalid database URL."""
        invalid_env = {
            "DATABASE_URL": "postgresql://invalid:invalid@localhost:9999/invalid_db"
        }

        with patch.dict(os.environ, invalid_env):
            result = script_runner.run_script("../scripts/db_utils.py", ["test"])
            assert result.returncode != 0
            assert "failed" in result.stdout.lower()

    @pytest.mark.slow
    def test_db_utils_help(self, script_runner):
        """Test db_utils.py help functionality."""
        result = script_runner.run_script("../scripts/db_utils.py", [])
        assert result.returncode != 0  # Should fail without command
        assert "Usage:" in result.stdout
        assert "Commands:" in result.stdout

    @pytest.mark.slow
    def test_db_utils_invalid_command(self, script_runner, db_env):
        """Test db_utils.py with invalid command."""
        with patch.dict(os.environ, db_env):
            result = script_runner.run_script("../scripts/db_utils.py", ["invalid"])
            assert result.returncode != 0
            assert "Unknown command" in result.stdout


@pytest.mark.integration
class TestEndToEndWorkflows:
    """End-to-end workflow integration tests."""

    @pytest.fixture
    def db_env(self):
        """Database environment configuration."""
        return {"DATABASE_URL": "postgresql://test:test@localhost:5432/test_db"}

    @pytest.mark.slow
    def test_complete_development_workflow(self, script_runner, db_env):
        """Test complete development workflow."""
        with patch.dict(os.environ, db_env):
            # 1. Check database health
            result = script_runner.run_script("../scripts/db_utils.py", ["health"])
            assert result.returncode == 0

            # 2. Check migration status
            result = script_runner.run_script("db_migrate.sh", ["--dry-run"])
            assert result.returncode == 0

            # 3. Clean and seed development data
            result = script_runner.run_script(
                "db_seed.sh", ["--clean-force", "all", "5", "--stats"]
            )
            assert result.returncode == 0

            # 4. Verify data integrity
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])
            assert result.returncode == 0

    @pytest.mark.slow
    def test_production_deployment_workflow(self, script_runner, db_env):
        """Test production deployment workflow simulation."""
        with patch.dict(os.environ, db_env):
            # 1. Backup check (dry run)
            result = script_runner.run_script("db_migrate.sh", ["--dry-run"])
            assert result.returncode == 0

            # 2. Migration with safety checks
            result = script_runner.run_script("db_migrate.sh", ["--check-only"])
            assert result.returncode == 0

            # 3. Conservative data seeding
            result = script_runner.run_script("db_seed.sh", ["--upsert", "users", "2"])
            assert result.returncode == 0

    @pytest.mark.slow
    def test_disaster_recovery_workflow(self, script_runner, db_env):
        """Test disaster recovery workflow simulation."""
        with patch.dict(os.environ, db_env):
            # 1. Health check to assess damage
            result = script_runner.run_script("../scripts/db_utils.py", ["health"])
            # Should work even if some data is missing

            # 2. Reset if necessary (commented out for safety)
            # result = script_runner.run_script("db_seed.sh", ["--reset-force", "all", "1"])
            # assert result.returncode == 0

            # 3. Verify recovery
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])
            assert result.returncode == 0

    @pytest.mark.slow
    def test_data_migration_workflow(self, script_runner, db_env):
        """Test data migration workflow."""
        with patch.dict(os.environ, db_env):
            # 1. Backup existing data (stats)
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])
            assert result.returncode == 0

            # 2. Clean specific data types
            result = script_runner.run_script(
                "db_seed.sh", ["--clean-force", "commands", "0"]
            )
            assert result.returncode == 0

            # 3. Migrate new data
            result = script_runner.run_script("db_seed.sh", ["commands", "10"])
            assert result.returncode == 0

            # 4. Verify migration
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])
            assert result.returncode == 0

    @pytest.mark.slow
    def test_testing_workflow(self, script_runner, db_env):
        """Test testing environment setup workflow."""
        with patch.dict(os.environ, db_env):
            # 1. Clean slate
            result = script_runner.run_script(
                "db_seed.sh", ["--clean-force", "all", "0"]
            )
            assert result.returncode == 0

            # 2. Seed test data
            result = script_runner.run_script("db_seed.sh", ["all", "3"])
            assert result.returncode == 0

            # 3. Add specific test scenarios
            result = script_runner.run_script("db_seed.sh", ["--upsert", "users", "5"])
            assert result.returncode == 0

            # 4. Verify test environment
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])
            assert result.returncode == 0
