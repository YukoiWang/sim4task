import services
import sims4.commands
import alarms
import clock
import routing
import sims4.math
from typing import Any, Optional
from sims4.resources import Types
from sims4.tuning.instances import TunedInstanceMetaclass

# from TheSims4ScriptModBuilder.game.decompile.base.lib.timeit import repeat

# ================= DEPENDENCIES =================

from sims4communitylib.utils.sims.common_sim_utils import CommonSimUtils
from sims4communitylib.utils.resources.common_interaction_utils import CommonInteractionUtils
from sims4communitylib.utils.sims.common_sim_interaction_utils import CommonSimInteractionUtils

import os

LOG_PATH = os.path.expanduser("~\\Documents\\Sims4Logs")
LOG_FILE = os.path.join(LOG_PATH, "family_script_log.txt")
SKIP_LIMIT = 10

if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)

def clear_log_file():
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("")  # 清空
    except Exception as e:
        print(f"[ScriptDebug]  Failed to clear log file: {e}")

def log_to_file(message: str):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception as e:
        print(f"[ScriptDebug]  Failed to write log file: {e}")


# ================= CONFIGURATION =================

FAMILY_NAMES = {
    "Dad": "Timmy",
    "Mom": "Eliza",
    "Son": "Bob",
    "Daughter": "Tina"
}

SCENARIOS = {
    "Dad": [
        # ("sleep", "object", "bed"),
        ("shower", "world", "shower"),
        ("read",    "world", "bookshelf"),
        # ("cook",   "world", "stove"),
        # ("eat",    "world", "food"),
        ("chat", "sim", "Eliza")

        # ("career",   "self",  None)
    ],
    "Mom": [
        # ("empty",  "world", "trash"),
        ("chat", "sim", "Bob"),
        # ("eat",    "world", "food"),
        ("watch",  "world", "tv"),
        ("read",    "world", "bookshelf")
        # ("career",   "self",  None)
    ],
    "Son": [
        ("chat", "sim", "Eliza"),
        ("practice", "world", "violin"),
        # ("eat",      "world", "food"),
        ("read",    "world", "bookshelf"),
        # ("sleep", "object", "bed"),
    ],
    "Daughter": [
        ("watch",  "world", "tv"),
        ("read",   "world", "bookshelf"),
        ("shower", "object", "shower"),
        # ("chat", "sim", "Timmy")
        # ("sleep", "object", "bed"),
        # ("eat",    "world", "food"),
        # ("dance",  "world", "stereo"),
        # ("paint",  "world", "easel")

        # ("watch",  "world", "tv")
    ]
}


def debug_test_route(sim, obj):
    """Debug: test if the Sim can route to the object's front tile."""
    try:
        obj_pos = obj.position
        obj_forward = obj.forward_vector

        front_pos = sims4.math.Vector3(
            obj_pos.x + obj_forward.x,
            obj_pos.y + obj_forward.y,
            obj_pos.z
        )

        sim_pos = sim.position

        result = routing.test_connectivity_pt_pt(
            sim.routing_location,
            routing.Location(front_pos, sim_pos, sim.routing_surface),
            sim.routing_context
        )

        if result:
            log(f"   [RouteTest]  Sim CAN reach target tile at {front_pos}")
            return True
        else:
            fail_reason = sim.routing_context.get_first_blocking_reason()
            log(f"   [RouteTest]  Route FAILED. Reason = {fail_reason}")
            return False

    except Exception as e:
        log(f"   [RouteTest]  Exception: {e}")
        return False

# ================= GLOBAL CONTEXT =================
class Context:
    alarm_handle = None
    connection = None
    alarm_owner = object()
    cursor = {k: 0 for k in SCENARIOS.keys()}
    fail_count = {k: 0 for k in SCENARIOS.keys()}
    running = False
    script_affordance_ids = {}
    skipped_tasks = {}

def log(msg):
    """Print logs to cheat console and Python output"""
    full_msg = f"[ScriptDebug] {msg}"

    print(full_msg)
    if Context.connection:
        try:
            output = sims4.commands.CheatOutput(Context.connection)
            output(f"> {msg}")
        except:
            pass
    log_to_file(full_msg)

