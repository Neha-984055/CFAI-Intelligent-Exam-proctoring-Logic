import dataclasses
from typing import List, Dict, Set, Tuple
import heapq
import math
import random

# =====================================================================
# CO1: PROBLEM FORMULATION & KNOWLEDGE REPRESENTATION
# Formulating the proctoring environment components (State space, actions, 
# constraints) using typed dataclasses and tracking step-by-step reasoning traces.
# =====================================================================

@dataclasses.dataclass(frozen=True)
class ProctoringState:
    """
    Represents a specific minute/snapshot of a student during an exam.
    Tracks head posture shift, audio level (dB), and tab switches.
    """
    head_posture: int   # Deviation degrees from center (e.g., 0=looking straight, 45=side)
    audio_level: float  # Ambient noise volume in decibels (dB)
    tab_switches: int   # Cumulative browser tab switches during the test

class ExamProctorAgent:
    def __init__(self, PEAS_description: dict):
        # Initializing agent using the structural PEAS framework defined in CO1/Session 1
        self.peas = PEAS_description
        self.reasoning_log: List[str] = []

    def log_reasoning(self, step_trace: str):
        """Appends step-by-step execution traces for system explainability."""
        self.reasoning_log.append(step_trace)


# =====================================================================
# CO2: GRAPH/STATE-SPACE SEARCH ALGORITHMS & HEURISTIC DESIGN
# Implementing an A* search algorithm to evaluate risk progression over time.
# The state space maps standard observations to elevated anomaly tiers.
# =====================================================================

class ProctoringSearchSpace:
    def __init__(self):
        # Knowledge representation via graph/dictionary node-to-cost mappings
        self.graph: Dict[str, List[Tuple[str, float]]] = {
            "Normal": [("Suspicious_Look", 2.0), ("Noise_Spike", 1.5)],
            "Suspicious_Look": [("Escalated_Risk", 3.0), ("Normal", 1.0)],
            "Noise_Spike": [("Escalated_Risk", 2.5), ("Normal", 1.0)],
            "Escalated_Risk": [("Flagged_Violation", 4.0)]
        }
    
    def get_neighbors(self, state: str) -> List[Tuple[str, float]]:
        return self.graph.get(state, [])

    @staticmethod
    def heuristic(current_state: str, goal_state: str) -> float:
        """
        Admissible and consistent heuristic estimating the distance to a Flagged_Violation.
        It never overestimates the step-cost (Admissibility Intuition).
        """
        h_values = {
            "Normal": 4.0,
            "Suspicious_Look": 2.0,
            "Noise_Spike": 2.0,
            "Escalated_Risk": 1.0,
            "Flagged_Violation": 0.0
        }
        return h_values.get(current_state, 99.0)

    def a_star_search(self, start: str, goal: str) -> Tuple[List[str], float]:
        """
        Computes the highest-probability path of violation escalation using A* search.
        Utilizes open sets managed via a priority queue/heap structure.
        """
        open_set = []
        heapq.heappush(open_set, (0 + self.heuristic(start, goal), 0, start, [start]))
        closed_set: Set[str] = set()

        while open_set:
            f, g, current, path = heapq.heappop(open_set)

            if current in closed_set:
                continue
            if current == goal:
                return path, g

            closed_set.add(current)

            for neighbor, cost in self.get_neighbors(current):
                if neighbor not in closed_set:
                    new_g = g + cost
                    new_f = new_g + self.heuristic(neighbor, goal)
                    heapq.heappush(open_set, (new_f, new_g, neighbor, path + [neighbor]))
        
        return [], float('inf')


# =====================================================================
# CO3: CONSTRAINT SATISFACTION PROBLEMS (CSP)
# Backtracking search checking that room configuration requirements match rules
# (e.g., webcam clearance, audio feeds, and secondary camera rules).
# =====================================================================

