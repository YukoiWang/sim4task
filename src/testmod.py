import services
import sims4.commands
import sims4.resources
# 显式导入
import interactions.context
import interactions.priority
# from sims4communitylib.utils.sims.common_sim_interaction_utils import CommonSimInteractionUtils
# from sims4communitylib.utils.resources.common_interaction_utils import CommonInteractionUtils
# from sims4communitylib.utils.sims.common_sim_utils import CommonSimUtils

ACTION_ID = 13950 # 淋浴

@sims4.commands.Command('sled.test_bob_shower', command_type=sims4.commands.CommandType.Live)
def sled_test_final(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output(">> [Final] Using Official Method: push_super_affordance")

    try:
        # 1. 找人 (Eliza)
        target_sim = None
        sim_info_manager = services.sim_info_manager()
        for sim_info in sim_info_manager.objects:
            if sim_info.first_name == "Bob":
                target_sim = sim_info.get_sim_instance()
                break

        if not target_sim:
            output("Error: Timmy not found!")
            return

        # 2. 找物体 (Shower)
        target_object = None
        object_manager = services.object_manager()
        for obj in object_manager.objects:
            if "shower" in str(obj).lower():
                target_object = obj
                break

        # 如果找不到淋浴间，为了测试，我们把 Target 设为 None 试试 (有些动作不需要 Target)
        if not target_object:
            output("Warning: No shower found. Trying without target...")
        else:
            output(f"Target: {target_object}")

        # 3. 获取 Affordance
        affordance = services.affordance_manager().get(ACTION_ID)
        if not affordance:
            output("Error: Invalid Action ID")
            return

        # 4. 创建 Context (照搬官方逻辑)
        # client=None, pick=None 这些我们可以省去，用默认值
        # context = interactions.context.InteractionContext(
        #     target_sim,
        #     interactions.context.InteractionContext.SOURCE_SCRIPT,
        #     interactions.priority.Priority.High
        # )
        # ... (代码上部保持不变)

        # 4. 创建 Context (修改为更强的权限和插入策略)
        context = interactions.context.InteractionContext(
            target_sim,
            # === 核心修改点 1: 来源 ===
            # 使用 AUTONOMY 来源通常会绕过用户界面发出的交互的限制
            interactions.context.InteractionContext.SOURCE_AUTONOMY,

            interactions.priority.Priority.High,

            # === 核心修改点 2: 插入策略 ===
            # 立即执行，而不是乖乖排队到最后
            insert_strategy=interactions.context.QueueInsertStrategy.NEXT
        )

        # 5. 推送动作 (使用官方同款方法！)
        output(">> Pushing via push_super_affordance with AUTONOMY source...")

        # ... (代码下部保持不变)

        # 5. 推送动作 (使用官方同款方法！)
        output(">> Pushing via push_super_affordance...")

        # === 核心修改点 ===
        # 使用 push_super_affordance 而不是 push_super_interaction
        result = target_sim.push_super_affordance(affordance, target_object, context)

        # affordance = CommonInteractionUtils.get_interaction_by_id(ACTION_ID)
        # sim_info = CommonSimUtils.get_sim_info(target_sim)
        #
        # result = CommonSimInteractionUtils.queue_super_interaction(
        #     sim_info=sim_info,
        #     affordance_id=affordance.guid64,
        #     target=target_object
        # )
        if result:
            output(">> SUCCESS: Interaction Pushed!")
        else:
            output(">> FAILED: Game returned False.")

    except Exception as e:
        output(f"CRASH: {str(e)}")