def _sim_id_for_sim(sim):
    try:
        return sim.sim_info.id
    except Exception:
        try:
            return sim.id
        except Exception:
            return None

def mark_affordance_as_script(sim, affordance_guid64):
    try:
        sim_id = _sim_id_for_sim(sim)
        if sim_id is None:
            return
        s = Context.script_affordance_ids.get(sim_id)
        if s is None:
            s = set()
            Context.script_affordance_ids[sim_id] = s
        s.add(int(affordance_guid64))
    except Exception as e:
        log(f"   [Marker] Exception when marking affordance: {e}")

def is_affordance_marked_script(sim, affordance_guid64):
    try:
        sim_id = _sim_id_for_sim(sim)
        if sim_id is None:
            return False
        s = Context.script_affordance_ids.get(sim_id, set())
        return int(affordance_guid64) in s
    except Exception:
        return False

def block_system_actions(sim, allow_script_actions=True):

    try:
        sim_info = CommonSimUtils.get_sim_info(sim)
        queue = sim.queue
        if not queue:
            return
        for interaction in list(queue):
            try:
                if is_interaction_from_script(interaction):
                    continue
                affordance = getattr(interaction, "affordance", None)
                if affordance is not None:
                    guid = getattr(affordance, "guid64", None)
                    if guid is not None and is_affordance_marked_script(sim, guid):
                        continue

                CommonSimInteractionUtils.cancel_interaction(
                    interaction,
                    cancel_reason="...",
                    immediate=True,
                    ignore_must_run=True
                )

                log(f"   [Blocker] Canceled system interaction: {interaction}")
            except Exception as e:
                log(f"   [Blocker] Exception when canceling an interaction: {e}")
    except Exception as e:
        log(f"   [Blocker] Exception in block_system_actions: {e}")

def is_interaction_from_script(interaction_obj):
    try:
        return bool(getattr(interaction_obj, "_from_script", False))
    except Exception:
        return False

def is_passive_or_idle_interaction(interaction: Any) -> bool:
    if interaction is None:
        return True

    tuning_name = str(interaction).lower()

    if any(keyword in tuning_name for keyword in ['stand_passive', 'idle', 'sit_passive', 'passive_consume']):
        return True

    # if interaction.priority <= interactions.priority.Priority.Low:
    #     return True

    return False

def fill_needs_no_buff(sim):
    tracker = sim.commodity_tracker
    for commodity in tracker:
        if commodity.is_visible:
            tracker.set_value(commodity, commodity.max_value)

# ================= CORE LOOP =================

