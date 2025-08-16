"""
End-to-end workflow tests for database migration and seeding scripts.

Tests cover:
- Complete migration + seeding workflows
- Multi-step operations with state verification
- Cross-script interactions and dependencies
- Real-world usage scenarios
- Performance and reliability under load
"""

import pytest
import subprocess
import asyncio
import os
import time
import json
from pathlib import Path
from unittest.mock import patch
import asyncpg
from typing import Dict, List, Any


@pytest.mark.integration
@pytest.mark.e2e
class TestEndToEndWorkflows:
    """End-to-end workflow tests."""

    @pytest.fixture
    def db_env(self):
        """Database environment configuration."""
        return {
            "DATABASE_URL": "postgresql://postgres:N9fgWyjhxkNUeYrPm6C8kZVjEpLw@51.79.231.184:32749/devpocket_warp_dev"
        }

    @pytest.fixture
    async def db_connection(self, db_env):
        """Create a direct database connection for verification."""
        conn = await asyncpg.connect(db_env["DATABASE_URL"])
        yield conn
        await conn.close()

    def run_script_with_timeout(
        self,
        script_runner,
        script_name: str,
        args: List[str],
        env: Dict[str, str],
        timeout: int = 60,
    ) -> subprocess.CompletedProcess:
        """Run script with timeout and environment."""
        with patch.dict(os.environ, env):
            return script_runner.run_script(script_name, args, timeout=timeout)

    async def get_table_counts(self, db_connection) -> Dict[str, int]:
        """Get row counts for all tables."""
        tables = [
            "users",
            "ssh_profiles",
            "ssh_keys",
            "sessions",
            "commands",
            "sync_data",
        ]
        counts = {}

        for table in tables:
            try:
                count = await db_connection.fetchval(f"SELECT COUNT(*) FROM {table}")
                counts[table] = count
            except Exception:
                counts[table] = 0

        return counts

    @pytest.mark.slow
    async def test_full_development_setup(self, script_runner, db_connection, db_env):
        """Test complete development environment setup workflow."""
        # Step 1: Check database connectivity
        result = self.run_script_with_timeout(
            script_runner, "../scripts/db_utils.py", ["test"], db_env
        )
        assert result.returncode == 0, "Database connection should work"

        # Step 2: Check migration status
        result = self.run_script_with_timeout(
            script_runner, "db_migrate.sh", ["--check-only"], db_env
        )
        assert result.returncode == 0, "Migration check should pass"

        # Step 3: Run migration dry-run
        result = self.run_script_with_timeout(
            script_runner, "db_migrate.sh", ["--dry-run"], db_env
        )
        assert result.returncode == 0, "Migration dry-run should work"

        # Step 4: Clean existing development data
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["--clean-force", "all", "0"], db_env
        )
        assert result.returncode == 0, "Data cleaning should work"

        # Step 5: Seed development dataset
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["all", "10"], db_env
        )
        assert result.returncode == 0, "Development data seeding should work"

        # Step 6: Verify data integrity
        counts = await self.get_table_counts(db_connection)

        # Should have users and related data
        assert (
            counts["users"] >= 10
        ), f"Expected at least 10 users, got {counts['users']}"
        assert (
            counts["ssh_profiles"] >= 5
        ), f"Expected SSH profiles, got {counts['ssh_profiles']}"
        assert counts["sessions"] >= 5, f"Expected sessions, got {counts['sessions']}"

        # Step 7: Generate database statistics
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["--stats-only"], db_env
        )
        assert result.returncode == 0, "Statistics generation should work"

        output = result.stdout + result.stderr
        assert (
            "Database Table Statistics" in output
            or "table statistics" in output.lower()
        )

    @pytest.mark.slow
    async def test_production_deployment_simulation(
        self, script_runner, db_connection, db_env
    ):
        """Test production deployment workflow simulation."""
        # Step 1: Pre-deployment health check
        result = self.run_script_with_timeout(
            script_runner, "../scripts/db_utils.py", ["health"], db_env
        )
        assert result.returncode == 0, "Health check should pass"

        # Step 2: Migration safety check
        result = self.run_script_with_timeout(
            script_runner, "db_migrate.sh", ["--dry-run", "head"], db_env
        )
        assert result.returncode == 0, "Migration dry-run should work"

        # Step 3: Backup verification (simulate)
        result = self.run_script_with_timeout(
            script_runner, "db_migrate.sh", ["--check-only"], db_env
        )
        assert result.returncode == 0, "Backup check should work"

        # Step 4: Conservative data initialization
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["--upsert", "users", "5"], db_env
        )
        assert result.returncode == 0, "Conservative seeding should work"

        # Step 5: Post-deployment verification
        counts = await self.get_table_counts(db_connection)
        assert counts["users"] >= 5, "Should have minimum required users"

        # Step 6: System health check
        result = self.run_script_with_timeout(
            script_runner, "../scripts/db_utils.py", ["health"], db_env
        )
        assert result.returncode == 0, "Post-deployment health check should pass"

    @pytest.mark.slow
    async def test_data_migration_workflow(self, script_runner, db_connection, db_env):
        """Test data migration and transformation workflow."""
        # Step 1: Baseline - ensure we have some data
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["users", "5"], db_env
        )
        assert result.returncode == 0

        # Step 2: Take snapshot of current state
        initial_counts = await self.get_table_counts(db_connection)

        # Step 3: Migrate commands data (clean old, seed new)
        result = self.run_script_with_timeout(
            script_runner,
            "db_seed.sh",
            ["--clean-force", "commands", "0"],
            db_env,
        )
        assert result.returncode == 0, "Commands cleaning should work"

        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["commands", "20"], db_env
        )
        assert result.returncode == 0, "Commands seeding should work"

        # Step 4: Migrate SSH data with upsert to handle conflicts
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["--upsert", "ssh", "15"], db_env
        )
        assert result.returncode == 0, "SSH data migration should work"

        # Step 5: Verify migration results
        final_counts = await self.get_table_counts(db_connection)

        # Users should remain the same or increase
        assert final_counts["users"] >= initial_counts["users"]

        # Should have new commands and SSH data
        assert final_counts["commands"] >= 20
        assert final_counts["ssh_profiles"] >= 10

        # Step 6: Integrity check
        # Verify foreign key relationships
        orphaned_commands = await db_connection.fetchval(
            """
            SELECT COUNT(*) FROM commands c
            LEFT JOIN sessions s ON c.session_id = s.id
            WHERE s.id IS NULL
        """
        )
        assert orphaned_commands == 0, "Should have no orphaned commands"

        orphaned_ssh = await db_connection.fetchval(
            """
            SELECT COUNT(*) FROM ssh_profiles sp
            LEFT JOIN users u ON sp.user_id = u.id
            WHERE u.id IS NULL
        """
        )
        assert orphaned_ssh == 0, "Should have no orphaned SSH profiles"

    @pytest.mark.slow
    async def test_disaster_recovery_simulation(
        self, script_runner, db_connection, db_env
    ):
        """Test disaster recovery workflow simulation."""
        # Step 1: Simulate disaster by cleaning all data
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["--clean-force", "all", "0"], db_env
        )
        assert result.returncode == 0, "Disaster simulation (data cleaning) should work"

        # Step 2: Verify disaster state
        counts = await self.get_table_counts(db_connection)
        assert all(
            count == 0 for count in counts.values()
        ), "All tables should be empty after disaster"

        # Step 3: Recovery - rebuild essential data
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["users", "10"], db_env
        )
        assert result.returncode == 0, "User recovery should work"

        # Step 4: Recovery - rebuild dependent data
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["ssh", "8"], db_env
        )
        assert result.returncode == 0, "SSH data recovery should work"

        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["sessions", "12"], db_env
        )
        assert result.returncode == 0, "Session data recovery should work"

        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["commands", "25"], db_env
        )
        assert result.returncode == 0, "Command data recovery should work"

        # Step 5: Verify recovery
        recovery_counts = await self.get_table_counts(db_connection)

        assert recovery_counts["users"] >= 10, "Should have recovered user data"
        assert recovery_counts["ssh_profiles"] >= 5, "Should have recovered SSH data"
        assert recovery_counts["sessions"] >= 10, "Should have recovered session data"
        assert recovery_counts["commands"] >= 20, "Should have recovered command data"

        # Step 6: Health verification
        result = self.run_script_with_timeout(
            script_runner, "../scripts/db_utils.py", ["health"], db_env
        )
        assert result.returncode == 0, "Post-recovery health check should pass"

    @pytest.mark.slow
    async def test_performance_stress_workflow(
        self, script_runner, db_connection, db_env
    ):
        """Test performance under stress conditions."""
        # Step 1: Clean start
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["--clean-force", "all", "0"], db_env
        )
        assert result.returncode == 0

        # Step 2: Large dataset seeding
        start_time = time.time()

        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["all", "100"], db_env, timeout=120
        )
        assert result.returncode == 0, "Large dataset seeding should work"

        seeding_time = time.time() - start_time

        # Step 3: Verify performance
        assert seeding_time < 60, f"Seeding took too long: {seeding_time}s"

        # Step 4: Verify data integrity under load
        counts = await self.get_table_counts(db_connection)
        assert counts["users"] >= 100, "Should have seeded users"
        assert counts["ssh_profiles"] >= 50, "Should have seeded SSH profiles"
        assert counts["commands"] >= 80, "Should have seeded commands"

        # Step 5: Statistics performance
        stats_start = time.time()
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["--stats-only"], db_env
        )
        stats_time = time.time() - stats_start

        assert result.returncode == 0, "Statistics should work"
        assert stats_time < 10, f"Statistics took too long: {stats_time}s"

    @pytest.mark.slow
    async def test_complex_scenario_workflow(
        self, script_runner, db_connection, db_env
    ):
        """Test complex real-world scenario workflow."""
        # Scenario: Multi-tenant application with staged data deployment

        # Step 1: Initialize base tenant data
        result = self.run_script_with_timeout(
            script_runner,
            "db_seed.sh",
            ["--clean-force", "users", "20"],
            db_env,
        )
        assert result.returncode == 0

        # Step 2: Add SSH configurations for development team
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["--upsert", "ssh", "15"], db_env
        )
        assert result.returncode == 0

        # Step 3: Simulate user activity with sessions and commands
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["sessions", "30"], db_env
        )
        assert result.returncode == 0

        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["commands", "50"], db_env
        )
        assert result.returncode == 0

        # Step 4: Add synchronization data for mobile apps
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["sync", "25"], db_env
        )
        assert result.returncode == 0

        # Step 5: Verification phase
        counts = await self.get_table_counts(db_connection)

        # Verify minimum expected data
        assert counts["users"] >= 20
        assert counts["ssh_profiles"] >= 10
        assert counts["sessions"] >= 25
        assert counts["commands"] >= 40
        assert counts["sync_data"] >= 20

        # Step 6: Complex integrity checks
        # Check user-session relationships
        user_sessions = await db_connection.fetchval(
            """
            SELECT COUNT(DISTINCT s.user_id) FROM sessions s
            JOIN users u ON s.user_id = u.id
        """
        )
        assert user_sessions >= 10, "Should have user-session relationships"

        # Check session-command relationships
        session_commands = await db_connection.fetchval(
            """
            SELECT COUNT(DISTINCT c.session_id) FROM commands c
            JOIN sessions s ON c.session_id = s.id
        """
        )
        assert session_commands >= 15, "Should have session-command relationships"

        # Check SSH key relationships
        ssh_user_keys = await db_connection.fetchval(
            """
            SELECT COUNT(*) FROM ssh_profiles sp
            JOIN ssh_keys sk ON sp.ssh_key_id = sk.id
            WHERE sp.user_id = sk.user_id
        """
        )
        # Should have some matching relationships (may not be all due to random generation)

        # Step 7: Performance verification under complex data
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["--stats-only"], db_env
        )
        assert result.returncode == 0

        output = result.stdout + result.stderr
        assert (
            "Database Table Statistics" in output
            or "table statistics" in output.lower()
        )

    @pytest.mark.slow
    async def test_incremental_update_workflow(
        self, script_runner, db_connection, db_env
    ):
        """Test incremental data update workflow."""
        # Step 1: Initial dataset
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["--clean-force", "all", "10"], db_env
        )
        assert result.returncode == 0

        initial_counts = await self.get_table_counts(db_connection)

        # Step 2: Incremental user additions
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["--upsert", "users", "5"], db_env
        )
        assert result.returncode == 0

        # Step 3: Incremental SSH additions
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["--upsert", "ssh", "8"], db_env
        )
        assert result.returncode == 0

        # Step 4: New activity data
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["commands", "20"], db_env
        )
        assert result.returncode == 0

        # Step 5: Verify incremental growth
        final_counts = await self.get_table_counts(db_connection)

        # Counts should have increased
        assert final_counts["users"] >= initial_counts["users"]
        assert final_counts["commands"] >= initial_counts["commands"] + 15

        # Step 6: Data consistency check
        result = self.run_script_with_timeout(
            script_runner, "../scripts/db_utils.py", ["health"], db_env
        )
        assert result.returncode == 0

    @pytest.mark.slow
    def test_error_handling_workflow(self, script_runner, db_env):
        """Test error handling across workflow steps."""
        # Step 1: Test with invalid database (should fail gracefully)
        invalid_env = {
            "DATABASE_URL": "postgresql://invalid:invalid@localhost:9999/invalid_db"
        }

        result = self.run_script_with_timeout(
            script_runner,
            "db_seed.sh",
            ["--stats-only"],
            invalid_env,
            timeout=30,
        )
        assert result.returncode != 0, "Should fail with invalid database"

        # Step 2: Test with invalid arguments (should fail gracefully)
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["invalid_type", "10"], db_env
        )
        assert result.returncode != 0, "Should fail with invalid seed type"

        # Step 3: Recovery with valid operations
        result = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["users", "3"], db_env
        )
        assert result.returncode == 0, "Should recover with valid operation"

        # Step 4: Test migration error handling
        result = self.run_script_with_timeout(
            script_runner, "db_migrate.sh", ["--unknown-option"], db_env
        )
        assert result.returncode != 0, "Should fail with unknown option"

        # Step 5: Recovery with valid migration command
        result = self.run_script_with_timeout(
            script_runner, "db_migrate.sh", ["--check-only"], db_env
        )
        assert result.returncode == 0, "Should recover with valid command"

    @pytest.mark.slow
    async def test_concurrent_operation_simulation(
        self, script_runner, db_connection, db_env
    ):
        """Test simulation of concurrent operations."""
        # Note: This is a simplified concurrent test. Real concurrent testing
        # would require more sophisticated threading/async handling

        # Step 1: Prepare base data
        result = self.run_script_with_timeout(
            script_runner,
            "db_seed.sh",
            ["--clean-force", "users", "10"],
            db_env,
        )
        assert result.returncode == 0

        # Step 2: Simulate "concurrent" operations by running them sequentially
        # but checking that each doesn't interfere with the others

        # Operation 1: Add SSH data
        result1 = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["ssh", "5"], db_env
        )

        # Operation 2: Add session data
        result2 = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["sessions", "8"], db_env
        )

        # Operation 3: Add command data
        result3 = self.run_script_with_timeout(
            script_runner, "db_seed.sh", ["commands", "12"], db_env
        )

        # All operations should succeed
        assert result1.returncode == 0, "SSH seeding should work"
        assert result2.returncode == 0, "Session seeding should work"
        assert result3.returncode == 0, "Command seeding should work"

        # Step 3: Verify data integrity after "concurrent" operations
        counts = await self.get_table_counts(db_connection)

        assert counts["users"] >= 10
        assert counts["ssh_profiles"] >= 3
        assert counts["sessions"] >= 5
        assert counts["commands"] >= 8

        # Step 4: Check for data consistency
        result = self.run_script_with_timeout(
            script_runner, "../scripts/db_utils.py", ["health"], db_env
        )
        assert result.returncode == 0, "Database should remain healthy"


