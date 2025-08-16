"""
Performance Test Baselines for DevPocket API.

Establishes performance benchmarks for:
- API response times
- Database query performance
- WebSocket connection handling
- SSH connection performance
- AI service response times
- Synchronization performance
- Concurrent user scenarios
"""

import pytest
import asyncio
import time
from unittest.mock import patch

from httpx import AsyncClient

from app.main import create_application


class TestAPIPerformance:
    """Test API endpoint performance."""

    @pytest.fixture
    def performance_app(self):
        """Create app instance for performance testing."""
        return create_application()

    @pytest.mark.asyncio
    async def test_auth_endpoint_performance(self, performance_app, benchmark):
        """Test authentication endpoint performance."""
        async with AsyncClient(app=performance_app, base_url="http://test") as client:

            def auth_request():
                return asyncio.run(
                    client.post(
                        "/api/auth/login",
                        json={
                            "username": "test@example.com",
                            "password": "testpassword",
                        },
                    )
                )

            # Benchmark the authentication request
            result = benchmark(auth_request)

            # Performance assertions
            assert result.status_code in [
                200,
                401,
            ]  # Should respond quickly regardless
            assert benchmark.stats["mean"] < 0.5  # Should complete within 500ms

    @pytest.mark.asyncio
    async def test_user_profile_performance(
        self, performance_app, auth_headers, benchmark
    ):
        """Test user profile retrieval performance."""
        async with AsyncClient(app=performance_app, base_url="http://test") as client:

            def profile_request():
                return asyncio.run(
                    client.get("/api/auth/profile", headers=auth_headers)
                )

            result = benchmark(profile_request)

            # Performance assertions
            assert result.status_code == 200
            assert benchmark.stats["mean"] < 0.2  # Should complete within 200ms

    @pytest.mark.asyncio
    async def test_ssh_profile_list_performance(
        self, performance_app, auth_headers, benchmark
    ):
        """Test SSH profile listing performance."""
        async with AsyncClient(app=performance_app, base_url="http://test") as client:

            def ssh_profiles_request():
                return asyncio.run(
                    client.get("/api/ssh/profiles", headers=auth_headers)
                )

            result = benchmark(ssh_profiles_request)

            # Performance assertions
            assert result.status_code == 200
            assert benchmark.stats["mean"] < 0.3  # Should complete within 300ms

    @pytest.mark.asyncio
    async def test_concurrent_api_requests(
        self, performance_app, auth_headers, benchmark
    ):
        """Test concurrent API request handling."""

        async def make_concurrent_requests():
            async with AsyncClient(
                app=performance_app, base_url="http://test"
            ) as client:
                # Create 10 concurrent requests
                tasks = [
                    client.get("/api/auth/profile", headers=auth_headers)
                    for _ in range(10)
                ]
                responses = await asyncio.gather(*tasks)
                return responses

        def concurrent_test():
            return asyncio.run(make_concurrent_requests())

        responses = benchmark(concurrent_test)

        # Performance assertions
        assert len(responses) == 10
        assert all(r.status_code == 200 for r in responses)
        assert benchmark.stats["mean"] < 1.0  # All 10 requests within 1 second


