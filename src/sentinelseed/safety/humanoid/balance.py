"""
Balance Monitoring and Fall Safety for Humanoid Robots.

This module provides balance monitoring, fall detection, and safe state
management for humanoid robots. It implements concepts from robotics
research including:

- Zero Moment Point (ZMP) monitoring
- Center of Mass (CoM) tracking
- Instability detection
- Safe state transitions (controlled kneel, sit, brace)
- Emergency stop protocols

References:
    - ZMP concept: Vukobratovic & Borovac (2004)
    - Fall detection: Renner & Behnke (2006) "Instability Detection"
    - Safe falling: Fujiwara et al. "Falling Motion Control"
    - ISO 10218:2025 - Emergency stop requirements
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple
import logging
import math
import threading
import time

logger = logging.getLogger("sentinelseed.humanoid.balance")

# Configuration constants
DEFAULT_MAX_HISTORY = 50
DEFAULT_ZMP_MARGIN_WARNING = 0.03  # meters
DEFAULT_ZMP_MARGIN_CRITICAL = 0.01  # meters
DEFAULT_MAX_TILT_ANGLE = 0.35  # radians (~20 degrees)
DEFAULT_MAX_ANGULAR_RATE = 2.0  # rad/s
DEFAULT_MAX_COM_VELOCITY = 2.0  # m/s
DEFAULT_FALL_DETECTION_THRESHOLD = 0.5  # radians (~29 degrees)
DEFAULT_MIN_COM_HEIGHT_RATIO = 0.5  # 50% of nominal height
DEFAULT_PREDICTION_HORIZON = 0.2  # seconds


class BalanceState(str, Enum):
    """Current balance state of the humanoid."""
    STABLE = "stable"              # Normal stable operation
    MARGINALLY_STABLE = "marginally_stable"  # Near stability limits
    UNSTABLE = "unstable"          # Actively losing balance
    FALLING = "falling"            # Fall detected, mitigation active
    FALLEN = "fallen"              # On the ground
    RECOVERING = "recovering"      # Getting back up
    EMERGENCY_STOP = "emergency_stop"  # Emergency stopped


class SafeState(str, Enum):
    """Safe states the humanoid can transition to."""
    STANDING = "standing"          # Normal standing
    CROUCHING = "crouching"        # Lowered CoM, wider stance
    KNEELING = "kneeling"          # One or both knees down
    SITTING = "sitting"            # Seated position
    LYING_PRONE = "lying_prone"    # Face down
    LYING_SUPINE = "lying_supine"  # Face up
    BRACING = "bracing"            # Bracing for impact
    FROZEN = "frozen"              # All joints locked (e-stop)


class FallDirection(str, Enum):
    """Direction of detected/predicted fall."""
    FORWARD = "forward"
    BACKWARD = "backward"
    LEFT = "left"
    RIGHT = "right"
    UNKNOWN = "unknown"


@dataclass
class ZMPState:
    """
    Zero Moment Point state.

    The ZMP is the point on the ground where the total moment of inertia
    forces equals zero. For stable walking, the ZMP must stay within
    the support polygon (foot/feet contact area).

    Attributes:
        x: ZMP x-coordinate (m) in robot frame
        y: ZMP y-coordinate (m) in robot frame
        support_polygon: List of (x, y) vertices defining support area
        margin: Distance from ZMP to nearest polygon edge (m)
        is_stable: Whether ZMP is within support polygon
    """
    x: float = 0.0
    y: float = 0.0
    support_polygon: List[Tuple[float, float]] = field(default_factory=list)
    margin: float = 0.0
    is_stable: bool = True

    @property
    def position(self) -> Tuple[float, float]:
        """Get ZMP position as tuple."""
        return (self.x, self.y)


@dataclass
class CoMState:
    """
    Center of Mass state.

    Attributes:
        x: CoM x-coordinate (m) in world frame
        y: CoM y-coordinate (m) in world frame
        z: CoM z-coordinate (m) in world frame
        vx: CoM x-velocity (m/s)
        vy: CoM y-velocity (m/s)
        vz: CoM z-velocity (m/s)
        height_nominal: Nominal standing CoM height (m)
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.9  # Typical humanoid CoM height
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    height_nominal: float = 0.9

    @property
    def position(self) -> Tuple[float, float, float]:
        """Get CoM position as tuple."""
        return (self.x, self.y, self.z)

    @property
    def velocity(self) -> Tuple[float, float, float]:
        """Get CoM velocity as tuple."""
        return (self.vx, self.vy, self.vz)

    @property
    def horizontal_velocity(self) -> float:
        """Get horizontal velocity magnitude."""
        return math.sqrt(self.vx**2 + self.vy**2)

    @property
    def height_ratio(self) -> float:
        """Ratio of current height to nominal (< 1 means lower)."""
        if self.height_nominal > 0:
            return self.z / self.height_nominal
        return 1.0