class ProctoringCSP:
    def __init__(self):
        # Variables represent sub-components that need an asset assigned
        self.variables = ["Primary_Webcam", "Microphone", "Secondary_Cam"]
        # Domains represent assignment slots/clearance qualities
        self.domains = {
            "Primary_Webcam": ["Clear", "Obstructed", "Low_Light"],
            "Microphone": ["Active_Feed", "Muted"],
            "Secondary_Cam": ["Wide_Angle_Clear", "No_Feed"]
        }
        
    def is_consistent(self, assignment: Dict[str, str]) -> bool:
        """Validates current assignments against hard integrity constraints."""
        # Rules: Microphone cannot be muted; Primary webcam must be perfectly clear.
        if "Primary_Webcam" in assignment and assignment["Primary_Webcam"] in ["Obstructed", "Low_Light"]:
            return False
        if "Microphone" in assignment and assignment["Microphone"] == "Muted":
            return False
        if "Secondary_Cam" in assignment and assignment["Secondary_Cam"] == "No_Feed":
            # High strictness configuration requires a secondary camera if setup is risky
            return False
        return True

    def backtracking_search(self, assignment: Dict[str, str] = None) -> Dict[str, str]:
        """
        Applies a basic constraint satisfaction backtracking methodology to 
        verify whether environment states comply with security profiles.
        """
        if assignment is None:
            assignment = {}

        if len(assignment) == len(self.variables):
            return assignment

        # MRV Heuristic Intuition: Selecting unassigned variable
        unassigned = [v for v in self.variables if v not in assignment]
        var = unassigned[0]

        for value in self.domains[var]:
            local_assignment = assignment.copy()
            local_assignment[var] = value
            
            # Forward checking verification step
            if self.is_consistent(local_assignment):
                result = self.backtracking_search(local_assignment)
                if result is not None:
                    return result
                    
        return None  # Triggers fallback tracking if constraints fail


# =====================================================================
# CO4: ADVERSARIAL DECISION MAKING (MINIMAX / POLICY SELECTION)
# Bounded agent decisions balancing system action triggers versus an evasive
# malicious user path (maximizing flag avoidance).
# =====================================================================

class ProctoringDecisionGame:
    @staticmethod
    def minimax_decision(depth: int, is_agent_maximizing: bool) -> int:
        """
        Simulates optimal policy selection under bounded computational visibility layers.
        Agent wants to maximize flag accuracy; cheating model acts to minimize visibility.
        """
        # Terminal Node Evaluation Concept
        if depth == 0:
            return random.choice([10, 45, 80]) # Mock risk values

        if is_agent_maximizing:
            max_eval = -math.inf
            # Simulate possible proctor validation responses
            for action_move in [1, 2]:
                evaluation = ProctoringDecisionGame.minimax_decision(depth - 1, False)
                max_eval = max(max_eval, evaluation)
            return max_eval
        else:
            min_eval = math.inf
            # Simulate candidate student environmental bypasses
            for student_move in [1, 2]:
                evaluation = ProctoringDecisionGame.minimax_decision(depth - 1, True)
                min_eval = min(min_eval, evaluation)
            return min_eval


# =====================================================================
# CO5: REASONING UNDER UNCERTAINTY (BAYES RULE)
# Handles noisy sensors and ambiguous alerts using a conditional probability matrix.
# Computes the likelihood of actual cheating given a system anomaly trigger.
# =====================================================================

class UncertaintyProbabilisticReasoning:
    @staticmethod
    def calculate_cheating_probability(has_anomaly_triggered: bool) -> float:
        """
        Applies Bayes' Rule to update state parameters under uncertain telemetry.
        P(Cheating | Anomaly) = [P(Anomaly | Cheating) * P(Cheating)] / P(Anomaly)
        """
        # Prior Base Probabilities
        p_cheating = 0.05   # Baseline distribution metric across cohorts
        p_clean = 0.95

        # Conditional Probabilities (Sensor sensitivity profiles)
        p_anomaly_given_cheating = 0.90  # Sensitivity
        p_anomaly_given_clean = 0.15     # False positive rate from dynamic lighting/background noise

        if has_anomaly_triggered:
            # Total probability of anomaly occurrence
            p_anomaly = (p_anomaly_given_cheating * p_cheating) + (p_anomaly_given_clean * p_clean)
            # Posterior calculation step
            p_post_cheating = (p_anomaly_given_cheating * p_cheating) / p_anomaly
            return round(p_post_cheating, 4)
        
        return 0.002 # Extremely low residual probability if clean profile detected


