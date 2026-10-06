#ifndef GUARD_QUEST_LOG_H
#define GUARD_QUEST_LOG_H

void QuestLog_Open(void);
void QuestLog_Close(void);
bool8 QuestLog_Update(void);
bool8 QuestLog_HasActiveQuest(void);
u16 QuestLog_GetCurrentTargetMapSecId(void);
const u8 *QuestLog_GetCurrentTitle(void);
u8 QuestLog_GetStoryProgress(void);
u8 QuestLog_GetStoryTotal(void);

#endif // GUARD_QUEST_LOG_H