@pytest.mark.integration
@pytest.mark.e2e
class TestWorkflowReliability:
    """Test workflow reliability and edge cases."""

    @pytest.fixture
    def db_env(self):
        """Database environment configuration."""
        return {
            "DATABASE_URL": "postgresql://postgres:N9fgWyjhxkNUeYrPm6C8kZVjEpLw@51.79.231.184:32749/devpocket_warp_dev"
        }

    @pytest.mark.slow
    def test_repeated_operations_stability(self, script_runner, db_env):
        """Test that repeated operations remain stable."""
        # Run the same operation multiple times
        for i in range(3):
            result = script_runner.run_script(
                "db_seed.sh", ["--upsert", "users", "5"], env=db_env
            )
            assert result.returncode == 0, f"Iteration {i+1} should succeed"

    @pytest.mark.slow
    def test_script_option_edge_cases(self, script_runner, db_env):
        """Test edge cases in script options."""
        with patch.dict(os.environ, db_env):
            # Test zero count
            result = script_runner.run_script("db_seed.sh", ["users", "0"])
            assert result.returncode == 0, "Zero count should work"

            # Test large count (but reasonable)
            result = script_runner.run_script("db_seed.sh", ["users", "50"])
            assert result.returncode == 0, "Large count should work"

    @pytest.mark.slow
    def test_environment_variable_handling(self, script_runner, temp_dir):
        """Test environment variable handling."""
        # Create custom env file
        env_file = temp_dir / "test.env"
        env_file.write_text(
            "DATABASE_URL=postgresql://postgres:N9fgWyjhxkNUeYrPm6C8kZVjEpLw@51.79.231.184:32749/devpocket_warp_dev\n"
        )

        # Test with custom env file
        result = script_runner.run_script(
            "db_seed.sh", ["--env-file", str(env_file), "--stats-only"]
        )
        assert result.returncode == 0, "Custom env file should work"

    @pytest.mark.slow
    def test_logging_consistency(self, script_runner, db_env):
        """Test that logging remains consistent across operations."""
        with patch.dict(os.environ, db_env):
            operations = [
                (["--stats-only"], "stats"),
                (["users", "2"], "seeding"),
                (["--clean-force", "users", "0"], "cleaning"),
            ]

            for args, operation_type in operations:
                result = script_runner.run_script("db_seed.sh", args)
                assert result.returncode == 0, f"{operation_type} should work"

                output = result.stdout + result.stderr
                # Should have consistent log format
                assert "[INFO]" in output, f"{operation_type} should have INFO logs"