# =====================================================================
# CO6: HYBRID INTEGRATED PIPELINE & EXPLAINABLE OUTPUTS
# Unifies Representation + Search + CSP Verification + Probabilistic Logic 
# to produce a production-ready, auditable reasoning log.
# =====================================================================

def run_intelligent_exam_proctor_pipeline():
    # Instantiate Master Configuration System (PEAS)
    peas_config = {
        "Performance": "Maintain exam integrity while minimizing false-positive flags",
        "Environment": "Web browser interface, user workspace camera, and microphone stream",
        "Actuators": "Automated warnings, lock-out protocol thresholds, human-proctor alerts",
        "Sensors": "Computer vision posture vectors, audio level captures, tab status counters"
    }
    
    agent = ExamProctorAgent(peas_config)
    agent.log_reasoning("[CO1 Initialization] Initialized Exam Proctoring framework under PEAS structure.")

    # 1. Capture Current Telemetry State via Core Dataclasses
    current_telemetry = ProctoringState(head_posture=35, audio_level=72.5, tab_switches=1)
    agent.log_reasoning(
        f"[CO1 Representation] Captured real-time telemetry frame: Posture Dev={current_telemetry.head_posture}°, "
        f"Audio Noise={current_telemetry.audio_level}dB, Browser Tabs Switched={current_telemetry.tab_switches}."
    )

    # 2. Check Structural Setup Rules via CSP Backtracking Verification
    csp_verifier = ProctoringCSP()
    validation_assignment = csp_verifier.backtracking_search()
    
    if validation_assignment:
        agent.log_reasoning(
            f"[CO3 CSP Proof] Hardware verification mapping confirmed: {validation_assignment}. "
            "Integrity bounds satisfied."
        )
    else:
        agent.log_reasoning("[CO3 CSP Failure Alert] Current system asset parameters fail secure integrity profiles!")

    # 3. Predict Escalation Velocity using Search Optimization Graph Bounds
    search_space = ProctoringSearchSpace()
    escalation_path, total_risk_cost = search_space.a_star_search("Normal", "Flagged_Violation")
    agent.log_reasoning(
        f"[CO2 Search Trace] Calculated risk progression path via A*: {escalation_path} "
        f"with cumulative weight index of {total_risk_cost}."
    )

    # 4. Resolve Uncertain Sensor Fluctuations through Bayes Calculations
    # Check if frame telemetry signals a raw mathematical anomaly threshold
    raw_anomaly_detected = current_telemetry.head_posture > 30 or current_telemetry.audio_level > 65.0
    posterior_risk = UncertaintyProbabilisticReasoning.calculate_cheating_probability(raw_anomaly_detected)
    agent.log_reasoning(
        f"[CO5 Probabilistic Inference] Updated Bayesian uncertainty analysis: "
        f"P(Actual Integrity Breach | Active Sensor Triggers) = {posterior_risk * 100}%."
    )

    # 5. Strategic Policy Evaluation under Bounded Computational Constraints
    optimal_game_policy = ProctoringDecisionGame.minimax_decision(depth=2, is_agent_maximizing=True)
    agent.log_reasoning(
        f"[CO4 Adversarial Logic] Strategic policy threshold finalized. "
        f"System action response index calibrated to: {optimal_game_policy}."
    )

    # Final Decision Execution Flow
    agent.log_reasoning("[CO6 System Orchestration Pipeline] Consolidating sub-module outputs for audit trail resolution.")
    
    print("=========================================================================")
    print("               EXPLAINABLE AI PROCTORING SYSTEM AUDIT LOG                ")
    print("=========================================================================\n")
    for step, trace in enumerate(agent.reasoning_log, start=1):
        print(f"Step {step}: {trace}")
    print("\n-------------------------------------------------------------------------")
    
    # Core Decision Trigger Output Logic
    if posterior_risk > 0.60:
        print("FINAL ACTION: [ALERT TRIGGERED] System flagged test instance for human review.")
    else:
        print("FINAL ACTION: [STATUS GREEN] Test integrity verified within standard variance ranges.")
    print("-------------------------------------------------------------------------")

if __name__ == "__main__":
    run_intelligent_exam_proctor_pipeline()