// Reusable Repel prompt, without altering saves or battle encounter rules.
EventScript_RepelWoreOff::
    checkitem ITEM_MAX_REPEL
    goto_if_eq VAR_RESULT, TRUE, EventScript_RepelPromptMax
    checkitem ITEM_SUPER_REPEL
    goto_if_eq VAR_RESULT, TRUE, EventScript_RepelPromptSuper
    checkitem ITEM_REPEL
    goto_if_eq VAR_RESULT, TRUE, EventScript_RepelPromptRegular
    msgbox Text_RepelWoreOff, MSGBOX_SIGN
    end

EventScript_RepelPromptMax::
    msgbox Text_RepelAskAgain, MSGBOX_YESNO
    goto_if_eq VAR_RESULT, YES, EventScript_RepelUseMax
    end

EventScript_RepelPromptSuper::
    msgbox Text_RepelAskAgain, MSGBOX_YESNO
    goto_if_eq VAR_RESULT, YES, EventScript_RepelUseSuper
    end

EventScript_RepelPromptRegular::
    msgbox Text_RepelAskAgain, MSGBOX_YESNO
    goto_if_eq VAR_RESULT, YES, EventScript_RepelUseRegular
    end

EventScript_RepelUseMax::
    removeitem ITEM_MAX_REPEL, 1
    setvar VAR_REPEL_STEP_COUNT, 250
    msgbox Text_RepelReused, MSGBOX_SIGN
    end

EventScript_RepelUseSuper::
    removeitem ITEM_SUPER_REPEL, 1
    setvar VAR_REPEL_STEP_COUNT, 200
    msgbox Text_RepelReused, MSGBOX_SIGN
    end

EventScript_RepelUseRegular::
    removeitem ITEM_REPEL, 1
    setvar VAR_REPEL_STEP_COUNT, 100
    msgbox Text_RepelReused, MSGBOX_SIGN
    end

Text_RepelWoreOff:
    .string "REPEL's effect wore off…$"

Text_RepelAskAgain:
    .string "REPEL wore off.\nUse another one?$"

Text_RepelReused:
    .string "A new REPEL took effect!$"
