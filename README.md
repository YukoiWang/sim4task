My main codes are in the ./src/test_alarm.py. 

### Implementation Logic & Core Architecture
I utilized a State Machine combined with a Polling design pattern to orchestrate Sim behaviors.
1. Global Context Management
The script uses a singleton Context class to manage the global state of the simulation:
Cursor: Tracks the current task index for each role (e.g., which step of the scenario the Sim is currently on).
Fail Count: Records the number of consecutive failures for the current task.
Skipped Tasks: Stores tasks that have been deferred due to excessive failures, along with their cooldown timestamps.
2. The Core Loop (Tick System)
The script registers a run_tick function via alarms.add_alarm, which triggers every 5 real-time seconds.
State Detection: Checks if the target Sim exists and validates their current "Busy" state.
Smart Filtering: The script distinguishes between three states:
Script Task: The Sim is doing what we told them to do (Wait).
Player Action: The Sim is doing something important (Wait).
Passive/Idle: The Sim is merely standing, listening, or idling (Interrupt and Execute).
Execution: It retrieves the instruction pointed to by the Cursor and attempts to find the target object and push the interaction.
3. Error Handling & Cooldown Mechanism
Retry: If an interaction push fails (e.g., route blocked), the failure count increments.
Deferral: If a specific task fails 10 consecutive times, the script moves that task to the end of the queue.
Cooldown: To prevent infinite loops on broken interactions, the deferred task enters a 30 in-game minute cooldown period during which it will be skipped.
### Functiona Introbuction
## Core Control
1. run_tick(_)
* Function: The "Heart" of the script. Runs periodically via the alarm.
* Logic:
Iterates through every role defined in SCENARIOS.
Calls native_find_sim to retrieve the Sim instance.
Calls fill_needs_no_buff to maximize needs (preventing autonomy or death from interrupting the script).
* Queue Inspection:
If running a Script Interaction → Wait.
If running a Passive/Idle Interaction → Ignore (proceed to push new task).
If running a System/Player Interaction → Wait.
* Cooldown Check: If the current task is still in the cooldown period, move it to the end of the queue and skip this tick.
Calls push_interaction to attempt the task.
Updates Context.cursor (on success) or Context.fail_count (on failure).

2. push_interaction(sim, action_kw, target_type, target_kw)
* Function: Converts abstract string commands into actual gameplay interactions.
* Parameters:
action_kw: Interaction keyword (e.g., "shower").
target_type: Target category (world, inv [inventory], sim, self).
target_kw: Target name keyword (e.g., "book").
* Logic:
Searches for candidate Objects or Sims based on target_type.
Iterates through all Super Affordances (interactions) on the candidate.
Filters out forbidden types (e.g., picker, ask, create_situation).
Matches the interaction name against action_kw.
Uses S4CL (queue_super_interaction) to push the interaction into the Sim's queue.
## Helper Functions Introduction
1. native_find_sim(role_or_name, output)
Function: Locates a loaded Sim instance based on the configuration role or raw name.
Logic: First checks the FAMILY_NAMES mapping, then scans the sim_info_manager for a matching first name.
2. fill_needs_no_buff(sim)
Function: Instantly fills all visible commodities (Hunger, Energy, etc.).
Purpose: Ensures the script runs smoothly without the Sim attempting to fix low needs autonomously.
3. is_passive_or_idle_interaction(interaction)
Function: Determines if the Sim's current action is "meaningless" (e.g., idling, standing passive, listening).
Returns: True if the Sim is effectively available, allowing the script to interrupt and insert a new task.

## Logging System
log(msg) / log_to_file(message)
Function: Dual-output logging.
Displays in the in-game Cheat Console.
Writes to a local file: ~/Documents/Sims4Logs/family_script_log.txt.
Purpose: Used for debugging script status, pathfinding results, and error tracking.
debug_test_route(sim, obj)
Function: Developer debugging tool.
Logic: Tests if the Sim can successfully calculate a path from their current location to the target object's front tile.
## Command Interface
* Initializes and starts the script: family.start
Operations: Clears logs, resets task cursors, resets failure counts, and registers the run_tick alarm.
* Stops the script: family.stop
Operations: Cancels the alarm and halts the loop.