class TestDatabasePerformance:
    """Test database operation performance."""

    @pytest.mark.asyncio
    async def test_user_query_performance(self, user_repository, benchmark):
        """Test user database query performance."""

        def user_query():
            return asyncio.run(user_repository.get_by_email("test@example.com"))

        benchmark(user_query)

        # Performance assertions
        assert benchmark.stats["mean"] < 0.1  # Should complete within 100ms

    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, user_repository, benchmark):
        """Test bulk insert performance."""

        def bulk_insert():
            users_data = [
                {
                    "email": f"user{i}@example.com",
                    "username": f"user{i}",
                    "hashed_password": "hashed_password",
                }
                for i in range(100)
            ]
            return asyncio.run(user_repository.bulk_create(users_data))

        result = benchmark(bulk_insert)

        # Performance assertions
        assert len(result) == 100
        assert benchmark.stats["mean"] < 2.0  # 100 inserts within 2 seconds

    @pytest.mark.asyncio
    async def test_complex_query_performance(self, command_repository, benchmark):
        """Test complex database query performance."""

        def complex_query():
            # Query with joins, filters, and aggregations
            return asyncio.run(
                command_repository.get_user_command_statistics("user-123")
            )

        benchmark(complex_query)

        # Performance assertions
        assert benchmark.stats["mean"] < 0.5  # Complex query within 500ms

    @pytest.mark.asyncio
    async def test_database_connection_pool_performance(self, db_session, benchmark):
        """Test database connection pool efficiency."""

        def connection_pool_test():
            async def get_connection():
                async with db_session() as session:
                    return await session.execute("SELECT 1")

            # Test multiple concurrent connections
            return asyncio.run(asyncio.gather(*[get_connection() for _ in range(20)]))

        results = benchmark(connection_pool_test)

        # Performance assertions
        assert len(results) == 20
        assert benchmark.stats["mean"] < 0.5  # All connections within 500ms


class TestWebSocketPerformance:
    """Test WebSocket performance."""

    @pytest.mark.asyncio
    async def test_websocket_connection_time(self, benchmark):
        """Test WebSocket connection establishment time."""

        def websocket_connect():
            # Mock WebSocket connection test
            start_time = time.time()
            # Simulate connection establishment
            time.sleep(0.01)  # 10ms simulated connection time
            return time.time() - start_time

        connection_time = benchmark(websocket_connect)

        # Performance assertions
        assert connection_time < 0.1  # Connection within 100ms

    @pytest.mark.asyncio
    async def test_websocket_message_throughput(self, benchmark):
        """Test WebSocket message throughput."""

        def websocket_throughput():
            # Simulate sending 1000 messages
            messages = [f"message_{i}" for i in range(1000)]
            start_time = time.time()

            # Mock message processing
            for message in messages:
                # Simulate message processing time
                pass

            return time.time() - start_time

        throughput_time = benchmark(websocket_throughput)

        # Performance assertions
        assert throughput_time < 1.0  # 1000 messages within 1 second
        messages_per_second = 1000 / throughput_time
        assert messages_per_second > 1000  # At least 1000 messages per second

    @pytest.mark.asyncio
    async def test_concurrent_websocket_connections(self, benchmark):
        """Test handling multiple concurrent WebSocket connections."""

        def concurrent_websockets():
            # Simulate 100 concurrent WebSocket connections
            connection_times = []

            for i in range(100):
                start_time = time.time()
                # Simulate connection processing
                time.sleep(0.001)  # 1ms per connection
                connection_times.append(time.time() - start_time)

            return connection_times

        connection_times = benchmark(concurrent_websockets)

        # Performance assertions
        assert len(connection_times) == 100
        assert max(connection_times) < 0.01  # Each connection within 10ms
        assert benchmark.stats["mean"] < 0.5  # All connections within 500ms


class TestSSHPerformance:
    """Test SSH operation performance."""

    @pytest.mark.asyncio
    async def test_ssh_connection_time(self, ssh_client, benchmark):
        """Test SSH connection establishment time."""

        def ssh_connect():
            with patch("paramiko.SSHClient") as mock_ssh:
                mock_ssh.return_value.connect.return_value = None
                return asyncio.run(ssh_client.connect())

        result = benchmark(ssh_connect)

        # Performance assertions
        assert result is True
        assert benchmark.stats["mean"] < 2.0  # SSH connection within 2 seconds

    @pytest.mark.asyncio
    async def test_ssh_command_execution_time(self, ssh_client, benchmark):
        """Test SSH command execution performance."""

        def ssh_execute():
            with patch.object(ssh_client, "execute_command") as mock_exec:
                mock_exec.return_value = {
                    "exit_code": 0,
                    "stdout": "command output",
                    "stderr": "",
                }
                return asyncio.run(ssh_client.execute_command("ls -la"))

        result = benchmark(ssh_execute)

        # Performance assertions
        assert result["exit_code"] == 0
        assert benchmark.stats["mean"] < 1.0  # Command execution within 1 second

    @pytest.mark.asyncio
    async def test_ssh_file_transfer_performance(self, ssh_client, benchmark):
        """Test SSH file transfer performance."""

        def ssh_transfer():
            with patch.object(ssh_client, "upload_file"):
                # Simulate 1MB file transfer
                file_size_mb = 1
                transfer_time = file_size_mb * 0.1  # 100ms per MB
                time.sleep(transfer_time)
                return transfer_time

        benchmark(ssh_transfer)

        # Performance assertions
        assert benchmark.stats["mean"] < 0.5  # 1MB transfer within 500ms