@dataclass
class IMUReading:
    """
    Inertial Measurement Unit reading.

    Attributes:
        roll: Roll angle (rad)
        pitch: Pitch angle (rad)
        yaw: Yaw angle (rad)
        roll_rate: Roll angular velocity (rad/s)
        pitch_rate: Pitch angular velocity (rad/s)
        yaw_rate: Yaw angular velocity (rad/s)
        acc_x: Linear acceleration x (m/s²)
        acc_y: Linear acceleration y (m/s²)
        acc_z: Linear acceleration z (m/s²)
        timestamp: Reading timestamp
    """
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    roll_rate: float = 0.0
    pitch_rate: float = 0.0
    yaw_rate: float = 0.0
    acc_x: float = 0.0
    acc_y: float = 0.0
    acc_z: float = 9.81  # Gravity
    timestamp: float = field(default_factory=time.time)

    @property
    def total_tilt(self) -> float:
        """Total tilt angle from vertical (rad)."""
        return math.sqrt(self.roll**2 + self.pitch**2)

    @property
    def total_angular_rate(self) -> float:
        """Total angular rate magnitude (rad/s)."""
        return math.sqrt(self.roll_rate**2 + self.pitch_rate**2 + self.yaw_rate**2)


@dataclass
class BalanceMonitorConfig:
    """
    Configuration for balance monitoring.

    Attributes:
        zmp_margin_warning: ZMP margin below which to warn (m)
        zmp_margin_critical: ZMP margin below which is critical (m)
        max_tilt_angle: Maximum safe tilt angle (rad)
        max_angular_rate: Maximum safe angular rate (rad/s)
        max_com_velocity: Maximum safe CoM horizontal velocity (m/s)
        fall_detection_threshold: Tilt threshold for fall detection (rad)
        min_com_height_ratio: Minimum CoM height ratio before fall (0-1)
        prediction_horizon: Time horizon for instability prediction (s)
        max_history: Maximum number of IMU readings to keep in history
    """
    zmp_margin_warning: float = DEFAULT_ZMP_MARGIN_WARNING
    zmp_margin_critical: float = DEFAULT_ZMP_MARGIN_CRITICAL
    max_tilt_angle: float = DEFAULT_MAX_TILT_ANGLE
    max_angular_rate: float = DEFAULT_MAX_ANGULAR_RATE
    max_com_velocity: float = DEFAULT_MAX_COM_VELOCITY
    fall_detection_threshold: float = DEFAULT_FALL_DETECTION_THRESHOLD
    min_com_height_ratio: float = DEFAULT_MIN_COM_HEIGHT_RATIO
    prediction_horizon: float = DEFAULT_PREDICTION_HORIZON
    max_history: int = DEFAULT_MAX_HISTORY

    def __post_init__(self):
        """Validate configuration values."""
        if self.zmp_margin_warning < 0:
            raise ValueError("zmp_margin_warning must be non-negative")
        if self.zmp_margin_critical < 0:
            raise ValueError("zmp_margin_critical must be non-negative")
        if self.zmp_margin_critical > self.zmp_margin_warning:
            raise ValueError("zmp_margin_critical must be <= zmp_margin_warning")
        if self.max_tilt_angle <= 0:
            raise ValueError("max_tilt_angle must be positive")
        if self.max_angular_rate <= 0:
            raise ValueError("max_angular_rate must be positive")
        if self.max_com_velocity <= 0:
            raise ValueError("max_com_velocity must be positive")
        if self.fall_detection_threshold <= 0:
            raise ValueError("fall_detection_threshold must be positive")
        if not 0 < self.min_com_height_ratio <= 1:
            raise ValueError("min_com_height_ratio must be in (0, 1]")
        if self.prediction_horizon <= 0:
            raise ValueError("prediction_horizon must be positive")
        if self.max_history < 1:
            raise ValueError("max_history must be >= 1")