def run_tick(_):

    if not Context.running:
        log("[Tick] Stopped -- no further ticks will be scheduled.")
        return

    try:
        log("======  TICK START ======")

        for role, actions in SCENARIOS.items():

            idx = Context.cursor.get(role, 0)
            total = len(actions)

            log(f"[{role}] ===  PROCESSING {role} | Task {idx+1}/{total} ===")

            # === STEP 1: FIND SIM ===
            sim = native_find_sim(role)
            if not sim:
                log(f"[{role}] Sim '{role}' Not Found")
                continue

            fill_needs_no_buff(sim)
            log(f"[{role}]  Found Sim Instance")

            # === STEP 2: CHECK BUSY ===
            current_running_interaction = sim.queue.running

            if current_running_interaction:
                if is_interaction_from_script(current_running_interaction):
                    log(f"[{role}]  Sim is busy performing OUR SCRIPTED ACTION: '{str(current_running_interaction)}'. Waiting...")
                    continue

                if is_passive_or_idle_interaction(current_running_interaction):
                    log(f"[{role}] ℹRunning Passive Action: '{str(current_running_interaction)}'. Ignoring...")
                else:
                    log(f"[{role}] Sim is busy performing NON-PASSIVE action: '{str(current_running_interaction)}'. Waiting...")
                    continue

            log(f"[{role}] Sim Idle, Ready For Action")

            # === STEP 3: GET ACTION ===
            if idx >= total:
                log(f"[{role}] All tasks completed")
                continue

            action_kw, target_type, target_kw = actions[idx]
            log(f"[{role}] Task Info -> Action='{action_kw}', TargetType='{target_type}', Target='{target_kw}'")

            now = services.time_service().sim_now
            cooldown = clock.interval_in_sim_minutes(30)

            last = Context.skipped_tasks.get(role, {}).get(action_kw)

            if last and now - last < cooldown:
                log(f"[{role}] ⏸ '{action_kw}' is cooling down. Defer and try others.")

                task = actions.pop(idx)
                actions.append(task)

                continue
            # ===== 🔥 COOLDOWN CHECK END =====

            # === STEP 4: PUSH INTERACTION ===
            log(f"[{role}] Attempting Interaction Push...")
            success = push_interaction(sim, action_kw, target_type, target_kw)

            if success:
                log(f"[{role}] SUCCESS: '{action_kw}' queued! -> Moving to next task")
                Context.cursor[role] = idx + 1
                Context.fail_count[role] = 0

            else:
                Context.fail_count[role] += 1
                fail_n = Context.fail_count[role]

                log(f"[{role}] FAILED ({fail_n} times) -> Action='{action_kw}', Target='{target_kw}'")

                if fail_n >= 10:
                    log(f"[{role}] ⏭ Too many failures. Defer + enter cooldown.")

                    task = actions.pop(idx)
                    actions.append(task)

                    Context.skipped_tasks.setdefault(role, {})
                    Context.skipped_tasks[role][action_kw] = now

                    Context.fail_count[role] = 0


    except Exception as e:
        log(f" CRITICAL ERROR inside run_tick: {e}")

    return True

def native_find_sim(role_or_name: str, output: Any = None) -> Optional[Any]:

    target_name = role_or_name.lower()

    real_name = FAMILY_NAMES.get(role_or_name)
    if real_name:
        target_name = real_name.lower()
        if output:
            output(f"   [FindSim] Found Role '{role_or_name}', Searching for Name '{target_name}'.")
    else:
        if output:
            output(f"   [FindSim] Searching directly for Name '{target_name}'.")

    sim_info_manager = services.sim_info_manager()
    if not sim_info_manager:
        if output:
            output("   [FindSim] Error: SimInfo Manager not available.")
        return None

    found_sim_instance = None

    if output:
        loaded_sim_names = [s.first_name for s in sim_info_manager.objects]
        output(f"   [FindSim] All Loaded SimInfo Names: {loaded_sim_names}")

    for sim_info in sim_info_manager.objects:
        if sim_info.first_name.lower() == target_name:
            sim_instance = sim_info.get_sim_instance()

            if sim_instance:
                found_sim_instance = sim_instance
                if output:
                    output(f"   [FindSim] Found Sim Instance: {found_sim_instance.first_name}")
                break

    if found_sim_instance is None and output:
        output(f"   [FindSim] Sim Instance '{target_name}' not found (Not Loaded).")

    return found_sim_instance

def stop(_connection=None):
    log("=== Script Stopping... ===")

    Context.running = False

    if Context.alarm_handle is not None:
        alarms.cancel_alarm(Context.alarm_handle)
        Context.alarm_handle = None

    log("=== Script Fully Stopped ===")