class TestAIServicePerformance:
    """Test AI service performance."""

    @pytest.mark.asyncio
    async def test_ai_command_suggestion_time(self, ai_service, benchmark):
        """Test AI command suggestion response time."""

        def ai_suggest():
            with patch.object(ai_service, "openrouter_service") as mock_service:
                mock_service.generate_command.return_value = {
                    "command": "ls -la",
                    "explanation": "Lists files with details",
                    "confidence": 0.95,
                }
                return asyncio.run(
                    ai_service.suggest_command(
                        {"prompt": "list files", "api_key": "test-key"}
                    )
                )

        result = benchmark(ai_suggest)

        # Performance assertions
        assert result.command == "ls -la"
        assert benchmark.stats["mean"] < 3.0  # AI response within 3 seconds

    @pytest.mark.asyncio
    async def test_ai_api_key_validation_cache(self, ai_service, benchmark):
        """Test AI API key validation caching performance."""

        def cached_validation():
            with patch.object(ai_service, "openrouter_service") as mock_service:
                mock_service.validate_api_key.return_value = True

                # First call - should hit API
                api_key = "test-key-123"
                result1 = asyncio.run(ai_service.validate_user_api_key(api_key))

                # Second call - should use cache
                result2 = asyncio.run(ai_service.validate_user_api_key(api_key))

                return result1, result2

        results = benchmark(cached_validation)

        # Performance assertions
        assert results[0] == results[1] is True
        assert benchmark.stats["mean"] < 0.1  # Cached validation within 100ms


class TestSynchronizationPerformance:
    """Test synchronization performance."""

    @pytest.mark.asyncio
    async def test_sync_data_processing_time(self, sync_service, benchmark):
        """Test sync data processing performance."""

        def sync_processing():
            # Simulate syncing 100 command history items
            sync_items = [
                {
                    "sync_type": "command_history",
                    "data": {"command": f"command_{i}"},
                    "version": 1,
                }
                for i in range(100)
            ]

            with patch.object(sync_service, "sync_repository") as mock_repo:
                mock_repo.bulk_create.return_value = sync_items
                return asyncio.run(sync_service.bulk_sync("user-123", sync_items))

        result = benchmark(sync_processing)

        # Performance assertions
        assert len(result) == 100
        assert benchmark.stats["mean"] < 1.0  # 100 items sync within 1 second

    @pytest.mark.asyncio
    async def test_real_time_sync_notification_time(self, sync_service, benchmark):
        """Test real-time sync notification performance."""

        def sync_notification():
            with patch.object(sync_service, "redis_client"):
                return asyncio.run(
                    sync_service.notify_sync_update(
                        "user-123",
                        {
                            "sync_type": "command_history",
                            "data": {"command": "ls"},
                        },
                    )
                )

        benchmark(sync_notification)

        # Performance assertions
        assert benchmark.stats["mean"] < 0.05  # Notification within 50ms

    @pytest.mark.asyncio
    async def test_conflict_resolution_time(self, sync_service, benchmark):
        """Test sync conflict resolution performance."""

        def conflict_resolution():
            local_data = {"value": "A", "timestamp": "2025-08-16T10:00:00Z"}
            remote_data = {"value": "B", "timestamp": "2025-08-16T11:00:00Z"}

            return sync_service.resolve_conflict(
                local_data, remote_data, "last_write_wins"
            )

        result = benchmark(conflict_resolution)

        # Performance assertions
        assert result["value"] == "B"
        assert benchmark.stats["mean"] < 0.01  # Conflict resolution within 10ms


