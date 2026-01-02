#!/usr/bin/env python3
"""
Real ROS2 Integration Test for Sentinel.

This script tests the Sentinel ROS2 integration with actual ROS2 nodes,
publishers, and subscribers. It verifies that:

1. SentinelSafetyNode can be created and configured
2. Safe commands pass through unchanged
3. Unsafe commands are blocked/clamped
4. Diagnostics are published correctly

Requirements:
    - ROS2 (Humble/Jazzy) installed and sourced
    - sentinelseed package installed
    - Run inside WSL2 or native Linux

Usage:
    source /opt/ros/humble/setup.bash  # or jazzy
    python3 test_ros2_real.py
"""

import sys
import time
import threading
from typing import List, Optional, Tuple
from dataclasses import dataclass

# Check ROS2 availability first
try:
    import rclpy
    from rclpy.node import Node
    from rclpy.executors import MultiThreadedExecutor
    from geometry_msgs.msg import Twist
    from std_msgs.msg import String
    ROS2_AVAILABLE = True
except ImportError as e:
    ROS2_AVAILABLE = False
    ROS2_ERROR = str(e)


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    message: str
    duration: float = 0.0


class TestResults:
    """Collect and report test results."""

    def __init__(self):
        self.results: List[TestResult] = []

    def add(self, name: str, passed: bool, message: str, duration: float = 0.0):
        self.results.append(TestResult(name, passed, message, duration))

    def print_summary(self):
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed

        for r in self.results:
            status = "[PASS]" if r.passed else "[FAIL]"
            print(f"  {status} {r.name}")
            if not r.passed:
                print(f"         {r.message}")

        print("-" * 60)
        print(f"Total: {len(self.results)} | Passed: {passed} | Failed: {failed}")
        print("=" * 60)

        return failed == 0


# ROS2-dependent classes are only defined when ROS2 is available
if ROS2_AVAILABLE:
    class TestPublisher(Node):
        """Node that publishes test commands."""

        def __init__(self, topic: str = '/cmd_vel_raw'):
            super().__init__('test_publisher')
            self.publisher = self.create_publisher(Twist, topic, 10)
            self.get_logger().info(f'TestPublisher ready on {topic}')

        def publish_velocity(self, linear_x: float, angular_z: float):
            msg = Twist()
            msg.linear.x = linear_x
            msg.angular.z = angular_z
            self.publisher.publish(msg)
            self.get_logger().debug(f'Published: linear={linear_x}, angular={angular_z}')

    class TestSubscriber(Node):
        """Node that subscribes to filtered commands."""

        def __init__(self, topic: str = '/cmd_vel'):
            super().__init__('test_subscriber')
            self.received_msgs: List[Twist] = []
            self.subscription = self.create_subscription(
                Twist,
                topic,
                self._callback,
                10
            )
            self.get_logger().info(f'TestSubscriber ready on {topic}')

        def _callback(self, msg: Twist):
            self.received_msgs.append(msg)
            self.get_logger().debug(f'Received: linear={msg.linear.x}, angular={msg.angular.z}')

        def get_last_msg(self) -> Optional[Twist]:
            return self.received_msgs[-1] if self.received_msgs else None

        def clear(self):
            self.received_msgs.clear()

    class StatusSubscriber(Node):
        """Node that subscribes to safety status."""

        def __init__(self, topic: str = '/sentinel/status'):
            super().__init__('status_subscriber')
            self.received_msgs: List[str] = []
            self.subscription = self.create_subscription(
                String,
                topic,
                self._callback,
                10
            )
            self.get_logger().info(f'StatusSubscriber ready on {topic}')

        def _callback(self, msg: String):
            self.received_msgs.append(msg.data)
            self.get_logger().debug(f'Status: {msg.data}')

        def get_last_status(self) -> Optional[str]:
            return self.received_msgs[-1] if self.received_msgs else None

        def clear(self):
            self.received_msgs.clear()