@dataclass
class BalanceAssessment:
    """
    Result of balance assessment.

    Attributes:
        state: Current balance state
        confidence: Confidence in assessment (0-1)
        fall_direction: Predicted fall direction if unstable
        time_to_fall: Estimated time until fall (s), None if stable
        recommended_action: Suggested action
        zmp_state: Current ZMP state
        com_state: Current CoM state
        violations: List of safety violations
    """
    state: BalanceState
    confidence: float = 1.0
    fall_direction: Optional[FallDirection] = None
    time_to_fall: Optional[float] = None
    recommended_action: str = ""
    zmp_state: Optional[ZMPState] = None
    com_state: Optional[CoMState] = None
    violations: List[str] = field(default_factory=list)

    @property
    def is_safe(self) -> bool:
        """Check if balance state is safe."""
        return self.state in (BalanceState.STABLE, BalanceState.MARGINALLY_STABLE)

    @property
    def requires_intervention(self) -> bool:
        """Check if intervention is needed."""
        return self.state in (
            BalanceState.UNSTABLE,
            BalanceState.FALLING,
            BalanceState.EMERGENCY_STOP,
        )


class BalanceMonitor:
    """
    Monitor balance state and detect instability.

    This class monitors ZMP, CoM, and IMU data to assess balance and
    detect potential falls. It can trigger safe state transitions
    when instability is detected.

    Thread Safety:
        This class is thread-safe. All state updates and reads are protected
        by a lock to prevent race conditions in multi-threaded applications.

    Example:
        monitor = BalanceMonitor()

        # Update with sensor readings
        monitor.update_imu(imu_reading)
        monitor.update_zmp(zmp_state)
        monitor.update_com(com_state)

        # Assess balance
        assessment = monitor.assess_balance()
        if not assessment.is_safe:
            print(f"Balance issue: {assessment.state}")
            print(f"Recommended: {assessment.recommended_action}")
    """

    def __init__(self, config: Optional[BalanceMonitorConfig] = None):
        """
        Initialize balance monitor.

        Args:
            config: Balance monitoring configuration

        Raises:
            TypeError: If config is not a BalanceMonitorConfig instance
        """
        if config is not None and not isinstance(config, BalanceMonitorConfig):
            raise TypeError(
                f"config must be BalanceMonitorConfig, got {type(config).__name__}"
            )

        self.config = config or BalanceMonitorConfig()

        # Thread safety lock
        self._lock = threading.RLock()

        # Current state
        self._balance_state = BalanceState.STABLE
        self._zmp_state = ZMPState()
        self._com_state = CoMState()
        self._imu_reading = IMUReading()
        self._history: List[Tuple[float, IMUReading]] = []

        # Callbacks
        self._on_instability: Optional[Callable[[BalanceAssessment], None]] = None
        self._on_fall_detected: Optional[Callable[[FallDirection], None]] = None

    def update_imu(self, reading: IMUReading) -> None:
        """
        Update with new IMU reading.

        Args:
            reading: IMU sensor reading

        Raises:
            TypeError: If reading is not an IMUReading instance
            ValueError: If reading contains invalid values (NaN/Inf)
        """
        if reading is None:
            raise TypeError("reading cannot be None")
        if not isinstance(reading, IMUReading):
            raise TypeError(
                f"reading must be IMUReading, got {type(reading).__name__}"
            )

        # Validate no NaN/Inf values in critical fields
        critical_values = [
            reading.roll, reading.pitch, reading.yaw,
            reading.roll_rate, reading.pitch_rate, reading.yaw_rate,
        ]
        for val in critical_values:
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"IMUReading contains invalid value: {val}")

        with self._lock:
            self._imu_reading = reading
            self._history.append((reading.timestamp, reading))
            if len(self._history) > self.config.max_history:
                self._history.pop(0)

    def update_zmp(self, state: ZMPState) -> None:
        """
        Update with new ZMP state.

        Args:
            state: Zero Moment Point state

        Raises:
            TypeError: If state is not a ZMPState instance
            ValueError: If state contains invalid values (NaN/Inf)
        """
        if state is None:
            raise TypeError("state cannot be None")
        if not isinstance(state, ZMPState):
            raise TypeError(
                f"state must be ZMPState, got {type(state).__name__}"
            )

        # Validate no NaN/Inf values
        if math.isnan(state.x) or math.isinf(state.x):
            raise ValueError(f"ZMPState.x contains invalid value: {state.x}")
        if math.isnan(state.y) or math.isinf(state.y):
            raise ValueError(f"ZMPState.y contains invalid value: {state.y}")

        with self._lock:
            self._zmp_state = state

    def update_com(self, state: CoMState) -> None:
        """
        Update with new CoM state.

        Args:
            state: Center of Mass state

        Raises:
            TypeError: If state is not a CoMState instance
            ValueError: If state contains invalid values (NaN/Inf)
        """
        if state is None:
            raise TypeError("state cannot be None")
        if not isinstance(state, CoMState):
            raise TypeError(
                f"state must be CoMState, got {type(state).__name__}"
            )

        # Validate no NaN/Inf values in position and velocity
        values = [state.x, state.y, state.z, state.vx, state.vy, state.vz]
        for val in values:
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"CoMState contains invalid value: {val}")

        with self._lock:
            self._com_state = state

    def assess_balance(self) -> BalanceAssessment:
        """
        Assess current balance state.

        Returns:
            BalanceAssessment with current state and recommendations
        """
        with self._lock:
            return self._assess_balance_locked()

    def _assess_balance_locked(self) -> BalanceAssessment:
        """Internal method to assess balance (assumes lock is held)."""
        violations = []
        fall_direction = None
        time_to_fall = None

        # Check IMU tilt
        tilt = self._imu_reading.total_tilt
        if tilt > self.config.fall_detection_threshold:
            self._balance_state = BalanceState.FALLING
            fall_direction = self._determine_fall_direction()
            violations.append(f"Critical tilt: {math.degrees(tilt):.1f}°")
        elif tilt > self.config.max_tilt_angle:
            self._balance_state = BalanceState.UNSTABLE
            fall_direction = self._determine_fall_direction()
            time_to_fall = self._estimate_time_to_fall()
            violations.append(f"Excessive tilt: {math.degrees(tilt):.1f}°")

        # Check angular rate
        ang_rate = self._imu_reading.total_angular_rate
        if ang_rate > self.config.max_angular_rate:
            if self._balance_state == BalanceState.STABLE:
                self._balance_state = BalanceState.MARGINALLY_STABLE
            violations.append(f"High angular rate: {ang_rate:.2f} rad/s")

        # Check ZMP margin
        if self._zmp_state.margin < self.config.zmp_margin_critical:
            if self._balance_state in (BalanceState.STABLE, BalanceState.MARGINALLY_STABLE):
                self._balance_state = BalanceState.UNSTABLE
            violations.append(f"Critical ZMP margin: {self._zmp_state.margin*100:.1f} cm")
        elif self._zmp_state.margin < self.config.zmp_margin_warning:
            if self._balance_state == BalanceState.STABLE:
                self._balance_state = BalanceState.MARGINALLY_STABLE
            violations.append(f"Low ZMP margin: {self._zmp_state.margin*100:.1f} cm")

        # Check ZMP inside polygon
        if not self._zmp_state.is_stable:
            self._balance_state = BalanceState.UNSTABLE
            violations.append("ZMP outside support polygon")

        # Check CoM height
        if self._com_state.height_ratio < self.config.min_com_height_ratio:
            self._balance_state = BalanceState.FALLING
            violations.append(f"CoM height low: {self._com_state.height_ratio:.0%}")

        # Check CoM velocity
        com_vel = self._com_state.horizontal_velocity
        if com_vel > self.config.max_com_velocity:
            if self._balance_state == BalanceState.STABLE:
                self._balance_state = BalanceState.MARGINALLY_STABLE
            violations.append(f"High CoM velocity: {com_vel:.2f} m/s")

        # Determine recommended action
        recommended = self._get_recommended_action()

        # Calculate confidence
        confidence = self._calculate_confidence()

        # If no violations, ensure stable state
        if not violations:
            self._balance_state = BalanceState.STABLE

        assessment = BalanceAssessment(
            state=self._balance_state,
            confidence=confidence,
            fall_direction=fall_direction,
            time_to_fall=time_to_fall,
            recommended_action=recommended,
            zmp_state=self._zmp_state,
            com_state=self._com_state,
            violations=violations,
        )

        # Trigger callbacks
        if assessment.requires_intervention and self._on_instability:
            self._on_instability(assessment)
        if self._balance_state == BalanceState.FALLING and self._on_fall_detected:
            self._on_fall_detected(fall_direction or FallDirection.UNKNOWN)

        return assessment

    def _determine_fall_direction(self) -> FallDirection:
        """Determine the direction of fall from IMU data."""
        roll = self._imu_reading.roll
        pitch = self._imu_reading.pitch

        # Determine primary fall direction
        if abs(pitch) > abs(roll):
            if pitch > 0:
                return FallDirection.BACKWARD
            else:
                return FallDirection.FORWARD
        else:
            if roll > 0:
                return FallDirection.RIGHT
            else:
                return FallDirection.LEFT

    def _estimate_time_to_fall(self) -> float:
        """Estimate time until fall based on current state."""
        # Simple estimate based on tilt angle and rate
        tilt = self._imu_reading.total_tilt
        rate = self._imu_reading.total_angular_rate

        remaining_angle = self.config.fall_detection_threshold - tilt
        if remaining_angle <= 0:
            return 0.0
        if rate <= 0.01:
            return float('inf')

        return remaining_angle / rate

    def _get_recommended_action(self) -> str:
        """Get recommended action based on balance state."""
        if self._balance_state == BalanceState.STABLE:
            return "Continue normal operation"
        elif self._balance_state == BalanceState.MARGINALLY_STABLE:
            return "Reduce speed, widen stance"
        elif self._balance_state == BalanceState.UNSTABLE:
            return "Execute balance recovery, consider safe state transition"
        elif self._balance_state == BalanceState.FALLING:
            return "Execute fall mitigation (brace for impact)"
        elif self._balance_state == BalanceState.EMERGENCY_STOP:
            return "Maintain frozen state until cleared"
        else:
            return "Assess situation"

    def _calculate_confidence(self) -> float:
        """Calculate confidence in the balance assessment."""
        # Base confidence
        confidence = 0.9

        # Reduce confidence if data is stale
        if len(self._history) < 3:
            confidence -= 0.2

        # Reduce confidence for extreme values
        if self._imu_reading.total_tilt > self.config.max_tilt_angle * 0.8:
            confidence -= 0.1

        return max(0.1, min(1.0, confidence))

    def trigger_emergency_stop(self) -> None:
        """Trigger emergency stop state."""
        with self._lock:
            self._balance_state = BalanceState.EMERGENCY_STOP
            logger.warning("Emergency stop triggered")

    def clear_emergency_stop(self) -> None:
        """Clear emergency stop and return to stable."""
        with self._lock:
            if self._balance_state == BalanceState.EMERGENCY_STOP:
                self._balance_state = BalanceState.STABLE
                logger.info("Emergency stop cleared")

    def set_instability_callback(
        self,
        callback: Optional[Callable[[BalanceAssessment], None]],
    ) -> None:
        """
        Set callback for instability detection.

        Args:
            callback: Function to call when instability is detected, or None to clear

        Raises:
            TypeError: If callback is not callable
        """
        if callback is not None and not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            self._on_instability = callback

    def set_fall_callback(
        self,
        callback: Optional[Callable[[FallDirection], None]],
    ) -> None:
        """
        Set callback for fall detection.

        Args:
            callback: Function to call when fall is detected, or None to clear

        Raises:
            TypeError: If callback is not callable
        """
        if callback is not None and not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            self._on_fall_detected = callback

    @property
    def current_state(self) -> BalanceState:
        """Get current balance state."""
        with self._lock:
            return self._balance_state

    def get_history(self) -> List[Tuple[float, IMUReading]]:
        """Get copy of IMU history for analysis."""
        with self._lock:
            return list(self._history)