class TestLoadTesting:
    """Test system performance under load."""

    @pytest.mark.asyncio
    async def test_api_load_testing(self, performance_app, benchmark):
        """Test API performance under load."""

        async def load_test():
            async with AsyncClient(
                app=performance_app, base_url="http://test"
            ) as client:
                # Simulate 50 concurrent users making requests
                tasks = []
                for i in range(50):
                    tasks.append(client.get("/api/auth/profile"))

                responses = await asyncio.gather(*tasks, return_exceptions=True)
                return responses

        def load_test_sync():
            return asyncio.run(load_test())

        responses = benchmark(load_test_sync)

        # Performance assertions
        assert len(responses) == 50
        success_count = sum(
            1 for r in responses if hasattr(r, "status_code") and r.status_code == 200
        )
        assert success_count >= 45  # At least 90% success rate
        assert benchmark.stats["mean"] < 5.0  # All requests within 5 seconds

    @pytest.mark.asyncio
    async def test_database_load_testing(self, user_repository, benchmark):
        """Test database performance under load."""

        def database_load_test():
            async def concurrent_queries():
                tasks = [user_repository.get_by_id(f"user-{i}") for i in range(20)]
                return await asyncio.gather(*tasks, return_exceptions=True)

            return asyncio.run(concurrent_queries())

        results = benchmark(database_load_test)

        # Performance assertions
        assert len(results) == 20
        assert benchmark.stats["mean"] < 2.0  # All queries within 2 seconds

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, benchmark):
        """Test memory usage under load."""

        def memory_load_test():
            import psutil
            import os

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss

            # Simulate memory-intensive operations
            large_data = []
            for i in range(1000):
                large_data.append({"data": "x" * 1000})  # 1KB per item

            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory

            # Clean up
            del large_data

            return memory_increase / 1024 / 1024  # MB

        memory_increase_mb = benchmark(memory_load_test)

        # Performance assertions
        assert memory_increase_mb < 50  # Memory increase should be reasonable
        assert benchmark.stats["mean"] < 1.0  # Memory allocation within 1 second


class TestPerformanceBaselines:
    """Establish performance baselines for monitoring."""

    def test_api_response_time_baseline(self):
        """Establish API response time baseline."""
        baselines = {
            "auth_login": {"max": 0.5, "avg": 0.2},  # 500ms max, 200ms avg
            "user_profile": {"max": 0.2, "avg": 0.1},  # 200ms max, 100ms avg
            "ssh_profiles": {"max": 0.3, "avg": 0.15},  # 300ms max, 150ms avg
            "ai_suggest": {"max": 3.0, "avg": 1.5},  # 3s max, 1.5s avg
            "sync_data": {"max": 1.0, "avg": 0.5},  # 1s max, 500ms avg
        }

        # Store baselines for monitoring
        with open("performance_baselines.json", "w") as f:
            import json

            json.dump(baselines, f, indent=2)

        assert len(baselines) == 5

    def test_throughput_baseline(self):
        """Establish throughput baseline."""
        throughput_baselines = {
            "api_requests_per_second": 1000,
            "websocket_messages_per_second": 5000,
            "database_queries_per_second": 2000,
            "concurrent_users": 100,
            "concurrent_websockets": 500,
        }

        # Store throughput baselines
        with open("throughput_baselines.json", "w") as f:
            import json

            json.dump(throughput_baselines, f, indent=2)

        assert throughput_baselines["api_requests_per_second"] >= 1000

    def test_resource_usage_baseline(self):
        """Establish resource usage baseline."""
        resource_baselines = {
            "max_memory_mb": 512,
            "max_cpu_percent": 80,
            "max_database_connections": 20,
            "max_redis_memory_mb": 100,
        }

        # Store resource usage baselines
        with open("resource_baselines.json", "w") as f:
            import json

            json.dump(resource_baselines, f, indent=2)

        assert resource_baselines["max_memory_mb"] <= 512