def run_tests():
    """Run all ROS2 integration tests."""
    results = TestResults()

    print("=" * 60)
    print("Sentinel ROS2 Real Integration Tests")
    print("=" * 60)

    # Test 1: ROS2 availability
    print("\n[Test 1] Checking ROS2 availability...")
    if not ROS2_AVAILABLE:
        results.add(
            "ROS2 Available",
            False,
            f"ROS2 not found: {ROS2_ERROR}. Make sure to source ROS2 setup.bash"
        )
        results.print_summary()
        return False
    results.add("ROS2 Available", True, "rclpy imported successfully")

    # Initialize ROS2
    print("\n[Test 2] Initializing ROS2...")
    try:
        rclpy.init()
        results.add("ROS2 Init", True, "rclpy.init() successful")
    except Exception as e:
        results.add("ROS2 Init", False, str(e))
        results.print_summary()
        return False

    try:
        # Test 3: Import Sentinel ROS2 integration
        print("\n[Test 3] Importing Sentinel ROS2 integration...")
        try:
            from sentinelseed.integrations.ros2 import (
                SentinelSafetyNode,
                CommandSafetyFilter,
                VelocityLimits,
            )
            from sentinelseed.integrations.ros2.nodes import ROS2_AVAILABLE as SENTINEL_ROS2

            if SENTINEL_ROS2:
                results.add("Sentinel Import", True, "Using real ROS2 (not mock)")
            else:
                results.add("Sentinel Import", False, "Sentinel is using mock mode despite ROS2 being available")
        except Exception as e:
            results.add("Sentinel Import", False, str(e))
            results.print_summary()
            return False

        # Test 4: Create SentinelSafetyNode
        print("\n[Test 4] Creating SentinelSafetyNode...")
        try:
            safety_node = SentinelSafetyNode(
                node_name='sentinel_test_node',
                input_topic='/cmd_vel_raw',
                output_topic='/cmd_vel',
                status_topic='/sentinel/status',
                max_linear_vel=1.0,
                max_angular_vel=0.5,
                mode='clamp',
            )
            results.add("Create SafetyNode", True, "Node created successfully")
        except Exception as e:
            results.add("Create SafetyNode", False, str(e))
            results.print_summary()
            return False

        # Test 5: Configure lifecycle
        print("\n[Test 5] Configuring lifecycle...")
        try:
            from rclpy.lifecycle import TransitionCallbackReturn
            ret = safety_node.on_configure(None)
            if ret == TransitionCallbackReturn.SUCCESS:
                results.add("Configure Lifecycle", True, "on_configure() returned SUCCESS")
            else:
                results.add("Configure Lifecycle", False, f"on_configure() returned {ret}")
        except Exception as e:
            results.add("Configure Lifecycle", False, str(e))

        # Test 6: Activate lifecycle
        print("\n[Test 6] Activating lifecycle...")
        try:
            ret = safety_node.on_activate(None)
            if ret == TransitionCallbackReturn.SUCCESS:
                results.add("Activate Lifecycle", True, "on_activate() returned SUCCESS")
            else:
                results.add("Activate Lifecycle", False, f"on_activate() returned {ret}")
        except Exception as e:
            results.add("Activate Lifecycle", False, str(e))

        # Test 7: Create test nodes
        print("\n[Test 7] Creating test publisher/subscriber...")
        try:
            publisher = TestPublisher('/cmd_vel_raw')
            subscriber = TestSubscriber('/cmd_vel')
            status_sub = StatusSubscriber('/sentinel/status')
            results.add("Create Test Nodes", True, "Publisher and subscribers created")
        except Exception as e:
            results.add("Create Test Nodes", False, str(e))
            results.print_summary()
            return False

        # Create executor
        executor = MultiThreadedExecutor()
        executor.add_node(safety_node)
        executor.add_node(publisher)
        executor.add_node(subscriber)
        executor.add_node(status_sub)

        # Spin in background
        spin_thread = threading.Thread(target=executor.spin, daemon=True)
        spin_thread.start()

        # Give nodes time to discover each other
        print("\n[Test 8] Waiting for node discovery...")
        time.sleep(2.0)
        results.add("Node Discovery", True, "Waited 2s for discovery")

        # Test 9: Safe command passthrough
        print("\n[Test 9] Testing safe command passthrough...")
        subscriber.clear()
        publisher.publish_velocity(0.5, 0.2)  # Safe: within limits
        time.sleep(0.5)

        last_msg = subscriber.get_last_msg()
        if last_msg is not None:
            if abs(last_msg.linear.x - 0.5) < 0.01 and abs(last_msg.angular.z - 0.2) < 0.01:
                results.add(
                    "Safe Command Passthrough",
                    True,
                    f"Command passed unchanged: linear={last_msg.linear.x}, angular={last_msg.angular.z}"
                )
            else:
                results.add(
                    "Safe Command Passthrough",
                    False,
                    f"Command modified unexpectedly: linear={last_msg.linear.x}, angular={last_msg.angular.z}"
                )
        else:
            results.add("Safe Command Passthrough", False, "No message received")

        # Test 10: Unsafe command clamping
        print("\n[Test 10] Testing unsafe command clamping...")
        subscriber.clear()
        publisher.publish_velocity(2.0, 1.0)  # Unsafe: exceeds limits
        time.sleep(0.5)

        last_msg = subscriber.get_last_msg()
        if last_msg is not None:
            # Should be clamped to 1.0 linear, 0.5 angular
            linear_ok = abs(last_msg.linear.x - 1.0) < 0.01
            angular_ok = abs(last_msg.angular.z - 0.5) < 0.01
            if linear_ok and angular_ok:
                results.add(
                    "Unsafe Command Clamping",
                    True,
                    f"Command clamped correctly: linear={last_msg.linear.x}, angular={last_msg.angular.z}"
                )
            else:
                results.add(
                    "Unsafe Command Clamping",
                    False,
                    f"Command not clamped correctly: linear={last_msg.linear.x} (expected 1.0), angular={last_msg.angular.z} (expected 0.5)"
                )
        else:
            results.add("Unsafe Command Clamping", False, "No message received")

        # Test 11: Status publication
        print("\n[Test 11] Testing status publication...")
        last_status = status_sub.get_last_status()
        if last_status is not None:
            if "safe=" in last_status and "processed=" in last_status:
                results.add(
                    "Status Publication",
                    True,
                    f"Status received: {last_status[:50]}..."
                )
            else:
                results.add(
                    "Status Publication",
                    False,
                    f"Invalid status format: {last_status}"
                )
        else:
            results.add("Status Publication", False, "No status message received")

        # Test 12: Diagnostics
        print("\n[Test 12] Testing diagnostics...")
        try:
            diag = safety_node.get_diagnostics()
            if diag.commands_processed > 0:
                results.add(
                    "Diagnostics",
                    True,
                    f"Processed: {diag.commands_processed}, Blocked: {diag.commands_blocked}"
                )
            else:
                results.add("Diagnostics", False, "No commands recorded in diagnostics")
        except Exception as e:
            results.add("Diagnostics", False, str(e))

        # Cleanup
        print("\n[Cleanup] Shutting down nodes...")
        safety_node.on_deactivate(None)
        safety_node.on_cleanup(None)
        executor.shutdown()

    finally:
        rclpy.shutdown()

    # Print summary
    return results.print_summary()


def main():
    """Main entry point."""
    print("")
    print("=" * 60)
    print("  SENTINEL ROS2 REAL INTEGRATION TEST")
    print("=" * 60)
    print("")
    print("This test verifies the Sentinel ROS2 integration works")
    print("with actual ROS2 nodes, publishers, and subscribers.")
    print("")
    print("Prerequisites:")
    print("  1. ROS2 (Humble/Jazzy) installed")
    print("  2. ROS2 environment sourced:")
    print("     source /opt/ros/humble/setup.bash")
    print("  3. sentinelseed installed:")
    print("     pip install sentinelseed")
    print("")

    success = run_tests()

    if success:
        print("\nAll tests passed! The ROS2 integration is working correctly.")
        sys.exit(0)
    else:
        print("\nSome tests failed. See details above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