class SafeStateManager:
    """
    Manage safe state transitions for humanoid robot.

    This class handles transitions between safe states when the robot
    needs to reduce risk (e.g., crouch when unstable, kneel for
    e-stop, brace for fall).

    Thread Safety:
        This class is thread-safe. All state transitions are protected
        by a lock to prevent race conditions.

    Example:
        manager = SafeStateManager()

        # Check if transition is valid
        if manager.can_transition(SafeState.KNEELING):
            trajectory = manager.get_transition_trajectory(SafeState.KNEELING)
            execute_trajectory(trajectory)
            manager.confirm_transition(SafeState.KNEELING)
    """

    # Valid state transitions
    _TRANSITIONS: Dict[SafeState, List[SafeState]] = {
        SafeState.STANDING: [SafeState.CROUCHING, SafeState.KNEELING, SafeState.BRACING, SafeState.FROZEN],
        SafeState.CROUCHING: [SafeState.STANDING, SafeState.KNEELING, SafeState.SITTING, SafeState.BRACING],
        SafeState.KNEELING: [SafeState.STANDING, SafeState.CROUCHING, SafeState.SITTING, SafeState.LYING_PRONE],
        SafeState.SITTING: [SafeState.KNEELING, SafeState.LYING_SUPINE],
        SafeState.LYING_PRONE: [SafeState.KNEELING],
        SafeState.LYING_SUPINE: [SafeState.SITTING],
        SafeState.BRACING: [SafeState.LYING_PRONE, SafeState.LYING_SUPINE],
        SafeState.FROZEN: [SafeState.STANDING, SafeState.CROUCHING],
    }

    # Estimated transition times (seconds)
    _TRANSITION_TIMES: Dict[Tuple[SafeState, SafeState], float] = {
        (SafeState.STANDING, SafeState.CROUCHING): 0.5,
        (SafeState.STANDING, SafeState.KNEELING): 1.5,
        (SafeState.STANDING, SafeState.BRACING): 0.3,
        (SafeState.STANDING, SafeState.FROZEN): 0.1,
        (SafeState.CROUCHING, SafeState.STANDING): 0.5,
        (SafeState.CROUCHING, SafeState.KNEELING): 1.0,
        (SafeState.KNEELING, SafeState.STANDING): 2.0,
        (SafeState.BRACING, SafeState.LYING_PRONE): 0.5,
    }

    # Default transition time when not explicitly specified
    _DEFAULT_TRANSITION_TIME: float = 1.0

    def __init__(self, initial_state: SafeState = SafeState.STANDING):
        """
        Initialize safe state manager.

        Args:
            initial_state: Starting safe state

        Raises:
            TypeError: If initial_state is not a SafeState
        """
        if not isinstance(initial_state, SafeState):
            raise TypeError(
                f"initial_state must be SafeState, got {type(initial_state).__name__}"
            )

        self._lock = threading.RLock()
        self._current_state = initial_state
        self._transition_in_progress = False
        self._target_state: Optional[SafeState] = None

    @property
    def current_state(self) -> SafeState:
        """Get current safe state."""
        with self._lock:
            return self._current_state

    @property
    def is_transitioning(self) -> bool:
        """Check if a transition is in progress."""
        with self._lock:
            return self._transition_in_progress

    @property
    def target_state(self) -> Optional[SafeState]:
        """Get target state of current transition, if any."""
        with self._lock:
            return self._target_state

    def can_transition(self, target: SafeState) -> bool:
        """
        Check if transition to target state is valid.

        Args:
            target: Desired target state

        Returns:
            True if transition is allowed

        Raises:
            TypeError: If target is not a SafeState
        """
        if not isinstance(target, SafeState):
            raise TypeError(
                f"target must be SafeState, got {type(target).__name__}"
            )

        with self._lock:
            if self._transition_in_progress:
                return False
            valid_targets = self._TRANSITIONS.get(self._current_state, [])
            return target in valid_targets

    def get_valid_transitions(self) -> List[SafeState]:
        """Get list of valid target states from current state."""
        with self._lock:
            return list(self._TRANSITIONS.get(self._current_state, []))

    def get_transition_time(self, target: SafeState) -> float:
        """
        Get estimated transition time to target state.

        Args:
            target: Target state

        Returns:
            Estimated time in seconds

        Raises:
            TypeError: If target is not a SafeState
        """
        if not isinstance(target, SafeState):
            raise TypeError(
                f"target must be SafeState, got {type(target).__name__}"
            )

        with self._lock:
            key = (self._current_state, target)
            return self._TRANSITION_TIMES.get(key, self._DEFAULT_TRANSITION_TIME)

    def start_transition(self, target: SafeState) -> bool:
        """
        Start transition to target state.

        Args:
            target: Target state

        Returns:
            True if transition started

        Raises:
            TypeError: If target is not a SafeState
        """
        if not isinstance(target, SafeState):
            raise TypeError(
                f"target must be SafeState, got {type(target).__name__}"
            )

        with self._lock:
            if self._transition_in_progress:
                return False
            valid_targets = self._TRANSITIONS.get(self._current_state, [])
            if target not in valid_targets:
                return False

            self._transition_in_progress = True
            self._target_state = target
            logger.debug(f"Starting transition: {self._current_state} -> {target}")
            return True

    def confirm_transition(self, state: SafeState) -> bool:
        """
        Confirm that transition to state completed.

        Args:
            state: State that was achieved

        Returns:
            True if transition was confirmed, False if state doesn't match target

        Raises:
            TypeError: If state is not a SafeState
        """
        if not isinstance(state, SafeState):
            raise TypeError(
                f"state must be SafeState, got {type(state).__name__}"
            )

        with self._lock:
            if self._transition_in_progress and state == self._target_state:
                old_state = self._current_state
                self._current_state = state
                self._transition_in_progress = False
                self._target_state = None
                logger.debug(f"Transition confirmed: {old_state} -> {state}")
                return True
            return False

    def cancel_transition(self) -> None:
        """Cancel ongoing transition."""
        with self._lock:
            if self._transition_in_progress:
                logger.debug(f"Transition cancelled: {self._current_state} -> {self._target_state}")
            self._transition_in_progress = False
            self._target_state = None

    def get_safest_state(self, fall_direction: Optional[FallDirection] = None) -> SafeState:
        """
        Get the safest achievable state given circumstances.

        Args:
            fall_direction: Direction of fall if applicable

        Returns:
            Recommended safe state

        Raises:
            TypeError: If fall_direction is not a FallDirection or None
        """
        if fall_direction is not None and not isinstance(fall_direction, FallDirection):
            raise TypeError(
                f"fall_direction must be FallDirection or None, got {type(fall_direction).__name__}"
            )

        with self._lock:
            # If falling, brace
            if fall_direction:
                valid = self._TRANSITIONS.get(self._current_state, [])
                if SafeState.BRACING in valid:
                    return SafeState.BRACING

            # Otherwise, prefer lower CoM states
            valid = self._TRANSITIONS.get(self._current_state, [])
            preference = [
                SafeState.CROUCHING,
                SafeState.KNEELING,
                SafeState.SITTING,
                SafeState.FROZEN,
            ]

            for state in preference:
                if state in valid:
                    return state

            return self._current_state


__all__ = [
    # Constants (for custom configuration)
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_ZMP_MARGIN_WARNING",
    "DEFAULT_ZMP_MARGIN_CRITICAL",
    "DEFAULT_MAX_TILT_ANGLE",
    "DEFAULT_MAX_ANGULAR_RATE",
    "DEFAULT_MAX_COM_VELOCITY",
    "DEFAULT_FALL_DETECTION_THRESHOLD",
    "DEFAULT_MIN_COM_HEIGHT_RATIO",
    "DEFAULT_PREDICTION_HORIZON",
    # Enums
    "BalanceState",
    "SafeState",
    "FallDirection",
    # Data classes
    "ZMPState",
    "CoMState",
    "IMUReading",
    "BalanceMonitorConfig",
    "BalanceAssessment",
    # Classes
    "BalanceMonitor",
    "SafeStateManager",
]