def push_interaction(sim, action_kw, target_type, target_kw):

    # 1. 前置检查
    if not action_kw:
        log("   [Push] Error: Action keyword is None/Empty.")
        return False
    action_kw_lower = action_kw.lower()

    try:
        candidates = []

        # 2. Search Candidates
        log(f"   [Push] Searching for target... Type: {target_type}, Keyword: {target_kw}")

        target_kw_lower = target_kw.lower() if target_kw else None

        # 非 self/sim 目标必须有关键字
        if target_type != "self" and target_type != "sim" and target_kw_lower is None:
            log("   [Push] Error: Target keyword is None/Empty for current type.")
            return False

        # 针对 'world' 目标的查找逻辑
        if target_type == "world":
            obj_mgr = services.object_manager()
            if obj_mgr:
                # 🛠️ 修正点 1：仅进行普通对象查找（移除了 Food 特殊查找）
                for obj in obj_mgr.get_all():
                    if not obj.is_sim and target_kw_lower in str(obj).lower():
                        candidates.append(obj)

        elif target_type == "inv":
            if getattr(sim, "inventory_component", None):
                for obj in sim.inventory_component:
                    if target_kw_lower and target_kw_lower in str(obj).lower():
                        candidates.append(obj)

        elif target_type == "sim":
            target_sim = native_find_sim(target_kw)
            if target_sim:
                candidates = [target_sim]
            else:
                log(f"   [Push] Target Sim '{target_kw}' not found nearby.")

        elif target_type == "self":
            candidates = [sim]

        # 3. Report Search Results
        log(f"   [Push] Found {len(candidates)} candidate object(s).")

        if not candidates:
            log("   [Push] No candidates found.")
            return False

        # 4. Match and Queue
        sim_info = CommonSimUtils.get_sim_info(sim)

        for obj in candidates:
            if not hasattr(obj, 'super_affordances'):
                continue

            log(f"   [Push] Checking Affordances on object: {obj}")

            for aff in obj.super_affordances():
                aff_name = CommonInteractionUtils.get_interaction_short_name(aff)
                if aff_name is None:
                    continue

                aff_name_lower = aff_name.lower()
                forbidden = ["picker", "pie_menu", "createobject", "create_situation", "ask"]

                if any(bad in aff_name_lower for bad in forbidden):
                    continue

                # 动作关键词匹配 (使用预先转换的 action_kw_lower)
                if action_kw_lower in aff_name_lower:
                    # 🛠️ 修正点 2：移除了 eat 的特殊过滤逻辑

                    log(f"   [Push] MATCH: Interaction '{aff_name}' found on object '{obj}'")

                    candidate_guid = getattr(aff, "guid64", None)

                    # 尝试推送交互
                    result = CommonSimInteractionUtils.queue_super_interaction(
                        sim_info, aff.guid64, target=obj
                    )

                    if result:
                        # 成功后的脚本标记逻辑（原封不动）
                        # ... (mark_affordance_as_script 和 queued_inter 逻辑保持不变) ...

                        log("   [Push] S4CL Queue Result: SUCCESS")
                        return True
                    else:
                        log("   [Push] S4CL Queue Result: FAILED (Blocked/In Use)")
                        # 如果失败了，就尝试下一个 candidate/affordance 组合

        log("   [Push] No matching interaction found on any candidate.")
        return False

    except Exception as e:
        # 捕捉所有的潜在崩溃，并记录
        log(f"   [Push] Exception Error: {e}")
        return False

# ================= COMMANDS =================

@sims4.commands.Command('family.start', command_type=sims4.commands.CommandType.Live)
def script_start_command(_connection=None):
    # 1. Refresh Connection
    Context.connection = _connection
    output = sims4.commands.CheatOutput(_connection)
    clear_log_file()
    log_to_file("======== New Session Started ========")

    output("=======================================")
    output(" Family Script STARTED (Verbose Mode)")
    output(" Please keep console open to see logs.")
    output("=======================================")

    # 2. Clear Old Alarm
    if Context.alarm_handle is not None:
        try:
            alarms.cancel_alarm(Context.alarm_handle)
        except:
            pass
        Context.alarm_handle = None

    # 3. Reset Progress
    Context.cursor = {k: 0 for k in SCENARIOS.keys()}
    Context.fail_count = {k: 0 for k in SCENARIOS.keys()}
    Context.running = True
    # 4. Kickstart Loop
    Context.alarm_handle = alarms.add_alarm(
        Context.alarm_owner,
        clock.interval_in_real_seconds(5.0),
        run_tick,
        repeating=True
    )

@sims4.commands.Command('family.stop', command_type=sims4.commands.CommandType.Live)
def script_stop_command(_connection=None):
    output = sims4.commands.CheatOutput(_connection)

    Context.running = False

    if Context.alarm_handle is not None:
        try:
            alarms.cancel_alarm(Context.alarm_handle)
        except:
            pass
        Context.alarm_handle = None

    output(" Family Script STOPPED")